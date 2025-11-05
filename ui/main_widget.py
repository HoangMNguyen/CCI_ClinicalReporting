"""Composed main widget for the Clinical Reporting tool.

The original :mod:`widget` module contained a single 1,600-line class
that intertwined UI wiring, persistence, and domain orchestration.  This
module replaces it with a composition of focused mixins that live in the
:mod:`ui` package.  Each mixin encapsulates one functional area (settings,
forms, filters, etc.), while :class:`Widget` coordinates them to create
the final :class:`~PySide6.QtWidgets.QWidget` used by the application.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QWidget

from ui_form import Ui_Widget

from .base import WidgetBaseMixin
from .common_items_tab import CommonItemsTabMixin
from .comparison_tab import ComparisonTabMixin
from .filters_tab import FiltersTabMixin
from .form_items_tab import FormItemsTabMixin
from .forms_tab import FormsTabMixin
from .navigation import NavigationMixin
from .run_save import RunAndSaveMixin
from .settings_tab import SettingsTabMixin


class Widget(
    QWidget,
    WidgetBaseMixin,
    SettingsTabMixin,
    FormsTabMixin,
    CommonItemsTabMixin,
    FormItemsTabMixin,
    FiltersTabMixin,
    ComparisonTabMixin,
    RunAndSaveMixin,
    NavigationMixin,
):
    """Concrete widget composed from specialized mixins."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Widget()
        self.ui.setupUi(self)

        self._initialize_state()
        self._setup_tables()
        self._init_settings_tab()
        self._init_form_tab()
        self._init_common_items_tab()
        self._init_form_items_tab()
        self._init_filters_tab()
        self._init_comparison_and_order_tab()
        self._init_run_and_save_controls()
        self._init_tab_navigation()
        self._initialize_list_views()


def main() -> int:
    """Entry point used by local testing."""
    app = QApplication(sys.argv)
    widget = Widget()
    widget.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

