"""Choose a file or folder: the chosen path, a Choose… button, and Remove.

In ``file``, ``files``, and ``dir`` mode the picker opens the dialog itself,
starts in the folder used last time (remembered per tool under
*settings_key*), and falls back to ``~/Downloads``. In ``external`` mode it
only shows the path; the owner connects :attr:`PathPicker.button` to its own
dialog and calls :meth:`PathPicker.set_path`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QWidget

from cci_ui.icons import IconName
from cci_ui.widgets.buttons import icon_button, make_button
from cci_ui.widgets.labels import ElidedLabel

MODES = ("external", "file", "files", "dir")


class PathPicker(QWidget):
    """Shows a chosen path, shortened in the middle when it doesn't fit."""

    #: Emitted with the new path (the first one in ``files`` mode), or "".
    pathChanged = Signal(str)

    def __init__(
        self,
        mode: str = "external",
        *,
        button_text: str = "Choose…",
        placeholder: str = "No file chosen",
        dialog_title: str = "",
        file_filter: str = "",
        settings_key: Optional[str] = None,
        settings: Optional[QSettings] = None,
        removable: bool = False,
        remove_text: str = "Remove",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        if mode not in MODES:
            raise ValueError(f"Unknown picker mode {mode!r}; expected one of {MODES}")
        self._mode = mode
        self._dialog_title = dialog_title or button_text.rstrip("…")
        self._file_filter = file_filter
        self._settings_key = settings_key
        self._settings = settings
        self._removable = removable
        self._paths: List[str] = []

        self.path_label = ElidedLabel(placeholder=placeholder, tone="secondary")
        self.button = make_button(button_text, icon_name=IconName.OPEN_FOLDER)
        self.clear_button = icon_button(IconName.CLOSE, remove_text)
        self.clear_button.setVisible(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.path_label, 1)
        layout.addWidget(self.button)
        layout.addWidget(self.clear_button)

        if mode != "external":
            self.button.clicked.connect(self.choose)
        self.clear_button.clicked.connect(self.clear)

    # ------------------------------------------------------------------
    # Value

    def path(self) -> str:
        """The chosen path ("" when nothing is chosen; the first in ``files`` mode)."""
        return self._paths[0] if self._paths else ""

    def paths(self) -> List[str]:
        return list(self._paths)

    def set_path(self, path: Optional[str]) -> None:
        self.set_paths([path] if path else [])

    def set_paths(self, paths: List[str]) -> None:
        """Show *paths*; :attr:`pathChanged` fires only if they differ."""
        paths = [p for p in paths if p]
        if paths == self._paths:
            return
        self._paths = paths
        several = len(self._paths) > 1
        self.path_label.setText(f"{len(self._paths)} files" if several else self.path())
        # The label manages its own tooltip for one long path.
        self.setToolTip("\n".join(self._paths) if several else "")
        self.clear_button.setVisible(self._removable and bool(self._paths))
        self.pathChanged.emit(self.path())

    def clear(self) -> None:
        self.set_paths([])

    # ------------------------------------------------------------------
    # Dialog

    def choose(self) -> None:
        """Open the file or folder dialog for this picker's mode."""
        start = self._start_folder()
        if self._mode == "dir":
            chosen = QFileDialog.getExistingDirectory(self, self._dialog_title, start)
            paths = [chosen] if chosen else []
        elif self._mode == "files":
            paths, _ = QFileDialog.getOpenFileNames(
                self, self._dialog_title, start, self._file_filter
            )
        else:
            chosen, _ = QFileDialog.getOpenFileName(
                self, self._dialog_title, start, self._file_filter
            )
            paths = [chosen] if chosen else []
        if not paths:
            return
        folder = paths[0] if self._mode == "dir" else str(Path(paths[0]).parent)
        self._remember_folder(folder)
        self.set_paths(paths)

    def _settings_store(self) -> QSettings:
        return self._settings if self._settings is not None else QSettings()

    def _start_folder(self) -> str:
        if self._settings_key:
            remembered = self._settings_store().value(
                f"folders/{self._settings_key}", ""
            )
            if remembered and os.path.isdir(remembered):
                return str(remembered)
        if self.path():
            current = Path(self.path())
            return str(current if self._mode == "dir" else current.parent)
        return str(Path.home() / "Downloads")

    def _remember_folder(self, folder: str) -> None:
        if self._settings_key:
            self._settings_store().setValue(f"folders/{self._settings_key}", folder)


__all__ = ["MODES", "PathPicker"]
