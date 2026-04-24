"""PDF compression — write a smaller copy of the document."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from opiter.core.document import Document

Quality = Literal["low", "medium", "high"]

# Preset tuning: PyMuPDF's save() supports several size-reduction flags.
# We vary garbage collection intensity and whether content streams are
# deflated/cleaned. High quality = minimal changes (just dedup + deflate);
# Low = aggressive garbage pass + full recompression.
_PRESETS = {
    "high":   {"garbage": 1, "deflate": True,  "clean": False},
    "medium": {"garbage": 3, "deflate": True,  "clean": True},
    "low":    {"garbage": 4, "deflate": True,  "clean": True},
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
        clean=opts["clean"],
    )
    return out
