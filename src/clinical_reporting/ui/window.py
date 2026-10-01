"""Composed main window for the Clinical Reporting tool.

The original :mod:`widget` module contained a single 1,600-line class
that intertwined UI wiring, persistence, and domain orchestration.  This
module replaces it with a composition of focused mixins that live in the
:mod:`ui` package.  Each mixin encapsulates one functional area (settings,
forms, filters, etc.), while :class:`Widget` coordinates them to create
the application's main window.
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
from .controller import FeatureController, compose_behaviors
from .filters_tab import FiltersTabMixin
from .join_config import JoinConfigMixin
from .main_ui import ClinicalReportingUi
from .navigation import NavigationMixin
from .ordering_tab import OrderRenameTabMixin
from .run_save_tab import RunAndSaveMixin
from .selection_tabs import CommonItemsTabMixin, FormItemsTabMixin, FormsTabMixin
from .settings_tab import SettingsTabMixin

#: The behaviors composed onto the window, in the order they are applied.
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


@compose_behaviors(*BEHAVIORS)
class Widget(QMainWindow):
    """Main window composed from explicit feature controllers.

    Pass the app's *theme* manager for the header's Display button (the
    tests and previews may leave it out).
    """

    def __init__(self, parent=None, *, theme: Optional[ThemeManager] = None):
        super().__init__(parent)
        self.ui = ClinicalReportingUi()
        self.ui.setup(self, theme)

        self._controllers = {
            "shared": FeatureController(self, WidgetBaseMixin, NavigationMixin),
            "workspace": FeatureController(
                self, SettingsTabMixin, AdditionalInputTabMixin
            ),
            "selection": FeatureController(
                self, FormsTabMixin, CommonItemsTabMixin, FormItemsTabMixin
            ),
            "rules": FeatureController(
                self, FiltersTabMixin, JoinConfigMixin, OrderRenameTabMixin
            ),
            "output": FeatureController(self, RunAndSaveMixin),
        }

        self._controllers["shared"].call("_initialize_state")
        self._controllers["workspace"].call("_init_settings_tab")
        self._controllers["workspace"].call("_init_additional_input_tab")
        self._controllers["selection"].call("_init_form_tab")
        self._controllers["selection"].call("_init_common_items_tab")
        self._controllers["selection"].call("_init_form_items_tab")
        self._controllers["rules"].call("_init_filters_tab")
        self._controllers["rules"].call("_init_comparison_and_order_tab")
        self._controllers["rules"].call("_init_join_table")
        self._controllers["output"].call("_init_run_and_save_controls")
        self._controllers["shared"].call("_initialize_list_views")
        self._controllers["shared"].call("_init_navigation")
        # The shell's overlay covers the sidebar too while work runs.
        self.task_runner = TaskRunner(self, overlay=self.ui.shell.busy)

    def closeEvent(self, event):  # noqa: N802 - Qt override
        """Ignore any job still running, and start no more, once closing."""
        super().closeEvent(event)
        if event.isAccepted():
            self.task_runner.shutdown()
