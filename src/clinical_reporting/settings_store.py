"""Where saved report settings live.

The desktop app keeps each saved setting as a JSON file in a folder the user
picks (``~/Documents`` by default). Callers list, load, and save settings
through a :class:`SettingsStore`. The JSON helpers work on text as well as
files, so a setting's JSON can be read and written without a file.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Union

from clinical_reporting.filenames import safe_file_stem

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SavedSetting:
    """One saved setting as shown in a picker."""

    #: Display name (the ``setting_name`` stored in the file, or its stem).
    name: str
    #: Opaque identifier handed back to :meth:`SettingsStore.load`.
    key: str


class SettingsStore(Protocol):
    """Lists, loads, and saves settings dictionaries (see ``CLReport.settings_to_dict``)."""

    def list(self, study_name: Optional[str] = None) -> List[SavedSetting]:
        """Saved settings, limited to *study_name* when given."""

    def load(self, key: str) -> Dict[str, Any]:
        """The settings dictionary stored under *key*."""

    def save(self, name: str, settings: Dict[str, Any]) -> str:
        """Store *settings* as *name* and return its key."""


def default_settings_folder() -> Path:
    """The folder used for saved settings until the user picks another."""
    return Path.home() / "Documents"


def settings_to_json(settings: Dict[str, Any]) -> str:
    """A setting as the JSON text saved for it (4-space indent)."""
    return json.dumps(settings, indent=4)


def settings_from_json(text: str) -> Dict[str, Any]:
    """The setting a saved JSON text holds."""
    return json.loads(text)


def write_settings_json(
    path: Union[str, os.PathLike], settings: Dict[str, Any]
) -> None:
    """Save *settings* to the JSON file at *path*."""
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(settings_to_json(settings))


def read_settings_json(path: Union[str, os.PathLike]) -> Dict[str, Any]:
    """The setting saved in the JSON file at *path*."""
    with open(path, "r", encoding="utf-8") as handle:
        return settings_from_json(handle.read())


class LocalFolderStore:
    """Saved settings as ``<name>.json`` files in one folder.

    Keys are absolute file paths, so :meth:`load` opens whatever path it is
    given; only pass keys that came from :meth:`list` or :meth:`save`.
    """

    def __init__(self, folder: Union[str, os.PathLike]):
        self.folder = Path(folder)

    def list(self, study_name: Optional[str] = None) -> List[SavedSetting]:
        if not self.folder.exists():
            return []

        found = []
        for settings_file in self.folder.glob("*.json"):
            try:
                data = read_settings_json(settings_file)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Skipping invalid settings file %s: %s", settings_file, exc
                )
                continue
            if not isinstance(data, dict):
                logger.warning(
                    "Skipping settings file %s: not a settings object", settings_file
                )
                continue
            if study_name and data.get("study_name") != study_name:
                continue
            display_name = data.get("setting_name") or settings_file.stem
            found.append(SavedSetting(display_name, str(settings_file)))
        return found

    def load(self, key: str) -> Dict[str, Any]:
        return read_settings_json(key)

    def save(self, name: str, settings: Dict[str, Any]) -> str:
        """Write *settings* to ``<name>.json``; the name is made file-safe first."""
        self.folder.mkdir(parents=True, exist_ok=True)
        path = self.folder / f"{safe_file_stem(name)}.json"
        write_settings_json(path, settings)
        return str(path)


__all__ = [
    "LocalFolderStore",
    "SavedSetting",
    "SettingsStore",
    "default_settings_folder",
    "read_settings_json",
    "settings_from_json",
    "settings_to_json",
    "write_settings_json",
]
