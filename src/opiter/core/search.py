"""Full-text search across a Document.

Powered by PyMuPDF's ``Page.search_for`` (case-insensitive). Returns flat
match records the UI can iterate over to navigate hits and draw overlays.
"""
from __future__ import annotations

from dataclasses import dataclass

from opiter.core.document import Document


@dataclass(frozen=True)
class SearchMatch:
    """A single text match in the document."""

    page_index: int
    """0-based page index where the match was found."""

    rect: tuple[float, float, float, float]
    """Bounding box in PDF points: (x0, y0, x1, y1)."""


def search(doc: Document, query: str) -> list[SearchMatch]:
    """Return every occurrence of *query* across all pages of *doc*.

    An empty or whitespace-only ``query`` returns an empty list.
    Search is case-insensitive (PyMuPDF default behavior).
    """
    if not query.strip():
        return []
    results: list[SearchMatch] = []
    for i in range(doc.page_count):
        for rect in doc.page(i).search_for(query):
            results.append(
                SearchMatch(
                    page_index=i,
                    rect=(rect.x0, rect.y0, rect.x1, rect.y1),
                )
            )
    return results
