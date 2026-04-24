"""Common interface every document-editor tab implements.

MainWindow routes menu actions to the active tab through this surface:
``save()``, ``save_as(path)``, ``is_modified()``, ``confirm_discard()``,
``close_document()``, ``display_name()`` plus a few Qt signals so the
shell can reflect modified state / title changes in the tab bar.

Editor kinds (PDF / DOCX / HWP) each subclass ``AbstractEditor``. The
shell never reaches into editor internals — anything format-specific
(rotate page, annotate, etc.) is kept inside its editor's own toolbar
and menu contributions, or exposed via optional capability methods the
editor implements and MainWindow checks with ``hasattr``.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget


class AbstractEditor(QWidget):
    # Emitted when the underlying document gets dirtied/cleaned. The shell
    # updates the tab title (adding/removing the '*' marker) and the Save
    # action's enabled state.
    modified_changed = Signal(bool)

    # Emitted when the editor's display name changes (e.g. Save As).
    title_changed = Signal(str)

    # Emitted to request a transient status-bar message from the shell.
    status_message = Signal(str, int)  # (text, timeout_ms)

    # ------------------------------------------------------------ open / save
    def open_file(self, path: str | Path) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def save(self) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def save_as(self, path: str | Path) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    # --------------------------------------------------------------- state
    def is_modified(self) -> bool:  # pragma: no cover - abstract
        raise NotImplementedError

    def file_path(self) -> Path | None:  # pragma: no cover - abstract
        raise NotImplementedError

    def display_name(self) -> str:
        p = self.file_path()
        return p.name if p is not None else "(untitled)"

    # --------------------------------------------------------- lifecycle
    def confirm_discard(self) -> bool:
        """Return True to allow closing the tab. Default: OK unless modified.
        Subclasses may override with a richer Save/Discard/Cancel prompt."""
        return not self.is_modified()

    def close_document(self) -> None:
        """Release any held resources. Called when the tab is removed."""
        return None
