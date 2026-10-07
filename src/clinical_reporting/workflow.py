"""What the automation tools' workflows take and give back.

Each workflow is a plain function, ``run(<inputs>, *, <options>) -> OutputFile``:
it reads its input files (a path or a file-like object), builds the workbook in
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
import re
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Iterator, Optional, Tuple, Type

from clinical_reporting.data import parse_study_name, read_data_dict_zip_corelisting
from clinical_reporting.filenames import output_file_name


@dataclass(frozen=True)
class OutputFile:
    """A finished workbook: the file name to save it under, and its bytes."""

    name: str
    data: bytes


def named_output(
    data: bytes, *, file_name: str, default_name: str, now: Optional[datetime] = None
) -> OutputFile:
    """*data* saved as "<file_name or default_name> YYMMDD_HHMMSS.xlsx".

    *now* stamps the name (a server passes the user's local time).
    """
    name = (file_name or "").strip() or default_name
    return OutputFile(output_file_name(name, now=now), data)


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


def file_name_of(source, fallback: str = "the file") -> str:
    """The name to call *source* in a message: its file name, or *fallback*."""
    return os.path.basename(input_name(source)) or fallback


@contextmanager
def reading_input(
    source,
    what: str,
    *,
    unreadable: Tuple[Type[BaseException], ...] = (zipfile.BadZipFile, KeyError),
    damage: str = "damaged",
) -> Iterator[None]:
    """Report a problem reading the input file *source* as a WorkflowInputError.

    A file that isn't there any more or can't be opened gets a message that
    names it, and so do the *unreadable* errors: "Couldn't read X. The file
    may be <damage>, or it isn't <what>." (*what* e.g. "a Corelisting
    export"). Wrap only the reading, and widen *unreadable* only where those
    errors can only mean an unreadable file: pandas raises ValueError for a
    file that isn't a workbook, but also for a bad date in a good one. A
    :class:`WorkflowInputError` raised inside passes as is.
    """
    name = file_name_of(source)
    try:
        yield
    except WorkflowInputError:
        raise
    except FileNotFoundError as exc:
        raise WorkflowInputError(
            f"Couldn't find {name}. It may have been moved or deleted; choose it again."
        ) from exc
    except PermissionError as exc:
        raise WorkflowInputError(
            f"Couldn't open {name}. It may be open in another program, or you "
            "may not have access to it."
        ) from exc
    except unreadable as exc:
        raise WorkflowInputError(
            f"Couldn't read {name}. The file may be {damage}, or it isn't {what}."
        ) from exc


#: A browser's " (n)" on a second download of the same file.
_COPY_SUFFIX = re.compile(r"\s*\(\d+\)$")
#: Five digits, alone or followed by "-" and a description.
_STUDY_TOKEN = re.compile(r"(\d{5})(?:-.*)?")


def study_named_by(source) -> Optional[str]:
    """The five-digit study number in a Corelisting export's file name, if any.

    It is the third "_"-separated part of the name, or the whole name when it
    has fewer parts (see :func:`~clinical_reporting.data.parse_study_name`):
    five digits, alone or followed by "-" and a description, with a browser's
    " (n)" copy suffix ignored. "Core_Listings_15420_….zip",
    "Core_Listings_15420 (1).zip" and "Core_Listings_12423-TmCD19-IL18_….zip"
    name 15420, 15420 and 12423; "Core_Listings_154201_….zip" and
    "UPCC15420_CoreListing_20260901.zip" name none.
    """
    token = os.path.splitext(parse_study_name(input_name(source)))[0]
    match = _STUDY_TOKEN.fullmatch(_COPY_SUFFIX.sub("", token))
    return match.group(1) if match else None


def check_study(source, study: str, workflow: str, supported: Iterable[str]) -> None:
    """Raise :class:`WorkflowInputError` if *source*'s file name names another study.

    When that study isn't one *workflow* supports, the message says so (rather
    than suggesting a study it can't do).
    """
    supported = tuple(supported)
    named = study_named_by(source)
    if named and named not in supported:
        raise UnsupportedStudyError(workflow, named, supported)
    if named and named != study:
        raise WorkflowInputError(
            f"{file_name_of(source, 'The file')} is an export of study {named}, "
            f"but study {study} is chosen. Choose study {named}, or study {study}'s "
            "export."
        )


def read_corelisting(source, cut_off_date=None) -> dict:
    """Read a Corelisting export for a workflow: form name to its DataFrame.

    *source* is the ZIP's path or a file-like object (see
    :func:`clinical_reporting.data.read_data_dict_zip_corelisting`). A file
    that isn't there any more, can't be opened, isn't a ZIP, or lacks the
    Corelisting columns raises :class:`WorkflowInputError` saying so.
    """
    with reading_input(source, "a Corelisting export"):
        return read_data_dict_zip_corelisting(source, cut_off_date)


__all__ = [
    "OutputFile",
    "UnsupportedStudyError",
    "WorkflowInputError",
    "check_study",
    "file_name_of",
    "input_name",
    "missing_forms_error",
    "named_output",
    "read_corelisting",
    "reading_input",
    "study_named_by",
]
