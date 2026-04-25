# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Page rendering — produces raw image bytes from a PDF page.

This module deliberately does not depend on Qt: callers in ``ui/`` adapt
``RenderedPage`` to their platform image type (e.g. ``QImage``).
"""
from __future__ import annotations

from dataclasses import dataclass

import fitz

from opiter.core.document import Document


@dataclass(frozen=True)
class RenderedPage:
    """A rasterized PDF page as raw RGB(A) bytes."""

    width: int
    height: int
    samples: bytes
    stride: int
    has_alpha: bool


def render_page(
    doc: Document,
    index: int,
    zoom: float = 1.0,
    rotation: int = 0,
) -> RenderedPage:
    """Render page *index* of *doc* at *zoom* and *rotation* (degrees, multiples of 90)."""
    page = doc.page(index)
    matrix = fitz.Matrix(zoom, zoom).prerotate(rotation)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    return RenderedPage(
        width=pix.width,
        height=pix.height,
        samples=bytes(pix.samples),
        stride=pix.stride,
        has_alpha=False,
    )
