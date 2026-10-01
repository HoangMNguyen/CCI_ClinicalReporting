"""Filters, Joins, and Comparisons: the rules that shape the report's rows."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget

from cci_ui.icons import IconName
from cci_ui.widgets.page import Page
from cci_ui.widgets.status import StatusBanner
from cci_ui.widgets.tables import ColumnSpec, TableToolbar, table_card
from clinical_reporting import steps

from ._common import make_table


class FiltersPage(Page):
    """Rows kept only when an item matches a value."""

    KEY = steps.FILTERS
    SECTION = "Rules"
    ICON = IconName.FILTERS
    EXPORTS = (
        "tableWidget_static_filter",
        "pushButton_static_filter_add",
        "pushButton_static_filter_remove",
    )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            steps.TITLES[self.KEY],
            "Keep only rows that match every filter.",
            parent=parent,
        )
        # Row numbers: validation messages name filters by row.
        self.tableWidget_static_filter = make_table(
            ["Item", "Operator", "Value"],
            [ColumnSpec("stretch"), ColumnSpec("fixed", 170), ColumnSpec("stretch")],
            placeholder="No filters. Press + to add one.",
            row_numbers=True,
        )
        toolbar = TableToolbar(
            add_tooltip="Add filter",
            remove_tooltip="Remove selected filter",
            caption="Select a row, then press − to remove it.",
        )
        self.pushButton_static_filter_add = toolbar.add_button
        self.pushButton_static_filter_remove = toolbar.remove_button
        self.body.addWidget(table_card(self.tableWidget_static_filter), 1)
        self.body.addWidget(toolbar)


class JoinsPage(Page):
    """How the selected forms are combined."""

    KEY = steps.JOINS
    SECTION = "Rules"
    ICON = IconName.JOINS
    EXPORTS = ("banner_joins", "tableWidget_join")

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            steps.TITLES[self.KEY],
            "Set how the selected forms are combined. Forms are joined in Order, "
            "using Item 1–3 as the matching keys.",
            parent=parent,
        )
        self.tableWidget_join = make_table(
            ["Form", "Item 1", "Item 2", "Item 3", "Order", "Type"],
            [
                ColumnSpec("interactive", 190),
                ColumnSpec("stretch"),
                ColumnSpec("stretch"),
                ColumnSpec("stretch"),
                ColumnSpec("fixed", 84),
                ColumnSpec("fixed", 140),
            ],
            placeholder="Select forms to set how they are joined.",
        )
        # What stops the joins from working, kept current as they change: a
        # state of the page, so it isn't repeated in the status bar.
        self.banner_joins = StatusBanner(dismissible=False, announce=False)
        self.body.addWidget(self.banner_joins)
        self.body.addWidget(table_card(self.tableWidget_join), 1)


class ComparisonsPage(Page):
    """Rows kept only when one item compares to another."""

    KEY = steps.COMPARISONS
    SECTION = "Rules"
    ICON = IconName.COMPARISONS
    EXPORTS = (
        "tableWidget_dynamic_filter",
        "pushButton_dynamic_filter_add",
        "pushButton_dynamic_filter_remove",
    )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            steps.TITLES[self.KEY],
            "Keep only rows where one item compares to another, for example an "
            "end date on or after its start date.",
            parent=parent,
        )
        self.tableWidget_dynamic_filter = make_table(
            ["Item 1", "Operator", "Item 2"],
            [ColumnSpec("stretch"), ColumnSpec("fixed", 120), ColumnSpec("stretch")],
            placeholder="No comparisons. Press + to add one.",
            row_numbers=True,
        )
        toolbar = TableToolbar(
            add_tooltip="Add comparison", remove_tooltip="Remove selected comparison"
        )
        self.pushButton_dynamic_filter_add = toolbar.add_button
        self.pushButton_dynamic_filter_remove = toolbar.remove_button
        self.body.addWidget(table_card(self.tableWidget_dynamic_filter), 1)
        self.body.addWidget(toolbar)
