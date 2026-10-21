"""What an automation, the web version or a script builds from a saved setting:
the base report (GLOSSARY), with no Qt and no telemetry.

:func:`build_base_report_from_forms` applies a saved setting to forms already
read, plus any additional inputs under the names the setting saved for them,
the way the desktop applies one the user picks, and runs it. A setting the
data doesn't fit is refused with a :class:`WorkflowInputError` that says what
is missing, unless ``missing_ok=True``; what the desktop would warn about
comes back in :attr:`BaseReport.warnings`. :func:`build_base_report` does the
same from a Corelisting export (a path or an open file), read as the desktop
reads it, up to an optional cut-off date. :meth:`BaseReport.to_workbook` names
the workbook as the desktop does, from the export file name the setting keeps
(:mod:`clinical_reporting.export_name`) unless one is given.
"""

from __future__ import annotations

import copy
import os
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Mapping, Optional, Sequence, Tuple, Union

import pandas as pd

from clinical_reporting import (
    additional_names,
    data,
    export_name,
    feedback,
    session,
    settings_store,
    stacking,
    steps,
    validation,
)
from clinical_reporting.export import dataframe_to_xlsx_bytes
from clinical_reporting.filenames import output_base_name, output_file_name
from clinical_reporting.workflow import (
    OutputFile,
    WorkflowInputError,
    input_name,
    read_corelisting,
    reading_input,
)

#: A saved setting: its dictionary, or the path of its JSON file.
Setting = Union[Mapping[str, Any], str, os.PathLike]
#: An input file: its path, or the open file (binary).
InputFile = Union[str, os.PathLike, BinaryIO]


@dataclass(frozen=True, eq=False)
class BaseReport:
    """A base report (GLOSSARY): a saved setting run on a study's data.

    ``table`` is the report's rows (no rows when nothing matched, with the
    columns kept); ``warnings`` are what the desktop would warn about, as
    :class:`~clinical_reporting.feedback.Message` objects (``kind`` is
    ``"warning"``); ``setting_name`` is the setting's name, its file's stem
    when it has none, or "" for an unnamed dictionary. ``file_name`` and
    ``add_date_time`` are the export file name the setting keeps
    (:mod:`clinical_reporting.export_name`): "" and ``True`` when it keeps
    none, as every setting saved before 2.21.
    """

    table: pd.DataFrame
    warnings: Tuple[feedback.Message, ...]
    setting_name: str
    file_name: str = ""
    add_date_time: bool = True

    def to_workbook(
        self,
        *,
        file_name: str = "",
        add_date_time: Optional[bool] = None,
        now: Optional[datetime] = None,
    ) -> OutputFile:
        """The table as the desktop exports it: a styled workbook, and its name.

        It is named as the desktop names it, from *file_name*, or from the
        file name the setting keeps when *file_name* is blank or just ".xlsx":
        "<name> YYMMDD_HHMMSS.xlsx", or "<name>.xlsx" when *add_date_time*
        (the setting's choice when ``None``) leaves out the date and time.
        Characters not allowed in file names are made "_"; *now* stamps it
        (default: the current time). Raises :class:`WorkflowInputError` when
        neither gives a name, just as the desktop waits for one.

        The bytes are the desktop export's for the same table, but for the
        creation time; a table without rows, which the desktop doesn't save,
        is written with its header row.
        """
        name = file_name if output_base_name(file_name) else self.file_name
        if not output_base_name(name):
            quoted = f" “{self.setting_name}”" if self.setting_name else ""
            raise WorkflowInputError(
                f"Give the workbook a file name: the saved setting{quoted} "
                "doesn't keep one."
            )
        if add_date_time is None:
            add_date_time = self.add_date_time
        return OutputFile(
            output_file_name(name, now=now, add_date_time=add_date_time),
            dataframe_to_xlsx_bytes(self.table),
        )


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


def _read_additional_inputs(
    sources: Sequence[InputFile],
) -> Dict[str, pd.DataFrame]:
    """Each additional input's rows, by its file name (its path, or ``name``)."""
    frames: Dict[str, pd.DataFrame] = {}
    for source in sources:
        key = input_name(source)
        if not key:
            raise WorkflowInputError(
                "An additional input has no file name. Give it one (a file "
                "object's name attribute) so its saved names can be found."
            )
        file_name = additional_names.file_name_of(key)
        if key in frames:
            raise WorkflowInputError(
                f"{file_name} is given twice as an additional input."
            )
        with reading_input(
            source,
            "a CSV or Excel file",
            unreadable=(ValueError, zipfile.BadZipFile),
        ):
            frames[key] = data.load_tabular_file(source, name=file_name)
    return frames


