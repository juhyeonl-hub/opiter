"""XDG-compliant config and cache paths for Opiter.

Honors ``XDG_CONFIG_HOME`` / ``XDG_CACHE_HOME`` when set, falling back
to ``~/.config`` / ``~/.cache`` per the XDG Base Directory Specification.
"""
from __future__ import annotations

import os
from pathlib import Path

_APP = "opiter"


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    path = Path(base) / _APP
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    path = Path(base) / _APP
    path.mkdir(parents=True, exist_ok=True)
    return path


def preferences_path() -> Path:
    return config_dir() / "preferences.json"
