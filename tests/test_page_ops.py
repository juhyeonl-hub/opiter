"""Tests for opiter.core.page_ops (extract / split / parsing)."""
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from opiter.core.document import Document
from opiter.core.page_ops import (
    extract_pages,
    parse_multi_range_spec,
    parse_page_range_spec,
    split_by_groups,
    split_per_page,
)


@pytest.fixture
def numbered_pdf(tmp_path: Path) -> Path:
    """5-page PDF whose first text on each page identifies it."""
    doc = fitz.open()
    for i in range(5):
        p = doc.new_page()
        p.insert_text((50, 100), f"PAGE_{i + 1}_MARKER", fontsize=18)
    out = tmp_path / "numbered.pdf"
    doc.save(out)
    doc.close()
    return out


def _first_marker(pdf_path: Path) -> str:
    with Document.open(pdf_path) as d:
        return d.page(0).get_text("text").strip().split("\n")[0]


# ----------------------------------------------------------- parse single
def test_parse_single_number() -> None:
    assert parse_page_range_spec("3", 5) == [2]


def test_parse_simple_range() -> None:
    assert parse_page_range_spec("1-3", 5) == [0, 1, 2]


def test_parse_combined_spec() -> None:
    assert parse_page_range_spec("1-3,5,2", 5) == [0, 1, 2, 4, 1]


def test_parse_with_whitespace() -> None:
    assert parse_page_range_spec(" 1 - 2 , 4 ", 5) == [0, 1, 3]


def test_parse_empty_raises() -> None:
    with pytest.raises(ValueError):
        parse_page_range_spec("", 5)
    with pytest.raises(ValueError):
        parse_page_range_spec("   ", 5)


def test_parse_out_of_range_raises() -> None:
    with pytest.raises(ValueError):
        parse_page_range_spec("6", 5)
    with pytest.raises(ValueError):
        parse_page_range_spec("0", 5)
    with pytest.raises(ValueError):
        parse_page_range_spec("1-99", 5)


def test_parse_reversed_range_raises() -> None:
    with pytest.raises(ValueError):
        parse_page_range_spec("5-2", 5)


def test_parse_garbage_raises() -> None:
    with pytest.raises(ValueError):
        parse_page_range_spec("abc", 5)
    with pytest.raises(ValueError):
        parse_page_range_spec("1-x", 5)


# ----------------------------------------------------------- parse multi
def test_parse_multi_basic() -> None:
    assert parse_multi_range_spec("1-2;3-4;5", 5) == [[0, 1], [2, 3], [4]]


def test_parse_multi_empty_raises() -> None:
    with pytest.raises(ValueError):
        parse_multi_range_spec("", 5)


def test_parse_multi_with_one_invalid_group_raises() -> None:
    with pytest.raises(ValueError):
        parse_multi_range_spec("1-2;99", 5)


# ---------------------------------------------------------------- extract
def test_extract_writes_correct_pages(numbered_pdf: Path, tmp_path: Path) -> None:
    out = tmp_path / "extract.pdf"
    with Document.open(numbered_pdf) as src:
        extract_pages(src, [0, 2, 4], out)  # pages 1, 3, 5

    with Document.open(out) as result:
        assert result.page_count == 3
        assert "PAGE_1_MARKER" in result.page(0).get_text("text")
        assert "PAGE_3_MARKER" in result.page(1).get_text("text")
        assert "PAGE_5_MARKER" in result.page(2).get_text("text")


def test_extract_does_not_mutate_source(numbered_pdf: Path, tmp_path: Path) -> None:
    out = tmp_path / "extract.pdf"
    with Document.open(numbered_pdf) as src:
        extract_pages(src, [1, 3], out)
        assert src.page_count == 5
        assert src.is_modified is False


def test_extract_empty_indices_raises(numbered_pdf: Path, tmp_path: Path) -> None:
    with Document.open(numbered_pdf) as src:
        with pytest.raises(ValueError):
            extract_pages(src, [], tmp_path / "x.pdf")


# ---------------------------------------------------------------- split
def test_split_by_groups_writes_one_file_per_group(
    numbered_pdf: Path, tmp_path: Path
) -> None:
    with Document.open(numbered_pdf) as src:
        files = split_by_groups(
            src, [[0, 1], [2], [3, 4]], tmp_path, "out"
        )
    assert [p.name for p in files] == ["out_1.pdf", "out_2.pdf", "out_3.pdf"]
    for p in files:
        assert p.exists()
    # File 1 has 2 pages, file 2 has 1, file 3 has 2.
    with Document.open(files[0]) as d:
        assert d.page_count == 2
    with Document.open(files[1]) as d:
        assert d.page_count == 1
        assert "PAGE_3_MARKER" in d.page(0).get_text("text")
    with Document.open(files[2]) as d:
        assert d.page_count == 2


def test_split_by_groups_rejects_missing_directory(
    numbered_pdf: Path, tmp_path: Path
) -> None:
    with Document.open(numbered_pdf) as src:
        with pytest.raises(ValueError):
            split_by_groups(src, [[0]], tmp_path / "nope", "x")


def test_split_per_page_creates_one_file_per_page(
    numbered_pdf: Path, tmp_path: Path
) -> None:
    out_dir = tmp_path / "perpage"
    out_dir.mkdir()
    with Document.open(numbered_pdf) as src:
        files = split_per_page(src, out_dir, "page")
    assert len(files) == 5
    for i, p in enumerate(files, start=1):
        assert p.name == f"page_{i}.pdf"
        with Document.open(p) as d:
            assert d.page_count == 1
            assert f"PAGE_{i}_MARKER" in d.page(0).get_text("text")
