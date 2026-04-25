# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 juhyeonl
"""PDF document metadata (title, author, subject, keywords, creator)."""
from __future__ import annotations

from dataclasses import dataclass

from opiter.core.document import Document


@dataclass
class Metadata:
    title: str = ""
    author: str = ""
    subject: str = ""
    keywords: str = ""
    creator: str = ""
    producer: str = ""  # usually read-only in viewer; editable here for symmetry


def read_metadata(doc: Document) -> Metadata:
    raw = doc._doc.metadata or {}  # noqa: SLF001
    return Metadata(
        title=raw.get("title") or "",
        author=raw.get("author") or "",
        subject=raw.get("subject") or "",
        keywords=raw.get("keywords") or "",
        creator=raw.get("creator") or "",
        producer=raw.get("producer") or "",
    )


def write_metadata(doc: Document, md: Metadata) -> None:
    """Update the document's Info dictionary. Marks modified."""
    doc._doc.set_metadata(  # noqa: SLF001
        {
            "title": md.title,
            "author": md.author,
            "subject": md.subject,
            "keywords": md.keywords,
            "creator": md.creator,
            "producer": md.producer,
        }
    )
    doc.mark_modified()
