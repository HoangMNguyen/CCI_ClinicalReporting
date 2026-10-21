"""Preview & export: the report's rows, and a panel to export or save them.

:class:`PreviewExportMixin` handles everything on the page: preview
generation, report export, and saved-setting persistence. Building the
preview and the export runs in the background
(:func:`cci_ui.tasks.run_task`).

The export needs a file name. The date and time of the export are added to
it unless Add the date and time is unticked
(:func:`clinical_reporting.filenames.output_file_name`). A file already in
the folder is replaced only once the user says so (:func:`ask_to_replace`);
one open in Excel can't be, and the message says to close it.

A saved setting holds the report's settings
(:meth:`~clinical_reporting.report.CLReport.settings_to_dict`, its applied
stacked forms and coalesced items included) plus the names given to the
additional input files on the Additional input page
(:func:`clinical_reporting.additional_names.add_to_settings`) and the
export's file name with its Add the date and time choice
(:func:`clinical_reporting.export_name.add_to_settings`); picking the setting
on Source data fills those two back in. Save setting waits while a Data step
is held: its changes can't reach the report, so they would be lost (the
button's tooltip names the steps to fix).
"""

from __future__ import annotations

import logging
import os
import traceback
from functools import partial
from typing import Optional

import pandas as pd
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLineEdit, QMessageBox, QWidget

from cci_ui.icons import IconName
from cci_ui.tasks import defer_if_busy, run_task
from cci_ui.widgets.buttons import make_button
from cci_ui.widgets.labels import text_label
from cci_ui.widgets.page import Page, PageKind
from cci_ui.widgets.path_picker import PathPicker
from cci_ui.widgets.responsive import ResponsiveSplit
from cci_ui.widgets.side_panel import SidePanel, full_width, labeled_field
from cci_ui.widgets.status import StatusBanner
from cci_ui.widgets.tables import style_table, table_card
from cci_ui.widgets.toggle import ToggleSwitch
from cci_ui.widgets.views import PreviewTableView
from clinical_reporting import export_name, feedback, steps
from clinical_reporting.additional_names import add_to_settings
from clinical_reporting.filenames import output_base_name, output_file_name
from clinical_reporting.session import build_report, export_report
from clinical_reporting.telemetry import (
    record_successful_export,
    record_successful_setting_save,
)
from clinical_reporting.ui.dialogs import choose_settings_directory, settings_folder
from clinical_reporting.ui.preview_model import ReportPreviewModel
from clinical_reporting.validation import CANNOT_RUN_PREFIX, ReportValidationError

from ._common import show_problem

logger = logging.getLogger(__name__)

#: The line under the title until a preview shows its size there.
SUBTITLE = "Check the rows, then export them to Excel."
#: The output folder's problem until one is chosen.
NO_OUTPUT_FOLDER = "Choose the folder to export to."
#: The file name's problem until one is typed.
NO_FILE_NAME = "Give the file a name."
#: The setting name's problem while saving is on and it is empty.
NO_SETTING_NAME = "Give the setting a name."
#: Save setting's tooltip (its shortcut), unless a held Data step stops it.
SAVE_TIP = "Save setting (Ctrl+S)"


def ask_to_replace(parent: Optional[QWidget], file_name: str) -> bool:
    """Ask whether the export may replace *file_name* in its folder; True if so.

    Cancel is the default button, and Escape picks it, so nothing is replaced
    by accident.
    """
    box = QMessageBox(
        QMessageBox.Icon.Warning,
        "Export to Excel",
        f"{file_name} already exists in this folder.",
        parent=parent,
    )
    box.setInformativeText("Replace it with this export?")
    replace = box.addButton("Replace", QMessageBox.ButtonRole.AcceptRole)
    cancel = box.addButton(QMessageBox.StandardButton.Cancel)
    box.setDefaultButton(cancel)
    box.setEscapeButton(cancel)
    box.exec()
    replaced = box.clickedButton() is replace
    box.deleteLater()  # Each prompt would stay behind in the window otherwise.
    return replaced


def _was_refused(exc: BaseException) -> bool:
    """Whether writing the file was refused (it is open in Excel, say).

    pandas opens the file itself, so its PermissionError arrives as it is; the
    cause and context are checked in case it comes wrapped (xlsxwriter's
    FileCreateError, when xlsxwriter opens the path itself).
    """
    return any(
        isinstance(error, PermissionError)
        for error in (exc, exc.__cause__, exc.__context__)
    )


