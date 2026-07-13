"""Tests for the filter table -> report synchronisation logic.

The searchable-combo UX rebuilds the report's filters from the table on every
edit, skipping rows whose item field is still empty ("an unfilled filter row
applies nothing"). These exercise that pure rebuild logic with lightweight
fakes, so no Qt event loop / display is required.
"""

import pandas as pd

from clinical_reporting.core.report import CLReport
from clinical_reporting.ui.tabs.filters import FiltersTabMixin


class _Combo:
    def __init__(self, text):
        self._text = text

    def currentText(self):
        return self._text


class _ValueItem:
    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text


class _StaticTable:
    """Fake static filter table: (item combo, operator combo, value item) per row."""

    def __init__(self, rows):
        self._rows = rows  # list of (item, operator, value)

    def rowCount(self):
        return len(self._rows)

    def cellWidget(self, row, col):
        item, operator, _ = self._rows[row]
        if col == 0:
            return _Combo(item)
        if col == 1:
            return _Combo(operator)
        return None

    def item(self, row, col):
        _, _, value = self._rows[row]
        return _ValueItem(value) if col == 2 else None


class _DynamicTable:
    """Fake dynamic filter table: (item1 combo, operator combo, item2 combo) per row."""

    def __init__(self, rows):
        self._rows = rows  # list of (item1, operator, item2)

    def rowCount(self):
        return len(self._rows)

    def cellWidget(self, row, col):
        return _Combo(self._rows[row][col])


class _UI:
    pass


class _FilterWidget(FiltersTabMixin):
    """Minimal stand-in exercising the mixin's sync logic without Qt widgets."""

    def __init__(self, report, *, static_rows=None, dynamic_rows=None):
        self.report = report
        self.ui = _UI()
        self.ui.tableWidget_static_filter = _StaticTable(static_rows or [])
        self.ui.tableWidget_dynamic_filter = _DynamicTable(dynamic_rows or [])


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


def test_synchronize_static_filters_keeps_valid_and_skips_empty_rows():
    report = _report_with_items()
    widget = _FilterWidget(
        report,
        static_rows=[
            ("Subject", "=", "1"),  # valid -> kept
            ("", "=", "x"),  # empty item -> skipped
            ("DM.Age", ">", "18"),  # valid -> kept
        ],
    )
    widget.synchronize_static_filters()
    assert report.get_static_filter_items() == [("Subject", "=", "1"), ("DM.Age", ">", "18")]


def test_synchronize_static_filters_all_empty_applies_nothing():
    report = _report_with_items()
    widget = _FilterWidget(report, static_rows=[("", "=", ""), ("", "<", "5")])
    widget.synchronize_static_filters()
    assert report.get_static_filter_items() == []


def test_synchronize_static_filters_drops_invalid_item_text():
    # A partially typed / unknown item is not a real selection and is not applied.
    report = _report_with_items()
    widget = _FilterWidget(report, static_rows=[("DM.Ag", "=", "30")])
    widget.synchronize_static_filters()
    assert report.get_static_filter_items() == []


def test_synchronize_dynamic_filters_skips_incomplete_rows():
    report = _report_with_items()
    widget = _FilterWidget(
        report,
        dynamic_rows=[
            ("DM.Age", ">", "VS.Pulse"),  # complete -> kept
            ("DM.Age", ">", ""),  # missing item2 -> skipped
            ("", "=", "VS.Pulse"),  # missing item1 -> skipped
        ],
    )
    widget.synchronize_dynamic_filters()
    assert report.get_dynamic_filter_items() == [("DM.Age", ">", "VS.Pulse")]
