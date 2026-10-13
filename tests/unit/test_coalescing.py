"""Coalesced items over made-up forms (clinical_reporting.coalescing)."""

import logging
from dataclasses import replace

import pandas as pd

from clinical_reporting import coalescing
from clinical_reporting.coalescing import (
    KEEP_EARLIER,
    SETTINGS_KEY,
    CoalescedItem,
    Fill,
    Overlap,
)


def _dm():
    """DM with Race, and Race Other Specify filled in on some of its rows."""
    return pd.DataFrame(
        {
            "Subject": ["101-001", "101-002", "101-003"],
            "Race": ["White", None, "Asian"],
            "Age": [34, 51, 47],
            "Race Other Specify": [None, "Hispanic", None],
        }
    )


def _race(*fills, name="Race"):
    return CoalescedItem("DM", name, "Race", fills or (Fill("Race Other Specify"),))


# --- build ----------------------------------------------------------------


def test_a_later_item_fills_the_empty_rows_and_leaves_the_form():
    outcome = coalescing.build(_race(), _dm())

    assert list(outcome.frame.columns) == ["Subject", "Race", "Age"]
    assert outcome.frame["Race"].tolist() == ["White", "Hispanic", "Asian"]
    assert outcome.frame["Age"].tolist() == [34, 51, 47]


def test_a_condition_lets_a_later_item_replace_a_value_whatever_its_case():
    dm = pd.DataFrame(
        {
            "Subject": ["101-001", "101-002", "101-003"],
            "Race": ["White", "OTHER", "Other"],
            "Race Other Specify": [None, "Hispanic", None],
        }
    )

    outcome = coalescing.build(_race(Fill("Race Other Specify", "=", "other")), dm)

    # Nothing fills the last row, so its Other stays.
    assert outcome.frame["Race"].tolist() == ["White", "Hispanic", "Other"]


def test_text_of_only_spaces_counts_as_empty():
    dm = pd.DataFrame(
        {
            "Subject": ["101-001", "101-002", "101-003"],
            "Race": ["  ", "White", None],
            "Race Other Specify": ["Hispanic", "   ", " "],
        }
    )

    outcome = coalescing.build(_race(), dm)

    # A blank later value fills nothing.
    assert outcome.frame["Race"].fillna("<empty>").tolist() == [
        "Hispanic",
        "White",
        "<empty>",
    ]


def _three_items():
    """The rows agreed for Race ← Race Other Specify ← Race Free Text."""
    return pd.DataFrame(
        {
            "Subject": [f"101-00{row}" for row in range(1, 8)],
            "Race": ["White", "Other", "Other", None, "White", "White", "Other"],
            "Race Other Specify": [
                None,
                "Hispanic",
                None,
                None,
                "Caucasian",
                "Other",
                "Hispanic",
            ],
            "Race Free Text": [None, None, None, "Mixed", None, None, "Mixed"],
        }
    )


RACE_THREE = CoalescedItem(
    "DM",
    "Race",
    "Race",
    (
        Fill("Race Other Specify", "=", "Other"),
        # Tested on the value so far (Race, or what Race Other Specify gave it).
        Fill("Race Free Text", "=", "Other"),
    ),
)


def test_each_later_item_fills_the_value_so_far_in_turn():
    outcome = coalescing.build(RACE_THREE, _three_items())

    assert outcome.frame["Race"].tolist() == [
        "White",
        "Hispanic",
        "Other",
        "Mixed",
        "White",  # Caucasian overlaps: the earlier value stays
        "White",  # so does Other, a value too
        "Hispanic",  # Mixed overlaps the Hispanic Race Other Specify gave
    ]
    assert list(outcome.frame.columns) == ["Subject", "Race"]


def test_an_overlap_names_its_row_and_both_values_and_rows_are_counted_by_item():
    outcome = coalescing.build(RACE_THREE, _three_items())

    assert outcome.overlaps == (
        Overlap(5, "101-005", "Race Other Specify", "White", "Caucasian"),
        Overlap(6, "101-006", "Race Other Specify", "White", "Other"),
        Overlap(7, "101-007", "Race Free Text", "Hispanic", "Mixed"),
    )
    assert dict(outcome.rows) == {
        "Race": 4,
        "Race Other Specify": 2,
        "Race Free Text": 1,
    }
    assert outcome.empty == 0


def test_a_form_without_subject_names_an_overlap_by_its_row_alone():
    form = pd.DataFrame({"A": ["x", None, None], "B": ["y", None, "z"]})

    outcome = coalescing.build(CoalescedItem("F", "A", "A", (Fill("B"),)), form)

    assert outcome.overlaps == (Overlap(1, None, "B", "x", "y"),)
    assert (dict(outcome.rows), outcome.empty) == ({"A": 1, "B": 1}, 1)


def test_an_outcome_counts_the_rows_filled_and_the_rows_that_overlap():
    outcome = coalescing.build(RACE_THREE, _three_items())

    assert (outcome.filled, outcome.overlapping) == (3, 3)


