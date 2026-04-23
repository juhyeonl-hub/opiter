"""Document model — wraps a fitz.Document with safe error handling.

Owns the PyMuPDF open/close lifecycle and tracks a "modified" flag so
the UI can mark unsaved changes and prompt on close.
"""
from __future__ import annotations

from pathlib import Path

import fitz

from opiter.utils.errors import CorruptedPDFError, EncryptedPDFError


class Document:
    """An opened PDF document. Owns the underlying ``fitz.Document``."""

    def __init__(self, path: Path, fitz_doc: fitz.Document) -> None:
        self.path = path
        self._doc = fitz_doc
        self._modified = False

    @classmethod
    def open(cls, path: str | Path) -> "Document":
        """Open the PDF at *path*.

        Raises:
            EncryptedPDFError: The PDF is password-protected.
            CorruptedPDFError: The file cannot be parsed as a PDF.
        """
        p = Path(path)
        try:
            doc = fitz.open(p)
        except Exception as exc:
            raise CorruptedPDFError(f"Cannot open {p}: {exc}") from exc
        if doc.is_encrypted:
            doc.close()
            raise EncryptedPDFError(f"{p} is password-protected")
        return cls(p, doc)

    # ----------------------------------------------------------- read-only
    @property
    def page_count(self) -> int:
        return self._doc.page_count

    @property
    def is_modified(self) -> bool:
        return self._modified

    def page(self, index: int) -> fitz.Page:
        if not 0 <= index < self.page_count:
            raise IndexError(
                f"Page {index} out of range (0..{self.page_count - 1})"
            )
        return self._doc.load_page(index)

    def page_size(self, index: int) -> tuple[float, float]:
        """Return ``(width, height)`` of page *index* in PDF points."""
        rect = self.page(index).rect
        return rect.width, rect.height

    def page_rotation(self, index: int) -> int:
        """Return current rotation of page *index* in degrees (0/90/180/270)."""
        return self.page(index).rotation

    # --------------------------------------------------------------- mutating
    def rotate_page(self, index: int, degrees: int) -> None:
        """Rotate page *index* by *degrees* (multiple of 90, can be negative).

        Rotation is cumulative relative to the current page rotation.
        Marks the document as modified.
        """
        if degrees % 90 != 0:
            raise ValueError(f"degrees must be a multiple of 90, got {degrees}")
        page = self.page(index)
        new_rot = (page.rotation + degrees) % 360
        page.set_rotation(new_rot)
        self._modified = True

    def delete_page(self, index: int) -> None:
        """Delete page at *index*. The document must have more than one page."""
        if not 0 <= index < self.page_count:
            raise IndexError(
                f"Page {index} out of range (0..{self.page_count - 1})"
            )
        if self.page_count == 1:
            raise ValueError("Cannot delete the only page in the document")
        self._doc.delete_page(index)
        self._modified = True

    def reorder_pages(self, new_order: list[int]) -> None:
        """Apply *new_order* — a permutation of ``[0..page_count-1]``.

        After the call, page at index ``i`` is whatever was at
        ``new_order[i]`` before. Identity permutation is a no-op (does
        not mark modified).
        """
        n = self.page_count
        ordered = list(new_order)
        if sorted(ordered) != list(range(n)):
            raise ValueError(
                f"new_order must be a permutation of [0..{n - 1}], got {ordered}"
            )
        if ordered == list(range(n)):
            return
        self._doc.select(ordered)
        self._modified = True

    def move_page(self, from_index: int, to_index: int) -> None:
        """Move the page at *from_index* so it lands at *to_index*.

        Implemented via ``fitz.Document.select(order)`` for clear semantics
        (PyMuPDF's native ``move_page`` has subtle pno/to interactions).
        Same-index move is a no-op and does not mark the document modified.
        """
        n = self.page_count
        if not 0 <= from_index < n:
            raise IndexError(
                f"from_index {from_index} out of range (0..{n - 1})"
            )
        if not 0 <= to_index < n:
            raise IndexError(
                f"to_index {to_index} out of range (0..{n - 1})"
            )
        if from_index == to_index:
            return
        order = list(range(n))
        page = order.pop(from_index)
        order.insert(to_index, page)
        self._doc.select(order)
        self._modified = True

    def insert_blank_page(
        self,
        after_index: int,
        width: float | None = None,
        height: float | None = None,
    ) -> int:
        """Insert a blank page directly after *after_index*. Return the new
        page's index.

        If ``width`` or ``height`` is omitted, the dimensions of the page at
        *after_index* are used so the blank page matches its neighbor.
        """
        if not 0 <= after_index < self.page_count:
            raise IndexError(
                f"Page {after_index} out of range (0..{self.page_count - 1})"
            )
        ref_w, ref_h = self.page_size(after_index)
        new_idx = after_index + 1
        self._doc.new_page(
            pno=new_idx,
            width=width if width is not None else ref_w,
            height=height if height is not None else ref_h,
        )
        self._modified = True
        return new_idx

    # --------------------------------------------------------------- save
    def save(self) -> None:
        """Save changes back to the original file (incremental write)."""
        self._doc.save(
            str(self.path),
            incremental=True,
            encryption=fitz.PDF_ENCRYPT_KEEP,
        )
        self._modified = False

    def save_as(self, new_path: str | Path) -> None:
        """Save a full copy to *new_path* and point the document at it.

        The underlying ``fitz.Document`` is reopened from *new_path* so that
        subsequent ``save()`` (incremental) calls target the new file —
        otherwise PyMuPDF raises "incremental needs original file" because
        its internal source path is still the original open path.
        """
        new_path = Path(new_path)
        self._doc.save(str(new_path))
        self._doc.close()
        self._doc = fitz.open(new_path)
        self.path = new_path
        self._modified = False

    # --------------------------------------------------------------- lifecycle
    def close(self) -> None:
        self._doc.close()

    def __enter__(self) -> "Document":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
