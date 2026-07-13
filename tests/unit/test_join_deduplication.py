import types

import pytest
from PySide6.QtWidgets import QApplication, QComboBox, QTableWidget, QTableWidgetItem

from clinical_reporting.core.forms import CLForm
from clinical_reporting.core.report import CLReport
from clinical_reporting.ui.tabs.comparison import ComparisonTabMixin


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class DummyJoinWidget(ComparisonTabMixin):
    def __init__(self, report: CLReport, table: QTableWidget):
        self.report = report
        self.ui = types.SimpleNamespace(tableWidget_join=table)


def _build_join_table() -> QTableWidget:
    table = QTableWidget()
    table.setColumnCount(6)
    table.setRowCount(1)
    table.setItem(0, 0, QTableWidgetItem("DM"))

    for col in range(1, 4):
        combo = QComboBox()
        combo.addItems(["", "Subject", "Visit"])
        table.setCellWidget(0, col, combo)

    table.cellWidget(0, 1).setCurrentText("Subject")
    table.cellWidget(0, 2).setCurrentText("Subject")
    table.cellWidget(0, 3).setCurrentText("Visit")

    order_combo = QComboBox()
    order_combo.addItems(["1", "2"])
    order_combo.setCurrentText("2")
    table.setCellWidget(0, 4, order_combo)

    join_type_combo = QComboBox()
    join_type_combo.addItems(["Left join", "Inner join"])
    join_type_combo.setCurrentText("Inner join")
    table.setCellWidget(0, 5, join_type_combo)

    return table


def test_join_keys_are_deduped_in_ui(qapp):
    report = CLReport()
    report.selected_forms = {"DM": CLForm("DM")}

    table = _build_join_table()
    widget = DummyJoinWidget(report, table)

    widget.update_join_list()

    form = report.selected_forms["DM"]
    assert form.get_join_items() == ["Subject", "Visit"]
    assert form.get_join_order() == 2
    assert form.get_join_how() == "Inner join"

    assert table.cellWidget(0, 1).currentText() == "Subject"
    assert table.cellWidget(0, 2).currentText() == ""
    assert table.cellWidget(0, 3).currentText() == "Visit"


def _build_order_table(orders) -> QTableWidget:
    """Build a join table with only the join-order column populated."""
    table = QTableWidget()
    table.setColumnCount(6)
    table.setRowCount(len(orders))
    for row, order in enumerate(orders):
        table.setItem(row, 0, QTableWidgetItem(f"Form{row}"))
        order_combo = QComboBox()
        order_combo.addItems([str(i) for i in range(1, len(orders) + 1)])
        order_combo.setCurrentText(str(order))
        table.setCellWidget(row, 4, order_combo)
    return table


def test_duplicate_join_orders_are_highlighted(qapp):
    table = _build_order_table([1, 2, 2])
    widget = DummyJoinWidget(CLReport(), table)

    widget._highlight_duplicate_join_orders()

    # The unique order (row 0) keeps default styling.
    assert table.cellWidget(0, 4).styleSheet() == ""
    # The shared order (rows 1 and 2) is shown red and bold.
    for row in (1, 2):
        style = table.cellWidget(row, 4).styleSheet()
        assert "color: red" in style
        assert "font-weight: bold" in style


def test_join_order_highlight_clears_when_unique(qapp):
    table = _build_order_table([2, 2])
    widget = DummyJoinWidget(CLReport(), table)

    widget._highlight_duplicate_join_orders()
    assert "color: red" in table.cellWidget(0, 4).styleSheet()

    # Resolve the conflict and re-run; styling should reset.
    table.cellWidget(1, 4).setCurrentText("1")
    widget._highlight_duplicate_join_orders()

    assert table.cellWidget(0, 4).styleSheet() == ""
    assert table.cellWidget(1, 4).styleSheet() == ""
