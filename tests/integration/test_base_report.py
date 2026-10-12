"""A base report: a saved setting run on a study's forms, without the desktop."""

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from clinical_reporting import BaseReport, build_base_report_from_forms, session
from clinical_reporting.report import CLReport
from clinical_reporting.settings_store import write_settings_json
from clinical_reporting.stacking import Match, StackedForm
from clinical_reporting.workflow import WorkflowInputError


def _forms():
    return {
        "DM": pd.DataFrame(
            {
                "Subject": ["01-1", "01-2", "01-3"],
                "Site": ["A", "A", "B"],
                "Age": [30, 17, 45],
            }
        ),
        "AE": pd.DataFrame(
            {
                "Subject": ["01-1", "01-3"],
                "Site": ["A", "B"],
                "Term": ["Headache", "Nausea"],
            }
        ),
    }


def _settings(min_age="18", ae_join=("Subject", "Site")):
    """Adults with AEs: DM's Age and AE's Term, for subjects at least *min_age*."""
    report = CLReport()
    report.set_data(_forms())
    report.add_selected_form("DM")
    report.add_selected_form("AE")
    report.set_common_item_state("Subject", selected=True)
    report.set_common_item_state("Site", selected=True)
    report.selected_forms["DM"].set_form_item_state("Age", selected=True)
    report.selected_forms["AE"].set_form_item_state("Term", selected=True)
    report.update_join_items("DM", [], 1, "Left join")
    report.update_join_items("AE", list(ae_join), 2, "Left join")
    report.add_static_filter_item("DM.Age", ">=", min_age)
    return report.settings_to_dict("Adults with AEs")


def _with_lab_and_height(settings):
    settings["selected_forms"]["LAB"] = {
        "selected_form_items": ["Result"],
        "join_items": ["Subject", "Site"],
        "join_order": 3,
        "join_how": "Left join",
    }
    settings["selected_forms"]["DM"]["selected_form_items"].append("Height")
    return settings


ADULTS_WITH_AES = pd.DataFrame(
    {
        "Subject": ["01-1", "01-3"],
        "Site": ["A", "B"],
        "DM.Age": [30, 45],
        "AE.Term": ["Headache", "Nausea"],
    }
)


def test_a_saved_setting_runs_on_the_forms():
    base = build_base_report_from_forms(_forms(), _settings())

    assert isinstance(base, BaseReport)
    assert_frame_equal(base.table, ADULTS_WITH_AES)
    assert base.warnings == ()
    assert base.setting_name == "Adults with AEs"


def test_a_setting_the_forms_lack_parts_of_is_refused():
    with pytest.raises(WorkflowInputError) as refused:
        build_base_report_from_forms(_forms(), _with_lab_and_height(_settings()))

    assert str(refused.value) == (
        "The saved setting “Adults with AEs” doesn't fit this export.\n"
        "Missing forms: LAB\n"
        "Missing items in DM: Height"
    )


def test_a_setting_without_a_name_is_refused_without_one():
    settings = _with_lab_and_height(_settings())
    settings["setting_name"] = None

    with pytest.raises(WorkflowInputError) as refused:
        build_base_report_from_forms(_forms(), settings)

    assert str(refused.value) == (
        "The saved setting doesn't fit this export.\n"
        "Missing forms: LAB\n"
        "Missing items in DM: Height"
    )


def test_missing_ok_runs_without_what_is_missing_and_says_so():
    base = build_base_report_from_forms(
        _forms(), _with_lab_and_height(_settings()), missing_ok=True
    )

    assert_frame_equal(base.table, ADULTS_WITH_AES)
    assert base.warnings == ("Missing forms: LAB", "Missing items in DM: Height")
    assert [warning.kind for warning in base.warnings] == ["warning", "warning"]


def test_a_saved_setting_file_without_a_name_is_named_after_the_file(tmp_path):
    settings = _settings()
    settings.pop("setting_name")
    write_settings_json(tmp_path / "adults.json", settings)

    base = build_base_report_from_forms(_forms(), tmp_path / "adults.json")

    assert_frame_equal(base.table, ADULTS_WITH_AES)
    assert base.setting_name == "adults"


@pytest.mark.parametrize(
    ("name", "text", "message"),
    [
        (
            "list.json",
            "[]",
            "Couldn't read list.json. The file may be damaged, or it isn't a "
            "saved setting.",
        ),
        (
            "bad.json",
            "{",
            "Couldn't read bad.json. The file may be damaged, or it isn't a "
            "saved setting.",
        ),
        (
            "nope.json",
            None,
            "Couldn't find nope.json. It may have been moved or deleted; choose it "
            "again.",
        ),
    ],
)
def test_a_saved_setting_file_that_cant_be_read_is_refused(
    tmp_path, name, text, message
):
    if text is not None:
        (tmp_path / name).write_text(text, encoding="utf-8")

    with pytest.raises(WorkflowInputError) as refused:
        build_base_report_from_forms(_forms(), tmp_path / name)

    assert str(refused.value) == message


def test_a_stacked_form_missing_a_member_is_built_without_it_and_said():
    forms = {
        "EOT": pd.DataFrame({"Subject": ["01-1"], "Site": ["A"], "Reason": ["Done"]}),
        "DS": pd.DataFrame({"Subject": ["01-2"], "Site": ["A"], "Status": ["Lost"]}),
    }
    source = session.new_report(None, forms)
    disposition = Match("Disposition", {"EOT": "Reason", "DS": "Status"})
    session.apply_stacked_forms(
        source, [StackedForm("DISP", ("EOT", "DS"), (disposition,))]
    )
    source.add_selected_form("DISP")
    source.set_common_item_state("Site", selected=True)
    source.selected_forms["DISP"].set_form_item_state("Disposition", selected=True)
    settings = source.settings_to_dict("Disposition")

    base = build_base_report_from_forms(
        {"EOT": forms["EOT"]}, settings, missing_ok=True
    )

    assert base.warnings == (
        "Missing forms: DS",
        "DISP is built without DS, which isn't loaded.",
    )
    assert [warning.kind for warning in base.warnings] == ["warning", "warning"]


def test_a_setting_that_matches_no_rows_gives_its_columns_and_no_rows():
    base = build_base_report_from_forms(_forms(), _settings(min_age="99"))

    assert list(base.table.columns) == ["Subject", "Site", "DM.Age", "AE.Term"]
    assert len(base.table) == 0


def test_a_report_that_cant_run_is_refused_as_the_desktop_says():
    with pytest.raises(WorkflowInputError) as refused:
        build_base_report_from_forms(_forms(), _settings(ae_join=()))

    assert str(refused.value).startswith("Cannot run:")
    assert "Form 'AE' needs at least one join item because it is not first." in str(
        refused.value
    )
