"""The names given to additional input files, kept with a saved setting.

On the Additional input step each extra CSV or Excel file becomes a form: it
gets a form name (its file name until renamed, and a name with a ``.`` can't
be applied) and, optionally, new names for its columns. A saved setting
keeps those names under :data:`SETTINGS_KEY`, one entry per renamed file, so
the next run can offer them again instead of the user retyping them:

.. code-block:: json

    "additional_input_names": [
        {
            "file_name": "lab_results.csv",
            "columns": ["Subject ID", "Visit Dt", "ALT (U/L)"],
            "form_name": "LAB",
            "column_names": {"Subject ID": "Subject", "Visit Dt": "Visit Date"}
        }
    ]

Entries name a file by its file name only, never its folder, so a saved
setting still holds no local paths and works on any machine. ``columns``
keeps the file's original headers, so a file saved under one name and
exported next time under another (a dated export, say) can still be
recognised: :func:`match` pairs listed files with entries by file name
first, then by the same column headers. An entry's column names for headers
a file doesn't have can't be used, unless another of its columns already
ends up with that name; :func:`ignored_names` lists them.

The key is optional. Settings saved before it existed have none, and
:func:`from_settings` then finds no entries; versions that predate it
ignore it, as they ignore any key they don't know. Like the rest of the
core, this module never imports Qt.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import PureWindowsPath
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
)

import pandas as pd

from clinical_reporting.data import named_columns

logger = logging.getLogger(__name__)

#: The saved-settings key that holds the entries.
SETTINGS_KEY = "additional_input_names"
#: :attr:`Match.by` when a file was matched by its file name.
BY_FILE_NAME = "file name"
#: :attr:`Match.by` when a file was matched by its column headers.
BY_COLUMNS = "columns"


@dataclass(frozen=True)
class SavedFileNames:
    """The names saved for one additional input file."""

    #: The file's name, without its folder.
    file_name: str
    #: Its original column headers ("Unnamed" and blank headers left out).
    columns: Tuple[str, ...] = ()
    #: The form name it was given ("" when only its columns were renamed).
    form_name: str = ""
    #: New column names, keyed by original header.
    column_names: Mapping[str, str] = field(default_factory=dict)


class Match(NamedTuple):
    """A listed file paired with a saved entry."""

    #: The entry's position in the saved list.
    index: int
    #: How they were paired: :data:`BY_FILE_NAME`, :data:`BY_COLUMNS`, or
    #: ``None`` when the user picked the entry.
    by: Optional[str] = None


class IgnoredName(NamedTuple):
    """A saved column name a listed file can't use (see :func:`ignored_names`)."""

    #: The file's name, without its folder.
    file_name: str
    #: The saved original header the file doesn't have.
    column: str
    #: The name it was to get.
    new_name: str


class FileNames(NamedTuple):
    """The names a saved entry gives one file (see :func:`names_from`)."""

    form_name: str
    #: New column names for the columns the file has, keyed by header.
    column_names: Dict[str, str]


def file_name_of(path: str) -> str:
    """The file name in *path*, whichever separator it uses."""
    return PureWindowsPath(path).name


def current_names(
    path: str,
    form_names: Mapping[str, str],
    column_names: Mapping[Tuple[str, str], str],
) -> Tuple[str, Dict[str, str]]:
    """The names *path* has now: its form name ("" if none) and column names.

    *form_names* and *column_names* are keyed as the Additional input step
    keeps them: by file path, and by ``(file path, original header)``.
    """
    form_name = (form_names.get(path) or "").strip()
    renames = {
        column: new_name
        for (file_path, column), new_name in column_names.items()
        if file_path == path and new_name
    }
    return form_name, renames


def to_settings(
    inputs: Mapping[str, pd.DataFrame],
    form_names: Mapping[str, str],
    column_names: Mapping[Tuple[str, str], str],
) -> List[Dict[str, Any]]:
    """The :data:`SETTINGS_KEY` entries for the files in *inputs*.

    *inputs* maps each listed file's path to its data. Only files with a
    form name or a column name get an entry, sorted by file name; folders
    are left out.
    """
    entries = []
    for path in sorted(inputs, key=lambda p: (file_name_of(p).casefold(), p)):
        form_name, renames = current_names(path, form_names, column_names)
        columns = named_columns(inputs[path])
        renames = {column: renames[column] for column in columns if column in renames}
        if not form_name and not renames:
            continue
        entries.append(
            {
                "file_name": file_name_of(path),
                "columns": columns,
                "form_name": form_name,
                "column_names": renames,
            }
        )
    return entries


def add_to_settings(
    settings: MutableMapping[str, Any],
    inputs: Mapping[str, pd.DataFrame],
    form_names: Mapping[str, str],
    column_names: Mapping[Tuple[str, str], str],
) -> MutableMapping[str, Any]:
    """Store the files' names in a settings dictionary; return *settings*.

    The key is only set when some file has names, so a setting without
    additional input names is saved exactly as before the key existed.
    """
    entries = to_settings(inputs, form_names, column_names)
    if entries:
        settings[SETTINGS_KEY] = entries
    else:
        settings.pop(SETTINGS_KEY, None)
    return settings


