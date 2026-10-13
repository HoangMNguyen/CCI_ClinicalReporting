"""Domain models, constants, and identifier helpers."""

from __future__ import annotations

from typing import Any, List, Mapping, Optional, Sequence, TypeVar

FORM_ITEM_SEPARATOR = "."
SUBJECT_COLUMN = "Subject"

T = TypeVar("T")


class JoinHow:
    """Persisted join labels and their pandas equivalents."""

    LEFT = "Left join"
    RIGHT = "Right join"
    INNER = "Inner join"
    OUTER = "Outer join"
    ALL = (LEFT, RIGHT, INNER, OUTER)
    _TO_PANDAS = {LEFT: "left", RIGHT: "right", INNER: "inner", OUTER: "outer"}

    @classmethod
    def to_pandas(cls, label: str | None, default: str = "left") -> str:
        return cls._TO_PANDAS.get(label or "", default)


class Operator:
    """Filter labels shared by settings, the UI, validation, and execution."""

    EQ = "="
    NE = "!="
    GT = ">"
    GE = ">="
    LT = "<"
    LE = "<="
    CONTAINS = "Contains"
    NOT_CONTAINS = "Does not contain"
    IN = "In"
    NOT_IN = "Not in"
    IS_NULL = "is Null"
    IS_NOT_NULL = "is not Null"
    STATIC = (
        EQ,
        NE,
        GT,
        GE,
        LT,
        LE,
        CONTAINS,
        NOT_CONTAINS,
        IN,
        NOT_IN,
        IS_NULL,
        IS_NOT_NULL,
    )
    DYNAMIC = (EQ, NE, GT, GE, LT, LE)
    NULLARY = (IS_NULL, IS_NOT_NULL)


def common_items(forms: Mapping[str, Any]) -> List[str]:
    """The items every one of *forms* (DataFrames by name) has.

    In the first form's column order, so common items keep the file's order
    rather than an alphabetical one.
    """
    frames = list(forms.values())
    if not frames:
        return []
    common = set(frames[0].columns)
    for frame in frames[1:]:
        common &= set(frame.columns)
    return [column for column in frames[0].columns if column in common]


def is_positive_integer(value) -> bool:
    """Whether *value* is a whole number above zero (and not a bool)."""
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def qualify(form_name: str, item: str) -> str:
    """Build a qualified ``form.item`` identifier."""
    return f"{form_name}{FORM_ITEM_SEPARATOR}{item}"


def is_qualified(name: str) -> bool:
    """Return whether a name contains the form/item separator."""
    return FORM_ITEM_SEPARATOR in name


def split_qualified(name: str) -> tuple[str, str]:
    """Split a qualified identifier on its first separator."""
    form_name, _, item = name.partition(FORM_ITEM_SEPARATOR)
    return form_name, item


def move_item(
    item: T,
    source: Optional[List[T]],
    target: Optional[List[T]],
    order: Optional[Sequence[T]] = None,
) -> bool:
    """Move an item between optional lists, preserving a reference order."""
    changed = False
    if source is not None and item in source:
        source.remove(item)
        changed = True
    if target is not None and item not in target:
        _insert_in_order(target, item, order)
        changed = True
    return changed


def _insert_in_order(target: List[T], item: T, order: Optional[Sequence[T]]) -> None:
    rank = None
    if order:
        try:
            rank = order.index(item)
        except ValueError:
            pass
    if rank is None:
        target.append(item)
        return
    for position, existing in enumerate(target):
        try:
            existing_rank = order.index(existing)
        except ValueError:
            target.insert(position, item)
            return
        if existing_rank > rank:
            target.insert(position, item)
            return
    target.append(item)


class CLForm:
    """Selection and join state for one clinical form."""

    def __init__(self, name: str):
        self.name = name
        self.available_form_items: List[str] = []
        self.selected_form_items: List[str] = []
        self.column_order: List[str] = []
        self.join_items: List[str] = []
        self.join_order = None
        self.join_how = None

    def get_name(self):
        return self.name

    def get_selected_form_items(self):
        return self.selected_form_items

    def set_form_item_state(self, item: str, *, selected: bool) -> bool:
        source, target = (
            (self.available_form_items, self.selected_form_items)
            if selected
            else (self.selected_form_items, self.available_form_items)
        )
        return move_item(item, source, target, self.column_order)

    def get_available_form_items(self):
        return self.available_form_items

    def remove_form_item(self, item: str) -> bool:
        removed_selected = move_item(item, self.selected_form_items, None)
        removed_available = move_item(item, self.available_form_items, None)
        return removed_selected or removed_available

    def set_join_how(self, how: str):
        self.join_how = how

    def get_join_how(self):
        return self.join_how

    def get_join_items(self):
        return self.join_items

    def set_join_items(self, items: list):
        self.join_items = list(items or [])  # None (no join items) is []

    def set_join_order(self, order: int):
        self.join_order = order

    def get_join_order(self):
        return self.join_order


__all__ = [
    "CLForm",
    "FORM_ITEM_SEPARATOR",
    "JoinHow",
    "Operator",
    "SUBJECT_COLUMN",
    "common_items",
    "is_qualified",
    "move_item",
    "qualify",
    "split_qualified",
]
