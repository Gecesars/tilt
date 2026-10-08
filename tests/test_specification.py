from dataclasses import asdict, replace
import math

import pytest

from tilt.engineering import Design, calculate, array_pattern, radiation_pattern, element_field, vertical_patterns
from tilt.reports import fmt, snapshot, export_csv
from tilt.specification import line_specification
from tilt.storage import Database


def test_full_pattern_corrects_axial_lobes_by_element_multiplication_not_clipping():
    r = calculate(Design(frequency_mhz=600, spacing_m=.5, tilt_deg=0, cut_step_mm=0,
                         element_pattern='half_wave_vertical'))
    angles = [-90, -75, -30, 0, 30, 75, 90]
    _, af = array_pattern(r, angles)
    _, total = radiation_pattern(r, angles)
    assert af[0] == pytest.approx(0, abs=1e-12)
    assert af[-1] == pytest.approx(0, abs=1e-12)
    assert total[0] == total[-1] == -60
    assert total[3] == pytest.approx(0, abs=1e-12)
    for angle, factor_db, full_db in zip(angles[1:-1], af[1:-1], total[1:-1]):
        e = math.radians(angle)
        independent = abs(math.cos(math.pi/2*math.sin(e))/math.cos(e))
        assert full_db == pytest.approx(max(-60, factor_db+20*math.log10(independent)), abs=1e-10)


def test_half_wave_dipole_reference_beamwidth_and_stable_null_limits():
    assert element_field(0, 'half_wave_vertical') == 1
    # Half-wave dipole has approximately 78 degree half-power beamwidth.
    assert 20*math.log10(element_field(39, 'half_wave_vertical')) == pytest.approx(-3, abs=.06)
    assert element_field(89.999999, 'half_wave_vertical') < 1e-7
    assert element_field(-89.999999, 'half_wave_vertical') == element_field(89.999999, 'half_wave_vertical')
    r = calculate(Design(frequency_mhz=600, spacing_m=.5, tilt_deg=2, element_pattern='half_wave_vertical'))
    # Suppression of the axial maximum must not erase other physical lobes.
    assert max(radiation_pattern(r, range(40, 80))[1]) > -20


@pytest.mark.parametrize('tilt', [-5, 0, 5])
def test_element_pattern_preserves_cuts_and_viewport_normalization(tilt):
    bare = calculate(Design(tilt_deg=tilt))
    full = calculate(replace(bare.design, element_pattern='half_wave_vertical'))
    assert bare.elements == full.elements
    data = vertical_patterns(full, -12, 12)
    assert list(data.actual_db) == radiation_pattern(full, data.angles)[1]
    assert list(vertical_patterns(full, -12, 12, factor_only=True).actual_db) == array_pattern(bare, data.angles)[1]


@pytest.mark.parametrize('tilt', [-3, 0, 3])
def test_fabrication_differences_are_actual_rounded_lengths(tilt):
    r = calculate(Design(elements=8, tilt_deg=tilt, cut_step_mm=5, length_reference='shield_edges'))
    assert r.elements[0].delta_previous_m is None
    for previous, e in zip(r.elements, r.elements[1:]):
        assert e.delta_previous_m == e.length_m-previous.length_m
        assert e.delta_e1_m == e.length_m-r.elements[0].length_m
    assert sum(e.delta_previous_m for e in r.elements[1:]) == pytest.approx(r.elements[-1].delta_e1_m)


def test_rating_exact_interpolated_limits_and_unknown_model():
    db = Database(':memory:')
    try:
        c = db.cable('LCF12-50')
        assert c.at(600)[1] == 1.55
        assert c.at(700)[1] == 1.43
        a, b = c.samples[8:10]
        f = math.sqrt(a[0]*b[0])
        r = calculate(Design(frequency_mhz=f, attenuation_db_100m=c.at(f)[0]))
        s = line_specification(r, c, c.name, c.kind, db.catalog_hash)
        assert s.average_power_w == pytest.approx(math.sqrt(a[2]*b[2])*1000)
        assert s.supporting_samples == (a, b)
        assert s.peak_power_w == c.peak_power_kw*1000
        assert s.branch_input_w == 250
        assert s.source_average_limit_w == s.average_power_w*4
        exact = replace(r, design=replace(r.design, frequency_mhz=a[0]))
        assert line_specification(exact, c, c.name, c.kind, db.catalog_hash).supporting_samples == (a,)
        unknown = line_specification(r, None, 'Personalizado', 'cable', db.catalog_hash)
        assert unknown.average_power_w is None and unknown.status == 'indisponível'
    finally:
        db.close()


