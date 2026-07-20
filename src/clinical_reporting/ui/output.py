"""Output UI feature behaviors."""

from __future__ import annotations

"""Run, preview, and persistence mixin for the Clinical Reporting widget.

This module handles everything on the final "Preview and Save" tab,
including preview generation, report export, and saved-setting
persistence.  It also defines the :class:`ReportPreviewModel` used to
bind pandas DataFrames to Qt views.
"""

import logging
import os
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from PySide6.QtCore import Qt, QAbstractTableModel
from PySide6.QtWidgets import QFileDialog

from clinical_reporting.validation import ReportValidationError
from clinical_reporting.export import write_xlsx
from clinical_reporting.telemetry import record_successful_export

logger = logging.getLogger(__name__)

class ReportPreviewModel(QAbstractTableModel):
    """Qt model that exposes a pandas DataFrame to a :class:`QTableView`."""

    def __init__(self, data: pd.DataFrame):
        super().__init__()
        self._data = data

    def rowCount(self, parent=None):  # noqa: N802 (Qt naming convention)
        return len(self._data)

    def columnCount(self, parent=None):  # noqa: N802
        return len(self._data.columns)

    def data(self, index, role=Qt.DisplayRole):  # noqa: N802
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            value = self._data.iloc[index.row(), index.column()]
            if pd.isna(value):
                return ""
            if isinstance(value, (pd.Timestamp, datetime, np.datetime64)):
                date = pd.Timestamp(value)
                return f"{date.month}/{date.day}/{date.year}"
            if isinstance(value, (float, np.floating)) and value == int(value):
                return str(int(value))
            return str(value)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return str(self._data.columns[section])
        if orientation == Qt.Vertical:
            return str(section + 1)
        return None

