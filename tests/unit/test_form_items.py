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
