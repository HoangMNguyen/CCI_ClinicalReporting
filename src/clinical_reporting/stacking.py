"""Stacked forms: forms made by putting other forms' rows one under another.

A stacked form takes the rows of two or more loaded forms, its members (forms
of a Corelisting export or additional inputs, never another stacked form), in
member order, each member's rows in file order. Its items, the stacked items,
line up the members' items by name:

- An item every member has under the same (exact, case-sensitive) name is a
  stacked item by itself. So a stacked form always has every common item.
- Every other member item is left out unless the user puts it in a match. A
  match lines up whole same-name groups of left-out items, at most one item
  from each member, and is named with one of their names or a new one.

A match keeps the item each member gave it, so a warning can name an item a
member no longer has, but names decide what lines up: a member added later
joins a match when it has an item with one of the match's names, and a name a
match holds is the match's in every member (a match never splits a same-name
group). Data that changes after Apply can make a match ambiguous (a member
with two of its items, a match named like an item every member now has); the
stacked form is then still built, but :func:`build_all` reports a conflict
and validation stops the report until the match is fixed, so no stacked item
quietly takes other values.

:class:`~clinical_reporting.report.CLReport` builds its stacked forms whenever
its data is set (:func:`build_all`), so every later step treats them as forms.
A saved setting keeps them under :data:`SETTINGS_KEY`:

.. code-block:: json

    "stacked_forms": [
        {
            "name": "VISITS",
            "members": ["SV", "DSSVLTFU"],
            "matches": [
                {"name": "Visit Name",
                 "items": {"SV": "Event Group Name", "DSSVLTFU": "Event Label"}}
            ]
        }
    ]

The key is only written when there are stacked forms, so a setting without
them saves exactly as before. Like the rest of the core, this module never
imports Qt.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field, replace
from difflib import SequenceMatcher
from functools import lru_cache
from types import MappingProxyType
from typing import (
    Any,
    Collection,
    Dict,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Tuple,
)

import pandas as pd

from clinical_reporting import feedback
from clinical_reporting.models import FORM_ITEM_SEPARATOR

logger = logging.getLogger(__name__)

#: The saved-settings key that holds the stacked forms.
SETTINGS_KEY = "stacked_forms"
#: What a stacked form without a name is called in messages.
NEW_STACKED_FORM = "New stacked form"


@dataclass(frozen=True)
class Match:
    """A stacked item the user made from at most one item of each member."""

    #: The stacked item's name.
    name: str
    #: The item each member gave it, keyed by member (read-only).
    items: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", MappingProxyType(dict(self.items)))

    @property
    def names(self) -> Tuple[str, ...]:
        """The names of its items, each once, in the order they were given."""
        return tuple(dict.fromkeys(self.items.values()))


@dataclass(frozen=True)
class StackedForm:
    """How one stacked form is made: its name, members and matches."""

    name: str
    #: The members, in the order they were added (the order of their rows).
    members: Tuple[str, ...]
    matches: Tuple[Match, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "members", tuple(self.members))
        object.__setattr__(self, "matches", tuple(self.matches))


@dataclass(frozen=True)
class ItemGroup:
    """The present members that have an unmatched item of this name."""

    name: str
    #: In member order.
    members: Tuple[str, ...]


@dataclass(frozen=True)
class MatchedItem:
    """A match as the loaded data fills it."""

    name: str
    #: The match's position in :attr:`StackedForm.matches`.
    index: int
    #: The item each present member gives it; ``None`` where it gives none.
    cells: Mapping[str, Optional[str]]
    #: Present members that no longer have the item the match took from them
    #: and give it nothing (the matched item is blank on their rows).
    missing: Tuple[str, ...] = ()
    #: Present members that no longer have the item the match took from them
    #: but give it another item with one of its names instead.
    replaced: Tuple[str, ...] = ()
    #: Present members that now have two or more items with the match's names,
    #: with those names, so which one it should take is ambiguous (see
    #: :attr:`Built.conflicts`).
    doubled: Mapping[str, Tuple[str, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "cells", MappingProxyType(dict(self.cells)))
        object.__setattr__(self, "doubled", MappingProxyType(dict(self.doubled)))


@dataclass(frozen=True)
class StackLayout:
    """How a stacked form's items line up over the loaded data (:func:`layout`)."""

    #: Members that are loaded, in member order.
    present: Tuple[str, ...]
    #: Members that aren't.
    missing: Tuple[str, ...]
    #: The items every present member has (and no match holds).
    every: Tuple[ItemGroup, ...]
    matched: Tuple[MatchedItem, ...]
    #: The other items, out of the stacked form unless matched.
    left_out: Tuple[ItemGroup, ...]
    #: The stacked items in order: where each first appears across the members.
    order: Tuple[str, ...]
    #: The rows of the present members together.
    rows: int


