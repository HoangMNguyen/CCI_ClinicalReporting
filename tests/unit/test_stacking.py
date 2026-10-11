"""Stacked forms over made-up forms (clinical_reporting.stacking)."""

import logging

import numpy as np
import pandas as pd
import pytest

from clinical_reporting import stacking
from clinical_reporting.stacking import (
    SETTINGS_KEY,
    ItemGroup,
    Match,
    StackedForm,
)

NAN = np.nan


def _data():
    """SV and DSSVLTFU: Subject and Visit in both, the rest in one of them."""
    return {
        "SV": pd.DataFrame(
            {
                "Subject": ["001", "002"],
                "Event Group Name": ["Screening", "Week 1"],
                "Visit": [1, 2],
                "Visit Status": ["Done", "Missed"],
            }
        ),
        "DSSVLTFU": pd.DataFrame(
            {
                "Event Label": ["Follow-up"],
                "Subject": ["003"],
                "Visit": [9],
                "LTFUDAT": ["2026-01-05"],
            }
        ),
    }


VISIT_NAME = Match("Visit Name", {"SV": "Event Group Name", "DSSVLTFU": "Event Label"})


def _visits(*matches, members=("SV", "DSSVLTFU")):
    return StackedForm("VISITS", members, matches)


# --- layout ---------------------------------------------------------------


def test_same_name_items_line_up_by_themselves_and_the_rest_are_left_out():
    plan = stacking.layout(_visits(), _data())

    assert plan.present == ("SV", "DSSVLTFU") and plan.missing == ()
    assert plan.every == (
        ItemGroup("Subject", ("SV", "DSSVLTFU")),
        ItemGroup("Visit", ("SV", "DSSVLTFU")),
    )
    assert plan.left_out == (
        ItemGroup("Event Group Name", ("SV",)),
        ItemGroup("Visit Status", ("SV",)),
        ItemGroup("Event Label", ("DSSVLTFU",)),
        ItemGroup("LTFUDAT", ("DSSVLTFU",)),
    )
    assert plan.matched == ()
    assert plan.order == ("Subject", "Visit")
    assert plan.rows == 3


def test_names_are_exact_and_case_sensitive():
    data = {
        "A": pd.DataFrame({"Subject": ["1"], "visit": [1]}),
        "B": pd.DataFrame({"Subject": ["2"], "Visit": [2]}),
    }

    plan = stacking.layout(StackedForm("S", ("A", "B")), data)

    assert [group.name for group in plan.every] == ["Subject"]
    assert [group.name for group in plan.left_out] == ["visit", "Visit"]


def test_a_match_takes_each_members_item_and_sits_where_its_first_item_appears():
    plan = stacking.layout(_visits(VISIT_NAME), _data())

    (item,) = plan.matched
    assert (item.name, item.index, dict(item.cells), item.missing) == (
        "Visit Name",
        0,
        {"SV": "Event Group Name", "DSSVLTFU": "Event Label"},
        (),
    )
    assert plan.order == ("Subject", "Visit Name", "Visit")
    assert [group.name for group in plan.left_out] == ["Visit Status", "LTFUDAT"]


def test_a_single_item_match_keeps_an_item_not_every_member_has():
    plan = stacking.layout(
        _visits(Match("Visit Status", {"SV": "Visit Status"})), _data()
    )

    assert dict(plan.matched[0].cells) == {"SV": "Visit Status", "DSSVLTFU": None}
    assert plan.matched[0].missing == ()
    assert plan.order == ("Subject", "Visit", "Visit Status")


def test_a_match_never_splits_a_same_name_group():
    data = {
        "M1": pd.DataFrame({"Subject": ["1"], "Note": ["a"]}),
        "M2": pd.DataFrame({"Subject": ["2"], "Note": ["b"]}),
        "M3": pd.DataFrame({"Subject": ["3"], "Remark": ["c"]}),
    }
    # Saved with M1's Note only: M2's Note goes with it all the same.
    stacked = StackedForm("S", ("M1", "M2", "M3"), (Match("Note", {"M1": "Note"}),))

    plan = stacking.layout(stacked, data)

    assert dict(plan.matched[0].cells) == {"M1": "Note", "M2": "Note", "M3": None}
    assert [group.name for group in plan.left_out] == ["Remark"]


