"""Low-level tabular file readers shared across the services layer.

Holds the CSV/Excel readers and the NA-handling configuration so both the
generic loaders and the corelisting-specific reader can use them without a
circular import.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Union

import pandas as pd

# Treat the literal strings "N/A", "None", "n/a" as meaningful clinical values
# rather than missing data; only the entries below are parsed as NaN.
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
    # "N/A",
    "NULL",
    "NaN",
    # "None",
    # "n/a",
    "nan",
    "null",
]
_READ_TABULAR_KWARGS = {
    "keep_default_na": False,
    "na_values": _DEFAULT_NA_VALUES_EXCEPT_LITERAL_NA,
}


def load_tabular_file(file_path: str, *, sheet: Union[int, str, None] = 0) -> pd.DataFrame:
    """
    Load a tabular file (CSV or Excel) into a dataframe.

    Args:
        file_path: Path to the CSV/XLS/XLSX file.
        sheet: Sheet name or index for Excel files. Ignored for CSV.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the extension is not supported.

    Returns:
        A pandas DataFrame containing the loaded data.
    """
    path = Path(file_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, **_READ_TABULAR_KWARGS)
    if suffix in {".xls", ".xlsx"}:
        return pd.read_excel(path, sheet_name=sheet, **_READ_TABULAR_KWARGS)

    raise ValueError(f"Unsupported file type for additional input: {suffix or 'unknown'}")


def load_additional_inputs(file_paths: Iterable[str]) -> Dict[str, pd.DataFrame]:
    """
    Load multiple tabular files into dataframes keyed by absolute path.

    Args:
        file_paths: Iterable of CSV/XLS/XLSX file paths.

    Returns:
        Dictionary mapping each resolved file path to its DataFrame.
    """
    additional_inputs: Dict[str, pd.DataFrame] = {}
    for file_path in file_paths:
        resolved_path = str(Path(file_path).expanduser().resolve())
        additional_inputs[resolved_path] = load_tabular_file(resolved_path)
    return additional_inputs
