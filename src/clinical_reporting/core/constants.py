"""Shared constants and small helpers for the reporting domain.

Centralises the magic strings that were previously duplicated across the engine
and the UI: join strategies, filter operators, and the ``form.item`` qualified
identifier convention. Keeping them here gives a single source of truth so the
UI dropdowns and the engine can never drift apart.
"""

from __future__ import annotations

# Separator between a form name and an item name in a qualified identifier
# (e.g. ``"DM.Age"``). Form names are not allowed to contain it.
FORM_ITEM_SEPARATOR = "."

# The common column treated as the subject identifier throughout the tool.
SUBJECT_COLUMN = "Subject"


class JoinHow:
    """Join strategy labels (as persisted in settings) and their pandas mapping."""

    LEFT = "Left join"
    RIGHT = "Right join"
    INNER = "Inner join"
    OUTER = "Outer join"

    #: Ordered labels, suitable for populating a UI dropdown.
    ALL = (LEFT, RIGHT, INNER, OUTER)

    _TO_PANDAS = {LEFT: "left", RIGHT: "right", INNER: "inner", OUTER: "outer"}

    @classmethod
    def to_pandas(cls, label: str | None, default: str = "left") -> str:
        """Translate a join label to the pandas ``merge(how=...)`` value."""
        return cls._TO_PANDAS.get(label or "", default)


class Operator:
    """Filter operator labels (as shown in the UI and stored in settings)."""

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

    #: Operators offered for static (column-vs-value) filters.
    STATIC = (EQ, NE, GT, GE, LT, LE, CONTAINS, NOT_CONTAINS, IN, NOT_IN, IS_NULL, IS_NOT_NULL)
    #: Operators offered for dynamic (column-vs-column) filters.
    DYNAMIC = (EQ, NE, GT, GE, LT, LE)
    #: Operators that ignore the value field.
    NULLARY = (IS_NULL, IS_NOT_NULL)


def qualify(form_name: str, item: str) -> str:
    """Build a qualified ``"form.item"`` identifier."""
    return f"{form_name}{FORM_ITEM_SEPARATOR}{item}"


def is_qualified(name: str) -> bool:
    """Return ``True`` when ``name`` contains the form/item separator."""
    return FORM_ITEM_SEPARATOR in name


def split_qualified(name: str) -> tuple[str, str]:
    """Split ``"form.item"`` into ``(form, item)`` on the first separator.

    Callers should guard with :func:`is_qualified`; for an unqualified name the
    whole string is returned as the form part and the item part is empty.
    """
    form_name, _, item = name.partition(FORM_ITEM_SEPARATOR)
    return form_name, item
