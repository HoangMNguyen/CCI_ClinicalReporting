"""The sidebar's step badges, worked out without Qt (clinical_reporting.steps)."""

import ast
from datetime import datetime
from pathlib import Path

import pandas as pd

from clinical_reporting import steps, validation
from clinical_reporting.additional_names import (
    BY_FILE_NAME,
    IgnoredName,
    SavedFileNames,
)
from clinical_reporting.models import JoinHow
from clinical_reporting.report import CLReport
from clinical_reporting.stacking import Match, StackedForm, layout
from clinical_reporting.steps import StepStatus
from clinical_reporting.validation import ReportValidationIssue


def _report():
    """DM and AE joined on Subject, DM.Age selected."""
    report = CLReport()
    report.set_data(
        {
            "DM": pd.DataFrame({"Subject": ["001"], "Age": [41]}),
            "AE": pd.DataFrame({"Subject": ["001"], "Term": ["Nausea"]}),
        }
    )
    report.set_common_item_state("Subject", selected=True)
    report.add_selected_form("DM")
    report.selected_forms["DM"].set_form_item_state("Age", selected=True)
    report.update_join_items("DM", [], 1, JoinHow.LEFT)
    report.add_selected_form("AE")
    report.update_join_items("AE", ["Subject"], 2, JoinHow.LEFT)
    return report


def _issue_codes_in_validation():
    """Every code ``validate_report`` can report (the ``_add_issue`` calls)."""
    tree = ast.parse(Path(validation.__file__).read_text(encoding="utf-8"))
    return {
        node.args[1].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", None) == "_add_issue"
        and isinstance(node.args[1], ast.Constant)
    }


def test_every_issue_code_has_a_step_or_deliberately_none():
    codes = _issue_codes_in_validation()
    placed = (
        set(steps.ISSUE_STEPS)
        | steps.FILTER_ITEM_ISSUE_CODES
        | steps.UNPLACED_ISSUE_CODES
    )

    assert len(codes) > 20, "the scan found too few codes"
    assert codes - placed == set()
    assert set(steps.ISSUE_STEPS.values()) <= set(steps.STEP_KEYS)


def test_nothing_loaded_shows_only_the_optional_step():
    statuses = steps.step_statuses(CLReport())

    assert statuses[steps.ADDITIONAL] == StepStatus(steps.OPTIONAL)
    others = {key: s for key, s in statuses.items() if key != steps.ADDITIONAL}
    assert set(others.values()) == {StepStatus()}
    assert list(statuses) == list(steps.STEP_KEYS)


def test_a_ready_report_shows_counts_and_done_steps():
    report = _report()
    report.add_static_filter_item("DM.Age", ">=", "18")
    report.set_rename_item("DM.Age", "Age (years)")
    report.set_rename_item("Subject", "Subject")  # Same name: not a rename.

    statuses = steps.step_statuses(
        report, source="Core_Listings_DEMO01.zip", additional_forms=1
    )

    assert statuses[steps.SOURCE] == StepStatus(
        steps.DONE, tip="Loaded Core_Listings_DEMO01.zip"
    )
    assert statuses[steps.ADDITIONAL] == StepStatus(steps.DONE, tip="1 form added")
    assert statuses[steps.FORMS] == StepStatus(count=2, tip="2 selected")
    assert statuses[steps.COMMON].count == 1
    assert statuses[steps.FORM_ITEMS].count == 1
    assert statuses[steps.FILTERS] == StepStatus(count=1, tip="1 filter")
    assert statuses[steps.COMPARISONS] == StepStatus()
    assert statuses[steps.JOINS] == StepStatus(steps.DONE, tip="Ready")
    assert statuses[steps.ORDER] == StepStatus(count=1, tip="1 renamed")
    assert statuses[steps.PREVIEW] == StepStatus()


def test_one_form_needs_no_join_and_an_export_finishes_the_last_step():
    report = _report()
    report.add_available_form("AE")  # As "remove" on the Forms page does.

    statuses = steps.step_statuses(report, exported_to="DEMO01 260930.xlsx")

    assert statuses[steps.JOINS] == StepStatus(tip="Not needed for one form")
    assert statuses[steps.PREVIEW] == StepStatus(
        steps.DONE, tip="Last exported DEMO01 260930.xlsx"
    )


