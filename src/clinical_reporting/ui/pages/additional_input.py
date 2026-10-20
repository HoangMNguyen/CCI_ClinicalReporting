"""Additional input: additional CSV or Excel files, their form and column names.

:class:`AdditionalInputMixin` wires the page's buttons to load CSV/Excel
files, manage the selected list, and rename forms/columns. Reading the files
runs in the background (:func:`cci_ui.tasks.run_task`). The files, with
their names, reach the report when the user goes to another step
(:meth:`~AdditionalInputMixin._apply_additional_step`, called by the window's
``apply_data_steps``); files that finish loading after the user left, and
names a picked setting fills in, reach it right away. So do they, without
leaving, once every file the loaded setting needs is listed and no New name
is red: the change that makes it so (files added, a Saved names pick, a name
typed, a file removed) brings them in; later ones wait for the user to
leave. A New name the report can't use (none typed, a ".", a loaded or
stacked form's name, another file's) is marked red with the reason, and
holds the step: nothing from it reaches the report until it is fixed. The
banner on the page says what reaching the report did (the wording is in
:mod:`clinical_reporting.steps`) and which files couldn't be read. Applying
starts from the report's forms as loaded (``CLReport.loaded_data``), so the
report rebuilds its stacked forms from the new set; a new Corelisting ZIP
brings the files' forms along.

A saved setting keeps the form and column names given to its additional
files (:mod:`clinical_reporting.additional_names`). The Form names table's
third column, Saved names, has a dropdown for each file: greyed out with
only None until a loaded setting has such names, then listing them by form
name, or by file name for an entry that only renames columns (each one's
tooltip names the file it was saved for). Files that match an entry, by
file name or else by columns (and only when the match is unambiguous), get
it picked and their names filled in, both when the setting is loaded and
when files are added later; names the user typed are never replaced by a
pick, nor cleared by picking None. A second banner, "Still to add", lists
the setting's files that no listed file stands for yet. A third lists the
picked names a file can't use: column names saved for headers it doesn't
have. Applying never stops for those; it adds the forms without them, and
its result says so.
"""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Collection, Dict, List, Optional, Sequence, Set, Tuple

import pandas as pd
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QListWidgetItem,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cci_ui.icons import IconName
from cci_ui.tasks import defer_if_busy, run_task
from cci_ui.widgets.buttons import make_button
from cci_ui.widgets.labels import section_label
from cci_ui.widgets.page import Page
from cci_ui.widgets.path_picker import downloads_folder
from cci_ui.widgets.status import StatusBanner
from cci_ui.widgets.tables import ColumnSpec, mark_cell, table_card
from cci_ui.widgets.views import PlaceholderListWidget
from clinical_reporting import feedback, steps
from clinical_reporting.additional_names import (
    FileNames,
    IgnoredName,
    Match,
    SavedFileNames,
    current_names,
    ignored_names,
    match,
    names_from,
)
from clinical_reporting.data import (
    additional_form_names,
    named_columns,
    try_load_tabular_files,
)
from clinical_reporting.report import CLReport
from clinical_reporting.session import (
    apply_additional_inputs,
    capture_selection,
    restore_selection,
)
from clinical_reporting.ui.table_actions import (
    add_copy_original_name_action,
    copy_original_names_to_new_names,
)

from ._common import CellComboBox, make_table

_NAME_COLUMNS = (ColumnSpec("stretch"), ColumnSpec("stretch", editable=True))
#: The Form names columns: file names are long, form names are short, and
#: the Saved names dropdowns list wider entries when they open.
_FORM_NAME_COLUMNS = (
    ColumnSpec("stretch"),
    ColumnSpec("interactive", 110, editable=True),
    ColumnSpec("interactive", 130, editable=True),
)
#: The Form names column holding each file's Saved names dropdown.
SAVED_NAMES_COLUMN = 2


