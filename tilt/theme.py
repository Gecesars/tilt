"""Explicit light palette: readable controls even when Windows uses dark mode."""
from pathlib import Path

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

ASSETS = Path(__file__).parent / 'assets'


def apply_palette():
    palette = QPalette()
    colors = {
        QPalette.ColorRole.Window: '#edf2f8',
        QPalette.ColorRole.WindowText: '#172d48',
        QPalette.ColorRole.Base: '#ffffff',
        QPalette.ColorRole.AlternateBase: '#f0f4fa',
        QPalette.ColorRole.Text: '#172d48',
        QPalette.ColorRole.Button: '#ffffff',
        QPalette.ColorRole.ButtonText: '#172d48',
        QPalette.ColorRole.Highlight: '#123c8b',
        QPalette.ColorRole.HighlightedText: '#ffffff',
        QPalette.ColorRole.ToolTipBase: '#172d48',
        QPalette.ColorRole.ToolTipText: '#ffffff',
        QPalette.ColorRole.PlaceholderText: '#53627b',
    }
    for role, color in colors.items():
        for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
            palette.setColor(group, role, QColor(color))
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(color))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor('#53627b'))
    QApplication.instance().setPalette(palette)


STYLE = '''
QMainWindow, QDialog {background:#edf2f8;}
QWidget {font-family:"Segoe UI";font-size:11pt;color:#172d48;}
QFrame#Header {background:white;border-bottom:1px solid #adbdd1;}
QLabel#AppTitle {font-size:21pt;font-weight:650;color:#092c74;}
QLabel#Subtitle {color:#40536e;font-size:10pt;}
QLabel#State {background:#e7eefb;color:#183d83;border-radius:5px;padding:10px;font-weight:600;}
QLabel#Error {background:#fff0ef;color:#8d241b;border:2px solid #bc3027;padding:10px;border-radius:5px;}
QLabel#Notice {background:#fff5df;color:#704200;border:1px solid #aa741d;padding:10px;border-radius:5px;}
QLabel#Answer {background:#eaf3ff;color:#12366f;border:1px solid #587caa;border-radius:6px;padding:13px;font-size:12pt;}
QGroupBox {background:white;border:1px solid #a8b9cf;border-radius:7px;margin-top:10px;padding:12px 12px 8px 12px;font-weight:600;}
QGroupBox::title {subcontrol-origin:margin;left:12px;padding:0 4px;color:#183d83;}
QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox {background:white;color:#172d48;border:2px solid #627995;border-radius:5px;min-height:26px;padding:2px 9px;selection-background-color:#123c8b;selection-color:white;}
QLineEdit:focus,QComboBox:focus,QSpinBox:focus,QDoubleSpinBox:focus {border:2px solid #092c74;background:#f3f7ff;}
QLineEdit[invalid="true"] {border:2px solid #bc3027;background:#fff0ef;}
QLineEdit:disabled,QComboBox:disabled,QSpinBox:disabled,QDoubleSpinBox:disabled {background:#e7edf4;color:#40536e;border-color:#9baabe;}
QComboBox {padding-right:35px;}
QComboBox::drop-down {subcontrol-origin:border;subcontrol-position:top right;width:30px;background:#123c8b;border-top-right-radius:3px;border-bottom-right-radius:3px;}
QComboBox::down-arrow {image:url(@DOWN@);width:14px;height:10px;}
QComboBox QAbstractItemView {background:white;color:#172d48;selection-background-color:#123c8b;selection-color:white;border:2px solid #627995;outline:0;}
QComboBox QAbstractItemView::item {min-height:32px;padding:4px;}
QSpinBox,QDoubleSpinBox {padding-right:32px;}
QSpinBox::up-button,QDoubleSpinBox::up-button {subcontrol-origin:border;subcontrol-position:top right;width:29px;background:#123c8b;border-bottom:1px solid white;border-top-right-radius:3px;}
QSpinBox::down-button,QDoubleSpinBox::down-button {subcontrol-origin:border;subcontrol-position:bottom right;width:29px;background:#123c8b;border-bottom-right-radius:3px;}
QSpinBox::up-arrow,QDoubleSpinBox::up-arrow {image:url(@UP@);width:12px;height:8px;}
QSpinBox::down-arrow,QDoubleSpinBox::down-arrow {image:url(@DOWN@);width:12px;height:8px;}
QCheckBox {spacing:9px;padding:4px 0;}
QCheckBox::indicator {width:20px;height:20px;border:2px solid #627995;border-radius:3px;background:white;}
QCheckBox::indicator:checked {background:#123c8b;border-color:#123c8b;image:url(@CHECK@);}
QCheckBox::indicator:focus {border-color:#092c74;}
QPushButton {background:white;color:#17365e;border:2px solid #627995;border-radius:6px;padding:6px 13px;font-weight:600;min-height:23px;}
QPushButton:hover {background:#e3edff;border-color:#123c8b;}
QPushButton:focus {border:2px solid #092c74;background:#e3edff;}
QPushButton:pressed {background:#cddfff;}
QPushButton:disabled {color:#53627b;background:#e7edf4;border-color:#9baabe;}
QPushButton#Primary {background:#123c8b;color:white;border:2px solid #123c8b;}
QPushButton#Primary:hover,QPushButton#Primary:focus {background:#092c74;border-color:#061e50;}
QPushButton#Primary:disabled {background:#e7edf4;color:#53627b;border-color:#9baabe;}
QPushButton#Choice {text-align:center;min-height:38px;padding:6px 4px;}
QPushButton#Choice:checked {background:#123c8b;color:white;border-color:#092c74;}
QPushButton#Disclosure:checked {background:#e3edff;color:#092c74;}
QTabWidget::pane {border:1px solid #a8b9cf;background:white;border-radius:4px;}
QTabBar::tab {padding:8px 15px;background:#e4ebf5;color:#324968;border-bottom:3px solid transparent;}
QTabBar::tab:selected {background:white;color:#092c74;border-bottom:3px solid #be1e2d;font-weight:600;}
QTableWidget {background:white;alternate-background-color:#eef3f9;gridline-color:#bdcbdd;border:0;selection-background-color:#d9e6ff;selection-color:#132f5a;font-size:11pt;}
QHeaderView::section {background:#e0e9f5;color:#17365e;border:0;border-bottom:1px solid #9eb2cc;padding:10px;font-weight:600;}
QFrame#Metric {background:white;border:1px solid #a8b9cf;border-radius:6px;}
QLabel#MetricValue {color:#092c74;font-size:21pt;font-weight:650;}
QLabel#MetricName {color:#40536e;font-size:10pt;}
QScrollArea {border:0;background:transparent;}
QScrollBar:vertical {background:#e1e8f2;width:13px;}
QScrollBar::handle:vertical {background:#637b9b;border-radius:4px;min-height:35px;}
QTextBrowser {border:0;background:white;padding:14px;}
QToolTip {background:#172d48;color:white;border:1px solid #172d48;padding:7px;}
QStatusBar {background:#142d50;color:white;}
QStatusBar QLabel {color:white;}
'''
for marker, name in [('DOWN', 'control_down.svg'), ('UP', 'control_up.svg'), ('CHECK', 'control_check.svg')]:
    STYLE = STYLE.replace('@'+marker+'@', (ASSETS/name).as_posix())
