from dataclasses import replace
import math

import pytest

from tilt.engineering import C_SI, Design, array_pattern, calculate, channel_frequency, parse_decimal
from tilt.engineering import wavelength_m, vertical_patterns


def test_cable_workbook_golden():
    # XLS Plan1 D5, D7, D9, D11; cached D15, D17, D22, D24 (read-only extraction).
    result = calculate(Design(frequency_mhz=623, elements=2, spacing_m=1.96, tilt_deg=2,
                              velocity_factor=.88, shortest_branch_m=.9698053480875263, cut_step_mm=0))
    assert result.wavelength_m*1000 == pytest.approx(481.54093097913324, abs=1e-9)
    assert result.phase_step_deg == pytest.approx(51.13809292018786, abs=1e-10)
    assert result.delta_length_m*1000 == pytest.approx(60.194651912473674, abs=1e-9)
    assert result.elements[0].length_m == pytest.approx(1.03, abs=1e-12)
    assert result.elements[1].length_m*1000 == pytest.approx(969.8053480875263, abs=1e-9)


def test_rigid_workbook_golden():
    result = calculate(Design(frequency_mhz=107.7, elements=2, spacing_m=2.7715877437325903,
                              tilt_deg=5, velocity_factor=.995, cut_step_mm=0))
    assert result.guided_wavelength_m*1000 == pytest.approx(2771.5877437325903, abs=1e-9)
    assert result.phase_step_deg == pytest.approx(31.219187052211154, abs=1e-10)
    assert result.delta_length_m*1000 == pytest.approx(240.35198945334338, abs=1e-9)


@pytest.mark.parametrize('tilt', [-20, -2, 0, 2, 20])
def test_independent_array_peak_and_length_sign(tilt):
    result = calculate(Design(frequency_mhz=600, elements=8, spacing_m=.25,
                              tilt_deg=tilt, cut_step_mm=0, attenuation_db_100m=2))
    angles, levels = array_pattern(result)
    peak = angles[max(range(len(levels)), key=levels.__getitem__)]
    assert peak == pytest.approx(-tilt, abs=.051)
    assert result.fitted_tilt_deg == pytest.approx(tilt, abs=1e-10)
    assert math.copysign(1, result.elements[0].length_m-result.elements[-1].length_m) == math.copysign(1, tilt)


def test_known_power_budget_and_no_double_count_of_splitter():
    result = calculate(Design(elements=4, tilt_deg=0, shortest_branch_m=10, common_feeder_m=90,
                              attenuation_db_100m=3, extra_loss_db=1, input_power_w=1000))
    expected = 10**(-4/10)
    assert result.feed_efficiency == pytest.approx(expected)
    assert result.total_power_w == pytest.approx(1000*expected)
    assert result.equivalent_loss_db == pytest.approx(4)
    assert all(e.power_w == pytest.approx(250*expected) for e in result.elements)
    assert result.coherence_efficiency == pytest.approx(1)


def test_missing_loss_is_not_zero_loss():
    unknown = calculate(Design(attenuation_db_100m=None))
    lossless = calculate(Design(attenuation_db_100m=0))
    assert unknown.feed_efficiency is None
    assert unknown.total_power_w is None
    assert all(e.power_w is None for e in unknown.elements)
    assert lossless.feed_efficiency == pytest.approx(1)


def test_extreme_loss_does_not_corrupt_coherence_or_known_loss():
    result = calculate(Design(tilt_deg=0, attenuation_db_100m=1000, common_feeder_m=1000))
    assert result.feed_efficiency == 0
    assert result.coherence_efficiency == pytest.approx(1)
    assert result.equivalent_loss_db == pytest.approx(10030)


def test_rounding_error_and_coherence_are_real():
    base = Design(frequency_mhz=600, spacing_m=.25, tilt_deg=1, elements=8,
                  attenuation_db_100m=0, cut_step_mm=10)
    coarse = calculate(base)
    ideal = calculate(replace(base, cut_step_mm=0))
    assert coarse.coherence_efficiency < ideal.coherence_efficiency
    assert any(abs(e.phase_error_deg) > 1 for e in coarse.elements)
    assert ideal.coherence_efficiency == pytest.approx(1)


def test_frequency_and_c_do_not_change_length_difference():
    a = calculate(Design())
    b = calculate(replace(a.design, frequency_mhz=1000, speed_m_s=C_SI))
    assert a.delta_length_m == b.delta_length_m
    assert a.phase_step_deg != b.phase_step_deg


