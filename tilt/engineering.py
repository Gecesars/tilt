"""Pure RF model. Positive tilt points down; E1 is the lowest element.

All lengths are metres internally. The model is an equal-power parallel feed,
with identical elements and no mutual coupling or individual element pattern.
"""
from dataclasses import asdict, dataclass
import math

C_SI = 299_792_458.0
C_WORKSHEET = 300_000_000.0


def finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label}: informe um número finito.')


def parse_decimal(text: str, label='Valor') -> float:
    """Accept comma OR dot decimal. Reject ambiguous thousands separators."""
    clean = text.strip()
    if not clean or (',' in clean and '.' in clean) or ' ' in clean:
        raise ValueError(f'{label}: use vírgula ou ponto decimal, sem separador de milhar.')
    try:
        value = float(clean.replace(',', '.'))
    except ValueError as exc:
        raise ValueError(f'{label}: número inválido.') from exc
    finite(value, label)
    return value


def channel_frequency(channel: int, standard='tv') -> float:
    if isinstance(channel, bool) or not isinstance(channel, int):
        raise ValueError('Canal deve ser inteiro.')
    if standard == 'tv':
        if 2 <= channel <= 4:
            return 57.0 + (channel - 2) * 6
        if 5 <= channel <= 6:
            return 79.0 + (channel - 5) * 6
        if 7 <= channel <= 13:
            return 177.0 + (channel - 7) * 6
        if 14 <= channel <= 69:
            return 473.0 + (channel - 14) * 6
    raise ValueError('Canal de TV fora da tabela de conversão (2–69).')


@dataclass(frozen=True)
class Design:
    frequency_mhz: float = 623.0
    elements: int = 4
    spacing_m: float = 0.48
    tilt_deg: float = 2.0
    velocity_factor: float = 0.88
    shortest_branch_m: float = 3.0
    common_feeder_m: float = 0.0
    attenuation_db_100m: float | None = None
    extra_loss_db: float = 0.0
    input_power_w: float = 1000.0
    cut_step_mm: float = 0.1
    speed_m_s: float = C_WORKSHEET

    def validate(self):
        for name, value in asdict(self).items():
            if name == 'attenuation_db_100m' and value is None:
                continue
            finite(value, name)
        if type(self.elements) is not int or not 2 <= self.elements <= 64:
            raise ValueError('Quantidade de elementos: use um inteiro entre 2 e 64.')
        if not 0.1 <= self.frequency_mhz <= 100_000:
            raise ValueError('Frequência: use de 0,1 a 100.000 MHz.')
        if not 0 < self.spacing_m <= 100:
            raise ValueError('Espaçamento: use um valor maior que zero e até 100 m.')
        if not -89 <= self.tilt_deg <= 89:
            raise ValueError('Tilt: use de −89° a +89°.')
        if not 0 < self.velocity_factor <= 1:
            raise ValueError('Fator de velocidade: deve ser maior que 0 e até 1.')
        if not 0 <= self.shortest_branch_m <= 10_000 or not 0 <= self.common_feeder_m <= 100_000:
            raise ValueError('Comprimentos fora dos limites da bancada.')
        if self.attenuation_db_100m is not None and not 0 <= self.attenuation_db_100m <= 100_000:
            raise ValueError('Atenuação: use um valor não negativo em dB/100 m.')
        if not 0 <= self.extra_loss_db <= 100:
            raise ValueError('Perdas adicionais: use de 0 a 100 dB.')
        if not 0 < self.input_power_w <= 1e9:
            raise ValueError('Potência de entrada: use um valor positivo até 1 GW.')
        if not 0 <= self.cut_step_mm <= 100:
            raise ValueError('Passo de corte: use de 0 a 100 mm (0 = ideal).')
        if self.speed_m_s not in (C_WORKSHEET, C_SI):
            raise ValueError('Selecione c da planilha ou c do SI.')


@dataclass(frozen=True)
class Element:
    number: int
    height_m: float
    ideal_length_m: float
    length_m: float
    relative_phase_deg: float
    phase_error_deg: float
    loss_db: float | None
    power_w: float | None


@dataclass(frozen=True)
class Result:
    design: Design
    wavelength_m: float
    guided_wavelength_m: float
    delta_length_m: float
    phase_step_deg: float
    delay_step_ns: float
    fitted_tilt_deg: float | None
    feed_efficiency: float | None
    coherence_efficiency: float
    total_power_w: float | None
    equivalent_loss_db: float | None
    elements: tuple[Element, ...]
    grating_angles_deg: tuple[float, ...]
    warnings: tuple[str, ...]


