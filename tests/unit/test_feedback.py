"""Status messages tagged by kind (clinical_reporting.feedback)."""

from clinical_reporting import feedback


def test_a_message_is_a_string_with_a_kind_and_details():
    message = feedback.error("Could not read x.zip", "Traceback ...")

    assert message == "Could not read x.zip" and message.kind == "error"
    assert message.details == "Traceback ..."
    assert feedback.kind_of("plain text") == "info"


def test_one_line_drops_line_breaks_and_bullets():
    assert feedback.one_line("Cannot run:\n- A.\n\n  - B.") == "Cannot run: A. B."
    assert feedback.one_line("Saved") == "Saved"
    assert feedback.one_line("Could not read x: bad zip\nNothing was loaded.") == (
        "Could not read x: bad zip. Nothing was loaded."
    )
