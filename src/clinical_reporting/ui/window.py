"""Main window for the Clinical Reporting tool.

:class:`Widget` is a ``QMainWindow`` plus the behavior mixins in
:data:`BEHAVIORS`, one per page or group of pages. A name Qt already
defines wins, then the first mixin listed; no mixin calls ``super()``.
The widgets come from :class:`~ui.main_ui.ClinicalReportingUi`, built in
code: the pages sit in an :class:`~cci_ui.widgets.shell.AppShell` with a
sidebar of steps; layouts and column rules handle resizing.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QMainWindow

from cci_ui.tasks import TaskRunner
from cci_ui.theme.manager import ThemeManager

from .additional_input_tab import AdditionalInputMixin
from .base import WidgetBaseMixin
from .main_ui import ClinicalReportingUi
from .navigation import NavigationMixin
from .pages.filters import FiltersMixin
from .pages.joins import JoinsMixin
from .pages.order_rename import OrderRenameMixin
from .pages.preview_export import PreviewExportMixin
from .selection_tabs import CommonItemsMixin, FormItemsMixin, FormsMixin
from .settings_tab import SourceDataMixin

#: The behavior mixins the window inherits, in resolution order.
BEHAVIORS = (
    WidgetBaseMixin,
    NavigationMixin,
    SourceDataMixin,
    AdditionalInputMixin,
    FormsMixin,
    CommonItemsMixin,
    FormItemsMixin,
    FiltersMixin,
    JoinsMixin,
    OrderRenameMixin,
    PreviewExportMixin,
)


class Widget(QMainWindow, *BEHAVIORS):
    """Main window: the Qt window plus every behavior mixin.

    Pass the app's *theme* manager for the header's Display button (the
    tests and previews may leave it out).
    """

    def __init__(self, parent=None, *, theme: Optional[ThemeManager] = None):
        super().__init__(parent)
        self.ui = ClinicalReportingUi()
        self.ui.setup(self, theme)

        self._initialize_state()
        self._init_source_data()
        self._init_additional_input()
        self._init_forms()
        self._init_common_items()
        self._init_form_items()
        self._init_filters()
        self._init_order_rename()
        self._init_joins()
        self._init_preview_export()
        self._init_navigation()
        # The shell's overlay covers the sidebar too while work runs.
        self.task_runner = TaskRunner(self, overlay=self.ui.shell.busy)

    def closeEvent(self, event):  # noqa: N802 - Qt override
        """Ignore any job still running, and start no more, once closing."""
        super().closeEvent(event)
        if event.isAccepted():
            self.task_runner.shutdown()
