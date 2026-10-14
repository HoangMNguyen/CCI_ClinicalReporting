"""Editable columns, on the DEMO01 sample report.

A column whose cells the user can change shows a pencil after its header
label; read-only columns don't. A plain-text cell of such a column opens on
one click (Ctrl- and Shift-clicks still select rows) and shows an I-beam
pointer. Rows holding dropdowns or fields are taller than read-only rows in
Compact, so the controls keep 2px above and below.
"""

import pandas as pd
import pytest
import shiboken6
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QLineEdit,
    QListWidget,
    QTableView,
)

from cci_ui.theme.tokens import LAYOUT, Density
from cci_ui.widgets.tables import is_editable_column
from clinical_reporting import steps
from clinical_reporting.ui.preview import build_preview_window


@pytest.fixture
def window(make_manager, settle):
    """The window on the sample report, shown, in Comfortable; Comfortable after."""
    theme = make_manager()
    # Not the automatic density: the test screen is small.
    theme.set_density(Density.COMFORTABLE)
    theme.apply()
    built = build_preview_window(theme=theme)
    built.resize(*LAYOUT.first_launch)
    built.show()
    QApplication.processEvents()
    yield built, theme
    theme.set_density(Density.COMFORTABLE)  # The density is process-wide.
    built.close()
    settle(built.task_runner)
    shiboken6.delete(built)


def _open(window, step):
    window.ui.shell.set_current(step)
    QApplication.processEvents()


def _tables(window):
    """Every table of the window, by what it is."""
    ui = window.ui
    grid = ui.tableView_stacked_items
    return {
        "Filters": ui.tableWidget_static_filter,
        "Comparisons": ui.tableWidget_dynamic_filter,
        "Joins": ui.tableWidget_join,
        "Order & rename": ui.tableWidget_rename,
        "Form names": ui.tableWidget_update_form_name,
        "Column names": ui.tableWidget_update_column_name,
        "Coalesced items": ui.tableWidget_coalesced_items,
        "Coalesced item's items": ui.tableWidget_coalesced_fills,
        "Stacked forms": ui.tableWidget_stacked_forms,
        "Items grid": grid,
        "Items grid's first column": grid.frozen,
        "Preview": ui.tableView_preview,
    }


def _shown_columns(view):
    model = view.model()
    if model is None:
        return []
    return [
        column
        for column in range(model.columnCount())
        if not view.isColumnHidden(column)
    ]


def _labels(view, columns):
    model = view.model()
    return [model.headerData(column, Qt.Orientation.Horizontal) for column in columns]


def _pencil_columns(view):
    return [
        column for column in _shown_columns(view) if is_editable_column(view, column)
    ]


def _can_change(view, index):
    """A dropdown or field to use, or a cell that can be typed in."""
    widget = view.indexWidget(index)
    if widget is not None:
        return widget.isEnabled() and widget.focusPolicy() != Qt.FocusPolicy.NoFocus
    flags = index.flags()
    return (
        view.editTriggers() != QAbstractItemView.EditTrigger.NoEditTriggers
        and bool(flags & Qt.ItemFlag.ItemIsEditable)
        and bool(flags & Qt.ItemFlag.ItemIsEnabled)
    )


def _changeable_columns(view):
    model = view.model()
    return [
        column
        for column in _shown_columns(view)
        if any(
            _can_change(view, model.index(row, column))
            for row in range(model.rowCount())
        )
    ]


def _rows(view):
    model = view.model()
    return 0 if model is None else model.rowCount()


# -- the Stacked forms page, as its own tests drive it


def _grid_rows(window):
    model = window.ui.tableView_stacked_items.model()
    return [model.index(row, 0).data() for row in range(model.rowCount())]


def _tick(window, row, *forms):
    """Tick *forms* in *row*'s Members checklist, in this order."""
    box = window.ui.tableWidget_stacked_forms.cellWidget(row, 1)
    box.showPopup()
    rows = box.findChild(QListWidget)
    for form in forms:
        (item,) = rows.findItems(form, Qt.MatchFlag.MatchExactly)
        center = rows.visualItemRect(item).center()
        QTest.mouseClick(rows.viewport(), Qt.MouseButton.LeftButton, pos=center)
    box.hidePopup()


