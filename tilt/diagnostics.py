"""Opt-in local diagnostic report for frozen-package verification."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import platform
import sys


def loaded_windows_modules():
    if sys.platform != 'win32':
        return []
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.K32EnumProcessModules.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    kernel.K32GetModuleFileNameExW.argtypes = [wintypes.HANDLE, wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
    process = kernel.GetCurrentProcess()
    modules = (wintypes.HMODULE * 2048)()
    needed = wintypes.DWORD()
    if not kernel.K32EnumProcessModules(process, modules, ctypes.sizeof(modules), ctypes.byref(needed)):
        raise ctypes.WinError(ctypes.get_last_error())
    if needed.value > ctypes.sizeof(modules):
        raise RuntimeError('Inventário de DLLs excedeu o limite.')
    paths = []
    for module in modules[:needed.value // ctypes.sizeof(wintypes.HMODULE)]:
        path = ctypes.create_unicode_buffer(32768)
        if not kernel.K32GetModuleFileNameExW(process, module, path, len(path)):
            raise ctypes.WinError(ctypes.get_last_error())
        paths.append(path.value)
    return sorted(set(paths), key=str.casefold)


def is_packaged_runtime(name):
    return name.casefold().startswith(('vcruntime14', 'msvcp14', 'concrt14', 'python3',
                                      'qt6', 'pyside6', 'shiboken', 'sqlite3', 'libcrypto', 'libssl', 'libffi'))


def write_diagnostics(path):
    from PySide6.QtCore import qVersion
    from . import __version__
    root = Path(sys.executable).parent.resolve()
    modules = loaded_windows_modules()
    runtimes = [p for p in modules if is_packaged_runtime(Path(p).name)]
    outside = [p for p in runtimes if not Path(p).resolve().is_relative_to(root)] if getattr(sys, 'frozen', False) else []
    report = {'application': __version__, 'os': platform.platform(), 'python': platform.python_version(),
              'qt': qVersion(), 'frozen': bool(getattr(sys, 'frozen', False)),
              'runtime_modules': runtimes, 'external_runtime_modules': outside,
              'loaded_modules': modules, 'path': os.environ.get('PATH', '')}
    Path(path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    return not outside
