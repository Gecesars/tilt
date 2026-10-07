import argparse
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
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
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
        QTimer.singleShot(1200, app.quit)
    code = app.exec()
    db.close()
    return code


if __name__ == '__main__':
    raise SystemExit(main())
