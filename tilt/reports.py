"""Traceable CSV and printable HTML; values use the last explicitly calculated design."""
import csv
from dataclasses import asdict
from html import escape
import json
from pathlib import Path

from .engineering import Result


def fmt(value, digits=3):
    return 'n/d' if value is None else f'{value:.{digits}f}'.replace('.', ',')


def snapshot(result: Result, model: str, catalog_hash: str):
    return {'schema_version': 1, 'engine_version': '1.0.0', 'model': model,
            'catalog_sha256': catalog_hash, 'result': asdict(result)}


def export_csv(path: Path, result: Result, model: str):
    d = result.design
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream, delimiter=';')
        writer.writerow(['EFTX Tilt', '1.0.0'])
        writer.writerow(['Modelo', model])
        for key, value in asdict(d).items():
            writer.writerow([key, '' if value is None else str(value).replace('.', ',')])
        writer.writerow(['feed_efficiency_percent', fmt(result.feed_efficiency*100 if result.feed_efficiency is not None else None)])
        writer.writerow(['coherence_efficiency_percent', fmt(result.coherence_efficiency*100)])
        writer.writerow(['Convenção', 'E1 inferior; tilt positivo para baixo; fase relativa a E1'])
        writer.writerow(['Elemento', 'Altura (m)', 'Comprimento ideal (mm)', 'Comprimento de corte (mm)',
                         'Fase relativa (graus)', 'Erro de fase (graus)', 'Perda total (dB)', 'Potência (W)'])
        for e in result.elements:
            writer.writerow([f'E{e.number}', fmt(e.height_m, 6), fmt(e.ideal_length_m*1000, 6),
                             fmt(e.length_m*1000, 6), fmt(e.relative_phase_deg, 6),
                             fmt(e.phase_error_deg, 6), fmt(e.loss_db, 6), fmt(e.power_w, 6)])
        for warning in result.warnings:
            writer.writerow(['Observação', warning])
        writer.writerow(['Limite do modelo', 'Divisão igual, elementos idênticos; sem acoplamento, ROE ou rendimento de radiação.'])


def report_html(result: Result, model: str, title: str):
    d = result.design
    rows = ''.join('<tr>' + ''.join(f'<td>{escape(str(x))}</td>' for x in [
        f'E{e.number}', fmt(e.height_m), fmt(e.ideal_length_m*1000), fmt(e.length_m*1000),
        fmt(e.relative_phase_deg), fmt(e.phase_error_deg), fmt(e.loss_db), fmt(e.power_w)]) + '</tr>'
        for e in result.elements)
    inputs = ''.join(f'<tr><td>{escape(key)}</td><td>{escape(str(value))}</td></tr>' for key, value in [
        ('Frequência', f'{fmt(d.frequency_mhz)} MHz'), ('Modelo', model),
        ('Quantidade de elementos', d.elements), ('Espaçamento', f'{fmt(d.spacing_m*1000)} mm'),
        ('Tilt solicitado (positivo para baixo)', f'{fmt(d.tilt_deg)}°'),
        ('Fator de velocidade', fmt(d.velocity_factor, 6)), ('Atenuação', f'{fmt(d.attenuation_db_100m)} dB/100 m'),
        ('Ramal mais curto', f'{fmt(d.shortest_branch_m)} m'), ('Linha comum', f'{fmt(d.common_feeder_m)} m'),
        ('Perdas adicionais totais', f'{fmt(d.extra_loss_db)} dB'), ('Potência na entrada', f'{fmt(d.input_power_w)} W'),
        ('Passo de corte', f'{fmt(d.cut_step_mm)} mm'), ('Velocidade c', f'{d.speed_m_s:g} m/s')])
    warnings = ''.join(f'<li>{escape(w)}</li>' for w in result.warnings)
    return f'''<html><head><meta charset="utf-8"><style>
    body {{font-family:Segoe UI,Arial;color:#16283e;font-size:10pt}} h1 {{color:#142ea3}}
    table {{border-collapse:collapse;width:100%;margin:12px 0}} td,th {{padding:6px;border:1px solid #cbd5e1}}
    th {{background:#edf3fa}} h2 {{font-size:13pt}} .note {{color:#4d6075}}
    </style></head><body><h1>EFTX · Tilt elétrico</h1><p>{escape(title)}</p>
    <h2>Entradas e hipóteses</h2><table>{inputs}</table>
    <h2>Resultados</h2><p>ΔL por nível: <b>{fmt(result.delta_length_m*1000, 4)} mm</b> ·
    Avanço de fase por nível: <b>{fmt(result.phase_step_deg, 4)}°</b><br>
    λ livre: {fmt(result.wavelength_m*1000)} mm · λ na linha: {fmt(result.guided_wavelength_m*1000)} mm<br>
    Eficiência de alimentação: {fmt(result.feed_efficiency*100 if result.feed_efficiency is not None else None)}% ·
    Coerência no alvo: {fmt(result.coherence_efficiency*100)}%<br>
    Potência entregue: {fmt(result.total_power_w)} W · Perda equivalente: {fmt(result.equivalent_loss_db)} dB</p>
    <h2>Comprimentos entre planos de referência</h2>
    <p>E1 é o elemento inferior. Tilt positivo aponta para baixo. Fase positiva = avanço em relação a E1.</p>
    <table><thead><tr><th>Elemento</th><th>z (m)</th><th>Ideal (mm)</th><th>Corte (mm)</th>
    <th>Fase (°)</th><th>Erro (°)</th><th>Perda (dB)</th><th>W</th></tr></thead><tbody>{rows}</tbody></table>
    <h2>Memória de cálculo</h2><p>λ₀ = c/f; λg = VF × λ₀; Δφ = 360° × d/λ₀ × sen(θ); ΔL = VF × d × sen(θ).<br>
    Lᵢ = Lmin + max(j × ΔL) − i × ΔL, para i,j = 0…N−1. Corte arredondado ao passo informado.<br>
    Aᵢ = α × (Lcomum + Lᵢ)/100 + Aextra; Pᵢ = Pin/N × 10^(−Aᵢ/10).<br>
    ηalimentação = ΣPᵢ/Pin. ηcoerência = |Σ aᵢ exp(jεᵢ)|² / (N × Σ aᵢ²), no tilt solicitado.</p>
    <ul>{warnings}</ul><p class="note">Modelo de alimentação paralela com divisão igual e linha comum do mesmo modelo.
    Eficiência de alimentação não inclui rendimento de radiação, descasamento/ROE ou acoplamento mútuo.
    O fator de arranjo não substitui o diagrama medido do elemento. Comprimentos não incluem correções
    de conectores e descontinuidades; conferir percurso físico e fase em bancada.</p>
    <p class="note">Referências: planilhas de tilt fornecidas; catálogo CableRating.xml do ADT-PY;
    interpolação log-log dentro da faixa de cada modelo, sem extrapolação.</p></body></html>'''


def export_json(path, payload):
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
