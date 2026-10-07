"""Traceable CSV and printable HTML; values use the last explicitly calculated design."""
import csv
from dataclasses import asdict
from html import escape
import json
from pathlib import Path

from .engineering import ENGINE_VERSION, ELEMENT_PATTERNS, LENGTH_REFERENCES, Result
from . import __version__


def fmt(value, digits=3):
    return 'n/d' if value is None else f'{value:.{digits}f}'.replace('.', ',')


def snapshot(result: Result, model: str, catalog_hash: str, view_range=(-90.0, 90.0)):
    return {'schema_version': 2, 'engine_version': ENGINE_VERSION, 'model': model,
            'catalog_sha256': catalog_hash, 'result': asdict(result),
            'fabrication': {
                'reference': result.design.length_reference,
                'reference_description': LENGTH_REFERENCES[result.design.length_reference],
                'termination_assumption': 'Atrasos iguais nas terminações; pontas expostas e conectores excluídos da medida de blindagem.',
                'units': 'mm',
                'rows': [{'element': e.number, 'ideal_mm': e.ideal_length_m*1000, 'finished_mm': e.length_m*1000,
                          'delta_previous_mm': e.delta_previous_m*1000 if e.delta_previous_m is not None else None,
                          'delta_e1_mm': e.delta_e1_m*1000} for e in result.elements]},
            'diagram': {'element_pattern': result.design.element_pattern,
                        'description': ELEMENT_PATTERNS[result.design.element_pattern],
                        'origin': 'analytical', 'elevation_range_deg': list(view_range),
                        'normalization': 'field / coherent amplitude sum; element maximum = 1',
                        'display_floor_db': -60}}


def export_csv(path: Path, result: Result, model: str):
    d = result.design
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream, delimiter=';')
        writer.writerow(['EFTX Tilt', __version__])
        writer.writerow(['Modelo', model])
        if result.line_specification:
            for key, value in asdict(result.line_specification).items():
                writer.writerow(['material.'+key, json.dumps(value, ensure_ascii=False)])
        for key, value in asdict(d).items():
            writer.writerow([key, '' if value is None else str(value).replace('.', ',')])
        writer.writerow(['feed_efficiency_percent', fmt(result.feed_efficiency*100 if result.feed_efficiency is not None else None)])
        writer.writerow(['coherence_efficiency_percent', fmt(result.coherence_efficiency*100)])
        writer.writerow(['Convenção', 'E1 inferior; tilt positivo para baixo; fase relativa a E1'])
        writer.writerow(['Elemento', 'Altura (m)', 'Comprimento ideal (mm)', 'Comprimento de corte (mm)',
                         'Fase relativa (graus)', 'Erro de fase (graus)', 'Perda total (dB)', 'Potência (W)',
                         'Diferença anterior (mm)', 'Diferença E1 (mm)'])
        for e in result.elements:
            writer.writerow([f'E{e.number}', fmt(e.height_m, 6), fmt(e.ideal_length_m*1000, 6),
                             fmt(e.length_m*1000, 6), fmt(e.relative_phase_deg, 6),
                             fmt(e.phase_error_deg, 6), fmt(e.loss_db, 6), fmt(e.power_w, 6),
                             fmt(e.delta_previous_m*1000 if e.delta_previous_m is not None else None, 6), fmt(e.delta_e1_m*1000, 6)])
        for warning in result.warnings:
            writer.writerow(['Observação', warning])
        writer.writerow(['Limite do modelo', 'Divisão igual, elementos idênticos; sem acoplamento, ROE ou rendimento de radiação.'])


