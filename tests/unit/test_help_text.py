"""The help beside each step has the same three sections, in the same order."""

import re

from clinical_reporting import help_text, steps

SECTIONS = ["What this step is for", "Step by step", "Good to know"]


def _headings(markdown):
    return re.findall(r"^#+ (.+)$", markdown, flags=re.MULTILINE)


def test_every_step_has_only_the_three_help_sections_in_order():
    headings = {key: _headings(help_text.help_markdown(key)) for key in steps.STEP_KEYS}

    assert headings == {key: SECTIONS for key in steps.STEP_KEYS}
