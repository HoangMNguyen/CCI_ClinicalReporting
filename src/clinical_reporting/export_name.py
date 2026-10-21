"""The export's file name, kept with a saved setting.

The export names its workbook from a file name, with or without the date and
time of the export (:func:`clinical_reporting.filenames.output_file_name`).
A saved setting can keep both under :data:`SETTINGS_KEY`
(:func:`add_to_settings`; :func:`from_settings` reads them back). The desktop
app's Save setting keeps File name and Add the date and time there, picking
the setting on Source data fills them back in, and
:meth:`clinical_reporting.base_report.BaseReport.to_workbook` names its
workbook from them:

.. code-block:: json

    "export_file_name": {"name": "DEMO01 DSMB", "add_date_time": false}

The name is kept as the export uses it
(:func:`clinical_reporting.filenames.output_base_name`): without a typed
``.xlsx``, and with characters not allowed in file names made ``_``, so a
saved setting still holds no folder.

The key is optional. It is written only when a file name is given (not blank
or just ``.xlsx``), so a setting saved without one is saved exactly as before
the key existed. Settings without it give no name (:func:`from_settings`
returns ``None``), and versions before 2.21 ignore it, as they ignore any key
they don't know. Like the rest of the core, this module never imports Qt.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping, Optional

from clinical_reporting.filenames import output_base_name

logger = logging.getLogger(__name__)

#: The saved-settings key that holds the export's file name.
SETTINGS_KEY = "export_file_name"


@dataclass(frozen=True)
class ExportName:
    """The export file name a saved setting keeps."""

    #: The name, without the date and time or the extension.
    name: str
    #: Whether the date and time of the export are added to the name.
    add_date_time: bool = True


def add_to_settings(
    settings: MutableMapping[str, Any], name: str, *, add_date_time: bool
) -> MutableMapping[str, Any]:
    """Store the export's file name in a settings dictionary; return *settings*.

    *name* is the file name as typed. The key is only set when it gives a
    name (see :func:`~clinical_reporting.filenames.output_base_name`), so a
    setting without one is saved exactly as before the key existed.
    """
    base = output_base_name(name)
    if base:
        settings[SETTINGS_KEY] = {"name": base, "add_date_time": bool(add_date_time)}
    else:
        settings.pop(SETTINGS_KEY, None)
    return settings


def from_settings(settings: Any) -> Optional[ExportName]:
    """The export file name saved in a settings dictionary, or ``None``.

    Settings without the key give ``None``. A hand-edited or damaged key never
    stops a setting from loading: a key without a usable name is ignored, and
    an ``add_date_time`` that isn't true or false counts as true; both are
    logged. One without ``add_date_time`` adds the date and time.
    """
    raw = settings.get(SETTINGS_KEY) if isinstance(settings, Mapping) else None
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        logger.warning("Ignoring saved %s: not an object", SETTINGS_KEY)
        return None
    name = raw.get("name")
    base = output_base_name(name) if isinstance(name, str) else ""
    if not base:
        logger.warning(
            "Ignoring saved %s: no usable file name in %r", SETTINGS_KEY, raw
        )
        return None
    add_date_time = raw.get("add_date_time", True)
    if not isinstance(add_date_time, bool):
        logger.warning(
            "Ignoring saved %s add_date_time %r: not true or false",
            SETTINGS_KEY,
            add_date_time,
        )
        add_date_time = True
    return ExportName(base, add_date_time)


__all__ = ["ExportName", "SETTINGS_KEY", "add_to_settings", "from_settings"]