def calculate(design: Design) -> Result:
    design.validate()
    d = design
    wavelength = d.speed_m_s / (d.frequency_mhz * 1e6)
    guided = wavelength * d.velocity_factor
    sine = math.sin(math.radians(d.tilt_deg))
    delta = d.velocity_factor * d.spacing_m * sine
    phase = 360 * d.spacing_m / wavelength * sine
    raw = [-i * delta for i in range(d.elements)]
    ideal = [d.shortest_branch_m + v - min(raw) for v in raw]
    step = d.cut_step_mm / 1000
    lengths = [math.floor(v / step + 0.5 + 1e-10) * step if step else v for v in ideal]
    common_loss = (d.attenuation_db_100m * d.common_feeder_m / 100 + d.extra_loss_db
                   if d.attenuation_db_100m is not None else None)
    rows, amps, errors = [], [], []
    for i, (actual, target) in enumerate(zip(lengths, ideal)):
        actual_phase = -360 * (actual - lengths[0]) / guided
        error = actual_phase - i * phase
        loss = (common_loss + actual * d.attenuation_db_100m / 100
                if common_loss is not None else None)
        power = d.input_power_w / d.elements * 10 ** (-loss / 10) if loss is not None else None
        rows.append(Element(i + 1, i * d.spacing_m, target, actual, actual_phase, error, loss, power))
        # Common losses cancel in coherence. Scaling by the shortest branch
        # avoids underflow for very large but finite attenuation inputs.
        relative_loss = (d.attenuation_db_100m or 0) * (actual-min(lengths)) / 100
        amps.append(10 ** (-relative_loss / 20))
        errors.append(math.radians(error))
    total = sum(row.power_w for row in rows) if common_loss is not None else None
    efficiency = total / d.input_power_w if total is not None else None
    equivalent_loss = None
    if common_loss is not None:
        least_loss = min(row.loss_db for row in rows)
        relative_transmission = sum(10**(-(row.loss_db-least_loss)/10) for row in rows)/d.elements
        equivalent_loss = least_loss - 10*math.log10(relative_transmission)
    # Coherence at the requested tilt, including amplitude imbalance and cut rounding.
    numerator = abs(sum(a * complex(math.cos(e), math.sin(e)) for a, e in zip(amps, errors))) ** 2
    denominator = d.elements * sum(a * a for a in amps)
    coherence = min(1.0, numerator / denominator) if denominator else 0.0
    center = (d.elements - 1) / 2
    slope = sum((i-center) * v for i, v in enumerate(lengths)) / sum((i-center)**2 for i in range(d.elements))
    fitted_sine = -slope / (d.velocity_factor * d.spacing_m)
    fitted = math.degrees(math.asin(fitted_sine)) if abs(fitted_sine) <= 1 else None
    # Ideal uniform-array alias directions, reported as elevation (positive upwards).
    grating = []
    ratio = wavelength / d.spacing_m
    # At most 16 directions shown; a dense array can have very many aliases.
    m_min = math.ceil((-1 + sine) / ratio)
    m_max = math.floor((1 + sine) / ratio)
    for m in range(max(m_min, -8), min(m_max, 8) + 1):
        if m and -1 <= -sine + m * ratio <= 1:
            grating.append(math.degrees(math.asin(-sine + m * ratio)))
    warnings = []
    if grating:
        warnings.append('O espaçamento permite lóbulos de grade. O tilt não define uma direção única de radiação.')
    if d.attenuation_db_100m is None:
        warnings.append('Atenuação não informada: eficiência de alimentação e potência entregue indisponíveis.')
    if d.shortest_branch_m == 0:
        warnings.append('Ramal mínimo zero: verifique o percurso físico até cada elemento.')
    if fitted is None or abs(fitted - d.tilt_deg) > 0.1:
        warnings.append('O passo de corte altera a progressão de tilt em mais de 0,1° ou impede sua realização.')
    return Result(d, wavelength, guided, delta, phase, d.spacing_m*sine/d.speed_m_s*1e9,
                  fitted, efficiency, coherence, total,
                  equivalent_loss,
                  tuple(rows), tuple(grating), tuple(warnings))


def array_pattern(result: Result, angles=None, untilted=False):
    """Normalized field in dB, floor -60 dB. No assertion of antenna gain."""
    if angles is None:
        angles = [-90 + i * 0.1 for i in range(1801)]
    d = result.design
    # Only differential losses affect normalized shape; avoid numerical underflow.
    minimum_length = min(e.length_m for e in result.elements)
    weights = [10 ** (-(d.attenuation_db_100m or 0) * (e.length_m-minimum_length) / 2000)
               for e in result.elements]
    norm = sum(weights)
    values = []
    for angle in angles:
        sine = math.sin(math.radians(angle))
        real = imag = 0.0
        for e, a in zip(result.elements, weights):
            phase = 2*math.pi*e.height_m/result.wavelength_m*sine
            if not untilted:
                phase += math.radians(e.relative_phase_deg)
            real += a*math.cos(phase)
            imag += a*math.sin(phase)
        values.append(max(-60.0, 20*math.log10(max(math.hypot(real, imag)/norm, 1e-3))))
    return list(angles), values
