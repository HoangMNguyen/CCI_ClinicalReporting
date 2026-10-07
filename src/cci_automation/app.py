"""CCI Automation's window: its three workflows, one page each.

A sidebar holds the pages, each a
:class:`cci_ui.widgets.workflow_page.WorkflowPage`: the enrollment log and
the DSMB report (a study, its Corelisting ZIP, and an optional cut-off date)
and the format tool (a CSV or Excel file). The work happens in each
workflow's ``run()``, which returns the workbook; the page saves it.
"""

from __future__ import annotations

from datetime import date
from functools import partial
from typing import Callable, Optional, Sequence

from PySide6.QtCore import QDate, QSettings, QTimer
from PySide6.QtWidgets import QComboBox, QDateEdit, QWidget

import cci_automation.dsmb.DSMB as dsmb
import cci_automation.enrollment_log.EnrollmentLog as enrollment
import cci_automation.format_tools.change_type as format_tool
from cci_automation import __version__
from cci_ui.icons import IconName
from cci_ui.theme.manager import ThemeManager
from cci_ui.tool_window import ToolWindow, run_tool
from cci_ui.widgets.path_picker import PathPicker
from cci_ui.widgets.toggle import ToggleSwitch
from cci_ui.widgets.workflow_page import WorkflowPage
from clinical_reporting.filenames import output_file_name
from clinical_reporting.workflow import (
    UnsupportedStudyError,
    WorkflowInputError,
    study_named_by,
)

#: Settings key and Windows taskbar id of this tool.
APP_ID = "cci-automation"
APP_NAME = "CCI Automation"
#: Smallest window that keeps a page and the sidebar usable (the page
#: scrolls, the sidebar folds to icons); size on first launch (wide enough for
#: the sidebar with its titles, tall enough for a page and a message).
MIN_SIZE = (860, 560)
FIRST_SIZE = (1120, 700)
#: Page keys.
ENROLLMENT = "enrollment-log"
DSMB = "dsmb-report"
FORMAT = "format-tools"


class StudyReportPage(WorkflowPage):
    """A study's report from its Corelisting export, up to a cut-off date if set.

    The study can be picked, or comes from the ZIP's file name when that
    names one of *studies* (*workflow* says which report this is, for the
    warning when it names another); *default_name* suggests the file name.
    The output folder is the one all three pages remember: one picked on a
    page shows on the others the next time the tool opens.
    """

    def __init__(
        self,
        title: str,
        subtitle: str,
        *,
        workflow: str,
        studies: Sequence[str],
        default_name: Callable[[str], str],
        settings: Optional[QSettings] = None,
    ) -> None:
        study = QComboBox()
        study.addItems(list(studies))
        corelisting = PathPicker(
            "file",
            dialog_title="Choose the Corelisting ZIP",
            file_filter="Zip files (*.zip)",
            settings_key="corelisting",
            settings=settings,
        )
        use_cut_off = ToggleSwitch()
        use_cut_off.setAccessibleName("Apply cut-off date")
        cut_off = QDateEdit(QDate.currentDate())
        cut_off.setCalendarPopup(True)
        cut_off.setFixedWidth(150)
        super().__init__(
            title,
            subtitle,
            inputs=[("Study", study), ("Corelisting ZIP", corelisting)],
            options=[("Apply cut-off date", use_cut_off), ("Cut-off date", cut_off)],
            name_preview=output_file_name,
            expected_errors=(WorkflowInputError,),
            settings=settings,
        )
        #: The study the report is for.
        self.study = study
        #: The Corelisting export.
        self.corelisting = corelisting
        #: Whether rows after :attr:`cut_off` are left out.
        self.use_cut_off = use_cut_off
        self.cut_off = cut_off
        self._workflow = workflow
        self._studies = tuple(studies)
        self._default_name = default_name
        self.options.set_footnote(
            "Only rows dated on or before the cut-off date are read from the export."
        )
        # Only after parenting (see cci_ui.widgets): the date shows when used.
        self.rows["Cut-off date"].setVisible(False)
        use_cut_off.toggled.connect(self._show_cut_off)
        corelisting.pathChanged.connect(self._take_study_from)
        study.currentTextChanged.connect(self._suggest_file_name)
        self._suggest_file_name(study.currentText())

    def cut_off_date(self) -> Optional[date]:
        """The cut-off date, or None when it isn't applied."""
        return self.cut_off.date().toPython() if self.use_cut_off.isChecked() else None

    def _show_cut_off(self, shown: bool) -> None:
        self.rows["Cut-off date"].setVisible(shown)
        # On a short window the new row can push Run out of view.
        QTimer.singleShot(0, self, self._keep_run_in_view)

    def _take_study_from(self, path: str) -> None:
        named = study_named_by(path) if path else None
        if named is None or named in self._studies:
            self.banner.clear()  # A warning about the ZIP chosen before.
            if named is not None:
                self.study.setCurrentText(named)
        else:
            self.warn(str(UnsupportedStudyError(self._workflow, named, self._studies)))

    def _suggest_file_name(self, study: str) -> None:
        self.suggest_file_name(self._default_name(study) if study else "")