class PreviewExportPage(Page):
    """The last step: check the rows, export them, save the setting for reuse.

    The page keeps its own captions current: the preview's size under the
    title, and the export's file name under the name field once it has one.
    F5 refreshes, Ctrl+E exports, and Ctrl+S saves the setting.
    """

    KEY = steps.PREVIEW
    SECTION = "Output"
    ICON = IconName.PREVIEW_EXPORT
    EXPORTS = (
        "pushButton_refresh_preview",
        "tableView_preview",
        "pathPicker_output_folder",
        "pushButton_output_folder",
        "lineEdit_file_name",
        "checkBox_add_date_time",
        "banner_run_state",
        "label_run_confirmation",
        "pushButton_run",
        "checkBox_save_current_setting",
        "lineEdit_setting_name",
        "pathPicker_output_setting_folder",
        "pushButton_output_setting",
        "label_save_confirmation",
        "pushButton_save_setting",
    )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            steps.TITLES[self.KEY], SUBTITLE, kind=PageKind.SPLIT, parent=parent
        )
        self.pushButton_refresh_preview = make_button(
            "Refresh", icon_name=IconName.REFRESH
        )
        self.add_action(self.pushButton_refresh_preview)

        self.tableView_preview = PreviewTableView(
            "The preview appears here when the report can run."
        )
        style_table(self.tableView_preview, row_numbers=True)
        self.tableView_preview.modelChanged.connect(self._show_preview_size)

        self.panel = self._build_panel()
        self.split = ResponsiveSplit(table_card(self.tableView_preview), self.panel)
        self.panel.follow(self.split)
        self.body.addWidget(self.split, 1)

        for keys, button, tooltip in (
            ("F5", self.pushButton_refresh_preview, "Build the preview again (F5)"),
            ("Ctrl+E", self.pushButton_run, "Export to Excel (Ctrl+E)"),
            ("Ctrl+S", self.pushButton_save_setting, SAVE_TIP),
        ):
            button.setToolTip(tooltip)
            self.add_shortcut(keys, button.click)  # Not while it's disabled.

    def _build_panel(self) -> SidePanel:
        panel = SidePanel()

        # Export
        self.pathPicker_output_folder = PathPicker(
            button_text="Choose…", placeholder="No folder chosen"
        )
        self.pushButton_output_folder = self.pathPicker_output_folder.button
        self.lineEdit_file_name = QLineEdit()
        self.lineEdit_file_name.setPlaceholderText("e.g. DEMO01 DSMB")
        self.lineEdit_file_name.textChanged.connect(self._show_file_name)
        self.checkBox_add_date_time = QCheckBox("Add the date and time")
        self.checkBox_add_date_time.setChecked(True)
        self.checkBox_add_date_time.toggled.connect(self._show_file_name)
        # A typed name can be one long word; it wraps instead of widening the panel.
        self.file_name_caption = text_label(style="caption", break_long_words=True)
        # What stops the export now ("Cannot run: Fix Filters first."), kept
        # current as the report changes; the banner below says results.
        self.banner_run_state = StatusBanner(dismissible=False, announce=False)
        self.label_run_confirmation = StatusBanner()
        self.pushButton_run = full_width(
            make_button("Export to Excel", variant="primary", icon_name=IconName.EXPORT)
        )
        export = panel.add_section("Export")
        export.addLayout(labeled_field("Folder", self.pathPicker_output_folder))
        name_field = labeled_field("File name", self.lineEdit_file_name)
        name_field.addWidget(self.checkBox_add_date_time)
        name_field.addWidget(self.file_name_caption)
        export.addLayout(name_field)
        export.addWidget(self.banner_run_state)
        export.addWidget(self.label_run_confirmation)
        export.addWidget(self.pushButton_run)
        self._show_file_name()

        # Save setting
        self.checkBox_save_current_setting = ToggleSwitch()
        self.checkBox_save_current_setting.setAccessibleName(
            "Save these settings for reuse"
        )
        save_toggle = QHBoxLayout()
        save_toggle.addWidget(text_label("Save these settings for reuse", wrap=True), 1)
        save_toggle.addWidget(self.checkBox_save_current_setting)
        self.lineEdit_setting_name = QLineEdit()
        self.lineEdit_setting_name.setPlaceholderText("Setting name")
        self.pathPicker_output_setting_folder = PathPicker(
            button_text="Choose…", placeholder="No folder chosen"
        )
        self.pushButton_output_setting = self.pathPicker_output_setting_folder.button
        self.label_save_confirmation = StatusBanner()
        self.pushButton_save_setting = full_width(
            make_button("Save setting", icon_name=IconName.SAVE)
        )
        save = panel.add_section("Save setting")
        save.addLayout(save_toggle)
        save.addLayout(labeled_field("Name", self.lineEdit_setting_name))
        save.addLayout(labeled_field("Folder", self.pathPicker_output_setting_folder))
        save.addWidget(self.label_save_confirmation)
        save.addWidget(self.pushButton_save_setting)
        return panel

    def _show_preview_size(self) -> None:
        """Under the title: the preview's rows and columns, once it has some."""
        model = self.tableView_preview.model()
        rows = model.rowCount() if model is not None else 0
        self.set_subtitle(
            steps.preview_caption(rows, model.columnCount()) if rows else SUBTITLE
        )

    def _show_file_name(self) -> None:
        """Under the name field: the file the export would write now, once named."""
        text = self.lineEdit_file_name.text()
        named = bool(output_base_name(text))
        self.file_name_caption.setVisible(named)
        if not named:
            return
        stamped = self.checkBox_add_date_time.isChecked()
        name = output_file_name(text, add_date_time=stamped)
        when = " (date and time of export)" if stamped else ""
        self.file_name_caption.setText(f"Saved as {name}{when}")

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().showEvent(event)
        self._show_file_name()  # The time in it moves on.


