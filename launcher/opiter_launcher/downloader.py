# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Streaming HTTP downloader for the launcher wizard.

Uses ``QNetworkAccessManager`` instead of ``urllib`` so we don't have
to bundle Python's ``_ssl`` + OpenSSL DLLs (Windows SmartScreen / SAC
heuristically blocks PE files containing those, which broke the
launcher in v0.1.13). Qt brings its own SSL stack via PySide6.

The pattern is:
    1. Open a sibling ``.part`` file for write.
    2. Issue a ``QNetworkAccessManager.get`` request.
    3. On every ``readyRead``, drain ``reply.readAll()`` to disk and
       emit progress.
    4. On ``finished``, rename the .part to its final path and emit
       ``finished_ok``; on error emit ``failed`` and clean up.
"""
from __future__ import annotations

from pathlib import Path
from typing import IO

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


class Downloader(QObject):
    """Streams *url* to *dest*, emitting progress on the GUI thread."""

    progress = Signal(int, int)   # (bytes_received, bytes_total)
    finished_ok = Signal(Path)    # full path to the downloaded file
    failed = Signal(str)          # human-readable error message

    def __init__(self, url: str, dest: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._url = url
        self._dest = Path(dest)
        self._tmp = self._dest.with_suffix(self._dest.suffix + ".part")
        self._file: IO[bytes] | None = None
        self._reply: QNetworkReply | None = None
        self._nam = QNetworkAccessManager(self)
        self._cancelled = False

    # ---------------------------------------------------------- public
    def start(self) -> None:
        try:
            self._dest.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(self._tmp, "wb")
        except OSError as exc:
            self.failed.emit(f"Could not open {self._tmp}: {exc}")
            return

        request = QNetworkRequest(QUrl(self._url))
        request.setHeader(
            QNetworkRequest.KnownHeaders.UserAgentHeader, b"Opiter-Launcher"
        )
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
        )
        self._reply = self._nam.get(request)
        self._reply.readyRead.connect(self._on_ready_read)
        self._reply.downloadProgress.connect(self._on_progress)
        self._reply.finished.connect(self._on_finished)

    def cancel(self) -> None:
        self._cancelled = True
        if self._reply is not None and self._reply.isRunning():
            self._reply.abort()

    # --------------------------------------------------------- handlers
    def _on_ready_read(self) -> None:
        if self._reply is None or self._file is None:
            return
        try:
            self._file.write(bytes(self._reply.readAll()))
        except OSError as exc:
            self.failed.emit(f"Disk write failed: {exc}")
            self.cancel()

    def _on_progress(self, received: int, total: int) -> None:
        # ``total`` is -1 when the server doesn't send Content-Length.
        if total < 0:
            total = 0
        self.progress.emit(received, total)

    def _on_finished(self) -> None:
        if self._file is not None:
            try:
                self._file.flush()
                self._file.close()
            except OSError:
                pass
            self._file = None

        if self._reply is None:
            return
        err = self._reply.error()
        err_string = self._reply.errorString()
        self._reply.deleteLater()
        self._reply = None

        if self._cancelled:
            self._cleanup_tmp()
            self.failed.emit("Download cancelled.")
            return
        if err != QNetworkReply.NetworkError.NoError:
            self._cleanup_tmp()
            self.failed.emit(f"Network error: {err_string}")
            return

        try:
            self._tmp.replace(self._dest)
        except OSError as exc:
            self.failed.emit(f"Couldn't move {self._tmp} → {self._dest}: {exc}")
            return
        self.finished_ok.emit(self._dest)

    def _cleanup_tmp(self) -> None:
        try:
            self._tmp.unlink()
        except OSError:
            pass
