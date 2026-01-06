"""Form selection tab mixin for the Clinical Reporting widget.

This module encapsulates the UI logic for choosing which forms
participate in a report.  It provides the slots that move forms between
the available and selected lists and exposes helpers used by the base
mixin to refresh the two list widgets.
"""

from __future__ import annotations

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