def test_problems_mark_the_step_that_fixes_them():
    report = _report()
    report.update_join_items("AE", [], 1, JoinHow.LEFT)  # Shares order 1 with DM.

    joins = steps.step_statuses(report)[steps.JOINS]

    assert joins.state == steps.ERROR and joins.count is None
    assert joins.tip == "Join order 1 is assigned to multiple forms: AE, DM."

    report.update_join_items("AE", [], 2, JoinHow.LEFT)
    report.add_dynamic_filter_item("DM.Age", "<", "AE.Term")  # AE.Term isn't selected.

    statuses = steps.step_statuses(report)
    assert statuses[steps.JOINS].state == steps.ERROR  # AE now lacks a join item.
    assert statuses[steps.COMPARISONS].state == steps.ERROR
    assert statuses[steps.FILTERS] == StepStatus()


def test_several_problems_are_counted_in_the_tip():
    report = _report()
    report.update_join_items("AE", ["Term", "Term"], 2, JoinHow.LEFT)

    joins = steps.step_statuses(report)[steps.JOINS]

    assert joins.state == steps.ERROR and joins.tip.endswith(" problems")


def test_filter_item_problems_go_by_their_field():
    def issue(field):
        return ReportValidationIssue("missing_filter_item", "gone", field)

    assert steps.issue_step(issue("static_filter_items.0")) == steps.FILTERS
    assert steps.issue_step(issue("dynamic_filter_items.2")) == steps.COMPARISONS
    assert steps.issue_step(issue(None)) is None


def test_the_summary_counts_what_the_report_holds():
    report = _report()
    report.add_static_filter_item("DM.Age", ">=", "18")

    assert steps.report_summary(report, "DEMO01") == (
        "DEMO01 · 2 forms · 2 items · 1 filter · 0 comparisons"
    )
    assert steps.report_summary(CLReport(), "DEMO01").startswith("No data loaded")


def test_every_step_has_a_title_and_the_data_steps_are_the_later_ones():
    assert list(steps.TITLES) == list(steps.STEP_KEYS)
    assert steps.NEEDS_DATA == set(steps.STEP_KEYS) - {steps.SOURCE, steps.ADDITIONAL}
    assert steps.TITLES[steps.SOURCE] in steps.NO_DATA_HINT
    # Stacked forms are made from the loaded forms, before anything is selected.
    assert steps.STEP_KEYS[:4] == (
        steps.SOURCE,
        steps.ADDITIONAL,
        steps.STACKED,
        steps.FORMS,
    )


def test_the_source_summary_counts_forms_and_rows_and_says_when():
    data = {"DM": range(2_000), "AE": range(431), "VS": []}
    read_at = datetime(2026, 9, 30, 10, 12)

    assert steps.source_summary(data, read_at) == (
        "3 forms · 2,431 rows · read at 10:12 on 30 Sep"
    )
    assert steps.source_summary({"DM": [1]}, read_at).startswith("1 form · 1 row ·")


def test_the_additional_input_step_says_what_applying_did():
    added = steps.additional_applied_message({"LB", "PK"})
    one = steps.additional_applied_message({"LB"})
    removed = steps.additional_applied_message(set())

    assert added == "2 files applied. New forms: LB, PK." and added.kind == "success"
    assert one.startswith("1 file applied.")
    assert removed.kind == "success" and "removed" in removed
    assert steps.ADD_FILES_FIRST.kind == "warning"
    assert steps.APPLY_ADDITIONAL_AGAIN.kind == "info"


