"""Filters and Comparisons: the rules that keep only some of the report's rows.

:class:`FiltersMixin` drives both pages: it wires the combo boxes, keeps the
:class:`CLReport` filter collections in sync with the tables, and responds to
user edits.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QCompleter, QTableWidgetItem, QWidget

from cci_ui.icons import IconName
from cci_ui.widgets.page import Page
from cci_ui.widgets.tables import ColumnSpec, TableToolbar, table_card
from clinical_reporting import report_columns, steps
from clinical_reporting.models import Operator

from ._common import CellComboBox, make_table

logger = logging.getLogger(__name__)


class FiltersPage(Page):
    """Rows kept only when an item matches a value."""

    KEY = steps.FILTERS
    SECTION = "Rules"
    ICON = IconName.FILTERS
    EXPORTS = (
        "tableWidget_static_filter",
        "pushButton_static_filter_add",
        "pushButton_static_filter_remove",
    )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            steps.TITLES[self.KEY],
            "Keep only rows that match every filter.",
            parent=parent,
        )
        # Row numbers: validation messages name filters by row.
        self.tableWidget_static_filter = make_table(
            ["Item", "Operator", "Value"],
            [ColumnSpec("stretch"), ColumnSpec("fixed", 170), ColumnSpec("stretch")],
            placeholder="No filters. Press + to add one.",
            row_numbers=True,
        )
        toolbar = TableToolbar(
            add_tooltip="Add filter",
            remove_tooltip="Remove selected filter",
            caption="Select a row, then press − to remove it.",
        )
        self.pushButton_static_filter_add = toolbar.add_button
        self.pushButton_static_filter_remove = toolbar.remove_button
        self.body.addWidget(table_card(self.tableWidget_static_filter), 1)
        self.body.addWidget(toolbar)


class ComparisonsPage(Page):
    """Rows kept only when one item compares to another."""

    KEY = steps.COMPARISONS
    SECTION = "Rules"
    ICON = IconName.COMPARISONS
    EXPORTS = (
        "tableWidget_dynamic_filter",
        "pushButton_dynamic_filter_add",
        "pushButton_dynamic_filter_remove",
    )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            steps.TITLES[self.KEY],
            "Keep only rows where one item compares to another, for example an "
            "end date on or after its start date.",
            parent=parent,
        )
        self.tableWidget_dynamic_filter = make_table(
            ["Item 1", "Operator", "Item 2"],
            [ColumnSpec("stretch"), ColumnSpec("fixed", 120), ColumnSpec("stretch")],
            placeholder="No comparisons. Press + to add one.",
            row_numbers=True,
        )
        toolbar = TableToolbar(
            add_tooltip="Add comparison", remove_tooltip="Remove selected comparison"
        )
        self.pushButton_dynamic_filter_add = toolbar.add_button
        self.pushButton_dynamic_filter_remove = toolbar.remove_button
        self.body.addWidget(table_card(self.tableWidget_dynamic_filter), 1)
        self.body.addWidget(toolbar)


class FiltersMixin:
    """Behavior for managing filters and comparisons."""

    def _init_filters(self) -> None:
        """Attach filter-related button handlers."""
        self.ui.pushButton_static_filter_add.clicked.connect(self.static_filter_add)
        self.ui.pushButton_static_filter_remove.clicked.connect(
            self.static_filter_remove
        )
        self.ui.pushButton_dynamic_filter_add.clicked.connect(self.dynamic_filter_add)
        self.ui.pushButton_dynamic_filter_remove.clicked.connect(
            self.dynamic_filter_remove
        )

    # ------------------------------------------------------------------
    # Filters

    def update_static_filter_table(self) -> None:
        """Populate the Filters table using report data."""
        self._safe_disconnect(self.ui.tableWidget_static_filter.itemChanged)

        self.ui.tableWidget_static_filter.setRowCount(0)
        for item, operator, value in self.report.get_static_filter_items():
            row = self.ui.tableWidget_static_filter.rowCount()
            self.ui.tableWidget_static_filter.insertRow(row)
            self._add_dropdown(row, 0, "item", item)
            self._add_dropdown(row, 1, "operator", operator)
            value_item = QTableWidgetItem(value)
            self.ui.tableWidget_static_filter.setItem(row, 2, value_item)

        self.ui.tableWidget_static_filter.itemChanged.connect(self._on_filter_changed)

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
        logger.debug(
            "Synchronized static filters: %s", self.report.get_static_filter_items()
        )
        self._report_changed()

    def _selected_filter_items(self) -> list[str]:
        """Return the sorted list of selectable filter items.

        The report's output columns: the selected common items, and each form's
        columns as ``form.item`` qualified names (its selected items and the
        common items it doesn't join on). Shared by the static and dynamic
        filter item pickers.
        """
        return sorted(report_columns.output_identifiers(self.report))

    def _populate_searchable_item_combo(
        self, combo: QComboBox, selected_value: Optional[str]
    ) -> None:
        """Turn ``combo`` into an editable, substring-searchable item picker.

        Lists every output column; typing filters the dropdown popup
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
        """Add an item or operator dropdown to the Filters table."""
        combo = CellComboBox()

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
        """Add a fresh, empty filter row.

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

        self.ui.tableWidget_static_filter.itemChanged.connect(self._on_filter_changed)
        operator_combo = self.ui.tableWidget_static_filter.cellWidget(row, 1)
        if operator_combo:
            self._on_operator_changed(row, operator_combo.currentText())

    @staticmethod
    def _selected_filter_rows(table) -> list[int]:
        """Return rows to remove: highlighted rows, else the current row.

        Rows come back bottom-up so removing them one by one does not shift
        the indexes of the rows still pending removal.
        """
        selected_rows = {item.row() for item in table.selectedItems()}
        if not selected_rows:
            current_row = table.currentRow()
            if current_row >= 0:
                selected_rows.add(current_row)
        return sorted(selected_rows, reverse=True)

    def static_filter_remove(self) -> None:
        """Remove highlighted filter rows."""
        rows = self._selected_filter_rows(self.ui.tableWidget_static_filter)
        if not rows:
            logger.debug("No rows selected for removal")
            return

        for row in rows:
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

        # Rebuild the table so the surviving rows' operator handlers are
        # reconnected with their new row indexes.
        self.update_static_filter_table()
        self._report_changed()

    def _on_filter_changed(self, *args) -> None:
        """Rebuild the report's filters from the current table state.

        Rebuilding the whole list (rather than patching a single row) keeps the
        report correct while the user types a partial item name, and naturally
        drops rows whose item field is still empty. Accepts and ignores whatever
        argument the triggering signal passes (a row int, text, or table item).
        """
        self.synchronize_static_filters()

    # ------------------------------------------------------------------
    # Comparisons

    def update_dynamic_filter_table(self) -> None:
        """Populate the Comparisons table."""
        self.ui.tableWidget_dynamic_filter.setRowCount(0)
        for item1, operator, item2 in self.report.get_dynamic_filter_items():
            row = self.ui.tableWidget_dynamic_filter.rowCount()
            self.ui.tableWidget_dynamic_filter.insertRow(row)
            self._add_dynamic_dropdown(row, 0, "item", item1)
            self._add_dynamic_dropdown(row, 1, "operator", operator)
            self._add_dynamic_dropdown(row, 2, "item", item2)

    def _add_dynamic_dropdown(
        self,
        row: int,
        column: int,
        dropdown_type: str,
        selected_value: Optional[str] = None,
    ) -> None:
        """Add item/operator dropdowns to the Comparisons table."""
        combo = CellComboBox()

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
        """Insert a new comparison row."""
        row = self.ui.tableWidget_dynamic_filter.rowCount()
        self.ui.tableWidget_dynamic_filter.insertRow(row)
        self._add_dynamic_dropdown(row, 0, "item")
        self._add_dynamic_dropdown(row, 1, "operator")
        self._add_dynamic_dropdown(row, 2, "item")

    def dynamic_filter_remove(self) -> None:
        """Remove the selected comparison rows.

        No rebuild is needed afterwards: the comparison change handlers ignore
        their captured row index and resynchronize the whole comparison list.
        """
        rows = self._selected_filter_rows(self.ui.tableWidget_dynamic_filter)
        if not rows:
            logger.debug("No rows selected for removal")
            return

        for row in rows:
            item1_combo = self.ui.tableWidget_dynamic_filter.cellWidget(row, 0)
            operator_combo = self.ui.tableWidget_dynamic_filter.cellWidget(row, 1)
            item2_combo = self.ui.tableWidget_dynamic_filter.cellWidget(row, 2)
            if item1_combo and operator_combo and item2_combo:
                item1 = item1_combo.currentText()
                operator = operator_combo.currentText()
                item2 = item2_combo.currentText()
                self.report.remove_dynamic_filter_item(item1, operator, item2)
            self.ui.tableWidget_dynamic_filter.removeRow(row)
        self._report_changed()

    def synchronize_dynamic_filters(self) -> None:
        """Rebuild the report's comparisons from the table, skipping empty rows.

        A row only contributes a comparison once both item fields and the operator
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
        logger.debug(
            "Synchronized dynamic filters: %s", self.report.get_dynamic_filter_items()
        )
        self._report_changed()

    def _on_dynamic_filter_changed(self, *args) -> None:
        """Rebuild the report's comparisons from the current table state."""
        self.synchronize_dynamic_filters()
