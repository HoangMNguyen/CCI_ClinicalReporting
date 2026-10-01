"""What the automation tools' workflows take and give back.

Each workflow is a plain function, ``run(inputs, params) -> OutputFile``: it
reads its input files (a path or a file-like object), builds the workbook in
memory, and returns it with the file name to save it under. It never writes
to a folder: the desktop tools save the bytes where the user chose
(:func:`cci_ui.files.save_output`), and a web version would offer the same
bytes as a download.

A problem with the inputs that the user can fix (a study the workflow isn't
set up for, a form missing from the export, a file that isn't there or isn't
a ZIP) raises :class:`WorkflowInputError` with a message written for them, so
the tools show it as is, without a traceback. The messages name a workflow
in the middle of a sentence, e.g. "the AE & DLT listing".
"""

from __future__ import annotations

import os
import zipfile
from dataclasses import dataclass
from typing import Iterable, Optional

from clinical_reporting.data import read_data_dict_zip_corelisting


@dataclass(frozen=True)
class OutputFile:
    """A finished workbook: the file name to save it under, and its bytes."""

    name: str
    data: bytes


class WorkflowInputError(ValueError):
    """The inputs can't make this workbook; the message says why, for the user."""


def _sentence(text: str) -> str:
    """*text* to start a sentence: its first letter capitalised."""
    return text[:1].upper() + text[1:]


class UnsupportedStudyError(WorkflowInputError):
    """The workflow isn't set up for the study (forms and columns differ per study)."""

    def __init__(self, workflow: str, study: Optional[str], supported: Iterable[str]):
        self.study = study
        self.supported = tuple(sorted(supported))
        studies = ", ".join(self.supported)
        if study:
            message = (
                f"{_sentence(workflow)} isn't set up for study {study}. "
                f"It supports {studies}."
            )
        else:
            message = (
                f"The study number isn't in the file name, so {workflow} can't tell "
                f"which study this is. It supports {studies}."
            )
        super().__init__(message)


def missing_forms_error(workflow: str, missing: Iterable[str]) -> WorkflowInputError:
    """The error for a Corelisting export without forms that *workflow* reads."""
    names = " or ".join(sorted(missing))
    return WorkflowInputError(
        f"The Corelisting export has no {names} form, which {workflow} needs."
    )


def input_name(source) -> str:
    """The file name of *source*: a path, or a file-like object's ``name`` ("")."""
    if isinstance(source, (str, os.PathLike)):
        return os.fspath(source)
    name = getattr(source, "name", "")
    return name if isinstance(name, str) else ""


def read_corelisting(source, cut_off_date=None) -> dict:
    """Read a Corelisting export for a workflow: form name to its DataFrame.

    *source* is the ZIP's path or a file-like object (see
    :func:`clinical_reporting.data.read_data_dict_zip_corelisting`). A file
    that isn't there any more, can't be opened, isn't a ZIP, or lacks the
    Corelisting columns raises :class:`WorkflowInputError` saying so.
    """
    name = os.path.basename(input_name(source)) or "the Corelisting export"
    try:
        return read_data_dict_zip_corelisting(source, cut_off_date)
    except FileNotFoundError as exc:
        raise WorkflowInputError(
            f"Couldn't find {name}. It may have been moved or deleted; choose it again."
        ) from exc
    except PermissionError as exc:
        raise WorkflowInputError(
            f"Couldn't open {name}. It may be open in another program, or you "
            "may not have access to it."
        ) from exc
    except (zipfile.BadZipFile, KeyError) as exc:
        raise WorkflowInputError(
            f"Couldn't read {name}. The file may be damaged, or it isn't a "
            "Corelisting export."
        ) from exc


__all__ = [
    "OutputFile",
    "UnsupportedStudyError",
    "WorkflowInputError",
    "input_name",
    "missing_forms_error",
    "read_corelisting",
]
