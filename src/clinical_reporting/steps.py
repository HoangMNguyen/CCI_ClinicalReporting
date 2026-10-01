"""The report's steps and where each one stands (no Qt needed).

A report is built in ten steps, from loading the data to exporting it
(:data:`STEP_KEYS`, titled :data:`TITLES`). :func:`step_statuses` says, for
each step, what its sidebar badge shows: nothing, a count (forms selected,
filters added, ...), done, optional, or a problem. Problems come from
:func:`clinical_reporting.validation.validate_report` by issue code
(:data:`ISSUE_STEPS`), so every front end points the user to the step that
fixes each one. The other functions word what the steps show:
:func:`report_summary` (the line under the window), :func:`source_summary`,
:func:`preview_caption`, :func:`joins_message`, and the Additional input
step's messages (:func:`additional_applied_message` and the constants).
"""

from __future__ import annotations

from datetime import datetime
from typing import (
    Collection,
    Dict,
    Iterable,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Sized,
)

from clinical_reporting import feedback
from clinical_reporting.validation import ReportValidationIssue

# The steps, in order. The desktop pages use these as their keys.
SOURCE = "source"
ADDITIONAL = "additional"
FORMS = "forms"
COMMON = "common"
FORM_ITEMS = "formitems"
FILTERS = "filters"
JOINS = "joins"
COMPARISONS = "comparisons"
ORDER = "order"
PREVIEW = "preview"
STEP_KEYS = (
    SOURCE,
    ADDITIONAL,
    FORMS,
    COMMON,
    FORM_ITEMS,
    FILTERS,
    JOINS,
    COMPARISONS,
    ORDER,
    PREVIEW,
)

#: Each step's title, as its page and the sidebar show it.
TITLES = {
    SOURCE: "Source data",
    ADDITIONAL: "Additional input",
    FORMS: "Forms",
    COMMON: "Common items",
    FORM_ITEMS: "Form items",
    FILTERS: "Filters",
    JOINS: "Joins",
    COMPARISONS: "Comparisons",
    ORDER: "Order & rename",
    PREVIEW: "Preview & export",
}
#: Steps with nothing to show until data is loaded; their pages say so
#: (:data:`NO_DATA`, :data:`NO_DATA_HINT`) instead.
NEEDS_DATA = frozenset(STEP_KEYS) - {SOURCE, ADDITIONAL}

#: What the window says before any data is loaded.
NO_DATA = "No data loaded"
#: How to load some.
NO_DATA_HINT = f"Choose a Corelisting ZIP on {TITLES[SOURCE]} to start a report."

#: The Additional input step, applied with no files.
ADD_FILES_FIRST = feedback.warning("Add at least one file first.")
#: The Additional input step, once a new Corelisting ZIP dropped its forms.
APPLY_ADDITIONAL_AGAIN = feedback.info(
    "The new Corelisting ZIP started a new report. Apply the files again to add "
    "their forms to it."
)

# What a badge shows (the values of cci_ui's StepState).
NONE = "none"
DONE = "done"
ERROR = "error"
OPTIONAL = "optional"

#: The step that fixes each validation issue. Filter items are checked in
#: both kinds of filter, so those two codes go by the issue's field instead
#: (see :func:`issue_step`). ``no_data`` and ``no_selected_forms`` have no
#: step: the badges already show that nothing is loaded or selected.
ISSUE_STEPS = {
    "missing_form": FORMS,
    "invalid_form_name": FORMS,
    "duplicate_common_item": COMMON,
    "missing_common_item": COMMON,
    "duplicate_form_item": FORM_ITEMS,
    "missing_form_item": FORM_ITEMS,
    "form_has_no_columns": FORM_ITEMS,
    "invalid_join_order": JOINS,
    "duplicate_join_order": JOINS,
    "duplicate_join_item": JOINS,
    "missing_join_item": JOINS,
    "join_item_not_common": JOINS,
    "missing_join_items": JOINS,
    "invalid_join_how": JOINS,
    "invalid_static_filter": FILTERS,
    "invalid_static_operator": FILTERS,
    "invalid_dynamic_filter": COMPARISONS,
    "invalid_dynamic_operator": COMPARISONS,
    "unknown_rename_item": ORDER,
    "invalid_output_name": ORDER,
    "duplicate_output_name": ORDER,
    "unknown_order_item": ORDER,
}
#: Issues that belong to a filter step, found by their field.
FILTER_ITEM_ISSUE_CODES = frozenset({"ambiguous_filter_item", "missing_filter_item"})
#: Issues no step fixes (see :data:`ISSUE_STEPS`).
UNPLACED_ISSUE_CODES = frozenset({"no_data", "no_selected_forms"})


