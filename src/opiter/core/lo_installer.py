# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""LibreOffice + h2orestart installer plumbing.

The viewer tabs need LibreOffice on PATH to render DOCX / HWP at full
fidelity. Rather than ship a 500 MB installer, we let the OS package
manager fetch it lazily on first need. This module exposes the
per-platform commands and small helpers for the UI dialog to invoke;
the actual ``QProcess`` orchestration and progress reporting lives in
``opiter.ui.lo_install_dialog``.

Conventions:
    - Every public function is pure (no Qt, no subprocess execution
      except the few small synchronous detection probes).
    - Commands are returned as ``list[str]`` ready for ``QProcess.start``.
    - "Installer" strings are an internal enum-ish: ``winget`` |
      ``brew`` | ``apt`` | ``dnf`` | ``pacman``. ``None`` means the
      platform is supported in principle but no recognized package
      manager was detected.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# H2Orestart pinned to the latest known-good release. Bump when a new
# release is published and tested.
_H2ORESTART_VERSION = "0.6.6"
_H2ORESTART_URL = (
    "https://github.com/ebandal/H2Orestart/releases/download/"
    f"{_H2ORESTART_VERSION}/H2Orestart.oxt"
)


# --------------------------------------------------------------- detection
def is_libreoffice_installed() -> bool:
    """True iff a ``soffice`` (or ``libreoffice``) binary is on PATH."""
    return _soffice_binary() is not None


def _soffice_binary() -> str | None:
    for name in ("soffice", "libreoffice"):
        path = shutil.which(name)
        if path:
            return path
    # Common Windows install locations winget doesn't always add to PATH.
    if sys.platform.startswith("win"):
        for guess in (
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ):
            if Path(guess).exists():
                return guess
    return None


def detect_installer() -> str | None:
    """Return the name of the OS package manager we should use to fetch
    LibreOffice on this machine, or ``None`` if none is recognized."""
    if sys.platform.startswith("win"):
        if shutil.which("winget"):
            return "winget"
        return None
    if sys.platform == "darwin":
        if shutil.which("brew"):
            return "brew"
        return None
    # Assume Linux.
    if shutil.which("apt-get") or shutil.which("apt"):
        return "apt"
    if shutil.which("dnf"):
        return "dnf"
    if shutil.which("pacman"):
        return "pacman"
    return None


def installer_display_name(installer: str) -> str:
    """Human-friendly installer name for dialog text."""
    return {
        "winget": "Windows Package Manager (winget)",
        "brew": "Homebrew",
        "apt": "APT (Debian / Ubuntu)",
        "dnf": "DNF (Fedora)",
        "pacman": "pacman (Arch)",
    }.get(installer, installer)


# ----------------------------------------------------------------- commands
def libreoffice_install_command(installer: str) -> list[str]:
    """Return the argv list that installs LibreOffice via *installer*.

    Linux variants are wrapped in ``pkexec`` (PolicyKit) so the user
    gets a graphical password prompt instead of a stuck terminal.
    """
    if installer == "winget":
        return [
            "winget", "install",
            "--id", "TheDocumentFoundation.LibreOffice",
            "-e",
            "--accept-source-agreements",
            "--accept-package-agreements",
            "--silent",
        ]
    if installer == "brew":
        return ["brew", "install", "--cask", "libreoffice"]
    if installer == "apt":
        return ["pkexec", "apt-get", "install", "-y", "libreoffice"]
    if installer == "dnf":
        return ["pkexec", "dnf", "install", "-y", "libreoffice"]
    if installer == "pacman":
        return ["pkexec", "pacman", "-S", "--noconfirm", "libreoffice"]
    raise ValueError(f"Unknown installer: {installer!r}")


def install_h2orestart_command(oxt_path: str | Path) -> list[str]:
    """Return the argv list that registers a downloaded H2Orestart.oxt
    extension with LibreOffice. The extension provides the HWP
    import/export filter LO needs to render Hangul Word Processor files.
    """
    soffice = _soffice_binary() or "soffice"
    return [soffice, "--headless", "unopkg", "add", "--shared", str(oxt_path)]


def h2orestart_oxt_url() -> str:
    """URL to download the pinned H2Orestart .oxt asset."""
    return _H2ORESTART_URL


def h2orestart_cache_path() -> Path:
    """Where we save the downloaded .oxt before passing it to unopkg."""
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    p = Path(base) / "opiter" / "h2orestart"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"H2Orestart-{_H2ORESTART_VERSION}.oxt"


# ----------------------------------------------------------------- helpers
def estimated_libreoffice_size_mb() -> int:
    """Rough display-only size of the LibreOffice download, MB."""
    return 350


def is_h2orestart_installed() -> bool:
    """True iff LibreOffice already has the H2Orestart extension loaded.

    Probes ``unopkg list`` and grep — fast (<200 ms) and accurate.
    Returns False if soffice itself isn't available.
    """
    soffice = _soffice_binary()
    if soffice is None:
        return False
    try:
        result = subprocess.run(
            [soffice, "unopkg", "list"],
            capture_output=True, text=True, timeout=20,
        )
    except (subprocess.SubprocessError, OSError):
        return False
    if result.returncode != 0:
        return False
    return "H2Orestart" in result.stdout
