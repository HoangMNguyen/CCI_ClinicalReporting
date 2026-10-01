"""Forms, Common items, and Form items: the same two-list picker three times."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget

from cci_ui.icons import IconName
from cci_ui.widgets.dual_list import DualListPicker
from cci_ui.widgets.page import Page
from clinical_reporting import steps


class _SelectionPage(Page):
    """A page holding one available ⇄ selected picker that fills it."""

    def __init__(
        self,
        title: str,
        subtitle: str,
        *,
        search_placeholder: str,
        available_placeholder: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(title, subtitle, parent=parent)
        self.picker = DualListPicker(
            search_placeholder=search_placeholder,
            available_placeholder=available_placeholder,
        )
        # "All" means every available entry, not only those the search shows.
        for button, tooltip in (
            (self.picker.add_all_button, "Add all"),
            (self.picker.remove_all_button, "Remove all"),
        ):
            button.setToolTip(tooltip)
            button.setAccessibleName(tooltip)
        self.body.addWidget(self.picker, 1)


class FormsPage(_SelectionPage):
    """Which forms go into the report."""

    KEY = steps.FORMS
    SECTION = "Selection"
    ICON = IconName.FORMS
    EXPORTS = (
        "lineEdit_form_search",
        "listWidget_form_available",
        "listWidget_form_selected",
        "pushButton_select_form",
        "pushButton_select_all_form",
        "pushButton_remove_form",
        "pushButton_remove_all_form",
    )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            "Forms",
            "Choose which forms go into the report.",
            search_placeholder="Search forms",
            available_placeholder="No forms to add. Load a Corelisting ZIP first.",
            parent=parent,
        )
        self.lineEdit_form_search = self.picker.search
        self.listWidget_form_available = self.picker.available
        self.listWidget_form_selected = self.picker.selected
        self.pushButton_select_form = self.picker.add_button
        self.pushButton_select_all_form = self.picker.add_all_button
        self.pushButton_remove_form = self.picker.remove_button
        self.pushButton_remove_all_form = self.picker.remove_all_button


class CommonItemsPage(_SelectionPage):
    """Items every selected form has, such as the subject and visit."""

    KEY = steps.COMMON
    SECTION = "Selection"
    ICON = IconName.COMMON_ITEMS
    EXPORTS = (
        "lineEdit_common_item_search",
        "listWidget_common_item_available",
        "listWidget_common_item_selected",
        "pushButton_select_common_item",
        "pushButton_select_all_common_item",
        "pushButton_remove_common_item",
        "pushButton_remove_all_common_item",
    )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            "Common items",
            "Items shared by every selected form, such as the subject and visit.",
            search_placeholder="Search common items",
            available_placeholder="No common items to add.",
            parent=parent,
        )
        self.lineEdit_common_item_search = self.picker.search
        self.listWidget_common_item_available = self.picker.available
        self.listWidget_common_item_selected = self.picker.selected
        self.pushButton_select_common_item = self.picker.add_button
        self.pushButton_select_all_common_item = self.picker.add_all_button
        self.pushButton_remove_common_item = self.picker.remove_button
        self.pushButton_remove_all_common_item = self.picker.remove_all_button


class FormItemsPage(_SelectionPage):
    """Items of each selected form to include as report columns."""

    KEY = steps.FORM_ITEMS
    SECTION = "Selection"
    ICON = IconName.FORM_ITEMS
    EXPORTS = (
        "lineEdit_form_item_search",
        "listWidget_form_item_available",
        "listWidget_form_item_selected",
        "pushButton_select_form_item",
        "pushButton_select_all_form_item",
        "pushButton_remove_form_item",
        "pushButton_remove_all_form_item",
    )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            "Form items",
            "Items from each selected form to include as report columns.",
            search_placeholder="Search form items",
            available_placeholder="No items to add. Select forms first.",
            parent=parent,
        )
        self.lineEdit_form_item_search = self.picker.search
        self.listWidget_form_item_available = self.picker.available
        self.listWidget_form_item_selected = self.picker.selected
        self.pushButton_select_form_item = self.picker.add_button
        self.pushButton_select_all_form_item = self.picker.add_all_button
        self.pushButton_remove_form_item = self.picker.remove_button
        self.pushButton_remove_all_form_item = self.picker.remove_all_button
