"""Tests for opiter.core.document."""
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from opiter.core.document import Document
from opiter.utils.errors import CorruptedPDFError


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Generate a 3-page PDF in tmp_path and return its path."""
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((50, 100), f"Sample page {i + 1}", fontsize=24)
    out = tmp_path / "sample.pdf"
    doc.save(out)
    doc.close()
    return out


def test_open_valid_pdf_reports_page_count(sample_pdf: Path) -> None:
    with Document.open(sample_pdf) as doc:
        assert doc.page_count == 3


def test_open_missing_file_raises_corrupted(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.pdf"
    with pytest.raises(CorruptedPDFError):
        Document.open(missing)


def test_open_garbage_file_raises_corrupted(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    with pytest.raises(CorruptedPDFError):
        Document.open(bad)


def test_page_index_bounds(sample_pdf: Path) -> None:
    with Document.open(sample_pdf) as doc:
        doc.page(0)
        doc.page(2)
        with pytest.raises(IndexError):
            doc.page(3)
        with pytest.raises(IndexError):
            doc.page(-1)


def test_page_size_returns_width_and_height(tmp_path: Path) -> None:
    doc = fitz.open()
    doc.new_page(width=612, height=792)  # US Letter
    out = tmp_path / "letter.pdf"
    doc.save(out)
    doc.close()
    with Document.open(out) as d:
        w, h = d.page_size(0)
        assert w == 612
        assert h == 792


# ----------------------------------------------------------- mutating / save
def _make_pdf(path: Path, pages: int = 3) -> Path:
    doc = fitz.open()
    for i in range(pages):
        p = doc.new_page()
        p.insert_text((50, 100), f"Page {i + 1}", fontsize=24)
    doc.save(path)
    doc.close()
    return path


def test_new_document_is_not_modified(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf")
    with Document.open(pdf) as doc:
        assert doc.is_modified is False


def test_rotate_page_marks_document_modified(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf")
    with Document.open(pdf) as doc:
        doc.rotate_page(0, 90)
        assert doc.is_modified is True
        assert doc.page_rotation(0) == 90


def test_rotate_page_is_cumulative(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf")
    with Document.open(pdf) as doc:
        doc.rotate_page(0, 90)
        doc.rotate_page(0, 90)
        doc.rotate_page(0, 90)
        assert doc.page_rotation(0) == 270
        doc.rotate_page(0, 90)
        assert doc.page_rotation(0) == 0


def test_rotate_page_accepts_negative_degrees(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf")
    with Document.open(pdf) as doc:
        doc.rotate_page(0, -90)
        assert doc.page_rotation(0) == 270


def test_rotate_page_rejects_non_multiple_of_90(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf")
    with Document.open(pdf) as doc:
        with pytest.raises(ValueError):
            doc.rotate_page(0, 45)


def test_save_clears_modified_flag(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf")
    with Document.open(pdf) as doc:
        doc.rotate_page(0, 90)
        assert doc.is_modified
        doc.save()
        assert not doc.is_modified


def test_save_persists_rotation_across_reopen(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf")
    with Document.open(pdf) as doc:
        doc.rotate_page(0, 90)
        doc.save()
    with Document.open(pdf) as doc2:
        assert doc2.page_rotation(0) == 90


def test_save_as_writes_new_file_and_updates_path(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf")
    with Document.open(pdf) as doc:
        doc.rotate_page(0, 180)
        new_path = tmp_path / "b.pdf"
        doc.save_as(new_path)
        assert doc.path == new_path
        assert not doc.is_modified
    assert new_path.exists()
    with Document.open(new_path) as reopened:
        assert reopened.page_rotation(0) == 180


def test_save_after_save_as_does_not_raise(tmp_path: Path) -> None:
    """Regression: PyMuPDF's incremental save requires the document's
    internal source path to match the target path. After save_as, the
    fitz.Document must be reopened from the new path so subsequent
    Ctrl+S (incremental) works."""
    pdf = _make_pdf(tmp_path / "a.pdf")
    with Document.open(pdf) as doc:
        doc.rotate_page(0, 90)
        new_path = tmp_path / "b.pdf"
        doc.save_as(new_path)

        # Further edits after save_as...
        doc.rotate_page(0, 90)
        assert doc.is_modified

        # ...and an incremental save to the new path must succeed.
        doc.save()
        assert not doc.is_modified

    # And the final state must be on disk.
    with Document.open(new_path) as reopened:
        assert reopened.page_rotation(0) == 180