def test_a_member_added_later_joins_a_match_by_name():
    data = {
        **_data(),
        "EXTRA": pd.DataFrame(
            {"Subject": ["004"], "Visit": [3], "Event Label": ["Unscheduled"]}
        ),
    }
    stacked = stacking.with_members(_visits(VISIT_NAME), ["SV", "DSSVLTFU", "EXTRA"])

    plan = stacking.layout(stacked, data)

    assert dict(plan.matched[0].cells) == {
        "SV": "Event Group Name",
        "DSSVLTFU": "Event Label",
        "EXTRA": "Event Label",
    }
    assert stacked.matches == (VISIT_NAME,)


def test_a_member_without_its_matched_item_is_reported():
    data = _data()
    data["DSSVLTFU"] = data["DSSVLTFU"].rename(columns={"Event Label": "Label"})

    plan = stacking.layout(_visits(VISIT_NAME), data)

    assert dict(plan.matched[0].cells) == {"SV": "Event Group Name", "DSSVLTFU": None}
    assert plan.matched[0].missing == ("DSSVLTFU",)


def test_a_missing_member_is_left_out_of_the_layout():
    plan = stacking.layout(_visits(members=("SV", "GONE", "DSSVLTFU")), _data())

    assert plan.present == ("SV", "DSSVLTFU") and plan.missing == ("GONE",)
    assert plan.rows == 3


# --- build ----------------------------------------------------------------


def test_rows_follow_member_order_then_file_order_and_blanks_fill_the_gaps():
    stacked = _visits(VISIT_NAME, Match("Visit Status", {"SV": "Visit Status"}))

    built = stacking.build(stacked, _data())

    expected = pd.DataFrame(
        {
            "Subject": ["001", "002", "003"],
            "Visit Name": ["Screening", "Week 1", "Follow-up"],
            "Visit": [1, 2, 9],
            "Visit Status": ["Done", "Missed", NAN],
        }
    )
    pd.testing.assert_frame_equal(built, expected)


def test_member_order_decides_the_rows():
    stacked = StackedForm("VISITS", ("DSSVLTFU", "SV"))

    built = stacking.build(stacked, _data())

    assert built["Subject"].tolist() == ["003", "001", "002"]
    assert list(built.columns) == ["Subject", "Visit"]


def test_values_keep_their_types():
    data = {
        "A": pd.DataFrame(
            {"Subject": ["1"], "Date": [pd.Timestamp("2026-01-05")], "N": [1]}
        ),
        "B": pd.DataFrame({"Subject": ["2"], "Date": ["UNK-2026"], "N": [2]}),
    }

    built = stacking.build(StackedForm("S", ("A", "B")), data)

    assert built["Date"].tolist() == [pd.Timestamp("2026-01-05"), "UNK-2026"]
    assert built["N"].dtype == np.int64


# --- build_all ------------------------------------------------------------


def test_build_all_builds_from_the_members_present_and_says_what_is_missing():
    data = _data()
    data["DSSVLTFU"] = data["DSSVLTFU"].rename(columns={"Event Label": "Label"})
    stacked = StackedForm("VISITS", ("SV", "DSSVLTFU", "GONE"), (VISIT_NAME,))

    built = stacking.build_all([stacked], data)

    assert list(built.forms) == ["VISITS"]
    assert built.forms["VISITS"]["Visit Name"].tolist() == ["Screening", "Week 1", NAN]
    assert built.clashes == ()
    assert dict(built.missing_members) == {"VISITS": ("GONE",)}
    assert dict(built.missing_items) == {"VISITS": (("DSSVLTFU", "Event Label"),)}


def test_no_member_present_means_no_stacked_form():
    built = stacking.build_all([StackedForm("LABS", ("LB", "PK"))], _data())

    assert dict(built.forms) == {}
    assert dict(built.missing_members) == {"LABS": ("LB", "PK")}


def test_a_stacked_form_named_like_a_loaded_form_is_not_built():
    built = stacking.build_all([StackedForm("SV", ("SV", "DSSVLTFU"))], _data())

    assert dict(built.forms) == {} and built.clashes == ("SV",)


def test_nothing_to_build_gives_an_empty_result():
    built = stacking.build_all([], _data())

    assert (dict(built.forms), built.clashes) == ({}, ())
    assert (dict(built.missing_members), dict(built.missing_items)) == ({}, {})


def test_build_all_stops_a_match_now_named_like_an_item_every_member_has():
    data = _data()
    for member in ("SV", "DSSVLTFU"):
        data[member] = data[member].assign(**{"Visit Name": "new"})

    built = stacking.build_all([_visits(VISIT_NAME)], data)

    assert dict(built.conflicts) == {
        "VISITS": (
            "VISITS: every member now has an item called Visit Name, also the name "
            "of a match. Rename the match on Stacked forms.",
        )
    }


