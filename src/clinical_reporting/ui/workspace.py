"""Workspace UI feature behaviors."""

from __future__ import annotations

"""Settings tab mixin for the Clinical Reporting widget.

This module collects all of the logic that interacts with filesystem
resources (input ZIP selection, saved setting folders, and saved setting
management).  The mixin exposes slot methods that are bound to the
settings tab controls from :class:`ui.window.Widget`.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QFileDialog

from clinical_reporting.report import CLReport
from clinical_reporting.data import parse_study_name, read_data_dict_zip_corelisting

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
        self.update_items_dependent_ui()

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
        self.update_items_dependent_ui()

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

    def _get_default_settings_directory(self) -> str:
        """Return the default folder used to store saved settings."""
        home = Path.home()
        default_dir = home / "Documents"
        return str(default_dir)

    def click_setting_location(self) -> None:
        """Let the user choose the directory that stores saved settings."""
        initial_dir = self.settings_directory or self._get_default_settings_directory()
        settings_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Settings Folder",
            initial_dir,
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
                logger.warning("Skipping invalid settings file %s: %s", settings_file, exc)
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
        """Load saved settings from ``file_path`` and reconcile with current data."""
        try:
            settings_data = self.report.load_setting_from_json(file_path)
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
        self.update_items_dependent_ui()
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


"""Additional input tab mixin for loading external files.

This mixin wires the buttons on the "Additional input" tab to allow users
to load CSV/Excel files, manage the selected list, and rename forms/columns.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Tuple, Set

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QListWidgetItem,
    QTableWidgetItem,
    QAbstractItemView,
    QMessageBox,
)

from clinical_reporting.report import CLReport
from clinical_reporting.data import (
    build_additional_data_map,
    load_tabular_file,
    strip_subject_prefix,
)

logger = logging.getLogger(__name__)


