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

from .additional_input_tab import AdditionalInputTabMixin
from .base import WidgetBaseMixin
from .filters_tab import FiltersTabMixin
from .join_config import JoinConfigMixin
from .main_ui import ClinicalReportingUi
from .navigation import NavigationMixin
from .ordering_tab import OrderRenameTabMixin
from .run_save_tab import RunAndSaveMixin
from .selection_tabs import CommonItemsTabMixin, FormItemsTabMixin, FormsTabMixin
from .settings_tab import SettingsTabMixin

#: The behavior mixins the window inherits, in resolution order.
BEHAVIORS = (
    WidgetBaseMixin,
    NavigationMixin,
    SettingsTabMixin,
    AdditionalInputTabMixin,
    FormsTabMixin,
    CommonItemsTabMixin,
    FormItemsTabMixin,
    FiltersTabMixin,
    JoinConfigMixin,
    OrderRenameTabMixin,
    RunAndSaveMixin,
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
        self._init_settings_tab()
        self._init_additional_input_tab()
        self._init_form_tab()
        self._init_common_items_tab()
        self._init_form_items_tab()
        self._init_filters_tab()
        self._init_comparison_and_order_tab()
        self._init_join_table()
        self._init_run_and_save_controls()
        self._init_navigation()
        # The shell's overlay covers the sidebar too while work runs.
        self.task_runner = TaskRunner(self, overlay=self.ui.shell.busy)

    def closeEvent(self, event):  # noqa: N802 - Qt override
        """Ignore any job still running, and start no more, once closing."""
        super().closeEvent(event)
        if event.isAccepted():
            self.task_runner.shutdown()
