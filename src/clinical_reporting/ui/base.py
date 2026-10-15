"""The window-level behavior mixin of the Clinical Reporting window.

:class:`WidgetBaseMixin` holds the window's shared state (set up in
``_initialize_state``), the refresh coordinators
(:meth:`~WidgetBaseMixin.update_all_ui` and the other ``update_*_ui``
methods here), which call the ``update_*`` refreshes the page modules in
:mod:`ui.pages` define, and small helpers more than one page uses: the
saved-settings folder and store, status labels, ``_report_changed``, and
quiet signal disconnects.
"""

from __future__ import annotations

import warnings
from typing import Collection, Dict, List, Optional, Sequence

from cci_ui.tasks import defer_if_busy
from clinical_reporting import session, steps
from clinical_reporting.report import CLReport
from clinical_reporting.settings_store import (
    LocalFolderStore,
    SettingsStore,
    default_settings_folder,
)
from clinical_reporting.stacking import StackedForm
from clinical_reporting.ui.dialogs import settings_folder, show_settings_folder
from clinical_reporting.validation import ReportValidationIssue

#: Each Data step's page: what applies its changes when the user leaves it,
#: and what says whether it has changes the report doesn't use yet.
_APPLY_STEPS = {
    steps.ADDITIONAL: "_apply_additional_step",
    steps.STACKED: "_apply_stacked_step",
    steps.COALESCED: "_apply_coalesced_step",
}
_UNAPPLIED_CHECKS = {
    steps.ADDITIONAL: "_has_unapplied_additional_inputs",
    steps.STACKED: "_has_unapplied_stacked_forms",
    steps.COALESCED: "_has_unapplied_coalesced_items",
}


