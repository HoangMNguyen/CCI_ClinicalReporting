"""Peer Review Automation: validates Medidata SDS workbooks.

The review is :func:`peer_review_automation.sds.run`, a plain function that
returns the findings workbook; the window, built on the ``cci_ui`` design
system, is :mod:`peer_review_automation.app`. Importing this package does not
import Qt.
"""

# Single source of truth for the release version. ``build_support.py`` reads
# this string when building the executable, so bumping a release means editing
# it here and nowhere else.
__version__ = "1.04"
