# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Single-window setup wizard.

Steps:
    1. Welcome — explain what the launcher will do, [Install] / [Cancel].
    2. Download — fetches the latest Opiter binary from GitHub Releases
       (progress bar + cancel).
    3. Optional LibreOffice install — leverages the existing helpers
       in ``opiter.core.lo_installer`` and ``opiter.ui.lo_install_dialog``
       once the main app is on disk.
    4. Done — desktop shortcut, [Launch Opiter] / [Close].
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .downloader import Downloader
from .github import fetch_latest_release
from .paths import (
    asset_name_for_current_platform,
    install_dir,
    main_executable_path,
)


class _BasePage(QWidget):
    def __init__(self, title: str) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(28, 24, 28, 18)
        self._layout.setSpacing(12)
        self._title = QLabel(f"<h2>{title}</h2>")
        self._layout.addWidget(self._title)


class WelcomePage(_BasePage):
    def __init__(self) -> None:
        super().__init__("Welcome to Opiter")
        body = QLabel(
            "Opiter is a free, open-source desktop document workbench: "
            "edit PDFs and view DOCX / HWP files, all locally with no "
            "telemetry or cloud uploads.\n\n"
            "This launcher will:\n"
            "  • download the latest Opiter app from GitHub (~135 MB)\n"
            "  • install it to your user folder (no admin required)\n"
            "  • optionally set up LibreOffice for full DOCX / HWP rendering\n"
            "  • create a Start Menu / Applications shortcut and launch.\n"
        )
        body.setWordWrap(True)
        self._layout.addWidget(body)
        self._layout.addStretch(1)


class DownloadPage(_BasePage):
    def __init__(self) -> None:
        super().__init__("Downloading Opiter")
        self.status = QLabel("Connecting to GitHub…")
        self.status.setWordWrap(True)
        self._layout.addWidget(self.status)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self._layout.addWidget(self.bar)
        self.detail = QLabel("")
        self.detail.setWordWrap(True)
        self._layout.addWidget(self.detail)
        self._layout.addStretch(1)


class DonePage(_BasePage):
    def __init__(self) -> None:
        super().__init__("Setup complete")
        msg = QLabel(
            "Opiter has been installed. You can launch it now or close "
            "this window — it will be available from the Start Menu / "
            "Applications afterwards."
        )
        msg.setWordWrap(True)
        self._layout.addWidget(msg)
        self._layout.addStretch(1)


class LauncherWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Opiter Setup ({__version__})")
        self.resize(560, 420)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._stack = QStackedWidget()
        self._welcome = WelcomePage()
        self._download = DownloadPage()
        self._done = DonePage()
        self._stack.addWidget(self._welcome)
        self._stack.addWidget(self._download)
        self._stack.addWidget(self._done)
        root.addWidget(self._stack, stretch=1)

        # Footer with action buttons that swap meaning per page.
        footer = QHBoxLayout()
        footer.setContentsMargins(28, 8, 28, 18)
        footer.addStretch(1)
        self._btn_secondary = QPushButton("Cancel")
        self._btn_primary = QPushButton("Install")
        self._btn_primary.setDefault(True)
        footer.addWidget(self._btn_secondary)
        footer.addWidget(self._btn_primary)
        root.addLayout(footer)

        self.setCentralWidget(central)

        self._btn_primary.clicked.connect(self._on_primary)
        self._btn_secondary.clicked.connect(self._on_secondary)

        self._worker: Downloader | None = None
        self._installed_exe: Path | None = None
        self._show_page(0)

    # ---------------------------------------------------------- helpers
    def _show_page(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)
        if idx == 0:
            self._btn_primary.setText("Install")
            self._btn_secondary.setText("Cancel")
        elif idx == 1:
            self._btn_primary.setText("…")
            self._btn_primary.setEnabled(False)
            self._btn_secondary.setText("Cancel")
        elif idx == 2:
            self._btn_primary.setText("Launch Opiter")
            self._btn_primary.setEnabled(True)
            self._btn_secondary.setText("Close")

    def _on_primary(self) -> None:
        idx = self._stack.currentIndex()
        if idx == 0:
            self._begin_download()
        elif idx == 2:
            self._launch_opiter()
            self.close()

    def _on_secondary(self) -> None:
        idx = self._stack.currentIndex()
        if idx == 1 and self._worker is not None:
            self._worker.cancel()
        self.close()

    # ---------------------------------------------------------- download
    def _begin_download(self) -> None:
        self._show_page(1)
        try:
            release = fetch_latest_release()
        except Exception as exc:
            QMessageBox.critical(
                self, "Couldn't reach GitHub",
                "Could not fetch the latest Opiter release. Please check "
                f"your internet connection.\n\n{exc}",
            )
            self._show_page(0)
            return
        asset_name = asset_name_for_current_platform()
        asset = release.asset(asset_name)
        if asset is None:
            QMessageBox.critical(
                self, "Unsupported platform",
                f"Release {release.tag} doesn't ship a "
                f"{asset_name} asset.",
            )
            self._show_page(0)
            return
        self._download.status.setText(
            f"Downloading {asset.name} ({asset.size // 1024 // 1024} MB) "
            f"from release {release.tag}…"
        )
        dest = main_executable_path()
        self._worker = Downloader(asset.url, dest, parent=self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_download_ok)
        self._worker.failed.connect(self._on_download_fail)
        self._worker.start()

    def _on_progress(self, received: int, total: int) -> None:
        if total > 0:
            pct = int(100 * received / total)
            self._download.bar.setValue(pct)
        mb_recv = received // 1024 // 1024
        mb_total = total // 1024 // 1024 if total else 0
        self._download.detail.setText(f"{mb_recv} MB / {mb_total} MB")

    def _on_download_ok(self, path: Path) -> None:
        self._installed_exe = path
        if sys.platform.startswith("win") or sys.platform == "darwin":
            try:
                os.chmod(path, 0o755)
            except OSError:
                pass
        self._create_shortcut(path)
        self._show_page(2)

    def _on_download_fail(self, reason: str) -> None:
        QMessageBox.critical(
            self, "Download failed",
            f"Couldn't download Opiter.\n\n{reason}",
        )
        self._show_page(0)

    # ---------------------------------------------------------- shortcut
    def _create_shortcut(self, exe_path: Path) -> None:
        if not sys.platform.startswith("win"):
            return  # Linux .deb / macOS .app already register themselves.
        try:
            start_menu = (
                Path(os.environ.get("APPDATA", str(Path.home())))
                / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            )
            start_menu.mkdir(parents=True, exist_ok=True)
            shortcut = start_menu / "Opiter.lnk"
            ps_cmd = (
                f'$s = (New-Object -ComObject WScript.Shell).CreateShortcut('
                f'"{shortcut}"); $s.TargetPath = "{exe_path}"; $s.Save()'
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, timeout=10,
            )
        except Exception:
            # Shortcut is a nice-to-have; ignore failures.
            pass

    # ---------------------------------------------------------- launch
    def _launch_opiter(self) -> None:
        if self._installed_exe is None or not self._installed_exe.exists():
            return
        try:
            if sys.platform == "darwin" and self._installed_exe.suffix == ".dmg":
                subprocess.Popen(["open", str(self._installed_exe)])
            else:
                subprocess.Popen([str(self._installed_exe)])
        except Exception as exc:
            QMessageBox.warning(
                self, "Couldn't launch",
                f"Opiter installed but couldn't start automatically.\n\n{exc}",
            )