def test_build_all_stops_a_member_that_now_has_two_items_of_one_match():
    data = _data()
    data["SV"] = data["SV"].assign(**{"Event Label": ["x", "y"]})

    built = stacking.build_all([_visits(VISIT_NAME)], data)

    assert dict(built.conflicts) == {
        "VISITS": (
            "VISITS: SV now has both Event Group Name and Event Label, which the "
            "match Visit Name lines up. Choose “—” in SV's cell or Unmatch it on "
            "Stacked forms.",
        )
    }


def test_build_all_stops_two_matches_with_one_name():
    stacked = _visits(VISIT_NAME, Match("Visit Name", {"SV": "Visit Status"}))

    built = stacking.build_all([stacked], _data())

    assert dict(built.conflicts) == {
        "VISITS": (
            "VISITS has two matches called Visit Name. Rename one on Stacked forms.",
        )
    }


def test_build_all_stops_two_matches_holding_one_item_name():
    # Only an edited setting gets here: the page matches left-out items only.
    stacked = _visits(VISIT_NAME, Match("Visit Label", {"DSSVLTFU": "Event Label"}))

    built = stacking.build_all([stacked], _data())

    assert dict(built.conflicts) == {
        "VISITS": (
            "VISITS: the matches Visit Name and Visit Label both line up Event "
            "Label. Unmatch one of them on Stacked forms.",
        )
    }


def test_build_all_says_when_a_member_gives_another_of_the_matchs_items():
    data = _data()
    data["DSSVLTFU"] = data["DSSVLTFU"].rename(
        columns={"Event Label": "Event Group Name"}
    )

    built = stacking.build_all([_visits(VISIT_NAME)], data)

    assert built.forms["VISITS"]["Visit Name"].tolist() == [
        "Screening",
        "Week 1",
        "Follow-up",
    ]
    assert dict(built.replaced) == {
        "VISITS": (("DSSVLTFU", "Event Label", "Event Group Name"),)
    }
    assert (dict(built.missing_items), dict(built.conflicts)) == ({}, {})


# --- editing --------------------------------------------------------------


def test_add_match_lines_up_left_out_groups_named_after_the_first():
    stacked = stacking.add_match(
        _visits(), _data(), ["Event Label", "Event Group Name"]
    )

    assert stacked.matches == (
        Match(
            "Event Group Name", {"SV": "Event Group Name", "DSSVLTFU": "Event Label"}
        ),
    )


def test_add_match_refuses_two_items_of_one_member():
    with pytest.raises(ValueError) as refused:
        stacking.add_match(_visits(), _data(), ["Visit Status", "Event Group Name"])

    assert str(refused.value) == (
        "Pick at most one item from each member: SV has both Event Group Name and "
        "Visit Status."
    )


def test_add_match_refuses_an_item_that_is_not_left_out():
    with pytest.raises(ValueError) as refused:
        stacking.add_match(_visits(), _data(), ["Subject"])

    assert str(refused.value) == "Subject isn't left out, so it can't be matched."


def test_matches_can_be_renamed_and_removed():
    stacked = _visits(VISIT_NAME, Match("Visit Status", {"SV": "Visit Status"}))

    renamed = stacking.rename_match(stacked, 0, "Visit Label")
    removed = stacking.remove_matches(renamed, [1])

    assert removed.matches == (
        Match("Visit Label", {"SV": "Event Group Name", "DSSVLTFU": "Event Label"}),
    )
    assert stacking.remove_matches(stacked, [0, 1]).matches == ()


def test_dropping_a_member_drops_its_items_from_the_matches():
    stacked = _visits(VISIT_NAME, Match("Visit Status", {"SV": "Visit Status"}))

    kept = stacking.with_members(stacked, ["DSSVLTFU"])

    assert kept == StackedForm(
        "VISITS", ("DSSVLTFU",), (Match("Visit Name", {"DSSVLTFU": "Event Label"}),)
    )


def test_definitions_compare_by_value_and_are_read_only():
    first = _visits(Match("Visit Name", {"SV": "Event Group Name"}))
    second = StackedForm(
        "VISITS", ["SV", "DSSVLTFU"], [Match("Visit Name", {"SV": "Event Group Name"})]
    )

    assert first == second
    with pytest.raises(TypeError):
        first.matches[0].items["SV"] = "Visit"


# --- a matched cell's dropdown -------------------------------------------


