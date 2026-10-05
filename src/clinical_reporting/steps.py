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
step's messages (:func:`additional_applied_message`, the constants, and the
``saved_names_*`` wording for the names a loaded setting saved for its
additional files; see :mod:`clinical_reporting.additional_names`).
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import (
    Collection,
    Dict,
    Iterable,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Sized,
    Tuple,
)

from clinical_reporting import feedback, report_columns
from clinical_reporting.additional_names import (
    BY_COLUMNS,
    BY_FILE_NAME,
    IgnoredName,
    SavedFileNames,
)
from clinical_reporting.models import qualify
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
#: The first entry of a file's Saved names dropdown: no saved names used.
SAVED_NAMES_NONE = "None"
#: The tooltip of a Saved names dropdown while there are none to pick.
SAVED_NAMES_UNAVAILABLE_TIP = (
    "No saved names to pick from. Start from a saved setting that has names "
    f"for additional files on {TITLES[SOURCE]}."
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
    """Items selected: the common items plus each form's items.

    (The report can have more columns: a later form's own copies of common
    items it doesn't join on, see :mod:`clinical_reporting.report_columns`.)
    """
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
    unjoined = report_columns.unjoined_common_items(report)
    if unjoined:
        names = [
            qualify(form, item) for form, items in unjoined.items() for item in items
        ]
        return feedback.info(
            "Forms keep their own values of common items they don't join on: "
            f"{feedback.short_list(names)}.",
            details="\n".join(names),
        )
    return None


def additional_applied_message(
    forms: Collection[str], ignored: Sequence[IgnoredName] = ()
) -> feedback.Message:
    """What applying the additional files did: the forms added (one per file).

    *ignored* are saved column names the files couldn't use (see
    :func:`clinical_reporting.additional_names.ignored_names`). They make
    the message a warning, though the forms were added all the same.
    """
    if not forms:
        return feedback.success("The additional forms were removed from the report.")
    added = ", ".join(sorted(forms))
    text = f"{_plural(len(forms), 'file')} applied. New forms: {added}."
    if ignored:
        return feedback.warning(
            f"{text} Saved column names ignored: {_lacking(ignored)}.",
            _ignored_details(ignored),
        )
    return feedback.success(text)


_MATCHED_BY = {BY_FILE_NAME: "by its file name", BY_COLUMNS: "by its columns"}


def _and_list(names: Sequence[str]) -> str:
    """*names* in a sentence: "a", "a and b", "a, b and c"."""
    if len(names) <= 1:
        return "".join(names)
    return f"{', '.join(names[:-1])} and {names[-1]}"


def _or_list(names: Sequence[str], shown: int = 5) -> str:
    """*names* as alternatives: "a", "a or b", "a, b or c", "…, e or 3 more"."""
    names = list(names)
    if len(names) > shown:
        names = [*names[:shown], f"{len(names) - shown} more"]
    if len(names) <= 1:
        return "".join(names)
    return f"{', '.join(names[:-1])} or {names[-1]}"


def _lacking(ignored: Sequence[IgnoredName], shown: int = 3) -> str:
    """The columns *ignored* names were saved for, by file.

    For example "lab.csv has no Visit Dt or ALT; pk.csv has no Conc", at
    most *shown* files of them.
    """
    # Files listed from two folders share a name; say each column once.
    by_file: Dict[str, Dict[str, None]] = {}
    for name in ignored:
        by_file.setdefault(name.file_name, {})[name.column] = None
    parts = [
        f"{file_name} has no {_or_list(list(columns))}"
        for file_name, columns in by_file.items()
    ]
    if len(parts) > shown:
        parts = [*parts[:shown], f"and {_plural(len(parts) - shown, 'more file')}"]
    return "; ".join(parts)


def _ignored_details(ignored: Sequence[IgnoredName]) -> str:
    """One line per ignored name: "lab.csv: Visit Dt → Visit Date"."""
    lines = (f"{name.file_name}: {name.column} → {name.new_name}" for name in ignored)
    return "\n".join(dict.fromkeys(lines))


def saved_names_label(entry: SavedFileNames) -> str:
    """A saved entry as a Saved names dropdown lists it: its form name, "LAB".

    An entry that only renames columns has no form name; its file name
    stands in. (A form name several entries share also gets the file name;
    see :func:`saved_names_labels`.)
    """
    return entry.form_name or entry.file_name


def saved_names_labels(entries: Sequence[SavedFileNames]) -> List[str]:
    """The Saved names dropdown's entries (see :func:`saved_names_label`).

    Entries with the same form name also show their file name, "LAB
    (lab_results.csv)", so entries saved for different files read apart.
    """
    labels = [saved_names_label(entry) for entry in entries]
    counts = Counter(labels)
    return [
        f"{label} ({entry.file_name})"
        if counts[label] > 1 and label != entry.file_name
        else label
        for label, entry in zip(labels, entries)
    ]


def saved_names_entry_tip(entry: SavedFileNames) -> str:
    """The tooltip of an entry in a Saved names dropdown: the file it was saved for."""
    return f"Saved for {entry.file_name}"


def saved_names_tip(
    entry: Optional[SavedFileNames] = None, by: Optional[str] = None
) -> str:
    """A Saved names dropdown's tooltip: the entry it shows, and why.

    *by* is how the entry was matched to the file
    (:attr:`clinical_reporting.additional_names.Match.by`); ``None`` when
    the user picked it.
    """
    if entry is None:
        return (
            "No saved names are used for this file. Pick an entry to fill in "
            "its form and column names."
        )
    if by == BY_FILE_NAME:
        return f"Picked because the file name matches {entry.file_name}."
    if by == BY_COLUMNS:
        return f"Picked because its columns match {entry.file_name}."
    return f"Using the names saved for {entry.file_name}."


def saved_names_filled_message(
    setting_name: str,
    picks: Sequence[Tuple[str, Optional[str]]],
    ignored: Sequence[IgnoredName] = (),
) -> feedback.Message:
    """What picking a loaded setting's saved names for the listed files did.

    *picks* are ``(file name, how it was matched)`` pairs. *ignored* are
    saved column names the files can't use (see
    :func:`clinical_reporting.additional_names.ignored_names`), which make
    the message a warning.
    """
    parts = [f"{name} {_MATCHED_BY.get(by, '')}".rstrip() for name, by in picks]
    text = (
        f"Saved names from “{setting_name}” picked for "
        f"{_plural(len(picks), 'file')}: {feedback.short_list(parts)}."
    )
    if ignored:
        return feedback.warning(
            f"{text} Some saved column names can't be used and will be ignored: "
            f"{_lacking(ignored)}. Check them, then Apply to report.",
            _ignored_details(ignored),
        )
    details = "\n".join(parts) if len(parts) > 5 else None
    return feedback.info(f"{text} Check them, then Apply to report.", details)


def saved_names_picked_message(
    entry: SavedFileNames, file_name: str, ignored: Sequence[IgnoredName] = ()
) -> feedback.Message:
    """What picking *entry* in *file_name*'s Saved names dropdown did.

    A warning when the file can't use some of the entry's column names
    (*ignored*).
    """
    name = saved_names_label(entry)
    if ignored:
        count = (
            "1 saved column name"
            if len(ignored) == 1
            else f"{len(ignored):,} saved column names"
        )
        return feedback.warning(
            f"Names from {name} filled in for {file_name}. {count} can't be "
            f"used and will be ignored: {_lacking(ignored)}. Check them, then "
            "Apply to report.",
            _ignored_details(ignored),
        )
    return feedback.info(
        f"Names from {name} filled in for {file_name}. Check them, then Apply "
        "to report."
    )


def saved_names_missing_message(
    setting_name: str, entries: Sequence[SavedFileNames]
) -> feedback.Message:
    """The files a loaded setting needs that aren't added yet (*entries*)."""
    names = [
        f"{entry.file_name} ({entry.form_name})" if entry.form_name else entry.file_name
        for entry in entries
    ]
    return feedback.warning(
        f"Still to add for “{setting_name}”: {feedback.short_list(names)}. "
        "Add them, and their saved names will be picked for you, or pick them in "
        "Saved names for files already added.",
        "\n".join(names) if len(names) > 5 else None,
    )


def saved_names_ignored_message(ignored: Sequence[IgnoredName]) -> feedback.Message:
    """The saved column names the listed files can't use (*ignored*).

    A standing warning: applying still adds the forms, without those names.
    """
    if len({(name.file_name, name.column) for name in ignored}) == 1:
        names, they, them = "A saved column name", "It's", "it"
    else:
        names, they, them = "Some saved column names", "They're", "them"
    forms = (
        "the form still applies"
        if len({name.file_name for name in ignored}) == 1
        else "the forms still apply"
    )
    return feedback.warning(
        f"{names} can't be used: {_lacking(ignored)}. {they} ignored; {forms} "
        f"without {them}.",
        _ignored_details(ignored),
    )


def saved_names_cleared_message(file_name: str) -> feedback.Message:
    """Picking None in *file_name*'s Saved names dropdown cleared its names."""
    return feedback.info(f"Saved names cleared for {file_name}.")


def saved_names_kept_message(file_name: str) -> feedback.Message:
    """Picking None left *file_name*'s names, which the user had changed."""
    return feedback.info(
        f"{file_name} no longer uses saved names. The names you changed stay."
    )


def saved_names_hint(
    missing_forms: Iterable[str],
    entries: Iterable[SavedFileNames],
    added: Collection[SavedFileNames] = (),
) -> Optional[str]:
    """For a loaded setting's "Missing forms" warning: the files that bring them.

    Says which additional files to add for the *missing_forms* that have
    saved names; for those whose file is already *added* (see
    ``AdditionalInputTabMixin._saved_names_added``), to check its form name
    and apply it. ``None`` when no missing form has saved names.
    """
    by_form = {entry.form_name: entry for entry in entries if entry.form_name}
    forms = [form for form in missing_forms if form in by_form]
    if not forms:
        return None
    where = TITLES[ADDITIONAL]
    to_add = [form for form in forms if by_form[form] not in added]
    to_apply = [form for form in forms if by_form[form] in added]
    hints = []
    if len(to_add) == 1:
        hints.append(
            f"{to_add[0]} comes from an additional file. Add "
            f"{by_form[to_add[0]].file_name} on {where}, and its saved names will "
            "be picked for you."
        )
    elif to_add:
        files = _and_list([by_form[form].file_name for form in to_add])
        hints.append(
            f"{_and_list(to_add)} come from additional files. Add {files} on "
            f"{where}, and their saved names will be picked for you."
        )
    if len(to_apply) == 1:
        hints.append(
            f"The file for {to_apply[0]} is added: check its form name on {where}, "
            "then Apply to report."
        )
    elif to_apply:
        hints.append(
            f"The files for {_and_list(to_apply)} are added: check their form "
            f"names on {where}, then Apply to report."
        )
    return " ".join(hints)


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
    "SAVED_NAMES_NONE",
    "SAVED_NAMES_UNAVAILABLE_TIP",
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
    "saved_names_cleared_message",
    "saved_names_entry_tip",
    "saved_names_filled_message",
    "saved_names_hint",
    "saved_names_ignored_message",
    "saved_names_kept_message",
    "saved_names_label",
    "saved_names_labels",
    "saved_names_missing_message",
    "saved_names_picked_message",
    "saved_names_tip",
    "selected_item_count",
    "source_summary",
    "step_statuses",
]
