"""Peer Review Automation's window: one page that reviews an SDS workbook.

The page (:class:`cci_ui.widgets.workflow_page.WorkflowPage`) takes the SDS
workbook, an optional validation file, whether to check naming conventions,
where to save, and a file name. The work happens in
:func:`peer_review_automation.sds.run`, which returns the review workbook;
the page saves it.
"""

from __future__ import annotations

from functools import partial
from typing import Optional

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QWidget

from cci_ui.icons import IconName
from cci_ui.theme.manager import ThemeManager
from cci_ui.theme.tokens import LAYOUT
from cci_ui.tool_window import ToolWindow, run_tool
from cci_ui.widgets.path_picker import PathPicker
from cci_ui.widgets.toggle import ToggleSwitch
from cci_ui.widgets.workflow_page import WorkflowPage
from clinical_reporting.filenames import output_file_name
from clinical_reporting.workflow import WorkflowInputError
from peer_review_automation import __version__, sds

#: Settings key and Windows taskbar id of this tool.
APP_ID = "peer-review-automation"
APP_NAME = "Peer Review Automation"
#: Smallest window that keeps the page usable (it scrolls); size on first
#: launch, taller than the other small tools' 680x540 so the Options card and
#: a three-line message fit without scrolling.
MIN_SIZE = LAYOUT.small_min_window
FIRST_SIZE = (680, 660)
PAGE_KEY = "sds-review"
PAGE_TITLE = "SDS peer review"
PAGE_SUBTITLE = (
    "Check a Medidata study design spec (SDS) workbook and list every problem found."
)


class Widget(ToolWindow):
    """The Peer Review Automation window.

    *settings* holds the folders it remembers (the tool's own settings by
    default; tests pass a throwaway file).
    """

    def __init__(
        self,
        theme: Optional[ThemeManager] = None,
        *,
        settings: Optional[QSettings] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(theme, title=APP_NAME, parent=parent)
        #: The SDS workbook exported from Medidata Rave.
        self.sds_file = PathPicker(
            "file",
            dialog_title="Choose the SDS workbook",
            file_filter="Excel files (*.xlsx)",
            settings_key="sds",
            settings=settings,
        )
        #: The optional validation report exported from Rave.
        self.validation_file = PathPicker(
            "file",
            placeholder="Optional",
            dialog_title="Choose the validation report",
            file_filter="CSV files (*.csv)",
            settings_key="validation",
            settings=settings,
            removable=True,
            remove_text="Remove the validation report",
        )
        self.check_naming = ToggleSwitch()
        self.check_naming.setAccessibleName("Check naming conventions")
        self.page = WorkflowPage(
            PAGE_TITLE,
            PAGE_SUBTITLE,
            inputs=[
                ("SDS workbook", self.sds_file),
                ("Validation report", self.validation_file),
            ],
            options=[("Check naming conventions", self.check_naming)],
            name_preview=output_file_name,
            expected_errors=(WorkflowInputError,),
            settings=settings,
        )
        self.shell.add_page(
            PAGE_KEY, self.page, title=PAGE_TITLE, icon_name=IconName.APP_PEER_REVIEW
        )
        self.sds_file.pathChanged.connect(self._suggest_file_name)
        self.page.runRequested.connect(self.run)
        self.sds_file.setFocus()  # Where a keyboard user starts.

    def _suggest_file_name(self, path: str) -> None:
        self.page.suggest_file_name(sds.default_file_name(path) if path else "")

    def run(self) -> None:
        """Review the chosen SDS workbook and save the findings."""
        sds_path = self.sds_file.path()
        if not sds_path:
            self.page.warn("Choose the SDS workbook first.")
            return
        self.page.start(
            self,
            partial(
                sds.run,
                sds_path,
                validation=self.validation_file.path() or None,
                check_naming=self.check_naming.isChecked(),
                file_name=self.page.file_name_base(),
            ),
            message="Reviewing the SDS workbook…",
        )


def main() -> int:
    """Start Peer Review Automation and run it until its window closes."""
    return run_tool(
        Widget,
        app_id=APP_ID,
        name=APP_NAME,
        version=__version__,
        first_size=FIRST_SIZE,
        min_size=MIN_SIZE,
    )
