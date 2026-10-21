"""Source data: the Corelisting ZIP, the cut-off date, and saved settings.

:class:`SourceDataMixin` holds the logic that works with files and folders
(input ZIP selection, saved setting folders, and saved setting management);
its slot methods are bound to the page's controls.

Reading the ZIP runs in the background (:func:`cci_ui.tasks.run_task`); the
data it returns is applied to the report in the callbacks, back on the GUI
thread.

Picking a saved setting also hands the names it saved for additional input
files to the Additional input page, which offers them in its Saved names
dropdowns ("Still to add" counts the files of the forms the setting selects
or stacks); when forms the setting needs are missing, the warning names the
files that bring them (or, for files already added, says to check and apply
them). Forgetting the loaded setting greys those dropdowns out again, back
to None: a new ZIP, removing the ZIP, turning the toggle off, picking
"Choose a setting…", or a setting that fails to load. A new ZIP, or removing
it, also tells the Stacked forms and Coalesced items pages to ask for Apply
again.

Picking a saved setting also fills in the export's file name and its Add the
date and time choice on Preview & export, from the ones saved with it
(:mod:`clinical_reporting.export_name`). A setting saved without a file name,
as every setting before 2.21 was, clears File name and ticks the box, so the
export waits for a name. Forgetting the setting leaves them as they are.
"""

from __future__ import annotations

import datetime
import logging
import os
import traceback
from functools import partial
from typing import Dict, Optional

import pandas as pd
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QComboBox, QDateEdit, QFileDialog, QWidget

from cci_ui.icons import IconName
from cci_ui.tasks import defer_if_busy, run_task
from cci_ui.widgets.page import Page, PageKind
from cci_ui.widgets.path_picker import PathPicker, downloads_folder
from cci_ui.widgets.section import Section
from cci_ui.widgets.status import StatusBanner
from cci_ui.widgets.toggle import ToggleSwitch
from clinical_reporting import export_name, feedback, steps
from clinical_reporting.additional_names import from_settings
from clinical_reporting.data import parse_study_name, read_data_dict_zip_corelisting
from clinical_reporting.session import (
    apply_saved_setting,
    new_report,
    replace_base_data,
    without_base_data,
)
from clinical_reporting.ui.dialogs import choose_settings_directory, settings_folder

from ._common import show_problem

logger = logging.getLogger(__name__)

#: The Setting box's problem when the setting picked couldn't be loaded.
SETTING_NOT_LOADED = "This setting couldn't be loaded; see the message below."


class SourceDataPage(Page):
    """Where every report starts."""

    KEY = steps.SOURCE
    SECTION = "Data"
    ICON = IconName.SOURCE_DATA
    EXPORTS = (
        "section_input_file",
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
            steps.TITLES[self.KEY],
            "Load a Corelisting export to start a report.",
            kind=PageKind.FORM,
            parent=parent,
        )
        # Why the ZIP couldn't be read, when it couldn't.
        self.banner_input_file = StatusBanner()
        self.pathPicker_input_file = PathPicker(
            button_text="Choose ZIP…",
            placeholder="No ZIP chosen",
            removable=True,
            remove_text="Remove file",
        )
        self.pushButton_input_file = self.pathPicker_input_file.button
        self.pushButton_remove_input = self.pathPicker_input_file.clear_button
        # Its footnote says what was read (forms, rows, when).
        self.section_input_file = Section("Corelisting ZIP")
        self.section_input_file.add_row("File", self.pathPicker_input_file)

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
        self.pathPicker_settings_folder = PathPicker(
            button_text="Settings folder…", placeholder="No folder chosen"
        )
        self.pushButton_setting_location = self.pathPicker_settings_folder.button
        self.comboBox_saved_setting = QComboBox()
        # Shown while the list is empty (the toggle is off); the list's own
        # first entry repeats it.
        self.comboBox_saved_setting.setPlaceholderText("Choose a setting…")
        saved_section = Section("Saved settings")
        saved_section.add_row(
            "Start from a saved setting", self.checkBox_saved_setting, label_width=None
        )
        saved_section.add_row("Folder", self.pathPicker_settings_folder)
        saved_section.add_row("Setting", self.comboBox_saved_setting)
        # Items of a loaded setting that the data doesn't have.
        self.label_setting = StatusBanner()

        for widget in (
            self.banner_input_file,
            self.section_input_file,
            cutoff_section,
            saved_section,
            self.label_setting,
        ):
            self.body.addWidget(widget)


