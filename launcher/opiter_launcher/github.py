# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Tiny GitHub Releases API client used by the launcher.

We deliberately use Qt's networking stack
(``QNetworkAccessManager``) instead of ``urllib``: Qt brings its own
SSL implementation as part of PySide6 and does not need Python's
_ssl + OpenSSL DLLs to be bundled into the .exe. The Windows
SmartScreen / Smart App Control heuristics flag generic OpenSSL
bundles as suspicious, so avoiding them keeps the launcher
unblocked while we wait for code-signing.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from PySide6.QtCore import QEventLoop, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

_REPO = "juhyeonl-hub/opiter"
_API = f"https://api.github.com/repos/{_REPO}/releases/latest"


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    url: str       # browser_download_url — works without auth
    size: int      # bytes


@dataclass(frozen=True)
class Release:
    tag: str       # e.g. "v0.1.13"
    assets: list[ReleaseAsset]

    def asset(self, name: str) -> ReleaseAsset | None:
        for a in self.assets:
            if a.name == name:
                return a
        return None


def fetch_latest_release(timeout_sec: float = 15.0) -> Release:
    """Return the most recent published release of the Opiter repo.

    Uses ``QNetworkAccessManager`` synchronously (via a nested
    ``QEventLoop``) — the call returns once the reply has finished or
    the timeout fires. Raises ``RuntimeError`` on any error.
    """
    nam = QNetworkAccessManager()
    request = QNetworkRequest(QUrl(_API))
    request.setHeader(
        QNetworkRequest.KnownHeaders.UserAgentHeader, b"Opiter-Launcher"
    )
    request.setRawHeader(b"Accept", b"application/vnd.github+json")
    request.setAttribute(
        QNetworkRequest.Attribute.RedirectPolicyAttribute,
        QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
    )

    reply = nam.get(request)
    loop = QEventLoop()
    reply.finished.connect(loop.quit)
    # Failsafe timeout — Qt's API has no built-in deadline on a single
    # request, so we drive one ourselves.
    from PySide6.QtCore import QTimer
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(int(timeout_sec * 1000))
    loop.exec()
    timer.stop()

    if not reply.isFinished():
        reply.abort()
        raise RuntimeError(
            f"Timed out fetching {_API} after {timeout_sec} s."
        )
    if reply.error() != QNetworkReply.NetworkError.NoError:
        msg = reply.errorString()
        reply.deleteLater()
        raise RuntimeError(f"GitHub API request failed: {msg}")

    body = bytes(reply.readAll())
    reply.deleteLater()
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not parse GitHub response: {exc}")

    assets = [
        ReleaseAsset(
            name=a["name"],
            url=a["browser_download_url"],
            size=int(a.get("size", 0)),
        )
        for a in data.get("assets", [])
    ]
    return Release(tag=data["tag_name"], assets=assets)
