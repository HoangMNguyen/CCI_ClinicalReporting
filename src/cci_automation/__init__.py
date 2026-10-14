"""CCI Automation: Enrollment Log, DSMB Report, and format tools.

Each workflow is a plain ``run()`` that returns the workbook: in
``enrollment_log.EnrollmentLog``, ``dsmb.DSMB`` and
``format_tools.change_type``, with shared helpers in
:mod:`cci_automation.util`. The window, built on the ``cci_ui`` design
system, is :mod:`cci_automation.app`. Corelisting loading and Excel styling
come from the ``clinical_reporting`` backend. Importing this package does not
import Qt.
"""

# Single source of truth for the release version. ``build_support.py`` reads
# this string when building the executable, so bumping a release means editing
# it here and nowhere else.
__version__ = "1.29"