def test_a_new_name_puts_the_coalesced_item_where_its_first_item_was():
    outcome = coalescing.build(_race(name="Race (all)"), _dm())

    assert list(outcome.frame.columns) == ["Subject", "Race (all)", "Age"]
    assert outcome.frame["Race (all)"].tolist() == ["White", "Hispanic", "Asian"]


def test_a_later_items_name_still_puts_it_where_its_first_item_was():
    outcome = coalescing.build(_race(name="Race Other Specify"), _dm())

    assert list(outcome.frame.columns) == ["Subject", "Race Other Specify", "Age"]


# --- the Apply check ------------------------------------------------------


def _forms():
    """DM, whose Race and Ethnicity are each filled in or specified, and AE."""
    dm = _dm().assign(
        **{
            "Ethnicity": [None, "Not Hispanic", None],
            "Ethnicity Other": ["Mixed", None, "Mixed"],
        }
    )
    return {
        "DM": dm,
        "AE": pd.DataFrame({"Subject": ["101-001"], "AE Term": ["Headache"]}),
    }


def test_well_made_coalesced_items_have_no_problems():
    ethnicity = CoalescedItem(
        "DM", "Ethnicity", "Ethnicity", (Fill("Ethnicity Other"),)
    )

    assert coalescing.problems([_race(), ethnicity], _forms()) == []


def test_a_coalesced_item_needs_a_loaded_form_and_two_of_its_items():
    items = [
        CoalescedItem("", "Race", "Race", (Fill("Race Other Specify"),)),
        CoalescedItem("LB", "Unit", "Unit", (Fill("Unit Other"),)),
        CoalescedItem("DM", "Age", "Age"),
        CoalescedItem("DM", "Sex", "Sex", (Fill(""), Fill("Ethnicity Other"))),
    ]

    assert coalescing.problems(items, _forms()) == [
        "Race: Pick its form.",
        "Unit in LB: LB isn't loaded.",
        "Age in DM: Pick at least two items.",
        "Sex in DM: Pick an item in each row.",
        "Sex in DM: DM has no Sex.",
    ]


def test_each_item_is_in_one_coalesced_item_once():
    items = [
        _race(Fill("Race Other Specify"), Fill("Race Other Specify")),
        CoalescedItem("DM", "Ethnicity", "Ethnicity", (Fill("Race Other Specify"),)),
    ]

    assert coalescing.problems(items, _forms()) == [
        "Race in DM: Race Other Specify is in it twice.",
        "Ethnicity in DM: Race Other Specify is already in Race.",
    ]


def test_a_name_is_given_and_free_in_its_form():
    origin = CoalescedItem("DM", "Origin", "Ethnicity", (Fill("Ethnicity Other"),))

    assert coalescing.problems([_race(name=" ")], _forms()) == [
        "New coalesced item in DM: Give it a name."
    ]
    assert coalescing.problems([_race(name="Age")], _forms()) == [
        "Age in DM: DM already has an item called Age."
    ]
    assert coalescing.problems([_race(name="Origin"), origin], _forms()) == [
        "Origin in DM: Another coalesced item of DM is called Origin.",
        "Origin in DM: Another coalesced item of DM is called Origin.",
    ]


def test_one_coalesced_items_problems_read_as_apply_says_them():
    items = [
        _race(name="Age"),
        CoalescedItem("DM", "Ethnicity", "Ethnicity", (Fill("Race Other Specify"),)),
    ]

    assert coalescing.problems_of(items, 1, _forms()) == [
        "Race Other Specify is already in Age."
    ]
    assert coalescing.name_problem(items, 0, _forms()) == (
        "DM already has an item called Age."
    )
    assert coalescing.name_problem(items, 1, _forms()) == ""


def test_a_preview_is_what_a_coalesced_item_gives_once_it_can_be_built():
    items = [_race(), CoalescedItem("DM", "Ethnicity", "Ethnicity", (Fill(""),))]

    preview = coalescing.preview(items, 0, _forms())

    assert preview.frame["Race"].tolist() == ["White", "Hispanic", "Asian"]
    assert coalescing.preview(items, 1, _forms()) is None


def test_a_common_item_is_only_coalesced_under_its_own_name():
    forms = {
        "DM": pd.DataFrame(
            {"Subject": ["101-001"], "Visit": [None], "Unscheduled Visit": ["U1"]}
        ),
        "AE": pd.DataFrame({"Subject": ["101-001"], "Visit": ["V2"]}),
    }
    keeps_its_name = CoalescedItem("DM", "Visit", "Visit", (Fill("Unscheduled Visit"),))

    assert coalescing.problems([keeps_its_name], forms) == []
    assert coalescing.problems([replace(keeps_its_name, name="Any Visit")], forms) == [
        "Any Visit in DM: Visit is a common item: name the coalesced item Visit, or "
        "leave Visit out."
    ]


def test_a_condition_needs_a_value():
    item = _race(Fill("Race Other Specify", "=", "  "))

    assert coalescing.problems([item], _forms()) == [
        "Race in DM: Give the condition for Race Other Specify a value."
    ]


