"""Safety Automation: Corelisting AE & DLT report for the Safety Department.

The headless report builder lives in
:mod:`safety_automation.ae_corelisting.AECoreListing`; the PySide6 GUI is
:mod:`safety_automation.app`. Corelisting loading comes from the
``clinical_reporting`` backend. Importing this package does not import Qt.
"""

# Single source of truth for the release version. ``build_support.py`` reads
# this string when building the executable, so bumping a release means editing
# it here and nowhere else.
__version__ = "1.07"
