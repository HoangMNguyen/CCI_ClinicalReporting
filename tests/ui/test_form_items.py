import types

import pandas as pd
from PySide6.QtWidgets import QListWidget

from clinical_reporting.report import CLReport
from clinical_reporting.ui.base import WidgetBaseMixin
from clinical_reporting.ui.selection_tabs import FormItemsTabMixin


class DummyFormItemsWidget(FormItemsTabMixin, WidgetBaseMixin):
    def __init__(self, report: CLReport):
        # Only the attributes used by the form item helpers are initialized.
        self.report = report
        self.ui = types.SimpleNamespace(
            listWidget_form_item_available=QListWidget(),
            listWidget_form_item_selected=QListWidget(),
            lineEdit_form_item_search=types.SimpleNamespace(text=lambda: ""),
        )


def test_selecting_an_unqualified_entry_changes_nothing(qapp):
    """An entry without the form/item separator leaves every form alone."""
    report = CLReport()
    report.set_data({"DM": pd.DataFrame({"Subject": ["001"], "AGE": [30]})})
    report.add_all_selected_forms()
    widget = DummyFormItemsWidget(report)
    available = widget.ui.listWidget_form_item_available
    # A bare form name: the list only ever holds "form.item" entries, and
    # splitting this one would select the item named "".
    available.addItem("DM")
    available.item(0).setSelected(True)

    widget.click_select_form_item()

    assert report.selected_forms["DM"].get_selected_form_items() == []