class SourceDataMixin:
    """Behavior for the Source data page and saved-setting management."""

    def _init_source_data(self) -> None:
        """Wire up controls on the Source data page."""
        # Disable settings directory selector until persistence is enabled.
        self.ui.pushButton_setting_location.setEnabled(False)
        self.ui.pushButton_input_file.clicked.connect(self.click_input_file)
        self.ui.pushButton_remove_input.clicked.connect(self.click_remove_input)
        self.ui.pushButton_remove_input.setEnabled(bool(self._input_file_path))
        self.ui.pushButton_output_folder.clicked.connect(self.click_output_file)
        self.ui.checkBox_saved_setting.stateChanged.connect(
            self.click_checkBox_saved_setting
        )
        self.ui.comboBox_saved_setting.setEnabled(False)
        self.ui.comboBox_saved_setting.clear()
        self.ui.comboBox_saved_setting.currentIndexChanged.connect(
            self.on_saved_setting_changed
        )
        self.ui.pushButton_setting_location.clicked.connect(self.click_setting_location)

        # Cut-off date is disabled until the user opts in via the checkbox, and
        # defaults to today's date.
        self.ui.cutoff_checkBox.setChecked(False)
        self.ui.cutoff_dateEdit.setEnabled(False)
        self.ui.cutoff_dateEdit.setDate(QDate.currentDate())
        self.ui.cutoff_checkBox.stateChanged.connect(self.click_cutoff_checkBox)
        self.ui.cutoff_dateEdit.editingFinished.connect(
            self._reload_with_current_cut_off
        )
        # A date picked in the calendar popup commits nothing by itself.
        calendar = self.ui.cutoff_dateEdit.calendarWidget()
        if calendar is not None:
            calendar.clicked.connect(self._reload_with_current_cut_off)
            calendar.activated.connect(self._reload_with_current_cut_off)

    # ------------------------------------------------------------------
    # Slots bound to the Source data page's buttons

    def click_input_file(self) -> None:
        """Open a file dialog to choose the input Corelisting ZIP file."""
        if defer_if_busy(self, self.click_input_file):
            return
        default_dir = downloads_folder()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select the input Corelisting zip file",
            default_dir,
            "Zip files (*.zip);;All Files (*)",
        )
        if not file_path:
            return

        cut_off_date = self._get_cut_off_date()
        run_task(
            self,
            read_data_dict_zip_corelisting,
            file_path,
            cut_off_date=cut_off_date,
            on_success=partial(self.open_input_data, file_path, cut_off_date),
            on_error=partial(
                self._show_input_file_error,
                file_path,
                "Nothing was loaded; the report is unchanged.",
            ),
            message="Reading Corelisting ZIP…",
        )

    def open_input_data(
        self,
        file_path: str,
        cut_off_date: Optional[datetime.date],
        data: Dict[str, pd.DataFrame],
    ) -> None:
        """Start a new report from Corelisting *data* read from *file_path*.

        Called with what :meth:`click_input_file` read; previews call it with
        sample data. Changing the cut-off date later re-reads *file_path*.
        """
        # A new report, so nothing from a previous load lingers.
        self.study_name = parse_study_name(file_path)
        self.report = new_report(self.study_name, data)
        self._forget_loaded_setting()
        # Remember the source so the cut-off can be re-applied without re-picking.
        self._input_file_path = file_path
        self._applied_cut_off_date = cut_off_date
        self._failed_cut_off_reload = None
        # The new report has none of the applied additional or stacked forms,
        # nor the coalesced items.
        self._forget_applied_additional_forms()
        forget_stacked_forms = getattr(self, "_forget_applied_stacked_forms", None)
        if forget_stacked_forms is not None:
            forget_stacked_forms()
        forget_coalesced = getattr(self, "_forget_applied_coalesced_items", None)
        if forget_coalesced is not None:
            forget_coalesced()
        self._forget_export_results()
        self.ui.pushButton_remove_input.setEnabled(True)

        self.update_all_ui()
        # The additional files, stacked forms and coalesced items carry over.
        self.apply_data_steps()
        self._show_input_file()
        self._show_data_read(data)

        if self.ui.checkBox_saved_setting.isChecked():
            self.settings_directory = settings_folder(self)
            self._refresh_saved_settings()

    def click_remove_input(self) -> None:
        """Remove the selected Corelisting ZIP and its forms from the report.

        Additional inputs are independent of the Corelisting ZIP, so forms
        already applied from the Additional input page remain available. The
        stacked forms and coalesced items made only from the ZIP's forms go
        with it; with no additional files either, every one goes.
        """
        if defer_if_busy(self, self.click_remove_input):
            return
        if not self._input_file_path:
            return

        additional_keys = getattr(self, "_additional_form_keys", set())
        removed = set(self.report.loaded_data) - set(additional_keys)
        built_stacked = list(self.report.stacked_forms)
        self.report = without_base_data(self.report, additional_keys)
        self.study_name = None
        self._input_file_path = None
        self._applied_cut_off_date = None
        self._failed_cut_off_reload = None
        self._forget_loaded_setting()
        self._forget_export_results()
        # The fresh report has no stacked forms or coalesced items; those
        # still made from an additional file reach it again with the other
        # Data steps.
        forget_stacked_forms = getattr(self, "_forget_applied_stacked_forms", None)
        if forget_stacked_forms is not None:
            forget_stacked_forms()
        forget_coalesced = getattr(self, "_forget_applied_coalesced_items", None)
        if forget_coalesced is not None:
            forget_coalesced()
        self._drop_data_steps_without_input(removed, built_stacked)

        self._show_input_file()
        self._show_data_read(None)
        self.ui.pushButton_remove_input.setEnabled(False)

        # Saved settings are study-specific; repopulate them after another ZIP
        # establishes the study name.
        self.ui.comboBox_saved_setting.clear()
        self.ui.comboBox_saved_setting.setEnabled(False)

        self.update_all_ui()
        self.apply_data_steps()

    def click_output_file(self) -> None:
        """Allow the user to choose the output directory for reports."""
        initial_dir = self.output_folder_name or downloads_folder()
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            initial_dir,
        )
        if folder:
            self.output_folder_name = folder
            self.ui.pathPicker_output_folder.set_path(folder)
            # Guarded: tests compose this mixin without Preview & export's.
            refresh_run = getattr(self, "_refresh_run_availability", None)
            if refresh_run is not None:
                refresh_run()

    def click_cutoff_checkBox(self, state: int) -> None:
        """Enable the date editor and re-apply the cut-off when toggled."""
        self.ui.cutoff_dateEdit.setEnabled(bool(state))
        self._reload_with_current_cut_off()

    def _get_cut_off_date(self):
        """Return the selected cut-off date, or ``None`` when disabled.

        The cut-off date is only applied when :attr:`cutoff_checkBox` is
        checked; otherwise all data is loaded regardless of event date.
        """
        if not self.ui.cutoff_checkBox.isChecked():
            return None
        return self.ui.cutoff_dateEdit.date().toPython()

    def _reload_with_current_cut_off(self) -> None:
        """Re-read the input ZIP with the current cut-off date.

        The cut-off filters rows while the ZIP is read, so changing it (or
        toggling the checkbox) after a file is loaded requires re-reading the
        data. Existing form/item/common selections and any loaded additional
        inputs are preserved where they remain valid. This is a no-op when no
        input file is loaded yet or the effective cut-off has not changed.

        The date field commits whenever it loses focus, which can happen while
        other work runs (to another app, or to a dialog); the reload then
        waits until that work is done. A reload that failed isn't retried for
        the same file and date, so each focus change doesn't repeat the
        error; picking the ZIP again or another date tries again.
        """
        if defer_if_busy(self, self._reload_with_current_cut_off):
            return
        input_path = self._input_file_path
        if not input_path:
            return

        cut_off_date = self._get_cut_off_date()
        if cut_off_date == self._applied_cut_off_date:
            if self._failed_cut_off_reload is not None:
                # Back to the applied date: the earlier failure no longer matters.
                self._failed_cut_off_reload = None
                self._show_input_file()
            return
        if (input_path, cut_off_date) == self._failed_cut_off_reload:
            return

        run_task(
            self,
            read_data_dict_zip_corelisting,
            input_path,
            cut_off_date=cut_off_date,
            on_success=partial(self._apply_cut_off_data, input_path, cut_off_date),
            on_error=partial(self._show_cut_off_reload_error, input_path, cut_off_date),
            message="Applying the cut-off date…",
        )

    def _apply_cut_off_data(
        self,
        input_path: str,
        cut_off_date: Optional[datetime.date],
        base_data: Dict[str, pd.DataFrame],
    ) -> None:
        """Swap in the ZIP data re-read by :meth:`_reload_with_current_cut_off`."""
        if input_path != self._input_file_path:
            return  # The ZIP was removed or replaced meanwhile; this data is stale.
        replace_base_data(
            self.report, base_data, getattr(self, "_additional_form_keys", set())
        )
        self._applied_cut_off_date = cut_off_date
        self._failed_cut_off_reload = None
        self.update_all_ui()
        self._show_input_file()
        self._show_data_read(base_data)

    def _show_cut_off_reload_error(
        self,
        input_path: str,
        cut_off_date: Optional[datetime.date],
        exc: BaseException,
        details: str,
    ) -> None:
        """Say why the reload failed, and remember it so it isn't retried.

        See :meth:`_reload_with_current_cut_off`.
        """
        self._failed_cut_off_reload = (input_path, cut_off_date)
        self._show_input_file_error(
            input_path,
            "The cut-off date was not applied; the report still uses the data "
            "loaded before.",
            exc,
            details,
        )

    def _show_input_file_error(
        self, file_path: str, outcome: str, exc: BaseException, details: str
    ) -> None:
        """Say the ZIP couldn't be read, and what that means (*outcome*).

        The problem stays on the Source data page, with the traceback behind
        "Show details"; the status bar repeats it, as a toast if the user is
        on another page (see :mod:`ui.navigation`).
        """
        logger.error("Could not read %s", file_path, exc_info=exc)
        problem = feedback.error(
            f"Could not read {os.path.basename(file_path)}: {exc}\n{outcome}", details
        )
        self._show_input_file(problem)

    def _show_data_read(self, data: Optional[Dict[str, pd.DataFrame]]) -> None:
        """Under the ZIP: how many forms and rows were read, and when."""
        if data is None:
            summary = ""
        else:
            summary = steps.source_summary(data, datetime.datetime.now())
        self.ui.section_input_file.set_footnote(summary)

    def _show_input_file(self, problem: Optional[feedback.Message] = None) -> None:
        """Show the loaded ZIP on the Source data page, and *problem* if any."""
        self.ui.pathPicker_input_file.set_path(self._input_file_path)
        self._set_label_text(self.ui.banner_input_file, problem or "")

    def click_checkBox_saved_setting(self, state: int) -> None:
        """Enable or disable saved setting controls based on the checkbox."""
        enabled = bool(state)
        self.ui.comboBox_saved_setting.setEnabled(enabled)
        self.ui.pushButton_setting_location.setEnabled(enabled)
        if enabled:
            self.settings_directory = settings_folder(self)
            self._refresh_saved_settings()
        else:
            self.ui.comboBox_saved_setting.clear()
            self.ui.comboBox_saved_setting.setEnabled(False)
            self._forget_loaded_setting()

    def click_setting_location(self) -> None:
        """Let the user choose the directory that stores saved settings."""
        choose_settings_directory(self)

    # ------------------------------------------------------------------
    # Saved settings helpers

    def _refresh_saved_settings(self) -> None:
        """Populate the saved settings combo box for the current study."""
        combo = self.ui.comboBox_saved_setting
        combo.blockSignals(True)
        combo.clear()

        saved_settings = self._settings_store().list(self.study_name)
        for saved in saved_settings:
            combo.addItem(saved.name, saved.key)

        if saved_settings:
            combo.insertItem(0, combo.placeholderText(), None)
            combo.setEnabled(True)
        else:
            combo.addItem("No saved settings found for this study", None)
            combo.setEnabled(False)

        # Keep showing the setting that is loaded (the list is refreshed after
        # a save, and the setting stays loaded).
        loaded_path = getattr(self, "_last_loaded_setting_path", None)
        loaded = combo.findData(loaded_path) if loaded_path else -1
        combo.setCurrentIndex(max(loaded, 0))
        combo.blockSignals(False)

    def _forget_loaded_setting(self) -> None:
        """Forget the saved setting that was loaded, and its warning.

        The Additional input page stops offering its saved names; the names
        already filled in stay.
        """
        self._last_loaded_setting_path = None
        self._pending_saved_setting_reapply = False
        self._set_label_text(self.label_setting, "")
        show_problem(self.ui.comboBox_saved_setting, "")
        forget_saved_names = getattr(self, "_forget_saved_additional_names", None)
        if forget_saved_names is not None:
            forget_saved_names()

    def _update_saved_setting_warning(self, reconciliation: dict) -> None:
        """Update the warning label and reapply flag for missing setting data.

        When missing forms come from additional files whose names the setting
        saved, the warning also says which files to add, or, for files
        already added, to check their form names and apply them.
        """
        lines = steps.setting_missing_lines(reconciliation)
        self._pending_saved_setting_reapply = bool(lines)

        missing_forms = reconciliation.get("forms", [])
        if missing_forms:
            added = getattr(self, "_saved_names_added", None)
            hint = steps.saved_names_hint(
                missing_forms,
                getattr(self, "_saved_additional_names", ()),
                added() if added is not None else (),
            )
            if hint:
                lines.insert(1, hint)
        self._set_label_text(
            self.label_setting, feedback.warning("\n".join(lines)) if lines else ""
        )

    def _apply_saved_setting_from_path(
        self,
        file_path: str,
        *,
        update_confirmation: bool = True,
        offer_saved_names: bool = False,
    ) -> bool:
        """Load the saved setting at ``file_path`` and reconcile it with the data.

        With *offer_saved_names* (the user picked the setting), the names it
        saved for additional input files are handed to the Additional input
        page, and the export's file name it saved fills in Preview & export
        (a setting without one clears it). Re-applying the setting once the
        files reach the report leaves them, so the user's picks and edits
        stay.
        """
        try:
            stored = self._settings_store().load(file_path)
            reconciliation = apply_saved_setting(self.report, stored)
        except Exception as exc:
            logger.exception("Failed to load settings from %s", file_path)
            # Said under the Setting box (on_saved_setting_changed marks it).
            self._setting_load_error = feedback.error(
                f"Failed to load settings: {exc}", traceback.format_exc()
            )
            self._set_label_text(self.label_setting, self._setting_load_error)
            self._pending_saved_setting_reapply = False
            return False

        self.study_name = self.report.study_name

        offer = getattr(self, "_offer_saved_additional_names", None)
        if offer_saved_names and offer is not None:
            setting_name = (
                stored.get("setting_name")
                or os.path.splitext(os.path.basename(file_path))[0]
            )
            # Only forms the setting selects, or stacks, need their files added.
            used_forms = set(stored.get("selected_forms") or ())
            used_forms.update(
                member
                for stacked in self.report.stacked_forms
                for member in stacked.members
            )
            offer(from_settings(stored), setting_name, used_forms)

        fill = getattr(self, "_fill_saved_export_name", None)
        if offer_saved_names and fill is not None:
            fill(export_name.from_settings(stored))

        self.update_all_ui()
        self._update_saved_setting_warning(reconciliation)

        if update_confirmation:
            self._set_label_text(
                self.label_save_confirmation,
                feedback.success(f"Loaded settings from {os.path.basename(file_path)}"),
            )
        return True

    def on_saved_setting_changed(self, index: int) -> None:
        """Load the selected saved setting into the report.

        A setting that can't be loaded marks the Setting box, and the banner
        under it says why.
        """
        if index < 0:
            return
        show_problem(self.ui.comboBox_saved_setting, "")

        file_path: Optional[str] = self.ui.comboBox_saved_setting.itemData(index)
        if not file_path:
            self._forget_loaded_setting()
            return

        if not self._apply_saved_setting_from_path(
            file_path, update_confirmation=True, offer_saved_names=True
        ):
            self._forget_loaded_setting()
            self._set_label_text(self.label_setting, self._setting_load_error)
            show_problem(self.ui.comboBox_saved_setting, SETTING_NOT_LOADED)
            return

        self._last_loaded_setting_path = file_path
        # The saved names it filled in are used now, and the setting's
        # selections on those forms come back with them.
        self.apply_data_steps()

        setting_name = self.ui.comboBox_saved_setting.currentText()
        if setting_name:
            self.ui.lineEdit_setting_name.setText(setting_name)
