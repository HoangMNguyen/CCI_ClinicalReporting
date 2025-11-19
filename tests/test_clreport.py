import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if "numpy" not in sys.modules:
    numpy_stub = types.SimpleNamespace(datetime64=object)
    sys.modules["numpy"] = numpy_stub

from CLReport import CLReport


def test_set_common_item_state_moves_between_lists():
    report = CLReport()
    report.available_common_items = ["Subject", "Visit"]
    report.selected_common_items = []

    assert report.set_common_item_state("Subject", selected=True) is True
    assert "Subject" in report.get_selected_common_items()
    assert "Subject" not in report.get_available_common_items()

    # Re-selecting should be a no-op
    assert report.set_common_item_state("Subject", selected=True) is False

    # Moving back to available restores the entry
    assert report.set_common_item_state("Subject", selected=False) is True
    assert "Subject" in report.get_available_common_items()
    assert "Subject" not in report.get_selected_common_items()


def test_move_between_lists_handles_missing_item_gracefully():
    report = CLReport()
    report.available_common_items = []
    report.selected_common_items = []

    # Moving a non-existent item simply adds it to the target list
    assert report.set_common_item_state("New", selected=True) is True
    assert report.get_selected_common_items() == ["New"]

    # Removing it again returns it to availability
    assert report.set_common_item_state("New", selected=False) is True
    assert report.get_available_common_items() == ["New"]
