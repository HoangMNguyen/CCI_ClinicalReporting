"""Settings tab mixin for the Clinical Reporting widget.

This module collects all of the logic that interacts with filesystem
resources (input ZIP selection, saved setting folders, and saved setting
management).  The mixin exposes slot methods that are bound to the
settings tab controls from :class:`ui.window.Widget`.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QFileDialog

from clinical_reporting.data import parse_study_name, read_data_dict_zip_corelisting
from clinical_reporting.report import CLReport
from clinical_reporting.ui.dialogs import choose_settings_directory

logger = logging.getLogger(__name__)


class SettingsTabMixin:
    """Behavior for the settings tab and saved-setting management."""

    def _init_settings_tab(self) -> None:
        """Wire up controls on the settings tab."""
        self.ui.pushButton_input_file.clicked.connect(self.click_input_file)
        self.ui.pushButton_remove_input.clicked.connect(self.click_remove_input)
        self.ui.pushButton_remove_input.setEnabled(bool(self._input_file_path))
        self.ui.pushButton_output_folder.clicked.connect(self.click_output_file)
        self.ui.checkBox_saved_setting.stateChanged.connect(self.click_checkBox_saved_setting)
        self.ui.comboBox_saved_setting.setEnabled(False)
        self.ui.comboBox_saved_setting.clear()
        self.ui.comboBox_saved_setting.currentIndexChanged.connect(self.on_saved_setting_changed)
        self.ui.pushButton_setting_location.clicked.connect(self.click_setting_location)

        # Cut-off date is disabled until the user opts in via the checkbox, and
        # defaults to today's date.
        self.ui.cutoff_checkBox.setChecked(False)
        self.ui.cutoff_dateEdit.setEnabled(False)
        self.ui.cutoff_dateEdit.setDate(QDate.currentDate())
        self.ui.cutoff_checkBox.stateChanged.connect(self.click_cutoff_checkBox)
        self.ui.cutoff_dateEdit.editingFinished.connect(self._reload_with_current_cut_off)

    # ------------------------------------------------------------------
    # Slots bound to settings tab buttons

    def click_input_file(self) -> None:
        """Open a file dialog to choose the input Corelisting ZIP file."""
        default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select the input Corelisting zip file",
            default_dir,
            "Zip files (*.zip);;All Files (*)",
        )
        if not file_path:
            return

        # Reset the report to avoid stale state from a previous load.
        self.report = CLReport()
        self._last_loaded_setting_path = None
        self._pending_saved_setting_reapply = False
        self.study_name = parse_study_name(file_path)
        self.report.set_study_name(self.study_name)
        cut_off_date = self._get_cut_off_date()
        self.report.set_data(read_data_dict_zip_corelisting(file_path, cut_off_date=cut_off_date))
        # Remember the source so the cut-off can be re-applied without re-picking.
        self._input_file_path = file_path
        self._applied_cut_off_date = cut_off_date
        self.ui.pushButton_remove_input.setEnabled(True)

        # Ensure "Subject" is selected by default and refresh all UI tabs.
        self.report.set_common_item_state("Subject", selected=True)
        self.update_all_ui()
        self.ui.label_input_file.setText("Input path: " + file_path)
        self._set_label_text(self.label_setting, "")

        if self.ui.checkBox_saved_setting.isChecked():
            if self.settings_directory is None:
                self.settings_directory = self._get_default_settings_directory()
            self._refresh_saved_settings()

    def click_remove_input(self) -> None:
        """Remove the selected Corelisting ZIP and its forms from the report.

        Additional inputs are independent of the Corelisting ZIP, so forms
        already applied from the additional-input tab remain available.
        """
        if not self._input_file_path:
            return

        selection_state = self._capture_selection_state()
        additional_keys = getattr(self, "_additional_form_keys", set())
        additional_data = {
            key: value for key, value in (getattr(self.report, "data", {}) or {}).items() if key in additional_keys
        }

        # Start with a clean report so filters, ordering, renames, and other
        # configuration tied to the removed Corelisting forms cannot linger.
        self.report = CLReport()
        if additional_data:
            self.report.set_data(additional_data)
            self._restore_selection_state(selection_state)

        self.study_name = None
        self._input_file_path = None
        self._applied_cut_off_date = None
        self._last_loaded_setting_path = None
        self._pending_saved_setting_reapply = False

        self.ui.label_input_file.setText("")
        self.ui.pushButton_remove_input.setEnabled(False)
        self._set_label_text(self.label_setting, "")

        # Saved settings are study-specific; repopulate them after another ZIP
        # establishes the study name.
        self.ui.comboBox_saved_setting.clear()
        self.ui.comboBox_saved_setting.setEnabled(False)

        self.update_all_ui()

    def click_output_file(self) -> None:
        """Allow the user to choose the output directory for reports."""
        initial_dir = self.output_folder_name or os.path.join(
            os.path.expanduser("~"),
            "Downloads",
        )
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            initial_dir,
        )
        if folder:
            self.output_folder_name = folder
            if self.label_output_folder is not None:
                self.label_output_folder.setText(f"Output folder: {folder}")

    def click_cutoff_checkBox(self, state: int) -> None:
        """Enable the date editor and re-apply the cut-off when toggled."""
        self.ui.cutoff_dateEdit.setEnabled(bool(state))
        self._reload_with_current_cut_off()

    def _get_cut_off_date(self):
        """Return the selected cut-off date, or ``None`` when disabled.

        The cut-off date is only applied when :attr:`cutoff_checkBox` is
        checked; otherwise all data is loaded regardless of event date.
        """
        if not self.ui.cutoff_checkBox.isChecked():
            return None
        return self.ui.cutoff_dateEdit.date().toPython()

    def _reload_with_current_cut_off(self) -> None:
        """Re-read the input ZIP with the current cut-off date.

        The cut-off filters rows while the ZIP is read, so changing it (or
        toggling the checkbox) after a file is loaded requires re-reading the
        data. Existing form/item/common selections and any loaded additional
        inputs are preserved where they remain valid. This is a no-op when no
        input file is loaded yet or the effective cut-off has not changed.
        """
        input_path = self._input_file_path
        if not input_path:
            return

        cut_off_date = self._get_cut_off_date()
        if cut_off_date == self._applied_cut_off_date:
            return

        selection_state = self._capture_selection_state()

        base_data = read_data_dict_zip_corelisting(input_path, cut_off_date=cut_off_date)

        # Preserve any additional-input forms currently merged into the report.
        additional_keys = getattr(self, "_additional_form_keys", set())
        preserved_additional = {
            key: value for key, value in (getattr(self.report, "data", {}) or {}).items() if key in additional_keys
        }

        self.report.set_data({**base_data, **preserved_additional})
        self._restore_selection_state(selection_state)
        self._applied_cut_off_date = cut_off_date

        self.update_all_ui()

    def click_checkBox_saved_setting(self, state: int) -> None:
        """Enable or disable saved setting controls based on the checkbox."""
        enabled = bool(state)
        self.ui.comboBox_saved_setting.setEnabled(enabled)
        self.ui.pushButton_setting_location.setEnabled(enabled)
        if enabled:
            if self.settings_directory is None:
                self.settings_directory = self._get_default_settings_directory()
            self._refresh_saved_settings()
        else:
            self.ui.comboBox_saved_setting.clear()
            self.ui.comboBox_saved_setting.setEnabled(False)
            self._set_label_text(self.label_setting, "")
            self._last_loaded_setting_path = None
            self._pending_saved_setting_reapply = False

    def click_setting_location(self) -> None:
        """Let the user choose the directory that stores saved settings."""
        choose_settings_directory(self)

    # ------------------------------------------------------------------
    # Saved settings helpers

    def _refresh_saved_settings(self) -> None:
        """Populate the saved settings combo box for the current study."""
        combo = self.ui.comboBox_saved_setting
        combo.blockSignals(True)
        combo.clear()

        saved_settings = self._settings_store().list(self.study_name)
        for saved in saved_settings:
            combo.addItem(saved.name, saved.key)

        if saved_settings:
            combo.insertItem(0, "Select a saved setting", None)
            combo.setEnabled(True)
        else:
            combo.addItem("No saved settings found for this study", None)
            combo.setEnabled(False)

        combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def _update_saved_setting_warning(self, reconciliation: dict) -> None:
        """Update the warning label and reapply flag for missing setting data."""
        missing_forms = reconciliation.get("forms", [])
        missing_items = reconciliation.get("items", [])

        self._pending_saved_setting_reapply = bool(missing_forms or missing_items)

        if missing_forms or missing_items:
            message_parts = []
            if missing_forms:
                message_parts.append("Missing forms: " + ", ".join(missing_forms))
            if missing_items:
                common_items = []
                form_items: dict[str, list[str]] = {}
                for item in missing_items:
                    item_str = str(item)
                    if "." in item_str:
                        form_name, item_name = item_str.split(".", 1)
                        if form_name and item_name:
                            form_items.setdefault(form_name, []).append(item_name)
                        else:
                            common_items.append(item_str)
                    else:
                        common_items.append(item_str)

                if common_items:
                    message_parts.append("Missing common items: " + ", ".join(sorted(common_items)))
                for form_name in sorted(form_items):
                    message_parts.append(f"Missing items in {form_name}: " + ", ".join(sorted(form_items[form_name])))
            self._set_label_text(self.label_setting, "\n".join(message_parts))
        else:
            self._set_label_text(self.label_setting, "")

    def _apply_saved_setting_from_path(self, file_path: str, *, update_confirmation: bool = True) -> bool:
        """Load the saved setting at ``file_path`` and reconcile it with the data."""
        try:
            stored = self._settings_store().load(file_path)
            settings_data = self.report.load_setting_from_dict(stored)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to load settings from %s", file_path)
            self._set_label_text(
                self.label_save_confirmation,
                f"Failed to load settings: {exc}",
            )
            self._set_label_text(self.label_setting, "")
            self._pending_saved_setting_reapply = False
            return False

        loaded_study_name = settings_data.get("study_name") if isinstance(settings_data, dict) else None
        if loaded_study_name:
            self.study_name = loaded_study_name
        self.report.set_study_name(self.study_name)

        reconciliation = self.report.reconcile_with_current_data()
        self.update_all_ui()
        self._update_saved_setting_warning(reconciliation)

        if update_confirmation:
            self._set_label_text(
                self.label_save_confirmation,
                f"Loaded settings from {os.path.basename(file_path)}",
            )
        return True

    def on_saved_setting_changed(self, index: int) -> None:
        """Load the selected saved setting into the report."""
        if index < 0:
            return

        file_path: Optional[str] = self.ui.comboBox_saved_setting.itemData(index)
        if not file_path:
            self._set_label_text(self.label_setting, "")
            self._last_loaded_setting_path = None
            self._pending_saved_setting_reapply = False
            return

        if not self._apply_saved_setting_from_path(file_path, update_confirmation=True):
            self._last_loaded_setting_path = None
            self._pending_saved_setting_reapply = False
            return

        self._last_loaded_setting_path = file_path

        setting_name = self.ui.comboBox_saved_setting.currentText()
        if setting_name:
            self.ui.lineEdit_setting_name.setText(setting_name)
