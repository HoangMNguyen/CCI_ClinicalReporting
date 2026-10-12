"""What happens to a report when the user acts, independent of any UI.

Front ends (the PySide6 desktop app today, possibly a web app later) collect
input and show results; the decisions about how the report changes live here
so every front end shares them. This module must never import Qt.

It holds:

- The selection snapshot and restore used whenever a report's data is
  rebuilt: changing the cut-off date, removing the Corelisting input,
  applying additional inputs, or applying stacked forms. Rebuilding creates
  fresh ``CLForm`` objects, so the user's selections are captured first and
  the ones that still exist are re-applied afterwards.
- Starting a report from Corelisting data and swapping that data out.
- Applying a saved setting (:func:`apply_saved_setting`): its selections are
  lined up with the report's data, and its joins, renames, filters and
  column order are tidied to match.
- Merging additional inputs into a report (:func:`apply_additional_inputs`):
  each file becomes a form named as given or after the file, replacing the
  forms an earlier merge added; :class:`AppliedInputs` says what was added.
- Building and exporting the report, the slow part, written so a front end
  can run it off its main thread. (Reading files is :mod:`clinical_reporting.data`.)

Threading: :func:`build_report` and :func:`export_report` change no report,
so a front end may run them in the background, provided nothing changes the
report they read meanwhile (the desktop app blocks its window). Functions
that change a report run on the main thread.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Collection, Dict, List, Mapping, Optional, Sequence, Tuple

import pandas as pd

from clinical_reporting.data import build_additional_data_map
from clinical_reporting.export import write_xlsx
from clinical_reporting.models import SUBJECT_COLUMN
from clinical_reporting.report import CLReport
from clinical_reporting.stacking import StackedForm


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
        "join": report.get_join_list_dict(),
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
    if SUBJECT_COLUMN in getattr(report, "static_available_common_items", []):
        report.set_common_item_state(SUBJECT_COLUMN, selected=True)

    # Restore join configuration for forms that still exist, dropping any
    # join items that are no longer valid selected common items. All in one
    # call: in between, a form's FORM.item columns would be missing and lose
    # their place in a customized column order.
    valid_common = set(report.get_selected_common_items())
    joins = []
    for form_name, join_config in state.get("join", {}).items():
        if form_name not in report.selected_forms:
            continue
        items = [item for item in join_config["items"] if item in valid_common]
        joins.append((form_name, items, join_config["order"], join_config["how"]))
    report.update_join_list(joins)


def new_report(study_name: Optional[str], data: Dict[str, pd.DataFrame]) -> CLReport:
    """A fresh report over *data*, as right after opening a Corelisting ZIP.

    ``Subject`` starts selected.
    """
    report = CLReport()
    report.set_study_name(study_name)
    report.set_data(data)
    report.set_common_item_state(SUBJECT_COLUMN, selected=True)
    return report


def _additional_forms(
    report: CLReport, additional_keys: Collection[str]
) -> Dict[str, pd.DataFrame]:
    data = getattr(report, "data", {}) or {}
    return {key: value for key, value in data.items() if key in additional_keys}


def replace_base_data(
    report: CLReport,
    base_data: Dict[str, pd.DataFrame],
    additional_keys: Collection[str],
) -> None:
    """Swap *report*'s Corelisting forms for *base_data* (e.g. a new cut-off).

    Forms named in *additional_keys* (merged in from additional inputs) stay,
    and the selections that still exist are restored.
    """
    state = capture_selection(report)
    report.set_data({**base_data, **_additional_forms(report, additional_keys)})
    restore_selection(report, state)


def apply_stacked_forms(report: CLReport, stacked_forms: Sequence[StackedForm]) -> None:
    """Apply *stacked_forms* to *report*, keeping the selections that still exist.

    The report's data is rebuilt with them (see
    :meth:`~clinical_reporting.report.CLReport.set_stacked_forms`).
    """
    state = capture_selection(report)
    report.set_stacked_forms(stacked_forms)
    restore_selection(report, state)


def apply_saved_setting(
    report: CLReport, settings: Mapping[str, Any]
) -> Dict[str, List[str]]:
    """Apply the saved setting *settings* to *report*, as every front end does.

    The setting's selections are read and lined up with the report's data; a
    setting with no study name keeps the report's. The joins are tidied
    (:meth:`~clinical_reporting.report.CLReport.normalize_joins`), and the
    renames, filters and column order follow the selection. Returns what the
    setting needs that the data lacks, ``{"forms": [...], "items": [...]}``
    (see :meth:`~clinical_reporting.report.CLReport.reconcile_with_current_data`).
    """
    previous = report.study_name
    report.load_setting_from_dict(dict(settings))
    report.set_study_name(settings.get("study_name") or previous)
    missing = report.reconcile_with_current_data()
    report.normalize_joins()
    report.sync_with_selection()
    report.update_selected_items_order_list()
    return missing


@dataclass(frozen=True, eq=False)
class AppliedInputs:
    """What :func:`apply_additional_inputs` added to a report.

    ``forms`` are the forms made from the additional files, by form name;
    ``signature`` is each one's column names, to tell whether a later apply
    changed anything.
    """

    forms: Dict[str, pd.DataFrame]
    signature: Dict[str, Tuple[str, ...]]


def apply_additional_inputs(
    report: CLReport,
    inputs: Mapping[str, pd.DataFrame],
    form_names: Mapping[str, str],
    column_names: Mapping[Tuple[str, str], str],
    previous_keys: Collection[str] = (),
) -> AppliedInputs:
    """Merge the additional files *inputs* (``{path: frame}``) into *report*.

    Each file becomes a form named by *form_names* (else its file name), with
    its columns renamed by *column_names* (``{(path, column): name}``; see
    :func:`clinical_reporting.data.build_additional_data_map`). The forms an
    earlier apply added (*previous_keys*) are replaced. The report's data is
    rebuilt, so the caller restores the selections it wants to keep. Check
    the names first (:func:`clinical_reporting.steps.additional_form_names_message`).
    """
    base = {
        key: frame
        for key, frame in report.loaded_data.items()
        if key not in previous_keys
    }
    extra = build_additional_data_map(inputs, form_names, column_names)
    report.set_data({**base, **extra})
    return AppliedInputs(
        extra,
        {
            name: tuple(str(column) for column in frame.columns)
            for name, frame in extra.items()
        },
    )


def without_base_data(report: CLReport, additional_keys: Collection[str]) -> CLReport:
    """A fresh report holding only *report*'s additional-input forms.

    Used when the Corelisting input is removed. Starting over drops all
    filters, ordering and renames, including those on the remaining forms;
    only the selections on the remaining forms come back.
    """
    remaining = _additional_forms(report, additional_keys)
    fresh = CLReport()
    if remaining:
        state = capture_selection(report)
        fresh.set_data(remaining)
        restore_selection(fresh, state)
    return fresh


def build_report(report: CLReport) -> Optional[pd.DataFrame]:
    """Run *report* and return its rows, or ``None`` if nothing matched.

    Raises :class:`~clinical_reporting.validation.ReportValidationError` when
    the selections can't produce a report.
    """
    result = report.create_report()
    if result is None or result.empty:
        return None
    return result.reset_index(drop=True)


def export_report(report: CLReport, file_path: str) -> Optional[str]:
    """Build *report* and write it to *file_path* as a styled Excel file.

    Returns *file_path*, or ``None`` (and writes nothing) if nothing matched.
    """
    result = build_report(report)
    if result is None:
        return None
    write_xlsx(result, file_path)
    return file_path


__all__ = [
    "AppliedInputs",
    "apply_additional_inputs",
    "apply_saved_setting",
    "apply_stacked_forms",
    "build_report",
    "capture_selection",
    "export_report",
    "new_report",
    "replace_base_data",
    "restore_selection",
    "without_base_data",
]