def _names_for(
    saved: Sequence[additional_names.SavedFileNames],
    frames: Mapping[str, pd.DataFrame],
) -> Tuple[
    Dict[str, str], Dict[Tuple[str, str], str], List[additional_names.IgnoredName]
]:
    """The form and column names the *saved* entries give the files *frames*.

    As the desktop picks them when the files are added: each file takes the
    entry it matches (:func:`clinical_reporting.additional_names.match`).
    Returns the form names by file, the column names by (file, column), and
    the saved column names the files can't use.
    """
    columns = {key: data.named_columns(frame) for key, frame in frames.items()}
    found = additional_names.match(saved, columns)
    form_names: Dict[str, str] = {}
    column_names: Dict[Tuple[str, str], str] = {}
    ignored: List[additional_names.IgnoredName] = []
    for key in sorted(
        found, key=lambda key: additional_names.file_name_of(key).casefold()
    ):
        entry = saved[found[key].index]
        names = additional_names.names_from(entry, columns[key])
        if names.form_name:
            form_names[key] = names.form_name
        for column, new_name in names.column_names.items():
            column_names[(key, column)] = new_name
        ignored.extend(
            additional_names.ignored_names(entry, key, columns[key], names.column_names)
        )
    return form_names, column_names, ignored


def build_base_report_from_forms(
    forms: Mapping[str, pd.DataFrame],
    setting: Setting,
    *,
    study_name: Optional[str] = None,
    additional_inputs: Sequence[InputFile] = (),
    missing_ok: bool = False,
) -> BaseReport:
    """Run the saved *setting* on *forms* (form name to its rows).

    *setting* is a settings dictionary or the path of a saved setting's JSON
    file; a setting with no name is named after its file. *study_name* is
    the report's study when the setting has none. *additional_inputs* are
    CSV or Excel files (paths, or open files with a ``name``) added as forms
    by the names the setting saved for them, as the desktop does. A file
    needs a saved form name: one named after itself is refused, its name
    holding a ".", as on the desktop.

    Raises :class:`WorkflowInputError` when the setting's file or an
    additional input can't be read, when the additional inputs' form names
    can't be used, when the setting needs forms or items the data lacks
    (unless *missing_ok*: they are left out, and said in the warnings), and
    when the report can't run (the desktop's "Cannot run:" message).
    """
    settings, setting_name = _read_setting(setting)
    frames = _read_additional_inputs(additional_inputs)
    form_names, column_names, ignored = _names_for(
        additional_names.from_settings(settings), frames
    )
    taken = set(forms) | {form.name for form in stacking.from_settings(settings)}
    clash = steps.additional_form_names_message(
        data.additional_form_names(frames, form_names), taken
    )
    if clash is not None:
        raise WorkflowInputError(clash.details)

    report = session.new_report(study_name, dict(forms))
    if frames:
        session.apply_additional_inputs(report, frames, form_names, column_names)
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
    coalesced = steps.coalesced_missing_message(report)
    if coalesced:
        warnings.append(coalesced)
    if ignored:
        warnings.append(steps.saved_names_ignored_message(ignored))
    saved = export_name.from_settings(settings)
    return BaseReport(
        table,
        tuple(warnings),
        setting_name,
        file_name=saved.name if saved else "",
        add_date_time=saved.add_date_time if saved else True,
    )


def build_base_report(
    corelisting: InputFile,
    setting: Setting,
    *,
    cut_off_date: Optional[date] = None,
    additional_inputs: Sequence[InputFile] = (),
    missing_ok: bool = False,
) -> BaseReport:
    """Run the saved *setting* on the Corelisting export *corelisting*.

    The export (a ZIP's path, or the open file) is read as the desktop reads
    it, up to *cut_off_date* when one is given; its study is named by its
    file name (:func:`clinical_reporting.data.parse_study_name`). The rest is
    :func:`build_base_report_from_forms`, which says what is refused.
    """
    forms = read_corelisting(corelisting, cut_off_date)
    name = input_name(corelisting)
    study = data.parse_study_name(name) if name else None
    return build_base_report_from_forms(
        forms,
        setting,
        study_name=study or None,
        additional_inputs=additional_inputs,
        missing_ok=missing_ok,
    )


__all__ = ["BaseReport", "build_base_report", "build_base_report_from_forms"]
