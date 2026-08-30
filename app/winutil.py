"""Windows の管理者権限まわりの薄いラッパー（ctypesのみで完結）。"""
from __future__ import annotations

import ctypes
import sys


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin() -> bool:
    """自身を管理者権限で起動し直す。成功したら True（呼び出し元は終了すること）。"""
    if is_admin():
        return False
    params = " ".join(f'"{a}"' for a in sys.argv)
    try:
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1
        )
    except Exception:
        return False
    return int(rc) > 32