def _new_stacked_form(window, name, *members):
    _open(window, steps.STACKED)
    window.click_new_stacked_form()
    row = window.ui.tableWidget_stacked_forms.rowCount() - 1
    edit = window.ui.tableWidget_stacked_forms.cellWidget(row, 0)
    edit.selectAll()
    QTest.keyClicks(edit, name)
    _tick(window, row, *members)


def _click_item(window, name, modifier=Qt.KeyboardModifier.NoModifier):
    grid = window.ui.tableView_stacked_items
    row = _grid_rows(window).index(name)
    center = grid.visualRect(grid.model().index(row, 1)).center()
    QTest.mouseClick(grid.viewport(), Qt.MouseButton.LeftButton, modifier, center)


def _fill_every_table(window, settle, tmp_path, monkeypatch):
    """Give every table rows, with something to change in each column that can be.

    An additional input file named LAB, saved in a setting that is then
    loaded (its Saved names dropdown has names to pick), a new filter, a new
    coalesced item whose second item has a condition, and a stacked form
    with Reason and Status matched.
    """
    ui = window.ui
    lab = tmp_path / "lab_results.csv"
    pd.DataFrame({"Subject ID": ["01-100"], "ALT (U/L)": [12]}).to_csv(lab, index=False)
    monkeypatch.setattr(
        QFileDialog, "getOpenFileNames", lambda *_args: ([str(lab)], "")
    )
    _open(window, steps.ADDITIONAL)
    settle(window.task_runner)  # Adding files waits while the window is busy.
    window.click_add_additional_files()
    settle(window.task_runner)
    ui.tableWidget_update_form_name.item(0, 1).setText("LAB")
    window.click_apply_additional_forms()
    window.settings_directory = str(tmp_path / "settings")
    ui.checkBox_save_current_setting.setChecked(True)
    ui.lineEdit_setting_name.setText("Lab review")
    window.click_save_setting()
    ui.checkBox_saved_setting.setChecked(True)
    ui.comboBox_saved_setting.setCurrentIndex(
        ui.comboBox_saved_setting.findText("Lab review")
    )
    settle(window.task_runner)
    ui.tableWidget_update_form_name.selectRow(0)  # Its columns show.

    window.static_filter_add()  # "=", so its value can be typed.

    _open(window, steps.COALESCED)
    window.click_new_coalesced_item()
    condition = ui.tableWidget_coalesced_fills.cellWidget(1, 2)
    condition.setCurrentIndex(condition.findText("="))

    _new_stacked_form(window, "DISP", "EOT", "DS")
    _click_item(window, "Reason")
    _click_item(window, "Status", Qt.KeyboardModifier.ControlModifier)
    window.click_match_stacked_items()
    QApplication.processEvents()


def test_the_pencil_marks_the_columns_the_user_can_change(window):
    built, _theme = window
    _new_stacked_form(built, "DISP", "EOT", "DS")

    pencils = {
        name: _labels(view, _pencil_columns(view))
        for name, view in _tables(built).items()
    }

    assert pencils == {
        "Filters": ["Item", "Operator", "Value"],
        "Comparisons": ["Item 1", "Operator", "Item 2"],
        "Joins": ["Item 1", "Item 2", "Item 3", "Order", "Type"],
        "Order & rename": ["Output name"],
        "Form names": ["New name", "Saved names"],
        "Column names": ["New name"],
        "Coalesced items": [],
        "Coalesced item's items": [
            "Item",
            "Fills where the value so far is empty or",
            "Value",
        ],
        "Stacked forms": ["Name", "Members"],
        "Items grid": ["EOT  24 rows", "DS  24 rows"],
        "Items grid's first column": ["Stacked item"],
        "Preview": [],
    }


