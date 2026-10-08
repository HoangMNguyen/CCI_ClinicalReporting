"""Status messages tagged by kind (clinical_reporting.feedback)."""

import pickle

import pytest

from clinical_reporting import feedback


def test_a_message_is_a_string_with_a_kind_and_details():
    message = feedback.error("Could not read x.zip", "Traceback ...")

    assert message == "Could not read x.zip" and message.kind == "error"
    assert message.details == "Traceback ..."


def test_unknown_kinds_are_rejected():
    with pytest.raises(ValueError):
        feedback.Message("text", kind="fatal")


def test_message_survives_pickling():
    restored = pickle.loads(pickle.dumps(feedback.warning("Missing forms: AE")))

    assert restored == "Missing forms: AE"
    assert restored.kind == "warning"


def test_one_line_drops_line_breaks_and_bullets():
    assert feedback.one_line("Cannot run:\n- A.\n\n  - B.") == "Cannot run: A. B."
    assert feedback.one_line("Saved") == "Saved"
    assert feedback.one_line("Could not read x: bad zip\nNothing was loaded.") == (
        "Could not read x: bad zip. Nothing was loaded."
    )


def test_short_list_names_a_few_and_counts_the_rest():
    assert feedback.short_list(["a.csv", "b.csv"]) == "a.csv, b.csv"
    assert feedback.short_list([f"f{n}" for n in range(8)], shown=3) == (
        "f0, f1, f2 and 5 more"
    )


def test_and_list_joins_names_into_a_sentence():
    assert feedback.and_list([]) == ""
    assert feedback.and_list(["SV"]) == "SV"
    assert feedback.and_list(["SV", "DS"]) == "SV and DS"
    assert feedback.and_list(iter(["SV", "DS", "LB"])) == "SV, DS and LB"
