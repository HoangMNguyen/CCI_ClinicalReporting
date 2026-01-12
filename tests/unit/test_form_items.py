import types

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QListWidget

from clinical_reporting.core.forms import CLForm
from clinical_reporting.core.report import CLReport
from clinical_reporting.ui.tabs.form_items import FormItemsTabMixin
from clinical_reporting.ui.widgets.base import WidgetBaseMixin


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class DummyFormItemsWidget(FormItemsTabMixin, WidgetBaseMixin):
    def __init__(self, report: CLReport):
        # Only the attributes used by the form item helpers are initialized.
        self.report = report
        self.ui = types.SimpleNamespace(
            listWidget_form_item_available=QListWidget(),
            listWidget_form_item_selected=QListWidget(),
            lineEdit_form_item_search=types.SimpleNamespace(text=lambda: ""),
        )


def test_form_items_handle_dotted_form_names(qapp):
    form_name = "Lab.2024"
    form = CLForm(form_name)
    form.available_form_items = ["Result"]

    report = CLReport()
    report.selected_forms = {form_name: form}

    widget = DummyFormItemsWidget(report)
    widget.add_listWidget_form_item_available()

    available_list = widget.ui.listWidget_form_item_available
    assert available_list.count() == 1

    item = available_list.item(0)
    assert item.data(Qt.UserRole) == (form_name, "Result")
    assert item.text() == f"{form_name}.Result"

    available_list.setCurrentRow(0)
    pairs = list(widget._iter_form_item_pairs(available_list))
    assert pairs == [(form_name, "Result")]