def test_the_pencils_are_on_exactly_the_columns_with_a_cell_to_change(
    window, settle, tmp_path, monkeypatch
):
    built, _theme = window
    _fill_every_table(built, settle, tmp_path, monkeypatch)
    tables = _tables(built)
    filled = {name: view for name, view in tables.items() if _rows(view)}
    # A date field's calendar is a table too, without a header.
    others = [
        view
        for view in built.findChildren(QTableView)
        if not view.horizontalHeader().isHidden()
        and not any(view is table for table in tables.values())
    ]

    pencils = {
        name: _labels(view, _pencil_columns(view)) for name, view in filled.items()
    }
    changeable = {
        name: _labels(view, _changeable_columns(view)) for name, view in filled.items()
    }

    assert others == []
    # The preview is built only once its page shows.
    assert [name for name in tables if name not in filled] in ([], ["Preview"])
    assert pencils == changeable


def test_one_plain_click_opens_a_text_cell_but_not_a_ctrl_click_or_read_only_cell(
    window,
):
    built, _theme = window
    _open(built, steps.ORDER)
    table = built.ui.tableWidget_rename
    table.clearSelection()

    def click(row, column, modifier=Qt.KeyboardModifier.NoModifier):
        center = table.visualRect(table.model().index(row, column)).center()
        QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, modifier, center)
        QApplication.processEvents()  # The editor opens after the click.
        return isinstance(table.cellWidget(row, column), QLineEdit)

    ctrl_click = click(1, 1, Qt.KeyboardModifier.ControlModifier)
    selected = [index.row() for index in table.selectionModel().selectedRows()]
    read_only = click(2, 0)
    plain = click(0, 1)

    assert (plain, ctrl_click, read_only) == (True, False, False)
    assert selected == [1]  # The Ctrl-click selected its row.


def test_the_pointer_is_an_i_beam_over_a_text_cell_only(window):
    built, _theme = window
    _open(built, steps.ORDER)
    table = built.ui.tableWidget_rename
    viewport = table.viewport()

    def pointer_over(row, column):
        center = table.visualRect(table.model().index(row, column)).center()
        QTest.mouseMove(viewport, center)
        return viewport.cursor().shape()

    assert (pointer_over(0, 1), pointer_over(0, 0)) == (
        Qt.CursorShape.IBeamCursor,
        Qt.CursorShape.ArrowCursor,
    )


def test_rows_holding_controls_are_taller_than_read_only_rows_in_compact(window):
    built, theme = window
    _open(built, steps.FILTERS)
    filters = built.ui.tableWidget_static_filter
    rename = built.ui.tableWidget_rename

    def rows_and_item_box():
        QApplication.processEvents()  # The dropdowns take their new places.
        cell = filters.visualRect(filters.model().index(0, 0))
        box = filters.cellWidget(0, 0).geometry()
        return (
            filters.verticalHeader().defaultSectionSize(),
            rename.verticalHeader().defaultSectionSize(),
            box.height(),
            (box.top() - cell.top(), cell.bottom() - box.bottom()),
        )

    comfortable = rows_and_item_box()
    theme.set_density(Density.COMPACT)
    compact = rows_and_item_box()
    theme.set_density(Density.COMFORTABLE)

    assert comfortable == (32, 32, 28, (2, 2))
    assert compact == (28, 24, 24, (2, 2))


def test_in_compact_every_table_holding_controls_has_the_taller_rows(window):
    built, theme = window
    tables = {
        name: view
        for name, view in _tables(built).items()
        if name not in ("Items grid", "Items grid's first column", "Preview")
    }
    theme.set_density(Density.COMPACT)
    heights = {
        name: view.verticalHeader().defaultSectionSize()
        for name, view in tables.items()
    }
    theme.set_density(Density.COMFORTABLE)

    # Dropdowns or fields in the cells: 28; plain text only: 24.
    assert heights == {
        "Filters": 28,
        "Comparisons": 28,
        "Joins": 28,
        "Order & rename": 24,
        "Form names": 28,
        "Column names": 24,
        "Coalesced items": 24,
        "Coalesced item's items": 28,
        "Stacked forms": 28,
    }
