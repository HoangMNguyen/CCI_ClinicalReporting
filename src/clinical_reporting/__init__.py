"""Public, headless API for the Clinical Reporting package.

Importing :mod:`clinical_reporting` intentionally does not import PySide6.  The
desktop application is loaded only by :mod:`clinical_reporting.__main__`.
"""

from .data import (
    build_additional_data_map,
    load_additional_inputs,
    load_tabular_file,
    read_data_dict_zip_corelisting,
    try_load_tabular_files,
)
from .export import dataframe_to_xlsx_bytes, write_csv, write_xlsx
from .models import CLForm, ReportConfig
from .report import CLReport
from .validation import (
    ReportValidationError,
    ReportValidationIssue,
    validate_report,
)

# Single source of truth for the release version. ``build_support.py`` reads
# this string when building the executable, so bumping a release means editing
# it here and nowhere else.
__version__ = "2.00"

# ``Report`` is the preferred public name. ``CLReport`` remains available for
# settings/scripts written against earlier releases.
Report = CLReport

__all__ = [
    "CLForm",
    "CLReport",
    "Report",
    "ReportConfig",
    "ReportValidationError",
    "ReportValidationIssue",
    "build_additional_data_map",
    "dataframe_to_xlsx_bytes",
    "load_additional_inputs",
    "load_tabular_file",
    "read_data_dict_zip_corelisting",
    "try_load_tabular_files",
    "validate_report",
    "write_csv",
    "write_xlsx",
]
