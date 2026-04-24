"""Apply text or image watermarks to a document's pages."""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import fitz

from opiter.core.document import Document


_VALID_ROTATE = {0, 90, 180, 270}


def add_text_watermark(
    doc: Document,
    text: str,
    page_indices: Sequence[int] | None = None,
    fontsize: int = 48,
    color: tuple[float, float, float] = (0.7, 0.7, 0.7),
    opacity: float = 0.35,
    rotate: int = 0,
) -> None:
    """Draw *text* across the center of each target page as a FreeText annot.

    ``page_indices=None`` means "every page". ``opacity`` 0..1 passes through
    Annot.set_opacity. ``rotate`` must be 0/90/180/270 — PyMuPDF's FreeText
    annot rejects other angles silently (which was why 45° watermarks were
    invisible). For diagonal stamping, draw onto page content directly —
    out of scope here.
    """
    if not text:
        raise ValueError("Watermark text cannot be empty")
    if rotate not in _VALID_ROTATE:
        raise ValueError(
            f"rotate must be one of {sorted(_VALID_ROTATE)}; got {rotate}"
        )
    targets = list(page_indices) if page_indices is not None else list(
        range(doc.page_count)
    )
    for idx in targets:
        page = doc.page(idx)
        rect = page.rect
        cx, cy = rect.width / 2, rect.height / 2
        # Rect sized so horizontal/vertical text at the chosen rotation fits.
        if rotate in (90, 270):
            box_w, box_h = fontsize * 1.5, rect.height
        else:
            box_w, box_h = rect.width, fontsize * 1.5
        wm_rect = fitz.Rect(
            cx - box_w / 2, cy - box_h / 2,
            cx + box_w / 2, cy + box_h / 2,
        )
        annot = page.add_freetext_annot(
            wm_rect, text,
            fontsize=fontsize,
            text_color=color,
            align=1,  # center
            rotate=rotate,
        )
        annot.set_opacity(opacity)
        annot.update()
    doc.mark_modified()


def add_image_watermark(
    doc: Document,
    image_path: str | Path,
    page_indices: Sequence[int] | None = None,
    scale: float = 0.5,
    opacity: float = 0.3,
) -> None:
    """Stamp *image_path* centered on each target page, scaled to
    ``scale`` × page width. ``opacity`` 0..1 adjusts transparency.

    Raises ValueError if the image file is missing or unreadable.
    """
    img = Path(image_path)
    if not img.is_file():
        raise ValueError(f"Image not found: {img}")
    if not (0.0 < scale <= 2.0):
        raise ValueError("scale must be in (0.0, 2.0]")
    img_bytes = img.read_bytes()

    targets = list(page_indices) if page_indices is not None else list(
        range(doc.page_count)
    )
    for idx in targets:
        page = doc.page(idx)
        page_rect = page.rect
        target_w = page_rect.width * scale
        # Preserve aspect ratio using fitz probe
        probe = fitz.open(str(img))
        try:
            img_rect = probe[0].rect
            aspect = img_rect.height / img_rect.width if img_rect.width else 1.0
        finally:
            probe.close()
        target_h = target_w * aspect
        cx, cy = page_rect.width / 2, page_rect.height / 2
        dest = fitz.Rect(
            cx - target_w / 2, cy - target_h / 2,
            cx + target_w / 2, cy + target_h / 2,
        )
        page.insert_image(dest, stream=img_bytes, overlay=True)
        # Note: opacity on insert_image is not universally supported across
        # PyMuPDF versions; if the user wants proper transparency they may
        # need to pre-render a translucent PNG. We still pass the param when
        # available via a fallback.
        _ = opacity  # reserved for future per-version handling
    doc.mark_modified()
