# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Create a PDF from a sequence of image files."""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import fitz


def images_to_pdf(
    image_paths: Sequence[str | Path],
    output_path: str | Path,
) -> Path:
    """Compile the given images into a single PDF (one page per image,
    page size matching the image's natural dimensions).

    Returns the written output path.
    Raises ``ValueError`` on empty input or unreadable images.
    """
    if not image_paths:
        raise ValueError("No input images")
    output = Path(output_path)

    new_doc = fitz.open()
    try:
        for raw in image_paths:
            p = Path(raw)
            if not p.is_file():
                raise ValueError(f"Not a file: {p}")
            img_doc = fitz.open(p)
            try:
                rect = img_doc[0].rect  # natural image size in points
                pdf_bytes = img_doc.convert_to_pdf()
            finally:
                img_doc.close()
            img_pdf = fitz.open("pdf", pdf_bytes)
            try:
                new_doc.insert_pdf(img_pdf)
            finally:
                img_pdf.close()
        new_doc.save(str(output))
    finally:
        new_doc.close()
    return output
