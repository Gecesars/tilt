"""Create deterministic WiX file components and installer resources from a frozen payload."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tilt import __version__
from tools.windows_package import excluded_windows_dll

NS = 'http://wixtoolset.org/schemas/v4/wxs'
COMPONENT_NAMESPACE = uuid.UUID('99dce0e3-0ed2-485f-8d4f-1aef9de9b7d0')


def stable_id(prefix, relative):
    return prefix + hashlib.sha256(relative.casefold().encode()).hexdigest()[:28]


def rtf(text):
    escaped = []
    for char in text:
        if char in '{}\\':
            escaped.append('\\'+char)
        elif char == '\n':
            escaped.append('\\par\n')
        elif ord(char) > 127:
            value = ord(char)
            escaped.append(f'\\u{value if value < 32768 else value-65536}?')
        else:
            escaped.append(char)
    return r'{\rtf1\ansi\ansicpg1252\deff0{\fonttbl{\f0 Segoe UI;}}\viewkind4\uc1\pard\f0\fs18 ' + ''.join(escaped) + '}'


def create_fragment(payload, output):
    payload = Path(payload).resolve()
    files = sorted(p for p in payload.rglob('*') if p.is_file())
    if not (payload/'EFTX_Tilt.exe').is_file() or not files:
        raise ValueError('Payload sem EFTX_Tilt.exe.')
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(payload):
            raise ValueError('Arquivo fora do payload: '+str(path))
        if excluded_windows_dll(path.name) or path.name.casefold() == '.env' or '.sqlite' in path.name.casefold():
            raise ValueError('Arquivo não distribuível no payload: '+str(path))
    ET.register_namespace('', NS)
    root = ET.Element(f'{{{NS}}}Wix')
    fragment = ET.SubElement(root, 'Fragment')
    directory_ref = ET.SubElement(fragment, 'DirectoryRef', Id='INSTALLFOLDER')
    directories = {'.': directory_ref}
    for path in files:
        relative = path.relative_to(payload)
        current = Path('.')
        for part in relative.parts[:-1]:
            parent = current.as_posix()
            current /= part
            key = current.as_posix()
            if key not in directories:
                directories[key] = ET.SubElement(directories[parent], 'Directory', Id=stable_id('dir', key), Name=part)
    group = ET.SubElement(fragment, 'ComponentGroup', Id='PayloadFiles')
    inventory = []
    for path in files:
        relative = path.relative_to(payload).as_posix()
        parent = path.relative_to(payload).parent.as_posix()
        directory_id = 'INSTALLFOLDER' if parent == '.' else stable_id('dir', parent)
        component_id = stable_id('cmp', relative)
        component = ET.SubElement(group, 'Component', Id=component_id, Directory=directory_id,
                                  Guid=str(uuid.uuid5(COMPONENT_NAMESPACE, relative.casefold())))
        ET.SubElement(component, 'File', Id=stable_id('file', relative),
                      Source='$(var.PayloadDir)\\'+relative.replace('/', '\\'))
        ET.SubElement(component, 'RegistryValue', Root='HKCU', Key='Software\\EFTX\\Tilt\\Components',
                      Name=component_id, Type='integer', Value='1', KeyPath='yes')
        inventory.append({'path': relative, 'bytes': path.stat().st_size,
                          'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    for relative in directories:
        if relative == '.':
            continue
        directory_id = stable_id('dir', relative)
        component = ET.SubElement(group, 'Component', Id=stable_id('clean', relative), Directory=directory_id,
                                  Guid=str(uuid.uuid5(COMPONENT_NAMESPACE, 'directory:'+relative.casefold())))
        ET.SubElement(component, 'RemoveFolder', Id=stable_id('remove', relative), Directory=directory_id, On='uninstall')
        ET.SubElement(component, 'RegistryValue', Root='HKCU', Key='Software\\EFTX\\Tilt\\Directories',
                      Name=directory_id, Type='integer', Value='1', KeyPath='yes')
    ET.indent(root)
    ET.ElementTree(root).write(output/'Payload.wxs', encoding='utf-8', xml_declaration=True)
    (output/'payload-manifest.json').write_text(json.dumps({'version': __version__, 'files': inventory}, indent=2), encoding='utf-8')
    return inventory


def prepare(payload, output):
    from PIL import Image, ImageOps
    payload, output = Path(payload).resolve(), Path(output).resolve()
    if not payload.is_relative_to(ROOT/'dist') or not output.is_relative_to(ROOT/'build'):
        raise ValueError('Use dist/ para payload e build/ para recursos do instalador.')
    output.mkdir(parents=True, exist_ok=True)
    for name in ('LICENSE.txt', 'THIRD_PARTY_NOTICES.md'):
        shutil.copy2(ROOT/name, payload/name)
    shutil.copytree(ROOT/'licenses', payload/'licenses', dirs_exist_ok=True)
    text = (ROOT/'LICENSE.txt').read_text(encoding='utf-8')
    (output/'license.rtf').write_text(rtf(text), encoding='ascii')
    logo = Image.open(ROOT/'tilt/assets/eftx_logo.jpeg').convert('RGB')
    icon = Image.new('RGB', (256,256), 'white')
    mark = ImageOps.contain(logo, (240, 210))
    icon.paste(mark, ((256-mark.width)//2, (256-mark.height)//2))
    icon.save(output/'eftx.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    banner = Image.new('RGB', (493,58), 'white')
    mark = ImageOps.contain(logo, (80,54))
    banner.paste(mark, (493-mark.width-5, (58-mark.height)//2))
    banner.save(output/'banner.bmp')
    dialog = Image.new('RGB', (493,312), 'white')
    dialog.paste('#0b2f75', (0,0,151,312))
    mark = ImageOps.contain(logo, (139,110))
    dialog.paste(mark, (6,45))
    dialog.save(output/'dialog.bmp')
    inventory = create_fragment(payload, output)
    code = str(uuid.uuid5(COMPONENT_NAMESPACE, 'product:'+__version__))
    (output/'product-code.txt').write_text(code, encoding='ascii')
    print(f'WiX: {len(inventory)} arquivos; produto {code}; versão {__version__}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('payload', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    prepare(args.payload, args.output)