class RunAndSaveMixin:
    """Behavior for previewing reports and persisting settings/results."""

    def _init_run_and_save_controls(self) -> None:
        """Connect run, save, and persistence-related buttons."""
        self.ui.pushButton_run.clicked.connect(self.click_run)
        self.ui.pushButton_save_setting.clicked.connect(self.click_save_setting)
        self.ui.pushButton_output_setting.clicked.connect(self.click_output_setting_folder)
        self.ui.checkBox_save_current_setting.stateChanged.connect(self.on_save_current_setting_state_changed)
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
                "Enable 'Save the current setting?' before selecting a settings folder.",
            )
            return

        default_dir = self._get_default_settings_directory()
        settings_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Settings Folder",
            default_dir,
        )
        if settings_dir:
            self.settings_directory = settings_dir
            self._set_label_text(
                self.label_save_confirmation,
                f"Settings folder set to {settings_dir}",
            )
            if self.ui.checkBox_saved_setting.isChecked():
                self._refresh_saved_settings()

    def click_save_setting(self) -> None:
        """Persist the current report configuration to disk."""
        if not self.ui.checkBox_save_current_setting.isChecked():
            self._set_label_text(
                self.label_save_confirmation,
                "Enable 'Save the current setting?' before saving.",
            )
            return

        settings_name = self.ui.lineEdit_setting_name.text().strip()
        if not settings_name:
            self._set_label_text(
                self.label_save_confirmation,
                "Please enter a setting name before saving.",
            )
            return

        settings_dir, error = self._prepare_settings_directory()
        if error:
            self._set_label_text(self.label_save_confirmation, error)
            return

        settings_path = os.path.join(settings_dir, f"{settings_name}.json")
        error = self._save_settings_to_path(settings_path, settings_name)
        if error:
            self._set_label_text(self.label_save_confirmation, error)
            return

        self._set_label_text(
            self.label_save_confirmation,
            f"Settings saved to {settings_path}",
        )
        if self.ui.checkBox_saved_setting.isChecked():
            self._refresh_saved_settings()

    def _prepare_settings_directory(self) -> tuple[str, Optional[str]]:
        """Ensure the settings directory exists before saving."""
        settings_dir = self.settings_directory or self._get_default_settings_directory()
        self.settings_directory = settings_dir
        try:
            os.makedirs(settings_dir, exist_ok=True)
        except OSError as exc:
            return settings_dir, f"Failed to prepare settings folder: {exc}"
        return settings_dir, None

    def _save_settings_to_path(self, path: str, settings_name: str) -> Optional[str]:
        """Serialize the current report settings to *path*."""
        try:
            self.report.save_setting_to_json(path, setting_name=settings_name)
        except Exception as exc:  # pylint: disable=broad-except
            return f"Failed to save settings: {exc}"
        return None

    # ------------------------------------------------------------------
    # Join-order conflict guarding

    #: Prefix used for the inline join-order conflict message so the button
    #: refresh can recognise (and clear) its own stale hint without clobbering
    #: unrelated run/preview status text.
    _JOIN_CONFLICT_PREFIX = "Cannot run:"

    def _join_order_conflict_message(self) -> Optional[str]:
        """Return an inline warning when selected forms share a join order.

        Returns ``None`` when every form has a unique join order.
        """
        report = getattr(self, "report", None)
        if report is None:
            return None
        conflicts = report.get_join_order_conflicts()
        if not conflicts:
            return None
        parts = [
            f"order {order} ({', '.join(forms)})"
            for order, forms in sorted(conflicts.items())
        ]
        return (
            f"{self._JOIN_CONFLICT_PREFIX} forms share the same join order — "
            f"{'; '.join(parts)}. Give each form a unique join order."
        )

    def _refresh_run_availability(self) -> None:
        """Enable/disable the Run button and surface any join-order conflict.

        Called whenever the join configuration changes so the disabled state and
        the inline hint stay in sync with the current selections.
        """
        message = self._join_order_conflict_message()
        run_button = getattr(self.ui, "pushButton_run", None)
        if run_button is not None:
            run_button.setEnabled(message is None)
        if message is not None:
            self._set_label_text(self.label_run_confirmation, message)
        elif (
            self.label_run_confirmation is not None
            and self.label_run_confirmation.text().startswith(self._JOIN_CONFLICT_PREFIX)
        ):
            # Conflict resolved: clear only our own stale hint.
            self._set_label_text(self.label_run_confirmation, "")

    # ------------------------------------------------------------------
    # Report preview and export

    def _report_validation_message(self) -> Optional[str]:
        """Return actionable validation feedback for the current report."""

        report = getattr(self, "report", None)
        if report is None:
            return f"{self._JOIN_CONFLICT_PREFIX} no report is loaded."
        issues = report.validate()
        if not issues:
            return None
        details = "\n".join(f"- {issue.message}" for issue in issues)
        return f"{self._JOIN_CONFLICT_PREFIX}\n{details}"

    def preview_report(self) -> None:
        """Generate and display a preview of the report."""
        validation_message = self._report_validation_message()
        if validation_message is not None:
            self._set_label_text(self.label_run_confirmation, validation_message)
            self.ui.tableView_preview.setModel(None)
            return
        try:
            self._set_label_text(self.label_run_confirmation, "Generating preview...")
            result_df = self.report.create_report()
            if result_df is not None and not result_df.empty:
                result_df = result_df.reset_index(drop=True)
                model = ReportPreviewModel(result_df)
                self.ui.tableView_preview.setModel(model)
                self.ui.tableView_preview.verticalHeader().setVisible(True)
                self.ui.tableView_preview.resizeColumnsToContents()
                self._set_label_text(
                    self.label_run_confirmation,
                    f"Preview generated successfully. Found {len(result_df)} rows with {len(result_df.columns)} columns.",
                )
            else:
                self._set_label_text(
                    self.label_run_confirmation,
                    "No data found. Please check your form selections, filters, and join settings.",
                )
                self.ui.tableView_preview.setModel(None)
        except ReportValidationError as exc:
            self._set_label_text(
                self.label_run_confirmation,
                f"{self._JOIN_CONFLICT_PREFIX}\n"
                + "\n".join(f"- {issue.message}" for issue in exc.issues),
            )
            self.ui.tableView_preview.setModel(None)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Error generating preview")
            self._set_label_text(
                self.label_run_confirmation,
                f"Error generating preview: {exc}",
            )
            self.ui.tableView_preview.setModel(None)

    def click_run(self) -> None:
        """Run the report and export it to an Excel file."""
        validation_message = self._report_validation_message()
        if validation_message is not None:
            self._set_label_text(self.label_run_confirmation, validation_message)
            return
        try:
            result_df = self.report.create_report()
            if result_df is None or result_df.empty:
                self._set_label_text(
                    self.label_run_confirmation,
                    "No data to save. Please check your selections and filters.",
                )
                return

            if not self.output_folder_name:
                self._set_label_text(
                    self.label_run_confirmation,
                    "Please select an output folder first.",
                )
                return

            file_name = self.ui.lineEdit_file_name.text()
            timestamp = datetime.now().strftime(" %y%m%d_%H%M%S")
            file_name += timestamp
            if not file_name.endswith(".xlsx"):
                file_name += ".xlsx"

            file_path = os.path.join(self.output_folder_name, file_name)
            # Write the report with the standard styling and short-date
            # formatting. The export logic lives in the exporter service so the
            # same output can be produced headlessly (scripts, tool chains, API).
            write_xlsx(result_df, file_path)
            try:
                # Usage counting is best-effort and must never change the
                # user's successful save outcome or produce UI feedback.
                record_successful_export()
            except Exception:  # Defensive isolation from telemetry regressions.
                pass
            self._set_label_text(
                self.label_run_confirmation,
                f"Report saved successfully to {file_path}",
            )
        except ReportValidationError as exc:
            self._set_label_text(
                self.label_run_confirmation,
                f"{self._JOIN_CONFLICT_PREFIX}\n"
                + "\n".join(f"- {issue.message}" for issue in exc.issues),
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Error saving report")
            self._set_label_text(
                self.label_run_confirmation,
                f"Error saving report: {exc}",
            )
