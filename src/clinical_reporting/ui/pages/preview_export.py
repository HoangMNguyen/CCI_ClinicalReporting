"""Preview & export: the report's rows, and a panel to export or save them."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QWidget

from cci_ui.icons import IconName
from cci_ui.widgets.buttons import make_button
from cci_ui.widgets.labels import text_label
from cci_ui.widgets.page import Page, PageKind
from cci_ui.widgets.path_picker import PathPicker
from cci_ui.widgets.responsive import ResponsiveSplit
from cci_ui.widgets.side_panel import SidePanel, full_width, labeled_field
from cci_ui.widgets.status import StatusBanner
from cci_ui.widgets.tables import style_table, table_card
from cci_ui.widgets.toggle import ToggleSwitch
from cci_ui.widgets.views import PreviewTableView
from clinical_reporting import steps
from clinical_reporting.filenames import output_file_name

#: The line under the title until a preview shows its size there.
SUBTITLE = "Check the rows, then export them to Excel."


class PreviewExportPage(Page):
    """The last step: check the rows, export them, save the setting for reuse.

    The page keeps its own captions current: the preview's size under the
    title, and the export's file name under the name field. F5 refreshes,
    Ctrl+E exports, and Ctrl+S saves the setting.
    """

    KEY = steps.PREVIEW
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
            steps.TITLES[self.KEY], SUBTITLE, kind=PageKind.SPLIT, parent=parent
        )
        self.pushButton_refresh_preview = make_button(
            "Refresh", icon_name=IconName.REFRESH
        )
        self.add_action(self.pushButton_refresh_preview)

        self.tableView_preview = PreviewTableView(
            "The preview appears here when the report can run."
        )
        style_table(self.tableView_preview, row_numbers=True)
        self.tableView_preview.modelChanged.connect(self._show_preview_size)

        self.panel = self._build_panel()
        self.split = ResponsiveSplit(table_card(self.tableView_preview), self.panel)
        self.panel.follow(self.split)
        self.body.addWidget(self.split, 1)

        for keys, button, tooltip in (
            ("F5", self.pushButton_refresh_preview, "Build the preview again (F5)"),
            ("Ctrl+E", self.pushButton_run, "Export to Excel (Ctrl+E)"),
            ("Ctrl+S", self.pushButton_save_setting, "Save setting (Ctrl+S)"),
        ):
            button.setToolTip(tooltip)
            self.add_shortcut(keys, button.click)  # Not while it's disabled.

    def _build_panel(self) -> SidePanel:
        panel = SidePanel()

        # Export
        self.pathPicker_output_folder = PathPicker(
            button_text="Choose…", placeholder="No folder chosen"
        )
        self.pushButton_output_folder = self.pathPicker_output_folder.button
        self.lineEdit_file_name = QLineEdit()
        self.lineEdit_file_name.setPlaceholderText("Optional, e.g. DEMO01 DSMB")
        self.lineEdit_file_name.textChanged.connect(self._show_file_name)
        self.file_name_caption = text_label(style="caption", wrap=True)
        self.label_run_confirmation = StatusBanner()
        self.pushButton_run = full_width(
            make_button("Export to Excel", variant="primary", icon_name=IconName.EXPORT)
        )
        export = panel.add_section("Export")
        export.addLayout(labeled_field("Folder", self.pathPicker_output_folder))
        name_field = labeled_field("File name", self.lineEdit_file_name)
        name_field.addWidget(self.file_name_caption)
        export.addLayout(name_field)
        export.addWidget(self.label_run_confirmation)
        export.addWidget(self.pushButton_run)
        self._show_file_name()

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
        self.pushButton_save_setting = full_width(
            make_button("Save setting", icon_name=IconName.SAVE)
        )
        save = panel.add_section("Save setting")
        save.addLayout(save_toggle)
        save.addLayout(labeled_field("Name", self.lineEdit_setting_name))
        save.addLayout(labeled_field("Folder", self.pathPicker_output_setting_folder))
        save.addWidget(self.label_save_confirmation)
        save.addWidget(self.pushButton_save_setting)
        return panel

    def _show_preview_size(self) -> None:
        """Under the title: the preview's rows and columns, once it has some."""
        model = self.tableView_preview.model()
        rows = model.rowCount() if model is not None else 0
        self.set_subtitle(
            steps.preview_caption(rows, model.columnCount()) if rows else SUBTITLE
        )

    def _show_file_name(self) -> None:
        """Under the name field: the file the export would write now."""
        name = output_file_name(self.lineEdit_file_name.text())
        self.file_name_caption.setText(f"Saved as {name} (date and time of export)")

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().showEvent(event)
        self._show_file_name()  # The time in it moves on.
