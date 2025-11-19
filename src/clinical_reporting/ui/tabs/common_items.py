"""Common items tab mixin for the Clinical Reporting widget.

This module isolates the logic that manages the shared item list used
across all selected forms.  The mixin mirrors the behavior of the form
selection tab but operates on the report's common item collection.
"""

from __future__ import annotations

from PySide6.QtWidgets import QListWidgetItem


class CommonItemsTabMixin:
    """Behavior for the common items tab."""

    def _init_common_items_tab(self) -> None:
        """Connect signals for the common items tab."""
        self.ui.pushButton_select_common_item.clicked.connect(
            self.click_select_common_item
        )
        self.ui.pushButton_remove_common_item.clicked.connect(
            self.click_remove_common_item
        )
        self.ui.pushButton_select_all_common_item.clicked.connect(
            self.click_select_all_common_item
        )
        self.ui.pushButton_remove_all_common_item.clicked.connect(
            self.click_remove_all_common_item
        )

        self.ui.listWidget_common_item_available.itemDoubleClicked.connect(
            self.on_common_item_available_double_clicked
        )
        self.ui.listWidget_common_item_selected.itemDoubleClicked.connect(
            self.on_common_item_selected_double_clicked
        )

    def update_common_items_ui(self) -> None:
        """Refresh both available and selected common item lists."""
        self.add_listWidget_common_item_available()
        self.add_listWidget_common_item_selected()
        self.update_items_dependent_ui()
        self.update_join_table_ui()

    def add_listWidget_common_item_available(self) -> None:
        """Populate the available common item list widget."""
        self.ui.listWidget_common_item_available.clear()
        for item in sorted(self.report.get_available_common_items()):
            self.ui.listWidget_common_item_available.addItem(item)

    def add_listWidget_common_item_selected(self) -> None:
        """Populate the selected common item list widget."""
        self.ui.listWidget_common_item_selected.clear()
        for item in self.report.get_selected_common_items():
            self.ui.listWidget_common_item_selected.addItem(item)

    def click_select_common_item(self) -> None:
        """Move highlighted items from available to selected."""
        if self._apply_common_item_action("select"):
            self.update_common_items_ui()

    def click_remove_common_item(self) -> None:
        """Return highlighted items to the available list."""
        if self._apply_common_item_action("remove"):
            self.update_common_items_ui()

    def click_select_all_common_item(self) -> None:
        """Move every available common item to the selected list."""
        self._apply_common_item_action("select_all")
        self.update_common_items_ui()

    def click_remove_all_common_item(self) -> None:
        """Return every selected common item to the available list."""
        self._apply_common_item_action("remove_all")
        self.update_common_items_ui()

    def on_common_item_available_double_clicked(self, item: QListWidgetItem) -> None:
        """Double-click shortcut to select a common item."""
        self.ui.listWidget_common_item_available.setCurrentItem(item)
        self.click_select_common_item()

    def on_common_item_selected_double_clicked(self, item: QListWidgetItem) -> None:
        """Double-click shortcut to remove a common item from the selection."""
        self.ui.listWidget_common_item_selected.setCurrentItem(item)
        self.click_remove_common_item()

