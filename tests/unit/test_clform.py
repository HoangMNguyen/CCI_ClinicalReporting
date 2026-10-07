from clinical_reporting.models import CLForm


def test_get_name():
    form = CLForm("Original")
    assert form.get_name() == "Original"


def test_form_item_state_and_queries():
    form = CLForm("Test")

    assert form.set_form_item_state("AGE", selected=True) is True
    assert form.get_selected_form_items() == ["AGE"]
    assert form.get_available_form_items() == []

    # Moving back to available removes it from selected
    assert form.set_form_item_state("AGE", selected=False) is True
    assert form.get_available_form_items() == ["AGE"]
    assert form.get_selected_form_items() == []

    # Removing clears the item from both collections
    assert form.remove_form_item("AGE") is True
    assert form.get_available_form_items() == []
    assert form.get_selected_form_items() == []


def test_move_item_helper_is_idempotent():
    form = CLForm("Test")

    form.available_form_items = ["HEIGHT"]
    assert form.set_form_item_state("HEIGHT", selected=True) is True
    assert form.get_selected_form_items() == ["HEIGHT"]
    assert form.get_available_form_items() == []

    # Re-adding the same item is a no-op
    assert form.set_form_item_state("HEIGHT", selected=True) is False


def test_join_items_accessors():
    form = CLForm("DM")
    form.set_join_items(["Subject", "Visit"])
    assert form.get_join_items() == ["Subject", "Visit"]


def test_join_order_and_how_accessors():
    form = CLForm("VS")

    form.set_join_order(2)
    assert form.get_join_order() == 2

    form.set_join_how("Inner join")
    assert form.get_join_how() == "Inner join"
