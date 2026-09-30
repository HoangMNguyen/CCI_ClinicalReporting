"""Tab navigation helpers for the Clinical Reporting widget."""

from __future__ import annotations


class NavigationMixin:
    """Behavior for inter-tab coordination."""

    def _init_tab_navigation(self) -> None:
        """Register tab navigation handlers."""
        self.ui.tabWidget.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index: int) -> None:
        """Trigger updates when specific pages become active."""
        if self.ui.tabWidget.widget(index) is self.ui.page_preview:
            self.preview_report()
