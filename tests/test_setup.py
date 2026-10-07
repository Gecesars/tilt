from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.prepare_setup import generate_lists
from tools.windows_package import consolidate_msvc
from tilt.diagnostics import is_packaged_runtime


def test_diagnostic_distinguishes_windows_crt_from_redistributable_msvc():
    assert not is_packaged_runtime('msvcp_win.dll')
    assert not is_packaged_runtime('ucrtbase.dll')
    assert all(is_packaged_runtime(n) for n in ('MSVCP140.dll','vcruntime140_1.dll',
                                              'Qt6Pdf.dll','python312.dll','sqlite3.dll','libcrypto-3.dll'))


def test_explicit_uninstaller_preserves_unknown_files(tmp_path):
    payload = tmp_path/'payload'
    payload.mkdir()
    (payload/'EFTX_Tilt.exe').write_bytes(b'fixture')
    (payload/'_internal').mkdir()
    (payload/'_internal/library.dll').write_bytes(b'library')
    output = tmp_path/'generated'
    output.mkdir()
    generate_lists(payload, output)
    remove = (output/'UninstallFiles.nsh').read_text(encoding='utf-8-sig')
    install = (output/'InstallFiles.nsh').read_text(encoding='utf-8-sig')
    assert 'library.dll' in remove and 'EFTX_Tilt.exe' in remove
    assert 'RMDir /r' not in remove and '*' not in remove
    assert 'sqlite' not in remove and 'user-added' not in remove
    assert install.count('IfErrors install_failed') == 2
    assert remove.count('uninstall_failed') == 2


def test_msvc_is_complete_and_newest_copies_are_bootstrap_local(monkeypatch):
    import pefile
    class FakePE:
        def __init__(self, path, **kwargs):
            self.VS_FIXEDFILEINFO = [SimpleNamespace(FileVersionMS=int(path[0]), FileVersionLS=0)]
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
    monkeypatch.setattr(pefile, 'PE', FakePE)
    names = ['vcruntime140.dll','vcruntime140_1.dll','msvcp140.dll','msvcp140_1.dll','msvcp140_2.dll']
    files = [('PySide6/'+name, '1/'+name, 'BINARY') for name in names]
    files.append(('vcruntime140.dll', '2/vcruntime140.dll', 'BINARY'))
    result = consolidate_msvc(files)
    assert len(result) == 5
    assert ('vcruntime140.dll','2/vcruntime140.dll','BINARY') in result
    assert all('/' not in name and '\\' not in name for name, _, _ in result)
    with pytest.raises(ValueError, match='incompleto'):
        consolidate_msvc(files[:2])


def test_exe_installer_is_per_user_and_independent_from_msi():
    source = (Path(__file__).resolve().parents[1]/'installer/Setup.nsi').read_text(encoding='utf-8')
    assert 'RequestExecutionLevel user' in source
    assert 'MUI_LICENSEPAGE_CHECKBOX' in source and '/ACCEPTEULA=' in source
    assert 'msiexec' not in source.lower() and 'download' not in source.lower()
    assert 'RMDir /r' not in source and 'Delete "$LOCALAPPDATA' not in source
    assert 'ReadINIStr $0 "$INSTDIR\\.eftx-install.ini"' in source
