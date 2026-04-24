"""Page-level operations that produce new files (extract, split).

Unlike the mutating methods on :class:`Document` (rotate, delete, etc.),
these operations never change the source document. They build new PDFs
on disk from a subset of the source's pages.
"""
from __future__ import annotations

from pathlib import Path

import fitz

from opiter.core.document import Document


# --------------------------------------------------------------- parsing
def parse_page_range_spec(spec: str, total_pages: int) -> list[int]:
    """Parse a comma-separated spec of 1-based page numbers/ranges.

    Examples:
        ``"1-3,5,7-9"`` on a 10-page doc → ``[0,1,2,4,6,7,8]``
        ``"1"`` → ``[0]``

    Raises ``ValueError`` for malformed input or out-of-range values.
    Whitespace around tokens is ignored. Duplicates are preserved in
    order so repeated pages can be exported intentionally.
    """
    indices: list[int] = []
    tokens = [t.strip() for t in spec.split(",") if t.strip()]
    if not tokens:
        raise ValueError("No pages specified")
    for token in tokens:
        if "-" in token:
            left, _, right = token.partition("-")
            try:
                a = int(left.strip())
                b = int(right.strip())
            except ValueError as exc:
                raise ValueError(f"Invalid range '{token}'") from exc
            if a < 1 or b < 1 or a > b or b > total_pages:
                raise ValueError(
                    f"Range '{token}' out of bounds (document has {total_pages} pages)"
                )
            indices.extend(range(a - 1, b))
        else:
            try:
                p = int(token)
            except ValueError as exc:
                raise ValueError(f"Invalid page number '{token}'") from exc
            if p < 1 or p > total_pages:
                raise ValueError(
                    f"Page {p} out of bounds (document has {total_pages} pages)"
                )
            indices.append(p - 1)
    return indices


def parse_multi_range_spec(spec: str, total_pages: int) -> list[list[int]]:
    """Parse a semicolon-separated list of single-range specs.

    Example: ``"1-3;4-7;8-10"`` → ``[[0,1,2], [3,4,5,6], [7,8,9]]``

    Raises ``ValueError`` on any malformed group.
    """
    groups: list[list[int]] = []
    raw_groups = [g.strip() for g in spec.split(";") if g.strip()]
    if not raw_groups:
        raise ValueError("No page groups specified")
    for raw in raw_groups:
        groups.append(parse_page_range_spec(raw, total_pages))
    return groups


# --------------------------------------------------------------- write
def _write_subset(doc: Document, indices: list[int], output: Path) -> None:
    """Write a PDF containing the given page indices from doc, in order."""
    if not indices:
        raise ValueError("Cannot write an empty subset")
    new_doc = fitz.open()
    try:
        for idx in indices:
            new_doc.insert_pdf(doc._doc, from_page=idx, to_page=idx)  # noqa: SLF001
        new_doc.save(str(output))
    finally:
        new_doc.close()


def extract_pages(
    doc: Document, page_indices: list[int], output_path: str | Path
) -> Path:
    """Extract the given 0-based page indices to a new PDF."""
    output_path = Path(output_path)
    _write_subset(doc, list(page_indices), output_path)
    return output_path


def split_by_groups(
    doc: Document,
    groups: list[list[int]],
    output_dir: str | Path,
    base_name: str,
) -> list[Path]:
    """Write one output file per group. Returns paths in group order.

    Output filename pattern: ``{base_name}_{n}.pdf`` where n starts at 1.
    """
    output_dir = Path(output_dir)
    if not output_dir.is_dir():
        raise ValueError(f"Output directory does not exist: {output_dir}")
    if not groups:
        raise ValueError("No groups to split")
    written: list[Path] = []
    for i, group in enumerate(groups, start=1):
        target = output_dir / f"{base_name}_{i}.pdf"
        _write_subset(doc, group, target)
        written.append(target)
    return written


def split_per_page(
    doc: Document, output_dir: str | Path, base_name: str
) -> list[Path]:
    """Produce one PDF per page. File ``{base_name}_1.pdf`` = page 1, etc."""
    return split_by_groups(
        doc, [[i] for i in range(doc.page_count)], output_dir, base_name
    )


# --------------------------------------------------------------- merge
def merge_pdfs(
    input_paths: list[str | Path], output_path: str | Path
) -> Path:
    """Concatenate the PDFs at *input_paths* into a single file at *output_path*.

    Pages appear in the order of *input_paths*. The source files are
    opened read-only and not modified. Returns the output path.

    Raises:
        ValueError: ``input_paths`` is empty.
    """
    if not input_paths:
        raise ValueError("No input PDFs to merge")
    output_path = Path(output_path)
    new_doc = fitz.open()
    try:
        for path in input_paths:
            src = fitz.open(str(path))
            try:
                new_doc.insert_pdf(src)
            finally:
                src.close()
        new_doc.save(str(output_path))
    finally:
        new_doc.close()
    return output_path
