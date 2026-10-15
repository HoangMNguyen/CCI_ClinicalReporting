"""The help beside each step has the same sections, in the same order."""

import re

from clinical_reporting import help_text, steps

STEP_SECTIONS = [
    "What this step is for",
    "Before you start",
    "Step by step",
    "Words used here",
    "Good to know",
]
OVERVIEW_SECTIONS = [
    "How a report is made",
    "Red fields",
    "The sidebar badges",
    "Keyboard shortcuts",
    "Display settings",
]


def _headings(markdown):
    return re.findall(r"^## (.+)$", markdown, flags=re.MULTILINE)


def test_every_step_has_its_help_sections_in_order():
    headings = {key: _headings(help_text.help_markdown(key)) for key in steps.STEP_KEYS}

    assert headings[steps.SOURCE] == OVERVIEW_SECTIONS + STEP_SECTIONS
    assert {key: found for key, found in headings.items() if key != steps.SOURCE} == {
        key: STEP_SECTIONS for key in steps.STEP_KEYS if key != steps.SOURCE
    }


def test_the_overview_lists_the_steps_in_sidebar_order():
    overview = help_text.help_markdown(steps.SOURCE)
    listed = re.findall(r"^\d+\. \*\*(.+?)\*\*", overview, flags=re.MULTILINE)

    assert listed[: len(steps.STEP_KEYS)] == [
        steps.TITLES[key] for key in steps.STEP_KEYS
    ]
