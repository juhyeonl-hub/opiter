# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""PDF compression — write a smaller copy of the document."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from opiter.core.document import Document

Quality = Literal["low", "medium", "high"]

# Preset tuning: PyMuPDF's save() supports several size-reduction flags.
# Without deflate_images / deflate_fonts the gain is negligible for PDFs
# whose bulk is embedded images/fonts — which is most of them.
_PRESETS = {
    "high": {
        "garbage": 1,
        "deflate": True,
        "deflate_images": False,
        "deflate_fonts": False,
        "clean": False,
    },
    "medium": {
        "garbage": 3,
        "deflate": True,
        "deflate_images": True,
        "deflate_fonts": True,
        "clean": True,
    },
    "low": {
        "garbage": 4,
        "deflate": True,
        "deflate_images": True,
        "deflate_fonts": True,
        "clean": True,
    },
}


def compress_pdf(
    doc: Document,
    output_path: str | Path,
    quality: Quality = "medium",
) -> Path:
    """Write a compressed copy of *doc* to *output_path*.

    Raises ``ValueError`` for unknown quality preset. Returns the output path.
    The source document is not modified.
    """
    if quality not in _PRESETS:
        raise ValueError(f"Unknown quality preset: {quality}")
    opts = _PRESETS[quality]
    out = Path(output_path)
    doc._doc.save(  # noqa: SLF001 — intentional use of fitz handle
        str(out),
        garbage=opts["garbage"],
        deflate=opts["deflate"],
        deflate_images=opts["deflate_images"],
        deflate_fonts=opts["deflate_fonts"],
        clean=opts["clean"],
    )
    return out
