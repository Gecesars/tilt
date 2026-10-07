# Build with: .venv\Scripts\python -m PyInstaller EFTX_Tilt.spec
from PyInstaller.utils.hooks import collect_data_files
import os
import sys
sys.path.insert(0, SPECPATH)
from tools.windows_package import configure_build_path, filter_windows_binaries, consolidate_msvc

allowed_roots = configure_build_path() if os.name == 'nt' else []

a = Analysis(['main.py'], pathex=[], binaries=[], datas=collect_data_files('tilt'),
             hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['pytest', 'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtWebEngineCore'],
             noarchive=False, optimize=0)
# Windows 10 supplies UCRT, API sets and ICU. Do not ship builder-specific
# copies, unrelated PATH dependencies, or unused Qt Virtual Keyboard/OpenSSL.
if os.name == 'nt':
    a.binaries = filter_windows_binaries(a.binaries, allowed_roots)
    a.binaries = consolidate_msvc(a.binaries)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='EFTX_Tilt', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=os.environ.get('EFTX_BUILD_CONSOLE') == '1',
          icon='tilt/assets/eftx_logo.jpeg')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='EFTX_Tilt')
