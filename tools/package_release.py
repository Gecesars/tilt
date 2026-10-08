"""Verify MSI/bridge payload, package the portable app and write release hashes."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tilt import __version__


def main():
    dist = ROOT/'dist'
    payload = dist/'release'/__version__/'EFTX_Tilt'
    setup = dist/f'EFTX_Tilt-{__version__}-Setup-x64.exe'
    msi = dist/f'EFTX_Tilt-{__version__}-Windows-x64.msi'
    if not setup.is_file() or not msi.is_file():
        raise FileNotFoundError('Gere o MSI e o EXE auxiliar antes de preparar a release.')
    inventory = json.loads((ROOT/'build/installer'/__version__/'payload-manifest.json').read_text(encoding='utf-8'))
    expected = {item['path']: item['sha256'] for item in inventory['files']}
    actual = {p.relative_to(payload).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in payload.rglob('*') if p.is_file()}
    if actual != expected:
        raise ValueError('Payload mudou após gerar o instalador. Recompile antes de publicar.')
    archive = dist/f'EFTX_Tilt-{__version__}-Windows-x64.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as writer:
        for relative in sorted(expected):
            writer.write(payload/relative, 'EFTX_Tilt/'+relative)
    with zipfile.ZipFile(archive) as reader:
        if reader.testzip():
            raise ValueError('CRC inválido no ZIP.')
        for relative, digest in expected.items():
            if hashlib.sha256(reader.read('EFTX_Tilt/'+relative)).hexdigest() != digest:
                raise ValueError('Hash inválido no ZIP: '+relative)
    for name in ('LICENSE.txt', 'THIRD_PARTY_NOTICES.md'):
        shutil.copy2(ROOT/name, dist/name)
    artifacts = [msi, setup, archive, dist/'LICENSE.txt', dist/'THIRD_PARTY_NOTICES.md']
    checksums = ''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in artifacts)
    (dist/'SHA256SUMS.txt').write_text(checksums, encoding='ascii')
    print(json.dumps({'version': __version__, 'verified_files': len(expected),
                      'artifacts': {p.name: p.stat().st_size for p in artifacts}}, indent=2))


if __name__ == '__main__':
    main()
