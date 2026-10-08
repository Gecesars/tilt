"""Asynchronous, opt-in installer downloads from the official public release."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

from PySide6.QtCore import QObject, QStandardPaths, QTimer, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest, QSslSocket

from . import __version__

REPOSITORY = 'https://github.com/Gecesars/tilt'
LATEST_URL = 'https://api.github.com/repos/Gecesars/tilt/releases/latest'
MAX_METADATA = 1024 * 1024
MAX_INSTALLER = 512 * 1024 * 1024


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r'v?(0|[1-9]\d{0,5})\.(0|[1-9]\d{0,5})\.(0|[1-9]\d{0,5})', value):
        raise ValueError('Versão publicada inválida.')
    return tuple(int(part) for part in value.removeprefix('v').split('.'))


@dataclass(frozen=True)
class Release:
    version: str
    url: str
    filename: str
    download_url: str
    size: int
    sha256: str


def parse_release(data):
    """No remote filename, command, notes or URL becomes executable input."""
    if not isinstance(data, dict) or data.get('draft') is not False or data.get('prerelease') is not False:
        raise ValueError('A publicação não é uma versão estável.')
    tag = data.get('tag_name')
    version_tuple(tag)
    version = tag.removeprefix('v')
    url = f'{REPOSITORY}/releases/tag/{tag}'
    if data.get('html_url') != url:
        raise ValueError('Origem da publicação inválida.')
    assets = data.get('assets')
    if not isinstance(assets, list):
        raise ValueError('Instalador indisponível nesta publicação.')
    # Prefer MSI; keep EXE fallback for existing stable releases.
    names = [f'EFTX_Tilt-{version}-Windows-x64.msi', f'EFTX_Tilt-{version}-Setup-x64.exe']
    filename = next((name for name in names if any(isinstance(asset, dict) and asset.get('name') == name
                                                for asset in assets)), names[0])
    matches = [asset for asset in assets if isinstance(asset, dict) and asset.get('name') == filename]
    if len(matches) != 1:
        raise ValueError('Instalador indisponível nesta publicação.')
    asset = matches[0]
    download_url = f'{REPOSITORY}/releases/download/{tag}/{filename}'
    size, digest = asset.get('size'), asset.get('digest')
    if (asset.get('state') != 'uploaded' or asset.get('browser_download_url') != download_url
            or type(size) is not int or not 0 < size <= MAX_INSTALLER
            or not isinstance(digest, str) or not re.fullmatch(r'sha256:[a-f0-9]{64}', digest)):
        raise ValueError('Instalador sem metadados válidos de integridade.')
    return Release(version, url, filename, download_url, size, digest[7:])


def safe_redirect(url):
    try:
        value = urlsplit(url)
        return (value.scheme == 'https' and value.hostname in {'github.com', 'release-assets.githubusercontent.com'}
                and value.port in (None, 443) and not value.username and not value.password and not value.fragment)
    except ValueError:
        return False


def verify_installer(path, release):
    path = Path(path)
    if path.name != release.filename or path.stat().st_size != release.size:
        raise ValueError('O instalador está incompleto. Faça o download novamente.')
    with path.open('rb') as stream:
        signature = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1' if path.suffix.lower() == '.msi' else b'MZ'
        if stream.read(len(signature)) != signature:
            raise ValueError('O arquivo recebido não é um instalador Windows.')
        stream.seek(0)
        if hashlib.file_digest(stream, 'sha256').hexdigest() != release.sha256:
            raise ValueError('A integridade do instalador não foi confirmada. Faça o download novamente.')


def installer_command(path):
    path = Path(path).resolve()
    if path.suffix.lower() == '.msi':
        log_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)) / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        # Native Windows Installer handles upgrade, repair, rollback and files
        # in use. The interactive wizard cannot copy before the app exits.
        return [str(Path(os.environ['SystemRoot'])/'System32'/'msiexec.exe'), '/i', str(path),
                '/norestart', '/L*v', str(log_dir/f'update-{__version__}.log')]
    return [str(path), f'/WAITPID={os.getpid()}']


def launch_installer(path, release):
    """Launch the interactive Windows Installer or the legacy-compatible bridge."""
    if sys.platform != 'win32':
        raise OSError('A instalação automática está disponível no Windows.')
    verify_installer(path, release)
    # Never invoke a shell, silently accept the license or pass remote arguments.
    # PyInstaller's altered DLL search path must not leak into the NSIS child.
    import ctypes
    ctypes.windll.kernel32.SetDllDirectoryW(None)
    try:
        return subprocess.Popen(installer_command(path),
                                cwd=str(Path(path).resolve().parent), close_fds=True)
    finally:
        if getattr(sys, 'frozen', False):
            ctypes.windll.kernel32.SetDllDirectoryW(sys._MEIPASS)


class UpdateClient(QObject):
    checked = Signal(object)
    downloaded = Signal(object, object)
    failed = Signal(str)
    cancelled = Signal()
    progress = Signal(int)

    def __init__(self, parent=None, cache_dir=None):
        super().__init__(parent)
        if sys.platform == 'win32':
            QSslSocket.setActiveBackend('schannel')  # TLS and CA store provided by Windows 10/11.
        self.manager = QNetworkAccessManager(self)
        self.cache_dir = Path(cache_dir) if cache_dir else Path(QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.CacheLocation)) / 'updates'
        self.reply = None
        self.release = None
        self.path = None
        self.stream = None
        self.timeout = QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.timeout.connect(lambda: self._abort('Tempo de conexão esgotado. Tente novamente.'))

    @property
    def busy(self):
        return self.reply is not None

    def _start(self, url, downloading=False):
        self.error = ''
        self.was_cancelled = False
        self.body = bytearray()
        self.received = 0
        self.downloading = downloading
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b'User-Agent', f'EFTX-Tilt/{__version__}'.encode('ascii'))
        request.setRawHeader(b'Accept', b'application/octet-stream' if downloading else b'application/vnd.github+json')
        if not downloading:
            request.setRawHeader(b'X-GitHub-Api-Version', b'2022-11-28')
        request.setTransferTimeout(30000)
        request.setMaximumRedirectsAllowed(5)
        request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                             QNetworkRequest.RedirectPolicy.UserVerifiedRedirectPolicy)
        self.reply = self.manager.get(request)
        self.reply.setReadBufferSize(256 * 1024)
        self.reply.readyRead.connect(self._read)
        self.reply.redirected.connect(self._redirect)
        self.reply.finished.connect(self._finished)
        self.timeout.start(30 * 60 * 1000 if downloading else 20000)

    def check(self):
        if not self.busy:
            self._start(LATEST_URL)

    def download(self, release):
        if self.busy:
            return
        self.release = release
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            folder = Path(tempfile.mkdtemp(prefix='eftx-update-', dir=self.cache_dir))
            self.path = folder / (release.filename + '.partial')
            self.stream = self.path.open('xb')
        except OSError:
            self.discard()
            self.failed.emit('Não foi possível gravar a atualização. Verifique o espaço e a permissão de escrita.')
            return
        self._start(release.download_url, downloading=True)

    def _redirect(self, url):
        if self.downloading and safe_redirect(url.toString()):
            self.reply.redirectAllowed.emit()
        else:
            self._abort('O download foi redirecionado para uma origem não autorizada.')

    def _abort(self, message):
        if self.reply:
            self.error = message
            self.reply.abort()

    def cancel(self):
        if self.reply:
            self.was_cancelled = True
            self.reply.abort()

    def _read(self):
        reply = self.reply
        if reply is None or self.error or self.was_cancelled:
            return
        # Redirect/HTTP error bodies are never part of the installer.
        if reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) != 200:
            reply.readAll()
            return
        while reply.bytesAvailable():
            chunk = bytes(reply.read(128 * 1024))
            self.received += len(chunk)
            if self.received > (self.release.size if self.downloading else MAX_METADATA):
                self._abort('O arquivo recebido ultrapassou o tamanho informado.')
                return
            if self.downloading:
                try:
                    self.stream.write(chunk)
                except OSError:
                    self._abort('Não foi possível gravar a atualização. Verifique o espaço em disco.')
                    return
            else:
                self.body.extend(chunk)
        if self.downloading:
            self.progress.emit(min(99, self.received * 100 // self.release.size))

    def _finished(self):
        reply = self.reply
        self._read()
        self.timeout.stop()
        self.reply = None
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        try:
            if self.stream:
                self.stream.close()
                self.stream = None
            if self.was_cancelled:
                self.discard()
                self.cancelled.emit()
                return
            if self.error:
                raise ValueError(self.error)
            if status in (403, 429):
                raise ValueError('O GitHub limitou as consultas. Tente novamente mais tarde.')
            if reply.error() != QNetworkReply.NetworkError.NoError or status != 200:
                raise ValueError('Não foi possível acessar a atualização. Verifique a conexão e tente novamente.')
            if self.downloading:
                final_path = self.path.with_suffix('')
                self.path.rename(final_path)
                self.path = final_path
                verify_installer(self.path, self.release)
                self.progress.emit(100)
                self.downloaded.emit(self.path, self.release)
            else:
                self.checked.emit(parse_release(json.loads(self.body)))
        except (ValueError, TypeError, OSError):
            # Network/server contents never appear in the user-facing error.
            self.discard()
            message = self.error or 'A atualização não pôde ser validada. Tente novamente mais tarde.'
            if status in (403, 429):
                message = 'O GitHub limitou as consultas. Tente novamente mais tarde.'
            elif reply.error() != QNetworkReply.NetworkError.NoError:
                message = 'Não foi possível acessar o GitHub. Verifique sua conexão e tente novamente.'
            self.failed.emit(message)
        finally:
            reply.deleteLater()

    def discard(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        if self.path:
            try:
                self.path.unlink(missing_ok=True)
                self.path.parent.rmdir()  # Only this download's empty, generated directory.
            except OSError:
                pass
            self.path = None
