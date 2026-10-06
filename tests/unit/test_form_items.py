import types

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