def test_grating_lobes_are_reported():
    safe = calculate(Design(frequency_mhz=600, spacing_m=.25))
    aliased = calculate(Design(frequency_mhz=600, spacing_m=1))
    assert not safe.grating_angles_deg
    assert len(aliased.grating_angles_deg) >= 2
    assert any('grade' in warning for warning in aliased.warnings)


@pytest.mark.parametrize('key,value', [
    ('frequency_mhz', 0), ('frequency_mhz', float('nan')), ('spacing_m', -1),
    ('velocity_factor', 0), ('velocity_factor', 1.01), ('tilt_deg', 90),
    ('elements', 1), ('elements', 65), ('elements', 2.5), ('elements', True),
    ('shortest_branch_m', -1), ('common_feeder_m', -1), ('attenuation_db_100m', -1),
    ('extra_loss_db', -1), ('input_power_w', 0), ('cut_step_mm', -1), ('speed_m_s', 299e6),
])
def test_invalid_physical_inputs_fail_closed(key, value):
    with pytest.raises(ValueError):
        calculate(replace(Design(), **{key: value}))


@pytest.mark.parametrize('value', ['', 'NaN', 'inf', '1.000,5', '1,000.5', '1 000', 'text'])
def test_invalid_localized_numbers(value):
    with pytest.raises(ValueError):
        parse_decimal(value)


def test_comma_dot_and_signed_inputs():
    assert parse_decimal(' -2,5 ') == -2.5
    assert parse_decimal('623.142857') == 623.142857


@pytest.mark.parametrize('channel,frequency', [(2,57),(4,69),(5,79),(6,85),(7,177),(13,213),(14,473),(39,623),(51,695),(69,803)])
def test_channel_boundaries(channel, frequency):
    assert channel_frequency(channel) == frequency


@pytest.mark.parametrize('channel', [1,70,2.5,True])
def test_invalid_channels(channel):
    with pytest.raises(ValueError):
        channel_frequency(channel)


def test_wavelength_is_not_scaled_by_cable_velocity_factor():
    assert wavelength_m(600) == .5
    assert wavelength_m(600, C_SI) == pytest.approx(.4996540966666667)
    result = calculate(Design(frequency_mhz=600, spacing_m=wavelength_m(600), velocity_factor=.66))
    assert result.guided_wavelength_m == .33
    assert result.design.spacing_m == .5


@pytest.mark.parametrize('frequency', [0, -1, float('nan'), float('inf'), True])
def test_wavelength_rejects_invalid_frequency(frequency):
    with pytest.raises(ValueError):
        wavelength_m(frequency)


def test_pattern_matches_closed_form_uniform_array_and_accepts_generators():
    d = Design(frequency_mhz=600, spacing_m=.25, elements=8, tilt_deg=5, cut_step_mm=0, attenuation_db_100m=0)
    r = calculate(d)
    angles = [-30., -12.4, -5., 0., 8.1, 23.7]
    actual_angles, actual = array_pattern(r, iter(angles))
    assert actual_angles == angles
    for angle, field_db in zip(angles, actual):
        psi = 2*math.pi*d.spacing_m/.5*(math.sin(math.radians(angle))+math.sin(math.radians(d.tilt_deg)))
        ratio = abs(math.sin(d.elements*psi/2)/(d.elements*math.sin(psi/2))) if abs(psi) > 1e-12 else 1
        expected = 20*math.log10(max(ratio, .001))
        assert field_db == pytest.approx(expected, abs=1e-10)


def test_viewport_sampling_preserves_reference_and_cut_effects():
    r = calculate(Design(frequency_mhz=600, spacing_m=.25, elements=8, tilt_deg=2.1234, cut_step_mm=20))
    narrow = vertical_patterns(r, -3, 3)
    assert -r.design.tilt_deg in narrow.angles
    assert min(narrow.angles) == -3
    assert max(narrow.angles) == 3
    assert list(narrow.actual_db) == array_pattern(r, narrow.angles)[1]
    assert max(abs(a-b) for a,b in zip(narrow.actual_db, narrow.ideal_db)) > .01
    assert all(-60 <= value <= 0 for value in narrow.actual_db)


def test_extreme_aperture_sampling_is_bounded_and_disclosed():
    r = calculate(Design(frequency_mhz=1000, spacing_m=100, elements=2))
    full = vertical_patterns(r)
    assert full.sampling_limited
    assert len(full.angles) <= 12003
    focused = vertical_patterns(r, -2.01, -1.99)
    assert not focused.sampling_limited


@pytest.mark.parametrize('start,stop', [(1,1),(1,-1),(-91,0),(0,91),(float('nan'),1)])
def test_invalid_plot_range_is_rejected(start, stop):
    with pytest.raises(ValueError):
        vertical_patterns(calculate(Design()), start, stop)
