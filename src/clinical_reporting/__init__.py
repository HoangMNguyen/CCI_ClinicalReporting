"""Public, headless API for the Clinical Reporting package.

Importing :mod:`clinical_reporting` intentionally does not import PySide6.  The
desktop application is loaded only by :mod:`clinical_reporting.__main__`.

The entry point for automations and scripts is :func:`build_base_report`: it
runs a saved setting on a Corelisting export, and
:meth:`BaseReport.to_workbook` gives the workbook the desktop exports for it
(``build_base_report_from_forms`` does the same from forms already read).
"""

from .base_report import BaseReport, build_base_report, build_base_report_from_forms
from .data import (
    build_additional_data_map,
    load_additional_inputs,
    load_tabular_file,
    read_data_dict_zip_corelisting,
    try_load_tabular_files,
)
from .export import dataframe_to_xlsx_bytes, write_csv, write_xlsx
from .models import CLForm
from .report import CLReport
from .validation import (
    ReportValidationError,
    ReportValidationIssue,
    validate_report,
)

# Single source of truth for the release version. ``build_support.py`` reads
# this string when building the executable, so bumping a release means editing
# it here and nowhere else.
__version__ = "2.21"

__all__ = [
    "BaseReport",
    "CLForm",
    "CLReport",
    "ReportValidationError",
    "ReportValidationIssue",
    "build_additional_data_map",
    "build_base_report",
    "build_base_report_from_forms",
    "dataframe_to_xlsx_bytes",
    "load_additional_inputs",
    "load_tabular_file",
    "read_data_dict_zip_corelisting",
    "try_load_tabular_files",
    "validate_report",
    "write_csv",
    "write_xlsx",
]