def test_common_feeder_overload_detected_even_when_branches_are_under_rating(window):
    c = window.db.cable('LCF12-50')
    alpha, kw = c.at(623)
    r = calculate(Design(input_power_w=kw*1000*1.5, common_feeder_m=10,
                         attenuation_db_100m=alpha, extra_loss_db=30))
    s = line_specification(r, c, c.name, c.kind, window.db.catalog_hash)
    assert s.branch_input_w == pytest.approx(r.design.input_power_w/4*10**(-alpha*10/1000))
    assert s.branch_margin_w > 0 and s.common_margin_w < 0
    assert s.status == 'excede referência'
    assert s.source_average_limit_w == kw*1000


def test_saved_revision_contains_fabrication_ratings_samples_and_diagram(window, tmp_path):
    window.diagrams.set_range(-20, 15)
    r = window.result
    window.save_project()
    record = window.db.project(window.db.projects()[0]['id'])
    saved = record['snapshot']
    assert saved['schema_version'] == 3
    assert saved['result']['line_specification']['average_power_w'] == r.line_specification.average_power_w
    assert saved['fabrication']['rows'][-1]['delta_e1_mm'] == r.elements[-1].delta_e1_m*1000
    assert saved['diagram']['element_pattern'] == 'half_wave_vertical'
    assert saved['diagram']['elevation_range_deg'] == [-20, 15]
    # Current catalog mutation cannot alter an already calculated/saved rating.
    window.db.connection.execute('UPDATE samples SET average_power_kw=999 WHERE cable_name=?', ('LCF12-50',))
    assert snapshot(r, 'LCF12-50', window.db.catalog_hash)['result']['line_specification'] == asdict(r.line_specification)
    assert window.db.project(record['id'])['snapshot'] == saved
    path = tmp_path/'cuts.csv'
    export_csv(path, r, 'LCF12-50')
    csv = path.read_text(encoding='utf-8-sig')
    assert 'material.average_power_w' in csv and 'Diferença anterior (mm)' in csv
    for row, e in enumerate(r.elements):
        assert window.simple_table.item(row, 3).text() == fmt(e.delta_e1_m*1000)


def test_legacy_project_preserves_original_model_until_user_selects_new_one(window):
    payload = dict(window.calculated_payload)
    payload['design'] = dict(payload['design'])
    del payload['design']['element_pattern']
    del payload['design']['length_reference']
    window.restore_payload(payload, 'Legado')
    assert window.element_pattern.currentData() == 'isotropic'
    assert window.length_reference.currentData() == 'electrical_planes'
    assert window.run_calculation()
    window.element_pattern.setCurrentIndex(window.element_pattern.findData('half_wave_vertical'))
    assert window.result is None and not window.save_button.isEnabled()


def test_open_saved_revision_restores_angular_range(window):
    window.diagrams.set_range(-11, 9)
    window.save_project()
    window.diagrams.set_range(-90, 90)
    window.project_table.selectRow(0)
    window.open_project()
    assert window.diagrams.view_range == (-11, 9)
    assert window.element_pattern.currentData() == 'half_wave_vertical'
    assert window.length_reference.currentData() == 'shield_edges'


@pytest.mark.parametrize('field,value', [('element_pattern', 'unknown'), ('length_reference', 'unknown')])
def test_unsupported_physical_models_are_rejected(field, value):
    with pytest.raises(ValueError):
        calculate(replace(Design(), **{field: value}))
