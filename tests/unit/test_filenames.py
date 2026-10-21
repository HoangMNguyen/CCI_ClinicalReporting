"""Output file names (clinical_reporting.filenames)."""

from datetime import datetime

from clinical_reporting.filenames import output_base_name, output_file_name


def test_output_file_name_stamps_and_adds_extension():
    now = datetime(2026, 9, 30, 10, 15, 0)

    assert output_file_name("DEMO01_DSMB", now=now) == "DEMO01_DSMB 260930_101500.xlsx"
    assert output_file_name("report.xlsx", now=now) == "report 260930_101500.xlsx"
    assert output_file_name("  ", now=now) == "260930_101500.xlsx"


def test_output_file_name_can_leave_out_the_date_and_time():
    assert output_file_name("DEMO01 DSMB", add_date_time=False) == "DEMO01 DSMB.xlsx"
    assert output_file_name("report.XLSX", add_date_time=False) == "report.xlsx"
    assert output_file_name("a/b:c", add_date_time=False) == "a_b_c.xlsx"


def test_a_windows_device_name_never_names_the_file():
    now = datetime(2026, 9, 30, 10, 15, 0)

    assert output_file_name("CON", add_date_time=False) == "CON_.xlsx"
    assert output_file_name("nul.xlsx", add_date_time=False) == "nul_.xlsx"
    assert output_file_name("com1.backup", add_date_time=False) == "com1_.backup.xlsx"
    # With the date and time after it, "CON" alone isn't one.
    assert output_file_name("CON", now=now) == "CON 260930_101500.xlsx"


def test_an_output_file_name_is_never_just_the_extension():
    now = datetime(2026, 9, 30, 10, 15, 0)

    assert output_file_name("  ", now=now, add_date_time=False) == (
        "260930_101500.xlsx"
    )
    assert output_file_name(".xlsx", now=now, add_date_time=False) == (
        "260930_101500.xlsx"
    )


def test_output_base_name_is_the_name_without_its_extension():
    assert output_base_name(" DEMO01 DSMB ") == "DEMO01 DSMB"
    assert output_base_name("report .XLSX") == "report"
    assert output_base_name("..\\x") == ".._x"
    assert output_base_name("report.csv", extension=".csv") == "report"
    assert output_base_name("   ") == ""
    assert output_base_name(".xlsx") == ""


def test_output_file_name_cannot_leave_the_output_folder():
    name = output_file_name(
        "..\\..\\secret/report:v2", now=datetime(2026, 1, 2, 3, 4, 5)
    )

    assert "/" not in name and "\\" not in name and ":" not in name
    assert name == ".._.._secret_report_v2 260102_030405.xlsx"
