from dataclasses import asdict, replace
import cmath
import json
import math
from pathlib import Path

import pytest

from tilt.engineering import Design, calculate, array_pattern, wavelength_m
from tilt.reports import export_csv, snapshot, report_html

REFERENCE = json.loads((Path(__file__).parent/'fixtures/fm_center_reference.json').read_text(encoding='utf-8'))


def central(**changes):
    return replace(Design(frequency_mhz=105.3, velocity_factor=.87, elements=6,
                          spacing_m=300/105.3, tilt_deg=0, cut_step_mm=0,
                          attenuation_db_100m=0, feed_layout='center', length_reference='shield_edges'), **changes)


@pytest.mark.parametrize('case', REFERENCE['cases'])
def test_center_lengths_match_original_ods_cached_results(case):
    result = calculate(central(elements=case['elements']))
    assert result.guided_wavelength_m*1000 == pytest.approx(REFERENCE['guided_mm'], abs=1e-9)
    assert [e.length_m*1000 for e in result.elements] == pytest.approx(case['mm'], abs=1e-8)
    assert all(b.added_wavelengths == 0 for b in result.center_feed.branches)
    assert result.coherence_efficiency == pytest.approx(1, abs=1e-12)


@pytest.mark.parametrize('count', [2, 3, 4, 5, 6, 12, 64])
@pytest.mark.parametrize('tilt', [-7, 0, 5])
def test_physical_cable_phasors_align_at_requested_tilt(count, tilt):
    # Independently propagate over actual cable and free-space paths. No use of
    # the implementation's stored relative phases or its regression fit.
    result = calculate(central(elements=count, tilt_deg=tilt, route_extra_m=.7))
    d = result.design
    phase = [cmath.exp(-2j*math.pi*(e.length_m/result.guided_wavelength_m
                                  + e.height_m/result.wavelength_m*math.sin(math.radians(tilt))))
             for e in result.elements]
    assert abs(sum(phase))/count == pytest.approx(1, abs=1e-11)
    assert result.fitted_tilt_deg == pytest.approx(tilt, abs=1e-9)
    assert array_pattern(result, [-tilt])[1][0] == pytest.approx(0, abs=1e-10)
    assert all(e.length_m >= b.minimum_route_m-1e-10 for e, b in zip(result.elements, result.center_feed.branches))


def test_odd_count_and_reach_extensions_preserve_symmetry_and_quarter_phase():
    result = calculate(central(elements=5, spacing_m=5, route_extra_m=2, reserve_wavelengths=2))
    lengths = [e.length_m for e in result.elements]
    assert lengths == pytest.approx(lengths[::-1], abs=1e-12)
    assert result.center_feed.branches[2].base_wavelengths == .25
    assert any(b.added_wavelengths > 2 for b in result.center_feed.branches)
    for length in lengths:
        assert (length/result.guided_wavelength_m)%1 == pytest.approx(.25, abs=1e-12)


def test_reserve_changes_losses_but_not_phase():
    design = central(tilt_deg=3, attenuation_db_100m=4)
    a, b = calculate(design), calculate(replace(design, reserve_wavelengths=2))
    assert [y.length_m-x.length_m for x, y in zip(a.elements, b.elements)] == pytest.approx([2*a.guided_wavelength_m]*6)
    assert [e.relative_phase_deg for e in a.elements] == pytest.approx([e.relative_phase_deg for e in b.elements], abs=1e-9)
    assert b.feed_efficiency < a.feed_efficiency
    assert a.elements[0].power_w < a.elements[2].power_w
    assert b.total_power_w/a.total_power_w == pytest.approx(10**(-4*(2*a.guided_wavelength_m)/1000))


def test_cut_rounding_never_shortens_below_required_route():
    result = calculate(central(frequency_mhz=3000, elements=3, spacing_m=.13,
                               route_extra_m=.1001, tilt_deg=1, cut_step_mm=100))
    for e, b in zip(result.elements, result.center_feed.branches):
        assert e.length_m >= b.minimum_route_m
        assert e.ideal_length_m >= b.minimum_route_m-1e-10
        assert e.length_m/.1 == pytest.approx(round(e.length_m/.1))


