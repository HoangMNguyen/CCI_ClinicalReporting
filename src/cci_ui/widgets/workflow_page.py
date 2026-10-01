"""A page that runs one workflow: its inputs, where to save, a file name, Run.

The small tools (Safety Automation, Peer Review Automation, and each of CCI
Automation's pages) are all this page: a centred form with the tool's input
rows, then the output folder and the file name, the tool's options, a banner
that says how the last run went, and the Run button under it.

The tool connects :attr:`WorkflowPage.runRequested`, checks its inputs, and
calls :meth:`WorkflowPage.start` with the job to run. The job builds the
workbook and returns it with its file name (an object with ``name`` and
``data``, see :mod:`cci_ui.files`); the page runs it on the window's task
runner behind the busy overlay, saves it in the chosen folder (never over an
existing file), and says where it went. Closing the window during a run lets
the run finish and save; the window just isn't there to say so.
"""

from __future__ import annotations

import os
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence, Tuple, Type, Union

from PySide6.QtCore import QSettings, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QWidget

from cci_ui.files import save_output
from cci_ui.icons import IconName
from cci_ui.tasks import run_task
from cci_ui.widgets.buttons import make_button
from cci_ui.widgets.page import Page, PageKind
from cci_ui.widgets.path_picker import PathPicker
from cci_ui.widgets.section import FormRow, Section
from cci_ui.widgets.status import StatusBanner

#: A form row: its label and field, and optionally how to lay it out
#: (:meth:`cci_ui.widgets.section.Section.add_row` keywords).
Row = Union[Tuple[str, QWidget], Tuple[str, QWidget, Dict[str, Any]]]


class SaveFailed(Exception):
    """The workbook was made but couldn't be saved; the message says why."""


def _run_and_save(folder: str, job: Callable[[], Any]) -> Path:
    """The worker-thread part of a run: build the output, then save it."""
    output = job()
    try:
        return save_output(output, folder)
    except OSError as exc:
        reason = exc.strerror or str(exc)
        raise SaveFailed(
            f"The workbook was made, but it couldn't be saved in {folder}: {reason}."
        ) from exc


