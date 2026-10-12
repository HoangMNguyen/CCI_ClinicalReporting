"""A base report: a saved setting run on a study's forms, without the desktop."""

import io

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


# ---------------------------------------------------------------------------
# Additional inputs
# ---------------------------------------------------------------------------


def _lab_settings(form_name="LAB"):
    """Adults with AEs plus LAB's ALT, from lab_results.csv by its saved names."""
    settings = _settings()
    settings["additional_input_names"] = [
        {
            "file_name": "lab_results.csv",
            "columns": ["Subject", "Site", "ALT (U/L)", "Visit Dt"],
            "form_name": form_name,
            "column_names": {"ALT (U/L)": "ALT", "Visit Dt": "Visit Date"},
        }
    ]
    settings["selected_forms"]["LAB"] = {
        "selected_form_items": ["ALT"],
        "join_items": ["Subject", "Site"],
        "join_order": 3,
        "join_how": "Left join",
    }
    return settings


def _lab_file(folder, name="lab_results.csv"):
    path = folder / name
    path.write_text("Subject,Site,ALT (U/L)\n01-1,A,40\n01-3,B,55\n", encoding="utf-8")
    return path


LAB_TABLE = pd.DataFrame(
    {
        "Subject": ["01-1", "01-3"],
        "Site": ["A", "B"],
        "DM.Age": [30, 45],
        "AE.Term": ["Headache", "Nausea"],
        "LAB.ALT": [40, 55],
    }
)
NO_VISIT_DT = (
    "A saved column name can't be used: lab_results.csv has no Visit Dt. It's "
    "ignored; the form still applies without it."
)


def test_an_additional_input_joins_the_report_by_its_saved_names(tmp_path):
    base = build_base_report_from_forms(
        _forms(), _lab_settings(), additional_inputs=[_lab_file(tmp_path)]
    )

    assert_frame_equal(base.table, LAB_TABLE)
    assert base.warnings == (NO_VISIT_DT,)
    assert base.warnings[0].kind == "warning"
    assert base.warnings[0].details == "lab_results.csv: Visit Dt → Visit Date"


def test_an_additional_input_can_be_an_open_file(tmp_path):
    with open(_lab_file(tmp_path), "rb") as lab:
        base = build_base_report_from_forms(
            _forms(), _lab_settings(), additional_inputs=[lab]
        )

    assert_frame_equal(base.table, LAB_TABLE)


def test_the_ignored_saved_names_are_the_last_warning(tmp_path):
    settings = _lab_settings()
    settings["selected_forms"]["PK"] = {
        "selected_form_items": ["Dose"],
        "join_items": ["Subject"],
        "join_order": 4,
        "join_how": "Left join",
    }

    base = build_base_report_from_forms(
        _forms(), settings, additional_inputs=[_lab_file(tmp_path)], missing_ok=True
    )

    assert base.warnings == ("Missing forms: PK", NO_VISIT_DT)


def test_an_additional_input_without_saved_names_is_refused_for_its_dot(tmp_path):
    # Named after its file, as on the desktop, it can't be a form: it holds a ".".
    with pytest.raises(WorkflowInputError) as refused:
        build_base_report_from_forms(
            _forms(), _settings(), additional_inputs=[_lab_file(tmp_path, "notes.csv")]
        )

    assert str(refused.value) == (
        "Cannot add forms because some form names are invalid or conflict with "
        "existing data.\n"
        "Form names cannot include '.':\n"
        "  - notes.csv"
    )


def test_an_additional_input_named_like_a_form_is_refused(tmp_path):
    with pytest.raises(WorkflowInputError) as refused:
        build_base_report_from_forms(
            _forms(), _lab_settings("DM"), additional_inputs=[_lab_file(tmp_path)]
        )

    assert str(refused.value) == (
        "Cannot add forms because some form names are invalid or conflict with "
        "existing data.\n"
        "Conflicts with existing report forms:\n"
        "  - DM: lab_results.csv"
    )


def test_an_additional_input_needs_a_file_name():
    with pytest.raises(WorkflowInputError) as refused:
        build_base_report_from_forms(
            _forms(), _settings(), additional_inputs=[io.BytesIO(b"Subject\n")]
        )

    assert str(refused.value) == (
        "An additional input has no file name. Give it one (a file object's name "
        "attribute) so its saved names can be found."
    )


def test_an_additional_input_given_twice_is_refused(tmp_path):
    lab = _lab_file(tmp_path)

    with pytest.raises(WorkflowInputError) as refused:
        build_base_report_from_forms(
            _forms(), _lab_settings(), additional_inputs=[lab, lab]
        )

    assert str(refused.value) == (
        "lab_results.csv is given twice as an additional input."
    )
