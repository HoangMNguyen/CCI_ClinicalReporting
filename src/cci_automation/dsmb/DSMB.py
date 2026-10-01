"""DSMB reports: one of CCI Automation's workflows.

:func:`run` reads a Corelisting export and returns the study's DSMB report
(:class:`clinical_reporting.workflow.OutputFile`). Each study's report comes
from its own module (``DSMB<study>.py``), which writes the workbook into a
folder; :func:`run` lets it write into a temporary folder and hands back the
bytes, so nothing here touches Qt or the user's folders.
"""

import tempfile
from datetime import date
from pathlib import Path
from typing import Optional

from clinical_reporting.filenames import output_file_name
from clinical_reporting.workflow import (
    OutputFile,
    UnsupportedStudyError,
    WorkflowInputError,
    check_study,
    missing_forms_error,
    read_corelisting,
)

#: What the messages call this workflow (in the middle of a sentence).
WORKFLOW = "the DSMB report"
#: Studies with a DSMB report module.
SUPPORTED_STUDIES = (
    "03325",
    "03821",
    "10325",
    "11823",
    "12423",
    "15122",
    "15420",
    "16321",
)


def default_file_name(study: str) -> str:
    """The file name to suggest for *study*'s report (the run adds the time)."""
    return f"{study} DSMB Report"


def run(
    corelisting,
    *,
    study: str,
    cut_off_date: Optional[date] = None,
    file_name: str = "",
) -> OutputFile:
    """Build *study*'s DSMB report from a Corelisting export.

    *corelisting* is the ZIP: its path, or a file-like object (an upload).
    With *cut_off_date*, rows dated after it are left out. The workbook is
    named *file_name* (or :func:`default_file_name`) plus the date and time.
    Raises :class:`~clinical_reporting.workflow.WorkflowInputError` for a
    study without a report (it used to make nothing, silently), an export
    whose file name names another study, one with no submitted Demographics
    (DM) forms (up to the cut-off date), or one that is gone or can't be read.

    The study's patient data sits in a temporary folder only while the module
    writes the report there.
    """
    if study not in SUPPORTED_STUDIES:
        raise UnsupportedStudyError(WORKFLOW, study, SUPPORTED_STUDIES)
    check_study(corelisting, study, WORKFLOW, SUPPORTED_STUDIES)
    data = read_corelisting(corelisting, cut_off_date)
    if "DM" not in data:
        raise missing_forms_error(WORKFLOW, ["DM"])
    # A file lock (an antivirus scan) mustn't turn a finished report, or the
    # module's own error, into a cleanup error.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        DSMB(data, study).write(folder, "report")
        report = Path(folder) / "report.xlsx"
        if not report.is_file():
            if data["DM"].empty:
                # Some studies' modules report only subjects with a DM form.
                when = " up to the cut-off date" if cut_off_date else ""
                raise WorkflowInputError(
                    "The Corelisting export has no submitted Demographics (DM) "
                    f"forms{when}, so there's no DSMB report to make."
                )
            raise RuntimeError(f"The DSMB module of study {study} wrote no report.")
        workbook = report.read_bytes()
    name = (file_name or "").strip() or default_file_name(study)
    return OutputFile(output_file_name(name), workbook)


class DSMB:
    """A study's DSMB report, written by the study's own module."""

    def __init__(self, data, study_name: str):
        """The report of *study_name* from *data* (form name to its DataFrame)."""
        self.input_data = data
        self.study_name = study_name

    def write(self, output_dir: str, output_file_name: str) -> None:
        """Write the report to ``<output_dir>/<output_file_name>.xlsx``."""
        self.output_dir = output_dir
        self.output_file_name = output_file_name
        self.data_analysis(self.input_data, self.study_name)

    def data_analysis(self, data, study_name):
        """Run *study_name*'s DSMB module on *data*.

        The module writes the report to
        ``<self.output_dir>/<self.output_file_name>.xlsx``.
        """
        if study_name not in SUPPORTED_STUDIES:
            raise UnsupportedStudyError(WORKFLOW, study_name, SUPPORTED_STUDIES)
        if study_name == "12423":
            from .DSMB12423 import DSMB12423

            x = DSMB12423(
                data,
                output_dir=self.output_dir,
                output_file_name=self.output_file_name,
            )
            x.run()
        if study_name == "11823":
            from .DSMB11823 import DSMB11823

            x = DSMB11823(
                data,
                output_dir=self.output_dir,
                output_file_name=self.output_file_name,
            )
            x.run()

        if study_name == "15122":
            from .DSMB15122 import DSMB15122

            DSMB15122(
                data,
                export=True,
                output_dir=self.output_dir,
                output_file_name=self.output_file_name,
            )
        if study_name == "03821":
            from .DSMB03821 import DSMB03821

            DSMB03821(
                data,
                export=True,
                output_dir=self.output_dir,
                output_file_name=self.output_file_name,
                #   debug=self.debug,
            )

        if study_name == "15420":
            from .DSMB15420 import DSMB15420

            DSMB15420(
                data,
                output_dir=self.output_dir,
                output_file_name=self.output_file_name,
            )

        if study_name == "16321":
            from .DSMB16321 import DSMB16321

            x = DSMB16321(
                data,
                output_dir=self.output_dir,
                output_file_name=self.output_file_name,
            )
            x.run()

        if study_name == "03325":
            from .DSMB03325 import DSMB03325

            x = DSMB03325(
                data,
                output_dir=self.output_dir,
                output_file_name=self.output_file_name,
            )
            x.run()

        if study_name == "10325":
            from .DSMB10325 import DSMB10325

            x = DSMB10325(
                data,
                output_dir=self.output_dir,
                output_file_name=self.output_file_name,
            )
            x.run()
