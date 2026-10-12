"""The desktop export and the base report give the same workbook.

A saved setting with an additional input, a stacked form and a hand-edited
join, run once through the window's handlers and once through
:func:`clinical_reporting.build_base_report_from_forms`. Only
``docProps/core.xml`` differs: it holds the time the workbook was made.
"""

import io
import zipfile

import pandas as pd
from PySide6.QtWidgets import QApplication

from clinical_reporting import build_base_report_from_forms, session
from clinical_reporting.additional_names import add_to_settings
from clinical_reporting.models import JoinHow
from clinical_reporting.report import CLReport
from clinical_reporting.sample_data import STUDY, configure_sample_report, sample_forms
from clinical_reporting.settings_store import write_settings_json
from clinical_reporting.stacking import Match, StackedForm
from clinical_reporting.ui.pages import additional_input

CREATED_AT = "docProps/core.xml"
DISP = StackedForm(
    "DISP",
    ("EOT", "DS"),
    (Match("Disposition", {"EOT": "Reason", "DS": "Status"}),),
)


def _parts(data: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return {
            name: archive.read(name)
            for name in archive.namelist()
            if name != CREATED_AT
        }


def _lab_results(folder):
    """lab_results.csv: an ALT result for some of DEMO01's subjects."""
    dm = sample_forms()["DM"].head(6)
    lab = pd.DataFrame(
        {
            "Subject": dm["Subject"],
            "Site": dm["Site"],
            "ALT (U/L)": range(20, 20 + len(dm)),
        }
    )
    path = folder / "lab_results.csv"
    lab.to_csv(path, index=False)
    return path, lab


def _parity_setting(folder, lab_path, lab):
    """The sample report, plus DISP, LAB and a hand-edited VS join; its file."""
    report = CLReport()
    report.set_study_name(STUDY)
    report.set_data({**sample_forms(), "LAB": lab.rename(columns={"ALT (U/L)": "ALT"})})
    session.apply_stacked_forms(report, [DISP])
    configure_sample_report(report)
    report.add_selected_form("DISP")
    report.selected_forms["DISP"].set_form_item_state("Disposition", selected=True)
    report.update_join_items("DISP", ["Subject", "Site"], 4, JoinHow.LEFT)
    report.add_selected_form("LAB")
    report.selected_forms["LAB"].set_form_item_state("ALT", selected=True)
    report.update_join_items("LAB", ["Subject", "Site"], 5, JoinHow.LEFT)
    report.update_join_items("VS", ["Visit", "Subject"], 3, JoinHow.LEFT)
    report.update_selected_items_order_list()
    settings = add_to_settings(
        report.settings_to_dict("Parity"),
        {str(lab_path): lab},
        {str(lab_path): "LAB"},
        {(str(lab_path), "ALT (U/L)"): "ALT"},
    )
    # The join as the user left it: applying the setting tidies it.
    assert settings["selected_forms"]["VS"]["join_items"] == ["Visit", "Subject"]
    path = folder / "parity.json"
    write_settings_json(path, settings)
    return path


def test_the_window_exports_what_the_base_report_gives(
    sample_window, settle, tmp_path, monkeypatch
):
    window = sample_window
    lab_path, lab = _lab_results(tmp_path)
    setting_path = _parity_setting(tmp_path, lab_path, lab)
    out = tmp_path / "out"
    out.mkdir()

    window.open_input_data(f"Core_Listings_{STUDY}_sample.zip", None, sample_forms())
    window.settings_directory = str(tmp_path)
    window.ui.checkBox_saved_setting.setChecked(True)
    combo = window.ui.comboBox_saved_setting
    combo.setCurrentIndex(combo.findText("Parity"))
    QApplication.processEvents()
    missing = window.ui.label_setting.text()
    monkeypatch.setattr(
        additional_input.QFileDialog,
        "getOpenFileNames",
        lambda *_args: ([str(lab_path)], ""),
    )
    window.click_add_additional_files()
    settle(window.task_runner)
    picked = dict(window.additional_form_names)
    window.click_apply_additional_forms()
    window.output_folder_name = str(out)
    window.ui.lineEdit_file_name.setText("")
    window.click_run()
    settle(window.task_runner)

    # The setting waited for LAB, whose saved names were picked; applying the
    # file applied the setting again, its VS join tidied.
    assert missing.startswith("Missing forms: LAB")
    assert picked == {str(lab_path.resolve()): "LAB"}
    assert window.ui.label_setting.text() == ""
    assert window.report.get_join_list_dict()["VS"] == {
        "items": ["Subject"],
        "order": 3,
        "how": "Left join",
    }
    assert window.ui.label_run_confirmation.kind() == "success"
    (exported,) = out.glob("*.xlsx")
    base = build_base_report_from_forms(
        sample_forms(),
        setting_path,
        study_name=STUDY,
        additional_inputs=[lab_path],
    )
    assert base.warnings == ()
    expected = _parts(exported.read_bytes())
    actual = _parts(base.to_workbook().data)
    assert sorted(actual) == sorted(expected)
    for name in expected:
        assert actual[name] == expected[name], name
