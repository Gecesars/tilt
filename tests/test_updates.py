from dataclasses import replace
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import threading
import time

import pytest
from PySide6.QtCore import QObject, Signal, QTimer, QUrl
from PySide6.QtTest import QTest

from tilt import update_ui, updates
from tilt.updates import Release, UpdateClient, parse_release, safe_redirect, verify_installer, version_tuple


CONTENT = b'MZ' + b'installer test payload' * 20


def metadata(version='1.5.0'):
    tag = 'v' + version
    name = f'EFTX_Tilt-{version}-Setup-x64.exe'
    return {'tag_name': tag, 'draft': False, 'prerelease': False,
            'html_url': f'{updates.REPOSITORY}/releases/tag/{tag}',
            'assets': [{'name': name, 'state': 'uploaded', 'size': len(CONTENT),
                        'digest': 'sha256:' + hashlib.sha256(CONTENT).hexdigest(),
                        'browser_download_url': f'{updates.REPOSITORY}/releases/download/{tag}/{name}'}]}


def test_versions_are_numeric_and_only_stable():
    assert version_tuple('v1.10.0') > version_tuple('1.9.12')
    assert version_tuple('1.4.0') == version_tuple('v1.4.0')
    for bad in ('1.4', '1.4.1-beta', '01.4.0', '../../1.4.0', 'v1.4.0\n', None, 140):
        with pytest.raises(ValueError):
            version_tuple(bad)


@pytest.mark.parametrize('field,value', [('draft', True), ('prerelease', True), ('tag_name', 'v2.0.0-rc1'),
                                      ('html_url', 'https://github.com/other/tilt/releases/tag/v1.5.0'),
                                      ('assets', []), ('assets', None)])
def test_reject_untrusted_or_incomplete_releases(field, value):
    data = metadata()
    data[field] = value
    with pytest.raises(ValueError):
        parse_release(data)


@pytest.mark.parametrize('field,value', [('browser_download_url', 'https://evil.example/installer.exe'),
                                      ('name', '../EFTX_Tilt-1.5.0-Setup-x64.exe'), ('state', 'new'),
                                      ('size', True), ('size', 0), ('size', updates.MAX_INSTALLER+1),
                                      ('digest', None), ('digest', 'sha256:'+'0'*63)])
def test_reject_unsafe_asset(field, value):
    data = metadata()
    data['assets'][0][field] = value
    with pytest.raises(ValueError):
        parse_release(data)


def test_reject_ambiguous_asset():
    data = metadata()
    data['assets'] *= 2
    with pytest.raises(ValueError):
        parse_release(data)


@pytest.mark.parametrize('url', ['http://github.com/file', 'https://github.com.evil.test/file',
                                 'https://github.com@evil.test/file', 'https://user@github.com/file',
                                 'file:///C:/temp/update.exe', 'https://127.0.0.1/file',
                                 'https://github.com:444/file', 'https://github.com:wrong/file'])
def test_redirect_rejects_downgrade_and_external_hosts(url):
    assert not safe_redirect(url)


def test_github_asset_redirect_and_file_integrity(tmp_path):
    assert safe_redirect('https://release-assets.githubusercontent.com/file?signature=example')
    release = parse_release(metadata())
    path = tmp_path / release.filename
    path.write_bytes(CONTENT)
    verify_installer(path, release)
    path.write_bytes(b'MZ' + b'x'*(len(CONTENT)-2))
    with pytest.raises(ValueError, match='integridade'):
        verify_installer(path, release)
    path.write_bytes(CONTENT[:-1])
    with pytest.raises(ValueError, match='incompleto'):
        verify_installer(path, release)


@pytest.fixture
def server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            time.sleep(getattr(self.server, 'delay', 0))
            status, headers, content = self.server.response
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header('Content-Length', len(content))
            self.end_headers()
            try:
                self.wfile.write(content)
            except OSError:
                pass
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.response = (200, {}, json.dumps(metadata()).encode())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    server.url = f'http://127.0.0.1:{server.server_port}/fixture'
    yield server
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def await_signal(signal, action, app):
    values = []
    signal.connect(lambda *args: values.append(args))
    action()
    deadline = time.monotonic() + 5
    while not values and time.monotonic() < deadline:
        QTest.qWait(10)
    assert values, 'Asynchronous operation did not finish'
    return values[0]


