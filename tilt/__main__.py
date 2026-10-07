import argparse
import os
from pathlib import Path
import sqlite3
import sys

from PySide6.QtCore import QStandardPaths, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from .storage import Database
from .window import MainWindow


def main():
    parser = argparse.ArgumentParser(description='EFTX Tilt elétrico')
    parser.add_argument('--database', type=Path, help='Banco SQLite alternativo para bancada/teste')
    parser.add_argument('--smoke-test', action='store_true', help='Abre e encerra após a primeira renderização')
    parser.add_argument('--smoke-pdf', type=Path, help='Com --smoke-test, gera um PDF de exemplo e testa sua prévia; não imprime')
    args = parser.parse_args()
    if args.smoke_pdf and not args.smoke_test:
        parser.error('--smoke-pdf requer --smoke-test')
    app = QApplication(sys.argv[:1])
    # Windows' offscreen Qt plugin does not enumerate fonts. Keep diagnostic
    # PDFs readable while native Windows continues to use its normal font set.
    if os.name == 'nt':
        from PySide6.QtGui import QFontDatabase
        if not QFontDatabase.families():
            for name in ('segoeui.ttf', 'segoeuib.ttf', 'segoeuii.ttf'):
                QFontDatabase.addApplicationFont(str(Path(os.environ.get('WINDIR', 'C:/Windows'))/'Fonts'/name))
    app.setApplicationName('EFTX Tilt')
    app.setOrganizationName('EFTX')
    app.setStyle('Fusion')
    database_path = args.database or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)) / 'tilt.sqlite3'
    try:
        db = Database(database_path)
    except (OSError, sqlite3.Error, ValueError):
        QMessageBox.critical(None, 'Banco indisponível', 'Não foi possível abrir o banco local. Verifique permissões, espaço em disco e a versão da aplicação.')
        return 1
    window = MainWindow(db)
    window.show()
    if args.smoke_test:
        if window.result is None:
            db.close()
            return 2
        if args.smoke_pdf:
            from .printing import PrintPreview
            window.write_pdf(args.smoke_pdf)
            preview = PrintPreview(args.smoke_pdf, window)
            preview.show()
        QTimer.singleShot(1200, app.quit)
    code = app.exec()
    db.close()
    return code


if __name__ == '__main__':
    raise SystemExit(main())
