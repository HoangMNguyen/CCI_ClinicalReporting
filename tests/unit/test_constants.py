"""Tests for core.constants and the shared core._helpers.move_item helper."""

from clinical_reporting.core._helpers import move_item
from clinical_reporting.core.constants import (
    FORM_ITEM_SEPARATOR,
    SUBJECT_COLUMN,
    JoinHow,
    Operator,
    is_qualified,
    qualify,
    split_qualified,
)


# ---------------------------------------------------------------------------
# JoinHow


def test_joinhow_to_pandas_maps_all_labels():
    assert JoinHow.to_pandas(JoinHow.LEFT) == "left"
    assert JoinHow.to_pandas(JoinHow.RIGHT) == "right"
    assert JoinHow.to_pandas(JoinHow.INNER) == "inner"
    assert JoinHow.to_pandas(JoinHow.OUTER) == "outer"


def test_joinhow_to_pandas_defaults_for_none_and_unknown():
    assert JoinHow.to_pandas(None) == "left"
    assert JoinHow.to_pandas("") == "left"
    assert JoinHow.to_pandas("Bogus join") == "left"
    assert JoinHow.to_pandas(None, default="inner") == "inner"


def test_joinhow_all_is_the_ordered_label_set():
    assert JoinHow.ALL == ("Left join", "Right join", "Inner join", "Outer join")


# ---------------------------------------------------------------------------
# Operator


def test_operator_groupings():
    assert set(Operator.DYNAMIC) == {"=", "!=", ">", ">=", "<", "<="}
    assert Operator.IS_NULL in Operator.STATIC
    assert Operator.IS_NULL not in Operator.DYNAMIC
    assert Operator.NULLARY == ("is Null", "is not Null")
    # Every dynamic operator is also a valid static operator.
    assert set(Operator.DYNAMIC).issubset(set(Operator.STATIC))


# ---------------------------------------------------------------------------
# Qualified-name helpers


def test_constants_separator_and_subject():
    assert FORM_ITEM_SEPARATOR == "."
    assert SUBJECT_COLUMN == "Subject"


def test_qualify_and_split_roundtrip():
    assert qualify("DM", "Age") == "DM.Age"
    assert is_qualified("DM.Age")
    assert not is_qualified("Age")
    assert split_qualified("DM.Age") == ("DM", "Age")


def test_split_qualified_splits_on_first_separator_only():
    # Item names may themselves contain dots; only the first separator splits.
    assert split_qualified("DM.Legal Sex (ig_DM1.SEX)") == ("DM", "Legal Sex (ig_DM1.SEX)")


# ---------------------------------------------------------------------------
# move_item


def test_move_item_moves_and_dedupes():
    source = ["a", "b"]
    target = ["c"]
    assert move_item("a", source, target) is True
    assert source == ["b"]
    assert target == ["c", "a"]


def test_move_item_does_not_duplicate_in_target():
    source = ["a"]
    target = ["a"]
    # Removed from source; not re-added to target -> still reports a change.
    assert move_item("a", source, target) is True
    assert source == []
    assert target == ["a"]


def test_move_item_is_noop_when_absent_from_source_and_already_in_target():
    source = ["a"]
    target = ["z"]
    assert move_item("z", source, target) is False
    assert source == ["a"]
    assert target == ["z"]


def test_move_item_supports_remove_only_and_add_only():
    source = ["a"]
    assert move_item("a", source, None) is True
    assert source == []

    target = []
    assert move_item("x", None, target) is True
    assert target == ["x"]
