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
