"""Additional input: extra CSV or Excel files, their form and column names."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout, QVBoxLayout, QWidget

from cci_ui.icons import IconName
from cci_ui.widgets.buttons import make_button
from cci_ui.widgets.labels import section_label
from cci_ui.widgets.page import Page
from cci_ui.widgets.status import StatusBanner
from cci_ui.widgets.tables import ColumnSpec, table_card
from cci_ui.widgets.views import PlaceholderListWidget
from clinical_reporting import steps

from ._common import make_table

_NAME_COLUMNS = (ColumnSpec("stretch"), ColumnSpec("stretch"))


class AdditionalInputPage(Page):
    """Optional files added to the report as extra forms."""

    KEY = steps.ADDITIONAL
    SECTION = "Data"
    ICON = IconName.ADDITIONAL_INPUT
    EXPORTS = (
        "pushButton_additional_file_add",
        "pushButton_additional_file_remove",
        "pushButton_apply_additional_files",
        "banner_additional",
        "listWidget_additional_file",
        "tableWidget_update_form_name",
        "tableWidget_update_column_name",
    )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            steps.TITLES[self.KEY],
            "Optional. Add CSV or Excel files, rename their forms and columns, "
            "then apply them to the report.",
            parent=parent,
        )
        self.pushButton_additional_file_add = make_button(
            "Add files…", icon_name=IconName.ADD
        )
        self.pushButton_additional_file_remove = make_button("Remove")
        self.pushButton_apply_additional_files = make_button(
            "Apply to report", variant="primary"
        )
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.addWidget(self.pushButton_additional_file_add)
        toolbar.addWidget(self.pushButton_additional_file_remove)
        toolbar.addStretch(1)
        toolbar.addWidget(self.pushButton_apply_additional_files)
        # What applying did, or why it couldn't.
        self.banner_additional = StatusBanner()

        self.listWidget_additional_file = PlaceholderListWidget(
            "No files added. Add CSV or Excel files to use them as extra forms."
        )
        self.listWidget_additional_file.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )

        self.tableWidget_update_form_name = make_table(
            ["Original name", "New name"],
            _NAME_COLUMNS,
            placeholder="Added files appear here.",
        )
        self.tableWidget_update_column_name = make_table(
            ["Original name", "New name"],
            _NAME_COLUMNS,
            placeholder="Select a file to rename its columns.",
            selection=QAbstractItemView.SelectionMode.ExtendedSelection,
        )
        names = QHBoxLayout()
        names.setSpacing(16)
        for title, table in (
            ("Form names", self.tableWidget_update_form_name),
            ("Column names", self.tableWidget_update_column_name),
        ):
            group = QVBoxLayout()
            group.setSpacing(6)
            group.addWidget(section_label(title))
            group.addWidget(table_card(table), 1)
            names.addLayout(group, 1)

        files_card = table_card(self.listWidget_additional_file)
        files_card.setMaximumHeight(140)

        self.body.addLayout(toolbar)
        self.body.addWidget(self.banner_additional)
        self.body.addWidget(files_card)
        self.body.addLayout(names, 1)
