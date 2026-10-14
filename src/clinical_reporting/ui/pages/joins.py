"""Joins: how the selected forms are combined into the report's rows.

:class:`JoinsMixin` owns the join table: one row per selected form, in join
order (the first form starts the report), with its join item dropdowns and
join type. Move up and Move down change a selected form's place
(:meth:`clinical_reporting.report.CLReport.move_join`). The order/rename table
on the Order & rename page lives in :mod:`ui.pages.order_rename`; join changes
trigger its refresh because the default column order follows the join order.
When a join change adds or removes a form's own copy of a common item
(``AE.Visit``, see :mod:`clinical_reporting.report_columns`), the filter
tables are rebuilt too, since their item lists change.

A form that needs a join item gets its name in the danger color. The banner
above the table says why there are no joins to set
(:func:`clinical_reporting.steps.joins_message`).
"""

from __future__ import annotations

from functools import partial
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import QHBoxLayout, QTableWidgetItem, QWidget

from cci_ui.icons import IconName
from cci_ui.theme.manager import current, theme_events
from cci_ui.theme.palette import qcolor
from cci_ui.widgets.buttons import make_button
from cci_ui.widgets.page import Page
from cci_ui.widgets.status import StatusBanner
from cci_ui.widgets.tables import ColumnSpec, table_card
from clinical_reporting import report_columns, steps
from clinical_reporting.models import JoinHow

from ._common import CellComboBox, make_table

_NUMBER_COLUMN, _FORM_COLUMN = 0, 1
_ITEM_COLUMNS = (2, 3, 4)
_TYPE_COLUMN = 5
_READ_ONLY = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable


class JoinsPage(Page):
    """How the selected forms are combined."""

    KEY = steps.JOINS
    SECTION = "Rules"
    ICON = IconName.JOINS
    EXPORTS = (
        "banner_joins",
        "tableWidget_join",
        "pushButton_join_up",
        "pushButton_join_down",
    )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            steps.TITLES[self.KEY],
            "Set how the selected forms are combined. The first form starts the "
            "report; each form below joins it on Item 1–3. Select a form, then "
            "Move up or Move down to change the order.",
            parent=parent,
        )
        self.tableWidget_join = make_table(
            ["#", "Form", "Item 1", "Item 2", "Item 3", "Type"],
            [
                ColumnSpec("fixed", 44),
                ColumnSpec("interactive", 190),
                ColumnSpec("stretch", editable=True),
                ColumnSpec("stretch", editable=True),
                ColumnSpec("stretch", editable=True),
                ColumnSpec("fixed", 140, editable=True),
            ],
            placeholder="Select forms to set how they are joined.",
            controls=True,
        )
        self.pushButton_join_up = make_button("Move up")
        self.pushButton_join_down = make_button("Move down")
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(self.pushButton_join_up)
        buttons.addWidget(self.pushButton_join_down)
        buttons.addStretch(1)
        # Why there are no joins to set: a state of the page, so it isn't
        # repeated in the status bar.
        self.banner_joins = StatusBanner(dismissible=False, announce=False)
        self.body.addWidget(self.banner_joins)
        self.body.addWidget(table_card(self.tableWidget_join), 1)
        self.body.addLayout(buttons)