def material_html(result):
    s = result.line_specification
    if s is None:
        return '<h2>Material e capacidade de potência</h2><p>Potência máxima: n/d. Sem especificação de catálogo neste cálculo.</p>'
    values = [
        ('Modelo / frequência', f'{s.model} / {fmt(s.frequency_mhz)} MHz'),
        ('Impedância / VF do catálogo', f'{fmt(s.impedance_ohm, 1)} Ω / {fmt(s.catalog_velocity_factor, 6)}'),
        ('Potência média máxima de catálogo', f'{fmt(s.average_power_w)} W por trecho'),
        ('Potência de pico de catálogo (não é potência média)', f'{fmt(s.peak_power_w)} W'),
        ('Tensão de pico de catálogo', f'{fmt(s.peak_voltage_v)} V'),
        ('Entrada de cada ramal / margem média', f'{fmt(s.branch_input_w)} W / {fmt(s.branch_margin_w)} W'),
        ('Entrada da linha comum / margem média', f'{fmt(s.common_input_w)} W / {fmt(s.common_margin_w)} W' if s.common_input_w is not None else 'Não há linha comum'),
        ('Limite médio na entrada do conjunto (só os cabos)', f'{fmt(s.source_average_limit_w)} W'),
        ('Verificação de potência média', s.status),
        ('Método / fonte', s.interpolation+' / '+s.source),
    ]
    rows = ''.join(f'<tr><td>{escape(k)}</td><td>{escape(v)}</td></tr>' for k, v in values)
    samples = ''.join(f'<tr><td>{fmt(f)}</td><td>{fmt(a, 6)}</td><td>{fmt(p*1000)}</td></tr>' for f, a, p in s.supporting_samples)
    return ('<h2>Material e capacidade de potência</h2><table>'+rows+'</table>'
            '<p>Margem = limite de catálogo menos potência de entrada do trecho; negativa significa excesso. '
            'A verificação considera perda na linha comum, divisão igual e não desconta perdas adicionais de localização desconhecida.</p>'
            '<p>'+escape(s.conditions)+'</p>'
            '<h3>Amostras usadas na frequência informada</h3><table><thead><tr><th>MHz</th><th>dB/100 m</th><th>Potência média (W)</th></tr></thead><tbody>'
            +samples+'</tbody></table><p class="note">Unidades originais do XML: Avpower e PeakPower em kW; '
            'AttenuationdBm em dB/100 m. As amostras e valores calculados são preservados na revisão SQLite.</p>')