def _cells_data():
    """A, B and C: Subject in each; B and C share Remark; slightly different dates."""
    return {
        "A": pd.DataFrame({"Subject": ["1"], "Visit Date": ["d1"], "Note": ["n"]}),
        "B": pd.DataFrame(
            {
                "Subject": ["2"],
                "Remark": ["r"],
                "Visit Dt": ["d2"],
                "Notes": ["m"],
                "VisitDate": ["d3"],
            }
        ),
        "C": pd.DataFrame({"Subject": ["3"], "Remark": ["s"], "Memo": ["o"]}),
    }


def _abc(*matches):
    return StackedForm("S", ("A", "B", "C"), matches)


def _choices(stacked, member):
    """What *member*'s cell in *stacked*'s first match offers."""
    data = _cells_data()
    return stacking.match_choices(stacking.layout(stacked, data), data, 0, member)


def test_a_cell_offers_its_left_out_items_with_similar_names_first():
    stacked = _abc(Match("Visit Date", {"A": "Visit Date"}))

    choices = _choices(stacked, "B")

    assert choices.current is None
    assert choices.similar == ("VisitDate", "Visit Dt")
    assert choices.others == ("Remark", "Notes")
    assert choices.clears == ()


def test_a_cell_never_offers_items_of_other_matches_or_of_every_member():
    stacked = _abc(
        Match("Visit Date", {"A": "Visit Date"}),
        Match("Notes", {"B": "Notes"}),
    )

    choices = _choices(stacked, "B")

    assert choices.similar + choices.others == ("VisitDate", "Visit Dt", "Remark")
    assert "Subject" not in choices.others


def test_a_cell_never_offers_an_item_that_would_give_another_member_two():
    # C already gives Memo, so B's Remark (which C has too) would give C two.
    stacked = _abc(Match("Note", {"A": "Note", "C": "Memo"}))

    choices = _choices(stacked, "B")

    assert "Remark" not in choices.similar + choices.others


def test_picking_an_item_brings_in_every_member_with_that_name():
    stacked = _abc(Match("Note", {"A": "Note"}))

    picked = stacking.set_match_item(stacked, _cells_data(), 0, "B", "Remark")

    assert picked.matches == (
        Match("Note", {"A": "Note", "B": "Remark", "C": "Remark"}),
    )


def test_clearing_an_item_takes_its_whole_same_name_group_out():
    stacked = _abc(Match("Note", {"A": "Note", "B": "Remark", "C": "Remark"}))

    assert _choices(stacked, "B").clears == ("C",)
    cleared = stacking.set_match_item(stacked, _cells_data(), 0, "B", None)

    assert cleared.matches == (Match("Note", {"A": "Note"}),)


def test_changing_an_item_swaps_whole_same_name_groups():
    stacked = _abc(Match("Note", {"A": "Note", "B": "Remark", "C": "Remark"}))

    changed = stacking.set_match_item(stacked, _cells_data(), 0, "B", "Notes")

    assert changed.matches == (Match("Note", {"A": "Note", "B": "Notes"}),)


def test_clearing_the_last_item_removes_the_match():
    stacked = _abc(Match("Note", {"A": "Note"}), Match("Memo", {"C": "Memo"}))

    cleared = stacking.set_match_item(stacked, _cells_data(), 0, "A", None)

    assert cleared.matches == (Match("Memo", {"C": "Memo"}),)


def test_picking_the_item_a_member_gives_instead_makes_it_the_saved_one():
    data = _data()
    data["DSSVLTFU"] = data["DSSVLTFU"].rename(
        columns={"Event Label": "Event Group Name"}
    )
    stacked = _visits(VISIT_NAME)
    assert stacking.layout(stacked, data).matched[0].replaced == ("DSSVLTFU",)

    fixed = stacking.set_match_item(stacked, data, 0, "DSSVLTFU", "Event Group Name")

    assert fixed.matches == (
        Match("Visit Name", {"SV": "Event Group Name", "DSSVLTFU": "Event Group Name"}),
    )
    assert stacking.layout(fixed, data).matched[0].replaced == ()


def test_picking_nothing_for_a_lost_item_forgets_it():
    data = _data()
    data["DSSVLTFU"] = data["DSSVLTFU"].drop(columns=["Event Label"])
    stacked = _visits(VISIT_NAME)
    assert stacking.layout(stacked, data).matched[0].missing == ("DSSVLTFU",)

    fixed = stacking.set_match_item(stacked, data, 0, "DSSVLTFU", None)

    assert fixed.matches == (Match("Visit Name", {"SV": "Event Group Name"}),)


