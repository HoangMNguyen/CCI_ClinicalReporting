"""Comparison, rename, and ordering mixin for the Clinical Reporting widget.

This module groups the behaviours that live on the "Comparison and
Order" tab: rename mapping management, join configuration, and item
ordering.  The routines interact heavily with Qt table widgets, so they
are consolidated here to keep the main widget concise.
"""

from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QTableWidgetItem


class ComparisonTabMixin:
    """Behavior for rename, join, and ordering controls."""

    def _init_comparison_and_order_tab(self) -> None:
        """Wire signals for rename and ordering widgets."""
        self.ui.tableWidget_rename.cellChanged.connect(self.on_rename_cell_changed)
        self.ui.pushButton_order_up.clicked.connect(self.click_order_up)
        self.ui.pushButton_order_down.clicked.connect(self.click_order_down)

    # ------------------------------------------------------------------
    # Rename table

    def update_rename_table(self) -> None:
        """Populate the rename table with selected items."""
        try:
            self.ui.tableWidget_rename.cellChanged.disconnect(
                self.on_rename_cell_changed
            )
        except Exception:
            pass

        self.ui.tableWidget_rename.setRowCount(0)
        rename_dict = self.report.get_rename_dict()
        row = 0

        for item in self.report.get_selected_common_items():
            self.ui.tableWidget_rename.insertRow(row)
            orig_item = QTableWidgetItem(item)
            orig_item.setFlags(orig_item.flags() & ~Qt.ItemIsEditable)
            self.ui.tableWidget_rename.setItem(row, 0, orig_item)
            new_name = rename_dict.get(item, "")
            new_item = QTableWidgetItem(new_name)
            self.ui.tableWidget_rename.setItem(row, 1, new_item)
            row += 1

        for form_name in self.report.get_selected_forms_list():
            form = self.report.selected_forms[form_name]
            for item in form.get_selected_form_items():
                combined_name = f"{form_name}.{item}"
                self.ui.tableWidget_rename.insertRow(row)
                orig_item = QTableWidgetItem(combined_name)
                orig_item.setFlags(orig_item.flags() & ~Qt.ItemIsEditable)
                self.ui.tableWidget_rename.setItem(row, 0, orig_item)
                new_name = rename_dict.get(combined_name, "")
                new_item = QTableWidgetItem(new_name)
                self.ui.tableWidget_rename.setItem(row, 1, new_item)
                row += 1

        self.ui.tableWidget_rename.cellChanged.connect(self.on_rename_cell_changed)
        self._adjust_column_widths(self.ui.tableWidget_rename)

    def on_rename_cell_changed(self, row: int, column: int) -> None:
        """Persist edits to the rename table back to the report."""
        if column != 1:
            return
        item = self.ui.tableWidget_rename.item(row, 0)
        new_name_item = self.ui.tableWidget_rename.item(row, 1)
        if not (item and new_name_item):
            return
        original_name = item.text()
        new_name = new_name_item.text()
        if new_name:
            self.report.set_rename_item(original_name, new_name)
        else:
            self.report.remove_rename_item(original_name)

    # ------------------------------------------------------------------
    # Join configuration

    def update_join_table_ui(self) -> None:
        """Refresh join controls when selections change."""
        self.update_selected_forms_table()

    def update_selected_forms_table(self) -> None:
        """Populate the join configuration table."""
        try:
            self.ui.tableWidget_join.cellChanged.disconnect()
        except Exception:
            pass

        self.ui.tableWidget_join.setRowCount(0)
        join_data = self.report.get_join_list_dict()

        for row, form_name in enumerate(self.report.get_selected_forms_list()):
            self.ui.tableWidget_join.insertRow(row)
            form_item = QTableWidgetItem(form_name)
            form_item.setFlags(form_item.flags() & ~Qt.ItemIsEditable)
            self.ui.tableWidget_join.setItem(row, 0, form_item)

            for col in range(1, 4):
                self._add_item_dropdown(row, col, form_name, join_data)

            join_order_combo = QComboBox()
            join_order_combo.addItems([str(i) for i in range(1, 6)])
            default_order = "1"
            if form_name in join_data and join_data[form_name]["order"]:
                default_order = str(join_data[form_name]["order"])
            join_order_combo.setCurrentText(default_order)
            join_order_combo.currentTextChanged.connect(self.update_join_list)
            join_order_combo.currentTextChanged.connect(
                lambda value, r=row: self.on_join_order_changed(r, value)
            )
            self.ui.tableWidget_join.setCellWidget(row, 4, join_order_combo)

            join_type_combo = QComboBox()
            join_types = ["Left join", "Right join", "Inner join", "Outer join"]
            for join_type in join_types:
                join_type_combo.addItem(join_type)
            default_join_type = "Left join"
            if form_name in join_data and join_data[form_name]["how"]:
                default_join_type = join_data[form_name]["how"]
            join_type_combo.setCurrentText(default_join_type)
            join_type_combo.currentTextChanged.connect(self.update_join_list)
            self.ui.tableWidget_join.setCellWidget(row, 5, join_type_combo)

            if default_order == "1":
                self.on_join_order_changed(row, "1")

        self._adjust_column_widths(self.ui.tableWidget_join)

    def on_join_order_changed(self, row: int, value: str) -> None:
        """Enable or disable join columns depending on the order selection."""
        item_cols = [1, 2, 3]
        join_type_col = 5
        enabled = value != "1"

        if value == "1":
            for col in item_cols:
                combo = self.ui.tableWidget_join.cellWidget(row, col)
                if combo:
                    combo.setCurrentIndex(0)
            join_type_combo = self.ui.tableWidget_join.cellWidget(row, join_type_col)
            if join_type_combo:
                join_type_combo.setCurrentIndex(0)
            self.update_join_list()

        for col in item_cols:
            combo = self.ui.tableWidget_join.cellWidget(row, col)
            if combo:
                combo.setEnabled(enabled)

        join_type_combo = self.ui.tableWidget_join.cellWidget(row, join_type_col)
        if join_type_combo:
            join_type_combo.setEnabled(enabled)

    def _add_item_dropdown(
        self,
        row: int,
        col: int,
        form_name: str,
        join_data: dict,
    ) -> None:
        """Add a dropdown for join-item selection."""
        combo = QComboBox()
        combo.addItem("")

        all_items: List[str] = []
        for item in self.report.get_selected_common_items():
            all_items.append(item)
        all_items.sort()
        for item in all_items:
            combo.addItem(item)

        if form_name in join_data and join_data[form_name]["items"]:
            items = join_data[form_name]["items"]
            item_idx = col - 1
            if item_idx < len(items):
                combo.setCurrentText(items[item_idx])

        combo.currentTextChanged.connect(self.update_join_list)
        self.ui.tableWidget_join.setCellWidget(row, col, combo)

        join_order = 0
        if form_name in join_data and join_data[form_name]["order"]:
            join_order = join_data[form_name]["order"]
        if str(join_order) == "1":
            combo.setEnabled(False)

    def update_join_list(self) -> None:
        """Persist join configuration changes back to the report."""
        join_list = []
        row_count = self.ui.tableWidget_join.rowCount()
        for row in range(row_count):
            form_name_item = self.ui.tableWidget_join.item(row, 0)
            if not form_name_item:
                continue
            form_name = form_name_item.text()

            join_items = []
            for col in range(1, 4):
                combo = self.ui.tableWidget_join.cellWidget(row, col)
                if combo:
                    join_items.append(combo.currentText())

            join_order_combo = self.ui.tableWidget_join.cellWidget(row, 4)
            join_order = 1
            if join_order_combo:
                try:
                    join_order = int(join_order_combo.currentText())
                except ValueError:
                    join_order = 1

            join_type_combo = self.ui.tableWidget_join.cellWidget(row, 5)
            join_type = "Left join"
            if join_type_combo:
                join_type = join_type_combo.currentText()

            join_list.append([form_name, join_items, join_order, join_type])

        self.report.update_join_list(join_list)

    # ------------------------------------------------------------------
    # Item ordering list

    def update_items_order_list(self) -> None:
        """Synchronise the ordering list widget with the report."""
        self.report.update_selected_items_order_list()
        self.ui.listWidget_items_order.clear()
        for item in self.report.get_selected_items_order_list():
            self.ui.listWidget_items_order.addItem(item)

    def click_order_up(self) -> None:
        """Move the highlighted item one position higher."""
        current_row = self.ui.listWidget_items_order.currentRow()
        if current_row <= 0:
            return
        item = self.ui.listWidget_items_order.takeItem(current_row)
        if item is None:
            return
        self.ui.listWidget_items_order.insertItem(current_row - 1, item)
        self.ui.listWidget_items_order.setCurrentRow(current_row - 1)
        self.update_report_order_list_from_widget()

    def click_order_down(self) -> None:
        """Move the highlighted item one position lower."""
        current_row = self.ui.listWidget_items_order.currentRow()
        if current_row < 0 or current_row >= self.ui.listWidget_items_order.count() - 1:
            return
        item = self.ui.listWidget_items_order.takeItem(current_row)
        if item is None:
            return
        self.ui.listWidget_items_order.insertItem(current_row + 1, item)
        self.ui.listWidget_items_order.setCurrentRow(current_row + 1)
        self.update_report_order_list_from_widget()

    def update_report_order_list_from_widget(self) -> None:
        """Persist the current list widget ordering back to the report."""
        new_order = []
        for index in range(self.ui.listWidget_items_order.count()):
            item = self.ui.listWidget_items_order.item(index)
            if item:
                new_order.append(item.text())
        self.report.set_selected_items_order_list(new_order)

