"""Keep Windows packages independent of native DLLs from the builder's PATH."""
import os
from pathlib import Path
import sys

UNUSED_QT = {
    'qtvirtualkeyboardplugin.dll', 'qt6virtualkeyboard.dll', 'qt6quick.dll',
    'qt6qml.dll', 'qt6qmlmeta.dll', 'qt6qmlmodels.dll', 'qt6qmlworkerscript.dll',
    'qt6opengl.dll', 'qopensslbackend.dll', 'libssl-3-x64.dll', 'libcrypto-3-x64.dll',
}


def excluded_windows_dll(name):
    name = name.replace('\\', '/').rsplit('/', 1)[-1].casefold()
    return (name in UNUSED_QT or name in {'ucrtbase.dll', 'icuuc.dll'}
            or name.startswith(('api-ms-win-', 'ext-ms-win-', 'icudt')))


def configure_build_path():
    """Only this Python and Windows may supply dependencies to the build."""
    windows = Path(os.environ['WINDIR'])
    roots = [Path(sys.prefix), Path(sys.base_prefix), windows]
    os.environ['PATH'] = os.pathsep.join(str(p) for p in (
        roots[0]/'Scripts', roots[1], roots[1]/'DLLs', windows/'System32', windows))
    return roots


def filter_windows_binaries(binaries, allowed_roots):
    allowed_roots = [Path(p).resolve() for p in allowed_roots]
    result = []
    for entry in binaries:
        if excluded_windows_dll(entry[0]):
            continue
        source = Path(entry[1]).resolve()
        if not any(source.is_relative_to(root) for root in allowed_roots):
            raise ValueError('DLL fora do Python/Qt/Windows autorizado: '+entry[0])
        result.append(entry)
    return result


def consolidate_msvc(binaries):
    """Put one newest bundled copy of each CRT DLL in the bootstrap directory."""
    import pefile
    groups = {}
    result = []
    for entry in binaries:
        name = Path(entry[0]).name.casefold()
        if name.startswith(('vcruntime140', 'msvcp140', 'concrt140')) and name.endswith('.dll'):
            with pefile.PE(entry[1], fast_load=False) as pe:
                info = pe.VS_FIXEDFILEINFO[0]
                version = (info.FileVersionMS, info.FileVersionLS)
            previous = groups.get(name)
            if previous is None or version > previous[0]:
                groups[name] = (version, entry[1])
        else:
            result.append(entry)
    required = {'vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll'}
    if not required.issubset(groups):
        raise ValueError('Runtime Visual C++ incompleto: '+str(sorted(required-groups.keys())))
    result.extend((name, source, 'BINARY') for name, (_, source) in sorted(groups.items()))
    return result
