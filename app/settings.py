import json
import os
from pathlib import Path

APP_NAME = "yt-dlp-YYY"

DEFAULTS = {
    "output_dir": str(Path.home() / "Downloads" / APP_NAME),
    "kind": "映像+音声",
    "quality": "最高品質",
    "container": "mp4",
    "appearance": "ダーク",
    "show_log": False,
    "auto_open_folder": True,
    "auto_copy_clipboard": True,
    "play_complete_sound": True,
}


def app_data_dir() -> Path:
    appdata = os.environ.get("APPDATA", str(Path.home()))
    return Path(appdata) / APP_NAME


def _settings_path() -> Path:
    return app_data_dir() / "settings.json"


def load_settings() -> dict:
    path = _settings_path()
    if not path.exists():
        return dict(DEFAULTS)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)
    merged = dict(DEFAULTS)
    merged.update(data)
    return merged


def save_settings(settings: dict) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
