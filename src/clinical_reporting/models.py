"""Domain models, configuration, constants, and identifier helpers."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, TypeVar, Union

FORM_ITEM_SEPARATOR = "."
SUBJECT_COLUMN = "Subject"

T = TypeVar("T")
PathLike = Union[str, Path]


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

    def _move_item(
        self,
        source: Optional[List[str]],
        target: Optional[List[str]],
        item: str,
        order: Optional[List[str]] = None,
    ) -> bool:
        return move_item(item, source, target, order)

    def get_name(self):
        return self.name

    def set_name(self, name: str):
        self.name = name

    def get_selected_form_items(self):
        return self.selected_form_items

    def set_form_item_state(self, item: str, *, selected: bool) -> bool:
        source, target = (
            (self.available_form_items, self.selected_form_items)
            if selected
            else (self.selected_form_items, self.available_form_items)
        )
        return self._move_item(source, target, item, order=self.column_order)

    def get_available_form_items(self):
        return self.available_form_items

    def remove_form_item(self, item: str) -> bool:
        removed_selected = self._move_item(self.selected_form_items, None, item)
        removed_available = self._move_item(self.available_form_items, None, item)
        return removed_selected or removed_available

    def set_join_how(self, how: str):
        self.join_how = how

    def get_join_how(self):
        return self.join_how

    def set_join_item_state(self, item: str, *, include: bool) -> bool:
        if include:
            return self._move_item(None, self.join_items, item)
        return self._move_item(self.join_items, None, item)

    def clear_join_items(self):
        self.join_items = []

    def get_join_items(self):
        return self.join_items

    def set_join_items(self, items: list):
        self.join_items = deepcopy(items)

    def set_join_order(self, order: int):
        self.join_order = order

    def get_join_order(self):
        return self.join_order

    def remove_join_order(self):
        self.join_order = None


@dataclass
class ReportConfig:
    """Typed wrapper around the backward-compatible settings dictionary."""

    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReportConfig":
        return cls(deepcopy(dict(data)))

    @classmethod
    def from_settings_json(cls, file_path: PathLike) -> "ReportConfig":
        with open(file_path, "r", encoding="utf-8") as handle:
            return cls(json.load(handle))

    def to_settings_json(self, file_path: PathLike) -> None:
        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump(self.raw, handle, indent=4)

    def to_dict(self) -> Dict[str, Any]:
        return deepcopy(self.raw)

    @property
    def study_name(self) -> Optional[str]:
        return self.raw.get("study_name")

    @property
    def setting_name(self) -> Optional[str]:
        return self.raw.get("setting_name")


__all__ = [
    "CLForm",
    "FORM_ITEM_SEPARATOR",
    "JoinHow",
    "Operator",
    "ReportConfig",
    "SUBJECT_COLUMN",
    "is_qualified",
    "move_item",
    "qualify",
    "split_qualified",
]
