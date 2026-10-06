"""Shared utilities for the Clinical Reporting main widget.

This module defines :class:`WidgetBaseMixin`, a collection of helper
methods that are used across multiple pages.  The mixin centralizes the
state initialization and provides shared routines for working with forms,
common items, and per-form items.  The per-page mixins use these
helpers to keep their logic narrowly focused on UI responsibilities
instead of duplicating low-level list management code.
"""

from __future__ import annotations

import re
import warnings
from typing import Iterable, Optional

from clinical_reporting.report import CLReport
from clinical_reporting.session import capture_selection, restore_selection
from clinical_reporting.settings_store import (
    LocalFolderStore,
    SettingsStore,
    default_settings_folder,
)
from clinical_reporting.ui.dialogs import show_settings_folder


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
        # without repeatedly resolving attribute names on the UI form.
        self.label_run_confirmation = getattr(self.ui, "label_run_confirmation", None)
        self.label_save_confirmation = getattr(self.ui, "label_save_confirmation", None)
        self.label_setting = getattr(self.ui, "label_setting", None)

        # Disable settings directory selector until persistence is enabled.
        self.ui.pushButton_setting_location.setEnabled(False)
        show_settings_folder(self, self._get_default_settings_directory())

    # ------------------------------------------------------------------
    # Shared helpers used by multiple pages

    def _initialize_list_views(self) -> None:
        """Populate list widgets with their initial contents."""
        self.add_listWidget_form_available()
        self.add_listWidget_form_selected()
        self.add_listWidget_common_item_available()
        self.add_listWidget_common_item_selected()

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
        windows without the navigation (the unit tests' partial windows).
        """
        refresh = getattr(self, "_shell_refresh", None)
        if refresh is not None:
            refresh.start()

    # ------------------------------------------------------------------
    # Selection state capture / restore
    #
    # Rebuilding the report's data (here: merging additional inputs) discards
    # the CLForm objects that hold the user's selections. The Qt-free logic
    # lives in :mod:`clinical_reporting.session`, which also uses it for the
    # cut-off reload and removing the input; these wrappers bind it to this
    # window's report.

    def _capture_selection_state(self) -> dict:
        """Snapshot current form/item/common/join selections for later restore."""
        return capture_selection(self.report)

    def _restore_selection_state(self, state: dict) -> None:
        """Re-apply a snapshot from :meth:`_capture_selection_state`."""
        restore_selection(self.report, state)

    # ------------------------------------------------------------------
    # Saved-settings storage (shared by the Source data and Preview & export pages)

    def _get_default_settings_directory(self) -> str:
        """Return the default folder used to store saved settings."""
        return str(default_settings_folder())

    def _settings_store(self) -> SettingsStore:
        """The store for the currently chosen settings folder."""
        folder = self.settings_directory or self._get_default_settings_directory()
        return LocalFolderStore(folder)

    def _apply_form_selection_action(self, action: str) -> bool:
        """Mutate report form selections based on the requested action."""
        if action == "select":
            selected_items = self.ui.listWidget_form_available.selectedItems()
            if not selected_items:
                return False
            for item in selected_items:
                self.report.add_selected_form(item.text())
            return True

        if action == "remove":
            selected_items = self.ui.listWidget_form_selected.selectedItems()
            if not selected_items:
                return False
            for item in selected_items:
                self.report.add_available_form(item.text())
            return True

        if action == "select_all":
            available_forms = self.report.get_available_forms_list()
            if not available_forms:
                return False
            self.report.add_all_selected_forms()
            return True

        if action == "remove_all":
            selected_forms = self.report.get_selected_forms_list()
            if not selected_forms:
                return False
            self.report.add_all_available_forms()
            return True

        raise ValueError(f"Unknown form selection action: {action}")

    def _toggle_common_item_selection(self, widget, *, selected: bool) -> bool:
        """Update common item state for all entries selected in ``widget``."""
        selected_items = widget.selectedItems()
        if not selected_items:
            return False

        for item in selected_items:
            self.report.set_common_item_state(item.text(), selected=selected)

        return True

    def _apply_common_item_action(self, action: str) -> bool:
        """Mutate common item selections using a shared implementation."""
        if action == "select":
            return self._toggle_common_item_selection(
                self.ui.listWidget_common_item_available, selected=True
            )

        if action == "remove":
            return self._toggle_common_item_selection(
                self.ui.listWidget_common_item_selected, selected=False
            )

        if action == "select_all":
            available_items = list(self.report.get_available_common_items())
            if not available_items:
                return False
            for item in available_items:
                self.report.set_common_item_state(item, selected=True)
            return True

        if action == "remove_all":
            selected_items = list(self.report.get_selected_common_items())
            if not selected_items:
                return False
            for item in selected_items:
                self.report.set_common_item_state(item, selected=False)
            return True

        raise ValueError(f"Unknown common item action: {action}")

    def _iter_form_item_pairs(self, widget) -> Iterable[tuple[str, str]]:
        """Yield ``(form_name, item_name)`` tuples from the widget selections."""
        for item in widget.selectedItems():
            item_text = item.text()
            if "." in item_text:
                yield item_text.split(".", 1)

    def _toggle_form_item_selection(self, widget, *, selected: bool) -> bool:
        """Update per-form item state for all entries selected in ``widget``."""
        changed = False
        for form_name, item_name in self._iter_form_item_pairs(widget):
            if form_name in self.report.selected_forms:
                self.report.selected_forms[form_name].set_form_item_state(
                    item_name, selected=selected
                )
                changed = True
        return changed

    def _apply_form_item_action(self, action: str) -> bool:
        """Mutate form item selections using a shared implementation."""
        if action == "select":
            return self._toggle_form_item_selection(
                self.ui.listWidget_form_item_available, selected=True
            )

        if action == "remove":
            return self._toggle_form_item_selection(
                self.ui.listWidget_form_item_selected, selected=False
            )

        if action == "select_all":
            changed = False
            for form_name in self.report.get_selected_forms_list():
                if form_name in self.report.selected_forms:
                    available_items = self.report.selected_forms[
                        form_name
                    ].get_available_form_items()
                    if not available_items:
                        continue
                    for item in available_items[:]:
                        self.report.selected_forms[form_name].set_form_item_state(
                            item, selected=True
                        )
                    changed = True
            return changed

        if action == "remove_all":
            changed = False
            for form_name in self.report.get_selected_forms_list():
                if form_name in self.report.selected_forms:
                    selected_items = self.report.selected_forms[
                        form_name
                    ].get_selected_form_items()
                    if not selected_items:
                        continue
                    for item in selected_items[:]:
                        self.report.selected_forms[form_name].set_form_item_state(
                            item, selected=False
                        )
                    changed = True
            return changed

        raise ValueError(f"Unknown form item action: {action}")

    def _set_label_text(self, label, message: Optional[str]) -> None:
        """Show *message* in a status label, if the label exists.

        Pass a :mod:`clinical_reporting.feedback` message (``feedback.error(…)``
        and so on) so the label can show how serious it is; ``""`` or ``None``
        clears it.
        Status banners read the kind and details from the message itself.
        """
        if label is not None:
            label.setText(message or "")

    def _compile_search_pattern(self, pattern_text: str) -> Optional[re.Pattern[str]]:
        """Compile a case-insensitive search regex; return ``None`` if empty/invalid."""
        if not pattern_text:
            return None

        try:
            return re.compile(pattern_text, flags=re.IGNORECASE)
        except re.error:
            return None

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