def test_the_stacked_forms_badge_says_how_they_stand():
    report = _report()
    assert steps.step_statuses(report)[steps.STACKED] == StepStatus(steps.OPTIONAL)

    report.set_stacked_forms([StackedForm("BOTH", ("DM", "AE"))])
    assert steps.step_statuses(report)[steps.STACKED] == StepStatus(
        steps.DONE, tip="1 stacked form"
    )

    report.set_stacked_forms(
        [StackedForm("BOTH", ("DM", "AE")), StackedForm("ALL", ("DM", "AE", "LB"))]
    )
    assert steps.step_statuses(report)[steps.STACKED] == StepStatus(
        steps.WARNING, tip="ALL is built without LB, which isn't loaded."
    )

    report.set_stacked_forms([StackedForm("DM", ("DM", "AE"))])
    assert steps.step_statuses(report)[steps.STACKED] == StepStatus(
        steps.ERROR,
        tip="DM is both a stacked form and a loaded form. Rename the stacked form "
        "on Stacked forms.",
    )

    report.set_stacked_forms([])
    assert steps.step_statuses(report)[steps.STACKED] == StepStatus(steps.OPTIONAL)


def test_the_stacked_forms_step_says_what_applying_did():
    report = _report()
    report.set_stacked_forms(
        [StackedForm("BOTH", ("DM", "AE")), StackedForm("LABS", ("LB", "PK"))]
    )
    applied = steps.stacked_applied_message(report)
    report.set_stacked_forms([])
    removed = steps.stacked_applied_message(report)

    assert applied == (
        "Applied. Stacked forms: BOTH (2 rows from DM, AE); LABS (not built)."
    )
    assert applied.kind == "success"
    assert removed == "The stacked forms were removed from the report."
    assert removed.kind == "success"
    assert steps.stacked_missing_message(report) == ""
    assert steps.STACKED_NOT_APPLIED.kind == "info"
    assert steps.APPLY_STACKED_AGAIN.kind == "info"


def test_the_stacked_forms_step_words_problems_and_members():
    one = steps.stacked_problems_message(["VISITS: Pick at least two members."])
    two = steps.stacked_problems_message(["A: Give it a name.", "B: Give it a name."])

    assert one == "Not applied. Fix this problem first, then apply again."
    assert (one.kind, one.details) == ("error", "VISITS: Pick at least two members.")
    assert two == "Not applied. Fix these 2 problems first, then apply again."
    assert two.details == "A: Give it a name.\nB: Give it a name."
    assert (
        steps.stacked_form_tooltip(StackedForm("VISITS", ("SV", "DSSVLTFU")))
        == "Stacked from SV, DSSVLTFU"
    )


def test_a_matched_cell_says_why_it_warns():
    data = {
        "SV": pd.DataFrame(
            {"Subject": ["1"], "Event Group Name": ["a"], "Event Label": ["b"]}
        ),
        "DS": pd.DataFrame({"Subject": ["2"], "Event Group Name": ["c"]}),
        "LB": pd.DataFrame({"Subject": ["3"]}),
    }
    match = Match(
        "Visit", {"SV": "Event Group Name", "DS": "Event Label", "LB": "Event Label"}
    )
    stacked = StackedForm("VISITS", ("SV", "DS", "LB"), (match,))
    item = layout(stacked, data).matched[0]

    assert [steps.stacked_cell_warning(item, match, m) for m in stacked.members] == [
        "SV now has Event Group Name and Event Label: which one is unclear. "
        "Choose “—” or Unmatch to fix it.",
        "DS has no Event Label; its Event Group Name is taken instead",
        "LB has no Event Label",
    ]


def test_saved_names_entries_read_as_their_form_names():
    lab = SavedFileNames("lab_results.csv", (), "LAB", {})
    old_lab = SavedFileNames("lab_old.csv", (), "LAB", {})
    columns_only = SavedFileNames("extra.csv", (), "", {"A": "B"})
    twin = SavedFileNames("extra.csv", (), "", {"C": "D"})

    assert steps.saved_names_label(lab) == "LAB"
    assert steps.saved_names_label(columns_only) == "extra.csv"
    assert steps.saved_names_labels([lab, columns_only]) == ["LAB", "extra.csv"]
    assert steps.saved_names_labels([lab, old_lab, columns_only, twin]) == [
        "LAB (lab_results.csv)",
        "LAB (lab_old.csv)",
        "extra.csv",
        "extra.csv",
    ]
    # A form name that is another entry's file name: only the form name gets
    # the file name added.
    named_like_a_file = SavedFileNames("x.csv", (), "extra.csv", {})
    assert steps.saved_names_labels([named_like_a_file, columns_only]) == [
        "extra.csv (x.csv)",
        "extra.csv",
    ]
    assert steps.saved_names_entry_tip(lab) == "Saved for lab_results.csv"


