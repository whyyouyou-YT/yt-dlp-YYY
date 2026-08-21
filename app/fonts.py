import ctypes
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FONT_FAMILY = "Noto Sans JP"

_FR_PRIVATE = 0x10


def get_fonts_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "assets" / "fonts"
    return PROJECT_ROOT / "assets" / "fonts"


def load_custom_fonts() -> None:
    if sys.platform != "win32":
        return
    fonts_dir = get_fonts_dir()
    for filename in ("NotoSansJP-Regular.ttf", "NotoSansJP-Bold.ttf"):
        font_path = fonts_dir / filename
        if font_path.exists():
            ctypes.windll.gdi32.AddFontResourceExW(str(font_path), _FR_PRIVATE, 0)