def test_async_check_does_not_block_and_parses_metadata(server, monkeypatch, tmp_path, app):
    monkeypatch.setattr(updates, 'LATEST_URL', server.url)
    client = UpdateClient(cache_dir=tmp_path)
    ticks = []
    QTimer.singleShot(0, lambda: ticks.append(True))
    result, = await_signal(client.checked, client.check, app)
    assert result.version == '1.5.0' and ticks and not client.busy


@pytest.mark.parametrize('status,body', [(429, b'secret rate details'), (500, b'private server error'),
                                        (200, b'not json'), (200, b'x'*(updates.MAX_METADATA+1))],
                         ids=['rate-limit', 'server-error', 'invalid-json', 'oversized'])
def test_network_failures_are_sanitized(server, monkeypatch, tmp_path, app, status, body):
    server.response = status, {}, body
    monkeypatch.setattr(updates, 'LATEST_URL', server.url)
    client = UpdateClient(cache_dir=tmp_path)
    message, = await_signal(client.failed, client.check, app)
    assert message and 'secret' not in message and 'private' not in message
    assert not client.busy


def test_cancel_download_removes_partial_and_never_emits_ready(server, tmp_path, app):
    release = replace(parse_release(metadata()), download_url=server.url)
    client = UpdateClient(cache_dir=tmp_path)
    ready = []
    client.downloaded.connect(lambda *args: ready.append(args))
    def start():
        client.download(release)
        client.cancel()
    await_signal(client.cancelled, start, app)
    assert not client.busy and not ready and not list(tmp_path.rglob('*.partial'))


def test_download_checks_digest_before_ready(server, tmp_path, app):
    server.response = 200, {}, CONTENT
    release = replace(parse_release(metadata()), download_url=server.url)
    client = UpdateClient(cache_dir=tmp_path)
    path, actual = await_signal(client.downloaded, lambda: client.download(release), app)
    assert path.read_bytes() == CONTENT and actual == release
    client.discard()
    assert not path.exists()
    server.response = 200, {}, b'MZ'+b'x'*(len(CONTENT)-2)
    await_signal(client.failed, lambda: client.download(release), app)
    assert not list(tmp_path.rglob('*.exe'))


def test_untrusted_redirect_is_never_followed(server, monkeypatch, tmp_path, app):
    server.response = 302, {'Location': 'http://127.0.0.1:1/should-not-connect'}, b''
    monkeypatch.setattr(updates, 'LATEST_URL', server.url)
    client = UpdateClient(cache_dir=tmp_path)
    await_signal(client.failed, client.check, app)
    assert not client.busy


def test_tls_certificate_failure_is_not_ignored(server, monkeypatch, tmp_path, app):
    # An HTTP-only server cannot complete TLS; the application must fail closed.
    monkeypatch.setattr(updates, 'LATEST_URL', server.url.replace('http:', 'https:'))
    client = UpdateClient(cache_dir=tmp_path)
    await_signal(client.failed, client.check, app)
    assert not client.busy


def test_timeout_stops_request_and_removes_partial(server, tmp_path, app):
    server.delay = .2
    release = replace(parse_release(metadata()), download_url=server.url)
    client = UpdateClient(cache_dir=tmp_path)
    def start():
        client.download(release)
        client.timeout.start(1)
    await_signal(client.failed, start, app)
    assert not client.busy and not list(tmp_path.rglob('*.partial'))


def test_allowed_github_redirect_emits_qt_permission(tmp_path, app):
    class Reply(QObject):
        redirectAllowed = Signal()
    client = UpdateClient(cache_dir=tmp_path)
    client.reply = Reply()
    client.downloading = True
    calls = []
    client.reply.redirectAllowed.connect(lambda: calls.append(True))
    client._redirect(QUrl('https://release-assets.githubusercontent.com/fixture?signature=example'))
    assert calls == [True]
    client.reply = None


def test_decline_update_never_downloads(window, monkeypatch):
    controller = window.updates
    called = []
    monkeypatch.setattr(controller, '_question', lambda *args: False)
    monkeypatch.setattr(controller.client, 'download', lambda *args: called.append(args))
    controller._checked(parse_release(metadata()))
    assert not called and controller.action.isEnabled()


@pytest.mark.parametrize('version', ['1.3.2', '1.4.0'])
def test_equal_and_older_versions_do_not_prompt(window, monkeypatch, version):
    def unexpected(*args):
        pytest.fail('Should not offer an equal/older version')
    monkeypatch.setattr(window.updates, '_question', unexpected)
    window.updates._checked(parse_release(metadata(version)))


