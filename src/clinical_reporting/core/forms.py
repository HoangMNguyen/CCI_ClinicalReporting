from copy import deepcopy
from typing import List, Optional


class CLForm:
    """A class to represent a form that contains multiple columns and can be joined with others."""

    def __init__(self, name: str):
        self.name = name  # Fixed: Initialize with the given name instead of None
        self.available_form_items: List[str] = []
        self.selected_form_items: List[str] = []
        self.join_items: List[str] = []
        self.join_order = None  # order of form to join
        self.join_how = None

    def _move_item(
        self,
        source: Optional[List[str]],
        target: Optional[List[str]],
        item: str,
    ) -> bool:
        """Move ``item`` between collections while keeping them mutually exclusive.

        The helper removes ``item`` from ``source`` (if provided) and adds it to ``target``
        (if provided) only when it is not already present there. This centralises the
        transfer-and-deduplicate behaviour for form and join items so callers do not
        need to manually juggle both lists.

        Returns ``True`` when any collection changed.
        """

        changed = False
        if source is not None and item in source:
            source.remove(item)
            changed = True

        if target is not None and item not in target:
            target.append(item)
            changed = True

        return changed

    def get_name(self):
        """Get the name of the form."""
        return self.name

    def set_name(self, name: str):
        """Set the name of the form."""
        self.name = name

    def get_selected_form_items(self):
        """Get the list of selected form items."""
        return self.selected_form_items

    def set_form_item_state(self, item: str, *, selected: bool) -> bool:
        """Ensure ``item`` appears only in the selected or available form items list."""

        source, target = (
            (self.available_form_items, self.selected_form_items)
            if selected
            else (self.selected_form_items, self.available_form_items)
        )
        return self._move_item(source, target, item)

    def get_available_form_items(self):
        """Get the list of available form items."""
        return self.available_form_items

    def remove_form_item(self, item: str) -> bool:
        """Remove ``item`` from both selected and available collections, if present."""

        removed_selected = self._move_item(self.selected_form_items, None, item)
        removed_available = self._move_item(self.available_form_items, None, item)
        return removed_selected or removed_available

    def set_join_how(self, how: str):
        """Set the join method for the form."""
        self.join_how = how

    def get_join_how(self):
        """Get the join method for the form."""
        return self.join_how

    def set_join_item_state(self, item: str, *, include: bool) -> bool:
        """Add or remove a join item while preventing duplicates."""

        if include:
            return self._move_item(None, self.join_items, item)
        return self._move_item(self.join_items, None, item)

    def clear_join_items(self):
        """Clear the join items list."""
        self.join_items = []

    def get_join_items(self):
        """Get the list of join items."""
        return self.join_items

    def set_join_items(self, items: list):
        """Set the join items list."""
        self.join_items = deepcopy(items)

    def set_join_order(self, order: int):
        """Set the order of the form to join."""
        self.join_order = order

    def get_join_order(self):
        """Get the order of the form to join."""
        return self.join_order

    def remove_join_order(self):
        """Remove the join order."""
        self.join_order = None
