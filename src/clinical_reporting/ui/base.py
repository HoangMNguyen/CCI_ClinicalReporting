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
from typing import Optional

from clinical_reporting.report import CLReport
from clinical_reporting.settings_store import (
    LocalFolderStore,
    SettingsStore,
    default_settings_folder,
)
from clinical_reporting.ui.dialogs import settings_folder, show_settings_folder


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