class WidgetBaseMixin:
    """Common behavior shared by all pages."""

    def _initialize_state(self) -> None:
        """Set up application state that is shared across pages."""
        self.study_name = None
        self.report = CLReport()
        self.output_folder_name = None
        self._additional_input_directory: Optional[str] = None
        self.settings_directory = None
        self._last_loaded_setting_path: Optional[str] = None
        self._pending_saved_setting_reapply = False
        # Path of the currently loaded input ZIP and the cut-off date that was
        # applied when it was read, so the cut-off can be re-applied on change.
        self._input_file_path: Optional[str] = None
        self._applied_cut_off_date = None
        # (path, cut-off) of a reload that failed, so it isn't retried on
        # every focus change of the date field.
        self._failed_cut_off_reload = None
        # The file last exported, for the Preview & export step's badge.
        self._last_export_path: Optional[str] = None
        # True while update_all_ui coordinates a full refresh; narrower
        # helpers use it to skip refreshes the coordinator already covers.
        self._in_coordinated_refresh = False
        # The report's validation issues as of the last shell refresh, and
        # the same by the field each names: the pages mark their fields
        # from these (ui.navigation).
        self._issues: List[ReportValidationIssue] = []
        self._issue_fields: Dict[str, List[ReportValidationIssue]] = {}
        # Problems a page shows that aren't in the report (yet), by step, one
        # line each: they turn its badge red and stop the export.
        self._page_problems: Dict[str, List[str]] = {}

        # Cache confirmation labels so they can be updated from individual pages
        # without repeatedly resolving attribute names on ``self.ui``.
        self.label_run_confirmation = getattr(self.ui, "label_run_confirmation", None)
        self.label_save_confirmation = getattr(self.ui, "label_save_confirmation", None)
        self.label_setting = getattr(self.ui, "label_setting", None)

        show_settings_folder(self, self._get_default_settings_directory())

    # ------------------------------------------------------------------
    # Shared helpers used by multiple pages

    def update_all_ui(self) -> None:
        """Refresh every UI area in the correct dependency order.

        Single coordinator for operations that touch several UI areas at once
        (form or common-item selection changes, loading inputs or saved
        settings). The narrower ``update_*`` helpers refresh only their own
        widgets, so each list and table is rebuilt exactly once from here.
        The flag suppresses the join table's own refresh of the order/rename
        and filter tables during population; the final step rebuilds those
        tables once instead.
        """
        self._in_coordinated_refresh = True
        try:
            # The names additional files can't take follow the data.
            update_additional = getattr(self, "update_additional_input_ui", None)
            if update_additional is not None:
                update_additional()
            self.update_stacked_forms_ui()
            self.update_coalesced_items_ui()
            self.update_forms_ui()
            self.update_common_items_ui()
            self.update_form_dependent_ui()
        finally:
            self._in_coordinated_refresh = False
        self.update_items_dependent_ui()

    def update_form_dependent_ui(self) -> None:
        """Refresh sections that rely on selected forms being up to date."""
        self.update_form_items_ui()
        self.update_join_table_ui()

    def update_items_dependent_ui(self) -> None:
        """Refresh features that depend on item selections."""
        # Park renames/filters for deselected items (and restore re-selected
        # ones) before the tables are rebuilt from the report.
        self.report.sync_with_selection()
        self.update_order_rename_table()
        self.update_static_filter_table()
        self.update_dynamic_filter_table()
        self._report_changed()

    def _report_changed(self) -> None:
        """Call after changing the report: the sidebar badges and status bar follow.

        :meth:`update_all_ui` and :meth:`update_items_dependent_ui` call it;
        so must anything else that changes the report (filters, joins,
        renames, exports). Changes made together refresh once, when control
        returns to the event loop (see :mod:`ui.navigation`). Does nothing in
        windows without the navigation (the tests' partial windows).
        """
        refresh = getattr(self, "_shell_refresh", None)
        if refresh is not None:
            refresh.start()

    # ------------------------------------------------------------------
    # The Data steps (Additional input, Stacked forms, Coalesced items)

    def _set_page_problems(self, step: str, lines: List[str]) -> None:
        """Keep what *step*'s page shows as problems, one line each; refresh."""
        problems = getattr(self, "_page_problems", None)
        if problems is None:  # A partial window (tests).
            problems = self._page_problems = {}
        if lines:
            problems[step] = list(lines)
        else:
            problems.pop(step, None)
        self._report_changed()

    def _is_open(self, key: str) -> bool:
        """Whether the page of step *key* is the one shown.

        Windows without the shell (the tests' partial windows) count every
        page as open: their tests apply the steps themselves.
        """
        shell = getattr(self.ui, "shell", None)
        return shell is None or shell.current() == key

    def _has_unapplied(self, key: str) -> bool:
        """Whether Data step *key*'s page differs from what the report uses."""
        check = getattr(self, _UNAPPLIED_CHECKS[key], None)
        return bool(check()) if check is not None else False

    def _held_steps(self) -> List[str]:
        """The Data steps whose changes can't reach the report: they have problems."""
        problems = getattr(self, "_page_problems", {})
        return [
            key
            for key in steps.DATA_STEPS
            if problems.get(key) and self._has_unapplied(key)
        ]

    def apply_data_steps(self) -> None:
        """Bring the changes of every Data step that isn't open to the report.

        Called when the user leaves a page, and when a Data step changes
        while it isn't open (files that finish loading, a picked setting's
        saved names, a new Corelisting ZIP). Each step applies only when it
        has changes and no problems (see the pages' ``_apply_*_step``).
        """
        if defer_if_busy(self, self.apply_data_steps):
            return
        for key in steps.DATA_STEPS:
            apply = getattr(self, _APPLY_STEPS[key], None)
            if apply is not None and not self._is_open(key):
                apply()
        self._report_changed()

    def _drop_data_steps_without_input(
        self,
        removed: Collection[str] = (),
        built_stacked: Sequence[StackedForm] = (),
    ) -> None:
        """Drop the stacked forms and coalesced items an input removal left bare.

        Called right after an input is removed. With no input left at all (no
        Corelisting ZIP, no additional files listed) every one goes, from the
        pages and from the report, at once. Otherwise those made only from
        the *removed* forms go from the pages: a removed ZIP's forms, its
        report having had the stacked forms *built_stacked* (see
        :func:`clinical_reporting.session.without_removed_forms`).
        """
        stacked = list(getattr(self, "_stacked_drafts", ()))
        coalesced = list(getattr(self, "_coalesced_drafts", ()))
        no_input = not getattr(self, "_input_file_path", None) and not getattr(
            self, "additional_inputs", None
        )
        if no_input:
            kept_stacked, kept_coalesced = [], []
            # The report still has the files' forms until the user leaves
            # Additional input: what was made from them goes now.
            report_changed = bool(
                self.report.stacked_forms or self.report.coalesced_items
            )
            if self.report.coalesced_items:
                session.apply_coalesced_items(self.report, [])
            if self.report.stacked_forms:
                session.apply_stacked_forms(self.report, [])
        elif removed:
            kept_stacked, kept_coalesced = session.without_removed_forms(
                removed, stacked, coalesced, built_stacked
            )
            report_changed = False
        else:
            return
        replace_stacked = getattr(self, "_replace_stacked_drafts", None)
        if replace_stacked is not None and kept_stacked != stacked:
            replace_stacked(kept_stacked)
        replace_coalesced = getattr(self, "_replace_coalesced_drafts", None)
        if replace_coalesced is not None and kept_coalesced != coalesced:
            replace_coalesced(kept_coalesced)
        if report_changed:
            self.update_all_ui()

    # ------------------------------------------------------------------
    # Saved-settings storage (shared by the Source data and Preview & export pages)

    def _get_default_settings_directory(self) -> str:
        """Return the default folder used to store saved settings."""
        return str(default_settings_folder())

    def _settings_store(self) -> SettingsStore:
        """The store for the currently chosen settings folder."""
        folder = settings_folder(self)
        return LocalFolderStore(folder)

    def _set_label_text(self, label, message: Optional[str]) -> None:
        """Show *message* in a status label, if the label exists.

        Pass a :mod:`clinical_reporting.feedback` message (``feedback.error(…)``
        and so on) so the label can show how serious it is; ``""`` or ``None``
        clears it.
        Status banners read the kind and details from the message itself.
        """
        if label is not None:
            label.setText(message or "")

    @staticmethod
    def _safe_disconnect(signal, slot=None) -> None:
        """Disconnect a Qt signal without raising or warning when nothing is connected.

        PySide6 emits a ``RuntimeWarning`` (and may raise ``RuntimeError``) when
        ``disconnect`` is called on a signal that has no matching connection.
        That warning is routed through Python's ``warnings`` machinery, so a
        plain ``try/except`` cannot silence it. This helper swallows both the
        warning and the exception, keeping table repopulation quiet.

        Args:
            signal: The bound Qt signal to disconnect (e.g. ``table.cellChanged``).
            slot: Optional specific slot to disconnect; when omitted, all
                connections on ``signal`` are removed.
        """
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            try:
                if slot is None:
                    signal.disconnect()
                else:
                    signal.disconnect(slot)
            except RuntimeError, TypeError:
                pass
