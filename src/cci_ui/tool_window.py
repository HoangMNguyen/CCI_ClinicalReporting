"""The main window of a small tool, and how such a tool starts.

Safety Automation, Peer Review Automation and CCI Automation are each a
:class:`ToolWindow`: the shell (with a sidebar only when there are several
pages), and a task runner whose work runs behind the shell's busy overlay.
Each page says how its run went in its own banner, so the shell's status bar
is hidden. :func:`run_tool` starts the app and opens the window where it was
last time (:func:`show_tool`).
"""

from __future__ import annotations

from typing import Callable, Optional, Tuple

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMainWindow, QWidget

from cci_ui.app import create_app
from cci_ui.tasks import TaskRunner
from cci_ui.theme.manager import ThemeManager
from cci_ui.widgets.shell import AppShell
from cci_ui.window_state import WindowState


class ToolWindow(QMainWindow):
    """A tool's window: :attr:`shell` and :attr:`task_runner`."""

    def __init__(
        self,
        theme: Optional[ThemeManager],
        *,
        title: str,
        with_sidebar: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.shell = AppShell(theme, title=title, with_sidebar=with_sidebar)
        self.setCentralWidget(self.shell)
        # Only after parenting (see cci_ui.widgets).
        self.shell.status_bar.setVisible(False)
        #: Runs the pages' work in the background, behind the busy overlay.
        self.task_runner = TaskRunner(self, overlay=self.shell.busy)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        """Start no more work once closing (a run already going finishes)."""
        super().closeEvent(event)
        if event.isAccepted():
            self.task_runner.shutdown()


def show_tool(
    window: ToolWindow,
    *,
    app_id: str,
    first_size: Tuple[int, int],
    min_size: Tuple[int, int],
    settings: Optional[QSettings] = None,
) -> None:
    """Show *window* where it was last time (its sidebar too); saved on close.

    *settings* holds the window state (the tool's own settings by default).
    """
    shell = window.shell if window.shell.sidebar is not None else None
    WindowState(app_id, settings).remember(
        window, first_size=first_size, min_size=min_size, shell=shell
    )
    window.show()


def run_tool(
    make_window: Callable[[ThemeManager], ToolWindow],
    *,
    app_id: str,
    name: str,
    version: str,
    first_size: Tuple[int, int],
    min_size: Tuple[int, int],
) -> int:
    """Start the app, show the window *make_window* builds, run until it closes."""
    app, theme = create_app(app_id=app_id, name=name, version=version)
    window = make_window(theme)
    show_tool(window, app_id=app_id, first_size=first_size, min_size=min_size)
    return app.exec()


__all__ = ["ToolWindow", "run_tool", "show_tool"]