def report_html(result: Result, model: str, title: str):
    d = result.design
    rows = ''.join('<tr>' + ''.join(f'<td>{escape(str(x))}</td>' for x in [
        f'E{e.number}', fmt(e.height_m), fmt(e.ideal_length_m*1000), fmt(e.length_m*1000),
        fmt(e.relative_phase_deg), fmt(e.phase_error_deg), fmt(e.loss_db), fmt(e.power_w)]) + '</tr>'
        for e in result.elements)
    fabrication = ''.join('<tr>'+''.join(f'<td>{escape(v)}</td>' for v in [
        f'E{e.number}', fmt(e.ideal_length_m*1000), fmt(e.length_m*1000),
        fmt(e.delta_previous_m*1000 if e.delta_previous_m is not None else None), fmt(e.delta_e1_m*1000)])+'</tr>' for e in result.elements)
    inputs = ''.join(f'<tr><td>{escape(key)}</td><td>{escape(str(value))}</td></tr>' for key, value in [
        ('Frequência', f'{fmt(d.frequency_mhz)} MHz'), ('Modelo', model),
        ('Quantidade de elementos', d.elements), ('Espaçamento', f'{fmt(d.spacing_m*1000)} mm'),
        ('Tilt solicitado (positivo para baixo)', f'{fmt(d.tilt_deg)}°'),
        ('Diagrama de cada antena', ELEMENT_PATTERNS[d.element_pattern]),
        ('Fator de velocidade', fmt(d.velocity_factor, 6)), ('Atenuação', f'{fmt(d.attenuation_db_100m)} dB/100 m'),
        ('Ramal mais curto', f'{fmt(d.shortest_branch_m)} m'), ('Linha comum', f'{fmt(d.common_feeder_m)} m'),
        ('Perdas adicionais totais', f'{fmt(d.extra_loss_db)} dB'), ('Potência na entrada', f'{fmt(d.input_power_w)} W'),
        ('Passo de corte', f'{fmt(d.cut_step_mm)} mm'), ('Velocidade c', f'{d.speed_m_s:g} m/s')])
    warnings = ''.join(f'<li>{escape(w)}</li>' for w in result.warnings)
    reference_note = ('Medir ao longo do eixo do cabo, entre as extremidades da blindagem; na linha rígida, do condutor externo. '
                      'Pontas expostas do condutor central e conectores não fazem parte desta medida.'
                      if d.length_reference == 'shield_edges' else
                      'Revisão com planos elétricos de referência: não interpretar como medida física de malha a malha sem conferir as terminações.')
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
    Potência entregue: {fmt(result.total_power_w)} W · Perda equivalente: {fmt(result.equivalent_loss_db)} dB<br>
    Espaçamento / λ livre: {fmt(d.spacing_m/result.wavelength_m, 6)} ·
    Atraso diferencial: {fmt(result.delay_step_ns, 6)} ns<br>
    Tilt da progressão após corte: {fmt(result.fitted_tilt_deg, 6)}° ·
    Erro máximo de fase após corte: {fmt(max(abs(e.phase_error_deg) for e in result.elements), 6)}°</p>
    {material_html(result)}
    <h2>Comprimentos entre planos de referência</h2>
    <p><b>{escape(LENGTH_REFERENCES[d.length_reference])}</b>.
    {reference_note}
    Os atrasos das terminações são considerados iguais em todos os ramais; diferenças exigem compensação medida.</p>
    <p>Diferença anterior = L(Ei) − L(Ei−1). Diferença E1 = L(Ei) − L(E1).
    Valores negativos indicam trechos mais curtos. Diferenças calculadas <b>após</b> o arredondamento ao passo de corte.</p>
    <table><thead><tr><th>Antena</th><th>Ideal (mm)</th><th>Medida final (mm)</th>
    <th>Dif. anterior (mm)</th><th>Dif. E1 (mm)</th></tr></thead><tbody>{fabrication}</tbody></table>
    <h3>Fase, perdas e potência em cada antena</h3>
    <p>E1 é o elemento inferior. Tilt positivo aponta para baixo. Fase positiva = avanço em relação a E1.</p>
    <table><thead><tr><th>Elemento</th><th>z (m)</th><th>Ideal (mm)</th><th>Corte (mm)</th>
    <th>Fase (°)</th><th>Erro (°)</th><th>Perda (dB)</th><th>W</th></tr></thead><tbody>{rows}</tbody></table>
    <h2>Memória de cálculo</h2><p>λ₀ = c/f; λg = VF × λ₀; Δφ = 360° × d/λ₀ × sen(θ); ΔL = VF × d × sen(θ).<br>
    Lᵢ = Lmin + max(j × ΔL) − i × ΔL, para i,j = 0…N−1. Corte arredondado ao passo informado.<br>
    Aᵢ = α × (Lcomum + Lᵢ)/100 + Aextra; Pᵢ = Pin/N × 10^(−Aᵢ/10).<br>
    ηalimentação = ΣPᵢ/Pin. ηcoerência = |Σ aᵢ exp(jεᵢ)|² / (N × Σ aᵢ²), no tilt solicitado.</p>
    <p><b>Diagrama: {escape(ELEMENT_PATTERNS[d.element_pattern])}.</b><br>
    Campo total = F_elemento(e) × |Σ aᵢ exp[j(2πzᵢ/λ₀ × sen(e) + φᵢ)]| / Σaᵢ.<br>
    Para dipolo vertical de meia onda: F_elemento(e) = cos[(π/2) sen(e)] / cos(e),
    com limite zero em e = ±90°. Para isotrópico: F_elemento = 1.
    Elevação e = 0° no horizonte; −90° para baixo; +90° para cima.
    Campo em dB = 20 log₁₀(campo relativo); piso visual −60 dB. A normalização não muda com o zoom.
    O tilt da progressão não é uma medição da direção de pico do diagrama completo.</p>
    <ul>{warnings}</ul><p class="note">Modelo de alimentação paralela com divisão igual e linha comum do mesmo modelo.
    Eficiência de alimentação não inclui rendimento de radiação, descasamento/ROE ou acoplamento mútuo.
    O fator de arranjo não substitui o diagrama medido do elemento. Comprimentos não incluem correções
    de conectores e descontinuidades; conferir percurso físico e fase em bancada.</p>
    <p class="note">Referências: planilhas de tilt fornecidas; catálogo CableRating.xml do ADT-PY;
    interpolação log-log dentro da faixa de cada modelo, sem extrapolação.</p></body></html>'''


def export_json(path, payload):
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
