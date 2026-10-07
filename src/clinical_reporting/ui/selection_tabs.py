"""Form, common-item, and per-form-item selection pages.

The three mixins here are the same dual-list picker pattern applied to
three collections: whole forms, common items shared across forms, and the
items within each selected form.  They provide the slots that move entries
between the available and selected lists and expose the refresh helpers
used by :class:`ui.base.WidgetBaseMixin`.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

from PySide6.QtWidgets import QListWidgetItem

from clinical_reporting.models import is_qualified, qualify, split_qualified


def _compile_search_pattern(pattern_text: str) -> Optional[re.Pattern[str]]:
    """Compile a case-insensitive search regex; return ``None`` if empty/invalid."""
    if not pattern_text:
        return None

    try:
        return re.compile(pattern_text, flags=re.IGNORECASE)
    except re.error:
        return None


class FormsMixin:
    """Behavior for the Forms page."""

    def _init_forms(self) -> None:
        """Attach handlers used to manage form selection widgets."""
        self.ui.pushButton_select_form.clicked.connect(self.click_select_form)
        self.ui.pushButton_remove_form.clicked.connect(self.click_remove_form)
        self.ui.pushButton_select_all_form.clicked.connect(self.click_select_all_form)
        self.ui.pushButton_remove_all_form.clicked.connect(self.click_remove_all_form)

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
        pattern = _compile_search_pattern(self.ui.lineEdit_form_search.text())
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
            self.update_all_ui()

    def click_remove_form(self) -> None:
        """Remove highlighted forms from the selection list."""
        if self._apply_form_selection_action("remove"):
            self.update_all_ui()

    def click_select_all_form(self) -> None:
        """Move every available form into the selection list."""
        if self._apply_form_selection_action("select_all"):
            self.update_all_ui()

    def click_remove_all_form(self) -> None:
        """Return every selected form back to the available list."""
        if self._apply_form_selection_action("remove_all"):
            self.update_all_ui()

    def on_form_available_double_clicked(self, item: QListWidgetItem) -> None:
        """Double-click shortcut to move a form to the selected list."""
        self.ui.listWidget_form_available.setCurrentItem(item)
        self.click_select_form()

    def on_form_selected_double_clicked(self, item: QListWidgetItem) -> None:
        """Double-click shortcut to return a form to the available list."""
        self.ui.listWidget_form_selected.setCurrentItem(item)
        self.click_remove_form()

    def _apply_form_selection_action(self, action: str) -> bool:
        """Mutate report form selections based on the requested action."""
        if action == "select":
            selected_items = self.ui.listWidget_form_available.selectedItems()
            if not selected_items:
                return False
            for item in selected_items:
                self.report.add_selected_form(item.text())
            return True

        if action == "remove":
            selected_items = self.ui.listWidget_form_selected.selectedItems()
            if not selected_items:
                return False
            for item in selected_items:
                self.report.add_available_form(item.text())
            return True

        if action == "select_all":
            available_forms = self.report.get_available_forms_list()
            if not available_forms:
                return False
            self.report.add_all_selected_forms()
            return True

        if action == "remove_all":
            selected_forms = self.report.get_selected_forms_list()
            if not selected_forms:
                return False
            self.report.add_all_available_forms()
            return True

        raise ValueError(f"Unknown form selection action: {action}")


class CommonItemsMixin:
    """Behavior for the Common items page."""

    def _init_common_items(self) -> None:
        """Connect signals for the Common items page."""
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

    def add_listWidget_common_item_available(self) -> None:
        """Populate the available common item list widget."""
        self.ui.listWidget_common_item_available.clear()
        pattern = _compile_search_pattern(self.ui.lineEdit_common_item_search.text())
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
            self.update_all_ui()

    def click_remove_common_item(self) -> None:
        """Return highlighted items to the available list."""
        if self._apply_common_item_action("remove"):
            self.update_all_ui()

    def click_select_all_common_item(self) -> None:
        """Move every available common item to the selected list."""
        self._apply_common_item_action("select_all")
        self.update_all_ui()

    def click_remove_all_common_item(self) -> None:
        """Return every selected common item to the available list."""
        self._apply_common_item_action("remove_all")
        self.update_all_ui()

    def on_common_item_available_double_clicked(self, item: QListWidgetItem) -> None:
        """Double-click shortcut to select a common item."""
        self.ui.listWidget_common_item_available.setCurrentItem(item)
        self.click_select_common_item()

    def on_common_item_selected_double_clicked(self, item: QListWidgetItem) -> None:
        """Double-click shortcut to remove a common item from the selection."""
        self.ui.listWidget_common_item_selected.setCurrentItem(item)
        self.click_remove_common_item()

    def _toggle_common_item_selection(self, widget, *, selected: bool) -> bool:
        """Update common item state for all entries selected in ``widget``."""
        selected_items = widget.selectedItems()
        if not selected_items:
            return False

        for item in selected_items:
            self.report.set_common_item_state(item.text(), selected=selected)

        return True

    def _apply_common_item_action(self, action: str) -> bool:
        """Mutate common item selections using a shared implementation."""
        if action == "select":
            return self._toggle_common_item_selection(
                self.ui.listWidget_common_item_available, selected=True
            )

        if action == "remove":
            return self._toggle_common_item_selection(
                self.ui.listWidget_common_item_selected, selected=False
            )

        if action == "select_all":
            available_items = list(self.report.get_available_common_items())
            if not available_items:
                return False
            for item in available_items:
                self.report.set_common_item_state(item, selected=True)
            return True

        if action == "remove_all":
            selected_items = list(self.report.get_selected_common_items())
            if not selected_items:
                return False
            for item in selected_items:
                self.report.set_common_item_state(item, selected=False)
            return True

        raise ValueError(f"Unknown common item action: {action}")


class FormItemsMixin:
    """Behavior for the Form items page.

    Mirrors the common-item behavior but keeps the form name prefix to
    disambiguate items originating from different forms.
    """

    def _init_form_items(self) -> None:
        """Connect signals for selecting items that belong to specific forms."""
        self.ui.pushButton_select_form_item.clicked.connect(self.click_select_form_item)
        self.ui.pushButton_remove_form_item.clicked.connect(self.click_remove_form_item)
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
        """Refresh the available and selected per-form item lists."""
        self.add_listWidget_form_item_available()
        self.add_listWidget_form_item_selected()

    def add_listWidget_form_item_available(self) -> None:
        """Populate the per-form available item list with all selected forms."""
        self.ui.listWidget_form_item_available.clear()
        selected_forms = self.report.get_selected_forms_list()
        if not selected_forms:
            return

        pattern = _compile_search_pattern(self.ui.lineEdit_form_item_search.text())
        available_entries = []
        for form_name in selected_forms:
            if form_name in self.report.selected_forms:
                form_items = self.report.selected_forms[
                    form_name
                ].get_available_form_items()
                for item in form_items:
                    display_text = qualify(form_name, item)
                    if pattern is not None and not pattern.search(display_text):
                        continue
                    available_entries.append((display_text, form_name, item))

        # Entries stay grouped by form with items in the input column order.
        for display_text, form_name, item in available_entries:
            list_item = QListWidgetItem(display_text)
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
                form_items = self.report.selected_forms[
                    form_name
                ].get_selected_form_items()
                for item in form_items:
                    combined_items.append((qualify(form_name, item), form_name, item))

        for display_text, form_name, item in combined_items:
            list_item = QListWidgetItem(display_text)
            self.ui.listWidget_form_item_selected.addItem(list_item)

    def click_select_form_item(self) -> None:
        """Move highlighted per-form items into the selected list."""
        if self._apply_form_item_action("select"):
            self.update_form_items_ui()
            self.update_items_dependent_ui()

    def click_remove_form_item(self) -> None:
        """Return highlighted per-form items to the available list."""
        if self._apply_form_item_action("remove"):
            self.update_form_items_ui()
            self.update_items_dependent_ui()

    def click_select_all_form_item(self) -> None:
        """Select every available per-form item."""
        self._apply_form_item_action("select_all")
        self.update_form_items_ui()
        self.update_items_dependent_ui()

    def click_remove_all_form_item(self) -> None:
        """Return every selected per-form item to the available list."""
        self._apply_form_item_action("remove_all")
        self.update_form_items_ui()
        self.update_items_dependent_ui()

    def on_form_item_available_double_clicked(self, item: QListWidgetItem) -> None:
        """Double-click shortcut to select a per-form item."""
        self.ui.listWidget_form_item_available.setCurrentItem(item)
        self.click_select_form_item()

    def on_form_item_selected_double_clicked(self, item: QListWidgetItem) -> None:
        """Double-click shortcut to remove a per-form item."""
        self.ui.listWidget_form_item_selected.setCurrentItem(item)
        self.click_remove_form_item()

    def _iter_form_item_pairs(self, widget) -> Iterable[tuple[str, str]]:
        """Yield ``(form_name, item_name)`` tuples from the widget selections."""
        for item in widget.selectedItems():
            item_text = item.text()
            if is_qualified(item_text):
                yield split_qualified(item_text)

    def _toggle_form_item_selection(self, widget, *, selected: bool) -> bool:
        """Update per-form item state for all entries selected in ``widget``."""
        changed = False
        for form_name, item_name in self._iter_form_item_pairs(widget):
            if form_name in self.report.selected_forms:
                self.report.selected_forms[form_name].set_form_item_state(
                    item_name, selected=selected
                )
                changed = True
        return changed

    def _apply_form_item_action(self, action: str) -> bool:
        """Mutate form item selections using a shared implementation."""
        if action == "select":
            return self._toggle_form_item_selection(
                self.ui.listWidget_form_item_available, selected=True
            )

        if action == "remove":
            return self._toggle_form_item_selection(
                self.ui.listWidget_form_item_selected, selected=False
            )

        if action == "select_all":
            changed = False
            for form_name in self.report.get_selected_forms_list():
                if form_name in self.report.selected_forms:
                    available_items = self.report.selected_forms[
                        form_name
                    ].get_available_form_items()
                    if not available_items:
                        continue
                    for item in available_items[:]:
                        self.report.selected_forms[form_name].set_form_item_state(
                            item, selected=True
                        )
                    changed = True
            return changed

        if action == "remove_all":
            changed = False
            for form_name in self.report.get_selected_forms_list():
                if form_name in self.report.selected_forms:
                    selected_items = self.report.selected_forms[
                        form_name
                    ].get_selected_form_items()
                    if not selected_items:
                        continue
                    for item in selected_items[:]:
                        self.report.selected_forms[form_name].set_form_item_state(
                            item, selected=False
                        )
                    changed = True
            return changed

        raise ValueError(f"Unknown form item action: {action}")
