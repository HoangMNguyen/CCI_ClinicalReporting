"""Filter management mixin for the Clinical Reporting widget.

This module contains all code related to static and dynamic filters.
It provides helper routines for wiring combo boxes, synchronising the
:class:`CLReport` filter collections with the UI tables, and responding to
user edits.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QCompleter, QTableWidgetItem

from clinical_reporting.core.constants import Operator, qualify

logger = logging.getLogger(__name__)


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
        self._safe_disconnect(self.ui.tableWidget_static_filter.itemChanged)

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
        logger.debug("Synchronized static filters: %s", self.report.get_static_filter_items())

    def _selected_filter_items(self) -> list[str]:
        """Return the sorted list of selectable filter items.

        Combines the selected common items with each selected form item rendered
        as a ``form.item`` qualified name. Shared by the static and dynamic
        filter item pickers.
        """
        items = list(self.report.get_selected_common_items())
        for form_name in self.report.get_selected_forms_list():
            form = self.report.selected_forms[form_name]
            for item in form.get_selected_form_items():
                items.append(qualify(form_name, item))
        items.sort()
        return items

    def _populate_searchable_item_combo(self, combo: QComboBox, selected_value: Optional[str]) -> None:
        """Turn ``combo`` into an editable, substring-searchable item picker.

        Lists every currently selected item; typing filters the dropdown popup
        to the entries that contain the typed text (case-insensitive). When no
        ``selected_value`` is supplied the combo starts empty, so a freshly
        added filter row applies nothing until the user picks an item.
        """
        combo.setEditable(True)
        # Typed text must not be inserted into the list as a new permanent item.
        combo.setInsertPolicy(QComboBox.NoInsert)

        for item in self._selected_filter_items():
            combo.addItem(item)

        completer = combo.completer()
        if completer is not None:
            completer.setCompletionMode(QCompleter.PopupCompletion)
            completer.setFilterMode(Qt.MatchContains)
            completer.setCaseSensitivity(Qt.CaseInsensitive)

        if selected_value:
            combo.setCurrentText(selected_value)
        else:
            # Start blank: an unfilled item field means "no filter on this row".
            combo.setCurrentIndex(-1)

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
            self._populate_searchable_item_combo(combo, selected_value)
        elif dropdown_type == "operator":
            for op in Operator.STATIC:
                combo.addItem(op)
            combo.currentTextChanged.connect(
                lambda text, r=row: self._on_operator_changed(r, text)
            )
            if selected_value:
                combo.setCurrentText(selected_value)

        combo.currentTextChanged.connect(lambda: self._on_filter_changed(row))
        self.ui.tableWidget_static_filter.setCellWidget(row, column, combo)

        if dropdown_type == "operator" and selected_value in Operator.NULLARY:
            self._on_operator_changed(row, selected_value)

    def _on_operator_changed(self, row: int, operator_text: str) -> None:
        """Enable/disable the value column based on the chosen operator."""
        value_item = self.ui.tableWidget_static_filter.item(row, 2)
        if operator_text in Operator.NULLARY:
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
        """Add a fresh, empty static filter row.

        The item field starts blank (and is searchable), so the row applies no
        filter until the user picks an item.
        """
        row = self.ui.tableWidget_static_filter.rowCount()
        self.ui.tableWidget_static_filter.insertRow(row)

        self._safe_disconnect(self.ui.tableWidget_static_filter.itemChanged)

        self._add_dropdown(row, 0, "item")
        self._add_dropdown(row, 1, "operator", "=")
        value_item = QTableWidgetItem("")
        self.ui.tableWidget_static_filter.setItem(row, 2, value_item)

        self.ui.tableWidget_static_filter.itemChanged.connect(
            self._on_filter_changed
        )
        operator_combo = self.ui.tableWidget_static_filter.cellWidget(row, 1)
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
            logger.debug("No rows selected for removal")
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
                logger.debug("Removed filter: %s %s '%s'", item, operator, value)
            self.ui.tableWidget_static_filter.removeRow(row)

        self.update_items_dependent_ui()

    def _on_filter_changed(self, *args) -> None:
        """Rebuild the report's static filters from the current table state.

        Rebuilding the whole list (rather than patching a single row) keeps the
        report correct while the user types a partial item name, and naturally
        drops rows whose item field is still empty. Accepts and ignores whatever
        argument the triggering signal passes (a row int, text, or table item).
        """
        self.synchronize_static_filters()

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
            self._populate_searchable_item_combo(combo, selected_value)
        else:
            for op in Operator.DYNAMIC:
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
            logger.debug("No rows selected for removal")
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

    def synchronize_dynamic_filters(self) -> None:
        """Rebuild the report's dynamic filters from the table, skipping empty rows.

        A row only contributes a filter once both item fields and the operator
        are filled in, so partially-filled or empty rows apply nothing.
        """
        new_filters = []
        for row in range(self.ui.tableWidget_dynamic_filter.rowCount()):
            item1_combo = self.ui.tableWidget_dynamic_filter.cellWidget(row, 0)
            operator_combo = self.ui.tableWidget_dynamic_filter.cellWidget(row, 1)
            item2_combo = self.ui.tableWidget_dynamic_filter.cellWidget(row, 2)
            if item1_combo and operator_combo and item2_combo:
                item1 = item1_combo.currentText()
                operator = operator_combo.currentText()
                item2 = item2_combo.currentText()
                if item1 and operator and item2:
                    new_filters.append((item1, operator, item2))

        self.report.set_dynamic_filter_items(new_filters)
        logger.debug("Synchronized dynamic filters: %s", self.report.get_dynamic_filter_items())

    def _on_dynamic_filter_changed(self, *args) -> None:
        """Rebuild the report's dynamic filters from the current table state."""
        self.synchronize_dynamic_filters()

