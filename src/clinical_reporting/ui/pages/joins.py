"""Joins: how the selected forms are combined into the report's rows."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget

from cci_ui.icons import IconName
from cci_ui.widgets.page import Page
from cci_ui.widgets.status import StatusBanner
from cci_ui.widgets.tables import ColumnSpec, table_card
from clinical_reporting import steps

from ._common import make_table


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
