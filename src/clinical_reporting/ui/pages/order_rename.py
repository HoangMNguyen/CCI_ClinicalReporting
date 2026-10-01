"""Order & rename: the output's column order and column names."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout, QWidget

from cci_ui.icons import IconName
from cci_ui.widgets.buttons import button_group, icon_button, make_button
from cci_ui.widgets.labels import text_label
from cci_ui.widgets.page import Page
from cci_ui.widgets.search import SearchField
from cci_ui.widgets.tables import ColumnSpec, table_card
from clinical_reporting import steps

from ._common import make_table


class OrderRenamePage(Page):
    """Where the report's columns get their order and readable names."""

    KEY = steps.ORDER
    SECTION = "Output"
    ICON = IconName.ORDER_RENAME
    EXPORTS = (
        "lineEdit_order_search",
        "label_search_result",
        "pushButton_select_next",
        "pushButton_select_all",
        "pushButton_order_top",
        "pushButton_order_up",
        "pushButton_order_down",
        "pushButton_order_bottom",
        "tableWidget_rename",
    )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            "Order & rename",
            "Set the column order of the Excel output and give columns readable names.",
            parent=parent,
        )
        self.lineEdit_order_search = SearchField("Search columns")
        self.lineEdit_order_search.setMinimumWidth(160)
        self.lineEdit_order_search.setMaximumWidth(320)
        self.label_search_result = text_label(style="caption")
        self.pushButton_select_next = make_button("Next match")
        self.pushButton_select_all = make_button("Select all matches")
        self.pushButton_order_top = icon_button(
            IconName.MOVE_TOP, "Move to top", variant="secondary"
        )
        self.pushButton_order_up = icon_button(
            IconName.MOVE_UP, "Move up", variant="secondary"
        )
        self.pushButton_order_down = icon_button(
            IconName.MOVE_DOWN, "Move down", variant="secondary"
        )
        self.pushButton_order_bottom = icon_button(
            IconName.MOVE_BOTTOM, "Move to bottom", variant="secondary"
        )
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.addWidget(self.lineEdit_order_search, 1)
        toolbar.addWidget(self.label_search_result)
        toolbar.addWidget(self.pushButton_select_next)
        toolbar.addWidget(self.pushButton_select_all)
        toolbar.addStretch(1)
        toolbar.addWidget(
            button_group(
                self.pushButton_order_top,
                self.pushButton_order_up,
                self.pushButton_order_down,
                self.pushButton_order_bottom,
            )
        )

        self.tableWidget_rename = make_table(
            ["Original name", "Output name"],
            [ColumnSpec("stretch"), ColumnSpec("stretch")],
            placeholder="Select forms and items to set the column order.",
            row_numbers=True,
            selection=QAbstractItemView.SelectionMode.ExtendedSelection,
        )
        self.body.addLayout(toolbar)
        self.body.addWidget(table_card(self.tableWidget_rename), 1)
