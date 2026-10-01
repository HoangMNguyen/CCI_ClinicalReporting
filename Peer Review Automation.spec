# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build recipe for Peer Review Automation.

The version is deliberately NOT part of this file's name. It comes from
``__version__`` in ``src/peer_review_automation/__init__.py``, or from the
``APP_VERSION`` environment variable for a one-off build::

    python -m PyInstaller "Peer Review Automation.spec"
    $env:APP_VERSION = "2.01"; python -m PyInstaller "Peer Review Automation.spec"
"""

import sys

# SPECPATH (the repository root) is injected by PyInstaller, and is where
# build_support.py lives.
sys.path.insert(0, SPECPATH)

from build_support import app_icon, package_version, ui_datas, version_resource

PACKAGE = "peer_review_automation"
PRODUCT = "Peer Review Automation"
DESCRIPTION = "Medidata SDS peer-review error report"

VERSION = package_version(PACKAGE)
EXE_NAME = f"{PRODUCT} V{VERSION}"

a = Analysis(
    ['src\\peer_review_automation\\__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=ui_datas(),
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
    icon=app_icon("peer-review-automation"),
)
