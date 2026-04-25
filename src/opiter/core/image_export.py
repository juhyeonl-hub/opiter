# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Export PDF pages as image files (PNG or JPEG)."""
from __future__ import annotations

from pathlib import Path
from typing import Literal, Sequence

import fitz

from opiter.core.document import Document

ImageFormat = Literal["png", "jpg"]

_DEFAULT_DPI = 150


def export_pages_as_images(
    doc: Document,
    page_indices: Sequence[int],
    output_dir: str | Path,
    base_name: str,
    fmt: ImageFormat = "png",
    dpi: int = _DEFAULT_DPI,
    jpg_quality: int = 90,
) -> list[Path]:
    """Render each page in ``page_indices`` to an image file.

    Output filename pattern: ``{base_name}_{n}.{fmt}`` where n is 1-based
    and matches position in ``page_indices`` (not the original PDF page
    number, so callers can export a custom subset).

    Returns list of written paths in order.
    Raises ``ValueError`` on bad arguments.
    """
    fmt_l = fmt.lower()
    if fmt_l not in ("png", "jpg", "jpeg"):
        raise ValueError(f"Unsupported format: {fmt}")
    if fmt_l == "jpeg":
        fmt_l = "jpg"
    if dpi <= 0:
        raise ValueError("dpi must be positive")
    if fmt_l == "jpg" and not (1 <= jpg_quality <= 100):
        raise ValueError("jpg_quality must be 1–100")

    out_dir = Path(output_dir)
    if not out_dir.is_dir():
        raise ValueError(f"Output directory does not exist: {out_dir}")
    if not page_indices:
        raise ValueError("No pages to export")

    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    written: list[Path] = []
    for i, idx in enumerate(page_indices, start=1):
        page = doc.page(idx)
        # alpha=False → PDF's white page background is baked into the image,
        # matching what the user sees in the viewer. alpha=True would strip
        # the background and make the export look like content floating in
        # a transparent void.
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        path = out_dir / f"{base_name}_{i}.{fmt_l}"
        if fmt_l == "png":
            pix.save(str(path))
        else:
            pix.save(str(path), jpg_quality=jpg_quality)
        written.append(path)
    return written
