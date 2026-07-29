"""Tests for the combined column order and rename table."""

import types

import pytest
from PySide6.QtCore import QItemSelectionModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
)

from clinical_reporting.report import CLReport
from clinical_reporting.ui.ordering_tab import OrderRenameTabMixin


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class DummyOrderWidget(OrderRenameTabMixin):
    """Minimal order/rename-tab host used to exercise the mixin."""

    def __init__(self, items, renames=None):
        self.report = CLReport()
        self.report.selected_common_items = list(items)
        self.report.set_rename_dict(dict(renames or {}))
        table = QTableWidget()
        table.setColumnCount(2)
        self.ui = types.SimpleNamespace(
            tableWidget_rename=table,
            pushButton_order_top=QPushButton(),
            pushButton_order_up=QPushButton(),
            pushButton_order_down=QPushButton(),
            pushButton_order_bottom=QPushButton(),
            lineEdit_order_search=QLineEdit(),
            label_search_result=QLabel(),
            pushButton_select_next=QPushButton(),
            pushButton_select_all=QPushButton(),
        )
        self._init_comparison_and_order_tab()
        self.update_order_rename_table()


def _table_text(widget):
    table = widget.ui.tableWidget_rename
    return [table.item(row, 0).text() for row in range(table.rowCount())]


def _rename_text(widget):
    table = widget.ui.tableWidget_rename
    return {
        table.item(row, 0).text(): table.item(row, 1).text()
        for row in range(table.rowCount())
    }


def _select_rows(widget, rows):
    table = widget.ui.tableWidget_rename
    table.clearSelection()
    selection_model = table.selectionModel()
    for row in rows:
        selection_model.select(
            table.model().index(row, 0),
            QItemSelectionModel.SelectionFlag.Select
            | QItemSelectionModel.SelectionFlag.Rows,
        )
    table.setCurrentCell(
        rows[0], 0, QItemSelectionModel.SelectionFlag.NoUpdate
    )


def _selected_text(widget):
    table = widget.ui.tableWidget_rename
    return [
        table.item(index.row(), 0).text()
        for index in sorted(table.selectionModel().selectedRows(), key=lambda index: index.row())
    ]


def test_order_table_supports_extended_row_selection(qapp):
    widget = DummyOrderWidget(["A", "B", "C"])
    table = widget.ui.tableWidget_rename

    assert table.selectionMode() == QAbstractItemView.ExtendedSelection
    assert table.selectionBehavior() == QAbstractItemView.SelectRows
    assert (
        table.horizontalHeader().sectionResizeMode(0)
        == QHeaderView.ResizeMode.Stretch
    )


def test_search_counts_original_name_matches_and_selects_first(qapp):
    widget = DummyOrderWidget(
        ["DM.Age", "DM.Weight", "VS.Age"],
        {"DM.Weight": "Age"},
    )

    widget.ui.lineEdit_order_search.setText("age")

    assert widget.ui.label_search_result.text() == "Matches: 2"
    assert _selected_text(widget) == ["DM.Age"]
    assert widget.ui.tableWidget_rename.currentRow() == 0


def test_search_ignores_renamed_output_and_reports_no_matches(qapp):
    widget = DummyOrderWidget(["DM.Weight", "VS.Pulse"], {"DM.Weight": "Age"})
    _select_rows(widget, [1])

    widget.ui.lineEdit_order_search.setText("age")

    assert widget.ui.label_search_result.text() == "Matches: 0"
    assert _selected_text(widget) == []


def test_search_is_reapplied_when_order_table_refreshes(qapp):
    widget = DummyOrderWidget(["DM.Age", "VS.Pulse"])
    widget.ui.lineEdit_order_search.setText("age")
    widget.report.selected_common_items.append("LB.AgeResult")

    widget.update_order_rename_table()

    assert widget.ui.label_search_result.text() == "Matches: 2"
    assert _selected_text(widget) == ["DM.Age"]