def _entry_from(item: Any) -> Optional[SavedFileNames]:
    """One saved entry, or ``None`` if *item* isn't a usable entry."""
    if not isinstance(item, Mapping):
        return None
    file_name = item.get("file_name")
    if not isinstance(file_name, str) or not file_name_of(file_name.strip()):
        return None
    columns = item.get("columns")
    columns = (
        [c for c in columns if isinstance(c, str)] if isinstance(columns, list) else []
    )
    form_name = item.get("form_name")
    form_name = form_name.strip() if isinstance(form_name, str) else ""
    renames = item.get("column_names")
    renames = renames if isinstance(renames, Mapping) else {}
    renames = {
        column: new_name.strip()
        for column, new_name in renames.items()
        if isinstance(column, str) and isinstance(new_name, str) and new_name.strip()
    }
    if not form_name and not renames:
        return None
    return SavedFileNames(
        file_name_of(file_name.strip()), tuple(columns), form_name, renames
    )


def from_settings(settings: Any) -> List[SavedFileNames]:
    """The entries saved in a settings dictionary, in their saved order.

    Settings without the key give none. A hand-edited or damaged key never
    stops a setting from loading: what can't be read is skipped and logged.
    """
    raw = settings.get(SETTINGS_KEY) if isinstance(settings, Mapping) else None
    if raw is None:
        return []
    if not isinstance(raw, list):
        logger.warning("Ignoring saved %s: not a list", SETTINGS_KEY)
        return []
    entries = []
    for position, item in enumerate(raw):
        entry = _entry_from(item)
        if entry is None:
            logger.warning(
                "Skipping saved %s entry %d: %r", SETTINGS_KEY, position, item
            )
        else:
            entries.append(entry)
    return entries


def match(
    saved: Sequence[SavedFileNames],
    files: Mapping[str, Sequence[str]],
    taken: Optional[Mapping[str, int]] = None,
) -> Dict[str, Match]:
    """Pair listed files with saved entries, one entry per file.

    *files* maps each listed file's path to its column headers (see
    :func:`clinical_reporting.data.named_columns`). *taken* maps files that
    already have an entry (the user's picks) to its index; those files and
    entries are left out.

    Files pair by file name first, ignoring case and folder, then the rest
    by the same set of column headers. Either way a pair is made only when
    the file and the entry are each other's only candidate, so two files
    named alike, or two entries with the same headers, pair with nothing.
    Files without headers never pair by columns.
    """
    taken = dict(taken or {})
    taken_entries = set(taken.values())
    free_files = [path for path in files if path not in taken]
    free_entries = [i for i in range(len(saved)) if i not in taken_entries]
    found: Dict[str, Match] = {}

    def pair(file_key: Callable[[str], Any], entry_key: Callable[[int], Any], by: str):
        files_by_key: Dict[Any, List[str]] = defaultdict(list)
        entries_by_key: Dict[Any, List[int]] = defaultdict(list)
        for path in free_files:
            if file_key(path):
                files_by_key[file_key(path)].append(path)
        for index in free_entries:
            if entry_key(index):
                entries_by_key[entry_key(index)].append(index)
        for key, paths in files_by_key.items():
            indexes = entries_by_key.get(key, [])
            if len(paths) == 1 and len(indexes) == 1:
                found[paths[0]] = Match(indexes[0], by)

    pair(
        lambda path: file_name_of(path).casefold(),
        lambda index: saved[index].file_name.casefold(),
        BY_FILE_NAME,
    )
    paired = {m.index for m in found.values()}
    free_files = [path for path in free_files if path not in found]
    free_entries = [index for index in free_entries if index not in paired]
    pair(
        lambda path: frozenset(files[path]),
        lambda index: frozenset(saved[index].columns),
        BY_COLUMNS,
    )
    return found


def names_from(entry: SavedFileNames, columns: Iterable[str]) -> FileNames:
    """The names *entry* gives a file with these column headers.

    Column names for headers the file doesn't have are left out (see
    :func:`ignored_names`).
    """
    present = set(columns)
    renames = {
        column: new_name
        for column, new_name in entry.column_names.items()
        if column in present
    }
    return FileNames(entry.form_name, renames)


def ignored_names(
    entry: SavedFileNames,
    path: str,
    columns: Iterable[str],
    column_names: Mapping[str, str],
) -> List[IgnoredName]:
    """The column names *entry* saved that the file at *path* can't use.

    *columns* are the file's headers and *column_names* the new names it has
    now, by header. A saved name is ignored when the file has no column with
    its header, unless one of the file's columns already ends up with that
    name (renamed by hand, say): then nothing is lost.
    """
    columns = list(columns)
    present = set(columns)
    names = {column_names.get(column) or column for column in columns}
    file_name = file_name_of(path)
    return [
        IgnoredName(file_name, column, new_name)
        for column, new_name in entry.column_names.items()
        if column not in present and new_name not in names
    ]


__all__ = [
    "BY_COLUMNS",
    "BY_FILE_NAME",
    "FileNames",
    "IgnoredName",
    "Match",
    "SETTINGS_KEY",
    "SavedFileNames",
    "add_to_settings",
    "current_names",
    "file_name_of",
    "from_settings",
    "ignored_names",
    "match",
    "names_from",
    "to_settings",
]
