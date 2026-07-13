"""Tests for the services.transforms static/dynamic DataFrame filters."""

import pandas as pd

from clinical_reporting.services.transforms import apply_dynamic_filter, apply_static_filter


def _people():
    return pd.DataFrame({"Age": [25, 40, 75], "Name": ["amy", "BOB", "cat"]})


# ---------------------------------------------------------------------------
# Static filters


def test_static_filter_numeric_comparison():
    out = apply_static_filter(_people(), "Age", ">", "30")
    assert out["Age"].tolist() == [40, 75]


def test_static_filter_string_equality_is_case_insensitive():
    out = apply_static_filter(_people(), "Name", "=", "bob")
    assert out["Name"].tolist() == ["BOB"]


def test_static_filter_contains_and_in():
    df = _people()
    assert apply_static_filter(df, "Name", "Contains", "a")["Name"].tolist() == ["amy", "cat"]
    assert apply_static_filter(df, "Age", "In", "25, 75")["Age"].tolist() == [25, 75]


def test_static_filter_null_operators():
    df = pd.DataFrame({"X": [1, None, 3]})
    assert apply_static_filter(df, "X", "is Null", "")["X"].isnull().all()
    assert len(apply_static_filter(df, "X", "is not Null", "")) == 2


def test_static_filter_missing_column_is_noop():
    df = _people()
    assert apply_static_filter(df, "Missing", "=", "x").equals(df)


# ---------------------------------------------------------------------------
# Dynamic filters


def test_dynamic_filter_compares_two_columns():
    df = pd.DataFrame({"A": [1, 5, 3], "B": [2, 2, 3]})
    assert apply_dynamic_filter(df, "A", ">", "B")["A"].tolist() == [5]
    assert apply_dynamic_filter(df, "A", "=", "B")["A"].tolist() == [3]


def test_dynamic_filter_missing_column_is_noop():
    df = pd.DataFrame({"A": [1]})
    assert apply_dynamic_filter(df, "A", ">", "Missing").equals(df)
