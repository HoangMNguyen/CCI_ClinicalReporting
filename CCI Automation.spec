# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build recipe for CCI Automation.

The version is deliberately NOT part of this file's name. It comes from
``__version__`` in ``src/cci_automation/__init__.py``, or from the
``APP_VERSION`` environment variable for a one-off build::

    python -m PyInstaller "CCI Automation.spec"
    $env:APP_VERSION = "2.01"; python -m PyInstaller "CCI Automation.spec"

Clockify credentials come from the ``CCI_CLOCKIFY_API_KEY`` and
``CCI_CLOCKIFY_WORKSPACE_ID`` environment variables at run time. A local
git-ignored ``src/cci_automation/clockify.json`` is bundled only if present,
as a fallback for machines where the variables are not set.
"""

import sys
from pathlib import Path

# SPECPATH (the repository root) is injected by PyInstaller, and is where
# build_support.py lives.
sys.path.insert(0, SPECPATH)

from build_support import package_version, version_resource

PACKAGE = "cci_automation"
PRODUCT = "CCI Automation"
DESCRIPTION = "Enrollment Logs, DSMB Reports, Clockify dashboards, formatting fixes"

VERSION = package_version(PACKAGE)
EXE_NAME = f"{PRODUCT} V{VERSION}"

_clockify_json = Path(SPECPATH) / "src" / "cci_automation" / "clockify.json"
_datas = [(str(_clockify_json), "cci_automation")] if _clockify_json.exists() else []

a = Analysis(
    ['src\\cci_automation\\__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=_datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'matplotlib'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=EXE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=version_resource(VERSION, PRODUCT, DESCRIPTION, EXE_NAME),
)