class Widget(ToolWindow):
    """The CCI Automation window.

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
        super().__init__(theme, title=APP_NAME, with_sidebar=True, parent=parent)
        self.enrollment = StudyReportPage(
            "Enrollment log",
            "Build a study's enrollment log from its Corelisting export.",
            workflow=enrollment.WORKFLOW,
            studies=enrollment.SUPPORTED_STUDIES,
            default_name=enrollment.default_file_name,
            settings=settings,
        )
        self.dsmb = StudyReportPage(
            "DSMB report",
            "Build a study's DSMB report from its Corelisting export.",
            workflow=dsmb.WORKFLOW,
            studies=dsmb.SUPPORTED_STUDIES,
            default_name=dsmb.default_file_name,
            settings=settings,
        )
        #: The CSV or Excel file the format tool fixes.
        self.format_source = PathPicker(
            "file",
            dialog_title="Choose the CSV or Excel file",
            file_filter="CSV or Excel files (*.csv *.xlsx)",
            settings_key="format-source",
            settings=settings,
        )
        self.format = WorkflowPage(
            "Format tools",
            "Keep lab ranges such as 10-20 as text and take the leading zeros out "
            "of dates (03/05/2026 becomes 3/5/2026) in a CSV or Excel file.",
            inputs=[("CSV or Excel file", self.format_source)],
            name_preview=output_file_name,
            expected_errors=(WorkflowInputError,),
            settings=settings,
        )
        self.shell.add_page(
            ENROLLMENT,
            self.enrollment,
            title="Enrollment log",
            icon_name=IconName.ENROLLMENT,
            section="Reports",
        )
        self.shell.add_page(
            DSMB,
            self.dsmb,
            title="DSMB report",
            icon_name=IconName.DSMB,
            section="Reports",
        )
        self.shell.add_page(
            FORMAT,
            self.format,
            title="Format tools",
            icon_name=IconName.FORMAT_TOOLS,
            section="Tools",
        )
        self.enrollment.runRequested.connect(self.run_enrollment_log)
        self.dsmb.runRequested.connect(self.run_dsmb_report)
        self.format.runRequested.connect(self.run_format_tool)
        self.format_source.pathChanged.connect(self._suggest_format_name)
        self.enrollment.corelisting.setFocus()  # Where a keyboard user starts.

    def _suggest_format_name(self, path: str) -> None:
        self.format.suggest_file_name(
            format_tool.default_file_name(path) if path else ""
        )

    def _run_study_report(self, page: StudyReportPage, run, message: str) -> None:
        zip_path = page.corelisting.path()
        if not zip_path:
            page.warn("Choose a Corelisting ZIP first.")
            return
        page.start(
            self,
            partial(
                run,
                zip_path,
                study=page.study.currentText(),
                cut_off_date=page.cut_off_date(),
                file_name=page.file_name_base(),
            ),
            message=message,
        )

    def run_enrollment_log(self) -> None:
        """Build the chosen study's enrollment log and save it."""
        self._run_study_report(
            self.enrollment, enrollment.run, "Building the enrollment log…"
        )

    def run_dsmb_report(self) -> None:
        """Build the chosen study's DSMB report and save it."""
        self._run_study_report(self.dsmb, dsmb.run, "Building the DSMB report…")

    def run_format_tool(self) -> None:
        """Format the chosen file and save the result."""
        source = self.format_source.path()
        if not source:
            self.format.warn("Choose a CSV or Excel file first.")
            return
        self.format.start(
            self,
            partial(format_tool.run, source, file_name=self.format.file_name_base()),
            message="Formatting the file…",
        )


def main() -> int:
    """Start CCI Automation and run it until its window closes."""
    return run_tool(
        Widget,
        app_id=APP_ID,
        name=APP_NAME,
        version=__version__,
        first_size=FIRST_SIZE,
        min_size=MIN_SIZE,
    )