class WorkflowPage(Page):
    """A form page for one workflow (see the module docstring).

    *inputs* are the tool's rows in the "Files" card, above the output folder
    and the file name; *options* go in an "Options" card below it, laid out
    as "label ··· field" unless a row says otherwise. :attr:`rows` has every
    row by its label, e.g. to hide one. *name_preview* turns the file name
    (as typed, or the suggested one) into the name the run would save, which
    shows under the card. Errors of the *expected_errors* types are problems
    the user can fix: their message shows as a warning, without a traceback.
    The output folder is remembered under *folder_key* in *settings* (the
    tool's own settings by default; no *folder_key*, not remembered).
    """

    #: Run was clicked.
    runRequested = Signal()

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        *,
        inputs: Sequence[Row] = (),
        options: Sequence[Row] = (),
        name_preview: Optional[Callable[[str], str]] = None,
        expected_errors: Tuple[Type[BaseException], ...] = (),
        folder_key: Optional[str] = "output",
        settings: Optional[QSettings] = None,
        run_text: str = "Run",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(title, subtitle, kind=PageKind.FORM, parent=parent)
        self._name_preview = name_preview
        self._expected_errors = tuple(expected_errors) + (SaveFailed,)
        self._suggested_name = ""
        self._saved_folder = ""
        #: Every form row, by its label.
        self.rows: Dict[str, FormRow] = {}

        #: Where the workbook goes; the last folder used is chosen again.
        self.output_folder = PathPicker(
            "dir",
            placeholder="No folder chosen",
            dialog_title="Choose the output folder",
            settings_key=folder_key or None,
            settings=settings,
        )
        self.output_folder.restore_last_folder()
        #: The file name, without the date and time the run adds.
        self.file_name = QLineEdit()
        self.file_name.textChanged.connect(self._show_file_name)

        self.files = Section("Files")
        for row in inputs:
            self._add_row(self.files, row)
        self._add_row(self.files, ("Output folder", self.output_folder))
        self._add_row(self.files, ("File name", self.file_name))
        self.body.addWidget(self.files)

        self.options: Optional[Section] = None
        if options:
            self.options = Section("Options")
            for row in options:
                self._add_row(self.options, row, label_width=None)
            self.body.addWidget(self.options)

        #: How the last run went.
        self.banner = StatusBanner()
        self.body.addWidget(self.banner)

        self.run_button = make_button(
            run_text, variant="primary", icon_name=IconName.RUN
        )
        self.run_button.clicked.connect(self.runRequested)
        # Right under the banner (not at the foot of a tall window).
        run_row = QHBoxLayout()
        run_row.addStretch(1)
        run_row.addWidget(self.run_button)
        self.body.addLayout(run_row)
        self._show_file_name()

    def _add_row(self, section: Section, row: Row, **defaults: Any) -> None:
        label, field, *layout = row
        options = {**defaults, **(layout[0] if layout else {})}
        self.rows[label] = section.add_row(label, field, **options)

    # ------------------------------------------------------------------
    # File name

    def file_name_base(self) -> str:
        """The file name typed, or else the suggested one."""
        return self.file_name.text().strip() or self._suggested_name

    def suggest_file_name(self, name: str) -> None:
        """Offer *name* (shown greyed in the empty field) when none is typed."""
        self._suggested_name = name
        self.file_name.setPlaceholderText(name)
        self._show_file_name()

    def _show_file_name(self) -> None:
        """Under the card: the file the run would save (once there's a name)."""
        base = self.file_name_base()
        if self._name_preview is None or not base:
            self.files.set_footnote("")
            return
        name = self._name_preview(base)
        self.files.set_footnote(f"Saved as {name} (date and time of the run)")

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().showEvent(event)
        self._show_file_name()  # The time in it moves on.

    # ------------------------------------------------------------------
    # Running

    def warn(self, text: str) -> None:
        """Say in the banner what to fix before the workflow can run."""
        self._say(text, "warning")

    def start(self, host: object, job: Callable[[], Any], *, message: str) -> bool:
        """Run *job* on *host*'s task runner and save its output in the folder.

        *job* runs on a worker thread, so it must not touch widgets: read the
        fields first and pass their values in. *message* shows on the busy
        overlay. Returns False if nothing started (no usable output folder, or
        work already running).
        """
        folder = self.output_folder.path()
        if not folder:
            self.warn("Choose an output folder first.")
            return False
        if not os.path.isdir(folder):
            self.warn(
                f"The output folder {folder} isn't there any more. Choose it again."
            )
            return False
        self.banner.set_action("", None)
        self.banner.clear()
        return run_task(
            host,
            partial(_run_and_save, folder, job),
            on_success=self._show_saved,
            on_error=self._show_failed,
            message=message,
        )

    def _show_saved(self, path: Path) -> None:
        self._saved_folder = str(path.parent)
        self._say(f"Saved {path.name} in {path.parent}.", "success")
        self.banner.set_action("Show in folder", self._open_saved_folder)

    def _show_failed(self, exc: BaseException, details: str) -> None:
        if isinstance(exc, self._expected_errors):
            self._say(str(exc), "warning")
        else:
            self._say(f"The workbook couldn't be made: {exc}", "error", details)

    def _say(self, text: str, kind: str, details: Optional[str] = None) -> None:
        self.banner.set_action("", None)
        self.banner.show_message(text, kind, details=details)
        # On a short window the banner can push Run out of view: bring it back
        # once the page has laid the banner out.
        QTimer.singleShot(0, self, self._keep_run_in_view)

    def _keep_run_in_view(self) -> None:
        if self.scroll_area is not None:
            self.scroll_area.ensureWidgetVisible(self.run_button)

    def _open_saved_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(self._saved_folder))


__all__ = ["Row", "SaveFailed", "WorkflowPage"]
