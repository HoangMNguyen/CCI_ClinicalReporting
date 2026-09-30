"""What happens to a report when the user acts, independent of any UI.

Front ends (the PySide6 desktop app today, possibly a web app later) collect
input and show results; the decisions about how the report changes live here
so every front end shares them. This module must never import Qt.

It currently holds the selection snapshot and restore used whenever a
report's data is rebuilt: changing the cut-off date, removing the
Corelisting input, or applying additional inputs. Rebuilding creates fresh
``CLForm`` objects, so the user's selections are captured first and the ones
that still exist are re-applied afterwards.
"""

from __future__ import annotations

from typing import Any, Dict

from clinical_reporting.report import CLReport


def capture_selection(report: CLReport) -> Dict[str, Any]:
    """Snapshot the form, item, common-item, and join selections of *report*."""
    selected_forms = getattr(report, "selected_forms", {})
    return {
        "forms": set(report.get_selected_forms_list()),
        "common": set(getattr(report, "selected_common_items", [])),
        "form_items": {
            form: set(cl_form.get_selected_form_items())
            for form, cl_form in selected_forms.items()
        },
        "join": {
            form: {
                "items": list(cl_form.get_join_items()),
                "order": cl_form.get_join_order(),
                "how": cl_form.get_join_how(),
            }
            for form, cl_form in selected_forms.items()
        },
    }


def restore_selection(report: CLReport, state: Dict[str, Any]) -> None:
    """Re-apply a :func:`capture_selection` snapshot to a rebuilt *report*.

    Only selections that still exist in the rebuilt report are restored;
    anything missing is dropped. ``Subject`` is always selected when present.
    """
    # Re-select previously selected forms when they still exist.
    for form in state.get("forms", set()):
        if form in report.available_forms:
            report.add_selected_form(form)

    # Re-select form items that are still available on their forms.
    for form_name, items in state.get("form_items", {}).items():
        if form_name not in report.selected_forms:
            continue
        cl_form = report.selected_forms[form_name]
        available_items = set(cl_form.get_available_form_items())
        for item in items:
            if item in available_items:
                cl_form.set_form_item_state(item, selected=True)

    # Re-identify common items; always include Subject when present.
    report.selected_common_items = []
    report.available_common_items = list(report.static_available_common_items)
    for common_item in state.get("common", set()):
        if common_item in report.static_available_common_items:
            report.set_common_item_state(common_item, selected=True)
    if "Subject" in getattr(report, "static_available_common_items", []):
        report.set_common_item_state("Subject", selected=True)

    # Restore join configuration for forms that still exist, dropping any
    # join items that are no longer valid selected common items.
    valid_common = set(report.get_selected_common_items())
    for form_name, join_config in state.get("join", {}).items():
        if form_name not in report.selected_forms:
            continue
        items = [item for item in join_config["items"] if item in valid_common]
        report.update_join_items(
            form_name, items, join_config["order"], join_config["how"]
        )


__all__ = ["capture_selection", "restore_selection"]
