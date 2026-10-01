"""Join configuration table on the Joins page.

This mixin owns the join table: per-form join item dropdowns, join order,
join type, and the inline conflict highlighting.  The order/rename table
on the Order & rename page lives in :mod:`ui.ordering_tab`; join changes trigger
its refresh because the default column order follows the join order. When a
join change adds or removes a form's own copy of a common item (``AE.Visit``,
see :mod:`clinical_reporting.report_columns`), the filter tables are rebuilt
too, since their item lists change.

Conflicts are drawn in the theme's colors: a shared join order marks its
dropdowns ``invalid`` (styled by the ``cci_ui`` stylesheet), and a form that
needs a join item gets its name in the danger color. The banner above the
table spells the problems out (:func:`clinical_reporting.steps.joins_message`).
"""

from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import QComboBox, QTableWidgetItem

from cci_ui.theme.manager import current, set_invalid, theme_events
from cci_ui.theme.palette import qcolor
from clinical_reporting import report_columns, steps
from clinical_reporting.models import JoinHow


class JoinConfigMixin:
    """Behavior for the join configuration controls."""

    def _init_join_table(self) -> None:
        """Recolor forms missing a join item when the theme changes.

        (The stylesheet restyles the invalid join orders by itself.)
        """
        # A bound method of the window, so Qt drops the connection with it.
        theme_events().changed.connect(self._paint_missing_join_items)

    def update_join_table_ui(self) -> None:
        """Refresh join controls when selections change."""
        self.update_selected_forms_table()

    def update_selected_forms_table(self) -> None:
        """Populate the join configuration table."""
        # No handler is connected to ``tableWidget_join.cellChanged`` (join edits
        # are captured via the per-cell combo boxes), so there is nothing to
        # disconnect here before repopulating the table.
        self.ui.tableWidget_join.setRowCount(0)
        join_data = self.report.get_join_list_dict()
        # Max join order equals number of selected forms
        selected_forms = self.report.get_selected_forms_list()
        max_order = max(1, len(selected_forms))

        for row, form_name in enumerate(self.report.get_selected_forms_list()):
            self.ui.tableWidget_join.insertRow(row)
            form_item = QTableWidgetItem(form_name)
            form_item.setFlags(form_item.flags() & ~Qt.ItemIsEditable)
            self.ui.tableWidget_join.setItem(row, 0, form_item)

            for col in range(1, 4):
                self._add_item_dropdown(row, col, form_name, join_data)

            join_order_combo = QComboBox()
            join_order_combo.addItems([str(i) for i in range(1, max_order + 1)])
            # Determine current/default order; clamp to available range if needed
            desired_order = 1
            if form_name in join_data and join_data[form_name]["order"]:
                try:
                    desired_order = int(join_data[form_name]["order"])
                except (TypeError, ValueError):
                    desired_order = 1
            clamped_order = min(max(1, desired_order), max_order)
            join_order_combo.setCurrentText(str(clamped_order))
            join_order_combo.currentTextChanged.connect(self.update_join_list)
            join_order_combo.currentTextChanged.connect(
                lambda value, r=row: self.on_join_order_changed(r, value)
            )
            self.ui.tableWidget_join.setCellWidget(row, 4, join_order_combo)

            # If we had to clamp the value, persist it immediately to the model
            if clamped_order != desired_order:
                items = join_data.get(form_name, {}).get("items", [])
                how = join_data.get(form_name, {}).get("how", JoinHow.LEFT)
                self.report.update_join_items(form_name, items, clamped_order, how)

            join_type_combo = QComboBox()
            for join_type in JoinHow.ALL:
                join_type_combo.addItem(join_type)
            default_join_type = JoinHow.LEFT
            if form_name in join_data and join_data[form_name]["how"]:
                default_join_type = join_data[form_name]["how"]
            join_type_combo.setCurrentText(default_join_type)
            join_type_combo.currentTextChanged.connect(self.update_join_list)
            self.ui.tableWidget_join.setCellWidget(row, 5, join_type_combo)

            if clamped_order == 1:
                self.on_join_order_changed(row, "1")

        self._highlight_duplicate_join_orders()
        self._highlight_missing_join_items()
        self._refresh_joins_banner()

    def _refresh_joins_banner(self) -> None:
        """Say above the join table what stops the joins, or why there are none."""
        message = steps.joins_message(self.report)
        self._set_label_text(getattr(self.ui, "banner_joins", None), message or "")

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

        self._highlight_duplicate_join_orders()

    def _highlight_duplicate_join_orders(self) -> None:
        """Flag join orders shared by two or more forms.

        When several forms are assigned the same join order the value is
        ambiguous, so the order dropdown of every affected row is marked
        invalid (the stylesheet shows it in the danger color, semibold, with
        a danger border). Rows with a unique order are cleared.
        """
        order_col = 4
        table = self.ui.tableWidget_join

        combos = []
        order_counts: dict[str, int] = {}
        for row in range(table.rowCount()):
            combo = table.cellWidget(row, order_col)
            if combo is None:
                continue
            value = combo.currentText()
            combos.append((combo, value))
            order_counts[value] = order_counts.get(value, 0) + 1

        for combo, value in combos:
            set_invalid(combo, order_counts.get(value, 0) > 1)

        # Keep the Run button and its inline hint in sync with the conflict
        # state.  Guarded because this mixin is exercised in isolation by tests
        # that do not compose the run/save behaviour.
        refresh_run = getattr(self, "_refresh_run_availability", None)
        if callable(refresh_run):
            refresh_run()

    def _highlight_missing_join_items(self) -> None:
        """Flag non-first forms without a join item and update Export to Excel."""
        self._paint_missing_join_items()

        # Join-item dropdown changes can resolve or introduce this error without
        # changing the join order, so refresh Export to Excel from here too.
        refresh_run = getattr(self, "_refresh_run_availability", None)
        if callable(refresh_run):
            refresh_run()

    def _paint_missing_join_items(self) -> None:
        """Show non-first forms without a join item in the danger color."""
        table = self.ui.tableWidget_join
        missing = QBrush(qcolor(current().colors.danger_text))
        for row in range(table.rowCount()):
            form_item = table.item(row, 0)
            order_combo = table.cellWidget(row, 4)
            if form_item is None or order_combo is None:
                continue

            has_join_item = any(
                (combo := table.cellWidget(row, col)) is not None
                and bool(combo.currentText())
                for col in range(1, 4)
            )
            is_missing = order_combo.currentText() != "1" and not has_join_item
            form_item.setForeground(missing if is_missing else QBrush())

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
            join_combos = []
            for col in range(1, 4):
                combo = self.ui.tableWidget_join.cellWidget(row, col)
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

            join_order_combo = self.ui.tableWidget_join.cellWidget(row, 4)
            join_order = 1
            if join_order_combo:
                try:
                    join_order = int(join_order_combo.currentText())
                except ValueError:
                    join_order = 1

            join_type_combo = self.ui.tableWidget_join.cellWidget(row, 5)
            join_type = JoinHow.LEFT
            if join_type_combo:
                join_type = join_type_combo.currentText()

            join_list.append([form_name, deduped_items, join_order, join_type])

        columns_before = set(report_columns.output_identifiers(self.report))
        self.report.update_join_list(join_list)
        self._highlight_missing_join_items()
        self._refresh_joins_banner()

        # The default column order follows the join order, so rebuild the
        # order/rename table (owned by OrderRenameTabMixin) after join changes;
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
