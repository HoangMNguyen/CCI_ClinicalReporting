"""Safety Automation's window: one page that builds the AE & DLT listing.

The page (:class:`cci_ui.widgets.workflow_page.WorkflowPage`) takes the
Corelisting ZIP, where to save, and a file name. The work happens in
:func:`safety_automation.ae_corelisting.AECoreListing.run`, which reads the
ZIP and returns the workbook; the page saves it.
"""

from __future__ import annotations

from functools import partial
from typing import Optional

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QWidget

import safety_automation.ae_corelisting.AECoreListing as listing
from cci_ui.icons import IconName
from cci_ui.theme.manager import ThemeManager
from cci_ui.theme.tokens import LAYOUT
from cci_ui.tool_window import ToolWindow, run_tool
from cci_ui.widgets.path_picker import PathPicker
from cci_ui.widgets.workflow_page import WorkflowPage
from clinical_reporting.filenames import output_file_name
from clinical_reporting.workflow import WorkflowInputError, study_named_by
from safety_automation import __version__

#: Settings key and Windows taskbar id of this tool.
APP_ID = "safety-automation"
APP_NAME = "Safety Automation"
#: Smallest window that keeps the page usable; size on first launch.
MIN_SIZE = LAYOUT.small_min_window
FIRST_SIZE = LAYOUT.small_first_launch
PAGE_KEY = "ae-dlt-listing"
PAGE_TITLE = "AE & DLT listing"
PAGE_SUBTITLE = (
    "Build the adverse event and dose-limiting toxicity workbook from a "
    "Corelisting export."
)


class Widget(ToolWindow):
    """The Safety Automation window.

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
        #: The Corelisting export; its file name tells the study.
        self.corelisting = PathPicker(
            "file",
            dialog_title="Choose the Corelisting ZIP",
            file_filter="Zip files (*.zip)",
            settings_key="corelisting",
            settings=settings,
        )
        self.page = WorkflowPage(
            PAGE_TITLE,
            PAGE_SUBTITLE,
            inputs=[("Corelisting ZIP", self.corelisting)],
            name_preview=output_file_name,
            expected_errors=(WorkflowInputError,),
            settings=settings,
        )
        self.shell.add_page(
            PAGE_KEY, self.page, title=PAGE_TITLE, icon_name=IconName.APP_SAFETY
        )
        self.corelisting.pathChanged.connect(self._suggest_file_name)
        self.page.runRequested.connect(self.run)
        self.corelisting.setFocus()  # Where a keyboard user starts.

    def _suggest_file_name(self, path: str) -> None:
        study = study_named_by(path) if path else None
        self.page.suggest_file_name(listing.default_file_name(study) if study else "")

    def run(self) -> None:
        """Build the workbook from the chosen ZIP and save it."""
        zip_path = self.corelisting.path()
        if not zip_path:
            self.page.warn("Choose a Corelisting ZIP first.")
            return
        self.page.start(
            self,
            partial(listing.run, zip_path, file_name=self.page.file_name_base()),
            message="Building the AE & DLT workbook…",
        )


def main() -> int:
    """Start Safety Automation and run it until its window closes."""
    return run_tool(
        Widget,
        app_id=APP_ID,
        name=APP_NAME,
        version=__version__,
        first_size=FIRST_SIZE,
        min_size=MIN_SIZE,
    )
