"""What an automation, the web version or a script builds from a saved setting:
the base report (GLOSSARY), with no Qt and no telemetry.

:func:`build_base_report_from_forms` applies a saved setting to forms already
read, the way the desktop applies one the user picks, and runs it. A setting
the data doesn't fit is refused with a :class:`WorkflowInputError` that says
what is missing, unless ``missing_ok=True``; what the desktop would warn
about comes back in :attr:`BaseReport.warnings`.
"""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Tuple, Union

import pandas as pd

from clinical_reporting import feedback, session, settings_store, steps, validation
from clinical_reporting.workflow import WorkflowInputError, reading_input

#: A saved setting: its dictionary, or the path of its JSON file.
Setting = Union[Mapping[str, Any], str, os.PathLike]


@dataclass(frozen=True, eq=False)
class BaseReport:
    """A base report (GLOSSARY): a saved setting run on a study's data.

    ``table`` is the report's rows (no rows when nothing matched, with the
    columns kept); ``warnings`` are what the desktop would warn about, as
    :class:`~clinical_reporting.feedback.Message` objects (``kind`` is
    ``"warning"``); ``setting_name`` is the setting's name, its file's stem
    when it has none, or "" for an unnamed dictionary.
    """

    table: pd.DataFrame
    warnings: Tuple[feedback.Message, ...]
    setting_name: str


def _read_setting(setting: Setting) -> Tuple[dict, str]:
    """The settings dictionary of *setting*, and the setting's name."""
    if isinstance(setting, Mapping):
        settings = copy.deepcopy(dict(setting))
        return settings, settings.get("setting_name") or ""
    with reading_input(setting, "a saved setting", unreadable=(ValueError,)):
        settings = settings_store.read_settings_json(setting)
        if not isinstance(settings, dict):
            raise ValueError("not a saved setting")
    return settings, settings.get("setting_name") or Path(setting).stem


def build_base_report_from_forms(
    forms: Mapping[str, pd.DataFrame],
    setting: Setting,
    *,
    study_name: Optional[str] = None,
    missing_ok: bool = False,
) -> BaseReport:
    """Run the saved *setting* on *forms* (form name to its rows).

    *setting* is a settings dictionary or the path of a saved setting's JSON
    file; a setting with no name is named after its file. *study_name* is
    the report's study when the setting has none.

    Raises :class:`WorkflowInputError` when the setting's file can't be read,
    when the setting needs forms or items *forms* lack (unless *missing_ok*:
    they are left out, and said in the warnings), and when the report can't
    run (the desktop's "Cannot run:" message).
    """
    settings, setting_name = _read_setting(setting)
    report = session.new_report(study_name, dict(forms))
    lines = steps.setting_missing_lines(session.apply_saved_setting(report, settings))
    if lines and not missing_ok:
        head = (
            f"The saved setting “{setting_name}” doesn't fit this export."
            if setting_name
            else "The saved setting doesn't fit this export."
        )
        raise WorkflowInputError("\n".join([head, *lines]))
    issues = report.validate()
    if issues:
        raise WorkflowInputError(str(validation.cannot_run_message(issues)))

    result = report.create_report()
    table = pd.DataFrame() if result is None else result.reset_index(drop=True)

    warnings = [feedback.warning(line) for line in lines]
    stacked = steps.stacked_missing_message(report)
    if stacked:
        warnings.append(stacked)
    return BaseReport(table, tuple(warnings), setting_name)


__all__ = ["BaseReport", "build_base_report_from_forms"]
