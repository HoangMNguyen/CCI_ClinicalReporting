"""Selection UI feature behaviors."""

from __future__ import annotations

"""Form selection tab mixin for the Clinical Reporting widget.

This module encapsulates the UI logic for choosing which forms
participate in a report.  It provides the slots that move forms between
the available and selected lists and exposes helpers used by the base
mixin to refresh the two list widgets.
"""

from PySide6.QtWidgets import QListWidgetItem

class FormsTabMixin:
    """Behavior for the form selection tab."""

    def _init_form_tab(self) -> None:
        """Attach handlers used to manage form selection widgets."""
        self.ui.pushButton_select_form.clicked.connect(self.click_select_form)
        self.ui.pushButton_remove_form.clicked.connect(self.click_remove_form)
        self.ui.pushButton_select_all_form.clicked.connect(
            self.click_select_all_form
        )
        self.ui.pushButton_remove_all_form.clicked.connect(
            self.click_remove_all_form
        )

        self.ui.listWidget_form_available.itemDoubleClicked.connect(
            self.on_form_available_double_clicked
        )
        self.ui.listWidget_form_selected.itemDoubleClicked.connect(
            self.on_form_selected_double_clicked
        )
        self.ui.listWidget_form_selected.itemSelectionChanged.connect(
            self.update_form_dependent_ui
        )
        self.ui.lineEdit_form_search.textChanged.connect(
            self.add_listWidget_form_available
        )

    # ------------------------------------------------------------------
    # Refresh helpers used by :class:`ui.base.WidgetBaseMixin`

    def update_forms_ui(self) -> None:
        """Update the available and selected form list widgets."""
        self.add_listWidget_form_available()
        self.add_listWidget_form_selected()

    def add_listWidget_form_available(self) -> None:
        """Populate the available forms list widget."""
        self.ui.listWidget_form_available.clear()
        pattern = self._compile_search_pattern(
            self.ui.lineEdit_form_search.text()
        )
        available_forms = sorted(self.report.get_available_forms_list())
        for form in available_forms:
            if pattern is not None and not pattern.search(form):
                continue
            self.ui.listWidget_form_available.addItem(form)

    def add_listWidget_form_selected(self) -> None:
        """Populate the selected forms list widget."""
        self.ui.listWidget_form_selected.clear()
        for form in self.report.get_selected_forms_list():
            self.ui.listWidget_form_selected.addItem(form)

    # ------------------------------------------------------------------
    # Slots for button and double-click interactions

    def click_select_form(self) -> None:
        """Select highlighted forms from the available list."""
        if self._apply_form_selection_action("select"):
            self._after_form_selection_change()

    def click_remove_form(self) -> None:
        """Remove highlighted forms from the selection list."""
        if self._apply_form_selection_action("remove"):
            self._after_form_selection_change()

    def click_select_all_form(self) -> None:
        """Move every available form into the selection list."""
        if self._apply_form_selection_action("select_all"):
            self._after_form_selection_change()

    def click_remove_all_form(self) -> None:
        """Return every selected form back to the available list."""
        if self._apply_form_selection_action("remove_all"):
            self._after_form_selection_change()

    def on_form_available_double_clicked(self, item: QListWidgetItem) -> None:
        """Double-click shortcut to move a form to the selected list."""
        self.ui.listWidget_form_available.setCurrentItem(item)
        self.click_select_form()

    def on_form_selected_double_clicked(self, item: QListWidgetItem) -> None:
        """Double-click shortcut to return a form to the available list."""
        self.ui.listWidget_form_selected.setCurrentItem(item)
        self.click_remove_form()



"""Common items tab mixin for the Clinical Reporting widget.

This module isolates the logic that manages the shared item list used
across all selected forms.  The mixin mirrors the behavior of the form
selection tab but operates on the report's common item collection.
"""

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
        self.ui.lineEdit_common_item_search.textChanged.connect(
            self.add_listWidget_common_item_available
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
        pattern = self._compile_search_pattern(
            self.ui.lineEdit_common_item_search.text()
        )
        # Items are kept in the input column order by the report model.
        for item in self.report.get_available_common_items():
            if pattern is not None and not pattern.search(item):
                continue
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



"""Per-form item selection mixin for the Clinical Reporting widget.

The routines in this module manage the granular selections of items
within each chosen form.  They mirror the common-item behavior but keep
the form name prefix to disambiguate items originating from different
forms.
"""

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


