"""The base report's workbook is the desktop export, byte for byte (DEMO01).

Only ``docProps/core.xml`` differs: it holds the time the workbook was made.
"""

import io
import zipfile

from clinical_reporting import build_base_report_from_forms
from clinical_reporting.report import CLReport
from clinical_reporting.sample_data import configure_sample_report, sample_forms
from clinical_reporting.session import export_report, new_report

CREATED_AT = "docProps/core.xml"


def _parts(data: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return {
            name: archive.read(name)
            for name in archive.namelist()
            if name != CREATED_AT
        }


def _sample_setting() -> dict:
    report = CLReport()
    report.set_study_name("DEMO01")
    report.set_data(sample_forms())
    configure_sample_report(report)
    report.update_selected_items_order_list()
    return report.settings_to_dict("golden")


def test_the_workbook_is_the_desktop_export(tmp_path):
    settings = _sample_setting()
    # The desktop's sequence for a picked setting, then its export.
    report = new_report("DEMO01", sample_forms())
    report.load_setting_from_dict(settings)
    report.reconcile_with_current_data()
    report.sync_with_selection()
    report.update_selected_items_order_list()
    desktop = export_report(report, str(tmp_path / "desktop.xlsx"))
    assert desktop is not None  # DEMO01 has rows to save.

    workbook = build_base_report_from_forms(
        sample_forms(), settings, study_name="DEMO01"
    ).to_workbook(file_name="golden")

    with open(desktop, "rb") as handle:
        expected = _parts(handle.read())
    actual = _parts(workbook.data)
    assert sorted(actual) == sorted(expected)
    for name in expected:
        assert actual[name] == expected[name], name
