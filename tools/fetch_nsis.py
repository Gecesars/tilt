"""Fetch pinned portable NSIS; no compiler installation or registry changes."""
import hashlib
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '3.12'
SHA256 = '56581f90db321581c5381193d796fffcf2d24b2f8fed2160a6c6a3baa67f2c4f'
URLS = (
    'https://downloads.sourceforge.net/project/nsis/NSIS%203/3.12/nsis-3.12.zip',
    'https://distfiles.macports.org/nsis/nsis-3.12.zip',
)


def main():
    folder = ROOT/'build/tools'
    folder.mkdir(parents=True, exist_ok=True)
    archive = folder/f'nsis-{VERSION}.zip'
    if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        for url in URLS:
            try:
                with urllib.request.urlopen(url, timeout=45) as response:
                    data = response.read()
                if hashlib.sha256(data).hexdigest() != SHA256:
                    continue
                archive.write_bytes(data)
                break
            except OSError:
                continue
        else:
            raise RuntimeError('Não foi possível obter NSIS com o SHA-256 fixado.')
    with zipfile.ZipFile(archive) as reader:
        for item in reader.infolist():
            if not (folder/item.filename).resolve().is_relative_to(folder.resolve()):
                raise ValueError('Caminho inválido no arquivo NSIS.')
        reader.extractall(folder)
    print(folder/f'nsis-{VERSION}'/'makensis.exe')


if __name__ == '__main__':
    main()
