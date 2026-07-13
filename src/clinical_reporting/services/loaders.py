"""Data-loading and input-shaping helpers.

These functions build the ``{form_name: DataFrame}`` dictionary that
:class:`~clinical_reporting.core.report.CLReport` consumes. They were lifted
out of the PySide6 UI so the same loading / combining logic can be reused from
scripts, batch jobs, tool chains, or a future API without instantiating any
widgets.

The low-level file readers live in their own modules --
:func:`load_tabular_file` / :func:`load_additional_inputs` in
:mod:`clinical_reporting.services.tabular` and
:func:`read_data_dict_zip_corelisting` in
:mod:`clinical_reporting.services.corelisting` -- and are re-exported here so
callers can treat this module as the single entry point for data loading.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

from clinical_reporting.services.corelisting import read_data_dict_zip_corelisting
from clinical_reporting.services.tabular import load_additional_inputs, load_tabular_file

__all__ = [
    "load_tabular_file",
    "load_additional_inputs",
    "read_data_dict_zip_corelisting",
    "parse_study_name",
    "strip_subject_prefix",
    "build_additional_data_map",
]


def parse_study_name(file_path: str) -> str:
    """Derive a study name from a Corelisting zip file name.

    Mirrors the original UI behaviour: the study name is the third
    underscore-delimited segment of the file name when present, otherwise the
    file stem.
    """
    file_name = os.path.basename(file_path)
    file_parts = file_name.split("_")
    if len(file_parts) > 2:
        return file_parts[2]
    return os.path.splitext(file_name)[0]


def strip_subject_prefix(value):
    """Remove a leading ``UPCC`` or ``100-`` (with optional separators) from a subject string.

    Non-string values are returned unchanged.
    """
    if isinstance(value, str):
        cleaned = re.sub(r"^(?:UPCC[-\s]*|100-)", "", value, flags=re.IGNORECASE)
        return cleaned.lstrip()
    return value


def build_additional_data_map(
    additional_inputs: Dict[str, pd.DataFrame],
    form_names: Dict[str, str],
    column_names: Dict[Tuple[str, str], str],
) -> Dict[str, pd.DataFrame]:
    """Build a ``{form_name: DataFrame}`` map from loaded additional input files.

    Applies the user-configured form/column renames, drops blank/``Unnamed``
    columns, and normalises the ``Subject`` column by stripping site prefixes.

    Args:
        additional_inputs: Mapping of file path -> loaded DataFrame.
        form_names: Mapping of file path -> desired form name. Falls back to
            the file name when a path is missing.
        column_names: Mapping of ``(file_path, original_column)`` -> new column
            name. Entries whose new name matches the original are ignored.

    Returns:
        A dictionary keyed by form name, ready to pass to ``CLReport.set_data``.
    """
    data_map: Dict[str, pd.DataFrame] = {}
    for file_path, df in additional_inputs.items():
        form_name = form_names.get(file_path) or Path(file_path).name

        df_clean = df.copy()
        drop_cols = []
        rename_map = {}
        for column in df_clean.columns:
            column_str = str(column)
            if not column_str or column_str.lower().startswith("unnamed"):
                drop_cols.append(column)
                continue
            updated_name = column_names.get((file_path, column_str))
            if updated_name and updated_name != column:
                rename_map[column] = updated_name

        if drop_cols:
            df_clean = df_clean.drop(columns=drop_cols)
        if rename_map:
            df_clean = df_clean.rename(columns=rename_map)

        if "Subject" in df_clean.columns:
            df_clean["Subject"] = df_clean["Subject"].apply(strip_subject_prefix)

        data_map[form_name] = df_clean
    return data_map
