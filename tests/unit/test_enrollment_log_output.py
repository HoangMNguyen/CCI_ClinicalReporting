from pathlib import Path

import pandas as pd
import pytest
from openpyxl import load_workbook

from cci_automation.enrollment_log.EnrollmentLog import EnrollmentLog


@pytest.mark.parametrize(("study_name", "column_count"), [("03325", 30), ("03821", 26)])
def test_enrollment_log_subject_id_is_written_as_text(
    tmp_path, study_name, column_count
):
    columns = (
        ["Subject ID#"]
        + [f"Col {idx}" for idx in range(2, column_count)]
        + ["End of Study Date"]
    )
    values = ["03/03/25"] + [""] * (column_count - 2) + ["05/01/2025"]

    enrollment_log = EnrollmentLog.__new__(EnrollmentLog)
    enrollment_log.study_name = study_name
    enrollment_log.output_df = pd.DataFrame([values], columns=columns)

    enrollment_log.output(Path(tmp_path) / f"enrollment_{study_name}.xlsx")

    worksheet = load_workbook(Path(tmp_path) / f"enrollment_{study_name}.xlsx")[
        f"Enrollment Log {study_name}"
    ]

    assert worksheet["A2"].value == "03/03/25"
    assert worksheet["A2"].data_type == "s"
    assert worksheet["A2"].number_format == "@"
