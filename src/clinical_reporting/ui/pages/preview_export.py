"""Preview & export: the report's rows, and a panel to export or save them."""

from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QBoxLayout,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from cci_ui.icons import IconName
from cci_ui.theme.manager import repolish
from cci_ui.widgets.buttons import make_button
from cci_ui.widgets.labels import section_label, text_label
from cci_ui.widgets.page import Page, PageKind
from cci_ui.widgets.path_picker import PathPicker
from cci_ui.widgets.responsive import ResponsiveSplit
from cci_ui.widgets.status import StatusBanner
from cci_ui.widgets.tables import style_table, table_card
from cci_ui.widgets.toggle import ToggleSwitch
from cci_ui.widgets.views import PreviewTableView

_PANEL_PADDING = 14


def _field(label: str, widget: QWidget) -> QVBoxLayout:
    """A small label above *widget*, as in the panel's fields."""
    layout = QVBoxLayout()
    layout.setSpacing(4)
    layout.addWidget(text_label(label, style="callout", tone="secondary"))
    layout.addWidget(widget)
    return layout


def _panel_section(title: str) -> Tuple[QWidget, QVBoxLayout]:
    """One titled section of the panel, and the layout to fill it."""
    section = QWidget()
    layout = QVBoxLayout(section)
    layout.setContentsMargins(
        _PANEL_PADDING, _PANEL_PADDING, _PANEL_PADDING, _PANEL_PADDING
    )
    layout.setSpacing(10)
    layout.addWidget(section_label(title))
    return section, layout


def _wide(button: QWidget) -> QWidget:
    button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return button


class PreviewExportPage(Page):
    """The last step: check the rows, export them, save the setting for reuse."""

    KEY = "preview"
    SECTION = "Output"
    ICON = IconName.PREVIEW_EXPORT
    EXPORTS = (
        "pushButton_refresh_preview",
        "tableView_preview",
        "pathPicker_output_folder",
        "pushButton_output_folder",
        "lineEdit_file_name",
        "label_run_confirmation",
        "pushButton_run",
        "checkBox_save_current_setting",
        "lineEdit_setting_name",
        "pathPicker_output_setting_folder",
        "pushButton_output_setting",
        "label_save_confirmation",
        "pushButton_save_setting",
    )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            "Preview & export",
            "Check the rows, then export them to Excel.",
            kind=PageKind.SPLIT,
            parent=parent,
        )
        self.pushButton_refresh_preview = make_button(
            "Refresh", icon_name=IconName.REFRESH
        )
        self.add_action(self.pushButton_refresh_preview)

        self.tableView_preview = PreviewTableView(
            "The preview appears here when the report can run."
        )
        style_table(self.tableView_preview, row_numbers=True)

        self.split = ResponsiveSplit(
            table_card(self.tableView_preview), self._build_panel()
        )
        self.split.stackedChanged.connect(self._arrange_panel)
        self._arrange_panel(self.split.is_stacked())
        self.body.addWidget(self.split, 1)

    def _build_panel(self) -> QWidget:
        # Export
        self.pathPicker_output_folder = PathPicker(
            button_text="Choose…", placeholder="No folder chosen"
        )
        self.pushButton_output_folder = self.pathPicker_output_folder.button
        self.lineEdit_file_name = QLineEdit()
        self.lineEdit_file_name.setPlaceholderText("Optional, e.g. DEMO01 DSMB")
        self.label_run_confirmation = StatusBanner()
        self.pushButton_run = _wide(
            make_button("Export to Excel", variant="primary", icon_name=IconName.EXPORT)
        )
        self._export_section, export = _panel_section("Export")
        export.addLayout(_field("Folder", self.pathPicker_output_folder))
        name_field = _field("File name", self.lineEdit_file_name)
        name_field.addWidget(
            text_label(
                "A date and time are added: name YYMMDD_HHMMSS.xlsx",
                style="caption",
                wrap=True,
            )
        )
        export.addLayout(name_field)
        export.addWidget(self.label_run_confirmation)
        export.addWidget(self.pushButton_run)

        # Save setting
        self.checkBox_save_current_setting = ToggleSwitch()
        self.checkBox_save_current_setting.setAccessibleName(
            "Save these settings for reuse"
        )
        save_toggle = QHBoxLayout()
        save_toggle.addWidget(text_label("Save these settings for reuse", wrap=True), 1)
        save_toggle.addWidget(self.checkBox_save_current_setting)
        self.lineEdit_setting_name = QLineEdit()
        self.lineEdit_setting_name.setPlaceholderText("Setting name")
        self.pathPicker_output_setting_folder = PathPicker(
            button_text="Choose…", placeholder="No folder chosen"
        )
        self.pushButton_output_setting = self.pathPicker_output_setting_folder.button
        self.label_save_confirmation = StatusBanner()
        self.pushButton_save_setting = _wide(
            make_button("Save setting", icon_name=IconName.SAVE)
        )
        self._save_section, save = _panel_section("Save setting")
        save.addLayout(save_toggle)
        save.addLayout(_field("Name", self.lineEdit_setting_name))
        save.addLayout(_field("Folder", self.pathPicker_output_setting_folder))
        save.addWidget(self.label_save_confirmation)
        save.addWidget(self.pushButton_save_setting)

        self._separator = QFrame()
        self._sections = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        self._sections.setContentsMargins(0, 0, 0, 0)
        self._sections.setSpacing(0)
        top = Qt.AlignmentFlag.AlignTop
        self._sections.addWidget(self._export_section, 0, top)
        self._sections.addWidget(self._separator)
        self._sections.addWidget(self._save_section, 0, top)
        self._sections.addStretch(1)  # Beside the grid: spare height goes last.

        content = QWidget()
        content.setProperty("cciRole", "pageContent")
        content.setLayout(self._sections)
        scroll = QScrollArea()
        scroll.setProperty("cciRole", "page")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)

        panel = QFrame()
        panel.setProperty("cciRole", "card")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(1, 1, 1, 1)
        panel_layout.addWidget(scroll)
        return panel

    def _arrange_panel(self, stacked: bool) -> None:
        """Sections one above the other beside the grid, side by side below it."""
        self._sections.setDirection(
            QBoxLayout.Direction.LeftToRight
            if stacked
            else QBoxLayout.Direction.TopToBottom
        )
        # Below the grid the two sections share the width; beside it they
        # keep their own height and the trailing stretch takes the rest.
        share = 1 if stacked else 0
        self._sections.setStretchFactor(self._export_section, share)
        self._sections.setStretchFactor(self._save_section, share)
        self._sections.setStretch(self._sections.count() - 1, 1 - share)
        self._separator.setProperty(
            "cciRole", "separatorVertical" if stacked else "separator"
        )
        repolish(self._separator)
