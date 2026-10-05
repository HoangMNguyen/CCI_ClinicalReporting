"""Additional input page mixin for loading external files.

This mixin wires the buttons on the "Additional input" page to allow users
to load CSV/Excel files, manage the selected list, and rename forms/columns.
Reading the files runs in the background (:func:`cci_ui.tasks.run_task`).
The banner on the page says what applying did (the wording is in
:mod:`clinical_reporting.steps`), which files couldn't be read, and which
form names clash; after a new Corelisting ZIP it asks to apply the files
again.

A saved setting keeps the form and column names given to its additional
files (:mod:`clinical_reporting.additional_names`). The Form names table
has a Saved names dropdown for each file: greyed out with only None until a
loaded setting has such names, then listing them. Files that match an
entry, by file name or else by columns (and only when the match is
unambiguous), get it picked and their names filled in, both when the
setting is loaded and when files are added later; names the user typed are
never replaced by a pick, nor cleared by picking None. A second banner,
"Still to add", lists the setting's files that no listed file stands for
yet. Nothing is applied until "Apply to report".
"""

from __future__ import annotations

import os
from functools import partial
from pathlib import Path
from typing import Collection, Dict, List, Optional, Sequence, Set, Tuple

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QListWidgetItem,
    QTableWidgetItem,
)

from cci_ui.tasks import defer_if_busy, run_task
from clinical_reporting import feedback, steps
from clinical_reporting.additional_names import (
    FileNames,
    Match,
    SavedFileNames,
    current_names,
    match,
    names_from,
)
from clinical_reporting.data import (
    build_additional_data_map,
    named_columns,
    strip_subject_prefix,
    try_load_tabular_files,
)
from clinical_reporting.report import CLReport
from clinical_reporting.ui.pages.additional_input import SAVED_NAMES_COLUMN
from clinical_reporting.ui.table_actions import (
    add_copy_original_name_action,
    copy_original_names_to_new_names,
)


