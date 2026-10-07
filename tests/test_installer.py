import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from tools.prepare_installer import create_fragment, rtf


def test_payload_inventory_and_component_identity_survive_version_changes(tmp_path):
    payload = tmp_path/'app'
    payload.mkdir()
    (payload/'EFTX_Tilt.exe').write_bytes(b'fixture executable')
    (payload/'_internal').mkdir()
    lib = payload/'_internal/runtime.dll'
    lib.write_bytes(b'first version')
    out = tmp_path/'wix'
    out.mkdir()
    first = create_fragment(payload, out)
    xml = (out/'Payload.wxs').read_text(encoding='utf-8')
    lib.write_bytes(b'next version')
    second = create_fragment(payload, out)
    assert xml == (out/'Payload.wxs').read_text(encoding='utf-8')
    before = {item['path']: item['sha256'] for item in first}
    after = {item['path']: item['sha256'] for item in second}
    assert before['_internal/runtime.dll'] != after['_internal/runtime.dll']
    assert before['EFTX_Tilt.exe'] == after['EFTX_Tilt.exe']
    tree = ET.parse(out/'Payload.wxs')
    ns = {'w': 'http://wixtoolset.org/schemas/v4/wxs'}
    assert all(r.attrib['Root'] == 'HKCU' for r in tree.findall('.//w:RegistryValue', ns))
    assert not tree.findall('.//w:RemoveFile', ns)


@pytest.mark.parametrize('name', ['tilt.sqlite3','tilt.sqlite3-wal','.env','Qt6VirtualKeyboard.dll','qtvirtualkeyboardplugin.dll'])
def test_payload_rejects_private_data_and_unused_gpl_plugin(tmp_path, name):
    (tmp_path/'EFTX_Tilt.exe').write_bytes(b'exe')
    (tmp_path/name).write_bytes(b'must not ship')
    with pytest.raises(ValueError):
        create_fragment(tmp_path, tmp_path)


def test_license_rtf_preserves_accents_and_escapes_markup():
    value = rtf('Licença {EFTX} \\ teste\nAutorizações')
    assert r'\u231?' in value and r'\u245?' in value
    assert r'\{EFTX\}' in value and r'\\ teste' in value and r'\par' in value
    value.encode('ascii')


def test_installer_has_explicit_silent_acceptance_and_preserves_database_location():
    root = Path(__file__).resolve().parents[1]
    source = (root/'installer/Product.wxs').read_text(encoding='utf-8')
    assert 'Scope="perUser"' in source
    assert 'EFTX_ACCEPT_LICENSE = &quot;1&quot;' in source
    assert 'WixUILicenseRtf' in source
    assert 'Advertise="yes"' not in source
    assert 'RemoveFile' not in source and 'tilt.sqlite3' not in source
    manifest = json.loads((root/'dotnet-tools.json').read_text(encoding='utf-8'))
    assert manifest['tools']['wix']['version'] == '5.0.2'
