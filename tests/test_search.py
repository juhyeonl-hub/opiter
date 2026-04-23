"""Tests for opiter.core.search."""
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from opiter.core.document import Document
from opiter.core.search import SearchMatch, search


@pytest.fixture
def text_pdf(tmp_path: Path) -> Path:
    """3-page PDF with deterministic text per page."""
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((50, 100), "Hello world", fontsize=14)
    p2 = doc.new_page()
    p2.insert_text((50, 100), "Hello again", fontsize=14)
    p3 = doc.new_page()
    p3.insert_text((50, 100), "Goodbye", fontsize=14)
    out = tmp_path / "text.pdf"
    doc.save(out)
    doc.close()
    return out


def test_search_finds_one_match_per_page(text_pdf: Path) -> None:
    with Document.open(text_pdf) as doc:
        results = search(doc, "hello")
    assert [m.page_index for m in results] == [0, 1]
    for m in results:
        assert isinstance(m, SearchMatch)
        x0, y0, x1, y1 = m.rect
        assert x1 > x0 and y1 > y0


def test_search_is_case_insensitive(text_pdf: Path) -> None:
    with Document.open(text_pdf) as doc:
        results = search(doc, "HELLO")
    assert len(results) == 2


def test_search_empty_query_returns_empty(text_pdf: Path) -> None:
    with Document.open(text_pdf) as doc:
        assert search(doc, "") == []
        assert search(doc, "   ") == []


def test_search_no_match_returns_empty(text_pdf: Path) -> None:
    with Document.open(text_pdf) as doc:
        assert search(doc, "xyzzy_nonexistent") == []


def test_search_locates_unique_term_on_correct_page(text_pdf: Path) -> None:
    with Document.open(text_pdf) as doc:
        results = search(doc, "Goodbye")
    assert len(results) == 1
    assert results[0].page_index == 2
