"""Use the verified payload to create explicit NSIS copy/removal lists."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tilt import __version__
from tools.prepare_installer import prepare, create_fragment


def nsis_escape(value):
    return value.replace('$', '$$').replace('"', '$\\"')


def generate_lists(payload, output):
    inventory = create_fragment(payload, output)
    install, uninstall, dirs = [], [], set()
    for item in inventory:
        relative = Path(item['path'])
        name = nsis_escape(str(relative))
        parent = nsis_escape(str(relative.parent))
        install.extend(['ClearErrors', f'SetOutPath "$INSTDIR\\{parent}"',
                        f'File "${{PAYLOAD}}\\{name}"', 'IfErrors install_failed'])
        uninstall.extend([f'Delete "$INSTDIR\\{name}"',
                          f'IfFileExists "$INSTDIR\\{name}" uninstall_failed'])
        dirs.update(p for p in relative.parents if str(p) != '.')
    uninstall.extend(f'RMDir "$INSTDIR\\{nsis_escape(str(p))}"' for p in sorted(dirs, key=lambda p: (-len(p.parts), str(p))))
    (output/'InstallFiles.nsh').write_text('\n'.join(install)+'\n', encoding='utf-8-sig')
    (output/'UninstallFiles.nsh').write_text('\n'.join(uninstall)+'\n', encoding='utf-8-sig')


if __name__ == '__main__':
    payload = ROOT/'dist/release'/__version__/'EFTX_Tilt'
    output = ROOT/'build/installer'/__version__
    prepare(payload, output)
    generate_lists(payload, output)
