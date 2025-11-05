import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from CLForm import CLForm


def test_set_form_item_state_enforces_mutual_exclusivity():
    form = CLForm("Test")

    # Start by making the item available
    changed = form.set_form_item_state("ItemA", selected=False)
    assert changed is True
    assert form.get_available_form_items() == ["ItemA"]
    assert form.get_selected_form_items() == []

    # Move the item to the selected collection and ensure it disappears from available
    changed = form.set_form_item_state("ItemA", selected=True)
    assert changed is True
    assert form.get_selected_form_items() == ["ItemA"]
    assert form.get_available_form_items() == []

    # Calling again should be a no-op and keep lists exclusive
    changed = form.set_form_item_state("ItemA", selected=True)
    assert changed is False
    assert form.get_selected_form_items() == ["ItemA"]
    assert form.get_available_form_items() == []


def test_set_join_item_state_prevents_duplicates():
    form = CLForm("Test")

    assert form.set_join_item_state("Subject", include=True) is True
    assert form.get_join_items() == ["Subject"]

    # Re-adding should not duplicate the entry
    assert form.set_join_item_state("Subject", include=True) is False
    assert form.get_join_items() == ["Subject"]

    # Removing works and subsequent removal is a no-op
    assert form.set_join_item_state("Subject", include=False) is True
    assert form.get_join_items() == []
    assert form.set_join_item_state("Subject", include=False) is False
