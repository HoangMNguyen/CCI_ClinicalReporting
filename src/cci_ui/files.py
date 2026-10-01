"""Saving a workflow's output in the folder the user chose (desktop only).

The tools' workflows return their workbook as bytes with a file name
(``clinical_reporting.workflow.OutputFile``, or anything else with ``name``
and ``data``); only the desktop window knows about folders. Plain file
writing, without Qt: the window runs it on its worker thread, right after
the workflow.
"""

from __future__ import annotations

import errno
from pathlib import Path
from typing import Protocol, Union


class SavableOutput(Protocol):
    """What :func:`save_output` writes: a file name and the file's bytes."""

    @property
    def name(self) -> str: ...

    @property
    def data(self) -> bytes: ...


def save_output(output: SavableOutput, folder: Union[str, Path]) -> Path:
    """Write *output* into *folder* and return the path written.

    Never replaces a file: a name that's taken gets a number, "name (2).xlsx".
    Only the file name part of ``output.name`` counts, so the file always lands
    in *folder*. Raises :class:`FileNotFoundError` if *folder* doesn't exist,
    and :class:`OSError` if the file can't be written (nothing is left behind).
    """
    folder = Path(folder)
    if not folder.is_dir():
        raise FileNotFoundError(
            errno.ENOENT, "the folder isn't there any more", str(folder)
        )
    name = Path(output.name).name
    stem, suffix = Path(name).stem, Path(name).suffix
    number = 1
    while True:
        path = folder / (name if number == 1 else f"{stem} ({number}){suffix}")
        try:
            file = open(path, "xb")  # Fails if the file exists, even if just made.
        except FileExistsError:
            number += 1
            continue
        try:
            with file:
                file.write(output.data)
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        return path


__all__ = ["SavableOutput", "save_output"]
