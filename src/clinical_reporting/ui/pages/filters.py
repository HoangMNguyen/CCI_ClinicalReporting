"""Filters and Comparisons: the rules that keep only some of the report's rows.

:class:`FiltersMixin` drives both pages: it wires the combo boxes, keeps the
:class:`CLReport` filter collections in sync with the tables (every row, in
table order, even one still being filled in), and responds to user edits.
Each field a row lacks or can't use is marked, with the reason as its
tooltip.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem, QWidget

from cci_ui.icons import IconName
from cci_ui.widgets.page import Page
from cci_ui.widgets.tables import ColumnSpec, TableToolbar, mark_cell, table_card
from clinical_reporting import report_columns, steps
from clinical_reporting.models import Operator

from ._common import CellComboBox, ItemBox, make_table, show_problem

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
            [
                ColumnSpec("stretch", editable=True),
                ColumnSpec("fixed", 170, editable=True),
                ColumnSpec("stretch", editable=True),
            ],
            placeholder="No filters. Press + to add one.",
            row_numbers=True,
            controls=True,
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
            [
                ColumnSpec("stretch", editable=True),
                ColumnSpec("fixed", 120, editable=True),
                ColumnSpec("stretch", editable=True),
            ],
            placeholder="No comparisons. Press + to add one.",
            row_numbers=True,
            controls=True,
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

    def _selected_filter_items(self) -> list[str]:
        """Return the sorted list of selectable filter items.

        The report's output columns: the selected common items, and each form's
        columns as ``form.item`` qualified names (its selected items and the
        common items it doesn't join on). Shared by the static and dynamic
        filter item pickers.
        """
        return sorted(report_columns.output_identifiers(self.report))

    def _filter_item_box(self, item: str, on_change) -> ItemBox:
        """A row's searchable item picker, showing *item* (blank: none yet).

        It lists every output column, and *item* too when it is another name
        the report accepts (a form item without its form, from a setting).
        """
        choices = self._selected_filter_items()
        if item and item not in choices:
            choices = sorted([*choices, item])
        box = ItemBox(choices, item)
        box.currentIndexChanged.connect(on_change)
        return box

    @staticmethod
    def _picked_item(box) -> str:
        """The item picked in *box*; typed text that isn't an item is no item."""
        if box is None:
            return ""
        index = box.currentIndex()
        return box.itemText(index) if index >= 0 else ""

    @staticmethod
    def _selected_filter_rows(table) -> list[int]:
        """Return rows to remove: highlighted rows, else the current row.

        Rows come back bottom-up so removing them one by one does not shift
        the indexes of the rows still pending removal.
        """
        selected_rows = {index.row() for index in table.selectedIndexes()}
        if not selected_rows:
            current_row = table.currentRow()
            if current_row >= 0:
                selected_rows.add(current_row)
        return sorted(selected_rows, reverse=True)

    # ------------------------------------------------------------------
    # Filters

    def update_static_filter_table(self) -> None:
        """Populate the Filters table using report data."""
        table = self.ui.tableWidget_static_filter
        self._safe_disconnect(table.itemChanged)

        table.setRowCount(0)
        for item, operator, value in self.report.get_static_filter_items():
            self._insert_static_row(item, operator, value)

        table.itemChanged.connect(self._on_filter_changed)
        self._report_changed()  # Draws the marks.

    def _insert_static_row(self, item: str, operator: str, value: str) -> None:
        table = self.ui.tableWidget_static_filter
        row = table.rowCount()
        table.insertRow(row)
        table.setCellWidget(row, 0, self._filter_item_box(item, self._on_filter_changed))
        combo = CellComboBox()
        combo.addItems(list(Operator.STATIC))
        combo.setCurrentText(operator)
        combo.currentTextChanged.connect(
            lambda text, r=row: self._on_operator_changed(r, text)
        )
        combo.currentTextChanged.connect(self._on_filter_changed)
        table.setCellWidget(row, 1, combo)
        table.setItem(row, 2, QTableWidgetItem(str(value)))
        self._on_operator_changed(row, operator)

    def synchronize_static_filters(self) -> None:
        """Store every row of the Filters table in the report, in table order.

        A row still being filled in is stored too: validation marks what it
        lacks, and the report's filter *n* is the table's row *n*.
        """
        table = self.ui.tableWidget_static_filter
        rows = []
        for row in range(table.rowCount()):
            operator_combo = table.cellWidget(row, 1)
            value_item = table.item(row, 2)
            rows.append(
                (
                    self._picked_item(table.cellWidget(row, 0)),
                    operator_combo.currentText() if operator_combo else "",
                    value_item.text() if value_item else "",
                )
            )
        self.report.set_static_filter_items(rows)
        logger.debug(
            "Synchronized static filters: %s", self.report.get_static_filter_items()
        )
        self._report_changed()

    def _on_operator_changed(self, row: int, operator_text: str) -> None:
        """Enable/disable the value column based on the chosen operator."""
        table = self.ui.tableWidget_static_filter
        value_item = table.item(row, 2)
        if value_item is None:
            value_item = QTableWidgetItem("")
            table.setItem(row, 2, value_item)
        if operator_text in Operator.NULLARY:
            value_item.setText("")
            value_item.setFlags(value_item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        else:
            value_item.setFlags(
                value_item.flags() | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable
            )

    def static_filter_add(self) -> None:
        """Add a fresh, empty filter row; it is a problem until it is filled in."""
        table = self.ui.tableWidget_static_filter
        self._safe_disconnect(table.itemChanged)
        self._insert_static_row("", "=", "")
        table.itemChanged.connect(self._on_filter_changed)
        self.synchronize_static_filters()

    def static_filter_remove(self) -> None:
        """Remove highlighted filter rows."""
        table = self.ui.tableWidget_static_filter
        rows = self._selected_filter_rows(table)
        if not rows:
            logger.debug("No rows selected for removal")
            return
        for row in rows:
            table.removeRow(row)
        self.synchronize_static_filters()
        # Rebuild the table so the surviving rows' operator handlers are
        # reconnected with their new row indexes.
        self.update_static_filter_table()

    def _on_filter_changed(self, *args) -> None:
        """Rebuild the report's filters from the current table state.

        Accepts and ignores whatever argument the triggering signal passes (a
        row int, text, or table item).
        """
        self.synchronize_static_filters()

    # ------------------------------------------------------------------
    # Comparisons

    def update_dynamic_filter_table(self) -> None:
        """Populate the Comparisons table."""
        self.ui.tableWidget_dynamic_filter.setRowCount(0)
        for item1, operator, item2 in self.report.get_dynamic_filter_items():
            self._insert_dynamic_row(item1, operator, item2)
        self._report_changed()  # Draws the marks.

    def _insert_dynamic_row(self, item1: str, operator: str, item2: str) -> None:
        table = self.ui.tableWidget_dynamic_filter
        row = table.rowCount()
        table.insertRow(row)
        changed = self._on_dynamic_filter_changed
        table.setCellWidget(row, 0, self._filter_item_box(item1, changed))
        combo = CellComboBox()
        combo.addItems(list(Operator.DYNAMIC))
        if operator:
            combo.setCurrentText(operator)
        combo.currentTextChanged.connect(changed)
        table.setCellWidget(row, 1, combo)
        table.setCellWidget(row, 2, self._filter_item_box(item2, changed))

    def dynamic_filter_add(self) -> None:
        """Add a fresh comparison row; it is a problem until it is filled in."""
        self._insert_dynamic_row("", "", "")
        self.synchronize_dynamic_filters()

    def dynamic_filter_remove(self) -> None:
        """Remove the selected comparison rows."""
        table = self.ui.tableWidget_dynamic_filter
        rows = self._selected_filter_rows(table)
        if not rows:
            logger.debug("No rows selected for removal")
            return
        for row in rows:
            table.removeRow(row)
        self.synchronize_dynamic_filters()
        self.update_dynamic_filter_table()

    def synchronize_dynamic_filters(self) -> None:
        """Store every row of the Comparisons table in the report, in table order.

        A row still being filled in is stored too (see
        :meth:`synchronize_static_filters`).
        """
        table = self.ui.tableWidget_dynamic_filter
        rows = []
        for row in range(table.rowCount()):
            operator_combo = table.cellWidget(row, 1)
            rows.append(
                (
                    self._picked_item(table.cellWidget(row, 0)),
                    operator_combo.currentText() if operator_combo else "",
                    self._picked_item(table.cellWidget(row, 2)),
                )
            )
        self.report.set_dynamic_filter_items(rows)
        logger.debug(
            "Synchronized dynamic filters: %s", self.report.get_dynamic_filter_items()
        )
        self._report_changed()

    def _on_dynamic_filter_changed(self, *args) -> None:
        """Rebuild the report's comparisons from the current table state."""
        self.synchronize_dynamic_filters()

    # ------------------------------------------------------------------
    # Marks

    def _mark_filter_problems(self) -> None:
        """Mark each filter's and comparison's fields with what they lack.

        From the window's last validation (``_issue_fields``, see
        :mod:`ui.navigation`): the report's filter *n* is the table's row *n*.
        """
        fields = getattr(self, "_issue_fields", {})

        def problem(field: str) -> str:
            return "\n".join(issue.message for issue in fields.get(field, ()))

        table = self.ui.tableWidget_static_filter
        for row in range(table.rowCount()):
            field = f"static_filter_items.{row}"
            item_box, operator_combo = table.cellWidget(row, 0), table.cellWidget(row, 1)
            value_item = table.item(row, 2)
            if item_box is not None:
                item_box.set_problem(problem(f"{field}.0"))
            if operator_combo is not None:
                show_problem(operator_combo, problem(f"{field}.1"))
            if value_item is not None:
                mark_cell(value_item, problem(f"{field}.2"))

        table = self.ui.tableWidget_dynamic_filter
        for row in range(table.rowCount()):
            field = f"dynamic_filter_items.{row}"
            for column in (0, 2):
                item_box = table.cellWidget(row, column)
                if item_box is not None:
                    item_box.set_problem(problem(f"{field}.{column}"))
            operator_combo = table.cellWidget(row, 1)
            if operator_combo is not None:
                show_problem(operator_combo, problem(f"{field}.1"))