class AdditionalInputTabMixin:
    """Behavior for the additional input tab."""

    def _init_additional_input_tab(self) -> None:
        """Attach handlers and prepare state for the additional input tab."""
        self.additional_inputs: Dict[str, pd.DataFrame] = {}
        self.additional_form_names: Dict[str, str] = {}
        self.additional_column_names: Dict[Tuple[str, str], str] = {}
        self._additional_form_keys: Set[str] = set()
        self._additional_input_signature: Dict[str, Tuple[str, ...]] = {}
        self._populating_additional_tables = False

        add_button = getattr(self.ui, "pushButton_additional_file_add", None)
        remove_button = getattr(self.ui, "pushButton_additional_file_remove", None)
        if remove_button is None:
            remove_button = getattr(self.ui, "pushButton_additional_file_2", None)
            if remove_button is not None:
                self.ui.pushButton_additional_file_remove = remove_button
        apply_button = getattr(self.ui, "pushButton_additional_file_add_2", None)

        # Alias the generated table names to clearer attributes if needed.
        if not hasattr(self.ui, "tableWidget_update_form_name"):
            self.ui.tableWidget_update_form_name = getattr(self.ui, "tableWidget_2", None)
        if not hasattr(self.ui, "tableWidget_update_column_name"):
            self.ui.tableWidget_update_column_name = getattr(self.ui, "tableWidget_", None)

        if add_button is not None:
            add_button.clicked.connect(self.click_add_additional_files)
        if remove_button is not None:
            remove_button.clicked.connect(self.click_remove_additional_files)
        if apply_button is not None:
            apply_button.clicked.connect(self.click_apply_additional_forms)

        if hasattr(self.ui, "listWidget_additional_file"):
            self.ui.listWidget_additional_file.itemSelectionChanged.connect(self._update_additional_buttons_state)

        form_table = getattr(self.ui, "tableWidget_update_form_name", None)
        column_table = getattr(self.ui, "tableWidget_update_column_name", None)
        if form_table is not None:
            form_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            form_table.setSelectionMode(QAbstractItemView.SingleSelection)
            form_table.itemChanged.connect(self._on_form_name_changed)
            form_table.itemSelectionChanged.connect(self._on_form_table_selection_changed)
        if column_table is not None:
            column_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            column_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
            self.copy_new_column_name_action = QAction(
                "Copy Original Item Name to New Item Name",
                column_table,
            )
            self.copy_new_column_name_action.setToolTip(
                "Copy the original item name for each selected row into its new item name cell"
            )
            self.copy_new_column_name_action.triggered.connect(self.copy_selected_new_column_names_to_updated)
            column_table.addAction(self.copy_new_column_name_action)
            column_table.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
            column_table.itemChanged.connect(self._on_column_name_changed)

        self._refresh_additional_files_ui()
        self._refresh_additional_tables()
        self._update_additional_buttons_state()

    # ------------------------------------------------------------------
    # Slots bound to additional input controls

    def click_add_additional_files(self) -> None:
        """Open a dialog and load user-selected additional input files."""
        initial_dir = (
            getattr(self, "_additional_input_directory", None)
            or os.path.join(os.path.expanduser("~"), "Downloads")
        )
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Additional Input Files",
            initial_dir,
            "Data Files (*.csv *.xls *.xlsx);;All Files (*)",
        )
        if not file_paths:
            return

        self._additional_input_directory = str(
            Path(file_paths[0]).expanduser().resolve().parent
        )

        for file_path in file_paths:
            resolved_path = str(Path(file_path).expanduser().resolve())
            if resolved_path in self.additional_inputs:
                continue
            try:
                self.additional_inputs[resolved_path] = load_tabular_file(resolved_path)
            except Exception:  # pylint: disable=broad-except
                logger.exception("Failed to load additional input '%s'", file_path)

        self._refresh_additional_files_ui()
        self._refresh_additional_tables()
        self._update_additional_buttons_state()

    def click_remove_additional_files(self) -> None:
        """Remove selected additional input files from the list."""
        widget = getattr(self.ui, "listWidget_additional_file", None)
        if widget is None:
            return

        selected_items = widget.selectedItems()
        if not selected_items:
            return

        removed_paths = []
        for item in selected_items:
            file_path = item.data(Qt.UserRole) or item.text()
            self.additional_inputs.pop(file_path, None)
            self.additional_form_names.pop(file_path, None)
            removed_paths.append(file_path)
            widget.takeItem(widget.row(item))

        if removed_paths:
            # Drop any column rename entries tied to removed files.
            self.additional_column_names = {
                key: val for key, val in self.additional_column_names.items() if key[0] not in removed_paths
            }

        self._refresh_additional_tables()
        self._update_additional_buttons_state()

    # ------------------------------------------------------------------
    # UI helpers

    def _refresh_additional_files_ui(self) -> None:
        """Populate the additional file list widget with current selections."""
        widget = getattr(self.ui, "listWidget_additional_file", None)
        if widget is None:
            return

        widget.clear()
        for file_path in sorted(self.additional_inputs):
            display_name = Path(file_path).name
            item = QListWidgetItem(display_name)
            item.setToolTip(file_path)
            item.setData(Qt.UserRole, file_path)
            widget.addItem(item)

    def _refresh_additional_tables(self) -> None:
        """Refresh the form/column rename tables."""
        self._populating_additional_tables = True
        try:
            self._populate_form_name_table()
            self._ensure_form_selection()
            self._populate_column_name_table()
        finally:
            self._populating_additional_tables = False

    def _populate_form_name_table(self) -> None:
        """Populate tableWidget_update_form_name with file names and editable form names."""
        table = getattr(self.ui, "tableWidget_update_form_name", None)
        if table is None:
            return

        table.blockSignals(True)
        paths = sorted(self.additional_inputs, key=lambda p: Path(p).name)
        table.setRowCount(len(paths))
        for row, file_path in enumerate(paths):
            file_name = Path(file_path).name
            item_name = QTableWidgetItem(file_name)
            item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable)
            item_name.setData(Qt.UserRole, file_path)
            table.setItem(row, 0, item_name)

            updated_name = self.additional_form_names.get(file_path, "")
            item_updated = QTableWidgetItem(updated_name)
            item_updated.setData(Qt.UserRole, file_path)
            table.setItem(row, 1, item_updated)
        table.blockSignals(False)

    def _populate_column_name_table(self) -> None:
        """Populate tableWidget_update_column_name with column headers for selected files."""
        table = getattr(self.ui, "tableWidget_update_column_name", None)
        if table is None:
            return

        table.blockSignals(True)
        rows = []
        for file_path in self._selected_form_paths():
            df = self.additional_inputs.get(file_path)
            if df is None:
                continue
            for column_name in df.columns:
                column_str = str(column_name)
                if not column_str or column_str.lower().startswith("unnamed"):
                    continue
                rows.append((file_path, column_str))

        table.setRowCount(len(rows))
        for row_index, (file_path, column_name) in enumerate(rows):
            new_column_display = column_name
            item_new_column = QTableWidgetItem(new_column_display)
            item_new_column.setFlags(item_new_column.flags() & ~Qt.ItemIsEditable)
            item_new_column.setData(Qt.UserRole, (file_path, column_name))
            table.setItem(row_index, 0, item_new_column)

            updated_column_name = self.additional_column_names.get((file_path, column_name), "")
            item_updated = QTableWidgetItem(updated_column_name)
            item_updated.setData(Qt.UserRole, (file_path, column_name))
            table.setItem(row_index, 1, item_updated)
        table.blockSignals(False)

    def _update_additional_buttons_state(self) -> None:
        """Enable or disable the remove button based on selection state."""
        widget = getattr(self.ui, "listWidget_additional_file", None)
        remove_button = getattr(self.ui, "pushButton_additional_file_remove", None)
        if widget is None or remove_button is None:
            return

        remove_button.setEnabled(bool(widget.selectedItems()))

    def _ensure_form_selection(self) -> None:
        """Ensure at least one row is selected to drive the column table."""
        table = getattr(self.ui, "tableWidget_update_form_name", None)
        if table is None or table.rowCount() == 0:
            return
        if not table.selectedItems():
            table.selectRow(0)

    def _selected_form_paths(self) -> list[str]:
        """Return the file paths for currently selected form rows."""
        table = getattr(self.ui, "tableWidget_update_form_name", None)
        if table is None or table.selectionModel() is None:
            return []
        rows = {index.row() for index in table.selectionModel().selectedRows()}
        paths = []
        for row in rows:
            item = table.item(row, 0)
            if item is None:
                continue
            file_path = item.data(Qt.UserRole)
            if file_path:
                paths.append(file_path)
        return paths

    # ------------------------------------------------------------------
    # Signal handlers for table edits

    def _on_form_name_changed(self, item: QTableWidgetItem) -> None:
        """Persist changes to the updated form name and refresh dependent UI."""
        if self._populating_additional_tables or item.column() != 1:
            return

        file_path = item.data(Qt.UserRole)
        if not file_path:
            return

        new_name = item.text().strip()
        if new_name:
            self.additional_form_names[file_path] = new_name
        else:
            self.additional_form_names.pop(file_path, None)

        self._populate_column_name_table()

    def _on_form_table_selection_changed(self) -> None:
        """Refresh the column table when the selected form changes."""
        if self._populating_additional_tables:
            return
        self._populate_column_name_table()

    def _on_column_name_changed(self, item: QTableWidgetItem) -> None:
        """Persist changes to the updated column name."""
        if self._populating_additional_tables or item.column() != 1:
            return

        key = item.data(Qt.UserRole)
        if not key:
            return

        new_name = item.text().strip()
        if new_name:
            self.additional_column_names[key] = new_name
        else:
            self.additional_column_names.pop(key, None)

    def copy_selected_new_column_names_to_updated(self) -> None:
        """Copy selected new-column values into their updated-name cells."""
        table = getattr(self.ui, "tableWidget_update_column_name", None)
        if table is None or table.selectionModel() is None:
            return

        signals_were_blocked = table.blockSignals(True)
        try:
            for index in table.selectionModel().selectedRows(0):
                new_column_item = table.item(index.row(), 0)
                updated_name_item = table.item(index.row(), 1)
                if new_column_item is None or updated_name_item is None:
                    continue

                key = updated_name_item.data(Qt.UserRole)
                updated_name = new_column_item.text()
                updated_name_item.setText(updated_name)
                if key:
                    self.additional_column_names[key] = updated_name
        finally:
            table.blockSignals(signals_were_blocked)

    def click_apply_additional_forms(self) -> None:
        """Apply the additional inputs to the report when requested."""
        self._apply_additional_inputs_to_report()

    # ------------------------------------------------------------------
    # Report integration

    def _build_additional_data_map(self) -> Dict[str, pd.DataFrame]:
        """Construct a dict of form_name -> dataframe with applied renames.

        Delegates to :func:`clinical_reporting.data.build_additional_data_map`
        so the same shaping logic is reusable headlessly.
        """
        return build_additional_data_map(
            self.additional_inputs,
            self.additional_form_names,
            self.additional_column_names,
        )

    @staticmethod
    def _build_additional_input_signature(data_map: Dict[str, pd.DataFrame]) -> Dict[str, Tuple[str, ...]]:
        """Summarize additional inputs by form name and column names."""
        signature: Dict[str, Tuple[str, ...]] = {}
        for form_name, df in data_map.items():
            signature[form_name] = tuple(str(column) for column in df.columns)
        return signature

    def _collect_additional_form_names(self) -> Dict[str, str]:
        """Return a mapping of file path -> form name for additional inputs."""
        form_names = {}
        for file_path in self.additional_inputs:
            form_name = self.additional_form_names.get(file_path) or Path(file_path).name
            form_names[file_path] = form_name
        return form_names

    def _warn_on_additional_form_conflicts(self, existing_forms: Set[str]) -> bool:
        """Warn when additional forms would overwrite existing form names."""
        name_map = self._collect_additional_form_names()
        if not name_map:
            return False

        dotted_names = sorted({name for name in name_map.values() if "." in name})
        name_to_paths: Dict[str, list[str]] = {}
        for file_path, form_name in name_map.items():
            name_to_paths.setdefault(form_name, []).append(file_path)

        duplicates = {form_name: paths for form_name, paths in name_to_paths.items() if len(paths) > 1}
        conflicts = {form_name: paths for form_name, paths in name_to_paths.items() if form_name in existing_forms}

        if not dotted_names and not duplicates and not conflicts:
            return False

        message_parts = ["Cannot add forms because some form names are invalid or conflict with existing data."]
        if dotted_names:
            message_parts.append("Form names cannot include '.':")
            message_parts.append("  - " + ", ".join(dotted_names))
        if duplicates:
            message_parts.append("Duplicate names in additional forms:")
            for form_name in sorted(duplicates):
                file_list = ", ".join(sorted(Path(path).name for path in duplicates[form_name]))
                message_parts.append(f"  - {form_name}: {file_list}")
        if conflicts:
            message_parts.append("Conflicts with existing report forms:")
            for form_name in sorted(conflicts):
                file_list = ", ".join(sorted(Path(path).name for path in conflicts[form_name]))
                message_parts.append(f"  - {form_name}: {file_list}")
        message_parts.append("Rename the forms in the table and try again.")

        QMessageBox.warning(self, "Form Name Conflict", "\n".join(message_parts))
        return True

    def _apply_additional_inputs_to_report(self) -> None:
        """Merge additional inputs into the current report and refresh UI."""
        # Ensure a report object exists.
        if not hasattr(self, "report") or self.report is None:
            self.report = CLReport()

        previous_signature = dict(getattr(self, "_additional_input_signature", {}))

        # Capture current selections (forms/items/common/join) to restore after
        # ``set_data`` rebuilds fresh CLForm objects with defaults.
        selection_state = self._capture_selection_state()

        base_data = dict(getattr(self.report, "data", {}) or {})
        # Remove previously injected additional forms.
        for form_key in getattr(self, "_additional_form_keys", set()):
            base_data.pop(form_key, None)

        if self._warn_on_additional_form_conflicts(set(base_data)):
            return

        additional_data = self._build_additional_data_map()
        new_signature = self._build_additional_input_signature(additional_data)
        signature_changed = new_signature != previous_signature

        combined_data = {**base_data, **additional_data}

        self.report.set_data(combined_data)
        self._additional_form_keys = set(additional_data.keys())
        self._additional_input_signature = new_signature

        if (
            signature_changed
            and new_signature
            and getattr(self, "_pending_saved_setting_reapply", False)
            and getattr(self, "_last_loaded_setting_path", None)
        ):
            if self._apply_saved_setting_from_path(
                self._last_loaded_setting_path,
                update_confirmation=False,
            ):
                return

        # Restore the selections that survive in the rebuilt report.
        self._restore_selection_state(selection_state)

        self.update_all_ui()

    @staticmethod
    def _strip_prefix(value):
        """Remove leading 'UPCC' or '100-' (with optional separators) from a subject string.

        Thin wrapper over
        :func:`clinical_reporting.data.strip_subject_prefix`.
        """
        return strip_subject_prefix(value)
