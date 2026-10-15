"""Coalesced items: one item made from two or more items of a form.

A coalesced item takes its items in order, row by row. Its first item gives
the value; each later item (a :class:`Fill`) fills that value where it is
still empty, or where it meets the fill's condition (a Filters operator and
value, tested on the value so far: ``= Other`` lets the item replace an
Other). The items it is made from leave the form, and the coalesced item
takes their place: where its first item was, under one of their names or a
new one.

A saved setting keeps the coalesced items under :data:`SETTINGS_KEY`:

.. code-block:: json

    "coalesced_items": [
        {
            "form": "DM",
            "name": "Race",
            "first": "Race",
            "fills": [
                {"item": "Race Other Specify", "operator": "=", "value": "Other"}
            ],
            "on_overlap": "refuse"
        }
    ]

The key is only written when there are coalesced items, so a setting
without them saves exactly as before. Like the rest of the core, this module
never imports Qt.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import (
    Any,
    Collection,
    Dict,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Tuple,
)

import numpy as np
import pandas as pd

from clinical_reporting import feedback
from clinical_reporting.export import to_short_date_string
from clinical_reporting.models import SUBJECT_COLUMN, Operator, common_items
from clinical_reporting.pipeline import static_filter_mask

logger = logging.getLogger(__name__)

#: The saved-settings key that holds the coalesced items.
SETTINGS_KEY = "coalesced_items"
#: What a coalesced item without a name is called in messages.
NEW_COALESCED_ITEM = "New coalesced item"
#: What a coalesced item does where values overlap (:class:`Overlap`):
#: refuse to be applied, which stops the report when later data brings one,
#: or keep the earlier value.
REFUSE = "refuse"
KEEP_EARLIER = "keep_earlier"
#: The Filters operators a fill's condition can use. Not is Null or is not
#: Null: an empty value is always filled.
CONDITION_OPERATORS = tuple(
    operator for operator in Operator.STATIC if operator not in Operator.NULLARY
)


@dataclass(frozen=True)
class Fill:
    """A later item of a coalesced item, and when it fills the value so far."""

    item: str
    #: The condition's Filters operator; "" for none (it fills empty values only).
    operator: str = ""
    value: str = ""


@dataclass(frozen=True)
class CoalescedItem:
    """How one coalesced item is made: its form, name, and items in order."""

    form: str
    name: str
    #: The item that gives the value to start with.
    first: str
    #: The later items, in order.
    fills: Tuple[Fill, ...] = ()
    #: :data:`REFUSE` or :data:`KEEP_EARLIER`.
    on_overlap: str = REFUSE

    def __post_init__(self) -> None:
        object.__setattr__(self, "fills", tuple(self.fills))

    @property
    def items(self) -> Tuple[str, ...]:
        """Its items in order: the first, then each fill's."""
        return (self.first, *(fill.item for fill in self.fills))


@dataclass(frozen=True)
class Overlap:
    """A row where a later item has a value and the value so far is one too.

    The value so far is real there: not empty, and not meeting the later
    item's condition. It stays; the later item's value doesn't.
    """

    #: The row's place in the form, from 1.
    row: int
    #: The row's Subject; ``None`` when the form has no Subject.
    subject: Any
    #: The later item.
    item: str
    #: The value so far, which stays.
    kept: Any
    #: The later item's value.
    other: Any