class StepStatus(NamedTuple):
    """What one step's badge shows, and the tooltip that explains it."""

    state: str = NONE
    count: Optional[int] = None
    tip: str = ""


def issue_step(issue: ReportValidationIssue) -> Optional[str]:
    """The step where *issue* is fixed, or ``None`` if no single step is."""
    if issue.code in FILTER_ITEM_ISSUE_CODES:
        field = issue.field or ""
        if field.startswith("static_filter_items"):
            return FILTERS
        if field.startswith("dynamic_filter_items"):
            return COMPARISONS
        return None
    return ISSUE_STEPS.get(issue.code)


_MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)  # fmt: skip


def _plural(count: int, word: str) -> str:
    return f"{count:,} {word}" if count == 1 else f"{count:,} {word}s"


def _problems(issues: List[ReportValidationIssue]) -> StepStatus:
    tip = issues[0].message if len(issues) == 1 else _plural(len(issues), "problem")
    return StepStatus(ERROR, tip=tip)


def _counted(count: int, tip: str) -> StepStatus:
    """A count badge, or no badge when there are none yet."""
    return StepStatus(count=count, tip=tip) if count else StepStatus()


def selected_item_count(report) -> int:
    """Columns the report will have: common items plus each form's items."""
    forms = (report.selected_forms or {}).values()
    return len(report.selected_common_items or []) + sum(
        len(form.get_selected_form_items()) for form in forms
    )


def _renamed_count(report) -> int:
    return sum(
        1 for original, new in (report.rename_dict or {}).items() if new != original
    )


def step_statuses(
    report,
    *,
    source: Optional[str] = None,
    additional_forms: int = 0,
    exported_to: Optional[str] = None,
) -> Dict[str, StepStatus]:
    """The badge of every step, keyed by step.

    Args:
        report: The report being built (a :class:`~clinical_reporting.CLReport`).
        source: Name of the loaded Corelisting export, if one is loaded.
        additional_forms: How many forms the additional input added.
        exported_to: Name of the file last exported for this data, if any
            (changes made since don't undo the badge).
    """
    statuses = {key: StepStatus() for key in STEP_KEYS}
    statuses[ADDITIONAL] = (
        StepStatus(DONE, tip=f"{_plural(additional_forms, 'form')} added")
        if additional_forms
        else StepStatus(OPTIONAL)
    )
    if source:
        statuses[SOURCE] = StepStatus(DONE, tip=f"Loaded {source}")
    if not report.data:
        return statuses

    selected_forms = report.selected_forms or {}
    statuses[FORMS] = StepStatus(
        count=len(selected_forms), tip=f"{len(selected_forms)} selected"
    )
    common = len(report.selected_common_items or [])
    statuses[COMMON] = StepStatus(count=common, tip=f"{common} selected")
    form_items = selected_item_count(report) - common
    statuses[FORM_ITEMS] = StepStatus(count=form_items, tip=f"{form_items} selected")
    filters = len(report.static_filter_items or [])
    statuses[FILTERS] = _counted(filters, _plural(filters, "filter"))
    comparisons = len(report.dynamic_filter_items or [])
    statuses[COMPARISONS] = _counted(comparisons, _plural(comparisons, "comparison"))
    renamed = _renamed_count(report)
    statuses[ORDER] = _counted(renamed, f"{renamed} renamed")
    if len(selected_forms) > 1:
        statuses[JOINS] = StepStatus(DONE, tip="Ready")
    elif selected_forms:
        statuses[JOINS] = StepStatus(tip="Not needed for one form")
    if exported_to:
        statuses[PREVIEW] = StepStatus(DONE, tip=f"Last exported {exported_to}")

    for step, issues in _issues_by_step(report.validate()).items():
        statuses[step] = _problems(issues)
    return statuses


