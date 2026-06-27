# -*- coding: utf-8 -*-
"""Detection of optional external engines / Python libraries.

The converter routes many formats to external programs (ffmpeg, LibreOffice,
Ghostscript, Calibre, ...) or optional Python packages.  This module locates
them and lets the rest of the app give clear, localized messages when an engine
is missing instead of crashing.
"""
from __future__ import annotations

import os
import shutil
import importlib.util
from functools import lru_cache


class ToolMissing(Exception):
    """Raised when an external engine or library required for a conversion
    is not available.  ``message`` is shown to the user (Japanese)."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


# ---- external executables -------------------------------------------------

# Common install locations that may not be on PATH (Windows-friendly).
_EXTRA_DIRS = [
    r"C:\Program Files\LibreOffice\program",
    r"C:\Program Files (x86)\LibreOffice\program",
    r"C:\Program Files\Calibre2",
    r"C:\Program Files\Calibre",
    r"C:\Program Files\gs",
    r"C:\Program Files\Inkscape\bin",
    r"C:\ffmpeg\bin",
    os.path.join(os.path.expanduser("~"), "scoop", "shims"),
]


def _which(*names: str) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    for d in _EXTRA_DIRS:
        if not os.path.isdir(d):
            continue
        for name in names:
            for ext in ("", ".exe", ".com", ".bat"):
                cand = os.path.join(d, name + ext)
                if os.path.isfile(cand):
                    return cand
    # Ghostscript on Windows ships as gswin64c / gswin32c under gs\gsX.Y\bin
    return None


@lru_cache(maxsize=None)
def ffmpeg() -> str | None:
    return _which("ffmpeg")


@lru_cache(maxsize=None)
def ffprobe() -> str | None:
    return _which("ffprobe")


@lru_cache(maxsize=None)
def soffice() -> str | None:
    return _which("soffice", "soffice.bin")


@lru_cache(maxsize=None)
def ghostscript() -> str | None:
    return _which("gswin64c", "gswin32c", "gs")


@lru_cache(maxsize=None)
def calibre() -> str | None:
    return _which("ebook-convert")


@lru_cache(maxsize=None)
def inkscape() -> str | None:
    return _which("inkscape")


@lru_cache(maxsize=None)
def imagemagick() -> str | None:
    return _which("magick", "convert")


def require_exe(getter, label: str, install_hint: str) -> str:
    path = getter()
    if not path:
        raise ToolMissing(
            f"この変換には外部エンジン「{label}」が必要ですが、見つかりませんでした。\n"
            f"インストール方法: {install_hint}"
        )
    return path


# ---- optional python libraries -------------------------------------------

def have_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def require_module(name: str, pip_name: str | None = None):
    if not have_module(name):
        pip_name = pip_name or name
        raise ToolMissing(
            f"この変換には Python ライブラリ「{pip_name}」が必要です。\n"
            f"インストール: pip install {pip_name}"
        )
    import importlib
    return importlib.import_module(name)
