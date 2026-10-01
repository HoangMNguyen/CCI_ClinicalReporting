"""Peer Review Automation: validates Medidata SDS workbooks.

The headless review logic lives in :mod:`peer_review_automation.sds`; the
PySide6 GUI in :mod:`peer_review_automation.app`. Importing this package does
not import Qt.
"""

# Single source of truth for the release version. ``build_support.py`` reads
# this string when building the executable, so bumping a release means editing
# it here and nowhere else.
__version__ = "1.11"
