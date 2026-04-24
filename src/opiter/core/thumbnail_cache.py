"""Persistent thumbnail cache backed by ``XDG_CACHE_HOME/opiter/thumbnails/``.

Cache key: SHA-1 of (resolved file path + mtime + page index + thumbnail width)
so that any of those changing busts the cache. Files are saved as PNG.

This is purely an I/O layer; the in-memory render lives in
:mod:`opiter.core.renderer`. The thumbnail panel calls :func:`get_or_render`
to resolve "give me a pixmap for page N at width W of doc D".
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import fitz

from opiter.core.document import Document
from opiter.core.renderer import render_page
from opiter.utils.paths import cache_dir


def _thumbs_dir() -> Path:
    d = cache_dir() / "thumbnails"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_key(doc: Document, page_index: int, width: int) -> str:
    p = doc.path.resolve()
    try:
        mtime = p.stat().st_mtime_ns
    except OSError:
        mtime = 0
    raw = f"{p}|{mtime}|{page_index}|{width}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def cache_path_for(doc: Document, page_index: int, width: int) -> Path:
    return _thumbs_dir() / f"{_cache_key(doc, page_index, width)}.png"


def get_or_render(doc: Document, page_index: int, width: int) -> bytes:
    """Return PNG bytes for the page-thumbnail. Reads cache if present, else
    renders and saves before returning."""
    cache = cache_path_for(doc, page_index, width)
    if cache.exists():
        try:
            return cache.read_bytes()
        except OSError:
            pass  # fall through to re-render

    page_w, _ = doc.page_size(page_index)
    zoom = (width / page_w) if page_w > 0 else 0.2
    rp = render_page(doc, page_index, zoom=zoom)
    pix = fitz.Pixmap(
        fitz.csRGB, rp.width, rp.height, rp.samples, rp.has_alpha
    )
    png_bytes: bytes = pix.tobytes("png")
    try:
        cache.write_bytes(png_bytes)
    except OSError:
        pass  # cache write failure is non-fatal
    return png_bytes
