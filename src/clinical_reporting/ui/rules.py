"""Rules UI feature behaviors."""

from __future__ import annotations

"""Comparison, rename, and ordering mixin for the Clinical Reporting widget.

This module groups the behaviours that live on the "Comparison and
Order" tab: rename mapping management, join configuration, and item
ordering.  The routines interact heavily with Qt table widgets, so they
are consolidated here to keep the main widget concise.
"""

from typing import List, Literal

from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtWidgets import QAbstractItemView, QComboBox, QTableWidgetItem

from clinical_reporting.models import JoinHow

class ComparisonTabMixin:
    """Behavior for rename, join, and ordering controls."""

    def _init_comparison_and_order_tab(self) -> None:
        """Wire signals for rename and ordering widgets."""
        table = self.ui.tableWidget_rename
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        table.cellChanged.connect(self.on_rename_cell_changed)
        table.itemSelectionChanged.connect(self._update_order_button_states)
        search_edit = getattr(self.ui, "lineEdit_order_search", None)
        if search_edit is not None:
            search_edit.textChanged.connect(self.search_order_items)
        search_result = getattr(self.ui, "label_search_result", None)
        if search_result is not None:
            search_result.setText("")
        select_next = getattr(self.ui, "pushButton_select_next", None)
        if select_next is not None:
            select_next.clicked.connect(self.click_select_next_order_match)
            select_next.setEnabled(False)
        select_all = getattr(self.ui, "pushButton_select_all", None)
        if select_all is not None:
            select_all.clicked.connect(self.click_select_all_order_matches)
            select_all.setEnabled(False)
        self.ui.pushButton_order_top.clicked.connect(self.click_order_top)
        self.ui.pushButton_order_up.clicked.connect(self.click_order_up)
        self.ui.pushButton_order_down.clicked.connect(self.click_order_down)
        self.ui.pushButton_order_bottom.clicked.connect(self.click_order_bottom)
        self._update_order_button_states()

    # ------------------------------------------------------------------
    # Order and rename table

    def update_order_rename_table(self) -> None:
        """Populate the table in output order while preserving its selection."""
        table = self.ui.tableWidget_rename
        selected_identifiers = {
            self._order_identifier_for_row(row) for row in self._selected_order_rows()
        }
        selected_identifiers.discard(None)
        current_identifier = self._order_identifier_for_row(table.currentRow())

        self.report.update_selected_items_order_list()
        rename_dict = self.report.get_rename_dict()
        signals_were_blocked = table.blockSignals(True)
        try:
            table.setRowCount(0)
            for row, identifier in enumerate(self.report.get_selected_items_order_list()):
                table.insertRow(row)
                orig_item = QTableWidgetItem(identifier)
                orig_item.setFlags(orig_item.flags() & ~Qt.ItemIsEditable)
                orig_item.setData(Qt.UserRole, identifier)
                table.setItem(row, 0, orig_item)
                new_name = rename_dict.get(identifier, "")
                new_item = QTableWidgetItem(new_name)
                table.setItem(row, 1, new_item)

            selection_model = table.selectionModel()
            for row in range(table.rowCount()):
                identifier = self._order_identifier_for_row(row)
                if identifier in selected_identifiers:
                    selection_model.select(
                        table.model().index(row, 0),
                        QItemSelectionModel.SelectionFlag.Select
                        | QItemSelectionModel.SelectionFlag.Rows,
                    )
                if identifier == current_identifier:
                    table.setCurrentCell(
                        row,
                        0,
                        QItemSelectionModel.SelectionFlag.NoUpdate,
                    )
        finally:
            table.blockSignals(signals_were_blocked)

        adjust_columns = getattr(self, "_adjust_column_widths", None)
        if callable(adjust_columns):
            adjust_columns(table)

        search_edit = getattr(self.ui, "lineEdit_order_search", None)
        if search_edit is not None and search_edit.text().strip():
            self.search_order_items(search_edit.text())
        else:
            search_result = getattr(self.ui, "label_search_result", None)
            if search_result is not None:
                search_result.setText("")
            self._update_order_button_states()

    def update_rename_table(self) -> None:
        """Compatibility wrapper for the former rename-only refresh."""
        self.update_order_rename_table()

    def update_items_order_list(self) -> None:
        """Compatibility wrapper for the former ordering-list refresh."""
        self.update_order_rename_table()

    def search_order_items(self, search_text: str) -> None:
        """Select the first original-name match and display the match count."""
        query = search_text.strip().casefold()
        search_result = getattr(self.ui, "label_search_result", None)
        if not query:
            if search_result is not None:
                search_result.setText("")
            self._update_order_search_button_states(0)
            return

        matching_rows = self._matching_order_rows(query)

        if search_result is not None:
            search_result.setText(f"Matches: {len(matching_rows)}")
        self._update_order_search_button_states(len(matching_rows))

        self._select_order_search_rows(matching_rows[:1])
        self._update_order_button_states()

    def click_select_next_order_match(self) -> None:
        """Select the next matching original name, wrapping at the end."""
        matching_rows = self._matching_order_rows()
        if not matching_rows:
            return

        current_row = self.ui.tableWidget_rename.currentRow()
        if current_row in matching_rows:
            current_index = matching_rows.index(current_row)
            next_row = matching_rows[(current_index + 1) % len(matching_rows)]
        else:
            next_row = matching_rows[0]
        self._select_order_search_rows([next_row])
        self._update_order_button_states()

    def click_select_all_order_matches(self) -> None:
        """Select every row whose original name matches the search text."""
        matching_rows = self._matching_order_rows()
        if not matching_rows:
            return
        self._select_order_search_rows(matching_rows)
        self._update_order_button_states()

    def _matching_order_rows(self, normalized_query: str | None = None) -> List[int]:
        """Return table rows matching the current original-name search."""
        if normalized_query is None:
            search_edit = getattr(self.ui, "lineEdit_order_search", None)
            if search_edit is None:
                return []
            normalized_query = search_edit.text().strip().casefold()
        if not normalized_query:
            return []

        table = self.ui.tableWidget_rename
        matching_rows = []
        for row in range(table.rowCount()):
            original_item = table.item(row, 0)
            if (
                original_item is not None
                and normalized_query in original_item.text().casefold()
            ):
                matching_rows.append(row)
        return matching_rows

    def _select_order_search_rows(self, rows: List[int]) -> None:
        """Replace the table selection with the supplied search-result rows."""
        table = self.ui.tableWidget_rename
        table.clearSelection()
        if not rows:
            return

        selection_model = table.selectionModel()
        first_row = rows[0]
        selection_model.setCurrentIndex(
            table.model().index(first_row, 0),
            QItemSelectionModel.SelectionFlag.ClearAndSelect
            | QItemSelectionModel.SelectionFlag.Rows,
        )
        for row in rows[1:]:
            selection_model.select(
                table.model().index(row, 0),
                QItemSelectionModel.SelectionFlag.Select
                | QItemSelectionModel.SelectionFlag.Rows,
            )
        table.scrollToItem(
            table.item(first_row, 0),
            QAbstractItemView.ScrollHint.PositionAtCenter,
        )

    def _update_order_search_button_states(self, match_count: int) -> None:
        """Enable search actions only when they have a useful result."""
        select_next = getattr(self.ui, "pushButton_select_next", None)
        if select_next is not None:
            select_next.setEnabled(match_count > 1)
        select_all = getattr(self.ui, "pushButton_select_all", None)
        if select_all is not None:
            select_all.setEnabled(match_count > 0)

    def on_rename_cell_changed(self, row: int, column: int) -> None:
        """Persist edits to the rename table back to the report."""
        if column != 1:
            return
        item = self.ui.tableWidget_rename.item(row, 0)
        new_name_item = self.ui.tableWidget_rename.item(row, 1)
        if not (item and new_name_item):
            return
        original_name = item.data(Qt.UserRole) or item.text()
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
            join_order_combo.currentTextChanged.connect(lambda value, r=row: self.on_join_order_changed(r, value))
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

        self._highlight_duplicate_join_orders()

    def _highlight_duplicate_join_orders(self) -> None:
        """Flag join orders shared by two or more forms.

        When several forms are assigned the same join order the value is
        ambiguous, so the number is shown in red and bold on every affected
        row.  Rows with a unique order are reset to the default styling.
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
            if order_counts.get(value, 0) > 1:
                combo.setStyleSheet("QComboBox { color: red; font-weight: bold; }")
            else:
                combo.setStyleSheet("")

        # Keep the Run button and its inline hint in sync with the conflict
        # state.  Guarded because this mixin is exercised in isolation by tests
        # that do not compose the run/save behaviour.
        refresh_run = getattr(self, "_refresh_run_availability", None)
        if callable(refresh_run):
            refresh_run()

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

        self.report.update_join_list(join_list)

        # The default column order follows the join order, so re-derive the
        # combined order/rename table after join changes. Guarded because this
        # mixin is exercised in isolation by tests that build only the join
        # table.
        if hasattr(self.ui, "tableWidget_rename"):
            self.update_order_rename_table()

    @staticmethod
    def _dedupe_join_items(join_items: List[str]) -> tuple[List[str], List[str]]:
        """Return deduped items and normalized UI values without duplicates."""
        seen: set[str] = set()
        deduped: List[str] = []
        normalized: List[str] = []
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

    # ------------------------------------------------------------------
    # Item ordering controls

    def click_order_top(self) -> None:
        """Move all selected items to the top while preserving their order."""
        self._move_selected_order_items("top")

    def click_order_up(self) -> None:
        """Move each selected item block one position higher."""
        self._move_selected_order_items("up")

    def click_order_down(self) -> None:
        """Move each selected item block one position lower."""
        self._move_selected_order_items("down")

    def click_order_bottom(self) -> None:
        """Move all selected items to the bottom while preserving their order."""
        self._move_selected_order_items("bottom")

    def _selected_order_rows(self) -> List[int]:
        """Return the selected table rows from top to bottom."""
        selection_model = self.ui.tableWidget_rename.selectionModel()
        if selection_model is None:
            return []
        return sorted(index.row() for index in selection_model.selectedRows())

    def _order_identifier_for_row(self, row: int) -> str | None:
        """Return the stable source identifier stored for a table row."""
        if row < 0:
            return None
        item = self.ui.tableWidget_rename.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.UserRole) or item.text()

    def _move_selected_order_items(
        self, destination: Literal["top", "up", "down", "bottom"]
    ) -> None:
        """Reorder selected table rows and retain the complete selection."""
        table = self.ui.tableWidget_rename
        count = table.rowCount()
        selected_rows = self._selected_order_rows()
        if not selected_rows:
            return

        selected_positions = set(selected_rows)
        new_order = list(range(count))

        if destination == "top":
            new_order = selected_rows + [
                row for row in range(count) if row not in selected_positions
            ]
        elif destination == "bottom":
            new_order = [
                row for row in range(count) if row not in selected_positions
            ] + selected_rows
        elif destination == "up":
            for row in selected_rows:
                if row > 0 and row - 1 not in selected_positions:
                    new_order[row - 1], new_order[row] = new_order[row], new_order[row - 1]
                    selected_positions.remove(row)
                    selected_positions.add(row - 1)
        elif destination == "down":
            for row in reversed(selected_rows):
                if row < count - 1 and row + 1 not in selected_positions:
                    new_order[row], new_order[row + 1] = new_order[row + 1], new_order[row]
                    selected_positions.remove(row)
                    selected_positions.add(row + 1)
        else:
            raise ValueError(f"Unknown order destination: {destination}")

        if new_order == list(range(count)):
            self._update_order_button_states()
            return

        identifiers = [self._order_identifier_for_row(row) for row in range(count)]
        if any(identifier is None for identifier in identifiers):
            return
        self.report.set_selected_items_order_list(
            [identifiers[original_row] for original_row in new_order]
        )
        self.update_order_rename_table()

    def _update_order_button_states(self) -> None:
        """Enable ordering actions only when they can move the selection."""
        table = self.ui.tableWidget_rename
        selected_rows = self._selected_order_rows()
        selected = set(selected_rows)
        can_move_up = any(row > 0 and row - 1 not in selected for row in selected_rows)
        can_move_down = any(
            row < table.rowCount() - 1 and row + 1 not in selected
            for row in selected_rows
        )

        self.ui.pushButton_order_top.setEnabled(can_move_up)
        self.ui.pushButton_order_up.setEnabled(can_move_up)
        self.ui.pushButton_order_down.setEnabled(can_move_down)
        self.ui.pushButton_order_bottom.setEnabled(can_move_down)

    def update_report_order_list_from_widget(self) -> None:
        """Persist the current table ordering back to the report."""
        new_order = [
            identifier
            for row in range(self.ui.tableWidget_rename.rowCount())
            if (identifier := self._order_identifier_for_row(row)) is not None
        ]
        self.report.set_selected_items_order_list(new_order)


"""Filter management mixin for the Clinical Reporting widget.

This module contains all code related to static and dynamic filters.
It provides helper routines for wiring combo boxes, synchronising the
:class:`CLReport` filter collections with the UI tables, and responding to
user edits.
"""

import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QCompleter, QTableWidgetItem

from clinical_reporting.models import Operator, qualify

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
