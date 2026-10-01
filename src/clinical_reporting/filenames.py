"""File names built from user-typed text.

Every name the tools write (exports, saved settings) goes through here, so a
typed name can never point outside the chosen folder, whether the file is
written to a local folder today or to server storage later.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

# Characters Windows forbids in file names, including both path separators.
_UNSAFE_FILE_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_file_stem(text: str) -> str:
    """Return *text* with characters not allowed in file names replaced by ``_``."""
    return _UNSAFE_FILE_NAME_CHARS.sub("_", text or "").strip()


def output_file_name(
    base_name: str, *, now: Optional[datetime] = None, extension: str = ".xlsx"
) -> str:
    """Return the export file name ``"<base> YYMMDD_HHMMSS.xlsx"``.

    A trailing *extension* typed by the user is dropped before the timestamp
    is added, and an empty base leaves just the timestamp.
    """
    stamp = (now or datetime.now()).strftime("%y%m%d_%H%M%S")
    base = safe_file_stem(base_name)
    if base.lower().endswith(extension.lower()):
        base = base[: -len(extension)].rstrip()
    return f"{base} {stamp}{extension}" if base else f"{stamp}{extension}"


__all__ = ["output_file_name", "safe_file_stem"]
