"""Output file names (clinical_reporting.filenames)."""

from datetime import datetime

from clinical_reporting.filenames import output_file_name


def test_output_file_name_stamps_and_adds_extension():
    now = datetime(2026, 9, 30, 10, 15, 0)

    assert output_file_name("DEMO01_DSMB", now=now) == "DEMO01_DSMB 260930_101500.xlsx"
    assert output_file_name("report.xlsx", now=now) == "report 260930_101500.xlsx"
    assert output_file_name("  ", now=now) == "260930_101500.xlsx"


def test_output_file_name_cannot_leave_the_output_folder():
    name = output_file_name(
        "..\\..\\secret/report:v2", now=datetime(2026, 1, 2, 3, 4, 5)
    )

    assert "/" not in name and "\\" not in name and ":" not in name
    assert name == ".._.._secret_report_v2 260102_030405.xlsx"
