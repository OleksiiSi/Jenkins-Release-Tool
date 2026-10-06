import json

from core.config import SETTINGS_DEFAULT_PATH, SETTINGS_PATH


def load_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return reset_to_defaults()

    return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))


def save_settings(data: dict) -> None:
    SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def reset_to_defaults() -> dict:
    defaults = json.loads(SETTINGS_DEFAULT_PATH.read_text(encoding="utf-8"))
    save_settings(defaults)

    return defaults
