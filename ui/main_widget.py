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

from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QApplication, QAbstractScrollArea, QWidget

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
        self._initial_widget_size = None
        self._initial_geometries = []
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
        self._capture_initial_layout_metrics()

    # ------------------------------------------------------------------
    # Dynamic resizing support

    def _capture_initial_layout_metrics(self) -> None:
        """Record the starting geometry for all UI elements."""

        self._initial_widget_size = self.size()
        self._initial_geometries = []
        self._record_child_geometries(self, depth=0)
        self._initial_geometries.sort(key=lambda item: item[0])

    def _record_child_geometries(self, widget: QWidget, *, depth: int) -> None:
        """Store child geometries in parent-first order for resizing."""

        for child in widget.findChildren(
            QWidget, options=Qt.FindDirectChildrenOnly
        ):
            if child is self:
                continue
            self._initial_geometries.append((depth, child, child.geometry()))

            # Avoid traversing into Qt-managed scroll area internals.
            if isinstance(child, QAbstractScrollArea):
                continue

            self._record_child_geometries(child, depth=depth + 1)

    def resizeEvent(self, event):  # noqa: D401 - inherited Qt docstring
        """Resize child widgets proportionally to the window size."""

        super().resizeEvent(event)

        if not self._initial_widget_size or not self._initial_geometries:
            return

        original_width = max(1, self._initial_widget_size.width())
        original_height = max(1, self._initial_widget_size.height())
        width_ratio = self.width() / original_width
        height_ratio = self.height() / original_height

        for _, child, rect in self._initial_geometries:
            if child is None or child.parent() is None:
                continue

            new_rect = QRect(
                round(rect.x() * width_ratio),
                round(rect.y() * height_ratio),
                max(1, round(rect.width() * width_ratio)),
                max(1, round(rect.height() * height_ratio)),
            )
            child.setGeometry(new_rect)

        tables = [
            getattr(self.ui, "tableWidget_join", None),
            getattr(self.ui, "tableWidget_static_filter", None),
            getattr(self.ui, "tableWidget_dynamic_filter", None),
            getattr(self.ui, "tableWidget_rename", None),
        ]

        for table in tables:
            if table is not None:
                self._adjust_column_widths(table)


def main() -> int:
    """Entry point used by local testing."""
    app = QApplication(sys.argv)
    widget = Widget()
    widget.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