def test_a_member_with_two_items_of_a_match_is_fixed_by_clearing_not_by_picking_again():
    data = _data()
    data["SV"] = data["SV"].assign(**{"Event Label": ["x", "y"]})
    stacked = _visits(VISIT_NAME)

    again = stacking.set_match_item(stacked, data, 0, "SV", "Event Group Name")
    cleared = stacking.set_match_item(stacked, data, 0, "SV", None)

    # Picking the item SV shows confirms nothing: it still has both names.
    assert again == stacked
    assert dict(stacking.build_all([again], data).conflicts) == {
        "VISITS": (
            "VISITS: SV now has both Event Group Name and Event Label, which the "
            "match Visit Name lines up. Choose “—” in SV's cell or Unmatch it on "
            "Stacked forms.",
        )
    }
    # "—" takes Event Group Name out of the match, so SV gives its Event Label.
    assert cleared.matches == (Match("Visit Name", {"DSSVLTFU": "Event Label"}),)
    assert dict(stacking.layout(cleared, data).matched[0].cells) == {
        "SV": "Event Label",
        "DSSVLTFU": "Event Label",
    }
    assert dict(stacking.build_all([cleared], data).conflicts) == {}


def test_a_pick_the_cell_does_not_offer_is_refused():
    stacked = _abc(Match("Note", {"A": "Note", "C": "Memo"}))

    with pytest.raises(ValueError) as refused:
        stacking.set_match_item(stacked, _cells_data(), 0, "B", "Remark")

    assert str(refused.value) == "B can't give Remark to Note."


# --- problems -------------------------------------------------------------


def test_names_must_be_given_unique_and_not_a_loaded_form():
    stacked_forms = [
        StackedForm("", ("SV", "DSSVLTFU")),
        StackedForm("VI.SITS", ("SV", "DSSVLTFU")),
        StackedForm("SV", ("SV", "DSSVLTFU")),
        StackedForm("VISITS", ("SV", "DSSVLTFU")),
        StackedForm(" VISITS ", ("SV", "DSSVLTFU")),
    ]

    assert stacking.problems(stacked_forms, ["SV", "DSSVLTFU"]) == [
        "New stacked form: Give it a name.",
        "VI.SITS: A form name can't contain “.”.",
        "SV: SV is already a loaded form.",
        "VISITS: Another stacked form is called VISITS.",
        "VISITS: Another stacked form is called VISITS.",
    ]


def test_members_must_be_two_or_more_loaded_forms():
    stacked_forms = [
        StackedForm("ONE", ("SV",)),
        StackedForm("ALL", ("ONE", "DSSVLTFU")),
    ]

    assert stacking.problems(stacked_forms, ["SV", "DSSVLTFU"]) == [
        "ONE: Pick at least two members.",
        "ALL: ONE is a stacked form, so it can't be a member.",
    ]


def test_matched_items_need_a_free_name():
    stacked = _visits(
        Match(" ", {"SV": "Visit Status"}),
        Match("Visit Name", {"SV": "Event Group Name"}),
        Match("Visit Name", {"DSSVLTFU": "Event Label"}),
        Match("Subject", {"DSSVLTFU": "LTFUDAT"}),
    )

    assert stacking.problems([stacked], ["SV", "DSSVLTFU"], _data()) == [
        "VISITS: Give the matched item a name.",
        "VISITS: VISITS already has an item called Visit Name.",
        "VISITS: VISITS already has an item called Visit Name.",
        "VISITS: VISITS already has an item called Subject.",
    ]


def test_a_match_with_two_items_of_one_member_is_a_problem():
    data = _data()
    data["SV"]["Event Label"] = ["Day 1", "Day 8"]

    problems = stacking.problems([_visits(VISIT_NAME)], ["SV", "DSSVLTFU"], data)

    assert problems == [
        "VISITS: Pick at most one item from each member: SV has both "
        "Event Group Name and Event Label."
    ]


def test_two_matches_holding_one_item_name_are_a_problem():
    stacked = _visits(VISIT_NAME, Match("Visit Label", {"DSSVLTFU": "Event Label"}))

    problems = stacking.problems([stacked], ["SV", "DSSVLTFU"])

    assert problems == [
        "VISITS: Keep each item in one match: Event Label is in both Visit Name "
        "and Visit Label."
    ]


