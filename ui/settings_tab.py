"""Settings tab mixin for the Clinical Reporting widget.

This module collects all of the logic that interacts with filesystem
resources (input ZIP selection, saved setting folders, and saved setting
management).  The mixin exposes slot methods that are bound to the
settings tab controls from :class:`ui.main_widget.Widget`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QFileDialog

from CLReport import CLReport
from util import read_data_dict_zip_corelisting


class SettingsTabMixin:
    """Behavior for the settings tab and saved-setting management."""

    def _init_settings_tab(self) -> None:
        """Wire up controls on the settings tab."""
        self.ui.pushButton_input_file.clicked.connect(self.click_input_file)
        self.ui.pushButton_output_folder.clicked.connect(self.click_output_file)
        self.ui.checkBox_saved_setting.stateChanged.connect(
            self.click_checkBox_saved_setting
        )
        self.ui.comboBox_saved_setting.setEnabled(False)
        self.ui.comboBox_saved_setting.clear()
        self.ui.comboBox_saved_setting.currentIndexChanged.connect(
            self.on_saved_setting_changed
        )
        self.ui.pushButton_setting_location.clicked.connect(
            self.click_setting_location
        )

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
        file_name = os.path.basename(file_path)
        file_parts = file_name.split("_")
        if len(file_parts) > 2:
            self.study_name = file_parts[2]
        else:
            self.study_name = os.path.splitext(file_name)[0]
        self.report.set_study_name(self.study_name)
        self.report.set_data(read_data_dict_zip_corelisting(file_path))

        # Ensure "Subject" is selected by default and refresh all UI tabs.
        self.report.set_common_item_state("Subject", selected=True)
        self.update_all_ui()
        self.ui.label_input_file.setText("Input path: " + file_path)
        self._set_label_text(self.label_setting, "")

        if self.ui.checkBox_saved_setting.isChecked():
            if self.settings_directory is None:
                self.settings_directory = self._get_default_settings_directory()
            self._refresh_saved_settings()

    def click_output_file(self) -> None:
        """Allow the user to choose the output directory for reports."""
        default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            default_dir,
        )
        if folder:
            self.output_folder_name = folder
            if self.label_output_folder is not None:
                self.label_output_folder.setText(f"Output folder: {folder}")

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

    def _get_default_settings_directory(self) -> str:
        """Return the default folder used to store saved settings."""
        home = Path.home()
        default_dir = home / "Documents"
        return str(default_dir)

    def click_setting_location(self) -> None:
        """Let the user choose the directory that stores saved settings."""
        default_dir = self.settings_directory or self._get_default_settings_directory()
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

    # ------------------------------------------------------------------
    # Saved settings helpers

    def _refresh_saved_settings(self) -> None:
        """Populate the saved settings combo box for the current study."""
        combo = self.ui.comboBox_saved_setting
        combo.blockSignals(True)
        combo.clear()

        settings_dir = self.settings_directory or self._get_default_settings_directory()
        settings_path = Path(settings_dir)
        if not settings_path.exists():
            combo.addItem("No saved settings found for this study", None)
            combo.blockSignals(False)
            combo.setEnabled(False)
            return

        saved_any = False
        study_name = self.study_name
        for settings_file in settings_path.glob("*.json"):
            try:
                with settings_file.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except (OSError, json.JSONDecodeError) as exc:
                print(f"Skipping invalid settings file {settings_file}: {exc}")
                continue

            if study_name and data.get("study_name") != study_name:
                continue

            display_name = data.get("setting_name") or settings_file.stem
            combo.addItem(display_name, str(settings_file))
            saved_any = True

        if saved_any:
            combo.insertItem(0, "Select a saved setting", None)
            combo.setEnabled(True)
        else:
            combo.addItem("No saved settings found for this study", None)
            combo.setEnabled(False)

        combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def on_saved_setting_changed(self, index: int) -> None:
        """Load the selected saved setting into the report."""
        if index < 0:
            return

        file_path: Optional[str] = self.ui.comboBox_saved_setting.itemData(index)
        if not file_path:
            self._set_label_text(self.label_setting, "")
            return

        try:
            settings_data = self.report.load_setting_from_json(file_path)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"Failed to load settings from {file_path}: {exc}")
            self._set_label_text(
                self.label_save_confirmation,
                f"Failed to load settings: {exc}",
            )
            self._set_label_text(self.label_setting, "")
            return

        loaded_study_name = (
            settings_data.get("study_name") if isinstance(settings_data, dict) else None
        )
        if loaded_study_name:
            self.study_name = loaded_study_name
        self.report.set_study_name(self.study_name)

        reconciliation = self.report.reconcile_with_current_data()
        self.update_all_ui()
        self.update_items_dependent_ui()

        missing_forms = reconciliation.get("forms", [])
        missing_items = reconciliation.get("items", [])
        if missing_forms or missing_items:
            message_parts = []
            if missing_forms:
                message_parts.append(
                    "Missing forms: " + ", ".join(missing_forms)
                )
            if missing_items:
                message_parts.append(
                    "Missing items: " + ", ".join(missing_items)
                )
            self._set_label_text(self.label_setting, "\n".join(message_parts))
        else:
            self._set_label_text(self.label_setting, "")

        setting_name = self.ui.comboBox_saved_setting.currentText()
        if setting_name:
            self.ui.lineEdit_setting_name.setText(setting_name)
        self._set_label_text(
            self.label_save_confirmation,
            f"Loaded settings from {os.path.basename(file_path)}",
        )

