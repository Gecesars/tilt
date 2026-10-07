"""Maintainer-only refresh of verbatim upstream license texts and attribution pages."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'licenses'
BASE = 'https://doc.qt.io/qt-6.11/'


def fetch(url):
    with urllib.request.urlopen(url, timeout=45) as response:
        return response.read()


class Description(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth, self.parts = 0, []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'div':
            if self.depth:
                self.depth += 1
            elif attrs.get('class') == 'descr':
                self.depth = 1
        if self.depth and tag in ('p', 'br', 'pre', 'h1', 'h2', 'h3', 'li', 'tr'):
            self.parts.append('\n')
        if self.depth and tag == 'a' and attrs.get('href','').startswith('https://'):
            self.parts.append(' ['+attrs['href']+'] ')
    def handle_endtag(self, tag):
        if tag == 'div' and self.depth:
            self.depth -= 1
        if self.depth and tag in ('p','pre','li','h1','h2','h3','tr'):
            self.parts.append('\n')
    def handle_data(self, data):
        if self.depth:
            self.parts.append(data)


def main():
    OUT.mkdir(exist_ok=True)
    (OUT/'qt-attributions').mkdir(exist_ok=True)
    index = fetch(BASE+'licenses-used-in-qt.html').decode()
    pages = set()
    for module in ('qt-core','qt-gui','qt-network','qt-image-formats','qt-svg','qt-pdf'):
        section = re.search(r'<h2[^>]*id="'+module+r'".*?(?=<h2|</div>)', index, re.S)
        if not section:
            raise ValueError('Seção ausente: '+module)
        pages.update(h for h in re.findall(r'href="([^"]+)"', section.group()) if h.endswith('.html'))
    def attribution(page):
        parser = Description()
        parser.feed(fetch(BASE+page).decode())
        text = ''.join(parser.parts).strip()
        if len(text) < 100:
            raise ValueError('Aviso incompleto: '+page)
        return 'qt-attributions/'+page.replace('.html','.txt'), BASE+page, ('Fonte: '+BASE+page+'\n\n'+text+'\n').encode()
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(attribution, sorted(pages)))
    sources = {
        'LGPL-3.0.txt': 'https://raw.githubusercontent.com/qt/qtbase/v6.11.2/LICENSES/LGPL-3.0-only.txt',
        'GPL-3.0.txt': 'https://raw.githubusercontent.com/qt/qtbase/v6.11.2/LICENSES/GPL-3.0-only.txt',
        'WiX-MS-RL.txt': 'https://raw.githubusercontent.com/wixtoolset/wix/v5.0.2/LICENSE.TXT',
        'OpenSSL-Apache-2.0.txt': 'https://raw.githubusercontent.com/openssl/openssl/openssl-3.0.16/LICENSE.txt',
        'OpenSSL-3.6.4-Apache-2.0.txt': 'https://raw.githubusercontent.com/openssl/openssl/openssl-3.6.4/LICENSE.txt',
    }
    for name, url in sources.items():
        results.append((name, url, fetch(url)))
    local = {
        'Python-3.12.10.txt': Path(sys.base_prefix)/'LICENSE.txt',
        'PyInstaller-bootloader.txt': ROOT/'.venv/Lib/site-packages/pyinstaller-6.22.3.dist-info/licenses/COPYING.txt',
    }
    for name, path in local.items():
        results.append((name, 'installed distribution: '+path.name, path.read_bytes()))
    # NSIS is pinned independently from the Python/Qt environment.
    nsis_notice = (OUT/'NSIS-COPYING.txt').read_bytes()
    if hashlib.sha256(nsis_notice).hexdigest() != '388357c1215ff403c5ebde3a5ecd273e68f8b79a579996775245d1ee65442aba':
        raise ValueError('Revisar aviso NSIS e hash ao alterar a versão do compilador.')
    results.append(('NSIS-COPYING.txt',
                    'https://sourceforge.net/projects/nsis/files/NSIS%203/3.12/nsis-3.12.zip/download',
                    nsis_notice))
    manifest = []
    for name, url, data in results:
        (OUT/name).write_bytes(data)
        manifest.append({'file':name,'source':url,'sha256':hashlib.sha256(data).hexdigest()})
    (OUT/'manifest.json').write_text(json.dumps({'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'notices':manifest}, indent=2), encoding='utf-8')
    print(f'{len(results)} avisos/licenças copiados; origens e SHA-256 registrados.')


if __name__ == '__main__':
    main()
