from pathlib import Path

import pytest

from tilt.platform_support import supports_windows
from tools.windows_package import filter_windows_binaries


@pytest.mark.parametrize('version,bits,expected', [
    ((6, 3, 9600), 64, False),  # Windows 8.1
    ((10, 0, 10240), 64, False),  # Original Windows 10
    ((10, 0, 17134), 64, False),  # 1803, below Qt baseline
    ((10, 0, 17763), 64, True),  # 1809 / LTSC 2019
    ((10, 0, 19044), 64, True),  # 21H2 / LTSC 2021
    ((10, 0, 19045), 64, True),  # 22H2
    ((10, 0, 22631), 64, True),  # Windows 11
    ((10, 0, 19045), 32, False),
])
def test_windows_baseline(version, bits, expected):
    assert supports_windows(version, bits) is expected


def test_foreign_system_shims_are_removed_but_real_runtimes_remain(tmp_path):
    python = tmp_path/'python'
    foreign = tmp_path/'other_app'
    items = [
        ('api-ms-win-core-file-l1-1-0.dll', str(foreign/'api-ms-win-core-file-l1-1-0.dll'), 'BINARY'),
        ('ucrtbase.dll', str(foreign/'ucrtbase.dll'), 'BINARY'),
        ('icuuc.dll', str(foreign/'icuuc.dll'), 'BINARY'),
        ('PySide6/plugins/tls/qopensslbackend.dll', str(python/'qopensslbackend.dll'), 'BINARY'),
        ('vcruntime140.dll', str(python/'vcruntime140.dll'), 'BINARY'),
        ('msvcp140.dll', str(python/'msvcp140.dll'), 'BINARY'),
        ('libcrypto-3.dll', str(python/'libcrypto-3.dll'), 'BINARY'),
        ('PySide6/Qt6Pdf.dll', str(python/'Qt6Pdf.dll'), 'BINARY'),
    ]
    assert filter_windows_binaries(items, [python]) == items[4:]


def test_unknown_dll_from_unrelated_application_stops_build(tmp_path):
    item = ('unknown.dll', str(tmp_path/'external/unknown.dll'), 'BINARY')
    with pytest.raises(ValueError, match='DLL fora'):
        filter_windows_binaries([item], [tmp_path/'python'])


def test_unsupported_windows_stops_before_loading_qt(monkeypatch):
    from tilt import __main__
    monkeypatch.setattr(__main__, 'require_supported_windows', lambda: False)
    assert __main__.main() == 1


def test_installer_uses_real_registry_build_instead_of_legacy_versionnt():
    # Windows Installer may report VersionNT=603 on both Windows 10 and 11.
    source = (Path(__file__).resolve().parents[1]/'installer/Product.wxs').read_text(encoding='utf-8')
    assert 'Name="CurrentBuildNumber"' in source
    assert 'EFTX_WINDOWS_BUILD &gt;= 17763' in source
    assert 'VersionNT &gt;= 1000' not in source
