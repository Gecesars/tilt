import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from dataclasses import asdict
import json

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from tilt.storage import Database
from tilt.window import CUSTOM, MainWindow
from tilt.reports import export_csv, export_json, report_html, snapshot
from tilt.reports import fmt


@pytest.fixture(scope='session')
def app():
    app = QApplication.instance() or QApplication([])
    if not QFontDatabase.families() and os.name == 'nt':
        QFontDatabase.addApplicationFont(os.path.join(os.environ.get('WINDIR', 'C:/Windows'), 'Fonts', 'segoeui.ttf'))
    return app


@pytest.fixture
def window(app):
    db = Database(':memory:')
    widget = MainWindow(db)
    widget.show()
    app.processEvents()
    yield widget
    widget.close()
    db.close()


def test_edit_invalidates_and_blocks_stale_export(window, app):
    assert window.result is not None
    field = window.fields['tilt_deg']
    field.setFocus()
    field.selectAll()
    QTest.keyClicks(field, '3,5')
    app.processEvents()
    assert window.result is None
    assert not window.export_button.isEnabled()
    assert not window.save_button.isEnabled()
    assert window.run_calculation()
    assert window.result.design.tilt_deg == 3.5


def test_invalid_entry_blocks_calculation(window):
    window.fields['frequency_mhz'].setText('nan')
    assert not window.run_calculation()
    assert window.result is None
    assert not window.error.isHidden()


def test_channel_and_catalog_bounds(window):
    window.frequency_mode.setCurrentIndex(1)
    window.channel.setValue(14)
    assert window.run_calculation()
    assert window.result.design.frequency_mhz == 473
    assert not window.fields['frequency_mhz'].isEnabled()
    window.ofdm_offset.setChecked(True)
    assert window.run_calculation()
    assert window.result.design.frequency_mhz == pytest.approx(473+1/7)
    window.frequency_mode.setCurrentIndex(0)
    window.fields['frequency_mhz'].setText('20000')
    assert not window.run_calculation()
    assert 'fora do catálogo' in window.error.text()


def test_examples_and_unknown_efficiency(window):
    window.load_example('cable')
    assert window.result.delta_length_m*1000 == pytest.approx(60.194651912473674)
    assert window.result.feed_efficiency is None
    window.load_example('rigid')
    assert window.result.delta_length_m*1000 == pytest.approx(240.35198945334338)
    assert window.kind.currentData() == 'rigid'
    assert window.array.kind == 'rigid'


def test_manual_model_does_not_inherit_catalog_attenuation(window):
    window.model.setCurrentText(CUSTOM)
    assert window.fields['attenuation_db_100m'].text() == ''
    assert window.run_calculation()
    assert window.result.feed_efficiency is None


def test_save_reopen_and_recalculate_preserves_inputs(window):
    window.load_example('rigid')
    expected = asdict(window.result.design)
    window.project_name.setText('Teste rígido')
    window.save_project()
    record = window.db.project(window.db.projects()[0]['id'])
    window.load_example('cable')
    window.restore_payload(record['payload'], record['title'])
    assert window.result is None
    assert window.run_calculation()
    assert asdict(window.result.design) == expected
    assert record['snapshot']['result']['delta_length_m'] == window.result.delta_length_m


def test_catalog_selection(window):
    window.catalog_search.setText('LCF12-50')
    assert window.catalog_table.rowCount() == 1
    window.catalog_table.selectRow(0)
    window.use_catalog_selection()
    assert window.model.currentText() == 'LCF12-50'


def test_exports_have_actual_results_and_escape_titles(window, tmp_path):
    window.load_example('cable')
    path = tmp_path/'cable.csv'
    export_csv(path, window.result, CUSTOM)
    content = path.read_text(encoding='utf-8-sig')
    assert '969,805348' in content and '1030,000000' in content
    assert 'n/d' in content
    html = report_html(window.result, CUSTOM, '<script>alert(1)</script>')
    assert '<script>' not in html
    path = tmp_path/'result.json'
    export_json(path, snapshot(window.result, CUSTOM, window.db.catalog_hash))
    assert json.loads(path.read_text(encoding='utf-8'))['result']['feed_efficiency'] is None


def test_simple_view_shows_lengths_and_hides_technical_controls(window):
    assert window.advanced_panel.isHidden()
    assert window.metric_cards['phase'].isHidden()
    assert not window.result_tabs.isTabVisible(1)
    assert window.result_detail_stack.currentIndex() == 0
    assert 'Exemplo inicial' in window.state.text()
    assert window.simple_table.rowCount() == window.result.design.elements
    for row, element in enumerate(window.result.elements):
        assert window.simple_table.item(row, 2).text() == fmt(element.length_m*1000, 3)


