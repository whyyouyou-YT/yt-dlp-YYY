import json
from pathlib import Path

from app.settings import app_data_dir

MAX_ENTRIES = 200


def _history_path() -> Path:
    return app_data_dir() / "history.json"


def load_history() -> list:
    path = _history_path()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    return data if isinstance(data, list) else []


def add_history_entry(entry: dict) -> None:
    history = load_history()
    history.insert(0, entry)
    del history[MAX_ENTRIES:]
    path = _history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def clear_history() -> None:
    path = _history_path()
    if path.exists():
        path.unlink()
