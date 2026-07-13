"""Public, headless API for the Clinical Reporting package.

Importing :mod:`clinical_reporting` intentionally does not import PySide6.  The
desktop application is loaded only by :mod:`clinical_reporting.__main__`.
"""

from .models import CLForm, ReportConfig
from .report import CLReport
from .validation import (
    ReportValidationError,
    ReportValidationIssue,
    validate_report,
)
from .data import (
    build_additional_data_map,
    load_additional_inputs,
    load_tabular_file,
    read_data_dict_zip_corelisting,
)
from .export import dataframe_to_xlsx_bytes, write_csv, write_xlsx

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
    "validate_report",
    "write_csv",
    "write_xlsx",
]
