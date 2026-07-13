"""Per-form item selection mixin for the Clinical Reporting widget.

The routines in this module manage the granular selections of items
within each chosen form.  They mirror the common-item behavior but keep
the form name prefix to disambiguate items originating from different
forms.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem


class FormItemsTabMixin:
    """Behavior for the per-form items tab."""

    def _init_form_items_tab(self) -> None:
        """Connect signals for selecting items that belong to specific forms."""
        self.ui.pushButton_select_form_item.clicked.connect(
            self.click_select_form_item
        )
        self.ui.pushButton_remove_form_item.clicked.connect(
            self.click_remove_form_item
        )
        self.ui.pushButton_select_all_form_item.clicked.connect(
            self.click_select_all_form_item
        )
        self.ui.pushButton_remove_all_form_item.clicked.connect(
            self.click_remove_all_form_item
        )

        self.ui.listWidget_form_item_available.itemDoubleClicked.connect(
            self.on_form_item_available_double_clicked
        )
        self.ui.listWidget_form_item_selected.itemDoubleClicked.connect(
            self.on_form_item_selected_double_clicked
        )
        self.ui.lineEdit_form_item_search.textChanged.connect(
            self.add_listWidget_form_item_available
        )

    def update_form_items_ui(self) -> None:
        """Refresh the form-item widgets and any dependent UI elements."""
        self.add_listWidget_form_item_available()
        self.add_listWidget_form_item_selected()
        self.update_items_dependent_ui()

    def add_listWidget_form_item_available(self) -> None:
        """Populate the per-form available item list with all selected forms."""
        self.ui.listWidget_form_item_available.clear()
        selected_forms = self.report.get_selected_forms_list()
        if not selected_forms:
            return

        pattern = self._compile_search_pattern(
            self.ui.lineEdit_form_item_search.text()
        )
        available_entries = []
        for form_name in selected_forms:
            if form_name in self.report.selected_forms:
                form_items = self.report.selected_forms[form_name].get_available_form_items()
                for item in form_items:
                    display_text = f"{form_name}.{item}"
                    if pattern is not None and not pattern.search(display_text):
                        continue
                    available_entries.append((display_text, form_name, item))

        # Entries stay grouped by form with items in the input column order.
        for display_text, form_name, item in available_entries:
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.UserRole, (form_name, item))
            self.ui.listWidget_form_item_available.addItem(list_item)

    def add_listWidget_form_item_selected(self) -> None:
        """Populate the per-form selected item list."""
        self.ui.listWidget_form_item_selected.clear()
        selected_forms = self.report.get_selected_forms_list()
        if not selected_forms:
            return

        combined_items = []
        for form_name in selected_forms:
            if form_name in self.report.selected_forms:
                form_items = self.report.selected_forms[form_name].get_selected_form_items()
                for item in form_items:
                    combined_items.append((f"{form_name}.{item}", form_name, item))

        for display_text, form_name, item in combined_items:
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.UserRole, (form_name, item))
            self.ui.listWidget_form_item_selected.addItem(list_item)

    def click_select_form_item(self) -> None:
        """Move highlighted per-form items into the selected list."""
        if self._apply_form_item_action("select"):
            self.update_form_items_ui()

    def click_remove_form_item(self) -> None:
        """Return highlighted per-form items to the available list."""
        if self._apply_form_item_action("remove"):
            self.update_form_items_ui()

    def click_select_all_form_item(self) -> None:
        """Select every available per-form item."""
        self._apply_form_item_action("select_all")
        self.update_form_items_ui()

    def click_remove_all_form_item(self) -> None:
        """Return every selected per-form item to the available list."""
        self._apply_form_item_action("remove_all")
        self.update_form_items_ui()

    def on_form_item_available_double_clicked(self, item: QListWidgetItem) -> None:
        """Double-click shortcut to select a per-form item."""
        self.ui.listWidget_form_item_available.setCurrentItem(item)
        self.click_select_form_item()

    def on_form_item_selected_double_clicked(self, item: QListWidgetItem) -> None:
        """Double-click shortcut to remove a per-form item."""
        self.ui.listWidget_form_item_selected.setCurrentItem(item)
        self.click_remove_form_item()

