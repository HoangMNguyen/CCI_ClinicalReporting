import types

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QTableWidget, QTableWidgetItem

from cci_ui.theme import manager as theme_manager
from cci_ui.theme.manager import Theme, current
from cci_ui.theme.palette import qcolor
from cci_ui.theme.tokens import COMFORTABLE, DARK, Density, Scheme
from clinical_reporting.models import CLForm
from clinical_reporting.report import CLReport
from clinical_reporting.ui.base import WidgetBaseMixin
from clinical_reporting.ui.pages.joins import JoinsMixin


class DummyJoinWidget(JoinsMixin, WidgetBaseMixin):
    def __init__(self, report: CLReport, table: QTableWidget):
        self.report = report
        self.ui = types.SimpleNamespace(tableWidget_join=table)


def _danger():
    return qcolor(current().colors.danger_text)


def _is_invalid(combo) -> bool:
    return bool(combo.property("invalid"))


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

    # The unique order (row 0) is fine; the shared order (rows 1 and 2) is
    # marked invalid, which the stylesheet draws in the danger color.
    assert not _is_invalid(table.cellWidget(0, 4))
    assert _is_invalid(table.cellWidget(1, 4)) and _is_invalid(table.cellWidget(2, 4))


def test_join_order_highlight_clears_when_unique(qapp):
    table = _build_order_table([2, 2])
    widget = DummyJoinWidget(CLReport(), table)

    widget._highlight_duplicate_join_orders()
    assert _is_invalid(table.cellWidget(0, 4))

    # Resolve the conflict and re-run; the mark should clear.
    table.cellWidget(1, 4).setCurrentText("1")
    widget._highlight_duplicate_join_orders()

    assert not _is_invalid(table.cellWidget(0, 4))
    assert not _is_invalid(table.cellWidget(1, 4))


def test_form_name_is_in_the_danger_color_when_it_needs_a_join_item(qapp):
    report = CLReport()
    report.selected_forms = {"DM": CLForm("DM")}
    table = _build_join_table()
    widget = DummyJoinWidget(report, table)
    for col in range(1, 4):
        table.cellWidget(0, col).setCurrentText("")

    widget.update_join_list()

    assert table.item(0, 0).foreground().color() == _danger()


def test_missing_join_item_highlight_clears_when_item_is_selected(qapp):
    table = _build_join_table()
    widget = DummyJoinWidget(CLReport(), table)
    for col in range(1, 4):
        table.cellWidget(0, col).setCurrentText("")
    widget._highlight_missing_join_items()
    assert table.item(0, 0).foreground().color() == _danger()

    table.cellWidget(0, 1).setCurrentText("Subject")
    widget._highlight_missing_join_items()

    assert table.item(0, 0).foreground().style() == Qt.NoBrush


def test_missing_join_item_highlight_refreshes_run_availability(qapp):
    table = _build_join_table()
    widget = DummyJoinWidget(CLReport(), table)
    refresh_calls = []
    widget._refresh_run_availability = lambda: refresh_calls.append(True)

    widget._highlight_missing_join_items()

    assert refresh_calls == [True]


def test_first_form_without_join_items_is_not_highlighted(qapp):
    table = _build_join_table()
    widget = DummyJoinWidget(CLReport(), table)
    for col in range(1, 4):
        table.cellWidget(0, col).setCurrentText("")
    table.cellWidget(0, 4).setCurrentText("1")

    widget._highlight_missing_join_items()

    assert table.item(0, 0).foreground().style() == Qt.NoBrush


def test_painting_the_missing_items_uses_the_current_theme_only(qapp, monkeypatch):
    table = _build_join_table()
    widget = DummyJoinWidget(CLReport(), table)
    refresh_calls = []
    widget._refresh_run_availability = lambda: refresh_calls.append(True)
    for col in range(1, 4):
        table.cellWidget(0, col).setCurrentText("")
    monkeypatch.setattr(
        theme_manager,
        "_current",
        Theme(Scheme.DARK, Density.COMFORTABLE, DARK, COMFORTABLE),
    )

    # What a theme change calls: recolor, without re-running the run checks.
    widget._paint_missing_join_items()

    assert table.item(0, 0).foreground().color() == qcolor(DARK.danger_text)
    assert refresh_calls == []
