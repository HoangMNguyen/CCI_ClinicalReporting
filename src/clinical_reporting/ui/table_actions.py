"""Shared behaviors for two-column original-name/new-name table widgets.

The table on the Order & rename page and the column-name table on the
Additional input page offer the same context action: copy each selected
row's original item name (column 0) into its editable new-name cell
(column 1). This module keeps the action text and the copy loop in one
place; callers supply only the persistence step for their backing model.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

COPY_ORIGINAL_NAME_ACTION_TEXT = "Copy Original Item Name to New Item Name"
COPY_ORIGINAL_NAME_ACTION_TOOLTIP = (
    "Copy the original item name for each selected row into its new item name cell"
)


def add_copy_original_name_action(table, on_triggered) -> QAction:
    """Attach the shared copy context action to *table* and return it."""
    action = QAction(COPY_ORIGINAL_NAME_ACTION_TEXT, table)
    action.setToolTip(COPY_ORIGINAL_NAME_ACTION_TOOLTIP)
    action.triggered.connect(on_triggered)
    table.addAction(action)
    table.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
    return action


def copy_original_names_to_new_names(table, persist) -> None:
    """Copy column 0 into column 1 for each selected row of *table*.

    ``persist`` is called with ``(original_item, new_name_item)`` after the
    new-name cell is updated so the caller can record the change in its
    backing model. Table signals are blocked during the copy so per-cell
    change handlers do not fire for these programmatic edits.
    """
    if table is None or table.selectionModel() is None:
        return

    signals_were_blocked = table.blockSignals(True)
    try:
        for index in table.selectionModel().selectedRows(0):
            original_item = table.item(index.row(), 0)
            new_name_item = table.item(index.row(), 1)
            if original_item is None or new_name_item is None:
                continue
            new_name_item.setText(original_item.text())
            persist(original_item, new_name_item)
    finally:
        table.blockSignals(signals_were_blocked)