@dataclass(frozen=True)
class Built:
    """The stacked forms built over some data (:func:`build_all`)."""

    #: The stacked rows of each stacked form built, keyed by its name.
    forms: Mapping[str, pd.DataFrame] = field(default_factory=dict)
    #: Stacked forms not built because a loaded form has their name.
    clashes: Tuple[str, ...] = ()
    #: Members that aren't loaded, keyed by stacked form.
    missing_members: Mapping[str, Tuple[str, ...]] = field(default_factory=dict)
    #: ``(member, item)`` pairs of matched items a present member no longer
    #: has, keyed by stacked form.
    missing_items: Mapping[str, Tuple[Tuple[str, str], ...]] = field(
        default_factory=dict
    )
    #: Why each stacked form can't be used as the data now is, keyed by stacked
    #: form: the data changed since Apply so that a match is named like an item
    #: every member has, two matches share a name, or a member has two items of
    #: one match; or an edited setting has two matches holding one item name.
    #: Validation stops the report until it is fixed on the page.
    conflicts: Mapping[str, Tuple[str, ...]] = field(default_factory=dict)
    #: ``(member, item, item used)`` for each matched item a present member no
    #: longer has but replaces with another item of the match, keyed by stacked
    #: form (a warning, like a missing one).
    replaced: Mapping[str, Tuple[Tuple[str, str, str], ...]] = field(
        default_factory=dict
    )


def _columns(frame: pd.DataFrame) -> List[str]:
    return list(dict.fromkeys(frame.columns))


def layout(stacked: StackedForm, data: Mapping[str, pd.DataFrame]) -> StackLayout:
    """How *stacked*'s items line up over *data* (the loaded forms).

    Each match takes, from each present member, the item the match saved for
    it if the member has it, else the member's item with one of the match's
    names (the first in the match's order), else nothing. Every name a match
    holds is the match's in every member. Of the other items, those every
    present member has are stacked by themselves; the rest are left out.
    """
    present = tuple(member for member in stacked.members if member in data)
    missing = tuple(member for member in stacked.members if member not in data)
    columns = {member: _columns(data[member]) for member in present}
    column_sets = {member: set(columns[member]) for member in present}

    claimed: Dict[str, int] = {}
    for index, match in enumerate(stacked.matches):
        for name in match.names:
            claimed.setdefault(name, index)

    matched = []
    for index, match in enumerate(stacked.matches):
        cells: Dict[str, Optional[str]] = {}
        gone: List[str] = []
        replaced: List[str] = []
        doubled: Dict[str, Tuple[str, ...]] = {}
        for member in present:
            have = [name for name in match.names if name in column_sets[member]]
            if len(have) > 1:
                doubled[member] = tuple(have)
            saved = match.items.get(member)
            if saved is not None and saved in have:
                cells[member] = saved
                continue
            cells[member] = have[0] if have else None
            if saved is not None:
                (replaced if have else gone).append(member)
        matched.append(
            MatchedItem(
                match.name,
                index,
                cells,
                tuple(gone),
                tuple(replaced),
                doubled,
            )
        )

    groups: Dict[str, List[str]] = {}
    for member in present:
        for name in columns[member]:
            if name not in claimed:
                groups.setdefault(name, []).append(member)
    every = tuple(
        ItemGroup(name, tuple(members))
        for name, members in groups.items()
        if len(members) == len(present)
    )
    left_out = tuple(
        ItemGroup(name, tuple(members))
        for name, members in groups.items()
        if len(members) != len(present)
    )

    order: Dict[str, None] = {}
    for member in present:
        for name in columns[member]:
            if name in claimed:
                order.setdefault(stacked.matches[claimed[name]].name)
            elif len(groups[name]) == len(present):
                order.setdefault(name)

    return StackLayout(
        present=present,
        missing=missing,
        every=every,
        matched=tuple(matched),
        left_out=left_out,
        order=tuple(order),
        rows=sum(len(data[member]) for member in present),
    )


