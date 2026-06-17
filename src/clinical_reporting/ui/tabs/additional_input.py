"""Additional input tab mixin for loading external files.

This mixin wires the buttons on the "Additional input" tab to allow users
to load CSV/Excel files, manage the selected list, and rename forms/columns.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Dict, Tuple, Set

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QListWidgetItem,
    QTableWidgetItem,
    QAbstractItemView,
    QMessageBox,
)

from clinical_reporting.core.report import CLReport
from clinical_reporting.services.util import load_tabular_file


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
            self.ui.listWidget_additional_file.itemSelectionChanged.connect(
                self._update_additional_buttons_state
            )

        form_table = getattr(self.ui, "tableWidget_update_form_name", None)
        column_table = getattr(self.ui, "tableWidget_update_column_name", None)
        if form_table is not None:
            form_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            form_table.setSelectionMode(QAbstractItemView.SingleSelection)
            form_table.itemChanged.connect(self._on_form_name_changed)
            form_table.itemSelectionChanged.connect(self._on_form_table_selection_changed)
        if column_table is not None:
            column_table.itemChanged.connect(self._on_column_name_changed)

        self._refresh_additional_files_ui()
        self._refresh_additional_tables()
        self._update_additional_buttons_state()

    # ------------------------------------------------------------------
    # Slots bound to additional input controls

    def click_add_additional_files(self) -> None:
        """Open a dialog and load user-selected additional input files."""
        default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Additional Input Files",
            default_dir,
            "Data Files (*.csv *.xls *.xlsx);;All Files (*)",
        )
        if not file_paths:
            return

        for file_path in file_paths:
            resolved_path = str(Path(file_path).expanduser().resolve())
            if resolved_path in self.additional_inputs:
                continue
            try:
                self.additional_inputs[resolved_path] = load_tabular_file(resolved_path)
            except Exception as exc:  # pylint: disable=broad-except
                print(f"Failed to load additional input '{file_path}': {exc}")

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

    def click_apply_additional_forms(self) -> None:
        """Apply the additional inputs to the report when requested."""
        self._apply_additional_inputs_to_report()

    # ------------------------------------------------------------------
    # Report integration

    def _build_additional_data_map(self) -> Dict[str, pd.DataFrame]:
        """Construct a dict of form_name -> dataframe with applied renames."""
        data_map: Dict[str, pd.DataFrame] = {}
        for file_path, df in self.additional_inputs.items():
            form_name = self.additional_form_names.get(file_path) or Path(file_path).name

            df_clean = df.copy()
            drop_cols = []
            rename_map = {}
            for column in df_clean.columns:
                column_str = str(column)
                if not column_str or column_str.lower().startswith("unnamed"):
                    drop_cols.append(column)
                    continue
                updated_name = self.additional_column_names.get((file_path, column_str))
                if updated_name and updated_name != column:
                    rename_map[column] = updated_name

            if drop_cols:
                df_clean = df_clean.drop(columns=drop_cols)
            if rename_map:
                df_clean = df_clean.rename(columns=rename_map)

            if "Subject" in df_clean.columns:
                df_clean["Subject"] = df_clean["Subject"].apply(self._strip_prefix)

            data_map[form_name] = df_clean
        return data_map

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

        # Capture current selections to restore if still applicable.
        previous_selected_forms = set(self.report.get_selected_forms_list())
        previous_selected_common = set(getattr(self.report, "selected_common_items", []))
        previous_form_items = {
            form: set(cl_form.get_selected_form_items())
            for form, cl_form in getattr(self.report, "selected_forms", {}).items()
        }

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

        # Re-select previously selected forms when they still exist.
        for form in previous_selected_forms:
            if form in self.report.available_forms:
                self.report.add_selected_form(form)

        # Re-select form items that are still available on their forms.
        for form_name, items in previous_form_items.items():
            if form_name not in self.report.selected_forms:
                continue
            cl_form = self.report.selected_forms[form_name]
            available_items = set(cl_form.get_available_form_items())
            for item in items:
                if item in available_items:
                    cl_form.set_form_item_state(item, selected=True)

        # Re-select common items that are still common; always include Subject if present.
        self.report.selected_common_items = []
        self.report.available_common_items = list(self.report.static_available_common_items)
        for common_item in previous_selected_common:
            if common_item in self.report.static_available_common_items:
                self.report.set_common_item_state(common_item, selected=True)
        if "Subject" in getattr(self.report, "static_available_common_items", []):
            self.report.set_common_item_state("Subject", selected=True)

        self.update_all_ui()

    @staticmethod
    def _strip_prefix(value):
        """Remove leading 'UPCC' or '100-' (with optional separators) from a subject string."""
        if isinstance(value, str):
            cleaned = re.sub(r"^(?:UPCC[-\s]*|100-)", "", value, flags=re.IGNORECASE)
            return cleaned.lstrip()
        return value
