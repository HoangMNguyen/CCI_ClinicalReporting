"""CCI Automation: Enrollment Log, DSMB Report, Clockify, and format tools.

Headless report builders live in the ``enrollment_log``, ``dsmb``,
``clockify``, and ``format_tools`` subpackages, with shared helpers in
:mod:`cci_automation.util`; the PySide6 GUI is :mod:`cci_automation.app`.
Corelisting loading and Excel styling come from the ``clinical_reporting``
backend. Importing this package does not import Qt.
"""

# Single source of truth for the release version. ``build_support.py`` reads
# this string when building the executable, so bumping a release means editing
# it here and nowhere else.
__version__ = "1.23"