def build(stacked: StackedForm, data: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """The stacked rows of *stacked* over *data*.

    The present members' rows in member order, each member's rows in file
    order; columns in item order (:func:`layout`), blank where a member gives
    nothing. Values are kept as they are.
    """
    return _build(layout(stacked, data), data)


def _build(plan: StackLayout, data: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """:func:`build` over the stacked form's *plan* (its :func:`layout`)."""
    every = [group.name for group in plan.every]
    parts = []
    for member in plan.present:
        # Each stacked item's column in this member. (A match named like an
        # item in every member, possible once the data changed after Apply,
        # gives way to that item; build_all reports it as a conflict, which
        # stops the report until it is fixed.)
        sources: Dict[str, str] = {name: name for name in every}
        for item in plan.matched:
            source = item.cells.get(member)
            if source is not None:
                sources.setdefault(item.name, source)
        names = [name for name in plan.order if name in sources]
        part = data[member].loc[:, [sources[name] for name in names]]
        part.columns = names
        parts.append(part)
    if not parts:
        return pd.DataFrame(columns=list(plan.order))
    return pd.concat(parts, ignore_index=True).reindex(columns=list(plan.order))


def build_all(
    stacked_forms: Iterable[StackedForm], data: Mapping[str, pd.DataFrame]
) -> Built:
    """The *stacked_forms* to add to *data* (the loaded forms), and what's amiss.

    A stacked form named like a loaded form isn't built (a clash), nor is one
    with no member loaded. Missing members and missing or replaced matched
    items are recorded for the warnings. Data that makes a stacked form
    ambiguous since it was applied is recorded as a conflict
    (:attr:`Built.conflicts`); the stacked form is still built, so the
    selections on it stay, but validation stops the report until it is fixed.
    """
    forms: Dict[str, pd.DataFrame] = {}
    clashes: List[str] = []
    missing_members: Dict[str, Tuple[str, ...]] = {}
    missing_items: Dict[str, Tuple[Tuple[str, str], ...]] = {}
    conflicts: Dict[str, Tuple[str, ...]] = {}
    replaced: Dict[str, Tuple[Tuple[str, str, str], ...]] = {}
    for stacked in stacked_forms:
        if stacked.name in data:
            clashes.append(stacked.name)
            continue
        plan = layout(stacked, data)
        if plan.missing:
            missing_members[stacked.name] = plan.missing
        if not plan.present:
            continue
        gone = tuple(
            (member, stacked.matches[item.index].items[member])
            for item in plan.matched
            for member in item.missing
        )
        if gone:
            missing_items[stacked.name] = gone
        swapped = tuple(
            (member, stacked.matches[item.index].items[member], item.cells[member])
            for item in plan.matched
            for member in item.replaced
        )
        if swapped:
            replaced[stacked.name] = swapped
        found = _conflicts(stacked, plan)
        if found:
            conflicts[stacked.name] = found
        forms[stacked.name] = _build(plan, data)
    return Built(
        forms, tuple(clashes), missing_members, missing_items, conflicts, replaced
    )


def _conflicts(stacked: StackedForm, plan: StackLayout) -> Tuple[str, ...]:
    """What makes *stacked* ambiguous over the data *plan* lays it out on.

    Apply refuses these (:func:`problems`); they come back when the data is
    set again with changed items (a saved setting, a new cut-off or export,
    additional inputs), or from an edited setting. Each would otherwise
    quietly put other values under a stacked item, or leave one out, so they
    stop the report instead.
    """
    name = stacked.name
    every = {group.name for group in plan.every}
    counts = Counter(match.name for match in stacked.matches)
    found: List[str] = []
    for item in plan.matched:
        match = stacked.matches[item.index]
        if counts[match.name] > 1:
            message = (
                f"{name} has two matches called {match.name}. Rename one on "
                "Stacked forms."
            )
            if message not in found:
                found.append(message)
        elif match.name in every:
            found.append(
                f"{name}: every member now has an item called {match.name}, also "
                "the name of a match. Rename the match on Stacked forms."
            )
        for member, have in item.doubled.items():
            both = (
                f"both {feedback.and_list(have)}"
                if len(have) == 2
                else feedback.and_list(have)
            )
            found.append(
                f"{name}: {member} now has {both}, which the match {match.name} "
                f"lines up. Choose “—” in {member}'s cell or Unmatch it on "
                "Stacked forms."
            )
    for item_name, holders in _shared_item_names(stacked).items():
        two = len(holders) == 2
        found.append(
            f"{name}: the matches {feedback.and_list(holders)} "
            f"{'both' if two else 'all'} line up {item_name}. Unmatch "
            f"{'one of them' if two else 'all but one'} on Stacked forms."
        )
    return tuple(found)


def _shared_item_names(stacked: StackedForm) -> Dict[str, List[str]]:
    """Item names more than one match holds, with those matches' names.

    The page only matches left-out items, so only an edited setting gets
    here; the later matches would otherwise lose the item quietly.
    """
    holders: Dict[str, List[str]] = {}
    for match in stacked.matches:
        for item_name in match.names:
            holders.setdefault(item_name, []).append(match.name)
    return {item: names for item, names in holders.items() if len(names) > 1}


# ---------------------------------------------------------------------------
# Editing a stacked form (each returns a new one)


def add_match(
    stacked: StackedForm,
    data: Mapping[str, pd.DataFrame],
    group_names: Collection[str],
) -> StackedForm:
    """*stacked* with a new match of the named left-out groups.

    The match is named after the first of them in left-out order and takes
    each member's item in member order. Raises :class:`ValueError`, with a
    message for the user, when a name isn't left out or two groups share a
    member.
    """
    plan = layout(stacked, data)
    left_out = {group.name: group for group in plan.left_out}
    if not group_names:
        raise ValueError("Select left-out items first.")
    for name in group_names:
        if name not in left_out:
            raise ValueError(f"{name} isn't left out, so it can't be matched.")
    names = [group.name for group in plan.left_out if group.name in group_names]
    taken: Dict[str, str] = {}
    for name in names:
        for member in left_out[name].members:
            if member in taken:
                raise ValueError(
                    "Pick at most one item from each member: "
                    f"{member} has both {taken[member]} and {name}."
                )
            taken[member] = name
    items = {member: taken[member] for member in plan.present if member in taken}
    return replace(stacked, matches=(*stacked.matches, Match(names[0], items)))


def remove_matches(stacked: StackedForm, indexes: Iterable[int]) -> StackedForm:
    """*stacked* without the matches at *indexes*; their items are left out again."""
    drop = set(indexes)
    return replace(
        stacked,
        matches=tuple(
            match for index, match in enumerate(stacked.matches) if index not in drop
        ),
    )


def rename_match(stacked: StackedForm, index: int, name: str) -> StackedForm:
    """*stacked* with the match at *index* named *name*."""
    matches = list(stacked.matches)
    matches[index] = Match(name, matches[index].items)
    return replace(stacked, matches=tuple(matches))


def with_members(stacked: StackedForm, members: Iterable[str]) -> StackedForm:
    """*stacked* with these *members*, in this order.

    Matches forget the items of members no longer in it; a match left with
    no item goes.
    """
    kept = tuple(dict.fromkeys(members))
    matches = []
    for match in stacked.matches:
        items = {member: item for member, item in match.items.items() if member in kept}
        if items:
            matches.append(Match(match.name, items))
    return StackedForm(stacked.name, kept, tuple(matches))


#: How alike (0 to 1) a left-out item's name must be to a match's names to be
#: offered under Similar names (see :func:`_similarity`).
_SIMILAR_AT = 0.6


def _squeezed(name: str) -> str:
    return "".join(letter for letter in name.casefold() if letter.isalnum())


@lru_cache(maxsize=4096)
def _similarity(a: str, b: str) -> float:
    """How alike item names *a* and *b* are, 0 to 1.

    Case, spaces and punctuation aside: the same name is 1; one inside the
    other is 0.9; a short form of the other (its letters in order from the
    same first letter, as Dt in Date) is 0.8; otherwise how much of the two
    names matches, in order.
    """
    x, y = _squeezed(a), _squeezed(b)
    if not x or not y:
        return 0.0
    if x == y:
        return 1.0
    if x in y or y in x:
        return 0.9
    short, long = sorted((x, y), key=len)
    rest = iter(long)
    if short[0] == long[0] and all(letter in rest for letter in short):
        return 0.8
    return SequenceMatcher(None, x, y).ratio()


@dataclass(frozen=True)
class MatchChoices:
    """What one member's cell in a match offers (:func:`match_choices`)."""

    #: The item the member gives the match now; ``None`` where it gives none.
    current: Optional[str]
    #: The member's left-out items most like the match's names, most alike
    #: first.
    similar: Tuple[str, ...]
    #: Its other left-out items the cell offers, in file order.
    others: Tuple[str, ...]
    #: The other present members that give the match an item of the current
    #: one's name, so they stop giving it too when the cell is cleared or
    #: changed.
    clears: Tuple[str, ...]


def match_choices(
    plan: StackLayout,
    data: Mapping[str, pd.DataFrame],
    index: int,
    member: str,
) -> MatchChoices:
    """What *member*'s cell in the match at *index* offers.

    *plan* is the stacked form's :func:`layout` over *data*. Besides its
    current item, a cell offers the member's left-out items: never an item
    every member has or another match holds, nor one whose same-name group
    would give another member a second item. The names most like the match's
    name and the items the other members give it come first; the member's
    own items aren't compared, as a form's items often share a prefix.
    """
    matched = plan.matched[index]
    current = matched.cells.get(member)
    offered = [
        group.name
        for group in plan.left_out
        if member in group.members
        and all(
            matched.cells.get(other) in (None, current)
            for other in group.members
            if other != member
        )
    ]
    references = [matched.name] + [
        item
        for other, item in matched.cells.items()
        if other != member and item is not None
    ]
    score = {
        name: max(_similarity(name, reference) for reference in references)
        for name in offered
    }
    position = {name: place for place, name in enumerate(_columns(data[member]))}
    return MatchChoices(
        current,
        tuple(
            sorted(
                (name for name in offered if score[name] >= _SIMILAR_AT),
                key=lambda name: (-score[name], position[name]),
            )
        ),
        tuple(
            sorted(
                (name for name in offered if score[name] < _SIMILAR_AT),
                key=position.__getitem__,
            )
        ),
        tuple(
            other
            for other in plan.present
            if other != member
            and current is not None
            and matched.cells.get(other) == current
        ),
    )


def set_match_item(
    stacked: StackedForm,
    data: Mapping[str, pd.DataFrame],
    index: int,
    member: str,
    item: Optional[str],
) -> StackedForm:
    """*stacked* with *member* giving *item* (``None``: nothing) to the match at *index*.

    Names line up whole same-name groups, so a change moves every member with
    the name: the current item's group leaves the match and *item*'s group
    joins it. Picking what the member gives now (an item standing in for a
    saved one it lost, or nothing) makes that the saved choice. A match left
    with no item goes. Raises :class:`ValueError` for an item the cell doesn't
    offer (:func:`match_choices`).
    """
    plan = layout(stacked, data)
    choices = match_choices(plan, data, index, member)
    match = stacked.matches[index]
    if item is not None and item not in (
        choices.current,
        *choices.similar,
        *choices.others,
    ):
        raise ValueError(f"{member} can't give {item} to {match.name}.")
    items = dict(match.items)
    if item == choices.current:
        if item is None:
            items.pop(member, None)
        else:
            items[member] = item
    else:
        items = {
            other: name
            for other, name in items.items()
            if other != member and name != choices.current
        }
        if item is not None:
            group = next(group for group in plan.left_out if group.name == item)
            items.update(dict.fromkeys(group.members, item))
    if items == dict(match.items):
        return stacked
    if not items:
        return remove_matches(stacked, [index])
    matches = list(stacked.matches)
    matches[index] = Match(match.name, items)
    return replace(stacked, matches=tuple(matches))


# ---------------------------------------------------------------------------
# The Apply check


def problems(
    stacked_forms: Sequence[StackedForm],
    loaded_form_names: Collection[str],
    data: Optional[Mapping[str, pd.DataFrame]] = None,
) -> List[str]:
    """What stops *stacked_forms* from being applied, one line each.

    Each line starts with its stacked form's name ("New stacked form" while
    it has none). *loaded_form_names* are the forms as loaded (Corelisting
    and additional inputs). With *data* (those forms), the checks that need
    the members' items run too: a match named like an item in every member,
    and a member with two items of one match.
    """
    loaded = set(loaded_form_names)
    names = [stacked.name.strip() for stacked in stacked_forms]
    counts = Counter(name for name in names if name)
    found = []
    for stacked, name in zip(stacked_forms, names):
        label = name or NEW_STACKED_FORM
        found.extend(
            f"{label}: {issue}"
            for issue in _issues(stacked, name, loaded, counts, data)
        )
    return found


def name_problem(
    stacked_forms: Sequence[StackedForm],
    index: int,
    loaded_form_names: Collection[str],
) -> str:
    """What's wrong with the name of the stacked form at *index*, or "".

    As :func:`problems` says it (without the stacked form's name in front),
    for a page that marks the name as it is typed.
    """
    names = [stacked.name.strip() for stacked in stacked_forms]
    counts = Counter(name for name in names if name)
    return _name_issue(names[index], set(loaded_form_names), counts)


def match_name_problem(stacked: StackedForm, plan: StackLayout, index: int) -> str:
    """What's wrong with the name of the match at *index*, or "".

    As :func:`problems` says it, over *stacked*'s :func:`layout` *plan* (a
    match can't take the name of an item every member has).
    """
    return _match_name_issue(
        stacked,
        stacked.matches[index].name.strip(),
        {group.name for group in plan.every},
    )


def _name_issue(
    name: str, loaded: Collection[str], stacked_names: Mapping[str, int]
) -> str:
    if not name:
        return "Give it a name."
    if FORM_ITEM_SEPARATOR in name:
        return f"A form name can't contain “{FORM_ITEM_SEPARATOR}”."
    if name in loaded:
        return f"{name} is already a loaded form."
    if stacked_names[name] > 1:
        return f"Another stacked form is called {name}."
    return ""


def _match_name_issue(
    stacked: StackedForm, match_name: str, every: Collection[str]
) -> str:
    if not match_name:
        return "Give the matched item a name."
    taken = Counter(match.name.strip() for match in stacked.matches)
    if match_name in every or taken[match_name] > 1:
        name = stacked.name.strip() or "This stacked form"
        return f"{name} already has an item called {match_name}."
    return ""


def _issues(
    stacked: StackedForm,
    name: str,
    loaded: Collection[str],
    stacked_names: Mapping[str, int],
    data: Optional[Mapping[str, pd.DataFrame]],
) -> List[str]:
    issues = []
    issue = _name_issue(name, loaded, stacked_names)
    if issue:
        issues.append(issue)
    if len(stacked.members) < 2:
        issues.append("Pick at least two members.")
    # A member named like a stacked form and a loaded form is the loaded form
    # (the stacked form's name is the problem then, reported on its own).
    issues.extend(
        f"{member} is a stacked form, so it can't be a member."
        for member in stacked.members
        if member in stacked_names and member not in loaded
    )

    plan = layout(stacked, data) if data is not None else None
    every = {group.name for group in plan.every} if plan else set()
    for match in stacked.matches:
        issue = _match_name_issue(stacked, match.name.strip(), every)
        if issue:
            issues.append(issue)
    for item_name, holders in _shared_item_names(stacked).items():
        both = "both " if len(holders) == 2 else ""
        issues.append(
            f"Keep each item in one match: {item_name} is in "
            f"{both}{feedback.and_list(holders)}."
        )
    if plan:
        for item in plan.matched:
            for member, have in item.doubled.items():
                both = "both " if len(have) == 2 else ""
                issues.append(
                    "Pick at most one item from each member: "
                    f"{member} has {both}{feedback.and_list(have)}."
                )
    return issues


# ---------------------------------------------------------------------------
# Saved settings


def to_settings(
    settings: MutableMapping[str, Any], stacked_forms: Sequence[StackedForm]
) -> MutableMapping[str, Any]:
    """Store *stacked_forms* in a settings dictionary; return *settings*.

    The key is only set when there are stacked forms, so a setting without
    them is saved exactly as before the key existed.
    """
    if not stacked_forms:
        settings.pop(SETTINGS_KEY, None)
        return settings
    settings[SETTINGS_KEY] = [
        {
            "name": stacked.name,
            "members": list(stacked.members),
            "matches": [
                {"name": match.name, "items": dict(match.items)}
                for match in stacked.matches
            ],
        }
        for stacked in stacked_forms
    ]
    return settings


def _match_from(item: Any, members: Collection[str]) -> Optional[Match]:
    """One saved match, or ``None`` if *item* isn't a usable one."""
    if not isinstance(item, Mapping):
        return None
    name = item.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    items = item.get("items")
    if not isinstance(items, Mapping):
        return None
    kept = {
        member: column
        for member, column in items.items()
        if member in members and isinstance(column, str) and column
    }
    return Match(name.strip(), kept) if kept else None


def _stacked_form_from(item: Any) -> Optional[StackedForm]:
    """One saved stacked form, or ``None`` if *item* isn't a usable one."""
    if not isinstance(item, Mapping):
        return None
    name = item.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    members = item.get("members")
    if not isinstance(members, list):
        return None
    members = tuple(
        dict.fromkeys(
            member.strip()
            for member in members
            if isinstance(member, str) and member.strip()
        )
    )
    raw_matches = item.get("matches") or []
    if not isinstance(raw_matches, list):
        return None
    matches = []
    for position, raw in enumerate(raw_matches):
        match = _match_from(raw, members)
        if match is None:
            logger.warning(
                "Skipping saved match %d of stacked form %s: %r",
                position,
                name.strip(),
                raw,
            )
        else:
            matches.append(match)
    return StackedForm(name.strip(), members, tuple(matches))


def from_settings(settings: Any) -> List[StackedForm]:
    """The stacked forms saved in a settings dictionary, in their saved order.

    Settings without the key give none. A hand-edited or damaged entry never
    stops a setting from loading: it is skipped and logged.
    """
    raw = settings.get(SETTINGS_KEY) if isinstance(settings, Mapping) else None
    if raw is None:
        return []
    if not isinstance(raw, list):
        logger.warning("Ignoring saved %s: not a list", SETTINGS_KEY)
        return []
    stacked_forms: List[StackedForm] = []
    seen = set()
    for position, item in enumerate(raw):
        stacked = _stacked_form_from(item)
        if stacked is None or stacked.name in seen:
            logger.warning(
                "Skipping saved %s entry %d: %r", SETTINGS_KEY, position, item
            )
            continue
        seen.add(stacked.name)
        stacked_forms.append(stacked)
    return stacked_forms


__all__ = [
    "NEW_STACKED_FORM",
    "SETTINGS_KEY",
    "Built",
    "ItemGroup",
    "Match",
    "MatchChoices",
    "MatchedItem",
    "StackLayout",
    "StackedForm",
    "add_match",
    "build",
    "build_all",
    "from_settings",
    "layout",
    "match_choices",
    "match_name_problem",
    "name_problem",
    "problems",
    "remove_matches",
    "rename_match",
    "set_match_item",
    "to_settings",
    "with_members",
]
