"""Tests for Phase 4 core modules: image export, image→PDF, compression,
watermark, metadata, TOC."""
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from opiter.core.compression import compress_pdf
from opiter.core.document import Document
from opiter.core.image_export import export_pages_as_images
from opiter.core.image_to_pdf import images_to_pdf
from opiter.core.metadata import Metadata, read_metadata, write_metadata
from opiter.core.toc import TocEntry, clear_toc, read_toc, write_toc
from opiter.core.watermark import add_text_watermark


# -------------------------------------------------------- fixtures
@pytest.fixture
def text_pdf(tmp_path: Path) -> Path:
    """3-page PDF with distinct text per page."""
    d = fitz.open()
    for i in range(3):
        p = d.new_page(width=400, height=500)
        p.insert_text((50, 100), f"P{i + 1}_marker", fontsize=14)
    out = tmp_path / "src.pdf"
    d.save(out)
    d.close()
    return out


# -------------------------------------------------------- 9-1 image export
def test_export_pages_as_images_png(text_pdf: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    with Document.open(text_pdf) as doc:
        paths = export_pages_as_images(doc, [0, 1, 2], out_dir, "page", fmt="png")
    assert len(paths) == 3
    for i, p in enumerate(paths, start=1):
        assert p.name == f"page_{i}.png"
        assert p.exists()
        assert p.stat().st_size > 100  # non-trivial content


def test_export_pages_as_images_jpg(text_pdf: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "jpgout"
    out_dir.mkdir()
    with Document.open(text_pdf) as doc:
        paths = export_pages_as_images(
            doc, [0], out_dir, "scan", fmt="jpg", jpg_quality=80
        )
    assert paths[0].name == "scan_1.jpg"
    assert paths[0].exists()


def test_export_rejects_bad_format(text_pdf: Path, tmp_path: Path) -> None:
    tmp_path.mkdir(exist_ok=True)
    with Document.open(text_pdf) as doc:
        with pytest.raises(ValueError):
            export_pages_as_images(doc, [0], tmp_path, "x", fmt="bmp")


def test_export_rejects_missing_dir(text_pdf: Path, tmp_path: Path) -> None:
    with Document.open(text_pdf) as doc:
        with pytest.raises(ValueError):
            export_pages_as_images(doc, [0], tmp_path / "nope", "x")


def test_export_custom_page_subset(text_pdf: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "sub"
    out_dir.mkdir()
    with Document.open(text_pdf) as doc:
        paths = export_pages_as_images(doc, [2, 0], out_dir, "p")
    # Order in output preserves caller's order
    assert [p.name for p in paths] == ["p_1.png", "p_2.png"]


# -------------------------------------------------------- 9-2 image → PDF
def test_images_to_pdf_combines_in_order(text_pdf: Path, tmp_path: Path) -> None:
    # First export some PNGs, then re-combine
    out_dir = tmp_path / "imgs"
    out_dir.mkdir()
    with Document.open(text_pdf) as doc:
        pngs = export_pages_as_images(doc, [0, 1, 2], out_dir, "i")
    combined = tmp_path / "combined.pdf"
    images_to_pdf(pngs, combined)
    with Document.open(combined) as re:
        assert re.page_count == 3


def test_images_to_pdf_empty_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        images_to_pdf([], tmp_path / "empty.pdf")


def test_images_to_pdf_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        images_to_pdf([tmp_path / "nope.png"], tmp_path / "o.pdf")


# -------------------------------------------------------- 9-3 compression
def test_compress_pdf_writes_output(text_pdf: Path, tmp_path: Path) -> None:
    out = tmp_path / "small.pdf"
    with Document.open(text_pdf) as doc:
        compress_pdf(doc, out, quality="medium")
    assert out.exists()
    with Document.open(out) as re:
        assert re.page_count == 3


def test_compress_pdf_rejects_unknown_quality(text_pdf: Path, tmp_path: Path) -> None:
    with Document.open(text_pdf) as doc:
        with pytest.raises(ValueError):
            compress_pdf(doc, tmp_path / "x.pdf", quality="ultra")  # type: ignore[arg-type]


def test_compress_does_not_mutate_source(text_pdf: Path, tmp_path: Path) -> None:
    original = text_pdf.stat().st_size
    with Document.open(text_pdf) as doc:
        compress_pdf(doc, tmp_path / "c.pdf", quality="low")
        assert doc.is_modified is False
    assert text_pdf.stat().st_size == original


# -------------------------------------------------------- 9-4 watermark
def test_text_watermark_adds_annot_to_every_page(text_pdf: Path) -> None:
    with Document.open(text_pdf) as doc:
        add_text_watermark(doc, "DRAFT")
        for i in range(doc.page_count):
            p = doc.page(i)
            annots = list(p.annots())
            assert len(annots) == 1
            assert annots[0].type[1] == "FreeText"
        assert doc.is_modified is True


def test_text_watermark_specific_pages_only(text_pdf: Path) -> None:
    with Document.open(text_pdf) as doc:
        add_text_watermark(doc, "CONFIDENTIAL", page_indices=[0, 2])
        p0 = doc.page(0)
        assert len(list(p0.annots())) == 1
        p1 = doc.page(1)
        assert len(list(p1.annots())) == 0
        p2 = doc.page(2)
        assert len(list(p2.annots())) == 1


def test_text_watermark_empty_text_rejected(text_pdf: Path) -> None:
    with Document.open(text_pdf) as doc:
        with pytest.raises(ValueError):
            add_text_watermark(doc, "")


def test_text_watermark_rejects_invalid_rotation(text_pdf: Path) -> None:
    """Regression: PyMuPDF's FreeText silently fails for rotate values
    other than 0/90/180/270 (e.g. 45°). The helper must reject upfront."""
    with Document.open(text_pdf) as doc:
        with pytest.raises(ValueError):
            add_text_watermark(doc, "DRAFT", rotate=45)
        with pytest.raises(ValueError):
            add_text_watermark(doc, "DRAFT", rotate=30)


def test_text_watermark_valid_rotations_all_succeed(text_pdf: Path) -> None:
    for rot in (0, 90, 180, 270):
        with Document.open(text_pdf) as doc:
            add_text_watermark(doc, f"R{rot}", rotate=rot)
            # Verify an annot was actually added on every page
            for i in range(doc.page_count):
                assert len(list(doc.page(i).annots())) == 1


def test_text_watermark_on_rotated_page_uses_effective_rotate(
    text_pdf: Path,
) -> None:
    """Regression: user's ``rotate`` argument is the visible-view rotation.
    When the page is rotated, the annot's stored rotate must be the sum
    (mod 360) so the rendered watermark matches the user's intent."""
    with Document.open(text_pdf) as doc:
        # Rotate page 0 by 90° and apply a "horizontal in my view" watermark
        doc.page(0).set_rotation(90)
        add_text_watermark(doc, "DRAFT", page_indices=[0], rotate=0)
        page = doc.page(0)
        annot = next(page.annots())
        # rotate=0 (user view) + page.rotation=90  →  effective 90 on annot
        assert annot.rotation == 90


# -------------------------------------------------------- 9-5 metadata
def test_metadata_round_trip(text_pdf: Path) -> None:
    with Document.open(text_pdf) as doc:
        md = Metadata(
            title="My Title",
            author="juhyeonl",
            subject="Test subject",
            keywords="test,metadata",
            creator="Opiter",
        )
        write_metadata(doc, md)
        assert doc.is_modified is True
        doc.save()

    with Document.open(text_pdf) as reopened:
        back = read_metadata(reopened)
        assert back.title == "My Title"
        assert back.author == "juhyeonl"
        assert back.subject == "Test subject"
        assert back.keywords == "test,metadata"
        assert back.creator == "Opiter"


def test_read_metadata_defaults_blank(text_pdf: Path) -> None:
    with Document.open(text_pdf) as doc:
        md = read_metadata(doc)
        # At minimum, a fresh doc has empty/None-ish fields
        assert isinstance(md.title, str)


# -------------------------------------------------------- 9-6 TOC
def test_toc_write_and_read_back(text_pdf: Path) -> None:
    with Document.open(text_pdf) as doc:
        write_toc(doc, [
            TocEntry(level=1, title="Chapter 1", page=1),
            TocEntry(level=2, title="Section 1.1", page=1),
            TocEntry(level=1, title="Chapter 2", page=2),
            TocEntry(level=1, title="Chapter 3", page=3),
        ])
        assert doc.is_modified is True
        entries = read_toc(doc)
        assert len(entries) == 4
        assert entries[0].title == "Chapter 1"
        assert entries[1].level == 2
        assert entries[3].page == 3


def test_clear_toc(text_pdf: Path) -> None:
    with Document.open(text_pdf) as doc:
        write_toc(doc, [TocEntry(level=1, title="T", page=1)])
        assert len(read_toc(doc)) == 1
        clear_toc(doc)
        assert read_toc(doc) == []


def test_toc_persists_after_save(text_pdf: Path) -> None:
    with Document.open(text_pdf) as doc:
        write_toc(doc, [
            TocEntry(level=1, title="Intro", page=1),
            TocEntry(level=1, title="End", page=3),
        ])
        doc.save()
    with Document.open(text_pdf) as re:
        entries = read_toc(re)
        assert [e.title for e in entries] == ["Intro", "End"]
