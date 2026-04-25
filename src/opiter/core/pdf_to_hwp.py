# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""PDF → HWP conversion (best-effort via LibreOffice + h2orestart).

No pure-Python HWP writer exists. The strategy here is a two-hop
conversion through DOCX:

1. PDF → DOCX via pdf2docx
2. DOCX → HWP via ``soffice --convert-to hwp``

Step 2 requires LibreOffice installed **and** the ``h2orestart``
extension loaded (which is the HWP import/export plugin — not bundled
by default). Without those, :func:`hwp_conversion_available` returns
False and callers should disable the menu item with an explanatory
tooltip / dialog.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from opiter.core.pdf_to_docx import pdf_to_docx


def _soffice_binary() -> str | None:
    for name in ("soffice", "libreoffice"):
        path = shutil.which(name)
        if path:
            return path
    return None


def hwp_conversion_available() -> bool:
    """True iff ``soffice`` is on PATH. We can't verify h2orestart from
    here without spawning LO; presence of soffice is treated as a
    necessary-but-not-sufficient signal. An actual convert attempt will
    fail gracefully if h2orestart is missing, and the caller surfaces
    that to the user.
    """
    return _soffice_binary() is not None


def pdf_to_hwp(pdf_path: str | Path, hwp_path: str | Path) -> Path:
    """Convert PDF → HWP via DOCX intermediate.

    Raises ``RuntimeError`` if LibreOffice / h2orestart aren't available
    or the conversion fails.
    """
    soffice = _soffice_binary()
    if soffice is None:
        raise RuntimeError(
            "LibreOffice (soffice) is not installed — required for HWP export."
        )
    pdf = Path(pdf_path)
    hwp_out = Path(hwp_path)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        tmp_docx = tmp_dir / f"{pdf.stem}.docx"
        pdf_to_docx(pdf, tmp_docx)

        # Ask LibreOffice to convert DOCX → HWP.
        # `hwp` filter is provided by the h2orestart extension when
        # installed; otherwise LibreOffice exits non-zero.
        result = subprocess.run(
            [
                soffice,
                "--headless",
                "--convert-to", "hwp",
                "--outdir", str(tmp_dir),
                str(tmp_docx),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "LibreOffice HWP conversion failed. The h2orestart extension "
                "is likely missing (required for HWP export).\n\n"
                f"stderr: {result.stderr.strip()}"
            )

        produced = tmp_dir / f"{pdf.stem}.hwp"
        if not produced.exists():
            raise RuntimeError(
                "LibreOffice did not produce an .hwp file — the h2orestart "
                "extension may not be loaded."
            )
        shutil.copy(produced, hwp_out)
    return hwp_out
