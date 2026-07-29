"""Tab navigation helpers for the Clinical Reporting widget."""

from __future__ import annotations


class NavigationMixin:
    """Behavior for inter-tab coordination."""

    def _init_tab_navigation(self) -> None:
        """Register tab navigation handlers."""
        self.ui.tabWidget.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index: int) -> None:
        """Trigger updates when specific tabs become active."""
        tab_text = self.ui.tabWidget.tabText(index)
        if tab_text == "Preview and Save":
            self.preview_report()