@pytest.mark.parametrize(
    ("action", "items", "expected"),
    [
        (
            "click_order_up",
            ["DM.Weight", "DM.Age", "VS.Age", "VS.Pulse"],
            ["DM.Age", "VS.Age", "DM.Weight", "VS.Pulse"],
        ),
        (
            "click_order_down",
            ["DM.Age", "VS.Age", "DM.Weight", "VS.Pulse"],
            ["DM.Weight", "DM.Age", "VS.Age", "VS.Pulse"],
        ),
    ],
)
def test_reordering_search_matches_preserves_multi_row_selection(
    qapp, action, items, expected
):
    widget = DummyOrderWidget(items)
    widget.ui.lineEdit_order_search.setText("age")
    widget.ui.pushButton_select_all.click()

    getattr(widget, action)()

    assert _table_text(widget) == expected
    assert _selected_text(widget) == ["DM.Age", "VS.Age"]
    assert widget.ui.label_search_result.text() == "Matches: 2"


def test_select_next_cycles_through_matches_and_wraps(qapp):
    widget = DummyOrderWidget(["DM.Age", "DM.Weight", "VS.Age", "LB.AgeResult"])
    widget.ui.lineEdit_order_search.setText("age")

    widget.ui.pushButton_select_next.click()
    assert _selected_text(widget) == ["VS.Age"]

    widget.ui.pushButton_select_next.click()
    assert _selected_text(widget) == ["LB.AgeResult"]

    widget.ui.pushButton_select_next.click()
    assert _selected_text(widget) == ["DM.Age"]


def test_select_all_selects_every_matching_row(qapp):
    widget = DummyOrderWidget(["DM.Age", "DM.Weight", "VS.Age", "LB.Result"])
    widget.ui.lineEdit_order_search.setText("age")

    widget.ui.pushButton_select_all.click()

    assert _selected_text(widget) == ["DM.Age", "VS.Age"]
    assert widget.ui.label_search_result.text() == "Matches: 2"


def test_search_buttons_reflect_match_count(qapp):
    widget = DummyOrderWidget(["DM.Age", "DM.Weight", "VS.Age"])

    assert widget.ui.pushButton_select_next.isEnabled() is False
    assert widget.ui.pushButton_select_all.isEnabled() is False

    widget.ui.lineEdit_order_search.setText("weight")
    assert widget.ui.pushButton_select_next.isEnabled() is False
    assert widget.ui.pushButton_select_all.isEnabled() is True

    widget.ui.lineEdit_order_search.setText("age")
    assert widget.ui.pushButton_select_next.isEnabled() is True
    assert widget.ui.pushButton_select_all.isEnabled() is True

    widget.ui.lineEdit_order_search.setText("missing")
    assert widget.ui.pushButton_select_next.isEnabled() is False
    assert widget.ui.pushButton_select_all.isEnabled() is False


@pytest.mark.parametrize(
    ("action", "selected_rows", "expected"),
    [
        ("click_order_top", [2, 3], ["C", "D", "A", "B", "E"]),
        ("click_order_up", [2, 3], ["A", "C", "D", "B", "E"]),
        ("click_order_down", [1, 2], ["A", "D", "B", "C", "E"]),
        ("click_order_bottom", [1, 2], ["A", "D", "E", "B", "C"]),
    ],
)
def test_contiguous_selection_moves_together_and_stays_selected(
    qapp, action, selected_rows, expected
):
    widget = DummyOrderWidget(["A", "B", "C", "D", "E"])
    _select_rows(widget, selected_rows)
    selected_before = _selected_text(widget)

    getattr(widget, action)()

    assert _table_text(widget) == expected
    assert _selected_text(widget) == selected_before
    assert widget.report.get_selected_items_order_list() == expected
    assert widget.report.order_list_customized is True


