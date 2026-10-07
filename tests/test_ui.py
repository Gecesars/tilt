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
