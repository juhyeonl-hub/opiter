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
        """Save a full copy to *new_path* and point the document at it."""
        new_path = Path(new_path)
        self._doc.save(str(new_path))
        self.path = new_path
        self._modified = False

    # --------------------------------------------------------------- lifecycle
    def close(self) -> None:
        self._doc.close()

    def __enter__(self) -> "Document":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
