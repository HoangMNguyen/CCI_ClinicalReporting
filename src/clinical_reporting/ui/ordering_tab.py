"""Column order and rename table on the Order & rename page.

This mixin owns the combined order/rename table: rename mapping
management, item ordering controls, and the original-name search. The
join table lives in :mod:`ui.join_config`; its
:meth:`JoinConfigMixin.update_join_list` re-derives this table because the
default column order follows the join order.
"""

from __future__ import annotations

from typing import List, Literal

from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtWidgets import QAbstractItemView, QTableWidgetItem

from clinical_reporting.ui.table_actions import (
    add_copy_original_name_action,
    copy_original_names_to_new_names,
)


class OrderRenameTabMixin:
    """Behavior for the rename and ordering controls."""

    def _init_comparison_and_order_tab(self) -> None:
        """Wire signals for rename and ordering widgets."""
        table = self.ui.tableWidget_rename
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.copy_original_name_action = add_copy_original_name_action(
            table, self.copy_selected_original_names_to_rename
        )
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
            for row, identifier in enumerate(
                self.report.get_selected_items_order_list()
            ):
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

        search_edit = getattr(self.ui, "lineEdit_order_search", None)
        if search_edit is not None:
            # Reordering rebuilds this table. Refresh the search status without
            # running the active-search selection behavior, which would replace
            # the rows whose selection was just restored above.
            self._refresh_order_search_status(search_edit.text())
        self._update_order_button_states()

    def search_order_items(self, search_text: str) -> None:
        """Select the first original-name match and display the match count."""
        query = search_text.strip().casefold()
        if not query:
            self._refresh_order_search_status(search_text)
            return

        matching_rows = self._refresh_order_search_status(search_text)

        self._select_order_search_rows(matching_rows[:1])
        self._update_order_button_states()

    def _refresh_order_search_status(self, search_text: str) -> List[int]:
        """Refresh search metadata without changing the table selection."""
        query = search_text.strip().casefold()
        search_result = getattr(self.ui, "label_search_result", None)
        matching_rows = self._matching_order_rows(query) if query else []

        if search_result is not None:
            search_result.setText(f"Matches: {len(matching_rows)}" if query else "")
        self._update_order_search_button_states(len(matching_rows))
        return matching_rows

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
        self._report_changed()

    def copy_selected_original_names_to_rename(self) -> None:
        """Copy each selected row's original name into its editable name cell."""

        def persist(original_item, _new_name_item) -> None:
            original_name = original_item.data(Qt.UserRole) or original_item.text()
            self.report.set_rename_item(original_name, original_item.text())

        copy_original_names_to_new_names(self.ui.tableWidget_rename, persist)
        self._report_changed()

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
                    new_order[row - 1], new_order[row] = (
                        new_order[row],
                        new_order[row - 1],
                    )
                    selected_positions.remove(row)
                    selected_positions.add(row - 1)
        elif destination == "down":
            for row in reversed(selected_rows):
                if row < count - 1 and row + 1 not in selected_positions:
                    new_order[row], new_order[row + 1] = (
                        new_order[row + 1],
                        new_order[row],
                    )
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
