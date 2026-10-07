"""Frozen material/rating evidence captured at calculation time, never on export."""
from bisect import bisect_left
from dataclasses import dataclass


@dataclass(frozen=True)
class LineSpecification:
    model: str
    kind: str
    frequency_mhz: float
    catalog_sha256: str
    source: str
    impedance_ohm: float | None
    catalog_velocity_factor: float | None
    average_power_w: float | None
    peak_power_w: float | None
    peak_voltage_v: float | None
    interpolation: str
    supporting_samples: tuple[tuple[float, float, float], ...]
    branch_input_w: float | None
    branch_margin_w: float | None
    common_input_w: float | None
    common_margin_w: float | None
    source_average_limit_w: float | None
    status: str
    conditions: str


RATING_CONDITIONS = (
    'Potência média máxima de referência do catálogo na frequência informada. '
    'O XML não informa temperatura, altitude ou ROE de referência. '
    'Não foram aplicados fatores de redução para a instalação. '
    'Conectores e divisor podem impor limites menores. Potência de pico é um limite '
    'separado do catálogo; sem fator de crista do sinal, a verificação de pico fica pendente.'
)


def line_specification(result, cable, model, kind, catalog_hash):
    d = result.design
    # Extra losses have no specified location: do not credit them as protection.
    branch = (d.input_power_w / d.elements * 10**(-d.attenuation_db_100m*d.common_feeder_m/1000)
              if d.attenuation_db_100m is not None else
              d.input_power_w/d.elements if d.common_feeder_m == 0 else None)
    common = d.input_power_w if d.common_feeder_m > 0 else None
    average = peak = voltage = impedance = vf = limit = None
    samples = ()
    method = 'indisponível'
    if cable is not None:
        _, kw = cable.at(d.frequency_mhz)
        average, peak, voltage = kw*1000, cable.peak_power_kw*1000, cable.peak_voltage_v
        impedance, vf = cable.impedance_ohm, cable.velocity_factor
        idx = bisect_left([row[0] for row in cable.samples], d.frequency_mhz)
        exact = cable.samples[idx][0] == d.frequency_mhz
        samples = (cable.samples[idx],) if exact else cable.samples[idx-1:idx+1]
        method = 'amostra exata' if exact else 'log-log entre amostras adjacentes'
        # The common feeder and branches use the same selected material.
        limit = average if common is not None else average*d.elements
    branch_margin = average-branch if average is not None and branch is not None else None
    common_margin = average-common if average is not None and common is not None else None
    margins = [v for v in (branch_margin, common_margin) if v is not None]
    status = ('indisponível' if average is None or branch is None else
              'excede referência' if any(v < 0 for v in margins) else 'dentro da referência')
    return LineSpecification(model, kind, d.frequency_mhz, catalog_hash,
        'ADT-PY / Rating / CableRating.xml' if cable is not None else 'Modelo personalizado; sem potência nominal',
        impedance, vf, average, peak, voltage, method, samples, branch, branch_margin,
        common, common_margin, limit, status, RATING_CONDITIONS)
