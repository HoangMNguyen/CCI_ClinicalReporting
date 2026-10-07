"""Run, preview, and persistence mixin for the Clinical Reporting widget.

This module handles everything on the final "Preview & export" page,
including preview generation, report export, and saved-setting
persistence. Building the preview and the export runs in the background
(:func:`cci_ui.tasks.run_task`).

A saved setting holds the report's settings
(:meth:`~clinical_reporting.report.CLReport.settings_to_dict`) plus the
names given to the additional input files on the Additional input page
(:func:`clinical_reporting.additional_names.add_to_settings`).
"""

from __future__ import annotations

import logging
import os
import traceback
from typing import Optional

import pandas as pd

from cci_ui.tasks import defer_if_busy, run_task
from clinical_reporting import feedback
from clinical_reporting.additional_names import add_to_settings
from clinical_reporting.filenames import output_file_name
from clinical_reporting.session import build_report, export_report
from clinical_reporting.telemetry import (
    record_successful_export,
    record_successful_setting_save,
)
from clinical_reporting.ui.dialogs import choose_settings_directory, settings_folder
from clinical_reporting.ui.preview_model import ReportPreviewModel
from clinical_reporting.validation import (
    CANNOT_RUN_PREFIX,
    JOIN_BLOCKING_ISSUE_CODES,
    ReportValidationError,
    cannot_run_message,
    report_issues_message,
)

logger = logging.getLogger(__name__)


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
        self.on_save_current_setting_state_changed()

    def on_save_current_setting_state_changed(self) -> None:
        """Enable/disable persistence buttons when the checkbox changes."""
        enabled = self.ui.checkBox_save_current_setting.isChecked()
        self.ui.pushButton_save_setting.setEnabled(enabled)
        self.ui.pushButton_output_setting.setEnabled(enabled)
        if not enabled:
            self._set_label_text(self.label_save_confirmation, "")

    # ------------------------------------------------------------------
    # Settings persistence helpers

    def click_output_setting_folder(self) -> None:
        """Let the user choose the directory used to save settings."""
        if not self.ui.checkBox_save_current_setting.isChecked():
            self._set_label_text(
                self.label_save_confirmation,
                feedback.warning(
                    "Turn on 'Save these settings for reuse' before choosing a "
                    "settings folder."
                ),
            )
            return

        choose_settings_directory(self)

    def click_save_setting(self) -> None:
        """Persist the current report configuration to disk."""
        if not self.ui.checkBox_save_current_setting.isChecked():
            self._set_label_text(
                self.label_save_confirmation,
                feedback.warning(
                    "Turn on 'Save these settings for reuse' before saving."
                ),
            )
            return

        settings_name = self.ui.lineEdit_setting_name.text().strip()
        if not settings_name:
            self._set_label_text(
                self.label_save_confirmation,
                feedback.warning("Please enter a setting name before saving."),
            )
            return

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

    # ------------------------------------------------------------------
    # Join-configuration guarding

    def _join_configuration_error_message(self) -> Optional[feedback.Message]:
        """Return validation feedback for join errors that block output."""
        report = getattr(self, "report", None)
        if report is None:
            return None
        return report_issues_message(report, JOIN_BLOCKING_ISSUE_CODES)

    def _refresh_run_availability(self) -> None:
        """Enable/disable Export to Excel and surface join-configuration errors.

        Called whenever the join configuration changes so the disabled state and
        the inline hint stay in sync with the current selections.
        """
        message = self._join_configuration_error_message()
        run_button = getattr(self.ui, "pushButton_run", None)
        if run_button is not None:
            run_button.setEnabled(message is None)
        if message is not None:
            self._set_label_text(self.label_run_confirmation, message)
        elif (
            self.label_run_confirmation is not None
            and self.label_run_confirmation.text().startswith(CANNOT_RUN_PREFIX)
        ):
            # Conflict resolved: clear only our own stale hint.
            self._set_label_text(self.label_run_confirmation, "")

    # ------------------------------------------------------------------
    # Report preview and export

    def _report_validation_message(self) -> Optional[feedback.Message]:
        """Return actionable validation feedback for the current report."""

        if getattr(self, "report", None) is None:
            return feedback.warning(f"{CANNOT_RUN_PREFIX} no report is loaded.")
        return report_issues_message(self.report)

    def preview_report(self) -> None:
        """Generate and display a preview of the report."""
        if defer_if_busy(self, self.preview_report):
            return
        validation_message = self._report_validation_message()
        if validation_message is not None:
            self._set_label_text(self.label_run_confirmation, validation_message)
            self.ui.tableView_preview.setModel(None)
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
                self.label_run_confirmation, cannot_run_message(exc.issues)
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
        validation_message = self._report_validation_message()
        if validation_message is not None:
            self._set_label_text(self.label_run_confirmation, validation_message)
            return
        # Checked first, so a missing folder doesn't cost a full report build.
        if not self.output_folder_name:
            self._set_label_text(
                self.label_run_confirmation,
                feedback.warning("Please select an output folder first."),
            )
            return

        file_name = output_file_name(self.ui.lineEdit_file_name.text())
        run_task(
            self,
            export_report,
            self.report,
            os.path.join(self.output_folder_name, file_name),
            on_success=self._show_export_result,
            on_error=self._show_export_error,
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

    def _show_export_error(self, exc: BaseException, details: str) -> None:
        """Say why the report couldn't be exported."""
        self._show_report_error("Error saving report", exc, details)