class AdditionalInputPage(Page):
    """Optional CSV or Excel files (additional inputs) added to the report as forms."""

    KEY = steps.ADDITIONAL
    SECTION = "Data"
    ICON = IconName.ADDITIONAL_INPUT
    EXPORTS = (
        "pushButton_additional_file_add",
        "pushButton_additional_file_remove",
        "banner_additional",
        "banner_saved_names",
        "banner_ignored_names",
        "listWidget_additional_file",
        "tableWidget_update_form_name",
        "tableWidget_update_column_name",
    )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            steps.TITLES[self.KEY],
            "Optional. Add CSV or Excel files and rename their forms and columns. "
            "Your changes reach the report when you go to another step, or once "
            "every file a saved setting needs is added.",
            parent=parent,
        )
        self.pushButton_additional_file_add = make_button(
            "Add files…", icon_name=IconName.ADD
        )
        self.pushButton_additional_file_remove = make_button("Remove")
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.addWidget(self.pushButton_additional_file_add)
        toolbar.addWidget(self.pushButton_additional_file_remove)
        toolbar.addStretch(1)
        # What reaching the report did, or which files couldn't be read.
        self.banner_additional = StatusBanner()
        # The loaded setting's files not added yet: a standing list, so it
        # stays until they are added and isn't repeated in the status bar.
        self.banner_saved_names = StatusBanner(dismissible=False, announce=False)
        # Saved column names the files can't use: standing too, until the
        # files or their names change.
        self.banner_ignored_names = StatusBanner(dismissible=False, announce=False)

        self.listWidget_additional_file = PlaceholderListWidget(
            "No files added. Add CSV or Excel files to use them as extra forms."
        )
        self.listWidget_additional_file.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )

        self.tableWidget_update_form_name = make_table(
            ["Original name", "New name", "Saved names"],
            _FORM_NAME_COLUMNS,
            placeholder="Added files appear here.",
            controls=True,
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
        self.body.addWidget(self.banner_saved_names)
        self.body.addWidget(self.banner_ignored_names)
        self.body.addWidget(files_card)
        self.body.addLayout(names, 1)


class AdditionalInputMixin:
    """Behavior for the Additional input page."""

    def _init_additional_input(self) -> None:
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
        # The last result of reaching the report, which a later add keeps
        # even when it is a warning.
        self._additional_applied_message: Optional[feedback.Message] = None
        # The files and names as they last reached the report (see
        # _additional_draft_key); None: not since the report was new.
        self._additional_applied_key = None

        add_button = getattr(self.ui, "pushButton_additional_file_add", None)
        remove_button = getattr(self.ui, "pushButton_additional_file_remove", None)

        if add_button is not None:
            add_button.clicked.connect(self.click_add_additional_files)
        if remove_button is not None:
            remove_button.clicked.connect(self.click_remove_additional_files)

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
        initial_dir = (
            getattr(self, "_additional_input_directory", None) or downloads_folder()
        )
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
        was_ready = self._setting_files_ready()
        self.additional_inputs.update(loaded)
        picks, ignored = self._pick_saved_names(list(loaded))
        self._refresh_additional_files_ui()
        self._refresh_additional_tables()
        self._update_additional_buttons_state()
        banner = self.ui.banner_additional
        unread = None
        if failures:
            names = [Path(path).name for path in failures]
            reasons = [f"{Path(path).name}: {why}" for path, why in failures.items()]
            # One line on the page (it doesn't scroll); the reasons per file
            # are behind "Show details".
            unread = feedback.warning(
                f"These files could not be read and were not added: "
                f"{feedback.short_list(names)}.",
                "\n".join(reasons),
            )
            self._set_label_text(banner, unread)
        elif picks:
            self._show_saved_names_message(
                steps.saved_names_filled_message(
                    self._saved_names_setting,
                    picks,
                    ignored,
                    still_to_add=bool(self._saved_files_still_to_add()),
                )
            )
        elif (
            banner.text()
            and banner.kind() == "warning"
            and banner.text() != getattr(self, "_additional_applied_message", None)
        ):
            # What went wrong before (unreadable files) is old news; a result
            # isn't.
            self._set_label_text(banner, "")
        self._put_setting_files_in_if_completed(was_ready, picks=picks, unread=unread)
        # The user may have gone to another step while the files were read.
        self.apply_data_steps()

    def click_remove_additional_files(self) -> None:
        """Remove selected additional input files from the list.

        Their forms leave the report when the user goes to another step. The
        last input gone (no Corelisting ZIP either), the stacked forms and
        coalesced items go at once: nothing is left to make them from.
        """
        widget = getattr(self.ui, "listWidget_additional_file", None)
        if widget is None:
            return

        selected_items = widget.selectedItems()
        if not selected_items:
            return

        was_ready = self._setting_files_ready()
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
        self._drop_data_steps_without_input()
        self._put_setting_files_in_if_completed(was_ready)

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
        """Refresh the form/column rename tables and the saved names banners."""
        self._populating_additional_tables = True
        try:
            self._populate_form_name_table()
            self._ensure_form_selection()
            self._populate_column_name_table()
        finally:
            self._populating_additional_tables = False
        self._show_saved_names_banners()

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
        self.update_additional_input_ui()

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

        was_ready = self._setting_files_ready()
        new_name = item.text().strip()
        if new_name:
            self.additional_form_names[file_path] = new_name
        else:
            self.additional_form_names.pop(file_path, None)

        self._populate_column_name_table()
        self.update_additional_input_ui()
        self._put_setting_files_in_if_completed(was_ready)

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
        # A column renamed to a saved name stands in for the one it lacks.
        self._show_ignored_saved_names()

    def copy_selected_new_column_names_to_updated(self) -> None:
        """Copy selected new-column values into their updated-name cells."""

        def persist(original_item, updated_name_item) -> None:
            key = updated_name_item.data(Qt.UserRole)
            if key:
                self.additional_column_names[key] = original_item.text()

        copy_original_names_to_new_names(
            getattr(self.ui, "tableWidget_update_column_name", None), persist
        )
        self._show_ignored_saved_names()

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

    def _show_saved_names_banners(self) -> None:
        """Refresh the "Still to add" and ignored names banners."""
        self._show_missing_saved_files()
        self._show_ignored_saved_names()

    def _needed_saved_entries(self) -> List[SavedFileNames]:
        """The loaded setting's entries for the files it needs.

        Only entries for forms the setting selects count: names saved for a
        file the setting doesn't use aren't needed.
        """
        used_forms = getattr(self, "_saved_names_forms", None)
        return [
            entry
            for entry in self._saved_names()
            if entry.form_name and (used_forms is None or entry.form_name in used_forms)
        ]

    def _saved_files_still_to_add(self) -> List[SavedFileNames]:
        """The files the loaded setting needs that no listed file stands for."""
        added = self._saved_names_added()
        return [entry for entry in self._needed_saved_entries() if entry not in added]

    def _show_missing_saved_files(self) -> None:
        """List the loaded setting's files that aren't added yet."""
        banner = getattr(self.ui, "banner_saved_names", None)
        if banner is None:
            return
        missing = self._saved_files_still_to_add()
        setting_name = getattr(self, "_saved_names_setting", "")
        self._set_label_text(
            banner,
            steps.saved_names_missing_message(setting_name, missing) if missing else "",
        )

    def _show_ignored_saved_names(self) -> None:
        """List the picked names the listed files can't use, if any.

        They stay listed until the files or their names change: another
        pick or None, the file removed, a column renamed to the saved name,
        or the setting forgotten.
        """
        banner = getattr(self.ui, "banner_ignored_names", None)
        if banner is None:
            return
        ignored = self._ignored_saved_names()
        self._set_label_text(
            banner, steps.saved_names_ignored_message(ignored) if ignored else ""
        )

    def _ignored_saved_names(self) -> List[IgnoredName]:
        """The picked names the listed files can't use, by file name.

        Only a file with a pick has saved names; applying adds its form
        without the column names saved for headers it doesn't have.
        """
        choices = getattr(self, "_saved_names_choice", {})
        count = len(self._saved_names())
        ignored: List[IgnoredName] = []
        for path in sorted(
            self.additional_inputs, key=lambda p: Path(p).name.casefold()
        ):
            choice = choices.get(path)
            if choice is not None and choice.index < count:
                ignored.extend(self._ignored_names_of(path, choice.index))
        return ignored

    def _ignored_names_of(self, file_path: str, index: int) -> List[IgnoredName]:
        """The names saved entry *index* has that *file_path* can't use."""
        return ignored_names(
            self._saved_names()[index],
            file_path,
            self._file_columns(file_path),
            self._current_names(file_path)[1],
        )

    def _saved_names_combo(
        self, file_path: str, entries: Sequence[SavedFileNames]
    ) -> QComboBox:
        """The Saved names dropdown for *file_path*, showing its pick.

        Greyed out, with only None, when there are no *entries*.
        """
        # Scrolling the table over it would otherwise replace the file's names.
        combo = CellComboBox()
        combo.addItem(steps.SAVED_NAMES_NONE)
        for entry, label in zip(entries, steps.saved_names_labels(entries)):
            combo.addItem(label)
            combo.setItemData(
                combo.count() - 1,
                steps.saved_names_entry_tip(entry),
                Qt.ItemDataRole.ToolTipRole,
            )
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

    def _file_columns(self, file_path: str) -> List[str]:
        """*file_path*'s column headers (none if it isn't listed)."""
        df = self.additional_inputs.get(file_path)
        return named_columns(df) if df is not None else []

    def _names_from_entry(self, file_path: str, index: int) -> FileNames:
        """The names saved entry *index* gives *file_path*."""
        return names_from(self._saved_names()[index], self._file_columns(file_path))

    def _has_names_from(self, file_path: str, index: int) -> bool:
        """Whether *file_path*'s names are exactly what entry *index* gives."""
        names = self._names_from_entry(file_path, index)
        return self._current_names(file_path) == (names.form_name, names.column_names)

    def _use_saved_names(
        self, file_path: str, index: Optional[int]
    ) -> List[IgnoredName]:
        """Give *file_path* the names of saved entry *index*, or none.

        Replaces the file's form and column names (``None`` clears them).
        Returns the entry's names the file can't use.
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
        return self._ignored_names_of(file_path, index)

    def _fill_saved_names(
        self, found: Dict[str, Match], paths: Collection[str]
    ) -> Tuple[List[Tuple[str, Optional[str]]], List[IgnoredName]]:
        """Fill in the names *found* for *paths*.

        Returns what was picked, as ``(file name, how it was matched)`` pairs,
        and the picked names the files can't use.
        """
        picks, ignored = [], []
        for file_path in sorted(paths, key=lambda path: Path(path).name.casefold()):
            if file_path not in found:
                continue
            ignored.extend(self._use_saved_names(file_path, found[file_path].index))
            self._saved_names_choice[file_path] = found[file_path]
            picks.append((Path(file_path).name, found[file_path].by))
        return picks, ignored

    def _listed_columns(self) -> Dict[str, List[str]]:
        """Each listed file's column headers, for matching."""
        return {path: named_columns(df) for path, df in self.additional_inputs.items()}

    def _pick_saved_names(
        self, new_paths: Sequence[str]
    ) -> Tuple[List[Tuple[str, Optional[str]]], List[IgnoredName]]:
        """Pick saved names for files just added; what was picked, as above.

        Only added files without names are filled in, and only with entries
        no listed file uses yet.
        """
        if not self._saved_names():
            return [], []
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
        not when it re-applies the setting once the files reach the report, so
        the picks made in between stay.
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
        picks, ignored = [], []
        if entries and self.additional_inputs:
            found = match(entries, self._listed_columns())
            eligible = [
                path
                for path, pick in found.items()
                if path in replaceable or self._has_names_from(path, pick.index)
            ]
            picks, ignored = self._fill_saved_names(found, eligible)
        # The "Still to add" banner says what isn't picked or added.
        self._refresh_additional_tables()
        if picks:
            self._show_saved_names_message(
                steps.saved_names_filled_message(setting_name, picks, ignored)
            )
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
        was_ready = self._setting_files_ready()
        previous = self._saved_names_choice.get(file_path)
        file_name = Path(file_path).name
        picked = None
        if index is not None:
            ignored = self._use_saved_names(file_path, index)
            self._saved_names_choice[file_path] = Match(index)
            entry = self._saved_names()[index]
            message = steps.saved_names_picked_message(entry, file_name, ignored)
            picked = (entry, file_name)
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
        self._show_saved_names_banners()
        self._show_saved_names_message(message)
        self.update_additional_input_ui()
        self._put_setting_files_in_if_completed(was_ready, picked=picked)

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

        (A new Corelisting ZIP starts a new report.) The files stay listed,
        and reach the new report with the other Data steps.
        """
        self._additional_form_keys = set()
        self._additional_input_signature = {}
        self._additional_applied_key = None

    def _collect_additional_form_names(self) -> Dict[str, str]:
        """Return a mapping of file path -> form name for additional inputs."""
        return additional_form_names(self.additional_inputs, self.additional_form_names)

    def _additional_draft_key(self) -> tuple:
        """The listed files and their names, to tell whether they changed."""
        return (
            tuple((path, id(frame)) for path, frame in self.additional_inputs.items()),
            tuple(sorted(self.additional_form_names.items())),
            tuple(sorted(self.additional_column_names.items())),
        )

    def _has_unapplied_additional_inputs(self) -> bool:
        """Whether the listed files or their names differ from the report's."""
        return self._additional_draft_key() != self._additional_applied_key and bool(
            self.additional_inputs or self._additional_form_keys
        )

    def _additional_name_problems(self) -> Dict[str, str]:
        """Why each listed file's New name can't be used, by path ("" if it can)."""
        loaded = set(getattr(self.report, "loaded_data", {}) or {})
        loaded -= set(self._additional_form_keys)
        stacked = {form.name for form in self.report.stacked_forms}
        return steps.additional_name_problems(
            self._collect_additional_form_names(),
            self.additional_form_names,
            loaded,
            stacked,
        )

    def _setting_files_ready(self) -> bool:
        """Whether every file the loaded setting needs is listed, no New name red.

        False while no loaded setting needs a file.
        """
        if not self._needed_saved_entries() or self._saved_files_still_to_add():
            return False
        return not any(self._additional_name_problems().values())

    def update_additional_input_ui(self) -> List[str]:
        """Mark each New name the report can't use; return the page's problems.

        The problems (one line per file) hold the step and turn its badge red.
        """
        found = self._additional_name_problems()
        table = getattr(self.ui, "tableWidget_update_form_name", None)
        if table is not None:
            for row in range(table.rowCount()):
                item = table.item(row, 1)
                if item is not None:
                    mark_cell(item, found.get(item.data(Qt.UserRole), ""))
        lines = [f"{Path(path).name}: {text}" for path, text in found.items() if text]
        self._set_page_problems(steps.ADDITIONAL, lines)
        return lines

    def _apply_additional_step(self) -> None:
        """Bring the listed files, with their names, to the report.

        Nothing when they haven't changed, or while a name can't be used (the
        page marks it). With no files left, their forms leave the report.
        """
        if not self._has_unapplied_additional_inputs():
            return
        if self.update_additional_input_ui():
            return
        # Ensure a report object exists.
        if not hasattr(self, "report") or self.report is None:
            self.report = CLReport()

        previous_signature = dict(getattr(self, "_additional_input_signature", {}))

        # Capture current selections (forms/items/common/join) to restore after
        # the merge rebuilds fresh CLForm objects with defaults.
        selection_state = capture_selection(self.report)

        applied = apply_additional_inputs(
            self.report,
            self.additional_inputs,
            self.additional_form_names,
            self.additional_column_names,
            self._additional_form_keys,
        )
        new_signature = applied.signature
        signature_changed = new_signature != previous_signature

        self._additional_form_keys = set(applied.forms)
        self._additional_input_signature = new_signature
        self._additional_applied_key = self._additional_draft_key()
        # The forms are added even when some picked names can't be used.
        self._additional_applied_message = steps.additional_applied_message(
            applied.forms, self._ignored_saved_names()
        )
        self._set_label_text(
            self.ui.banner_additional, self._additional_applied_message
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
        restore_selection(self.report, selection_state)

        self.update_all_ui()

    def _put_setting_files_in_if_completed(
        self,
        was_ready: bool,
        *,
        picks: Sequence[Tuple[str, Optional[str]]] = (),
        picked: Optional[Tuple[SavedFileNames, str]] = None,
        unread: Optional[feedback.Message] = None,
    ) -> None:
        """Bring the files to the report at once if this change completed them.

        Called after a change on the page (files added, a Saved names pick, a
        New name typed, files removed); *was_ready* is
        :meth:`_setting_files_ready` before it. Only the change into "every
        file the loaded setting needs is listed, and no New name is red"
        counts: later ones wait until the user leaves the step. Only on the
        page open in the window: elsewhere the step reaches the report
        anyway, and partial windows (tests) apply it themselves. It runs just
        after the change, so the table it rebuilds isn't the one still
        handling that change. *picks*, *picked* and *unread* are what the
        change did, for the message (see :meth:`_put_setting_files_in`).
        """
        shell = getattr(self.ui, "shell", None)
        if was_ready or shell is None or shell.current() != steps.ADDITIONAL:
            return
        if not self._setting_files_ready():
            return
        QTimer.singleShot(
            0, self, partial(self._put_setting_files_in, picks, picked, unread)
        )

    def _put_setting_files_in(
        self,
        picks: Sequence[Tuple[str, Optional[str]]] = (),
        picked: Optional[Tuple[SavedFileNames, str]] = None,
        unread: Optional[feedback.Message] = None,
    ) -> None:
        """Bring the listed files to the report now: the setting's are all in.

        Then the other Data steps, as on leaving. The banner says what
        completed the files (*picks*: names picked as they were added;
        *picked*: a Saved names pick, as ``(entry, file name)``), what reached
        the report, and the files that couldn't be read (*unread*).
        """
        if defer_if_busy(
            self, partial(self._put_setting_files_in, picks, picked, unread)
        ):
            return
        # Something may have changed since the change that completed them.
        if (
            not self._setting_files_ready()
            or not self._has_unapplied_additional_inputs()
        ):
            return
        setting_name = self._saved_names_setting
        self._apply_additional_step()
        message = steps.setting_files_in_message(
            setting_name,
            self._additional_form_keys,
            self._ignored_saved_names(),
            picks=picks,
            picked=picked,
        )
        if unread is not None:
            details = "\n".join(
                text for text in (message.details, unread.details) if text
            )
            message = feedback.warning(f"{message} {unread}", details or None)
        self._additional_applied_message = message
        self._set_label_text(self.ui.banner_additional, message)
        self.apply_data_steps()
