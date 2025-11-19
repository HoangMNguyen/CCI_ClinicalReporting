"""Shared utilities for the Clinical Reporting main widget.

This module defines :class:`WidgetBaseMixin`, a collection of helper
methods that are used across multiple UI tabs.  The mixin centralizes the
state initialization and provides shared routines for working with forms,
common items, and per-form items.  Individual tab mixins import these
helpers to keep their logic narrowly focused on UI responsibilities
instead of duplicating low-level list management code.
"""

from __future__ import annotations

from typing import Iterable, Optional

from PySide6.QtWidgets import QAbstractItemView

from clinical_reporting.core.report import CLReport


class WidgetBaseMixin:
    """Common behavior shared by all widget tabs."""

    def _initialize_state(self) -> None:
        """Set up application state that is shared across tabs."""
        self.setWindowTitle("Clinical Reporting Tool")
        self.study_name = None
        self.report = CLReport()
        self.output_folder_name = None
        self.settings_directory = None

        # Cache confirmation labels so they can be updated from individual tabs
        # without repeatedly resolving attribute names on the UI form.
        self.label_run_confirmation = getattr(self.ui, "label_run_confirmation", None)
        self.label_save_confirmation = getattr(self.ui, "label_save_confirmation", None)
        self.label_output_folder = getattr(self.ui, "label_output_folder", None)
        self.label_setting = getattr(self.ui, "label_setting", None)
        if self.label_save_confirmation is None and hasattr(self.ui, "label_confirmation"):
            self.label_save_confirmation = self.ui.label_confirmation
        if self.label_run_confirmation is not None:
            self.label_run_confirmation.setText("")
        if self.label_save_confirmation is not None:
            self.label_save_confirmation.setText("")
        if self.label_setting is not None:
            self.label_setting.setText("")
        if self.label_save_confirmation is not None and not hasattr(self.ui, "label_save_confirmation"):
            self.ui.label_save_confirmation = self.label_save_confirmation
        
        # Disable settings directory selector until persistence is enabled.
        self.ui.pushButton_setting_location.setEnabled(False)

    # ------------------------------------------------------------------
    # Shared helpers used by multiple tabs

    def _after_form_selection_change(self) -> None:
        """Refresh dependent UI elements whenever selected forms change."""
        self.update_forms_ui()
        self.update_common_items_ui()
        self.update_form_dependent_ui()

    def _initialize_list_views(self) -> None:
        """Populate list widgets with their initial contents."""
        self.add_listWidget_form_available()
        self.add_listWidget_form_selected()
        self.add_listWidget_common_item_available()
        self.add_listWidget_common_item_selected()

    def update_all_ui(self) -> None:
        """Refresh every UI area in the correct dependency order."""
        self.update_forms_ui()
        self.update_common_items_ui()
        self.update_form_dependent_ui()

    def update_form_dependent_ui(self) -> None:
        """Refresh sections that rely on selected forms being up to date."""
        self.update_form_items_ui()
        self.update_join_table_ui()

    def update_items_dependent_ui(self) -> None:
        """Refresh features that depend on item selections."""
        self.update_rename_table()
        self.update_static_filter_table()
        self.update_dynamic_filter_table()
        self.update_items_order_list()

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
        """Safely update a ``QLabel`` if it exists."""
        if label is not None:
            label.setText(message or "")

    # ------------------------------------------------------------------
    # Table configuration helpers

    def _setup_tables(self) -> None:
        """Set up table widgets with consistent column sizing."""
        tables = [
            self.ui.tableWidget_join,
            self.ui.tableWidget_static_filter,
            self.ui.tableWidget_dynamic_filter,
            self.ui.tableWidget_rename,
        ]

        for table in tables:
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setSelectionMode(QAbstractItemView.SingleSelection)
            self._adjust_column_widths(table)
            table.horizontalHeader().sectionResized.connect(
                lambda index, old_size, new_size, t=table: self._adjust_column_widths(t)
            )

    def _adjust_column_widths(self, table) -> None:
        """Adjust table columns to evenly fill the available width."""
        if table.columnCount() == 0:
            return

        available_width = table.width()
        if not table.verticalHeader().isHidden():
            available_width -= table.verticalHeader().width()
        available_width -= 20
        if table.verticalScrollBar().isVisible():
            available_width -= table.verticalScrollBar().width()
        if table.showGrid():
            available_width -= table.columnCount() * 2

        column_width = max(50, available_width // table.columnCount())
        for col in range(table.columnCount()):
            table.setColumnWidth(col, column_width)