def _issues_by_step(
    issues: Iterable[ReportValidationIssue],
) -> Dict[str, List[ReportValidationIssue]]:
    by_step: Dict[str, List[ReportValidationIssue]] = {}
    for issue in issues:
        step = issue_step(issue)
        if step is not None:
            by_step.setdefault(step, []).append(issue)
    return by_step


def report_summary(report, study_name: Optional[str] = None) -> str:
    """One line about the report, e.g. "DEMO01 · 3 forms · 12 items · 1 filter"."""
    if not report.data:
        return f"{NO_DATA} · choose a Corelisting ZIP on {TITLES[SOURCE]}"
    parts = [study_name] if study_name else []
    parts += [
        _plural(len(report.selected_forms or {}), "form"),
        _plural(selected_item_count(report), "item"),
        _plural(len(report.static_filter_items or []), "filter"),
        _plural(len(report.dynamic_filter_items or []), "comparison"),
    ]
    return " · ".join(parts)


def source_summary(data: Mapping[str, Sized], read_at: datetime) -> str:
    """What was read from the Corelisting ZIP, and when.

    For example "18 forms · 2,431 rows · read at 10:12 on 30 Sep"; *data*
    maps each form to its rows. (The date, not "today": the text stays on
    screen past midnight.)
    """
    forms = _plural(len(data), "form")
    rows = _plural(sum(len(frame) for frame in data.values()), "row")
    month = _MONTHS[read_at.month - 1]  # Not %b: that follows the locale.
    return f"{forms} · {rows} · read at {read_at:%H:%M} on {read_at.day} {month}"


def preview_caption(rows: int, columns: int) -> str:
    """The size of a preview, e.g. "1,284 rows · 42 columns"."""
    return f"{_plural(rows, 'row')} · {_plural(columns, 'column')}"


def joins_message(report) -> Optional[feedback.Message]:
    """What the Joins step says about the report's joins, if anything."""
    issues = [issue for issue in report.validate() if issue_step(issue) == JOINS]
    if issues:
        problems = " ".join(issue.message for issue in issues)
        return feedback.error(
            f"{problems} The report can't be exported until this is fixed."
        )
    if len(report.selected_forms or {}) < 2:
        return feedback.info("Joins apply when two or more forms are selected.")
    return None


def additional_applied_message(forms: Collection[str]) -> feedback.Message:
    """What applying the additional files did: the forms added (one per file)."""
    if not forms:
        return feedback.success("The additional forms were removed from the report.")
    added = ", ".join(sorted(forms))
    return feedback.success(
        f"{_plural(len(forms), 'file')} applied. New forms: {added}."
    )


__all__ = [
    "ADDITIONAL",
    "ADD_FILES_FIRST",
    "APPLY_ADDITIONAL_AGAIN",
    "COMMON",
    "COMPARISONS",
    "DONE",
    "ERROR",
    "FILTERS",
    "FILTER_ITEM_ISSUE_CODES",
    "FORMS",
    "FORM_ITEMS",
    "ISSUE_STEPS",
    "JOINS",
    "NEEDS_DATA",
    "NONE",
    "NO_DATA",
    "NO_DATA_HINT",
    "OPTIONAL",
    "ORDER",
    "PREVIEW",
    "SOURCE",
    "STEP_KEYS",
    "TITLES",
    "UNPLACED_ISSUE_CODES",
    "StepStatus",
    "additional_applied_message",
    "issue_step",
    "joins_message",
    "preview_caption",
    "report_summary",
    "selected_item_count",
    "source_summary",
    "step_statuses",
]
