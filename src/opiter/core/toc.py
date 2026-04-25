# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""Bookmarks / Table of Contents editing.

PyMuPDF represents the TOC as a list of ``[level, title, page, ...]``
entries. Level is 1-based indentation; page is 1-based.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from opiter.core.document import Document


@dataclass
class TocEntry:
    level: int  # 1-based
    title: str
    page: int  # 1-based page number (PyMuPDF convention)
    children: List["TocEntry"] = field(default_factory=list)


def read_toc(doc: Document) -> list[TocEntry]:
    """Return the TOC as a flat list of entries (preserving order)."""
    raw = doc._doc.get_toc()  # noqa: SLF001
    entries: list[TocEntry] = []
    for row in raw:
        # Rows may have 3 or more columns; first three are always level/title/page
        lvl, title, page = row[0], row[1], row[2]
        entries.append(TocEntry(level=int(lvl), title=str(title), page=int(page)))
    return entries


def write_toc(doc: Document, entries: list[TocEntry]) -> None:
    """Replace the document's TOC. Entries must form a valid tree
    (first entry's level should be 1; subsequent levels must not jump
    beyond previous + 1 — PyMuPDF enforces this)."""
    toc = [[e.level, e.title, e.page] for e in entries]
    doc._doc.set_toc(toc)  # noqa: SLF001
    doc.mark_modified()


def clear_toc(doc: Document) -> None:
    doc._doc.set_toc([])  # noqa: SLF001
    doc.mark_modified()