def test_saved_names_a_file_cant_use_are_said_by_file():
    ignored = [
        IgnoredName("lab.csv", "Visit Dt", "Visit Date"),
        IgnoredName("lab.csv", "ALT (U/L)", "ALT"),
        IgnoredName("pk.csv", "Conc", "CONC"),
    ]
    lab_entry = SavedFileNames("lab_results.csv", (), "LAB", {})

    applied = steps.additional_applied_message({"LAB", "PK"}, ignored)
    standing = steps.saved_names_ignored_message(ignored[:1])
    filled = steps.saved_names_filled_message(
        "Monthly", [("lab.csv", BY_FILE_NAME)], ignored[:2]
    )
    picked = steps.saved_names_picked_message(lab_entry, "lab.csv", ignored[:2])
    columns = [IgnoredName("lab.csv", f"C{i}", f"N{i}") for i in range(7)]
    files = [IgnoredName(f"f{i}.csv", "C", "N") for i in range(5)]

    assert applied.kind == "warning"
    assert applied == (
        "2 files applied. New forms: LAB, PK. Saved column names ignored: "
        "lab.csv has no Visit Dt or ALT (U/L); pk.csv has no Conc."
    )
    assert applied.details == (
        "lab.csv: Visit Dt → Visit Date\nlab.csv: ALT (U/L) → ALT\npk.csv: Conc → CONC"
    )
    assert standing.kind == "warning"
    assert standing == (
        "A saved column name can't be used: lab.csv has no Visit Dt. It's "
        "ignored; the form still applies without it."
    )
    assert steps.saved_names_ignored_message(ignored).endswith(
        "They're ignored; the forms still apply without them."
    )
    assert filled.kind == "warning"
    assert filled == (
        "Saved names from “Monthly” picked for 1 file: lab.csv by its file name. "
        "Some saved column names can't be used and will be ignored: lab.csv has "
        "no Visit Dt or ALT (U/L). Check them, then Apply to report."
    )
    assert picked == (
        "Names from LAB filled in for lab.csv. 2 saved column names can't be used "
        "and will be ignored: lab.csv has no Visit Dt or ALT (U/L). Check them, "
        "then Apply to report."
    )
    many_columns = steps.saved_names_ignored_message(columns)
    assert "lab.csv has no C0, C1, C2, C3, C4 or 2 more." in many_columns
    assert len(many_columns.details.splitlines()) == 7
    assert "f2.csv has no C; and 2 more files." in steps.saved_names_ignored_message(
        files
    )
    assert "f2.csv has no C; and 1 more file." in steps.saved_names_ignored_message(
        files[:4]
    )
    # Two listed files with the same name, both lacking the column.
    twice = steps.saved_names_ignored_message([ignored[0], ignored[0]])
    assert twice.startswith("A saved column name can't be used: lab.csv has no")
    assert "lab.csv has no Visit Dt. It's ignored" in twice
    assert twice.details == "lab.csv: Visit Dt → Visit Date"
    assert steps.additional_applied_message({"LB"}, ()).kind == "success"


def test_the_preview_caption_says_its_size():
    assert steps.preview_caption(1284, 42) == "1,284 rows · 42 columns"
    assert steps.preview_caption(1, 1) == "1 row · 1 column"


def test_the_joins_message_explains_what_stops_the_joins():
    report = _report()
    fine = steps.joins_message(report)
    report.update_join_items("AE", [], 1, JoinHow.LEFT)  # Shares order 1 with DM.
    shared = steps.joins_message(report)
    report.add_available_form("AE")
    one_form = steps.joins_message(report)

    assert fine is None
    assert shared.kind == "error"
    assert shared == (
        "Join order 1 is assigned to multiple forms: AE, DM. "
        "The report can't be exported until this is fixed."
    )
    assert one_form.kind == "info" and "two or more forms" in one_form
