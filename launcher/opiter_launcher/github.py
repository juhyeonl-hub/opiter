# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Tiny GitHub Releases API client used by the launcher.

We only need: list latest release + find a named asset's browser URL.
Plain ``urllib`` is fine here — no extra dependencies, keeps the
launcher binary as small as possible.
"""
from __future__ import annotations

import json
# Explicit ``ssl`` import so PyInstaller's static-analysis dependency
# walk sees it; without this the bundled .exe fails on https with
# "unknown url type: https" because urllib lazy-imports ssl only when
# it actually needs to open a TLS connection.
import ssl  # noqa: F401
import urllib.request
from dataclasses import dataclass

_REPO = "juhyeonl-hub/opiter"
_API = f"https://api.github.com/repos/{_REPO}/releases/latest"


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    url: str       # browser_download_url — works without auth
    size: int      # bytes


@dataclass(frozen=True)
class Release:
    tag: str       # e.g. "v0.1.10"
    assets: list[ReleaseAsset]

    def asset(self, name: str) -> ReleaseAsset | None:
        for a in self.assets:
            if a.name == name:
                return a
        return None


def fetch_latest_release(timeout_sec: float = 10.0) -> Release:
    """Return the most recent published release of the Opiter repo."""
    req = urllib.request.Request(
        _API,
        headers={
            "User-Agent": "Opiter-Launcher",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        data = json.load(resp)
    assets = [
        ReleaseAsset(
            name=a["name"],
            url=a["browser_download_url"],
            size=int(a.get("size", 0)),
        )
        for a in data.get("assets", [])
    ]
    return Release(tag=data["tag_name"], assets=assets)
