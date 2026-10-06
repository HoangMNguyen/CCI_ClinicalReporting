"""The enrollment log: one of CCI Automation's workflows.

:func:`run` reads a Corelisting export and returns the study's enrollment
log (:class:`clinical_reporting.workflow.OutputFile`); :class:`EnrollmentLog`
builds it with the study's own module (``EnrollmentLog<study>.py``). Nothing
here touches Qt or a folder.
"""

import io
from datetime import date
from typing import Optional

import pandas as pd

from clinical_reporting.filenames import output_file_name
from clinical_reporting.workflow import (
    OutputFile,
    UnsupportedStudyError,
    check_study,
    missing_forms_error,
    read_corelisting,
)

#: What the messages call this workflow (in the middle of a sentence).
WORKFLOW = "the enrollment log"
#: Studies with an enrollment log module.
SUPPORTED_STUDIES = (
    "03325",
    "03821",
    "10325",
    "11823",
    "12423",
    "15122",
    "15420",
    "16321",
    "30425",
    "50425",
)


def default_file_name(study: str) -> str:
    """The file name to suggest for *study*'s log (the run adds the time)."""
    return f"{study} Enrollment Log"


def run(
    corelisting,
    *,
    study: str,
    cut_off_date: Optional[date] = None,
    file_name: str = "",
) -> OutputFile:
    """Build *study*'s enrollment log from a Corelisting export.

    *corelisting* is the ZIP: its path, or a file-like object (an upload).
    With *cut_off_date*, rows dated after it are left out. The workbook is
    named *file_name* (or :func:`default_file_name`) plus the date and time.
    Raises :class:`~clinical_reporting.workflow.WorkflowInputError` for a
    study without a log, an export whose file name names another study, or
    one that is gone or can't be read.
    """
    if study not in SUPPORTED_STUDIES:
        raise UnsupportedStudyError(WORKFLOW, study, SUPPORTED_STUDIES)
    check_study(corelisting, study, WORKFLOW, SUPPORTED_STUDIES)
    data = read_corelisting(corelisting, cut_off_date)
    if "DM" not in data:  # Every study's log starts from the Demographics form.
        raise missing_forms_error(WORKFLOW, ["DM"])
    workbook = EnrollmentLog(data, study).to_excel_bytes()
    name = (file_name or "").strip() or default_file_name(study)
    return OutputFile(output_file_name(name), workbook)


