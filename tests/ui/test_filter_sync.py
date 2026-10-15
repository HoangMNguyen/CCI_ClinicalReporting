"""The filter tables and the report's filters, kept in step.

Every edit stores every row of the table in the report, in table order, a row
still being filled in too (validation marks what it lacks). Most tests use the
sample window.
"""

import pandas as pd
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication

from clinical_reporting.report import CLReport
from clinical_reporting.ui.base import WidgetBaseMixin
from clinical_reporting.ui.pages.filters import FiltersMixin


class _FilterWidget(FiltersMixin, WidgetBaseMixin):
    """Minimal stand-in: the mixin's item list, without Qt widgets."""

    def __init__(self, report):
        self.report = report


def _report_with_items():
    report = CLReport()
    report.set_data(
        {
            "DM": pd.DataFrame({"Subject": ["1"], "Age": [30]}),
            "VS": pd.DataFrame({"Subject": ["1"], "Pulse": [60]}),
        }
    )
    report.add_selected_form("DM")
    report.selected_forms["DM"].set_form_item_state("Age", selected=True)
    report.add_selected_form("VS")
    report.selected_forms["VS"].set_form_item_state("Pulse", selected=True)
    report.set_common_item_state("Subject", selected=True)
    return report


def test_selected_filter_items_are_sorted_common_and_form_items():
    widget = _FilterWidget(_report_with_items())
    assert widget._selected_filter_items() == ["DM.Age", "Subject", "VS.Pulse"]


def test_every_filter_row_is_stored_in_table_order(sample_window):
    window = sample_window
    table = window.ui.tableWidget_static_filter

    window.static_filter_add()
    added = list(window.report.get_static_filter_items())
    box = table.cellWidget(1, 0)
    box.setCurrentIndex(box.findText("Subject"))
    table.item(1, 2).setText("01-100")

    assert added == [("DM.Age", ">=", "18"), ("", "=", "")]
    assert window.report.get_static_filter_items() == [
        ("DM.Age", ">=", "18"),
        ("Subject", "=", "01-100"),
    ]


def test_typed_text_that_isnt_an_item_stores_no_item(sample_window):
    window = sample_window
    window.static_filter_add()

    window.ui.tableWidget_static_filter.cellWidget(1, 0).setEditText("DM.Ag")
    window.synchronize_static_filters()

    assert window.report.get_static_filter_items()[1] == ("", "=", "")


def test_removing_a_filter_row_keeps_the_rows_in_step(sample_window):
    window = sample_window
    table = window.ui.tableWidget_static_filter
    window.static_filter_add()
    table.selectRow(0)

    window.static_filter_remove()

    assert window.report.get_static_filter_items() == [("", "=", "")]
    assert table.rowCount() == 1 and table.cellWidget(0, 0).currentText() == ""


def test_every_comparison_row_is_stored_in_table_order(sample_window):
    window = sample_window
    table = window.ui.tableWidget_dynamic_filter

    window.dynamic_filter_add()
    added = list(window.report.get_dynamic_filter_items())
    left = table.cellWidget(1, 0)
    left.setCurrentIndex(left.findText("DM.Age"))

    assert added == [("AE.End Date", ">=", "AE.Start Date"), ("", "=", "")]
    assert window.report.get_dynamic_filter_items() == [
        ("AE.End Date", ">=", "AE.Start Date"),
        ("DM.Age", "=", ""),
    ]


def test_the_wheel_leaves_an_unfocused_filter_operator_alone(sample_window):
    sample_window.ui.shell.set_current("filters")
    QApplication.processEvents()
    operator = sample_window.ui.tableWidget_static_filter.cellWidget(0, 1)
    centre = QPointF(operator.rect().center())
    wheel = QWheelEvent(
        centre,
        operator.mapToGlobal(centre),
        QPoint(0, 0),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )

    QApplication.sendEvent(operator, wheel)

    assert operator.currentText() == ">="
