"""User consent, progress and save-before-install for the desktop updater."""
from PySide6.QtCore import QObject, QTimer, Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QProgressDialog

from . import __version__
from .updates import UpdateClient, launch_installer, version_tuple


class UpdateController(QObject):
    def __init__(self, window, client=None):
        super().__init__(window)
        self.window = window
        self.client = client or UpdateClient(self)
        self.manual = False
        self.dialog = None
        self.presenting = False
        self.client.checked.connect(self._checked)
        self.client.downloaded.connect(self._downloaded)
        self.client.failed.connect(self._failed)
        self.client.cancelled.connect(self._cancelled)
        self.client.progress.connect(self._progress)
        self.action = window.menuBar().addMenu('Ajuda').addAction('Verificar atualizações…')
        self.action.triggered.connect(lambda: self.check(manual=True))
        self.timer = QTimer(self)
        self.timer.setInterval(24 * 60 * 60 * 1000)
        self.timer.timeout.connect(self.check)
        self.startup = QTimer(self)
        self.startup.setSingleShot(True)
        self.startup.timeout.connect(self.check)
        QApplication.instance().aboutToQuit.connect(self.client.cancel)

    def start(self):
        self.startup.start(3000)
        self.timer.start()

    def check(self, manual=False):
        if self.client.busy or self.presenting:
            return
        self.manual = manual
        self.action.setEnabled(False)
        if manual:
            self.window.statusBar().showMessage('Consultando atualizações no GitHub…')
        self.client.check()

    def _question(self, title, message, accept):
        dialog = QMessageBox(QMessageBox.Icon.Information, title, message, parent=self.window)
        dialog.setTextFormat(Qt.TextFormat.PlainText)
        proceed = dialog.addButton(accept, QMessageBox.ButtonRole.AcceptRole)
        later = dialog.addButton('Agora não', QMessageBox.ButtonRole.RejectRole)
        dialog.setDefaultButton(later)
        dialog.setEscapeButton(later)
        dialog.exec()
        return dialog.clickedButton() is proceed

    def _checked(self, release):
        self.action.setEnabled(True)
        if version_tuple(release.version) <= version_tuple(__version__):
            if self.manual:
                QMessageBox.information(self.window, 'Atualizações',
                                        f'O EFTX Tilt {__version__} está atualizado.')
            return
        self.presenting = True
        accepted = self._question('Atualização disponível',
                                 f'EFTX Tilt {release.version} está disponível.\n'
                                 f'Versão instalada: {__version__}.\n\n'
                                 f'Deseja baixar a atualização ({release.size / 1024 / 1024:.1f} MB)?\n'
                                 'Seus projetos salvos serão mantidos. Você poderá continuar usando o app durante o download.',
                                 'Baixar atualização')
        self.presenting = False
        if not accepted:
            return
        self.action.setEnabled(False)
        self.dialog = QProgressDialog('Baixando atualização do EFTX Tilt…', 'Cancelar', 0, 100, self.window)
        self.dialog.setWindowTitle('Atualização do aplicativo')
        self.dialog.setWindowModality(Qt.WindowModality.NonModal)
        self.dialog.setAutoClose(False)
        self.dialog.setAutoReset(False)
        self.dialog.canceled.connect(self.client.cancel)
        self.dialog.show()
        self.client.download(release)

    def _progress(self, value):
        if self.dialog:
            self.dialog.setValue(value)

    def _close_progress(self):
        if self.dialog:
            self.dialog.reset()
            self.dialog.deleteLater()
            self.dialog = None
        self.action.setEnabled(True)

    def _downloaded(self, path, release):
        self._close_progress()
        self.presenting = True
        try:
            if not self._question('Atualização pronta',
                                  f'O instalador da versão {release.version} foi baixado e verificado.\n\n'
                                  'Vamos salvar o cálculo atual, fechar o EFTX Tilt e abrir o assistente de instalação.\n'
                                  'Ao terminar, abra o aplicativo pelo atalho EFTX Tilt Desktop.',
                                  'Salvar cálculo e instalar'):
                self.client.discard()
                return
            if not self.window.run_calculation() or not self.window.save_project():
                self.client.discard()
                QMessageBox.warning(self.window, 'Atualização adiada',
                                    'O cálculo atual não pôde ser salvo. Corrija os campos ou o banco antes de atualizar.')
                return
            try:
                launch_installer(path, release)
            except (OSError, ValueError):
                self.client.discard()
                QMessageBox.warning(self.window, 'Instalação não iniciada',
                                    'Não foi possível abrir o instalador. Seu cálculo foi salvo. Tente novamente em Ajuda → Verificar atualizações.')
                return
            QApplication.instance().quit()
        finally:
            self.presenting = False

    def _failed(self, message):
        downloading = self.dialog is not None
        self._close_progress()
        if self.manual or downloading:
            QMessageBox.warning(self.window, 'Atualizações', message)
        else:
            self.window.statusBar().showMessage('Atualizações indisponíveis no momento. Você pode continuar usando o aplicativo.', 10000)

    def _cancelled(self):
        self._close_progress()
        self.window.statusBar().showMessage('Download cancelado. Nenhuma atualização foi instalada.', 7000)
