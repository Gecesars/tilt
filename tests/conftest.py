import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from tilt.storage import Database
from tilt.window import MainWindow


@pytest.fixture(scope='session')
def app():
    app = QApplication.instance() or QApplication([])
    if not QFontDatabase.families() and os.name == 'nt':
        for name in ('segoeui.ttf', 'segoeuib.ttf', 'segoeuii.ttf'):
            QFontDatabase.addApplicationFont(os.path.join(os.environ.get('WINDIR', 'C:/Windows'), 'Fonts', name))
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
