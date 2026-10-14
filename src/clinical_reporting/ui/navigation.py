"""Moving between the steps, and keeping the window around the pages current.

The pages sit in an :class:`~cci_ui.widgets.shell.AppShell` (``self.ui.shell``):
a sidebar of steps, a header saying where you are, and a status bar. This
mixin:

- builds the preview whenever its page opens;
- keeps the sidebar badges (:func:`clinical_reporting.steps.step_statuses`),
  the header, the window title, the status bar summary, and the "No data
  loaded" state of the pages that need data up to date. The other
  behaviors call :meth:`~ui.base.WidgetBaseMixin._report_changed` after
  changing the report; the refresh runs once control returns to the event
  loop, however many changes were made;
- shows the newest message of the pages' banners in the status bar (when
  that banner clears, the newest one still showing takes its place), and
  as a toast when it is a result (success or error) that appears on a page
  other than the one open. Banners that describe a page's state (their
  ``announce`` is off, like the Joins page's) are left out.
"""

from __future__ import annotations

import os
from typing import List

from PySide6.QtCore import QTimer

from cci_ui.widgets.sidebar import StepState
from cci_ui.widgets.status import StatusBanner, show_toast
from clinical_reporting import steps
from clinical_reporting.feedback import one_line
from clinical_reporting.ui.main_ui import APP_NAME

#: Message kinds that also show as a toast when raised off the open page.
#: (Warnings and progress stay in the status bar.)
TOAST_KINDS = frozenset({"success", "error"})
#: What follows each refresh, in this order (the pages that have them): the
#: marks on the fields that fix a problem, then the buttons they hold back.
MARKS = (
    "_mark_join_problems",
    "_mark_filter_problems",
    "_mark_rename_problems",
    "_mark_form_item_problems",
    "_refresh_run_availability",
    "_refresh_save_availability",
)


class NavigationMixin:
    """Behavior for the sidebar, header, status bar, and page changes."""

    def _init_navigation(self) -> None:
        """Follow page changes and status messages; show the report.

        Runs after the other behaviors have set up their state, which the
        refresh reads.
        """
        self.ui.shell.currentPageChanged.connect(self.on_page_changed)
        # Coalesces the refreshes asked for while the report changes.
        self._shell_refresh = QTimer(self)
        self._shell_refresh.setSingleShot(True)
        self._shell_refresh.setInterval(0)
        self._shell_refresh.timeout.connect(self._refresh_shell)
        # Banners showing a message, oldest first; the status bar shows the
        # newest.
        self._showing_banners: List[StatusBanner] = []
        for banner in self.ui.shell.findChildren(StatusBanner):
            if banner.announce:
                # A bound method: the connection doesn't keep the window alive.
                banner.messageChanged.connect(self._repeat_message)
        self._refresh_shell()

    def on_page_changed(self, key: str) -> None:
        """Apply the Data step just left, then build the preview on its page."""
        self.apply_data_steps()
        if key == steps.PREVIEW and self.report.data:
            self.preview_report()

    def _refresh_shell(self) -> None:
        """Bring the badges, header, title, status summary and marks up to date.

        The report is validated once here; the pages mark the fields that fix
        each problem from the issues kept (``_issues``, ``_issue_fields``),
        and Export to Excel and Save setting follow.
        """
        shell = self.ui.shell
        source, exported = self._input_file_path, self._last_export_path
        issues = self.report.validate()
        self._issues = issues
        self._issue_fields = steps.issues_by_field(issues)
        statuses = steps.step_statuses(
            self.report,
            source=os.path.basename(source) if source else None,
            additional_forms=len(self._additional_form_keys),
            exported_to=os.path.basename(exported) if exported else None,
            issues=issues,
            page_problems=self._page_problems,
        )
        for key, status in statuses.items():
            shell.sidebar.set_status(
                key, StepState(status.state), count=status.count, tip=status.tip
            )
        study = self.study_name
        loaded = bool(self.report.data)
        for key in steps.NEEDS_DATA:
            shell.page(key).show_empty_state(not loaded)
        if not loaded:
            # However the data went (the ZIP or the additional files removed).
            self._forget_preview()
        shell.set_context(study or ("" if loaded else steps.NO_DATA))
        self.setWindowTitle(f"{study} — {APP_NAME}" if study else APP_NAME)
        shell.status_bar.set_summary(steps.report_summary(self.report, study))
        for name in MARKS:
            mark = getattr(self, name, None)
            if callable(mark):
                mark()

    def _repeat_message(self) -> None:
        """Show the new message of the banner that sent it (maybe as a toast)."""
        banner = self.sender()
        if not isinstance(banner, StatusBanner):
            return  # Called directly, not by a banner's signal.
        if banner in self._showing_banners:
            self._showing_banners.remove(banner)
        if banner.text():
            self._showing_banners.append(banner)
        status_bar = self.ui.shell.status_bar
        if self._showing_banners:
            newest = self._showing_banners[-1]
            status_bar.show_message(one_line(newest.text()), newest.kind())
        else:
            status_bar.clear_message()

        page = self.ui.shell.current_page()
        on_open_page = page is not None and page.isAncestorOf(banner)
        if banner.text() and banner.kind() in TOAST_KINDS and not on_open_page:
            show_toast(self, one_line(banner.text()), banner.kind())
