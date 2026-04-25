# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""PyInstaller entry shim — preserves the package context that
``opiter_launcher.main`` needs for its relative imports."""
from opiter_launcher.main import main

if __name__ == "__main__":
    main()