def test_confirm_download_and_cancel_controls(window, monkeypatch):
    controller = window.updates
    downloads = []
    monkeypatch.setattr(controller, '_question', lambda *args: True)
    monkeypatch.setattr(controller.client, 'download', downloads.append)
    release = parse_release(metadata())
    controller._checked(release)
    assert downloads == [release] and controller.dialog is not None
    controller._cancelled()
    assert controller.dialog is None and controller.action.isEnabled()


def test_real_download_reaches_second_consent_and_can_be_deferred(window, server, tmp_path, app, monkeypatch):
    server.response = 200, {}, CONTENT
    controller = window.updates
    controller.client.cache_dir = tmp_path
    confirmations = []
    def confirm(*args):
        confirmations.append(args)
        return len(confirmations) == 1  # Download yes; installation no.
    monkeypatch.setattr(controller, '_question', confirm)
    release = replace(parse_release(metadata()), download_url=server.url)
    await_signal(controller.client.downloaded, lambda: controller._checked(release), app)
    assert len(confirmations) == 2 and controller.dialog is None
    assert not controller.client.busy and not list(tmp_path.rglob('*.exe'))
    assert not window.db.projects()


@pytest.mark.parametrize('failure', ['invalid_input', 'database'])
def test_installation_aborted_if_current_work_cannot_be_saved(window, monkeypatch, failure):
    controller = window.updates
    monkeypatch.setattr(controller, '_question', lambda *args: True)
    messages, launches = [], []
    monkeypatch.setattr(update_ui.QMessageBox, 'warning', lambda *args: messages.append(args))
    monkeypatch.setattr(update_ui, 'launch_installer', lambda *args: launches.append(args))
    if failure == 'invalid_input':
        window.fields['frequency_mhz'].setText('invalid')
    else:
        def fail(*args):
            raise sqlite3.OperationalError('fixture')
        monkeypatch.setattr(window.db, 'save_project', fail)
    controller._downloaded(Path('unused.exe'), parse_release(metadata()))
    assert not launches and messages


def test_save_before_launch_and_exit_order(window, monkeypatch, app):
    controller = window.updates
    monkeypatch.setattr(controller, '_question', lambda *args: True)
    events = []
    window.fields['tilt_deg'].setText('3.5')
    def launch(*args):
        record = window.db.project(window.db.projects()[0]['id'])
        assert record['payload']['design']['tilt_deg'] == 3.5
        events.append('saved then launched')
    monkeypatch.setattr(update_ui, 'launch_installer', launch)
    monkeypatch.setattr(app, 'quit', lambda: events.append('quit'))
    controller._downloaded(Path('fixture.exe'), parse_release(metadata()))
    assert events == ['saved then launched', 'quit']


def test_launch_failure_keeps_app_open_and_saved_project(window, monkeypatch, app):
    monkeypatch.setattr(window.updates, '_question', lambda *args: True)
    def fail(*args):
        raise OSError('access denied')
    monkeypatch.setattr(update_ui, 'launch_installer', fail)
    messages, exits = [], []
    monkeypatch.setattr(update_ui.QMessageBox, 'warning', lambda *args: messages.append(args))
    monkeypatch.setattr(app, 'quit', lambda: exits.append(True))
    window.updates._downloaded(Path('fixture.exe'), parse_release(metadata()))
    assert window.db.projects() and messages and not exits


def test_automatic_error_is_nonmodal_manual_error_is_visible(window, monkeypatch):
    messages = []
    monkeypatch.setattr(update_ui.QMessageBox, 'warning', lambda *args: messages.append(args))
    window.updates._failed('Falha de conexão')
    assert not messages
    window.updates.manual = True
    window.updates._failed('Falha de conexão')
    assert len(messages) == 1


def test_installer_command_uses_no_shell_or_silent_install(tmp_path, monkeypatch):
    if updates.sys.platform != 'win32':
        pytest.skip('Windows process launcher')
    release = parse_release(metadata())
    path = tmp_path/release.filename
    path.write_bytes(CONTENT)
    calls = []
    monkeypatch.setattr(updates.subprocess, 'Popen', lambda *args, **kwargs: calls.append((args, kwargs)))
    updates.launch_installer(path, release)
    args, kwargs = calls[0]
    assert args[0][0] == str(path.resolve())
    assert args[0][1].startswith('/WAITPID=') and len(args[0]) == 2
    assert not kwargs.get('shell')
