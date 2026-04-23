"""Document model — wraps a fitz.Document with safe error handling.

This module is the only place in `core/` that touches PyMuPDF's open/close
lifecycle. UI code interacts with PDFs exclusively through `Document`.
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

    @property
    def page_count(self) -> int:
        return self._doc.page_count

    def page(self, index: int) -> fitz.Page:
        if not 0 <= index < self.page_count:
            raise IndexError(
                f"Page {index} out of range (0..{self.page_count - 1})"
            )
        return self._doc.load_page(index)

    def page_size(self, index: int) -> tuple[float, float]:
        """Return ``(width, height)`` of page *index* in PDF points.

        Exposes page dimensions to UI code without forcing it to touch
        ``fitz.Page`` directly.
        """
        rect = self.page(index).rect
        return rect.width, rect.height

    def close(self) -> None:
        self._doc.close()

    def __enter__(self) -> "Document":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
