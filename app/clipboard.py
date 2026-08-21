import ctypes
from ctypes import wintypes
from pathlib import Path

GMEM_MOVEABLE = 0x0002
CF_HDROP = 15


class _DROPFILES(ctypes.Structure):
    _fields_ = [
        ("pFiles", wintypes.DWORD),
        ("pt", wintypes.POINT),
        ("fNC", wintypes.BOOL),
        ("fWide", wintypes.BOOL),
    ]


_kernel32 = ctypes.windll.kernel32
_user32 = ctypes.windll.user32

# HGLOBAL/HANDLE is pointer-sized; without explicit restype ctypes assumes a
# 32-bit int and truncates the handle on 64-bit Windows, corrupting it.
_kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
_kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
_kernel32.GlobalLock.restype = ctypes.c_void_p
_kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
_kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
_kernel32.GlobalFree.restype = wintypes.HGLOBAL
_kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
_user32.OpenClipboard.argtypes = [wintypes.HWND]
_user32.SetClipboardData.restype = wintypes.HANDLE
_user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]


def copy_files_to_clipboard(paths: list[str]) -> bool:
    """ファイル群をエクスプローラー/Discord等に貼り付け可能な形でクリップボードにコピーする(CF_HDROP)。"""
    existing = [str(Path(p).resolve()) for p in paths if p and Path(p).exists()]
    if not existing:
        return False

    file_list = "\0".join(existing) + "\0\0"
    file_list_bytes = file_list.encode("utf-16-le")
    offset = ctypes.sizeof(_DROPFILES)
    total_size = offset + len(file_list_bytes)

    h_global = _kernel32.GlobalAlloc(GMEM_MOVEABLE, total_size)
    if not h_global:
        return False
    p_global = _kernel32.GlobalLock(h_global)
    if not p_global:
        _kernel32.GlobalFree(h_global)
        return False
    try:
        dropfiles = _DROPFILES(pFiles=offset, pt=wintypes.POINT(0, 0), fNC=False, fWide=True)
        ctypes.memmove(p_global, ctypes.byref(dropfiles), ctypes.sizeof(dropfiles))
        ctypes.memmove(p_global + offset, file_list_bytes, len(file_list_bytes))
    finally:
        _kernel32.GlobalUnlock(h_global)

    if not _user32.OpenClipboard(0):
        _kernel32.GlobalFree(h_global)
        return False
    try:
        _user32.EmptyClipboard()
        if not _user32.SetClipboardData(CF_HDROP, h_global):
            _kernel32.GlobalFree(h_global)
            return False
    finally:
        _user32.CloseClipboard()
    return True