def test_overlaps_stop_apply_unless_the_earlier_value_is_kept():
    forms = {"DM": _three_items()}

    assert coalescing.problems([RACE_THREE], forms) == [
        "Race in DM: 2 rows have a value in Race Other Specify where Race already "
        "has one: 101-005 (White / Caucasian), 101-006 (White / Other).",
        "Race in DM: 1 row has a value in Race Free Text where Race already has "
        "one: 101-007 (Hispanic / Mixed).",
    ]
    assert (
        coalescing.problems([replace(RACE_THREE, on_overlap=KEEP_EARLIER)], forms) == []
    )


def test_an_overlap_problem_shows_its_first_five_rows():
    form = pd.DataFrame(
        {"Subject": [f"S{n}" for n in range(1, 8)], "A": ["x"] * 7, "B": ["y"] * 7}
    )
    item = CoalescedItem("F", "A", "A", (Fill("B"),))

    assert coalescing.problems([item], {"F": form}) == [
        "A in F: 7 rows have a value in B where A already has one: S1 (x / y), "
        "S2 (x / y), S3 (x / y), S4 (x / y), S5 (x / y) and 2 more."
    ]
    assert coalescing.problems([item], {"F": form.drop(columns="Subject")[:1]}) == [
        "A in F: 1 row has a value in B where A already has one: row 1 (x / y)."
    ]


def test_overlap_values_show_as_the_export_shows_them():
    form = pd.DataFrame(
        {
            "Subject": ["101-001"],
            "Dose": [10.0],
            "Dose Text": ["10 mg"],
            "Start Date": [pd.Timestamp("2026-01-05")],
            "Start Date Text": ["early Jan"],
        }
    )
    items = [
        CoalescedItem("EX", "Dose", "Dose", (Fill("Dose Text"),)),
        CoalescedItem("EX", "Start Date", "Start Date", (Fill("Start Date Text"),)),
    ]

    assert coalescing.problems(items, {"EX": form}) == [
        "Dose in EX: 1 row has a value in Dose Text where Dose already has one: "
        "101-001 (10 / 10 mg).",
        "Start Date in EX: 1 row has a value in Start Date Text where Start Date "
        "already has one: 101-001 (1/5/2026 / early Jan).",
    ]


def test_with_one_form_loaded_no_item_is_held_to_its_name():
    # One form has no joins, so its items aren't common items to keep.
    item = CoalescedItem("F", "Any", "A", (Fill("B"),))

    assert (
        coalescing.problems([item], {"F": pd.DataFrame({"A": ["x"], "B": [None]})})
        == []
    )


# --- saved settings -------------------------------------------------------

SAVED_RACE = {
    "form": "DM",
    "name": "Race",
    "first": "Race",
    "fills": [
        {"item": "Race Other Specify", "operator": "=", "value": "Other"},
        {"item": "Race Free Text", "operator": "=", "value": "Other"},
    ],
    "on_overlap": "refuse",
}


def test_coalesced_items_are_saved_and_read_back():
    outcome = CoalescedItem(
        "AE", "Outcome", "Outcome", (Fill("Outcome Other"),), KEEP_EARLIER
    )

    settings = coalescing.to_settings(
        {"setting_name": "monthly"}, [RACE_THREE, outcome]
    )

    assert settings == {
        "setting_name": "monthly",
        SETTINGS_KEY: [
            SAVED_RACE,
            {
                "form": "AE",
                "name": "Outcome",
                "first": "Outcome",
                "fills": [{"item": "Outcome Other"}],
                "on_overlap": "keep_earlier",
            },
        ],
    }
    assert coalescing.from_settings(settings) == [RACE_THREE, outcome]


def test_without_coalesced_items_the_key_is_not_saved():
    settings = {"setting_name": "monthly", SETTINGS_KEY: [SAVED_RACE]}

    assert coalescing.to_settings(settings, []) == {"setting_name": "monthly"}
    assert coalescing.from_settings({"setting_name": "monthly"}) == []
    assert coalescing.from_settings(None) == []


def test_a_key_that_is_not_a_list_is_ignored(caplog):
    with caplog.at_level(logging.WARNING):
        assert coalescing.from_settings({SETTINGS_KEY: SAVED_RACE}) == []

    assert "not a list" in caplog.text


def test_damaged_entries_are_skipped_and_the_rest_kept(caplog):
    junk = [
        "Race",
        {**SAVED_RACE, "form": " "},
        {**SAVED_RACE, "name": ""},
        {**SAVED_RACE, "first": 3},
        {**SAVED_RACE, "fills": []},
        {**SAVED_RACE, "fills": ["Race Other Specify"]},
        {**SAVED_RACE, "fills": [{"item": "Race Other Specify", "operator": "~"}]},
        {**SAVED_RACE, "on_overlap": "sometimes"},
        {**SAVED_RACE, "form": " DM "},  # Repeats a name in its form.
    ]
    tolerated = {
        "form": " DM ",
        "name": " Race ",
        "first": "Race",
        "fills": [{"item": "Race Other Specify"}],
    }

    with caplog.at_level(logging.WARNING):
        items = coalescing.from_settings({SETTINGS_KEY: [tolerated, *junk]})

    assert items == [_race()]
    assert caplog.text.count("Skipping saved coalesced_items entry") == len(junk)
