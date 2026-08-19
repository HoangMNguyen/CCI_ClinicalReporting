"""Shared build helpers for the PyInstaller spec files at the repository root.

A ``.spec`` file is a Python script that PyInstaller executes, so every spec
imports this module instead of hard-coding a release number. The version is
resolved once, here, and used for both the executable's file name and the
Windows VERSIONINFO resource (Properties -> Details).

Resolution order:

1. The ``APP_VERSION`` environment variable, for one-off or CI builds.
2. ``__version__`` in the application package's ``__init__.py`` (the default).

Cutting a release therefore means editing one string in one ``__init__.py``;
the spec files themselves never change and are never duplicated per version.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from PyInstaller.utils.win32 import versioninfo

SRC = Path(__file__).resolve().parent / "src"

# Stamped into every executable this repository builds. Set this to the legal
# entity name if these binaries are ever distributed outside the department.
COMPANY_NAME = "CCI"

_VERSION_RE = re.compile(r"^__version__\s*=\s*[\"']([^\"']+)[\"']", re.MULTILINE)


def package_version(package: str) -> str:
    """Return the release version for ``package``.

    ``APP_VERSION`` wins when set; otherwise ``__version__`` is read out of
    ``src/<package>/__init__.py`` as plain text. The file is parsed rather
    than imported so that resolving a version number never drags pandas or
    PySide6 into the build process.
    """
    override = os.environ.get("APP_VERSION", "").strip()
    if override:
        return override.lstrip("vV")

    init = SRC / package / "__init__.py"
    match = _VERSION_RE.search(init.read_text(encoding="utf-8"))
    if match is None:
        raise SystemExit(f"build_support: no __version__ found in {init}")
    return match.group(1)


def _version_tuple(version: str) -> tuple[int, int, int, int]:
    """Coerce a dotted version into the four integers Windows requires.

    ``"2.01"`` becomes ``(2, 1, 0, 0)`` and ``"1.10.2"`` becomes
    ``(1, 10, 2, 0)``. Any non-numeric suffix (``"2.01-beta"``) is dropped
    from the numeric resource; the original string is still shown verbatim as
    FileVersion/ProductVersion.
    """
    parts: list[int] = []
    for chunk in version.split(".")[:4]:
        digits = re.match(r"\d+", chunk)
        parts.append(int(digits.group()) if digits else 0)
    parts.extend([0] * (4 - len(parts)))
    return parts[0], parts[1], parts[2], parts[3]


def version_resource(
    version: str,
    product_name: str,
    description: str,
    exe_name: str,
) -> versioninfo.VSVersionInfo:
    """Build the VERSIONINFO resource shown in the file's Details tab.

    Passing the returned object straight to ``EXE(version=...)`` keeps the
    embedded metadata in lockstep with the file name, so a build can never
    ship an executable whose reported version disagrees with its title.
    """
    numbers = _version_tuple(version)
    strings = [
        versioninfo.StringStruct("CompanyName", COMPANY_NAME),
        versioninfo.StringStruct("FileDescription", description),
        versioninfo.StringStruct("FileVersion", version),
        versioninfo.StringStruct("InternalName", exe_name),
        versioninfo.StringStruct("OriginalFilename", f"{exe_name}.exe"),
        versioninfo.StringStruct("ProductName", product_name),
        versioninfo.StringStruct("ProductVersion", version),
    ]
    return versioninfo.VSVersionInfo(
        ffi=versioninfo.FixedFileInfo(filevers=numbers, prodvers=numbers),
        kids=[
            # "040904B0" is U.S. English + Unicode, matching the Translation
            # pair below; the two must agree or Explorer shows no details.
            versioninfo.StringFileInfo([versioninfo.StringTable("040904B0", strings)]),
            versioninfo.VarFileInfo(
                [versioninfo.VarStruct("Translation", [0x0409, 1200])]
            ),
        ],
    )
