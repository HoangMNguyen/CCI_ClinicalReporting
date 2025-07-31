from copy import deepcopy


class CLForm:
    """A class to represent a form that contains multiple columns and can be joined with others."""

    def __init__(self, name: str):
        self.name = name  # Fixed: Initialize with the given name instead of None
        self.available_form_items = []
        self.selected_form_items = []
        self.join_items = []
        self.join_order = None  # order of form to join
        self.join_how = None

    def get_name(self):
        """Get the name of the form."""
        return self.name

    def set_name(self, name: str):
        """Set the name of the form."""
        self.name = name

    def get_selected_form_items(self):
        """Get the list of selected form items."""
        return self.selected_form_items

    def add_selected_form_item(self, item: str):
        """Add an item to the selected form items list."""
        if item not in self.selected_form_items:
            self.selected_form_items.append(item)
            self.remove_available_form_item(item)

    def remove_selected_form_item(self, item: str):
        """Remove an item from the selected form items list."""
        if item in self.selected_form_items:
            self.selected_form_items.remove(item)

    def get_available_form_items(self):
        """Get the list of available form items."""
        return self.available_form_items

    def add_available_form_item(self, item: str):
        """Add an item to the available form items list."""
        if item not in self.available_form_items:
            self.available_form_items.append(item)
            self.remove_selected_form_item(item)

    def remove_available_form_item(self, item: str):
        """Remove an item from the available form items list."""
        if item in self.available_form_items:
            self.available_form_items.remove(item)

    def set_join_how(self, how: str):
        """Set the join method for the form."""
        self.join_how = how

    def get_join_how(self):
        """Get the join method for the form."""
        return self.join_how

    def add_join_item(self, item: str):
        """Add an item to the join items list."""
        if item not in self.join_items:
            self.join_items.append(item)

    def remove_join_item(self, item: str):
        """Remove an item from the join items list."""
        if item in self.join_items:
            self.join_items.remove(item)

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
