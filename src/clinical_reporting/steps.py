"""The report's steps and where each one stands (no Qt needed).

A report is built in eleven steps, from loading the data to exporting it
(:data:`STEP_KEYS`, titled :data:`TITLES`). :func:`step_statuses` says, for
each step, what its sidebar badge shows: nothing, a count (forms selected,
filters added, ...), done, optional, a warning, or a problem. Problems come
from :func:`clinical_reporting.validation.validate_report` by issue code
(:data:`ISSUE_STEPS`), and from the pages themselves (a Data step's changes
that can't reach the report yet), so every front end points the user to the
step that fixes each one (:func:`cannot_run_message`). The other functions
word what the steps show: :func:`report_summary` (the line under the
window), :func:`source_summary`, :func:`setting_missing_lines` (what a loaded
setting needs that the data lacks), :func:`preview_caption`,
:func:`joins_message`, the Additional input step's messages
(:func:`additional_applied_message`, :func:`additional_name_problems`,
:func:`additional_form_names_message`, and the ``saved_names_*`` wording
for the names a loaded setting saved for its additional files; see
:mod:`clinical_reporting.additional_names`), the Stacked forms step's (the
``stacked_*`` ones; see :mod:`clinical_reporting.stacking`), and the
Coalesced items step's (the ``coalesced_*`` ones; see
:mod:`clinical_reporting.coalescing`).
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
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

from clinical_reporting import coalescing, feedback, report_columns
from clinical_reporting.additional_names import (
    BY_COLUMNS,
    BY_FILE_NAME,
    IgnoredName,
    SavedFileNames,
)
from clinical_reporting.coalescing import CoalescedItem, Outcome
from clinical_reporting.models import (
    FORM_ITEM_SEPARATOR,
    is_qualified,
    qualify,
    split_qualified,
)
from clinical_reporting.stacking import Match, MatchedItem, StackedForm, layout
from clinical_reporting.validation import CANNOT_RUN_PREFIX, ReportValidationIssue

# The steps, in order. The desktop pages use these as their keys.
SOURCE = "source"
ADDITIONAL = "additional"
STACKED = "stacked"
COALESCED = "coalesced"
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
    STACKED,
    COALESCED,
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
    STACKED: "Stacked forms",
    COALESCED: "Coalesced items",
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
#: The steps that change the report's data. Each reaches the report when the
#: user leaves it; one with problems is held (nothing from it is used).
DATA_STEPS = (ADDITIONAL, STACKED, COALESCED)

#: What the window says before any data is loaded.
NO_DATA = "No data loaded"
#: How to load some.
NO_DATA_HINT = f"Choose a Corelisting ZIP on {TITLES[SOURCE]} to start a report."

#: How names filled in on Additional input end their message.
NAMES_USED_ON_LEAVING = "Check them; they're used when you go to another step."
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
WARNING = "warning"
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
    "stacked_form_name_clash": STACKED,
    "stacked_form_conflict": STACKED,
    "coalesced_item_conflict": COALESCED,
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


def row_count(count: int) -> str:
    """A number of rows as the pages say it: "1 row", "1,514 rows"."""
    return _plural(count, "row")


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
    issues: Optional[Sequence[ReportValidationIssue]] = None,
    page_problems: Optional[Mapping[str, Sequence[str]]] = None,
) -> Dict[str, StepStatus]:
    """The badge of every step, keyed by step.

    Args:
        report: The report being built (a :class:`~clinical_reporting.CLReport`).
        source: Name of the loaded Corelisting export, if one is loaded.
        additional_forms: How many forms the additional input added.
        exported_to: Name of the file last exported for this data, if any
            (changes made since don't undo the badge).
        issues: The report's validation issues, when the caller has them
            already (else the report is validated here).
        page_problems: Problems a page shows that aren't in the report yet,
            by step, one line each; a step with any shows them as its problem.
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
        return _with_page_problems(statuses, page_problems)

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
    statuses[STACKED] = _stacked_status(report)
    statuses[COALESCED] = _coalesced_status(report)
    if len(selected_forms) > 1:
        statuses[JOINS] = StepStatus(DONE, tip="Ready")
    elif selected_forms:
        statuses[JOINS] = StepStatus(tip="Not needed for one form")
    if exported_to:
        statuses[PREVIEW] = StepStatus(DONE, tip=f"Last exported {exported_to}")

    found = report.validate() if issues is None else issues
    for step, step_issues in _issues_by_step(found).items():
        statuses[step] = _problems(step_issues)
    return _with_page_problems(statuses, page_problems)


def _with_page_problems(
    statuses: Dict[str, StepStatus],
    page_problems: Optional[Mapping[str, Sequence[str]]],
) -> Dict[str, StepStatus]:
    """*statuses*, each step with page problems showing them instead."""
    for step, lines in (page_problems or {}).items():
        if lines:
            tip = lines[0] if len(lines) == 1 else _plural(len(lines), "problem")
            statuses[step] = StepStatus(ERROR, tip=tip)
    return statuses


def issues_by_field(
    issues: Iterable[ReportValidationIssue],
) -> Dict[str, List[ReportValidationIssue]]:
    """*issues* by the field each names, in order (those without a field left out).

    The pages mark each field with the messages found under it.
    """
    by_field: Dict[str, List[ReportValidationIssue]] = {}
    for issue in issues:
        if issue.field:
            by_field.setdefault(issue.field, []).append(issue)
    return by_field


def cannot_run_message(
    issues: Iterable[ReportValidationIssue],
    page_problems: Optional[Mapping[str, Sequence[str]]] = None,
) -> Optional[feedback.Message]:
    """What stops the report from running, naming the steps to fix, or ``None``.

    For example "Cannot run: Fix Filters and Joins first." Problems no step
    fixes are said as they are ("Cannot run: Select at least one form before
    running."). *page_problems* are the pages' own problems by step (see
    :func:`step_statuses`); the details list every problem by its step.
    """
    issues = list(issues)
    page_problems = page_problems or {}
    by_step = _issues_by_step(issues)
    unplaced = [issue.message for issue in issues if issue_step(issue) is None]
    to_fix = [key for key in STEP_KEYS if page_problems.get(key) or by_step.get(key)]
    if not to_fix and not unplaced:
        return None
    titles = [TITLES[key] for key in to_fix]
    parts = [*unplaced, *([f"Fix {feedback.and_list(titles)} first."] if to_fix else [])]
    details = "\n".join(
        f"{TITLES[key]}: {line}"
        for key in to_fix
        for line in [
            *page_problems.get(key, ()),
            *(issue.message for issue in by_step.get(key, ())),
        ]
    )
    return feedback.warning(f"{CANNOT_RUN_PREFIX} " + " ".join(parts), details or None)


def _stacked_status(report) -> StepStatus:
    """The Stacked forms badge: warning, done or optional (validation aside)."""
    missing = stacked_missing_message(report)
    if missing:
        return StepStatus(WARNING, tip=str(missing))
    if report.stacked_forms:
        return StepStatus(DONE, tip=_plural(len(report.stacked_forms), "stacked form"))
    return StepStatus(OPTIONAL)


def _coalesced_status(report) -> StepStatus:
    """The Coalesced items badge: warning, done or optional (validation aside)."""
    missing = coalesced_missing_message(report)
    if missing:
        return StepStatus(WARNING, tip=str(missing))
    if report.coalesced_items:
        count = len(report.coalesced_items)
        return StepStatus(DONE, tip=_plural(count, "coalesced item"))
    return StepStatus(OPTIONAL)


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
    """Why the Joins step has no joins to set, or which columns it adds, if any."""
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
    """What reaching the report did for the additional files: the forms added.

    One form per file. *ignored* are saved column names the files couldn't
    use (see :func:`clinical_reporting.additional_names.ignored_names`). They
    make the message a warning, though the forms were added all the same.
    """
    if not forms:
        return feedback.success(
            f"{TITLES[ADDITIONAL]}: the additional forms were removed from the report."
        )
    added = ", ".join(sorted(forms))
    text = (
        f"{TITLES[ADDITIONAL]} updated: {_plural(len(forms), 'file')} added to the "
        f"report. New forms: {added}."
    )
    if ignored:
        return feedback.warning(
            f"{text} Saved column names ignored: {_lacking(ignored)}.",
            _ignored_details(ignored),
        )
    return feedback.success(text)


def additional_name_problems(
    name_map: Mapping[str, str],
    typed: Mapping[str, str],
    loaded: Collection[str],
    stacked: Collection[str],
) -> Dict[str, str]:
    """Why each additional file's form name can't be used, by path ("" if it can).

    *name_map* is each file's form name as it would be added (``{path: form
    name}``; the file name when none was typed), *typed* the names typed in.
    *loaded* are the other forms loaded, *stacked* the stacked forms' names.
    """
    counts = Counter(name_map.values())
    found: Dict[str, str] = {}
    for path, name in name_map.items():
        if FORM_ITEM_SEPARATOR in name:
            found[path] = (
                "Give it a form name."
                if not typed.get(path, "").strip()
                else f"A form name can't contain “{FORM_ITEM_SEPARATOR}”."
            )
        elif name in loaded:
            found[path] = f"{name} is already a loaded form."
        elif name in stacked:
            found[path] = f"{name} is already a stacked form."
        elif counts[name] > 1:
            found[path] = f"Another file's form is called {name}."
        else:
            found[path] = ""
    return found


def held_save_tip(held: Collection[str]) -> str:
    """Why Save setting waits: the Data steps *held* (their changes can't apply).

    For example "Fix Stacked forms first: its changes aren't in the report yet."
    """
    titles = [TITLES[key] for key in DATA_STEPS if key in held]
    whose = "its" if len(titles) == 1 else "their"
    return (
        f"Fix {feedback.and_list(titles)} first: {whose} changes aren't in the "
        "report yet."
    )


def additional_form_names_message(
    name_map: Mapping[str, str], taken: Collection[str]
) -> Optional[feedback.Message]:
    """Why the additional files' form names can't be used, or ``None``.

    *name_map* is each file's form name (``{path: form name}``, see
    :func:`clinical_reporting.data.additional_form_names`); *taken* are the
    report's form names the files can't take (its loaded and stacked forms).
    A name can't hold a ".", two files can't share one, and none can be
    taken. A warning to show on one line; its details list the reasons by
    file.
    """
    dotted_names = sorted({name for name in name_map.values() if is_qualified(name)})
    name_to_paths: Dict[str, List[str]] = {}
    for file_path, form_name in name_map.items():
        name_to_paths.setdefault(form_name, []).append(file_path)
    duplicates = {
        form_name: paths for form_name, paths in name_to_paths.items() if len(paths) > 1
    }
    conflicts = {
        form_name: paths
        for form_name, paths in name_to_paths.items()
        if form_name in taken
    }
    if not dotted_names and not duplicates and not conflicts:
        return None

    clashing = sorted(set(dotted_names) | set(duplicates) | set(conflicts))
    message_parts = [
        "Cannot add forms because some form names are invalid or conflict "
        "with existing data."
    ]
    if dotted_names:
        message_parts.append("Form names cannot include '.':")
        message_parts.append("  - " + ", ".join(dotted_names))
    if duplicates:
        message_parts.append("Duplicate names in additional forms:")
        for form_name in sorted(duplicates):
            file_list = ", ".join(
                sorted(Path(path).name for path in duplicates[form_name])
            )
            message_parts.append(f"  - {form_name}: {file_list}")
    if conflicts:
        message_parts.append("Conflicts with existing report forms:")
        for form_name in sorted(conflicts):
            file_list = ", ".join(
                sorted(Path(path).name for path in conflicts[form_name])
            )
            message_parts.append(f"  - {form_name}: {file_list}")
    # One line on the page (it doesn't scroll); the reasons per file are
    # behind "Show details".
    return feedback.warning(
        f"These form names can't be used: {feedback.short_list(clashing)}. "
        "Rename them in the table and try again.",
        "\n".join(message_parts),
    )


_MATCHED_BY = {BY_FILE_NAME: "by its file name", BY_COLUMNS: "by its columns"}


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
            f"{_lacking(ignored)}. Check them on {TITLES[ADDITIONAL]}.",
            _ignored_details(ignored),
        )
    details = "\n".join(parts) if len(parts) > 5 else None
    return feedback.info(f"{text} Check them on {TITLES[ADDITIONAL]}.", details)


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
            f"used and will be ignored: {_lacking(ignored)}. {NAMES_USED_ON_LEAVING}",
            _ignored_details(ignored),
        )
    return feedback.info(
        f"Names from {name} filled in for {file_name}. {NAMES_USED_ON_LEAVING}"
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
        "the form is still added"
        if len({name.file_name for name in ignored}) == 1
        else "the forms are still added"
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


def setting_missing_lines(missing: Mapping[str, Sequence[str]]) -> List[str]:
    """What a saved setting needs that the data lacks, as lines to show.

    *missing* is what
    :meth:`~clinical_reporting.CLReport.reconcile_with_current_data` returns.
    The forms come first, as given ("Missing forms: LAB, PK"); then the
    common items ("Missing common items: Visit"), which include items without
    a form or with an empty part; then one line per form for its items
    ("Missing items in DM: Age, Sex"), forms and items sorted. ``[]`` when
    nothing is missing.
    """
    lines = []
    forms = list(missing.get("forms") or ())
    if forms:
        lines.append("Missing forms: " + ", ".join(forms))
    common_items = []
    form_items: Dict[str, List[str]] = {}
    for item in missing.get("items") or ():
        form_name, item_name = split_qualified(str(item))
        if form_name and item_name:
            form_items.setdefault(form_name, []).append(item_name)
        else:
            common_items.append(str(item))
    if common_items:
        lines.append("Missing common items: " + ", ".join(sorted(common_items)))
    for form_name in sorted(form_items):
        lines.append(
            f"Missing items in {form_name}: " + ", ".join(sorted(form_items[form_name]))
        )
    return lines


def saved_names_hint(
    missing_forms: Iterable[str],
    entries: Iterable[SavedFileNames],
    added: Collection[SavedFileNames] = (),
) -> Optional[str]:
    """For a loaded setting's "Missing forms" warning: the files that bring them.

    Says which additional files to add for the *missing_forms* that have
    saved names; for those whose file is already *added* (see
    ``AdditionalInputMixin._saved_names_added``), to check its form name
    and apply it. ``None`` when no missing form has saved names.
    """
    by_form = {entry.form_name: entry for entry in entries if entry.form_name}
    forms = [form for form in missing_forms if form in by_form]
    if not forms:
        return None
    where = TITLES[ADDITIONAL]
    to_add = [form for form in forms if by_form[form] not in added]
    to_check = [form for form in forms if by_form[form] in added]
    hints = []
    if len(to_add) == 1:
        hints.append(
            f"{to_add[0]} comes from an additional file. Add "
            f"{by_form[to_add[0]].file_name} on {where}, and its saved names will "
            "be picked for you."
        )
    elif to_add:
        files = feedback.and_list([by_form[form].file_name for form in to_add])
        hints.append(
            f"{feedback.and_list(to_add)} come from additional files. Add {files} on "
            f"{where}, and their saved names will be picked for you."
        )
    if len(to_check) == 1:
        hints.append(
            f"The file for {to_check[0]} is added: check its form name on {where}."
        )
    elif to_check:
        hints.append(
            f"The files for {feedback.and_list(to_check)} are added: check their "
            f"form names on {where}."
        )
    return " ".join(hints)


def stacked_form_tooltip(stacked: StackedForm) -> str:
    """How a stacked form says what it is, e.g. "Stacked from SV, DSSVLTFU"."""
    return f"Stacked from {', '.join(stacked.members)}"


def stacked_clear_tooltip(clears: Sequence[str], item: str) -> str:
    """What choosing "—" in a match's cell also clears: the members sharing its *item*.

    For example "Choosing — also clears DS, which gives Status too."
    """
    gives = "gives" if len(clears) == 1 else "give"
    others = feedback.and_list(clears)
    return f"Choosing — also clears {others}, which {gives} {item} too."


def stacked_not_loaded_hint(missing: Sequence[str]) -> str:
    """What the items grid says when the *missing* members leave it fewer than two.

    For example "LAB isn't loaded. Add its file on Additional input, or untick
    it in Members." The members stay, so adding the file brings them back.
    """
    where = TITLES[ADDITIONAL]
    if len(missing) == 1:
        return (
            f"{missing[0]} isn't loaded. Add its file on {where}, "
            "or untick it in Members."
        )
    return (
        f"{feedback.and_list(missing)} aren't loaded. Add their files on "
        f"{where}, or untick them in Members."
    )


def stacked_cell_warning(item: MatchedItem, match: Match, member: str) -> str:
    """Why *member*'s cell in a matched row warns, or "" when it doesn't.

    For example "DSSVLTFU has no Event Label; its Event Group Name is taken
    instead", or "DSSVLTFU has no Event Label". (A member that gives two of
    the match's items is a problem, not a warning: see
    :func:`clinical_reporting.stacking.form_problems`.)
    """
    if member in item.replaced:
        return (
            f"{member} has no {match.items[member]}; "
            f"its {item.cells[member]} is taken instead"
        )
    if member in item.missing:
        return f"{member} has no {match.items[member]}"
    return ""


def stacked_applied_message(report) -> feedback.Message:
    """What reaching the report did for the stacked forms: each one's rows and members.

    For example "Stacked forms updated: VISITS (1,514 rows from SV,
    DSSVLTFU)."; a stacked form that couldn't be built (see
    :func:`stacked_missing_message` and the validation issues) says so.
    """
    if not report.stacked_forms:
        return feedback.success(
            f"{TITLES[STACKED]}: the stacked forms were removed from the report."
        )
    parts = []
    for stacked in report.stacked_forms:
        rows = report.stacked_build.forms.get(stacked.name)
        if rows is None:
            parts.append(f"{stacked.name} (not built)")
            continue
        present = layout(stacked, report.loaded_data).present
        parts.append(
            f"{stacked.name} ({row_count(len(rows))} from {', '.join(present)})"
        )
    return feedback.success(f"{TITLES[STACKED]} updated: {'; '.join(parts)}.")


def stacked_missing_message(report) -> str:
    """The members and matched items the report's stacked forms lack.

    A warning, for example "VISITS is built without DSSVLTFU, which isn't
    loaded. In VISITS, SV has no Visit Status: the matched item is blank on
    its rows."; a matched item a member replaced with another of the match's
    items says so ("Visit Name takes its Event Group Name instead"); ``""``
    when nothing is missing.
    """
    built = report.stacked_build
    sentences = []
    for stacked in report.stacked_forms:
        name = stacked.name
        members = list(built.missing_members.get(name, ()))
        if members:
            loaded = "isn't loaded" if len(members) == 1 else "aren't loaded"
            listed = feedback.and_list(members)
            if name in built.forms:
                sentences.append(f"{name} is built without {listed}, which {loaded}.")
            else:
                sentences.append(f"{name} isn't built: {listed} {loaded}.")
        items = built.missing_items.get(name, ())
        if items:
            lacks = feedback.and_list(
                [f"{member} has no {item}" for member, item in items]
            )
            blank = (
                "the matched item is blank on its rows"
                if len(items) == 1
                else "the matched items are blank on their rows"
            )
            sentences.append(f"In {name}, {lacks}: {blank}.")
        for member, saved, used in built.replaced.get(name, ()):
            match = next(
                match for match in stacked.matches if match.items.get(member) == saved
            )
            sentences.append(
                f"In {name}, {member} has no {saved}: {match.name} takes its {used} "
                "instead."
            )
    if not sentences:
        return ""
    return feedback.warning(" ".join(sentences))


def coalesced_applied_message(report) -> feedback.Message:
    """What reaching the report did for the coalesced items: the rows each filled.

    For example "Coalesced items updated: Race in DM (12 rows filled)."; a
    coalesced item that couldn't be built (see :func:`coalesced_missing_message`
    and the validation issues) says so.
    """
    if not report.coalesced_items:
        return feedback.success(
            f"{TITLES[COALESCED]}: the coalesced items were removed from the report."
        )
    parts = []
    for position, item in enumerate(report.coalesced_items):
        outcome = report.coalesced_build.outcomes.get(position)
        if outcome is None:
            parts.append(f"{coalescing.label(item)} (not built)")
            continue
        filled = row_count(outcome.filled)
        parts.append(f"{coalescing.label(item)} ({filled} filled)")
    return feedback.success(f"{TITLES[COALESCED]} updated: {'; '.join(parts)}.")


def coalesced_counts(item: CoalescedItem, outcome: Outcome) -> str:
    """Where the rows of *item*'s form take their value from, as *outcome* gives.

    For example "DM has 250 rows: 230 keep Race · 12 filled from Race Other
    Specify · 6 left empty · 2 rows overlap".
    """
    (first, kept), *later = outcome.rows.items()
    overlapping = outcome.overlapping
    parts = [
        f"{kept:,} keep {first}",
        *(f"{count:,} filled from {name}" for name, count in later),
        f"{outcome.empty:,} left empty",
        "1 row overlaps" if overlapping == 1 else f"{overlapping:,} rows overlap",
    ]
    rows = sum(outcome.rows.values()) + outcome.empty
    return f"{item.form} has {row_count(rows)}: {' · '.join(parts)}"


def coalesced_missing_message(report) -> str:
    """The forms and items the report's coalesced items lack.

    A warning, for example "Race in DM is built without Race Other Specify,
    which DM doesn't have."; ``""`` when nothing is missing.
    """
    built = report.coalesced_build
    sentences = []
    for position, item in enumerate(report.coalesced_items):
        named = coalescing.label(item)
        if item.form in built.missing_forms:
            sentences.append(f"{named} isn't built: {item.form} isn't loaded.")
            continue
        lacking = built.missing_items.get(position)
        if not lacking:
            continue
        if position in built.outcomes:
            sentences.append(
                f"{named} is built without {feedback.and_list(lacking)}, which "
                f"{item.form} doesn't have."
            )
        else:
            sentences.append(
                f"{named} isn't built: {item.form} has no {_or_list(lacking)}."
            )
    if not sentences:
        return ""
    return feedback.warning(" ".join(sentences))


__all__ = [
    "ADDITIONAL",
    "COALESCED",
    "COMMON",
    "COMPARISONS",
    "DATA_STEPS",
    "DONE",
    "ERROR",
    "FILTERS",
    "FILTER_ITEM_ISSUE_CODES",
    "FORMS",
    "FORM_ITEMS",
    "ISSUE_STEPS",
    "JOINS",
    "NEEDS_DATA",
    "NAMES_USED_ON_LEAVING",
    "NONE",
    "NO_DATA",
    "NO_DATA_HINT",
    "OPTIONAL",
    "ORDER",
    "PREVIEW",
    "SAVED_NAMES_NONE",
    "SAVED_NAMES_UNAVAILABLE_TIP",
    "SOURCE",
    "STACKED",
    "STEP_KEYS",
    "TITLES",
    "UNPLACED_ISSUE_CODES",
    "WARNING",
    "StepStatus",
    "additional_applied_message",
    "additional_form_names_message",
    "additional_name_problems",
    "cannot_run_message",
    "coalesced_applied_message",
    "coalesced_counts",
    "coalesced_missing_message",
    "held_save_tip",
    "issue_step",
    "issues_by_field",
    "joins_message",
    "preview_caption",
    "report_summary",
    "row_count",
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
    "setting_missing_lines",
    "source_summary",
    "stacked_applied_message",
    "stacked_cell_warning",
    "stacked_clear_tooltip",
    "stacked_form_tooltip",
    "stacked_missing_message",
    "stacked_not_loaded_hint",
    "step_statuses",
]
