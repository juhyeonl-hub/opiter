# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""HTTP download helper that emits progress via a Qt signal.

Used by the launcher to stream the main Opiter binary off GitHub
Releases without blocking the UI thread. Lives in its own QThread so
the wizard can show a smooth progress bar.
"""
from __future__ import annotations

from pathlib import Path

import ssl  # noqa: F401  — bundled https support, see github.py
import urllib.request

from PySide6.QtCore import QThread, Signal


class DownloadWorker(QThread):
    """Streams *url* to *dest* and emits progress at every chunk."""

    progress = Signal(int, int)   # (bytes_received, bytes_total)
    finished_ok = Signal(Path)    # full path to the downloaded file
    failed = Signal(str)          # human-readable error message

    _CHUNK_BYTES = 64 * 1024

    def __init__(self, url: str, dest: Path, parent=None) -> None:
        super().__init__(parent)
        self._url = url
        self._dest = Path(dest)
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:  # pragma: no cover - thread entry
        try:
            req = urllib.request.Request(
                self._url, headers={"User-Agent": "Opiter-Launcher"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                total = int(resp.headers.get("Content-Length") or 0)
                received = 0
                self._dest.parent.mkdir(parents=True, exist_ok=True)
                # Write to a sibling .part file then rename — never leave
                # a half-finished binary at the final path.
                tmp = self._dest.with_suffix(self._dest.suffix + ".part")
                with open(tmp, "wb") as out:
                    while True:
                        if self._cancelled:
                            self.failed.emit("Download cancelled.")
                            try:
                                tmp.unlink()
                            except OSError:
                                pass
                            return
                        chunk = resp.read(self._CHUNK_BYTES)
                        if not chunk:
                            break
                        out.write(chunk)
                        received += len(chunk)
                        self.progress.emit(received, total)
                tmp.replace(self._dest)
            self.finished_ok.emit(self._dest)
        except Exception as exc:  # pragma: no cover - network surface
            self.failed.emit(f"{type(exc).__name__}: {exc}")