@dataclass(frozen=True)
class Outcome:
    """What building a coalesced item over its form gave (:func:`build`)."""

    #: The form with the coalesced item in place of its items.
    frame: pd.DataFrame
    #: How many rows take their value from each item, by item (the first
    #: item's count includes values nothing replaced, an Other say).
    rows: Mapping[str, int]
    #: How many rows are left empty.
    empty: int
    #: In item order, then row order.
    overlaps: Tuple[Overlap, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", MappingProxyType(dict(self.rows)))

    @property
    def filled(self) -> int:
        """How many rows a later item filled."""
        return sum(list(self.rows.values())[1:])

    @property
    def overlapping(self) -> int:
        """How many rows overlap (at one later item or more)."""
        return len({overlap.row for overlap in self.overlaps})


def _empty(values: pd.Series) -> pd.Series:
    """Which of *values* are empty: missing, or text of only spaces."""
    blank = values.astype("string").str.strip().eq("").fillna(False)
    return (values.isna() | blank).astype(bool)


def build(item: CoalescedItem, frame: pd.DataFrame) -> Outcome:
    """*item* built over *frame*, its form.

    Each later item fills the value so far where that value is empty or
    meets the item's condition, and the later item has a value; where the
    value so far is real and the later item has a value too, that is an
    :class:`Overlap` and the value so far stays.
    """
    current = frame[item.first]
    # Which item gives each row its value: 0 the first, n the nth fill, -1 none.
    origin = np.where(_empty(current).to_numpy(), -1, 0)
    subjects = frame[SUBJECT_COLUMN] if SUBJECT_COLUMN in frame.columns else None
    overlaps: List[Overlap] = []
    for position, fill in enumerate(item.fills, start=1):
        source = frame[fill.item]
        open_ = _empty(current)
        if fill.operator:
            open_ |= static_filter_mask(current, fill.operator, fill.value)
        has = ~_empty(source)
        for row in np.flatnonzero((~open_ & has).to_numpy()):
            overlaps.append(
                Overlap(
                    int(row) + 1,
                    None if subjects is None else subjects.iat[row],
                    fill.item,
                    current.iat[row],
                    source.iat[row],
                )
            )
        takes = open_ & has
        if takes.any():
            current = current.where(~takes, source)
            origin = np.where(takes.to_numpy(), position, origin)
    rows: Dict[str, int] = {
        name: int((origin == position).sum())
        for position, name in enumerate(item.items)
    }
    coalesced = frame.drop(columns=[fill.item for fill in item.fills])
    coalesced[item.first] = current
    return Outcome(
        coalesced.rename(columns={item.first: item.name}),
        rows,
        int((origin == -1).sum()),
        tuple(overlaps),
    )


@dataclass(frozen=True)
class Built:
    """The coalesced items built over some data (:func:`build_all`)."""

    #: The forms coalescing changed, keyed by form.
    forms: Mapping[str, pd.DataFrame] = field(default_factory=dict)
    #: What building each coalesced item gave, keyed by its position.
    outcomes: Mapping[int, Outcome] = field(default_factory=dict)
    #: The forms of coalesced items that aren't there; those aren't built.
    missing_forms: Tuple[str, ...] = ()
    #: The items each coalesced item's form lacks, keyed by its position. It
    #: is built from the others (with none left, it isn't built).
    missing_items: Mapping[int, Tuple[str, ...]] = field(default_factory=dict)
    #: Why the report can't use the coalesced items as the data now is, one
    #: message each: values that overlap in one set to refuse them (it is
    #: built, keeping the earlier values), or, in one not built, a name an
    #: item of the form now has, or an item another coalesced item holds (an
    #: edited setting). Validation stops the report until they are fixed. An
    #: overlap's message names its first five rows.
    conflicts: Tuple[str, ...] = ()
    #: The same messages, an overlap's naming every row.
    conflict_details: Tuple[str, ...] = ()


def _present(item: CoalescedItem, columns: Collection[str]) -> Optional[CoalescedItem]:
    """*item* without the items *columns* lacks; ``None`` when none is left.

    When its first item is gone, the next present one starts the value.
    """
    kept = [fill for fill in (Fill(item.first), *item.fills) if fill.item in columns]
    if not kept:
        return None
    first, *fills = kept
    return replace(item, first=first.item, fills=tuple(fills))


def build_all(
    items: Sequence[CoalescedItem], data: Mapping[str, pd.DataFrame]
) -> Built:
    """*items* built over *data* (the loaded and stacked forms), and what's amiss.

    Each coalesced item is built over its form as the ones before it left
    it. One whose form or items are missing is built from what is there
    (:attr:`Built.missing_forms`, :attr:`Built.missing_items`); what makes
    one unusable is recorded in :attr:`Built.conflicts`.
    """
    forms: Dict[str, pd.DataFrame] = {}
    outcomes: Dict[int, Outcome] = {}
    missing_forms: List[str] = []
    missing_items: Dict[int, Tuple[str, ...]] = {}
    conflicts: List[str] = []
    details: List[str] = []
    # The coalesced item that holds each (form, item).
    holders: Dict[Tuple[str, str], str] = {}
    for position, item in enumerate(items):
        if item.form not in data:
            if item.form not in missing_forms:
                missing_forms.append(item.form)
            continue
        columns = data[item.form].columns
        lacking = tuple(name for name in item.items if name not in columns)
        if lacking:
            missing_items[position] = lacking
        present = _present(item, set(columns))
        if present is None:
            continue
        frame = forms.get(item.form, data[item.form])
        held = [
            (name, holders[(item.form, name)])
            for name in present.items
            if (item.form, name) in holders
        ]
        if held:
            found = [
                f"{label(item)}: {name} is also in {holder}. Keep each item in "
                "one coalesced item on Coalesced items."
                for name, holder in held
            ]
            conflicts.extend(found)
            details.extend(found)
            continue
        if item.name in frame.columns and item.name not in present.items:
            found = [
                f"{label(item)}: {item.form} now has its own {item.name}. Rename "
                "the coalesced item on Coalesced items."
            ]
            conflicts.extend(found)
            details.extend(found)
            continue
        for name in present.items:
            holders[(item.form, name)] = item.name
        outcome = build(present, frame)
        if outcome.overlaps and item.on_overlap == REFUSE:
            # The same lines twice: naming the first five rows, and every row.
            for shown, lines in ((5, conflicts), (None, details)):
                lines.extend(
                    f"{label(item)}: {line} Change a condition, or keep the "
                    "earlier value, on Coalesced items."
                    for _, line in _overlap_lines(present, outcome, shown)
                )
        forms[item.form] = outcome.frame
        outcomes[position] = outcome
    return Built(
        forms,
        outcomes,
        tuple(missing_forms),
        missing_items,
        tuple(conflicts),
        tuple(details),
    )


# ---------------------------------------------------------------------------
# What stops coalesced items from reaching the report


def label(item: CoalescedItem) -> str:
    """How messages name *item*: "Race in DM" ("New coalesced item" unnamed)."""
    name = item.name.strip() or NEW_COALESCED_ITEM
    return f"{name} in {item.form}" if item.form else name


def problems(
    items: Sequence[CoalescedItem],
    data: Mapping[str, pd.DataFrame],
    *,
    shown: Optional[int] = 5,
) -> List[str]:
    """What stops *items* from reaching the report over *data*, one line each.

    *data* holds the forms coalesced items are made from (the loaded forms
    and the stacked forms). Each line starts with the coalesced item, as
    "Race in DM: "; a problem marked on several of its fields is said once.
    A common item can only be coalesced under its own name, so the forms
    still join on it; with one form loaded there are no joins, and no item
    is held to its name. An overlap's line names its first *shown* rows
    (every row with ``None``).
    """
    return [
        f"{label(item)}: {text}"
        for item, found in zip(items, item_problems(items, data, shown=shown))
        for text in dict.fromkeys(problem.text for problem in found)
    ]


def item_problems(
    items: Sequence[CoalescedItem],
    data: Mapping[str, pd.DataFrame],
    outcomes: Sequence[Optional[Outcome]] = (),
    *,
    shown: Optional[int] = 5,
) -> List[List[feedback.Problem]]:
    """What stops each of *items* from reaching the report, on its fields.

    One list per coalesced item, in :func:`problems`' order. A problem's
    field is ``"form"``, ``"name"``, ``"item.k"`` (its item in row *k*, row
    0 its first item), ``"value.k"`` (row *k*'s condition value) or
    ``"overlap.k"`` (the rows row *k* overlaps, while it refuses overlaps);
    a problem with an item is on every row holding it. *outcomes* holds what
    :func:`preview` gave for each, by position, so the overlaps aren't built
    again; without one, the item is built over *data*.
    """
    found = []
    for position, (item, (issues, buildable)) in enumerate(
        zip(items, _checks(items, data))
    ):
        if buildable and item.on_overlap == REFUSE:
            outcome = outcomes[position] if position < len(outcomes) else None
            if outcome is None:
                outcome = build(item, data[item.form])
            issues = [
                *issues,
                *(
                    feedback.Problem(f"overlap.{row}", line)
                    for row, line in _overlap_lines(item, outcome, shown)
                ),
            ]
        found.append(issues)
    return found


def preview(
    items: Sequence[CoalescedItem], position: int, data: Mapping[str, pd.DataFrame]
) -> Optional[Outcome]:
    """What the coalesced item at *position* among *items* gives over *data*.

    ``None`` while it can't be built: no form, fewer than two items, an item
    its form lacks or another coalesced item holds (see :func:`item_problems`).
    """
    _, buildable = _checks(items, data)[position]
    if not buildable:
        return None
    item = items[position]
    return build(item, data[item.form])


def _names(items: Sequence[CoalescedItem]) -> Counter:
    """How many coalesced items of each form have each name."""
    return Counter(
        (item.form, item.name.strip()) for item in items if item.name.strip()
    )


def _checks(
    items: Sequence[CoalescedItem], data: Mapping[str, pd.DataFrame]
) -> List[Tuple[List[feedback.Problem], bool]]:
    """Each coalesced item's problems but its overlaps, and if it can be built."""
    names = _names(items)
    common = set(common_items(data)) if len(data) > 1 else set()
    # The position of the coalesced item each (form, item) is in first.
    holders: Dict[Tuple[str, str], int] = {}
    return [
        _issues(items, position, data, names, common, holders)
        for position in range(len(items))
    ]


def _issues(
    items: Sequence[CoalescedItem],
    position: int,
    data: Mapping[str, pd.DataFrame],
    names: Mapping[Tuple[str, str], int],
    common: Collection[str],
    holders: Dict[Tuple[str, str], int],
) -> Tuple[List[feedback.Problem], bool]:
    Problem = feedback.Problem
    item = items[position]
    if not item.form:
        return [Problem("form", "Pick its form.")], False
    if item.form not in data:
        return [Problem("form", f"{item.form} isn't loaded.")], False
    columns = set(data[item.form].columns)
    picked = [name for name in item.items if name.strip()]
    counts = Counter(picked)

    def on_rows_of(name: str, text: str) -> List[feedback.Problem]:
        """*text* on every row holding the item *name*."""
        return [
            Problem(f"item.{row}", text)
            for row, held in enumerate(item.items)
            if held == name
        ]

    issues = []
    if len(item.items) < 2:
        issues.append(Problem("item.1", "Pick at least two items."))
    issues.extend(
        Problem(f"item.{row}", "Pick an item in each row.")
        for row, name in enumerate(item.items)
        if not name.strip()
    )
    for name in counts:
        if name not in columns:
            issues.extend(on_rows_of(name, f"{item.form} has no {name}."))
    for name, count in counts.items():
        if count > 1:
            issues.extend(on_rows_of(name, f"{name} is in it twice."))
    issues.extend(
        Problem(f"value.{row}", f"Give the condition for {fill.item} a value.")
        for row, fill in enumerate(item.fills, start=1)
        if fill.operator and not str(fill.value).strip()
    )
    for picked_name in counts:
        holder = holders.setdefault((item.form, picked_name), position)
        if holder != position:
            other = items[holder].name.strip() or NEW_COALESCED_ITEM
            issues.extend(
                on_rows_of(picked_name, f"{picked_name} is already in {other}.")
            )
    # Overlaps only count once it can be built as it stands.
    buildable = not issues
    name_issue = _name_issue(item, columns, names)
    if name_issue:
        issues.append(Problem("name", name_issue))
    name = item.name.strip()
    for picked_name in counts:
        if picked_name in common and picked_name != name:
            text = (
                f"{picked_name} is a common item: name the coalesced item "
                f"{picked_name}, or leave {picked_name} out."
            )
            issues.extend([*on_rows_of(picked_name, text), Problem("name", text)])
    return issues, buildable


def _name_issue(
    item: CoalescedItem, columns: Collection[str], names: Mapping[Tuple[str, str], int]
) -> str:
    name = item.name.strip()
    if not name:
        return "Give it a name."
    if name in columns and name not in item.items:
        return f"{item.form} already has an item called {name}."
    if names[(item.form, name)] > 1:
        return f"Another coalesced item of {item.form} is called {name}."
    return ""


def _overlap_lines(
    item: CoalescedItem, outcome: Outcome, shown: Optional[int]
) -> List[Tuple[int, str]]:
    """The overlaps of *outcome*, one line per later item, with its row.

    The row is the later item's place in *item* (1 for its first fill).
    Each line names its first *shown* rows, or every row with ``None``.
    """
    name = item.name.strip() or item.first
    lines = []
    for row, fill in enumerate(item.fills, start=1):
        rows = [
            _row_label(overlap)
            for overlap in outcome.overlaps
            if overlap.item == fill.item
        ]
        if not rows:
            continue
        have = "1 row has" if len(rows) == 1 else f"{len(rows):,} rows have"
        listed = feedback.short_list(rows, len(rows) if shown is None else shown)
        lines.append(
            (
                row,
                f"{have} a value in {fill.item} where {name} already has one: "
                f"{listed}.",
            )
        )
    return lines


def _row_label(overlap: Overlap) -> str:
    """An overlap's row as messages name it: "101-004 (White / Caucasian)"."""
    subject = overlap.subject
    where = (
        f"row {overlap.row}" if subject is None or pd.isna(subject) else _shown(subject)
    )
    return f"{where} ({_shown(overlap.kept)} / {_shown(overlap.other)})"


def _shown(value: Any) -> str:
    """*value* as the export shows it: dates m/d/yyyy, whole numbers bare."""
    value = to_short_date_string(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


# ---------------------------------------------------------------------------
# Saved settings


def to_settings(
    settings: MutableMapping[str, Any], items: Sequence[CoalescedItem]
) -> MutableMapping[str, Any]:
    """Store *items* in a settings dictionary; return *settings*.

    The key is only set when there are coalesced items, so a setting without
    them is saved exactly as before the key existed.
    """
    if not items:
        settings.pop(SETTINGS_KEY, None)
        return settings
    settings[SETTINGS_KEY] = [
        {
            "form": item.form,
            "name": item.name,
            "first": item.first,
            "fills": [_fill_to_settings(fill) for fill in item.fills],
            "on_overlap": item.on_overlap,
        }
        for item in items
    ]
    return settings


def _fill_to_settings(fill: Fill) -> Dict[str, str]:
    saved = {"item": fill.item}
    if fill.operator:
        saved.update(operator=fill.operator, value=fill.value)
    return saved


def _fill_from(raw: Any) -> Optional[Fill]:
    """One saved fill, or ``None`` if *raw* isn't a usable one."""
    if not isinstance(raw, Mapping):
        return None
    item = raw.get("item")
    if not isinstance(item, str) or not item.strip():
        return None
    operator = raw.get("operator") or ""
    if not operator:
        return Fill(item)
    value = raw.get("value", "")
    if operator not in CONDITION_OPERATORS or not isinstance(value, str):
        return None
    return Fill(item, operator, value)


def _item_from(raw: Any) -> Optional[CoalescedItem]:
    """One saved coalesced item, or ``None`` if *raw* isn't a usable one."""
    if not isinstance(raw, Mapping):
        return None
    form, name, first = (raw.get(key) for key in ("form", "name", "first"))
    if not all(isinstance(text, str) and text.strip() for text in (form, name, first)):
        return None
    raw_fills = raw.get("fills")
    if not isinstance(raw_fills, list) or not raw_fills:
        return None
    fills = [_fill_from(fill) for fill in raw_fills]
    on_overlap = raw.get("on_overlap", REFUSE)
    if None in fills or on_overlap not in (REFUSE, KEEP_EARLIER):
        return None
    return CoalescedItem(form.strip(), name.strip(), first, tuple(fills), on_overlap)


def from_settings(settings: Any) -> List[CoalescedItem]:
    """The coalesced items saved in a settings dictionary, in their saved order.

    Settings without the key give none. A hand-edited or damaged entry never
    stops a setting from loading: it is skipped and logged, as is a second
    coalesced item with a name its form's first already has.
    """
    raw = settings.get(SETTINGS_KEY) if isinstance(settings, Mapping) else None
    if raw is None:
        return []
    if not isinstance(raw, list):
        logger.warning("Ignoring saved %s: not a list", SETTINGS_KEY)
        return []
    items: List[CoalescedItem] = []
    seen = set()
    for position, entry in enumerate(raw):
        item = _item_from(entry)
        if item is None or (item.form, item.name) in seen:
            logger.warning(
                "Skipping saved %s entry %d: %r", SETTINGS_KEY, position, entry
            )
            continue
        seen.add((item.form, item.name))
        items.append(item)
    return items


__all__ = [
    "CONDITION_OPERATORS",
    "KEEP_EARLIER",
    "NEW_COALESCED_ITEM",
    "REFUSE",
    "SETTINGS_KEY",
    "CoalescedItem",
    "Fill",
    "Outcome",
    "Overlap",
    "Built",
    "build",
    "build_all",
    "from_settings",
    "item_problems",
    "label",
    "preview",
    "problems",
    "to_settings",
]