class JoinsMixin:
    """Behavior for the join configuration controls."""

    def _init_joins(self) -> None:
        """Wire the move buttons; recolor forms missing a join item with the theme."""
        self.ui.pushButton_join_up.clicked.connect(self.click_move_join_up)
        self.ui.pushButton_join_down.clicked.connect(self.click_move_join_down)
        self.ui.tableWidget_join.itemSelectionChanged.connect(
            self._update_join_move_buttons
        )
        self._update_join_move_buttons()
        # A bound method of the window, so Qt drops the connection with it.
        theme_events().changed.connect(self._paint_missing_join_items)

    def update_join_table_ui(self, select: Optional[int] = None) -> None:
        """Tidy the report's joins (``CLReport.normalize_joins``), then show them.

        The rows follow the join order; row *select* is selected afterwards.
        """
        # No handler is connected to ``tableWidget_join.cellChanged`` (join edits
        # are captured via the per-cell combo boxes), so there is nothing to
        # disconnect here before repopulating the table.
        table = self.ui.tableWidget_join
        table.setRowCount(0)
        self.report.normalize_joins()
        join_data = self.report.get_join_list_dict()
        forms = sorted(join_data, key=lambda form: join_data[form]["order"])

        for row, form_name in enumerate(forms):
            table.insertRow(row)
            number = QTableWidgetItem(str(row + 1))
            number.setFlags(_READ_ONLY)
            table.setItem(row, _NUMBER_COLUMN, number)
            form_item = QTableWidgetItem(form_name)
            form_item.setFlags(_READ_ONLY)
            table.setItem(row, _FORM_COLUMN, form_item)

            combos = [
                self._add_item_dropdown(row, column, join_data[form_name]["items"])
                for column in _ITEM_COLUMNS
            ]
            join_type_combo = CellComboBox()
            join_type_combo.setAccessibleName(f"Join type of {form_name}")
            for join_type in JoinHow.ALL:
                join_type_combo.addItem(join_type)
            join_type_combo.setCurrentText(join_data[form_name]["how"])
            join_type_combo.currentTextChanged.connect(self.update_join_list)
            self._put_join_widget(row, _TYPE_COLUMN, join_type_combo)
            combos.append(join_type_combo)

            for combo in combos:
                # The first form starts the report: it joins on nothing.
                combo.setEnabled(row > 0)
                combo.focused.connect(partial(table.selectRow, row))

        self._highlight_missing_join_items()
        self._refresh_joins_banner()
        if select is not None and 0 <= select < table.rowCount():
            table.selectRow(select)
        self._update_join_move_buttons()

    def _put_join_widget(self, row: int, column: int, widget: QWidget) -> None:
        """Put *widget* in a cell, over an empty item so the row can be selected."""
        under = QTableWidgetItem("")
        under.setFlags(_READ_ONLY)
        self.ui.tableWidget_join.setItem(row, column, under)
        self.ui.tableWidget_join.setCellWidget(row, column, widget)

    def _refresh_joins_banner(self) -> None:
        """Say above the join table what stops the joins, or why there are none."""
        message = steps.joins_message(self.report)
        self._set_label_text(getattr(self.ui, "banner_joins", None), message or "")

    def _selected_join_row(self) -> Optional[int]:
        rows = self.ui.tableWidget_join.selectionModel().selectedRows()
        return rows[0].row() if rows else None

    def _update_join_move_buttons(self) -> None:
        """Move up/down only for a selected form that has a place to go."""
        row = self._selected_join_row()
        count = self.ui.tableWidget_join.rowCount()
        self.ui.pushButton_join_up.setEnabled(row is not None and row > 0)
        self.ui.pushButton_join_down.setEnabled(row is not None and row < count - 1)

    def click_move_join_up(self) -> None:
        """Move the selected form one place up in the join order."""
        self._move_join(-1)

    def click_move_join_down(self) -> None:
        """Move the selected form one place down in the join order."""
        self._move_join(1)

    def _move_join(self, step: int) -> None:
        row = self._selected_join_row()
        if row is None:
            return
        form = self.ui.tableWidget_join.item(row, _FORM_COLUMN).text()
        columns_before = set(report_columns.output_identifiers(self.report))
        self.report.move_join(form, step)
        self.update_join_table_ui(select=row + step)
        self._after_join_change(columns_before)

    def _highlight_missing_join_items(self) -> None:
        """Flag non-first forms without a join item and update Export to Excel."""
        self._paint_missing_join_items()

        # Join-item dropdown changes can resolve or introduce this error, so
        # refresh Export to Excel from here too.
        refresh_run = getattr(self, "_refresh_run_availability", None)
        if callable(refresh_run):
            refresh_run()

    def _paint_missing_join_items(self) -> None:
        """Show non-first forms without a join item in the danger color."""
        table = self.ui.tableWidget_join
        missing = QBrush(qcolor(current().colors.danger_text))
        for row in range(table.rowCount()):
            form_item = table.item(row, _FORM_COLUMN)
            if form_item is None:
                continue
            has_join_item = any(
                (combo := table.cellWidget(row, column)) is not None
                and bool(combo.currentText())
                for column in _ITEM_COLUMNS
            )
            is_missing = row > 0 and not has_join_item
            form_item.setForeground(missing if is_missing else QBrush())

    def _add_item_dropdown(
        self, row: int, column: int, items: List[str]
    ) -> CellComboBox:
        """Add a dropdown for join-item selection; return it."""
        combo = CellComboBox()
        combo.setAccessibleName(f"Item {column - _ITEM_COLUMNS[0] + 1}")
        combo.addItem("")
        for item in sorted(self.report.get_selected_common_items()):
            combo.addItem(item)
        index = column - _ITEM_COLUMNS[0]
        if index < len(items):
            combo.setCurrentText(items[index])
        combo.currentTextChanged.connect(self.update_join_list)
        self._put_join_widget(row, column, combo)
        return combo

    def update_join_list(self) -> None:
        """Persist join configuration changes back to the report."""
        table = self.ui.tableWidget_join
        join_list = []
        for row in range(table.rowCount()):
            form_name_item = table.item(row, _FORM_COLUMN)
            if not form_name_item:
                continue
            form_name = form_name_item.text()

            join_items = []
            join_combos = []
            for column in _ITEM_COLUMNS:
                combo = table.cellWidget(row, column)
                if combo:
                    join_items.append(combo.currentText())
                    join_combos.append(combo)

            deduped_items, normalized_items = self._dedupe_join_items(join_items)
            if normalized_items != join_items:
                for combo, normalized in zip(join_combos, normalized_items):
                    if combo.currentText() != normalized:
                        combo.blockSignals(True)
                        combo.setCurrentText(normalized)
                        combo.blockSignals(False)

            join_type_combo = table.cellWidget(row, _TYPE_COLUMN)
            join_type = JoinHow.LEFT
            if join_type_combo:
                join_type = join_type_combo.currentText()

            join_list.append([form_name, deduped_items, row + 1, join_type])

        columns_before = set(report_columns.output_identifiers(self.report))
        self.report.update_join_list(join_list)
        self._highlight_missing_join_items()
        self._refresh_joins_banner()
        self._after_join_change(columns_before)

    def _after_join_change(self, columns_before: set) -> None:
        """Follow a join change on the pages whose tables list the columns."""
        # The default column order follows the join order, so rebuild the
        # order/rename table (owned by OrderRenameMixin) after join changes;
        # when the report's columns changed too (a form's own copy of a common
        # item came or went), rebuild the filter tables as well. Not on every
        # change: rebuilding drops a filter row that is still half filled in.
        # Guarded because this mixin is exercised in isolation by tests that
        # build only the join table, and skipped while update_all_ui
        # coordinates a full refresh -- the coordinator rebuilds those tables
        # once at the end instead.
        refresh_tables = hasattr(self.ui, "tableWidget_rename") and not getattr(
            self, "_in_coordinated_refresh", False
        )
        columns_changed = (
            set(report_columns.output_identifiers(self.report)) != columns_before
        )
        if refresh_tables and columns_changed:
            self.update_items_dependent_ui()  # Reports the change too.
            return
        self._report_changed()
        if refresh_tables:
            self.update_order_rename_table()

    @staticmethod
    def _dedupe_join_items(join_items: list[str]) -> tuple[list[str], list[str]]:
        """Return deduped items and normalized UI values without duplicates."""
        seen: set[str] = set()
        deduped: list[str] = []
        normalized: list[str] = []
        for item in join_items:
            if not item:
                normalized.append("")
                continue
            if item in seen:
                normalized.append("")
                continue
            seen.add(item)
            deduped.append(item)
            normalized.append(item)
        return deduped, normalized
