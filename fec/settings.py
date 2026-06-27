# -*- coding: utf-8 -*-
"""User settings persistence (JSON under %APPDATA%\\FileExtensionConverter)."""
from __future__ import annotations

import json
import os

_BASE = os.environ.get("APPDATA") or os.path.expanduser("~")
APP_DIR = os.path.join(_BASE, "FileExtensionConverter")
SETTINGS_PATH = os.path.join(APP_DIR, "settings.json")

# theme: "system" (Windows default) | "white" | "amoled"
DEFAULTS = {
    "theme": "system",
    "ask_every_time": True,
    "default_save_dir": "",
    "update_repo": "",  # GitHub owner/repo; blank = updater.DEFAULT_REPO
}


def load() -> dict:
    data = dict(DEFAULTS)
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            data.update({k: loaded[k] for k in DEFAULTS if k in loaded})
    except Exception:
        pass
    return data


def save(data: dict) -> None:
    os.makedirs(APP_DIR, exist_ok=True)
    clean = {k: data.get(k, DEFAULTS[k]) for k in DEFAULTS}
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)