class PreviewExportMixin:
    """Behavior for previewing reports and persisting settings/results."""

    def _init_preview_export(self) -> None:
        """Connect run, save, and persistence-related buttons."""
        self.ui.pushButton_run.clicked.connect(self.click_run)
        self.ui.pushButton_refresh_preview.clicked.connect(self.preview_report)
        self.ui.pushButton_save_setting.clicked.connect(self.click_save_setting)
        self.ui.pushButton_output_setting.clicked.connect(
            self.click_output_setting_folder
        )
        self.ui.checkBox_save_current_setting.stateChanged.connect(
            self.on_save_current_setting_state_changed
        )
        self.ui.lineEdit_setting_name.textChanged.connect(
            self._refresh_save_availability
        )
        self.ui.lineEdit_file_name.textChanged.connect(self._refresh_run_availability)
        self.on_save_current_setting_state_changed()

    def on_save_current_setting_state_changed(self) -> None:
        """Enable/disable persistence buttons when the checkbox changes."""
        enabled = self.ui.checkBox_save_current_setting.isChecked()
        self.ui.pushButton_output_setting.setEnabled(enabled)
        if not enabled:
            self._set_label_text(self.label_save_confirmation, "")
        self._refresh_save_availability()

    def _refresh_save_availability(self) -> None:
        """Save setting only while saving is on, the setting has a name, and no
        Data step is held (its changes would be lost).

        The name field is marked while it is empty and saving is on.
        """
        on = self.ui.checkBox_save_current_setting.isChecked()
        named = bool(self.ui.lineEdit_setting_name.text().strip())
        held = self._held_steps()
        show_problem(
            self.ui.lineEdit_setting_name, NO_SETTING_NAME if on and not named else ""
        )
        save = self.ui.pushButton_save_setting
        save.setEnabled(on and named and not held)
        save.setToolTip(steps.held_save_tip(held) if on and held else SAVE_TIP)

    # ------------------------------------------------------------------
    # Settings persistence helpers

    def click_output_setting_folder(self) -> None:
        """Let the user choose the directory used to save settings."""
        if not self.ui.checkBox_save_current_setting.isChecked():
            return  # The button is disabled then.

        choose_settings_directory(self)

    def click_save_setting(self) -> None:
        """Save the current report to disk as a saved setting."""
        settings_name = self.ui.lineEdit_setting_name.text().strip()
        if not self.ui.checkBox_save_current_setting.isChecked() or not settings_name:
            return  # The button is disabled then.

        # Remember the folder so both settings-folder buttons open there next.
        self.settings_directory = settings_folder(self)
        try:
            settings = self.report.settings_to_dict(settings_name)
            add_to_settings(
                settings,
                getattr(self, "additional_inputs", {}),
                getattr(self, "additional_form_names", {}),
                getattr(self, "additional_column_names", {}),
            )
            export_name.add_to_settings(
                settings,
                self.ui.lineEdit_file_name.text(),
                add_date_time=self.ui.checkBox_add_date_time.isChecked(),
            )
            settings_path = self._settings_store().save(settings_name, settings)
        except Exception as exc:
            self._set_label_text(
                self.label_save_confirmation,
                feedback.error(
                    f"Failed to save settings: {exc}", traceback.format_exc()
                ),
            )
            return

        try:
            # Like report counting, setting-save telemetry is best-effort and
            # must never alter the user's successful save result.
            record_successful_setting_save(settings_name)
        except Exception:  # Defensive isolation from telemetry regressions.
            pass

        self._set_label_text(
            self.label_save_confirmation,
            feedback.success(f"Settings saved to {settings_path}"),
        )
        if self.ui.checkBox_saved_setting.isChecked():
            self._refresh_saved_settings()

    def _fill_saved_export_name(self, saved: Optional[export_name.ExportName]) -> None:
        """Fill in File name and Add the date and time from a picked setting
        (*saved*).

        ``None`` (it kept no file name) clears File name and ticks the box, so
        the export waits for a name. The Source data page calls this when the
        user picks a setting, not when it re-applies the setting once its files
        reach the report.
        """
        if getattr(self.ui, "lineEdit_file_name", None) is None:
            return  # A partial window (in tests) without this page.
        self.ui.checkBox_add_date_time.setChecked(
            saved.add_date_time if saved else True
        )
        self.ui.lineEdit_file_name.setText(saved.name if saved else "")

    # ------------------------------------------------------------------
    # What stops the export

    def _refresh_run_availability(self) -> None:
        """Export to Excel only when nothing stops it; say what does.

        From the window's last validation and the pages' own problems: the
        steps to fix go in the banner above the button. The output folder is
        marked until one is chosen, and the file name until one is typed.
        """
        issues = getattr(self, "_issues", None)
        if issues is None:  # A partial window (tests): validate here.
            issues = self.report.validate() if self.report is not None else []
        message = steps.cannot_run_message(issues, getattr(self, "_page_problems", {}))
        has_folder = bool(self.output_folder_name)
        picker = getattr(self.ui, "pathPicker_output_folder", None)
        if picker is not None:
            picker.set_problem("" if has_folder else NO_OUTPUT_FOLDER)
        name_field = getattr(self.ui, "lineEdit_file_name", None)
        named = True  # A partial window (tests) has no name to wait for.
        if name_field is not None:
            named = bool(output_base_name(name_field.text()))
            show_problem(name_field, "" if named else NO_FILE_NAME)
        run_button = getattr(self.ui, "pushButton_run", None)
        if run_button is not None:
            run_button.setEnabled(message is None and has_folder and named)
        self._set_label_text(getattr(self.ui, "banner_run_state", None), message or "")

    # ------------------------------------------------------------------
    # Report preview and export

    def _report_validation_message(self) -> Optional[feedback.Message]:
        """Return actionable validation feedback for the current report."""

        if getattr(self, "report", None) is None:
            return feedback.warning(f"{CANNOT_RUN_PREFIX} no report is loaded.")
        return steps.cannot_run_message(
            self.report.validate(), getattr(self, "_page_problems", {})
        )

    def _refuse_to_run(self) -> None:
        """Clear the preview and the last result: the banner says what stops it."""
        self.ui.tableView_preview.setModel(None)
        self._set_label_text(self.label_run_confirmation, "")
        self._refresh_run_availability()

    def preview_report(self) -> None:
        """Generate and display a preview of the report."""
        if defer_if_busy(self, self.preview_report):
            return
        if self._report_validation_message() is not None:
            self._refuse_to_run()
            return
        self._set_label_text(
            self.label_run_confirmation, feedback.info("Generating preview...")
        )
        run_task(
            self,
            build_report,
            self.report,
            on_success=self._show_preview,
            on_error=self._show_preview_error,
            message="Building the preview…",
        )

    def _show_preview(self, result_df: Optional[pd.DataFrame]) -> None:
        """Show the rows built by :meth:`preview_report`."""
        if result_df is None:
            self._set_label_text(
                self.label_run_confirmation,
                feedback.warning(
                    "No data found. Please check your form selections, filters, "
                    "and join settings."
                ),
            )
            self.ui.tableView_preview.setModel(None)
            return
        self.ui.tableView_preview.setModel(ReportPreviewModel(result_df))
        self.ui.tableView_preview.verticalHeader().setVisible(True)
        self.ui.tableView_preview.fit_columns()
        # The page shows the size under its title; nothing else to say.
        self._set_label_text(self.label_run_confirmation, "")

    def _show_preview_error(self, exc: BaseException, details: str) -> None:
        """Clear the preview and say why it couldn't be built."""
        self.ui.tableView_preview.setModel(None)
        self._show_report_error("Error generating preview", exc, details)

    def _show_report_error(
        self, what_failed: str, exc: BaseException, details: str
    ) -> None:
        """Explain why building the report failed (preview or export)."""
        if isinstance(exc, ReportValidationError):
            self._set_label_text(
                self.label_run_confirmation,
                steps.cannot_run_message(
                    exc.issues, getattr(self, "_page_problems", {})
                ),
            )
            return
        logger.error(what_failed, exc_info=exc)
        self._set_label_text(
            self.label_run_confirmation,
            feedback.error(f"{what_failed}: {exc}", details),
        )

    def click_run(self) -> None:
        """Run the report and export it to an Excel file."""
        if defer_if_busy(self, self.click_run):
            return
        typed = self.ui.lineEdit_file_name.text()
        if not self.output_folder_name or not output_base_name(typed):
            return  # The button is disabled then.
        if self._report_validation_message() is not None:
            self._refuse_to_run()
            return

        file_name = output_file_name(
            typed, add_date_time=self.ui.checkBox_add_date_time.isChecked()
        )
        file_path = os.path.join(self.output_folder_name, file_name)
        if os.path.exists(file_path) and not ask_to_replace(self, file_name):
            return  # Kept: the file stays as it was.
        run_task(
            self,
            export_report,
            self.report,
            file_path,
            on_success=self._show_export_result,
            on_error=partial(self._show_export_error, file_path),
            message="Exporting the report…",
        )

    def _show_export_result(self, file_path: Optional[str]) -> None:
        """Confirm the file written by :meth:`click_run` (None: no rows)."""
        if file_path is None:
            self._set_label_text(
                self.label_run_confirmation,
                feedback.warning(
                    "No data to save. Please check your selections and filters."
                ),
            )
            return
        try:
            # Usage counting is best-effort and must never change the
            # user's successful save outcome or produce UI feedback.
            record_successful_export(os.path.basename(file_path))
        except Exception:  # Defensive isolation from telemetry regressions.
            pass
        self._last_export_path = file_path
        self._report_changed()
        self._set_label_text(
            self.label_run_confirmation,
            feedback.success(f"Report saved successfully to {file_path}"),
        )

    def _forget_export_results(self) -> None:
        """Clear the preview, export and save results of the data loaded before.

        The new data's preview is built when the user asks (Refresh) or opens
        the page: a new report has no forms selected yet.
        """
        self._forget_preview()
        self._last_export_path = None
        self._set_label_text(self.label_run_confirmation, "")
        self._set_label_text(self.label_save_confirmation, "")

    def _forget_preview(self) -> None:
        """Clear the preview grid (the page's caption follows)."""
        if self.ui.tableView_preview.model() is not None:
            self.ui.tableView_preview.setModel(None)

    def _show_export_error(
        self, file_path: str, exc: BaseException, details: str
    ) -> None:
        """Say why the report couldn't be exported to *file_path*."""
        if _was_refused(exc):
            logger.warning("Couldn't write %s", file_path, exc_info=exc)
            self._set_label_text(
                self.label_run_confirmation,
                feedback.error(
                    f"Couldn't save {os.path.basename(file_path)}. If it's open "
                    "in Excel, close it, then export again.",
                    details,
                ),
            )
            return
        self._show_report_error("Error saving report", exc, details)
