# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Opiter launcher — small bootstrap installer.

Ships as a tiny ``opiter-setup.exe`` (~25 MB). On first run it
downloads the main Opiter binary from GitHub Releases, optionally
installs LibreOffice + H2Orestart, sets up a Start Menu shortcut
and launches the app. On subsequent runs it just launches the
already-installed Opiter (and offers updates if a newer release is
available).
"""
__version__ = "0.1.0"