def test_noncontiguous_blocks_each_move_one_position(qapp):
    widget = DummyOrderWidget(["A", "B", "C", "D", "E"])
    _select_rows(widget, [1, 3])

    widget.click_order_up()

    assert _table_text(widget) == ["B", "A", "D", "C", "E"]
    assert _selected_text(widget) == ["B", "D"]


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        ("click_order_top", ["B", "D", "A", "C", "E"]),
        ("click_order_bottom", ["A", "C", "E", "B", "D"]),
    ],
)
def test_noncontiguous_top_and_bottom_moves_are_stable(qapp, action, expected):
    widget = DummyOrderWidget(["A", "B", "C", "D", "E"])
    _select_rows(widget, [1, 3])

    getattr(widget, action)()

    assert _table_text(widget) == expected
    assert _selected_text(widget) == ["B", "D"]


def test_boundary_move_is_noop_and_does_not_customize_report(qapp):
    widget = DummyOrderWidget(["A", "B", "C", "D"])
    _select_rows(widget, [0, 1])

    widget.click_order_up()

    assert _table_text(widget) == ["A", "B", "C", "D"]
    assert _selected_text(widget) == ["A", "B"]
    assert widget.report.order_list_customized is False


def test_buttons_reflect_available_selection_moves(qapp):
    widget = DummyOrderWidget(["A", "B", "C", "D"])
    buttons = widget.ui

    assert buttons.pushButton_order_top.isEnabled() is False
    assert buttons.pushButton_order_up.isEnabled() is False
    assert buttons.pushButton_order_down.isEnabled() is False
    assert buttons.pushButton_order_bottom.isEnabled() is False

    _select_rows(widget, [0, 1])
    assert buttons.pushButton_order_top.isEnabled() is False
    assert buttons.pushButton_order_up.isEnabled() is False
    assert buttons.pushButton_order_down.isEnabled() is True
    assert buttons.pushButton_order_bottom.isEnabled() is True

    _select_rows(widget, [2, 3])
    assert buttons.pushButton_order_top.isEnabled() is True
    assert buttons.pushButton_order_up.isEnabled() is True
    assert buttons.pushButton_order_down.isEnabled() is False
    assert buttons.pushButton_order_bottom.isEnabled() is False


def test_reordering_preserves_renames_and_editing_targets_original_item(qapp):
    widget = DummyOrderWidget(
        ["Subject", "DM.Age", "VS.Pulse"],
        {"DM.Age": "Age", "VS.Pulse": "PulseBPM"},
    )
    _select_rows(widget, [2])

    widget.click_order_top()

    assert _table_text(widget) == ["VS.Pulse", "Subject", "DM.Age"]
    assert _rename_text(widget) == {
        "VS.Pulse": "PulseBPM",
        "Subject": "",
        "DM.Age": "Age",
    }

    widget.ui.tableWidget_rename.item(0, 1).setText("HeartRate")

    assert widget.report.get_rename_dict() == {
        "DM.Age": "Age",
        "VS.Pulse": "HeartRate",
    }


def test_context_action_copies_selected_original_names_to_rename(qapp):
    widget = DummyOrderWidget(
        ["Subject", "DM.Age", "VS.Pulse"],
        {"DM.Age": "Age"},
    )
    _select_rows(widget, [0, 2])

    widget.copy_original_name_action.trigger()

    assert _rename_text(widget) == {
        "Subject": "Subject",
        "DM.Age": "Age",
        "VS.Pulse": "VS.Pulse",
    }
    # Identity values are intentionally omitted from the report mapping until
    # the user edits the copied text into an actual rename.
    assert widget.report.get_rename_dict() == {"DM.Age": "Age"}


def test_refresh_uses_custom_order_and_removes_blank_rename(qapp):
    widget = DummyOrderWidget(["A", "B", "C"], {"B": "Bee"})
    widget.report.set_selected_items_order_list(["C", "B", "A"])

    widget.update_order_rename_table()

    assert _table_text(widget) == ["C", "B", "A"]
    assert _rename_text(widget)["B"] == "Bee"

    widget.ui.tableWidget_rename.item(1, 1).setText("")

    assert widget.report.get_rename_dict() == {}
