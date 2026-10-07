# Build with: .venv\Scripts\python -m PyInstaller EFTX_Tilt.spec
from PyInstaller.utils.hooks import collect_data_files
import os

a = Analysis(['main.py'], pathex=[], binaries=[], datas=collect_data_files('tilt'),
             hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['pytest', 'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtWebEngineCore'],
             noarchive=False, optimize=0)
# Qt 6.11 uses Windows' ICU API (unversioned symbols). A third-party ICU on
# PATH (e.g. Poppler's ICU 78) has different exports and must not shadow it.
if os.name == 'nt':
    a.binaries = [entry for entry in a.binaries
                  if not (os.path.basename(entry[0]).lower() == 'icuuc.dll'
                          or os.path.basename(entry[0]).lower().startswith('icudt'))]
# The desktop uses physical keyboard input, not Qt Virtual Keyboard (GPL-only).
# Do not ship an unused optional plugin or the Qt Quick chain it pulls in.
unused_qt = {'qtvirtualkeyboardplugin.dll', 'qt6virtualkeyboard.dll', 'qt6quick.dll',
             'qt6qml.dll', 'qt6qmlmeta.dll', 'qt6qmlmodels.dll', 'qt6qmlworkerscript.dll', 'qt6opengl.dll'}
a.binaries = [entry for entry in a.binaries if os.path.basename(entry[0]).lower() not in unused_qt]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='EFTX_Tilt', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=os.environ.get('EFTX_BUILD_CONSOLE') == '1',
          icon='tilt/assets/eftx_logo.jpeg')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='EFTX_Tilt')
