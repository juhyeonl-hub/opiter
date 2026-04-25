# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Modal dialog that drives the LibreOffice (+ H2Orestart) install.

State machine:

    Stage 1 — install LibreOffice via the OS package manager
              (winget / brew / pkexec apt|dnf|pacman).
    Stage 2 — download the H2Orestart .oxt from GitHub.
    Stage 3 — register the .oxt with LibreOffice via ``unopkg add``.

Each stage is a ``QProcess`` (or ``QNetworkAccessManager`` for the
download). stdout / stderr is streamed into a small log view so the
user can see what's happening; a progress bar advances by stage.

Emits ``finished_ok`` (LibreOffice up and running, h2orestart present)
or ``finished_failed(reason)``. The caller can then re-run the
DOCX/HWP open path which will now hit the high-fidelity tier.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QByteArray,
    QProcess,
    QTimer,
    QUrl,
    Qt,
    Signal,
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QVBoxLayout,
)

from opiter.core import lo_installer


class LibreOfficeInstallDialog(QDialog):
    """Walks LibreOffice + H2Orestart through install in the background."""

    finished_ok = Signal()
    finished_failed = Signal(str)

    def __init__(self, parent=None, install_h2orestart: bool = True) -> None:
        super().__init__(parent)
        self.setWindowTitle("Install LibreOffice")
        self.setModal(True)
        self.resize(640, 420)

        self._install_h2orestart = install_h2orestart

        self._installer = lo_installer.detect_installer()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self._status = QLabel(self._initial_status_text())
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(2000)
        layout.addWidget(self._log, stretch=1)

        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self._buttons.rejected.connect(self._on_cancel)
        layout.addWidget(self._buttons)

        self._proc: QProcess | None = None
        self._net = QNetworkAccessManager(self)
        self._stage = 0  # 0=idle, 1=install LO, 2=download oxt, 3=register oxt
        self._cancelled = False
        # Some package managers (notably winget on Windows) print their
        # success line and keep the parent process alive for trailing
        # cleanup, so QProcess.finished can be slow / never to fire.
        # Poll in parallel and advance the stage when soffice actually
        # shows up on the filesystem — whichever signal arrives first.
        self._lo_poll = QTimer(self)
        self._lo_poll.setInterval(2000)  # 2 s
        self._lo_poll.timeout.connect(self._poll_lo_install)
        self._stage1_advanced = False

    # ------------------------------------------------------------ public
    def start(self) -> None:
        """Kick off the install. Connect to ``finished_ok`` / ``finished_failed``
        before calling this."""
        if self._installer is None:
            self._fail(
                "No supported package manager was found on this system. "
                "Please install LibreOffice manually from "
                "https://www.libreoffice.org/download/."
            )
            return
        self._begin_stage1()

    # ------------------------------------------------------------ helpers
    def _initial_status_text(self) -> str:
        installer = self._installer
        if installer is None:
            return (
                "No supported package manager was detected. You can "
                "still install LibreOffice manually from libreoffice.org."
            )
        size = lo_installer.estimated_libreoffice_size_mb()
        return (
            f"Installing LibreOffice (~{size} MB) via "
            f"{lo_installer.installer_display_name(installer)}.\n"
            "This unlocks pixel-perfect rendering of DOCX and HWP files."
        )

    def _append_log(self, text: str) -> None:
        if not text:
            return
        self._log.appendPlainText(text.rstrip())

    def _set_progress(self, percent: int, status: str) -> None:
        self._progress.setValue(max(0, min(100, percent)))
        self._status.setText(status)

    def _on_cancel(self) -> None:
        self._teardown(reject=True)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """User clicked the title bar X — same as Cancel, but tear
        everything down forcefully so the dialog doesn't hang waiting
        on a still-running QProcess (winget can stay alive for a long
        time after it prints success)."""
        self._teardown(reject=True)
        event.accept()

    def _teardown(self, *, reject: bool) -> None:
        """Stop timers, disconnect QProcess signals, kill subprocess.
        Safe to call multiple times."""
        self._cancelled = True
        try:
            self._lo_poll.stop()
        except RuntimeError:
            pass
        if self._proc is not None:
            # Disconnect first so a late-fired finished signal can't
            # re-enter the dialog after we've torn it down.
            try:
                self._proc.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            try:
                self._proc.errorOccurred.disconnect()
            except (RuntimeError, TypeError):
                pass
            try:
                self._proc.readyReadStandardOutput.disconnect()
            except (RuntimeError, TypeError):
                pass
            if self._proc.state() != QProcess.ProcessState.NotRunning:
                self._proc.kill()
                # Don't waitForFinished — that re-blocks the GUI which
                # is exactly what made the dialog "Not Responding" in
                # the first place. Letting Qt clean up at deleteLater
                # time is fine because the QProcess is parented to us.
            self._proc = None
        if reject:
            self.reject()

    def _fail(self, reason: str) -> None:
        self._append_log(f"\nFAILED: {reason}")
        self._set_progress(0, "Install aborted.")
        self.finished_failed.emit(reason)
        # Switch Cancel into Close so user can read log first.
        self._buttons.clear()
        self._buttons.addButton(QDialogButtonBox.StandardButton.Close)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.accept)

    def _success(self) -> None:
        self._set_progress(100, "Done.")
        self.finished_ok.emit()
        self._buttons.clear()
        self._buttons.addButton(QDialogButtonBox.StandardButton.Close)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.accept)

    # -------------------------------------- Stage 1 — install LibreOffice
    def _begin_stage1(self) -> None:
        if lo_installer.is_libreoffice_installed():
            # Skip straight to h2orestart if requested.
            self._begin_stage2_or_finish()
            return
        self._stage = 1
        self._stage1_advanced = False
        cmd = lo_installer.libreoffice_install_command(self._installer)  # type: ignore[arg-type]
        self._set_progress(
            5,
            f"Installing LibreOffice via {lo_installer.installer_display_name(self._installer)}…",  # type: ignore[arg-type]
        )
        self._append_log("$ " + " ".join(cmd))
        self._lo_poll.start()
        self._spawn_process(cmd, on_done=self._stage1_done)

    def _poll_lo_install(self) -> None:
        """Watchdog: advance Stage 1 the moment soffice actually appears
        on disk, even if QProcess.finished hasn't fired yet (winget on
        Windows can take a long while to report exit after the install
        is effectively complete).
        """
        if self._stage != 1 or self._stage1_advanced:
            return
        if lo_installer.is_libreoffice_installed():
            self._stage1_advanced = True
            self._lo_poll.stop()
            self._append_log(
                "[opiter] soffice detected on disk — advancing to "
                "H2Orestart even though the package manager hasn't "
                "fully exited yet."
            )
            # Detach the lingering QProcess so it doesn't fire stage1_done
            # later and double-advance.
            if self._proc is not None:
                try:
                    self._proc.finished.disconnect()
                except (RuntimeError, TypeError):
                    pass
            self._begin_stage2_or_finish()

    def _stage1_done(self, exit_code: int) -> None:
        if self._cancelled or self._stage1_advanced:
            return
        self._lo_poll.stop()
        if exit_code != 0 and not lo_installer.is_libreoffice_installed():
            self._fail(
                f"LibreOffice install exited with code {exit_code}. "
                "See the log above for details."
            )
            return
        if not lo_installer.is_libreoffice_installed():
            self._fail(
                "Install reported success but soffice is still not on PATH "
                "and isn't in the standard install locations. You may need "
                "to restart your shell or sign out / back in."
            )
            return
        self._stage1_advanced = True
        self._begin_stage2_or_finish()

    # -------------------------------- Stage 2 — download H2Orestart .oxt
    def _begin_stage2_or_finish(self) -> None:
        if not self._install_h2orestart:
            self._success()
            return
        if lo_installer.is_h2orestart_installed():
            self._append_log("H2Orestart already installed — skipping.")
            self._success()
            return
        self._stage = 2
        self._set_progress(
            55,
            "Downloading H2Orestart extension (HWP support)…",
        )
        url = lo_installer.h2orestart_oxt_url()
        self._append_log(f"GET {url}")
        request = QNetworkRequest(QUrl(url))
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
        )
        reply = self._net.get(request)
        reply.downloadProgress.connect(self._on_oxt_progress)
        reply.finished.connect(lambda r=reply: self._stage2_done(r))

    def _on_oxt_progress(self, received: int, total: int) -> None:
        if total <= 0:
            return
        # Stage 2 spans 55–80% of the bar.
        pct = 55 + int(25 * received / total)
        self._set_progress(pct, "Downloading H2Orestart extension…")

    def _stage2_done(self, reply: QNetworkReply) -> None:
        if self._cancelled:
            reply.deleteLater()
            return
        if reply.error() != QNetworkReply.NetworkError.NoError:
            err = reply.errorString()
            reply.deleteLater()
            self._fail(f"Download failed: {err}")
            return
        data: QByteArray = reply.readAll()
        reply.deleteLater()
        if data.isEmpty():
            self._fail("H2Orestart download returned no data.")
            return
        oxt_path = lo_installer.h2orestart_cache_path()
        try:
            oxt_path.write_bytes(bytes(data))
        except OSError as exc:
            self._fail(f"Could not save H2Orestart.oxt: {exc}")
            return
        self._append_log(f"Saved {oxt_path} ({len(bytes(data)) // 1024} KB)")
        self._begin_stage3(oxt_path)

    # -------------------------------- Stage 3 — register extension with LO
    def _begin_stage3(self, oxt_path: Path) -> None:
        self._stage = 3
        self._set_progress(85, "Registering H2Orestart extension with LibreOffice…")
        cmd = lo_installer.install_h2orestart_command(oxt_path)
        self._append_log("$ " + " ".join(cmd))
        self._spawn_process(cmd, on_done=self._stage3_done)

    def _stage3_done(self, exit_code: int) -> None:
        if self._cancelled:
            return
        if exit_code != 0:
            self._fail(
                "Registering H2Orestart with LibreOffice failed. HWP files "
                "will fall back to text-only rendering."
            )
            return
        self._success()

    # ------------------------------------------------------------ subprocess
    def _spawn_process(self, cmd: list[str], on_done) -> None:
        from opiter.core.office_to_pdf import soffice_subprocess_env
        from PySide6.QtCore import QProcessEnvironment

        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        # Strip PYTHONHOME/PYTHONPATH so LO's bundled Python doesn't try
        # to use our interpreter's paths (matters most for stage 3,
        # ``unopkg add``, which loads LO's Python runtime).
        qenv = QProcessEnvironment.systemEnvironment()
        for var in ("PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP"):
            qenv.remove(var)
        self._proc.setProcessEnvironment(qenv)
        self._proc.readyReadStandardOutput.connect(self._on_proc_stdout)
        self._proc.finished.connect(
            lambda code, _status: on_done(code)
        )
        self._proc.errorOccurred.connect(self._on_proc_error)
        program, *args = cmd
        self._proc.start(program, args)

    def _on_proc_stdout(self) -> None:
        if self._proc is None:
            return
        data = self._proc.readAllStandardOutput().data().decode(
            "utf-8", errors="replace"
        )
        self._append_log(data)

    def _on_proc_error(self, error: QProcess.ProcessError) -> None:
        msg = {
            QProcess.ProcessError.FailedToStart:
                "Failed to start the install command — is the package "
                "manager actually installed?",
            QProcess.ProcessError.Crashed:
                "Install process crashed.",
        }.get(error, f"Install process error: {error.name}")
        self._fail(msg)
