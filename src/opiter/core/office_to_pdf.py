# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""DOCX / HWP → PDF conversion via LibreOffice (headless).

Used by the DOCX and HWP viewer tabs to render documents at full
fidelity through PyMuPDF / QPdfView. When LibreOffice isn't on PATH
the caller must fall back to lower-fidelity rendering.

HWP conversion additionally requires the ``h2orestart`` extension to
be loaded into LibreOffice. Presence of soffice is treated as a
necessary-but-not-sufficient signal; the conversion call itself
surfaces missing extension errors.

Converted PDFs are cached under ``XDG_CACHE_HOME/opiter/office-pdf/``
keyed on (resolved-path, mtime) so reopening a document is instant.
"""
from __future__ import annotations

import hashlib
import logging
import subprocess
from pathlib import Path

from opiter.core.lo_installer import find_soffice
from opiter.utils.paths import cache_dir

log = logging.getLogger(__name__)


_CONVERT_TIMEOUT_SECONDS = 120


def office_conversion_available() -> bool:
    """True iff a LibreOffice binary is reachable. h2orestart presence
    is checked separately (HWP-specific). Reuses the lookup logic in
    :mod:`opiter.core.lo_installer` so both the install-prompt and the
    actual conversion agree on whether LO is available."""
    return find_soffice() is not None


def _office_pdf_cache_dir() -> Path:
    d = cache_dir() / "office-pdf"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_key(src: Path) -> str:
    p = src.resolve()
    try:
        mtime = p.stat().st_mtime_ns
    except OSError:
        mtime = 0
    raw = f"{p}|{mtime}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def cached_pdf_for(src: Path) -> Path:
    """Return the cache path that ``convert_to_pdf`` would produce for
    *src* — exists() check tells you whether to convert."""
    return _office_pdf_cache_dir() / f"{_cache_key(src)}.pdf"


def convert_to_pdf(src: str | Path) -> Path:
    """Convert DOCX / HWP / RTF / ODT etc. to PDF via headless soffice.

    Uses a content-keyed cache so unchanged files reuse the previous
    conversion. Returns the cached PDF path. Raises ``RuntimeError`` if
    LibreOffice is missing or conversion fails (e.g. h2orestart not
    loaded for HWP).
    """
    soffice = find_soffice()
    if soffice is None:
        raise RuntimeError(
            "LibreOffice (soffice) is not installed — required for "
            "high-fidelity DOCX/HWP rendering."
        )
    src_path = Path(src)
    cache_pdf = cached_pdf_for(src_path)
    if cache_pdf.exists():
        return cache_pdf

    out_dir = cache_pdf.parent
    cmd = [
        soffice,
        "--headless",
        "--convert-to", "pdf",
        "--outdir", str(out_dir),
        str(src_path),
    ]
    log.info("converting %s via %s", src_path, soffice)
    log.debug("cmd=%r", cmd)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_CONVERT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        log.error("LibreOffice conversion timed out for %s", src_path)
        raise RuntimeError(
            f"LibreOffice conversion of {src_path.name} timed out "
            f"after {_CONVERT_TIMEOUT_SECONDS} seconds."
        )
    log.info(
        "soffice rc=%s stdout=%r stderr=%r",
        result.returncode, result.stdout[:500], result.stderr[:500],
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"LibreOffice conversion failed for {src_path.name} "
            f"(rc={result.returncode}).\n"
            f"stdout: {result.stdout.strip()[:500]}\n"
            f"stderr: {result.stderr.strip()[:500]}"
        )
    produced = out_dir / f"{src_path.stem}.pdf"
    if not produced.exists():
        # List what soffice actually produced so we can diagnose.
        siblings = sorted(p.name for p in out_dir.iterdir())[:30]
        raise RuntimeError(
            f"LibreOffice exited 0 but {produced.name} is missing.\n"
            f"out_dir contents: {siblings}\n"
            f"For HWP files the h2orestart extension may not be loaded."
        )
    if produced != cache_pdf:
        # soffice names the output by the source filename; rename to our
        # cache-key filename so future lookups hit instantly.
        shutil.move(str(produced), cache_pdf)
    return cache_pdf