def test_a_name_s_problem_reads_as_apply_says_it():
    stacked_forms = [
        StackedForm("VISITS", ("SV", "DSSVLTFU")),
        StackedForm(" VISITS ", ("SV", "DSSVLTFU")),
        StackedForm("SV", ("SV", "DSSVLTFU")),
        StackedForm("VI.SITS", ("SV", "DSSVLTFU")),
        StackedForm(" ", ("SV", "DSSVLTFU")),
        StackedForm("LABS", ("SV", "DSSVLTFU")),
    ]

    found = [
        stacking.name_problem(stacked_forms, index, ["SV", "DSSVLTFU"])
        for index in range(len(stacked_forms))
    ]

    assert found == [
        "Another stacked form is called VISITS.",
        "Another stacked form is called VISITS.",
        "SV is already a loaded form.",
        "A form name can't contain “.”.",
        "Give it a name.",
        "",
    ]


def test_a_match_name_s_problem_reads_as_apply_says_it():
    data = _data()
    stacked = _visits(
        Match("Visit Name", {"SV": "Event Group Name"}),
        Match("Visit Name", {"DSSVLTFU": "Event Label"}),
        Match("Subject", {"SV": "Visit Status"}),
        Match(" ", {"DSSVLTFU": "LTFUDAT"}),
    )
    plan = stacking.layout(stacked, data)

    found = [stacking.match_name_problem(stacked, plan, index) for index in range(4)]

    assert found == [
        "VISITS already has an item called Visit Name.",
        "VISITS already has an item called Visit Name.",
        "VISITS already has an item called Subject.",
        "Give the matched item a name.",
    ]
    fine = _visits(VISIT_NAME)
    assert stacking.match_name_problem(fine, stacking.layout(fine, data), 0) == ""


def test_well_made_stacked_forms_have_no_problems():
    assert stacking.problems([_visits(VISIT_NAME)], ["SV", "DSSVLTFU"], _data()) == []


# --- saved settings -------------------------------------------------------

SAVED = {
    "name": "VISITS",
    "members": ["SV", "DSSVLTFU"],
    "matches": [
        {
            "name": "Visit Name",
            "items": {"SV": "Event Group Name", "DSSVLTFU": "Event Label"},
        },
        {"name": "Visit Status", "items": {"SV": "Visit Status"}},
    ],
}


def test_stacked_forms_are_saved_and_read_back():
    stacked = _visits(VISIT_NAME, Match("Visit Status", {"SV": "Visit Status"}))

    settings = stacking.to_settings({"setting_name": "monthly"}, [stacked])

    assert settings == {"setting_name": "monthly", SETTINGS_KEY: [SAVED]}
    assert stacking.from_settings(settings) == [stacked]


def test_without_stacked_forms_the_key_is_not_saved():
    settings = {"setting_name": "monthly", SETTINGS_KEY: [SAVED]}

    assert stacking.to_settings(settings, []) == {"setting_name": "monthly"}
    assert stacking.from_settings({"setting_name": "monthly"}) == []
    assert stacking.from_settings(None) == []


def test_a_key_that_is_not_a_list_is_ignored(caplog):
    with caplog.at_level(logging.WARNING):
        assert stacking.from_settings({SETTINGS_KEY: {"name": "VISITS"}}) == []

    assert "not a list" in caplog.text


def test_damaged_entries_are_skipped_and_the_rest_kept(caplog):
    junk = [
        "VISITS",
        {"name": "", "members": ["SV", "DSSVLTFU"]},
        {"name": "LABS", "members": "LB"},
        {"name": "LABS", "members": ["LB", "PK"], "matches": "none"},
        {"name": "VISITS", "members": ["SV", "DSSVLTFU"]},  # Repeats a name.
    ]
    tolerated = {
        "name": " VISITS ",
        "members": [" SV", 3, "DSSVLTFU", "SV"],
        "matches": [
            {
                "name": " Visit Name ",
                "items": {"SV": "Event Group Name", "DSSVLTFU": 5},
            },
            {"name": "Lost", "items": {"GONE": "Item"}},
            "junk",
        ],
    }

    with caplog.at_level(logging.WARNING):
        stacked_forms = stacking.from_settings({SETTINGS_KEY: [tolerated, *junk]})

    assert stacked_forms == [
        StackedForm(
            "VISITS",
            ("SV", "DSSVLTFU"),
            (Match("Visit Name", {"SV": "Event Group Name"}),),
        )
    ]
    assert caplog.text.count("Skipping saved stacked_forms entry") == len(junk)
    assert caplog.text.count("Skipping saved match") == 2