def test_material_buttons_filter_models_and_change_illustration(window):
    for index, kind in [(1, 'rigid'), (0, 'cable')]:
        QTest.mouseClick(window.kind_buttons.button(index), Qt.MouseButton.LeftButton)
        assert window.kind.currentData() == kind
        assert window.kind_buttons.checkedId() == index
        names = [window.model.itemText(i) for i in range(window.model.count())]
        assert set(names) == {c.name for c in window.db.cables(kind)} | {CUSTOM}
        assert window.result is None
        assert window.run_calculation()
        assert window.array.kind == kind


def test_collapsing_details_preserves_calculation_and_all_inputs(window):
    window.advanced_button.setChecked(True)
    window.fields['common_feeder_m'].setText('15,5')
    window.fields['extra_loss_db'].setText('0,4')
    assert window.run_calculation()
    before = window.calculated_payload.copy()
    result = window.result
    window.advanced_button.setChecked(False)
    window.technical_button.setChecked(True)
    assert window.result_tabs.isTabVisible(3)
    assert window.result_detail_stack.currentIndex() == 1
    window.result_tabs.setCurrentIndex(2)
    window.technical_button.setChecked(False)
    assert window.result_tabs.currentIndex() == 0
    assert window.result is result
    assert window.calculated_payload == before
    assert window.read_design() == result.design
    assert window.save_button.isEnabled()
    assert '15,5' in window.advanced_summary.text()


@pytest.mark.parametrize('value', ['abc', '-1'])
def test_invalid_hidden_advanced_field_reopens_panel(window, value):
    window.fields['input_power_w'].setText(value)
    window.advanced_button.setChecked(False)
    assert not window.run_calculation()
    assert window.advanced_button.isChecked()
    assert not window.advanced_panel.isHidden()
    assert window.fields['input_power_w'].property('invalid')


def test_custom_model_exposes_required_characteristics(window):
    window.model.setCurrentText(CUSTOM)
    assert window.advanced_button.isChecked()
    assert window.fields['velocity_factor'].isEnabled()
    assert window.fields['attenuation_db_100m'].text() == ''


def test_invalid_hidden_common_feeder_can_be_corrected(window):
    window.fields['common_feeder_m'].setText('-1')
    assert not window.run_calculation()
    assert window.advanced_button.isChecked()
    assert 'Trecho antes do divisor' in window.error.text()
    window.fields['common_feeder_m'].setText('5')
    assert window.run_calculation()


def test_channel_mode_only_shows_relevant_frequency_controls(window):
    window.frequency_mode.setCurrentIndex(1)
    window.channel.setValue(14)
    assert not window.channel.isHidden()
    assert window.fields['frequency_mhz'].parentWidget().isHidden()
    assert '473,0000 MHz' in window.frequency_readout.text()
    window.frequency_mode.setCurrentIndex(0)
    assert window.channel.isHidden()
    assert window.frequency_readout.isHidden()
    assert not window.fields['frequency_mhz'].parentWidget().isHidden()


@pytest.mark.parametrize('tilt, wording', [(2, 'menores'), (-2, 'maiores'), (0, 'mesmo comprimento')])
def test_plain_language_direction_matches_computed_lengths(window, tilt, wording):
    window.fields['tilt_deg'].setText(str(tilt))
    assert window.run_calculation()
    assert wording in window.answer.text()
    lower, upper = window.result.elements[0].length_m, window.result.elements[-1].length_m
    assert (lower > upper) if tilt > 0 else (upper > lower) if tilt < 0 else lower == upper


def test_simple_view_preserves_engineering_warnings(window):
    assert any('lóbulos' in text for text in window.result.warnings)
    assert 'outras direções' in window.warnings.text()
    window.technical_button.setChecked(True)
    assert 'lóbulos' in window.warnings.text()
    window.technical_button.setChecked(False)
    assert 'outras direções' in window.warnings.text()


def test_control_palette_is_readable_even_after_dark_system_palette(app):
    from PySide6.QtGui import QColor, QPalette
    dark = QPalette()
    dark.setColor(QPalette.ColorRole.Text, QColor('white'))
    dark.setColor(QPalette.ColorRole.Base, QColor('#222222'))
    app.setPalette(dark)
    db = Database(':memory:')
    widget = MainWindow(db)
    try:
        palette = app.palette()
        assert palette.color(QPalette.ColorRole.Text).name() == '#172d48'
        assert palette.color(QPalette.ColorRole.Base).name() == '#ffffff'
        assert palette.color(QPalette.ColorRole.HighlightedText).name() == '#ffffff'
        assert palette.color(QPalette.ColorRole.Highlight).name() == '#123c8b'
    finally:
        widget.close()
        db.close()
