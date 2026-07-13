"""Load Corelisting, CSV, Excel, and additional clinical-report inputs."""

from __future__ import annotations

import os
import re
import zipfile
from pathlib import Path
from typing import Dict, Iterable, Tuple, Union

import pandas as pd

# Keep literal clinical values such as "N/A", "None", and "n/a".  Pandas'
# remaining conventional markers continue to be interpreted as missing.
_DEFAULT_NA_VALUES_EXCEPT_LITERAL_NA = [
    "",
    "#N/A",
    "#N/A N/A",
    "#NA",
    "-1.#IND",
    "-1.#QNAN",
    "-NaN",
    "-nan",
    "1.#IND",
    "1.#QNAN",
    "<NA>",
    "NULL",
    "NaN",
    "nan",
    "null",
]
_READ_TABULAR_KWARGS = {
    "keep_default_na": False,
    "na_values": _DEFAULT_NA_VALUES_EXCEPT_LITERAL_NA,
}


def load_tabular_file(
    file_path: str, *, sheet: Union[int, str, None] = 0
) -> pd.DataFrame:
    """Load a CSV or Excel file while preserving literal clinical NA values."""
    path = Path(file_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, **_READ_TABULAR_KWARGS)
    if suffix in {".xls", ".xlsx"}:
        return pd.read_excel(path, sheet_name=sheet, **_READ_TABULAR_KWARGS)

    raise ValueError(
        f"Unsupported file type for additional input: {suffix or 'unknown'}"
    )


def load_additional_inputs(file_paths: Iterable[str]) -> Dict[str, pd.DataFrame]:
    """Load tabular files into dataframes keyed by absolute path."""
    additional_inputs: Dict[str, pd.DataFrame] = {}
    for file_path in file_paths:
        resolved_path = str(Path(file_path).expanduser().resolve())
        additional_inputs[resolved_path] = load_tabular_file(resolved_path)
    return additional_inputs


def read_data_dict_zip_corelisting(input_dir: str, cut_off_date=None) -> dict:
    """Read a Corelisting ZIP and apply its clinical data-cleaning rules."""
    data: dict = {}
    if cut_off_date is not None:
        cut_off_date = pd.to_datetime(cut_off_date)

    with zipfile.ZipFile(input_dir, "r") as archive:
        for file_name in archive.namelist():
            if not file_name.endswith(".csv"):
                continue

            file_stem = file_name.split(".")[0]
            with archive.open(file_name) as source:
                df = pd.read_csv(source, **_READ_TABULAR_KWARGS)
                last_token = file_stem.split("_")[-1]
                is_eos = "EOS" in last_token and "EOSTCONF" not in last_token

                has_event_date = (
                    "Event Date" in df.columns
                    and df["Event Date"].isnull().sum() != len(df["Event Date"])
                )
                if has_event_date or is_eos:
                    df["Event Date"] = pd.to_datetime(df["Event Date"])
                    if cut_off_date is not None and not is_eos:
                        df = df[df["Event Date"] <= cut_off_date]
                    elif cut_off_date is not None and is_eos:
                        column_name = df.columns[
                            df.columns.str.contains("End of Study Date", case=False)
                        ][0]
                        df[column_name] = pd.to_datetime(df[column_name]).dt.date
                        df = df[
                            (df[column_name] <= cut_off_date.date())
                            | df[column_name].isnull()
                        ]

                df = df.loc[:, ~df.columns.str.contains("_RAW")]
                df["Subject"] = df["Subject"].str.replace(
                    "^100-", "", regex=True
                )
                df = df[df["Form Status"] == "Submitted"]
                df = df[df["Form ILB Status"] == False]  # noqa: E712

            tokens = file_stem.split("_")
            form_name = tokens[-1] if tokens[-1] != "2" else f"{tokens[-2]}_2"
            data[form_name] = df

    return data


def parse_study_name(file_path: str) -> str:
    """Derive the study name used by the UI from a Corelisting filename."""
    file_name = os.path.basename(file_path)
    file_parts = file_name.split("_")
    if len(file_parts) > 2:
        return file_parts[2]
    return os.path.splitext(file_name)[0]


def strip_subject_prefix(value):
    """Remove a leading ``UPCC`` or ``100-`` subject-site prefix."""
    if isinstance(value, str):
        cleaned = re.sub(
            r"^(?:UPCC[-\s]*|100-)", "", value, flags=re.IGNORECASE
        )
        return cleaned.lstrip()
    return value


def build_additional_data_map(
    additional_inputs: Dict[str, pd.DataFrame],
    form_names: Dict[str, str],
    column_names: Dict[Tuple[str, str], str],
) -> Dict[str, pd.DataFrame]:
    """Apply UI form/column names and normalize additional input data."""
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


__all__ = [
    "build_additional_data_map",
    "load_additional_inputs",
    "load_tabular_file",
    "parse_study_name",
    "read_data_dict_zip_corelisting",
    "strip_subject_prefix",
]
