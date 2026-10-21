"""File names built from user-typed text.

Every name the tools write (exports, saved settings) goes through here, so a
typed name can never point outside the folder it is written to.
"""

from __future__ import annotations

import ntpath
import re
from datetime import datetime
from typing import Optional

# Characters Windows forbids in file names, including both path separators.
_UNSAFE_FILE_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_file_stem(text: str) -> str:
    """Return *text* with characters not allowed in file names replaced by ``_``."""
    return _UNSAFE_FILE_NAME_CHARS.sub("_", text or "").strip()


def output_base_name(text: str, *, extension: str = ".xlsx") -> str:
    """Return the export name in *text*, without the date and time or the extension.

    It is :func:`safe_file_stem` of *text* with a trailing *extension* typed by
    the user dropped; "" when nothing is left (a blank name, or just the
    extension).
    """
    base = safe_file_stem(text)
    if extension and base.lower().endswith(extension.lower()):
        base = base[: -len(extension)].rstrip()
    return base


def output_file_name(
    base_name: str,
    *,
    now: Optional[datetime] = None,
    extension: str = ".xlsx",
    add_date_time: bool = True,
) -> str:
    """Return the export file name ``"<base> YYMMDD_HHMMSS.xlsx"``.

    The base is :func:`output_base_name` of *base_name*. Without
    *add_date_time* the name is ``"<base>.xlsx"``, with ``_`` after a Windows
    device name such as ``CON`` or ``NUL``, which can't name a file. An empty
    base leaves just the timestamp either way, so a name is never only the
    extension.
    """
    base = output_base_name(base_name, extension=extension)
    if base and not add_date_time:
        if ntpath.isreserved(f"{base}{extension}"):
            # Windows reads the part before the first "." as the device name.
            head, dot, rest = base.partition(".")
            base = f"{head}_{dot}{rest}"
        return f"{base}{extension}"
    stamp = (now or datetime.now()).strftime("%y%m%d_%H%M%S")
    return f"{base} {stamp}{extension}" if base else f"{stamp}{extension}"


__all__ = ["output_base_name", "output_file_name", "safe_file_stem"]
