# -*- coding: utf-8 -*-
"""Update checking via GitHub Releases.

Checks the latest release of a GitHub repo, compares its tag with the running
version, and (if newer) downloads the Setup .exe asset so the caller can launch
the installer wizard.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request

from . import __version__

# Override via settings key "update_repo" if your repo name differs.
DEFAULT_REPO = "Himare4092/File-Extension-Converter"

_UA = {"User-Agent": "FileExtensionConverter-Updater"}


class UpdateError(Exception):
    pass


def get_repo(settings_dict: dict | None) -> str:
    if settings_dict:
        r = (settings_dict.get("update_repo") or "").strip()
        if r:
            return r
    return DEFAULT_REPO


def _parse_version(v: str) -> tuple:
    v = (v or "").strip().lstrip("vV")
    parts = []
    for chunk in v.replace("-", ".").replace("_", ".").split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) or (0,)


def is_newer(remote_tag: str, local: str = __version__) -> bool:
    return _parse_version(remote_tag) > _parse_version(local)


def check(repo: str) -> tuple[str, str | None, str | None]:
    """Return (latest_tag, installer_exe_url, release_html_url).

    Uses the releases *list* endpoint (not /releases/latest) so that
    pre-releases are considered too, then picks the highest version tag.
    Raises UpdateError with a localized message on failure."""
    url = f"https://api.github.com/repos/{repo}/releases?per_page=30"
    req = urllib.request.Request(
        url, headers={**_UA, "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise UpdateError("公開されているリリースが見つかりませんでした。") from e
        raise UpdateError(f"サーバーエラー (HTTP {e.code}) が発生しました。") from e
    except urllib.error.URLError as e:
        raise UpdateError("ネットワークに接続できませんでした。") from e
    except Exception as e:  # noqa
        raise UpdateError(f"アップデート確認に失敗しました: {e}") from e

    releases = [r for r in data if isinstance(r, dict) and not r.get("draft")]
    if not releases:
        raise UpdateError("公開されているリリースが見つかりませんでした。")

    best = max(releases, key=lambda r: _parse_version(r.get("tag_name") or ""))
    tag = best.get("tag_name") or best.get("name") or ""
    asset_url = None
    for a in best.get("assets", []):
        if a.get("name", "").lower().endswith(".exe"):
            asset_url = a.get("browser_download_url")
            break
    return tag, asset_url, best.get("html_url")


def download(url: str, dest_dir: str | None = None) -> str:
    dest_dir = dest_dir or tempfile.mkdtemp(prefix="fec_update_")
    name = url.split("/")[-1] or "Setup.exe"
    out = os.path.join(dest_dir, name)
    req = urllib.request.Request(url, headers=_UA)
    try:
        with urllib.request.urlopen(req, timeout=120) as r, open(out, "wb") as f:
            shutil.copyfileobj(r, f)
    except Exception as e:  # noqa
        raise UpdateError(f"ダウンロードに失敗しました: {e}") from e
    return out


def launch_installer(path: str) -> None:
    """Start the installer wizard (interactive) and detach."""
    subprocess.Popen([path], close_fds=True)
