# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Per-platform install locations for the launcher.

Windows  : %LOCALAPPDATA%\\Opiter\\        (no admin required)
macOS    : ~/Applications/Opiter/          (per-user, no admin)
Linux    : ~/.local/share/Opiter/          (XDG; .deb still preferred)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def install_dir() -> Path:
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or str(
            Path.home() / "AppData" / "Local"
        )
        d = Path(base) / "Opiter"
    elif sys.platform == "darwin":
        d = Path.home() / "Applications" / "Opiter"
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(
            Path.home() / ".local" / "share"
        )
        d = Path(base) / "Opiter"
    d.mkdir(parents=True, exist_ok=True)
    return d


def main_executable_path() -> Path:
    """Where the launcher will write the downloaded Opiter binary."""
    if sys.platform.startswith("win"):
        return install_dir() / "opiter.exe"
    if sys.platform == "darwin":
        return install_dir() / "Opiter.app"
    return install_dir() / "opiter"


def asset_name_for_current_platform() -> str:
    """Match a GitHub Release asset filename to this OS."""
    if sys.platform.startswith("win"):
        return "opiter-windows-x86_64.exe"
    if sys.platform == "darwin":
        return "opiter-macos-arm64.dmg"
    return "opiter-linux-amd64.deb"


def state_file() -> Path:
    """Tiny JSON file recording the installed Opiter version, so we can
    decide whether to offer an update on subsequent launcher runs."""
    return install_dir() / "launcher-state.json"
