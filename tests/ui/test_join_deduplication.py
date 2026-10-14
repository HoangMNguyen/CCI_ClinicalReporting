import types

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QComboBox, QTableWidget, QTableWidgetItem

from clinical_reporting.models import CLForm
from clinical_reporting.report import CLReport
from clinical_reporting.ui.base import WidgetBaseMixin
from clinical_reporting.ui.pages.joins import JoinsMixin


class DummyJoinWidget(JoinsMixin, WidgetBaseMixin):
    def __init__(self, report: CLReport, table: QTableWidget):
        self.report = report
        self.ui = types.SimpleNamespace(tableWidget_join=table)


def _build_join_table() -> QTableWidget:
    """DM first (it joins on nothing), then VS on Subject, Subject and Visit."""
    table = QTableWidget()
    table.setColumnCount(6)
    table.setRowCount(2)
    for row, form in enumerate(("DM", "VS")):
        table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        table.setItem(row, 1, QTableWidgetItem(form))
        for col in range(2, 5):
            combo = QComboBox()
            combo.addItems(["", "Subject", "Visit"])
            table.setCellWidget(row, col, combo)
        join_type_combo = QComboBox()
        join_type_combo.addItems(["Left join", "Inner join"])
        table.setCellWidget(row, 5, join_type_combo)

    table.cellWidget(1, 2).setCurrentText("Subject")
    table.cellWidget(1, 3).setCurrentText("Subject")
    table.cellWidget(1, 4).setCurrentText("Visit")
    table.cellWidget(1, 5).setCurrentText("Inner join")
    return table


def test_join_keys_are_deduped_in_ui(qapp):
    report = CLReport()
    report.selected_forms = {"DM": CLForm("DM"), "VS": CLForm("VS")}

    table = _build_join_table()
    widget = DummyJoinWidget(report, table)

    widget.update_join_list()

    form = report.selected_forms["VS"]
    assert form.get_join_items() == ["Subject", "Visit"]
    assert form.get_join_order() == 2
    assert form.get_join_how() == "Inner join"

    assert table.cellWidget(1, 2).currentText() == "Subject"
    assert table.cellWidget(1, 3).currentText() == ""
    assert table.cellWidget(1, 4).currentText() == "Visit"


def test_the_wheel_leaves_an_unfocused_join_type_alone(sample_window):
    sample_window.ui.shell.set_current("joins")
    QApplication.processEvents()
    table = sample_window.ui.tableWidget_join
    rows = {table.item(row, 1).text(): row for row in range(table.rowCount())}
    join_type = table.cellWidget(rows["VS"], 5)
    centre = QPointF(join_type.rect().center())
    wheel = QWheelEvent(
        centre,
        join_type.mapToGlobal(centre),
        QPoint(0, 0),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )

    QApplication.sendEvent(join_type, wheel)

    assert join_type.currentText() == "Left join"


def test_the_join_table_tidies_a_form_after_the_first(sample_window):
    window = sample_window
    window.report.update_join_items("VS", ["Visit", "Subject"], 3, "Sideways")

    window.update_join_table_ui()

    assert window.report.get_join_list_dict()["VS"] == {
        "items": ["Subject"],
        "order": 3,
        "how": "Left join",
    }
    table = window.ui.tableWidget_join
    vs = next(
        row for row in range(table.rowCount()) if table.item(row, 1).text() == "VS"
    )
    assert [table.cellWidget(vs, col).currentText() for col in range(2, 6)] == [
        "Subject",
        "",
        "",
        "Left join",
    ]