@pytest.mark.parametrize('changes', [{'feed_layout':'x'}, {'route_extra_m':-1}, {'route_extra_m':float('nan')},
                                     {'reserve_wavelengths':.5}, {'reserve_wavelengths':True}, {'reserve_wavelengths':101},
                                     {'velocity_factor':1e-200}])
def test_invalid_center_inputs_fail_explicitly(changes):
    with pytest.raises(ValueError):
        calculate(central(**changes))


def test_spacing_multiplier_tilt_and_saved_center_plan(window, tmp_path):
    window.load_central_example()
    assert window.result.design.feed_layout == 'center'
    assert window.result.design.velocity_factor == .87
    assert not window.apply_tilt.isChecked()
    assert window.central_table.rowCount() == 6
    assert window.result_tabs.isTabVisible(window.central_tab_index)
    assert 'mesma fase' in window.answer.text()
    window.spacing_factor.setValue(.75)
    assert window.result is None
    assert window.number('spacing_mm') == pytest.approx(.75*wavelength_m(105.3)*1000, abs=1e-8)
    window.apply_tilt.setChecked(True)
    window.fields['tilt_deg'].setText('2,5')
    window.fields['route_extra_m'].setText('0,4')
    window.reserve_wavelengths.setValue(1)
    assert window.run_calculation()
    expected = asdict(window.result)
    window.save_project()
    record = window.db.project(window.db.projects()[0]['id'])
    assert record['payload']['schema_version'] == 2
    assert record['snapshot']['schema_version'] == 3
    assert record['snapshot']['result']['center_feed']['divider_height_m'] == window.result.center_feed.divider_height_m
    assert record['snapshot']['result']['center_feed']['branches'][0]['added_wavelengths'] == window.result.center_feed.branches[0].added_wavelengths
    window.load_example('cable')
    window.restore_payload(record['payload'], record['title'])
    assert window.spacing_factor.value() == .75
    assert window.run_calculation()
    assert asdict(window.result) == expected
    csv = tmp_path/'center.csv'
    export_csv(csv, window.result, 'Personalizado')
    assert 'Lambda_g adicionados' in csv.read_text(encoding='utf-8-sig')
    assert 'Divisor central e dimensionamento' in report_html(window.result, 'Personalizado', 'Teste')


def test_no_tilt_ignores_disabled_angle_and_legacy_revision_keeps_old_algorithm(window):
    window.load_central_example()
    window.fields['tilt_deg'].setText('9')
    assert window.run_calculation()
    assert window.result.design.tilt_deg == 0
    window.load_example('cable')
    legacy = dict(window.calculated_payload)
    legacy['schema_version'] = 1
    legacy['design'] = dict(legacy['design'])
    for field in ('feed_layout','route_extra_m','reserve_wavelengths'):
        legacy['design'].pop(field)
    legacy.pop('spacing_factor')
    old_lengths = [e.length_m for e in window.result.elements]
    window.load_central_example()
    window.restore_payload(legacy, 'Revisão 1.3')
    assert window.run_calculation()
    assert window.result.center_feed is None
    assert [e.length_m for e in window.result.elements] == old_lengths


def test_center_pdf_has_fabrication_formula_and_reach(window, tmp_path):
    from tilt.printing import load_pdf
    window.load_central_example()
    path = window.write_pdf(tmp_path/'central.pdf')
    doc = load_pdf(path)
    try:
        text = ' '.join(' '.join(doc.getAllText(i).text() for i in range(doc.pageCount())).split())
        for phrase in ('Divisor central', 'Percurso mínimo', 'Correção tilt', 'λg adicionados',
                       '8055,556', '5576,923', '3098,291', 'malha', 'E6', 'Calculo de cabos para antena fm.ods'):
            assert phrase in text
    finally:
        doc.close()
