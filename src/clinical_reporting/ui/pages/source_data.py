"""Source data: the Corelisting ZIP, the cut-off date, and saved settings."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QComboBox, QDateEdit, QWidget

from cci_ui.icons import IconName
from cci_ui.widgets.page import Page, PageKind
from cci_ui.widgets.path_picker import PathPicker
from cci_ui.widgets.section import Section
from cci_ui.widgets.status import StatusBanner
from cci_ui.widgets.toggle import ToggleSwitch


class SourceDataPage(Page):
    """Where every report starts."""

    KEY = "source"
    SECTION = "Data"
    ICON = IconName.SOURCE_DATA
    EXPORTS = (
        "pathPicker_input_file",
        "pushButton_input_file",
        "pushButton_remove_input",
        "banner_input_file",
        "cutoff_checkBox",
        "cutoff_dateEdit",
        "checkBox_saved_setting",
        "comboBox_saved_setting",
        "pathPicker_settings_folder",
        "pushButton_setting_location",
        "label_setting",
    )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            "Source data",
            "Load a Corelisting export to start a report.",
            kind=PageKind.FORM,
            parent=parent,
        )
        # Why the ZIP couldn't be read, when it couldn't.
        self.banner_input_file = StatusBanner()
        self.pathPicker_input_file = PathPicker(
            button_text="Choose ZIP…", placeholder="No ZIP chosen", removable=True
        )
        self.pushButton_input_file = self.pathPicker_input_file.button
        self.pushButton_remove_input = self.pathPicker_input_file.clear_button
        zip_section = Section("Corelisting ZIP")
        zip_section.add_row("File", self.pathPicker_input_file)

        self.cutoff_checkBox = ToggleSwitch()
        self.cutoff_checkBox.setAccessibleName("Apply cut-off date")
        self.cutoff_dateEdit = QDateEdit()
        self.cutoff_dateEdit.setCalendarPopup(True)
        self.cutoff_dateEdit.setFixedWidth(150)
        cutoff_section = Section(
            "Cut-off date",
            "Only rows on or before this date are loaded from the Corelisting ZIP.",
        )
        cutoff_section.add_row(
            "Apply cut-off date", self.cutoff_checkBox, label_width=None
        )
        cutoff_section.add_row("Cut-off", self.cutoff_dateEdit, end_aligned=True)

        self.checkBox_saved_setting = ToggleSwitch()
        self.checkBox_saved_setting.setAccessibleName("Start from a saved setting")
        self.comboBox_saved_setting = QComboBox()
        self.pathPicker_settings_folder = PathPicker(
            button_text="Settings folder…", placeholder="No folder chosen"
        )
        self.pushButton_setting_location = self.pathPicker_settings_folder.button
        saved_section = Section("Saved settings")
        saved_section.add_row(
            "Start from a saved setting", self.checkBox_saved_setting, label_width=None
        )
        saved_section.add_row("Setting", self.comboBox_saved_setting)
        saved_section.add_row("Folder", self.pathPicker_settings_folder)
        # Items of a loaded setting that the data doesn't have.
        self.label_setting = StatusBanner()

        for widget in (
            self.banner_input_file,
            zip_section,
            cutoff_section,
            saved_section,
            self.label_setting,
        ):
            self.body.addWidget(widget)