class EnrollmentLog:
    """A study's enrollment log, worked out from its Corelisting forms."""

    def __init__(self, data, study_name):
        """Work out the log from *data* (form name to its DataFrame)."""
        self.study_name = study_name
        self.data = data
        self.output_df = self.collect_data()

    def to_excel_bytes(self) -> bytes:
        """The log as a workbook."""
        buffer = io.BytesIO()
        self.output(buffer)
        return buffer.getvalue()

    def collect_data(self):
        if self.study_name == "12423":
            from .EnrollmentLog12423 import EnrollmentLog12423

            output_df = EnrollmentLog12423(self.data)
        elif self.study_name == "03821":
            from .EnrollmentLog03821 import EnrollmentLog03821

            output_df = EnrollmentLog03821(self.data)
        elif self.study_name == "11823":
            from .EnrollmentLog11823 import EnrollmentLog11823

            output_df = EnrollmentLog11823(self.data)
        elif self.study_name == "15122":
            from .EnrollmentLog15122 import EnrollmentLog15122

            output_df = EnrollmentLog15122(self.data)
        elif self.study_name == "15420":
            from .EnrollmentLog15420 import EnrollmentLog15420

            output_df = EnrollmentLog15420(self.data)
        elif self.study_name == "16321":
            from .EnrollmentLog16321 import EnrollmentLog16321

            output_df = EnrollmentLog16321(self.data)
        elif self.study_name == "03325":
            from .EnrollmentLog03325 import EnrollmentLog03325

            output_df = EnrollmentLog03325(self.data)
        elif self.study_name == "10325":
            from .EnrollmentLog10325 import EnrollmentLog10325

            output_df = EnrollmentLog10325(self.data)
        elif self.study_name == "50425":
            from .EnrollmentLog50425 import EnrollmentLog50425

            output_df = EnrollmentLog50425(self.data)
        elif self.study_name == "30425":
            from .EnrollmentLog30425 import EnrollmentLog30425

            output_df = EnrollmentLog30425(self.data)
        else:
            raise UnsupportedStudyError(WORKFLOW, self.study_name, SUPPORTED_STUDIES)
        return output_df

    def output(self, target):
        """Write the log's workbook to *target* (a path or a binary file)."""
        sheet_name = "Enrollment Log " + self.study_name
        subject_id_columns = [
            col
            for col in self.output_df.columns
            if str(col).strip().lower().startswith("subject")
        ]
        for col in subject_id_columns:
            self.output_df[col] = self.output_df[col].where(
                self.output_df[col].isna(), self.output_df[col].astype(str)
            )

        # Convert all potential date-like columns to datetime
        for col in self.output_df.columns:
            if col in subject_id_columns:
                continue
            # check if text is stored as the dedicated string dtype instead of object.
            is_text_dtype = pd.api.types.is_object_dtype(
                self.output_df[col]
            ) or pd.api.types.is_string_dtype(self.output_df[col])
            if pd.api.types.is_datetime64_any_dtype(self.output_df[col]) or (
                is_text_dtype
                and self.output_df[col]
                .apply(lambda x: pd.to_datetime(x, errors="coerce"))
                .notna()
                .any()
            ):
                # format="mixed" parses each element individually (dates are "m/d/Y", blanks/"N/A"
                # coerce to NaT) — same result as before but without pandas' format-inference warning.
                self.output_df[col] = pd.to_datetime(
                    self.output_df[col], errors="coerce", format="mixed"
                )

        with pd.ExcelWriter(target, engine="xlsxwriter") as writer:
            # Write once
            self.output_df.to_excel(writer, index=False, sheet_name=sheet_name)

            workbook = writer.book
            worksheet = writer.sheets[sheet_name]

            # Excel date format with no leading zeros
            date_fmt = workbook.add_format({"num_format": "m/d/yyyy"})
            text_fmt = workbook.add_format({"num_format": "@"})

            # Overwrite datetime cells with proper Excel dates
            for row_idx in range(1, len(self.output_df) + 1):  # +1 skips header
                row = self.output_df.iloc[row_idx - 1]
                eos_val = row["End of Study Date"]

                for col_idx, col_name in enumerate(self.output_df.columns):
                    val = row[col_name]

                    if not pd.isna(eos_val):  # End of Study Date is NOT blank
                        if col_name == "End of Study Date":
                            # Always write the actual End of Study Date
                            worksheet.write_datetime(
                                row_idx, col_idx, eos_val.to_pydatetime(), date_fmt
                            )
                        else:
                            if pd.isna(val) or val == "":
                                # Blank → force "N/A"
                                worksheet.write(row_idx, col_idx, "N/A")
                            else:
                                # Keep original value
                                if pd.api.types.is_datetime64_any_dtype(
                                    self.output_df[col_name]
                                ):
                                    worksheet.write_datetime(
                                        row_idx, col_idx, val.to_pydatetime(), date_fmt
                                    )
                                else:
                                    worksheet.write(row_idx, col_idx, val)
                    else:
                        # End of Study Date IS blank → write everything as-is, no "N/A"
                        if pd.isna(val) or val == "":
                            worksheet.write(row_idx, col_idx, "")
                        else:
                            if pd.api.types.is_datetime64_any_dtype(
                                self.output_df[col_name]
                            ):
                                worksheet.write_datetime(
                                    row_idx, col_idx, val.to_pydatetime(), date_fmt
                                )
                            else:
                                worksheet.write(row_idx, col_idx, val)

            worksheet.autofit()

            blue_header_format = writer.book.add_format(
                {
                    "bg_color": "#B7DEE8",
                    "text_wrap": True,
                    "valign": "vcenter",
                    "align": "center",
                    "bold": True,
                    "border": 2,
                }
            )
            purple_header_format = writer.book.add_format(
                {
                    "bg_color": "#7030A0",
                    "text_wrap": True,
                    "valign": "vcenter",
                    "align": "center",
                    "bold": True,
                    "font_color": "white",
                    "border": 2,
                }
            )
            green_header_format = writer.book.add_format(
                {
                    "bg_color": "#C4D79B",
                    "text_wrap": True,
                    "valign": "vcenter",
                    "align": "center",
                    "bold": True,
                    "border": 2,
                }
            )
            pink_header_format = writer.book.add_format(
                {
                    "bg_color": "#FABF8F",
                    "text_wrap": True,
                    "valign": "vcenter",
                    "align": "center",
                    "bold": True,
                    "border": 2,
                }
            )
            lavender_header_format = writer.book.add_format(
                {
                    "bg_color": "#E5D6F5",
                    "text_wrap": True,
                    "valign": "vcenter",
                    "align": "center",
                    "bold": True,
                    "border": 2,
                }
            )
            yellow_header_format = writer.book.add_format(
                {
                    "bg_color": "#FFFF00",
                    "text_wrap": True,
                    "valign": "vcenter",
                    "align": "center",
                    "bold": True,
                    "border": 2,
                }
            )
            border_format = writer.book.add_format({"border": 1})
            worksheet.conditional_format(
                0,
                0,
                len(self.output_df.index),
                len(self.output_df.columns) - 1,
                {"type": "formula", "criteria": "True", "format": border_format},
            )
            if self.study_name == "11823":
                for i in range(7):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], blue_header_format
                    )
                for i in range(7, 11):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], purple_header_format
                    )
                for i in range(11, 16):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], green_header_format
                    )
                for i in range(16, 22):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], pink_header_format
                    )
                for i in range(22, 23):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], yellow_header_format
                    )
            elif self.study_name == "12423":
                for i in range(8):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], blue_header_format
                    )
                for i in range(8, 12):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], purple_header_format
                    )
                for i in range(12, 17):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], green_header_format
                    )
                for i in range(17, 23):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], pink_header_format
                    )
                for i in range(23, 24):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], yellow_header_format
                    )
            elif self.study_name == "15122":
                for i in range(8):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], blue_header_format
                    )
                for i in range(8, 12):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], purple_header_format
                    )
                for i in range(12, 17):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], green_header_format
                    )
                for i in range(17, 18):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], pink_header_format
                    )
                for i in range(18, 19):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], yellow_header_format
                    )
            elif self.study_name == "15420":
                for i in range(8):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], blue_header_format
                    )
                for i in range(8, 11):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], purple_header_format
                    )
                for i in range(11, 17):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], green_header_format
                    )
                for i in range(17, 23):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], pink_header_format
                    )
                for i in range(23, 24):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], yellow_header_format
                    )
            elif self.study_name == "16321":
                for i in range(7):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], blue_header_format
                    )
                for i in range(7, 11):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], purple_header_format
                    )
                for i in range(11, 17):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], green_header_format
                    )
                for i in range(17, 27):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], pink_header_format
                    )
                for i in range(27, 28):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], yellow_header_format
                    )
            elif self.study_name == "03821":
                for i in range(9):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], blue_header_format
                    )
                for i in range(9, 13):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], purple_header_format
                    )
                for i in range(13, 19):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], green_header_format
                    )
                for i in range(19, 25):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], pink_header_format
                    )
                for i in range(25, 26):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], yellow_header_format
                    )
            elif self.study_name == "03325":
                for i in range(8):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], blue_header_format
                    )
                for i in range(8, 12):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], purple_header_format
                    )
                for i in range(12, 24):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], green_header_format
                    )
                for i in range(24, 29):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], pink_header_format
                    )
                for i in range(29, 30):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], yellow_header_format
                    )
            elif self.study_name == "10325":
                for i in range(8):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], blue_header_format
                    )
                for i in range(8, 12):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], purple_header_format
                    )
                for i in range(12, 20):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], green_header_format
                    )
                for i in range(20, 26):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], pink_header_format
                    )
                for i in range(26, 27):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], yellow_header_format
                    )
            elif self.study_name == "50425":
                for i in range(9):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], pink_header_format
                    )
                for i in range(9, 12):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], purple_header_format
                    )
                for i in range(12, 16):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], lavender_header_format
                    )
                for i in range(16, 19):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], blue_header_format
                    )
                for i in range(19, 26):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], green_header_format
                    )
                for i in range(26, 28):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], yellow_header_format
                    )
            elif self.study_name == "30425":
                for i in range(0, 8):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], blue_header_format
                    )
                for i in range(8, 11):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], purple_header_format
                    )
                for i in range(11, 14):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], green_header_format
                    )
                for i in range(14, 18):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], blue_header_format
                    )
                for i in range(18, 19):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], green_header_format
                    )
                for i in range(19, 23):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], pink_header_format
                    )
                for i in range(23, 26):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], blue_header_format
                    )
                for i in range(26, 28):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], pink_header_format
                    )
                for i in range(28, 29):
                    worksheet.write(
                        0, i, self.output_df.columns.values[i], yellow_header_format
                    )

            worksheet.set_row(0, 60)
            worksheet.set_column("A:CQ", 15)
            for col_name in subject_id_columns:
                col_idx = self.output_df.columns.get_loc(col_name)
                worksheet.set_column(col_idx, col_idx, 15, text_fmt)
        # writer.save()
