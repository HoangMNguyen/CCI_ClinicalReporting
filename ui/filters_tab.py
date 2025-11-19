"""Filter management mixin for the Clinical Reporting widget.

This module contains all code related to static and dynamic filters.
It provides helper routines for wiring combo boxes, synchronising the
:class:`CLReport` filter collections with the UI tables, and responding to
user edits.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QTableWidgetItem


class FiltersTabMixin:
    """Behavior for managing static and dynamic filters."""

    def _init_filters_tab(self) -> None:
        """Attach filter-related button handlers."""
        self.ui.pushButton_static_filter_add.clicked.connect(
            self.static_filter_add
        )
        self.ui.pushButton_static_filter_remove.clicked.connect(
            self.static_filter_remove
        )
        self.ui.pushButton_dynamic_filter_add.clicked.connect(
            self.dynamic_filter_add
        )
        self.ui.pushButton_dynamic_filter_remove.clicked.connect(
            self.dynamic_filter_remove
        )

    # ------------------------------------------------------------------
    # Static filters

    def update_static_filter_table(self) -> None:
        """Populate the static filter table using report data."""
        try:
            self.ui.tableWidget_static_filter.itemChanged.disconnect()
        except Exception:
            pass

        self.ui.tableWidget_static_filter.setRowCount(0)
        for item, operator, value in self.report.get_static_filter_items():
            row = self.ui.tableWidget_static_filter.rowCount()
            self.ui.tableWidget_static_filter.insertRow(row)
            self._add_dropdown(row, 0, "item", item)
            self._add_dropdown(row, 1, "operator", operator)
            value_item = QTableWidgetItem(value)
            self.ui.tableWidget_static_filter.setItem(row, 2, value_item)

        self.ui.tableWidget_static_filter.itemChanged.connect(
            self._on_filter_changed
        )
        self._adjust_column_widths(self.ui.tableWidget_static_filter)

    def synchronize_static_filters(self) -> None:
        """Synchronise the report's filter list with the table contents."""
        new_filters = []
        for row in range(self.ui.tableWidget_static_filter.rowCount()):
            item_combo = self.ui.tableWidget_static_filter.cellWidget(row, 0)
            operator_combo = self.ui.tableWidget_static_filter.cellWidget(row, 1)
            value_item = self.ui.tableWidget_static_filter.item(row, 2)
            if item_combo and operator_combo and value_item:
                item = item_combo.currentText()
                operator = operator_combo.currentText()
                value = value_item.text()
                if item and operator:
                    new_filters.append((item, operator, value))

        self.report.set_static_filter_items([])
        for item, operator, value in new_filters:
            self.report.add_static_filter_item(item, operator, value)
        print(f"Synchronized static filters: {self.report.get_static_filter_items()}")

    def _add_dropdown(
        self,
        row: int,
        column: int,
        dropdown_type: str,
        selected_value: Optional[str] = None,
    ) -> None:
        """Add an item or operator dropdown to the static filter table."""
        combo = QComboBox()

        if dropdown_type == "item":
            all_items = []
            for item in self.report.get_selected_common_items():
                all_items.append(item)
            for form_name in self.report.get_selected_forms_list():
                form = self.report.selected_forms[form_name]
                for item in form.get_selected_form_items():
                    all_items.append(f"{form_name}.{item}")
            all_items.sort()
            for item in all_items:
                combo.addItem(item)

        elif dropdown_type == "operator":
            operators = [
                "=",
                "!=",
                ">",
                ">=",
                "<",
                "<=",
                "Contains",
                "Does not contain",
                "In",
                "Not in",
                "is Null",
                "is not Null",
            ]
            for op in operators:
                combo.addItem(op)
            combo.currentTextChanged.connect(
                lambda text, r=row: self._on_operator_changed(r, text)
            )

        if selected_value:
            combo.setCurrentText(selected_value)

        combo.currentTextChanged.connect(lambda: self._on_filter_changed(row))
        self.ui.tableWidget_static_filter.setCellWidget(row, column, combo)

        if dropdown_type == "operator" and selected_value in {"is Null", "is not Null"}:
            self._on_operator_changed(row, selected_value)

    def _on_operator_changed(self, row: int, operator_text: str) -> None:
        """Enable/disable the value column based on the chosen operator."""
        value_item = self.ui.tableWidget_static_filter.item(row, 2)
        if operator_text in {"is Null", "is not Null"}:
            if value_item is None:
                value_item = QTableWidgetItem("")
                self.ui.tableWidget_static_filter.setItem(row, 2, value_item)
            value_item.setText("")
            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEnabled)
        else:
            if value_item is None:
                value_item = QTableWidgetItem("")
                self.ui.tableWidget_static_filter.setItem(row, 2, value_item)
            value_item.setFlags(
                value_item.flags() | Qt.ItemIsEnabled | Qt.ItemIsEditable
            )

    def static_filter_add(self) -> None:
        """Add a fresh static filter row."""
        row = self.ui.tableWidget_static_filter.rowCount()
        self.ui.tableWidget_static_filter.insertRow(row)

        try:
            self.ui.tableWidget_static_filter.itemChanged.disconnect()
        except Exception:
            pass

        self._add_dropdown(row, 0, "item")
        self._add_dropdown(row, 1, "operator", "=")
        value_item = QTableWidgetItem("")
        self.ui.tableWidget_static_filter.setItem(row, 2, value_item)

        item_combo = self.ui.tableWidget_static_filter.cellWidget(row, 0)
        operator_combo = self.ui.tableWidget_static_filter.cellWidget(row, 1)
        if item_combo and operator_combo:
            item = item_combo.currentText()
            operator = operator_combo.currentText()
            value = ""
            if item:
                self.report.add_static_filter_item(item, operator, value)
                print(f"Added initial filter: {item} {operator} '{value}'")

        self.ui.tableWidget_static_filter.itemChanged.connect(
            self._on_filter_changed
        )
        if operator_combo:
            self._on_operator_changed(row, operator_combo.currentText())

    def static_filter_remove(self) -> None:
        """Remove highlighted static filter rows."""
        selected_rows = {item.row() for item in self.ui.tableWidget_static_filter.selectedItems()}
        if not selected_rows:
            current_row = self.ui.tableWidget_static_filter.currentRow()
            if current_row >= 0:
                selected_rows.add(current_row)

        if not selected_rows:
            print("No rows selected for removal")
            return

        for row in sorted(selected_rows, reverse=True):
            item_combo = self.ui.tableWidget_static_filter.cellWidget(row, 0)
            operator_combo = self.ui.tableWidget_static_filter.cellWidget(row, 1)
            value_item = self.ui.tableWidget_static_filter.item(row, 2)
            if item_combo and operator_combo and value_item:
                item = item_combo.currentText()
                operator = operator_combo.currentText()
                value = value_item.text()
                self.report.remove_static_filter_item(item, operator, value)
                print(f"Removed filter: {item} {operator} '{value}'")
            self.ui.tableWidget_static_filter.removeRow(row)

        self.update_items_dependent_ui()

    def _on_filter_changed(self, row: Optional[int] = None) -> None:
        """Respond to edits made within the static filter table."""
        if isinstance(row, QTableWidgetItem):
            row = row.row()
        elif row is None and isinstance(self.sender(), QTableWidgetItem):
            row = self.sender().row()
        elif row is None:
            sender = self.sender()
            if sender:
                for r in range(self.ui.tableWidget_static_filter.rowCount()):
                    for c in range(2):
                        if self.ui.tableWidget_static_filter.cellWidget(r, c) == sender:
                            row = r
                            break
                    if row is not None:
                        break

        if row is None:
            print("Could not determine which row changed")
            return

        item_combo = self.ui.tableWidget_static_filter.cellWidget(row, 0)
        operator_combo = self.ui.tableWidget_static_filter.cellWidget(row, 1)
        value_item = self.ui.tableWidget_static_filter.item(row, 2)
        if not (item_combo and operator_combo and value_item):
            return

        item = item_combo.currentText()
        operator = operator_combo.currentText()
        value = value_item.text()
        if not (item and operator):
            return

        current_filters = self.report.get_static_filter_items()
        if len(current_filters) > self.ui.tableWidget_static_filter.rowCount():
            self.synchronize_static_filters()
            return

        if row < len(current_filters):
            old_item, old_operator, old_value = current_filters[row]
            self.report.remove_static_filter_item(old_item, old_operator, old_value)

        self.report.add_static_filter_item(item, operator, value)
        print(f"Updated filter: {item} {operator} '{value}'")

    # ------------------------------------------------------------------
    # Dynamic filters

    def update_dynamic_filter_table(self) -> None:
        """Populate the dynamic filter table."""
        self.ui.tableWidget_dynamic_filter.setRowCount(0)
        for item1, operator, item2 in self.report.get_dynamic_filter_items():
            row = self.ui.tableWidget_dynamic_filter.rowCount()
            self.ui.tableWidget_dynamic_filter.insertRow(row)
            self._add_dynamic_dropdown(row, 0, "item", item1)
            self._add_dynamic_dropdown(row, 1, "operator", operator)
            self._add_dynamic_dropdown(row, 2, "item", item2)
        self._adjust_column_widths(self.ui.tableWidget_dynamic_filter)

    def _add_dynamic_dropdown(
        self,
        row: int,
        column: int,
        dropdown_type: str,
        selected_value: Optional[str] = None,
    ) -> None:
        """Add item/operator dropdowns to the dynamic filter table."""
        combo = QComboBox()

        if dropdown_type == "item":
            all_items = []
            for item in self.report.get_selected_common_items():
                all_items.append(item)
            for form_name in self.report.get_selected_forms_list():
                form = self.report.selected_forms[form_name]
                for item in form.get_selected_form_items():
                    all_items.append(f"{form_name}.{item}")
            all_items.sort()
            for item in all_items:
                combo.addItem(item)
        else:
            for op in ["=", "!=", ">", ">=", "<", "<="]:
                combo.addItem(op)

        if selected_value:
            combo.setCurrentText(selected_value)

        combo.currentTextChanged.connect(lambda: self._on_dynamic_filter_changed(row))
        self.ui.tableWidget_dynamic_filter.setCellWidget(row, column, combo)

    def dynamic_filter_add(self) -> None:
        """Insert a new dynamic filter row."""
        row = self.ui.tableWidget_dynamic_filter.rowCount()
        self.ui.tableWidget_dynamic_filter.insertRow(row)
        self._add_dynamic_dropdown(row, 0, "item")
        self._add_dynamic_dropdown(row, 1, "operator")
        self._add_dynamic_dropdown(row, 2, "item")

    def dynamic_filter_remove(self) -> None:
        """Remove the selected dynamic filter rows."""
        selected_rows = {
            item.row() for item in self.ui.tableWidget_dynamic_filter.selectedItems()
        }
        if not selected_rows:
            current_row = self.ui.tableWidget_dynamic_filter.currentRow()
            if current_row >= 0:
                selected_rows.add(current_row)

        if not selected_rows:
            print("No rows selected for removal")
            return

        for row in sorted(selected_rows, reverse=True):
            item1_combo = self.ui.tableWidget_dynamic_filter.cellWidget(row, 0)
            operator_combo = self.ui.tableWidget_dynamic_filter.cellWidget(row, 1)
            item2_combo = self.ui.tableWidget_dynamic_filter.cellWidget(row, 2)
            if item1_combo and operator_combo and item2_combo:
                item1 = item1_combo.currentText()
                operator = operator_combo.currentText()
                item2 = item2_combo.currentText()
                self.report.remove_dynamic_filter_item(item1, operator, item2)
            self.ui.tableWidget_dynamic_filter.removeRow(row)

    def _on_dynamic_filter_changed(self, row: int) -> None:
        """Persist edits made to a dynamic filter row."""
        item1_combo = self.ui.tableWidget_dynamic_filter.cellWidget(row, 0)
        operator_combo = self.ui.tableWidget_dynamic_filter.cellWidget(row, 1)
        item2_combo = self.ui.tableWidget_dynamic_filter.cellWidget(row, 2)
        if not (item1_combo and operator_combo and item2_combo):
            return

        item1 = item1_combo.currentText()
        operator = operator_combo.currentText()
        item2 = item2_combo.currentText()
        if not (item1 and item2 and operator):
            return

        self.report.update_dynamic_filter_item(row, item1, operator, item2)