class _SavedNamesComboBox(QComboBox):
    """A Saved names dropdown that ignores the wheel unless it has focus.

    Scrolling the table over it must not pick another entry, which would
    replace the file's names.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class AdditionalInputTabMixin:
    """Behavior for the Additional input page."""

    def _init_additional_input_tab(self) -> None:
        """Attach handlers and prepare state for the Additional input page."""
        self.additional_inputs: Dict[str, pd.DataFrame] = {}
        self.additional_form_names: Dict[str, str] = {}
        self.additional_column_names: Dict[Tuple[str, str], str] = {}
        self._additional_form_keys: Set[str] = set()
        self._additional_input_signature: Dict[str, Tuple[str, ...]] = {}
        self._populating_additional_tables = False
        # The loaded setting's saved names and each file's pick among them
        # (the dropdowns are rebuilt with the table, so the picks live here).
        self._saved_additional_names: List[SavedFileNames] = []
        self._saved_names_choice: Dict[str, Match] = {}
        self._saved_names_setting = ""
        # The forms the loaded setting selects (None: count every saved form).
        self._saved_names_forms: Optional[Set[str]] = None
        self._saved_names_message: Optional[feedback.Message] = None

        add_button = getattr(self.ui, "pushButton_additional_file_add", None)
        remove_button = getattr(self.ui, "pushButton_additional_file_remove", None)
        apply_button = getattr(self.ui, "pushButton_apply_additional_files", None)

        if add_button is not None:
            add_button.clicked.connect(self.click_add_additional_files)
        if remove_button is not None:
            remove_button.clicked.connect(self.click_remove_additional_files)
        if apply_button is not None:
            apply_button.clicked.connect(self.click_apply_additional_forms)

        if hasattr(self.ui, "listWidget_additional_file"):
            self.ui.listWidget_additional_file.itemSelectionChanged.connect(
                self._update_additional_buttons_state
            )

        form_table = getattr(self.ui, "tableWidget_update_form_name", None)
        column_table = getattr(self.ui, "tableWidget_update_column_name", None)
        if form_table is not None:
            form_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            form_table.setSelectionMode(QAbstractItemView.SingleSelection)
            form_table.itemChanged.connect(self._on_form_name_changed)
            form_table.itemSelectionChanged.connect(
                self._on_form_table_selection_changed
            )
        if column_table is not None:
            column_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            column_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
            self.copy_new_column_name_action = add_copy_original_name_action(
                column_table, self.copy_selected_new_column_names_to_updated
            )
            column_table.itemChanged.connect(self._on_column_name_changed)

        self._refresh_additional_files_ui()
        self._refresh_additional_tables()
        self._update_additional_buttons_state()

    # ------------------------------------------------------------------
    # Slots bound to additional input controls

    def click_add_additional_files(self) -> None:
        """Open a dialog and load user-selected additional input files."""
        if defer_if_busy(self, self.click_add_additional_files):
            return
        initial_dir = getattr(
            self, "_additional_input_directory", None
        ) or os.path.join(os.path.expanduser("~"), "Downloads")
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Additional Input Files",
            initial_dir,
            "Data Files (*.csv *.xls *.xlsx);;All Files (*)",
        )
        if not file_paths:
            return

        self._additional_input_directory = str(
            Path(file_paths[0]).expanduser().resolve().parent
        )

        new_paths = []
        for file_path in file_paths:
            resolved_path = str(Path(file_path).expanduser().resolve())
            if (
                resolved_path not in self.additional_inputs
                and resolved_path not in new_paths
            ):
                new_paths.append(resolved_path)
        if not new_paths:
            return

        run_task(
            self,
            try_load_tabular_files,
            new_paths,
            on_success=self._add_loaded_additional_files,
            message="Reading additional files…",
        )

    def _add_loaded_additional_files(
        self, result: Tuple[Dict[str, pd.DataFrame], Dict[str, str]]
    ) -> None:
        """List the files read by :meth:`click_add_additional_files`."""
        loaded, failures = result
        self.additional_inputs.update(loaded)
        picked = self._pick_saved_names(list(loaded))
        self._refresh_additional_files_ui()
        self._refresh_additional_tables()
        self._update_additional_buttons_state()
        banner = self.ui.banner_additional
        if failures:
            names = [Path(path).name for path in failures]
            reasons = [f"{Path(path).name}: {why}" for path, why in failures.items()]
            # One line on the page (it doesn't scroll); the reasons per file
            # are behind "Show details".
            problem = feedback.warning(
                f"These files could not be read and were not added: "
                f"{feedback.short_list(names)}.",
                "\n".join(reasons),
            )
            self._set_label_text(banner, problem)
        elif picked is not None:
            self._show_saved_names_message(picked)
        elif banner.text() and banner.kind() == "warning":
            # What went wrong before (unreadable files, nothing to apply, a
            # name clash) is old news; a result or the "apply again" hint isn't.
            self._set_label_text(banner, "")

    def click_remove_additional_files(self) -> None:
        """Remove selected additional input files from the list."""
        widget = getattr(self.ui, "listWidget_additional_file", None)
        if widget is None:
            return

        selected_items = widget.selectedItems()
        if not selected_items:
            return

        removed_paths = []
        choices = getattr(self, "_saved_names_choice", {})
        for item in selected_items:
            file_path = item.data(Qt.UserRole) or item.text()
            self.additional_inputs.pop(file_path, None)
            self.additional_form_names.pop(file_path, None)
            choices.pop(file_path, None)
            removed_paths.append(file_path)
            widget.takeItem(widget.row(item))

        if removed_paths:
            # Drop any column rename entries tied to removed files.
            self.additional_column_names = {
                key: val
                for key, val in self.additional_column_names.items()
                if key[0] not in removed_paths
            }

        self._refresh_additional_tables()
        self._update_additional_buttons_state()

    # ------------------------------------------------------------------
    # UI helpers

    def _refresh_additional_files_ui(self) -> None:
        """Populate the additional file list widget with current selections."""
        widget = getattr(self.ui, "listWidget_additional_file", None)
        if widget is None:
            return

        widget.clear()
        for file_path in sorted(self.additional_inputs):
            display_name = Path(file_path).name
            item = QListWidgetItem(display_name)
            item.setToolTip(file_path)
            item.setData(Qt.UserRole, file_path)
            widget.addItem(item)

    def _refresh_additional_tables(self) -> None:
        """Refresh the form/column rename tables and the "Still to add" banner."""
        self._populating_additional_tables = True
        try:
            self._populate_form_name_table()
            self._ensure_form_selection()
            self._populate_column_name_table()
        finally:
            self._populating_additional_tables = False
        self._show_missing_saved_files()

    def _populate_form_name_table(self) -> None:
        """Populate tableWidget_update_form_name with file names and editable form names."""
        table = getattr(self.ui, "tableWidget_update_form_name", None)
        if table is None:
            return

        table.blockSignals(True)
        paths = sorted(self.additional_inputs, key=lambda p: Path(p).name)
        table.setRowCount(len(paths))
        for row, file_path in enumerate(paths):
            file_name = Path(file_path).name
            item_name = QTableWidgetItem(file_name)
            item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable)
            item_name.setData(Qt.UserRole, file_path)
            table.setItem(row, 0, item_name)

            updated_name = self.additional_form_names.get(file_path, "")
            item_updated = QTableWidgetItem(updated_name)
            item_updated.setData(Qt.UserRole, file_path)
            table.setItem(row, 1, item_updated)
        self._fill_saved_names_column(table, paths)
        table.blockSignals(False)

    def _populate_column_name_table(self) -> None:
        """Populate tableWidget_update_column_name with column headers for selected files."""
        table = getattr(self.ui, "tableWidget_update_column_name", None)
        if table is None:
            return

        table.blockSignals(True)
        rows = []
        for file_path in self._selected_form_paths():
            df = self.additional_inputs.get(file_path)
            if df is None:
                continue
            rows.extend((file_path, column) for column in named_columns(df))

        table.setRowCount(len(rows))
        for row_index, (file_path, column_name) in enumerate(rows):
            new_column_display = column_name
            item_new_column = QTableWidgetItem(new_column_display)
            item_new_column.setFlags(item_new_column.flags() & ~Qt.ItemIsEditable)
            item_new_column.setData(Qt.UserRole, (file_path, column_name))
            table.setItem(row_index, 0, item_new_column)

            updated_column_name = self.additional_column_names.get(
                (file_path, column_name), ""
            )
            item_updated = QTableWidgetItem(updated_column_name)
            item_updated.setData(Qt.UserRole, (file_path, column_name))
            table.setItem(row_index, 1, item_updated)
        table.blockSignals(False)

    def _update_additional_buttons_state(self) -> None:
        """Enable or disable the remove button based on selection state."""
        widget = getattr(self.ui, "listWidget_additional_file", None)
        remove_button = getattr(self.ui, "pushButton_additional_file_remove", None)
        if widget is None or remove_button is None:
            return

        remove_button.setEnabled(bool(widget.selectedItems()))

    def _ensure_form_selection(self) -> None:
        """Ensure at least one row is selected to drive the column table."""
        table = getattr(self.ui, "tableWidget_update_form_name", None)
        if table is None or table.rowCount() == 0:
            return
        if not table.selectedItems():
            table.selectRow(0)

    def _selected_form_paths(self) -> list[str]:
        """Return the file paths for currently selected form rows."""
        table = getattr(self.ui, "tableWidget_update_form_name", None)
        if table is None or table.selectionModel() is None:
            return []
        rows = {index.row() for index in table.selectionModel().selectedRows()}
        paths = []
        for row in rows:
            item = table.item(row, 0)
            if item is None:
                continue
            file_path = item.data(Qt.UserRole)
            if file_path:
                paths.append(file_path)
        return paths

    # ------------------------------------------------------------------
    # Signal handlers for table edits

    def _on_form_name_changed(self, item: QTableWidgetItem) -> None:
        """Persist changes to the updated form name and refresh dependent UI."""
        if self._populating_additional_tables or item.column() != 1:
            return

        file_path = item.data(Qt.UserRole)
        if not file_path:
            return

        new_name = item.text().strip()
        if new_name:
            self.additional_form_names[file_path] = new_name
        else:
            self.additional_form_names.pop(file_path, None)

        self._populate_column_name_table()

    def _on_form_table_selection_changed(self) -> None:
        """Refresh the column table when the selected form changes."""
        if self._populating_additional_tables:
            return
        self._populate_column_name_table()

    def _on_column_name_changed(self, item: QTableWidgetItem) -> None:
        """Persist changes to the updated column name."""
        if self._populating_additional_tables or item.column() != 1:
            return

        key = item.data(Qt.UserRole)
        if not key:
            return

        new_name = item.text().strip()
        if new_name:
            self.additional_column_names[key] = new_name
        else:
            self.additional_column_names.pop(key, None)

    def copy_selected_new_column_names_to_updated(self) -> None:
        """Copy selected new-column values into their updated-name cells."""

        def persist(original_item, updated_name_item) -> None:
            key = updated_name_item.data(Qt.UserRole)
            if key:
                self.additional_column_names[key] = original_item.text()

        copy_original_names_to_new_names(
            getattr(self.ui, "tableWidget_update_column_name", None), persist
        )

    def click_apply_additional_forms(self) -> None:
        """Apply the additional inputs to the report when requested."""
        self._apply_additional_inputs_to_report()

    # ------------------------------------------------------------------
    # Saved names from a loaded setting

    def _saved_names(self) -> List[SavedFileNames]:
        """The loaded setting's saved names (none when no setting has any)."""
        return getattr(self, "_saved_additional_names", None) or []

    def _fill_saved_names_column(self, table, paths: Sequence[str]) -> None:
        """Give each row a Saved names dropdown (greyed out without saved names).

        Called while the Form names table is rebuilt (its signals blocked).
        Rows are reused, so every row gets a new dropdown for its own file.
        """
        if table.columnCount() <= SAVED_NAMES_COLUMN:
            return
        entries = self._saved_names()
        for row, file_path in enumerate(paths):
            # Qt deletes a replaced dropdown later; hide it now so it isn't
            # left drawn over the table until then.
            old = table.cellWidget(row, SAVED_NAMES_COLUMN)
            if old is not None:
                old.hide()
            # Under the dropdown, so the cell can't open a text editor (a
            # greyed-out dropdown lets double-clicks through to the table).
            cell = QTableWidgetItem("")
            cell.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            table.setItem(row, SAVED_NAMES_COLUMN, cell)
            table.setCellWidget(
                row, SAVED_NAMES_COLUMN, self._saved_names_combo(file_path, entries)
            )

    def _saved_names_added(self) -> List[SavedFileNames]:
        """The saved entries a listed file stands for.

        A listed file stands for an entry when it has the entry picked, or
        has the entry's file name.
        """
        if not hasattr(self, "additional_inputs"):
            return []
        picked = {
            pick.index for pick in getattr(self, "_saved_names_choice", {}).values()
        }
        listed = {Path(path).name.casefold() for path in self.additional_inputs}
        return [
            entry
            for index, entry in enumerate(self._saved_names())
            if index in picked or entry.file_name.casefold() in listed
        ]

    def _show_missing_saved_files(self) -> None:
        """List the loaded setting's files that aren't added yet.

        Only entries for forms the setting selects count: names saved for a
        file the setting doesn't use aren't missing.
        """
        banner = getattr(self.ui, "banner_saved_names", None)
        if banner is None:
            return
        used_forms = getattr(self, "_saved_names_forms", None)
        added = self._saved_names_added()
        missing = [
            entry
            for entry in self._saved_names()
            if entry.form_name
            and (used_forms is None or entry.form_name in used_forms)
            and entry not in added
        ]
        setting_name = getattr(self, "_saved_names_setting", "")
        self._set_label_text(
            banner,
            steps.saved_names_missing_message(setting_name, missing) if missing else "",
        )

    def _saved_names_combo(
        self, file_path: str, entries: Sequence[SavedFileNames]
    ) -> QComboBox:
        """The Saved names dropdown for *file_path*, showing its pick.

        Greyed out, with only None, when there are no *entries*.
        """
        combo = _SavedNamesComboBox()
        combo.addItem(steps.SAVED_NAMES_NONE)
        for entry in entries:
            combo.addItem(steps.saved_names_label(entry))
        combo.setEnabled(bool(entries))
        # The list may be wider than the cell, so long entries read in full.
        view = combo.view()
        view.setMinimumWidth(view.sizeHintForColumn(0) + 24)
        choice = self._saved_names_choice.get(file_path)
        combo.setCurrentIndex(0 if choice is None else choice.index + 1)
        combo.setToolTip(self._saved_names_tip(file_path))
        combo.setAccessibleName(f"Saved names for {Path(file_path).name}")
        # Bound to the file, not the row. activated fires only when the user
        # picks, and also when they pick the entry already shown.
        combo.activated.connect(partial(self._on_saved_names_activated, file_path))
        return combo

    def _saved_names_tip(self, file_path: str) -> str:
        """The tooltip of *file_path*'s dropdown: its pick, and why."""
        if not self._saved_names():
            return steps.SAVED_NAMES_UNAVAILABLE_TIP
        choice = self._saved_names_choice.get(file_path)
        if choice is None:
            return steps.saved_names_tip()
        return steps.saved_names_tip(self._saved_names()[choice.index], choice.by)

    def _current_names(self, file_path: str) -> Tuple[str, Dict[str, str]]:
        """The form name and column names *file_path* has now."""
        return current_names(
            file_path, self.additional_form_names, self.additional_column_names
        )

    def _names_from_entry(self, file_path: str, index: int) -> FileNames:
        """The names saved entry *index* gives *file_path*."""
        df = self.additional_inputs.get(file_path)
        columns = named_columns(df) if df is not None else []
        return names_from(self._saved_names()[index], columns)

    def _has_names_from(self, file_path: str, index: int) -> bool:
        """Whether *file_path*'s names are exactly what entry *index* gives."""
        names = self._names_from_entry(file_path, index)
        return self._current_names(file_path) == (names.form_name, names.column_names)

    def _use_saved_names(self, file_path: str, index: Optional[int]) -> List[str]:
        """Give *file_path* the names of saved entry *index*, or none.

        Replaces the file's form and column names (``None`` clears them).
        Returns the entry's renamed columns that the file doesn't have.
        """
        self.additional_form_names.pop(file_path, None)
        self.additional_column_names = {
            key: value
            for key, value in self.additional_column_names.items()
            if key[0] != file_path
        }
        if index is None:
            return []
        names = self._names_from_entry(file_path, index)
        if names.form_name:
            self.additional_form_names[file_path] = names.form_name
        for column, new_name in names.column_names.items():
            self.additional_column_names[(file_path, column)] = new_name
        return names.unmatched

    def _fill_saved_names(
        self, found: Dict[str, Match], paths: Collection[str]
    ) -> Optional[feedback.Message]:
        """Fill in the names *found* for *paths*, and say what was picked.

        ``None`` when none of *paths* has a match.
        """
        picks, unmatched = [], {}
        for file_path in sorted(paths, key=lambda path: Path(path).name.casefold()):
            if file_path not in found:
                continue
            missing = self._use_saved_names(file_path, found[file_path].index)
            self._saved_names_choice[file_path] = found[file_path]
            file_name = Path(file_path).name
            picks.append((file_name, found[file_path].by))
            if missing:
                unmatched[file_name] = missing
        if not picks:
            return None
        return steps.saved_names_filled_message(
            self._saved_names_setting, picks, unmatched
        )

    def _listed_columns(self) -> Dict[str, List[str]]:
        """Each listed file's column headers, for matching."""
        return {path: named_columns(df) for path, df in self.additional_inputs.items()}

    def _pick_saved_names(self, new_paths: Sequence[str]) -> Optional[feedback.Message]:
        """Pick saved names for files just added, and say what was picked.

        Only added files without names are filled in, and only with entries
        no listed file uses yet. ``None`` when nothing was picked.
        """
        if not self._saved_names():
            return None
        taken = {path: pick.index for path, pick in self._saved_names_choice.items()}
        found = match(self._saved_names(), self._listed_columns(), taken)
        unnamed = [path for path in new_paths if self._current_names(path) == ("", {})]
        return self._fill_saved_names(found, unnamed)

    def _offer_saved_additional_names(
        self,
        entries: Sequence[SavedFileNames],
        setting_name: str,
        used_forms: Optional[Collection[str]] = None,
    ) -> None:
        """Offer a loaded setting's saved names (*entries*) on this page.

        The Saved names dropdowns offer them while there are any. Listed
        files that match an entry get it picked and their names filled in,
        unless that would replace names the user typed: a file is filled in
        when it has no names, when its names are still what the previous
        setting's pick gave it, or when they already equal what the new pick
        gives.

        *used_forms* are the forms the setting selects: the "Still to add"
        banner lists only the files for those (``None``: every saved form).

        The Source data page calls this when the user picks a saved setting,
        not when it re-applies the setting after "Apply to report", so the
        picks made in between stay.
        """
        if not hasattr(self, "additional_form_names"):
            return  # A partial window (in tests) without this page's state.
        old_choices = dict(getattr(self, "_saved_names_choice", {}))
        replaceable = {
            path
            for path in self.additional_inputs
            if self._current_names(path) == ("", {})
            or (
                path in old_choices
                and self._has_names_from(path, old_choices[path].index)
            )
        }
        self._saved_additional_names = list(entries)
        self._saved_names_choice = {}
        self._saved_names_setting = setting_name
        self._saved_names_forms = None if used_forms is None else set(used_forms)
        message = None
        if entries and self.additional_inputs:
            found = match(entries, self._listed_columns())
            eligible = [
                path
                for path, pick in found.items()
                if path in replaceable or self._has_names_from(path, pick.index)
            ]
            message = self._fill_saved_names(found, eligible)
        # The "Still to add" banner says what isn't picked or added.
        self._refresh_additional_tables()
        if message is not None:
            self._show_saved_names_message(message)
        else:
            self._clear_saved_names_message()

    def _forget_saved_additional_names(self) -> None:
        """Stop offering saved names: the dropdowns go back to None, greyed out.

        The names already filled in stay; they are the user's now.
        """
        if not self._saved_names():
            return
        self._saved_additional_names = []
        self._saved_names_choice = {}
        self._saved_names_setting = ""
        self._saved_names_forms = None
        self._clear_saved_names_message()
        self._refresh_additional_tables()

    def _show_saved_names_message(self, message: feedback.Message) -> None:
        """Say *message* in the banner, remembered so it can go with the names."""
        self._saved_names_message = message
        self._set_label_text(self.ui.banner_additional, message)

    def _clear_saved_names_message(self) -> None:
        """Clear the banner if it still says something about saved names."""
        shown = getattr(self, "_saved_names_message", None)
        banner = self.ui.banner_additional
        if shown is not None and banner.text() == shown:
            self._set_label_text(banner, "")
        self._saved_names_message = None

    def _on_saved_names_activated(self, file_path: str, combo_index: int) -> None:
        """Use the entry picked in *file_path*'s dropdown (the first: none).

        Picking an entry gives the file its names. Picking None clears only
        names a pick gave and the user didn't change since; names they typed
        stay.
        """
        index = combo_index - 1 if combo_index > 0 else None
        if index is not None and index >= len(self._saved_names()):
            return  # A dropdown left from saved names that are gone.
        previous = self._saved_names_choice.get(file_path)
        file_name = Path(file_path).name
        if index is not None:
            unmatched = self._use_saved_names(file_path, index)
            self._saved_names_choice[file_path] = Match(index)
            entry = self._saved_names()[index]
            message = steps.saved_names_picked_message(entry, file_name, unmatched)
        elif previous is None:
            return  # None again: nothing was picked, the names are the user's.
        else:
            del self._saved_names_choice[file_path]
            if self._has_names_from(file_path, previous.index):
                self._use_saved_names(file_path, None)
                message = steps.saved_names_cleared_message(file_name)
            else:
                message = steps.saved_names_kept_message(file_name)

        # Update the row in place: rebuilding the table would delete the
        # dropdown that is emitting this signal.
        table = self.ui.tableWidget_update_form_name
        row = self._form_table_row(file_path)
        if row >= 0:
            self._populating_additional_tables = True
            try:
                new_name = self.additional_form_names.get(file_path, "")
                table.item(row, 1).setText(new_name)
            finally:
                self._populating_additional_tables = False
            combo = table.cellWidget(row, SAVED_NAMES_COLUMN)
            if combo is not None:
                combo.setToolTip(self._saved_names_tip(file_path))
            table.selectRow(row)
        # Selecting a row that was already selected refreshes nothing.
        self._populate_column_name_table()
        self._show_missing_saved_files()
        self._show_saved_names_message(message)

    def _form_table_row(self, file_path: str) -> int:
        """The Form names row showing *file_path*, or -1."""
        table = self.ui.tableWidget_update_form_name
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item is not None and item.data(Qt.UserRole) == file_path:
                return row
        return -1

    # ------------------------------------------------------------------
    # Report integration

    def _forget_applied_additional_forms(self) -> None:
        """Note that the report no longer has the applied additional forms.

        (A new Corelisting ZIP starts a new report.) The files stay listed;
        the banner says to apply them again.
        """
        if self._additional_form_keys:
            self._set_label_text(
                self.ui.banner_additional, steps.APPLY_ADDITIONAL_AGAIN
            )
        self._additional_form_keys = set()
        self._additional_input_signature = {}

    def _build_additional_data_map(self) -> Dict[str, pd.DataFrame]:
        """Construct a dict of form_name -> dataframe with applied renames.

        Delegates to :func:`clinical_reporting.data.build_additional_data_map`
        so the same shaping logic is reusable headlessly.
        """
        return build_additional_data_map(
            self.additional_inputs,
            self.additional_form_names,
            self.additional_column_names,
        )

    @staticmethod
    def _build_additional_input_signature(
        data_map: Dict[str, pd.DataFrame],
    ) -> Dict[str, Tuple[str, ...]]:
        """Summarize additional inputs by form name and column names."""
        signature: Dict[str, Tuple[str, ...]] = {}
        for form_name, df in data_map.items():
            signature[form_name] = tuple(str(column) for column in df.columns)
        return signature

    def _collect_additional_form_names(self) -> Dict[str, str]:
        """Return a mapping of file path -> form name for additional inputs."""
        form_names = {}
        for file_path in self.additional_inputs:
            form_name = (
                self.additional_form_names.get(file_path) or Path(file_path).name
            )
            form_names[file_path] = form_name
        return form_names

    def _warn_on_additional_form_conflicts(self, existing_forms: Set[str]) -> bool:
        """Say (in the banner) if additional forms' names clash; True if they do."""
        name_map = self._collect_additional_form_names()
        if not name_map:
            return False

        dotted_names = sorted({name for name in name_map.values() if "." in name})
        name_to_paths: Dict[str, list[str]] = {}
        for file_path, form_name in name_map.items():
            name_to_paths.setdefault(form_name, []).append(file_path)

        duplicates = {
            form_name: paths
            for form_name, paths in name_to_paths.items()
            if len(paths) > 1
        }
        conflicts = {
            form_name: paths
            for form_name, paths in name_to_paths.items()
            if form_name in existing_forms
        }

        if not dotted_names and not duplicates and not conflicts:
            return False

        clashing = sorted(set(dotted_names) | set(duplicates) | set(conflicts))
        message_parts = [
            "Cannot add forms because some form names are invalid or conflict "
            "with existing data."
        ]
        if dotted_names:
            message_parts.append("Form names cannot include '.':")
            message_parts.append("  - " + ", ".join(dotted_names))
        if duplicates:
            message_parts.append("Duplicate names in additional forms:")
            for form_name in sorted(duplicates):
                file_list = ", ".join(
                    sorted(Path(path).name for path in duplicates[form_name])
                )
                message_parts.append(f"  - {form_name}: {file_list}")
        if conflicts:
            message_parts.append("Conflicts with existing report forms:")
            for form_name in sorted(conflicts):
                file_list = ", ".join(
                    sorted(Path(path).name for path in conflicts[form_name])
                )
                message_parts.append(f"  - {form_name}: {file_list}")

        # One line on the page (it doesn't scroll); the reasons per file are
        # behind "Show details".
        conflict = feedback.warning(
            f"These form names can't be used: {feedback.short_list(clashing)}. "
            "Rename them in the table and try again.",
            "\n".join(message_parts),
        )
        self._set_label_text(self.ui.banner_additional, conflict)
        return True

    def _apply_additional_inputs_to_report(self) -> None:
        """Merge additional inputs into the current report and refresh UI."""
        # Ensure a report object exists.
        if not hasattr(self, "report") or self.report is None:
            self.report = CLReport()

        previous_signature = dict(getattr(self, "_additional_input_signature", {}))

        # Capture current selections (forms/items/common/join) to restore after
        # ``set_data`` rebuilds fresh CLForm objects with defaults.
        selection_state = self._capture_selection_state()

        base_data = dict(getattr(self.report, "data", {}) or {})
        # Remove previously injected additional forms.
        for form_key in getattr(self, "_additional_form_keys", set()):
            base_data.pop(form_key, None)

        if self._warn_on_additional_form_conflicts(set(base_data)):
            return

        additional_data = self._build_additional_data_map()
        if not additional_data and not self._additional_form_keys:
            self._set_label_text(
                self.ui.banner_additional,
                steps.ADD_FILES_FIRST,
            )
            return
        new_signature = self._build_additional_input_signature(additional_data)
        signature_changed = new_signature != previous_signature

        combined_data = {**base_data, **additional_data}

        self.report.set_data(combined_data)
        self._additional_form_keys = set(additional_data.keys())
        self._additional_input_signature = new_signature
        self._set_label_text(
            self.ui.banner_additional,
            steps.additional_applied_message(additional_data),
        )

        if (
            signature_changed
            and new_signature
            and getattr(self, "_pending_saved_setting_reapply", False)
            and getattr(self, "_last_loaded_setting_path", None)
        ):
            if self._apply_saved_setting_from_path(
                self._last_loaded_setting_path,
                update_confirmation=False,
            ):
                return

        # Restore the selections that survive in the rebuilt report.
        self._restore_selection_state(selection_state)

        self.update_all_ui()

    @staticmethod
    def _strip_prefix(value):
        """Remove leading 'UPCC' or '100-' (with optional separators) from a subject string.

        Thin wrapper over
        :func:`clinical_reporting.data.strip_subject_prefix`.
        """
        return strip_subject_prefix(value)
