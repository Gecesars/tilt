"""Check the documented Qt Windows baseline before importing any Qt DLL."""
import struct
import sys

MIN_WINDOWS_BUILD = 17763  # Windows 10 version 1809, Qt 6.11 minimum.
WINDOWS_REQUIREMENT = 'Windows 10 versão 1809 ou posterior (64 bits), ou Windows 11 (64 bits).'


def supports_windows(version, pointer_bits):
    return pointer_bits == 64 and tuple(version) >= (10, 0, MIN_WINDOWS_BUILD)


def require_supported_windows():
    if sys.platform != 'win32':
        return True
    version = sys.getwindowsversion().platform_version
    if supports_windows(version, struct.calcsize('P') * 8):
        return True
    import ctypes
    ctypes.windll.user32.MessageBoxW(
        None, 'Este aplicativo requer '+WINDOWS_REQUIREMENT,
        'EFTX Tilt — Windows incompatível', 0x10)
    return False
