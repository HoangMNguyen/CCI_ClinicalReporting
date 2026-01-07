from copy import deepcopy
import json
from typing import Any, Dict, List, Optional

import numpy as np

from clinical_reporting.core.forms import CLForm


class CLReport:
    """A class to represent a report that contains multiple forms and columns."""

    def __init__(self):
        self.study_name = None
        self.data = {}
        self.available_forms = {}
        self.selected_forms = {}
        self.available_common_items = []
        self.selected_common_items = []
        self.new_items = []
        self.order_list = []
        self.rename_dict = {}
        self.file_path = None
        self.static_available_common_items = []  # Initialize as empty, will be populated dynamically
        self.static_filter_items = []  # Static filter items: Item Name, Operator, Value
        self.dynamic_filter_items = []  # Dynamic filter items: Item Name 1 , Operator, Item Name 2
        self.selected_items_order_list = []

    @staticmethod
    def _move_between_lists(
        item: str,
        source: Optional[List[str]],
        target: Optional[List[str]],
    ) -> bool:
        """Move ``item`` between ``source`` and ``target`` while avoiding duplicates."""

        changed = False
        if source is not None and item in source:
            source.remove(item)
            changed = True

        if target is not None and item not in target:
            target.append(item)
            changed = True

        return changed

    def set_study_name(self, study_name: str):
        """Set the study name for the report."""
        self.study_name = study_name

    def identify_common_items(self):
        """Identify columns that exist in all forms of the data."""
        if not self.data:
            return

        # Get all forms
        forms = list(self.data.keys())
        if not forms:
            return

        # Start with all columns from the first form
        common_columns = set(self.data[forms[0]].columns)

        # Find intersection with all other forms
        for form in forms[1:]:
            form_columns = set(self.data[form].columns)
            common_columns = common_columns.intersection(form_columns)

        # Update static_available_common_items with the common columns
        self.static_available_common_items = sorted(list(common_columns))

        if "Subject" in self.static_available_common_items:
            # Move "Subject" to the front of the list
            self.set_common_item_state("Subject", selected=True)

    def set_data(self, data: dict):
        """Set the data for the report."""
        self.data = data

        # Identify common columns across all forms
        self.identify_common_items()

        # by default, all forms are available.
        # for each form in data, create a CLForm object
        self.add_all_available_forms()

        # by default, all common items are available.
        self.add_all_available_common_items()

    def get_data(self):
        """Get the data for the report."""
        return self.data

    def add_available_form(self, form: str):
        """Add the available form to the available forms dictionary."""
        self.available_forms[form] = CLForm(form)
        self.remove_selected_form(form)

    def add_all_available_forms(self):
        """Add all available forms from the data to the available forms dictionary."""
        for form_name in self.data.keys():
            self.add_available_form(form_name)
            # remove all selected forms
            self.remove_all_selected_forms()

    def remove_available_form(self, form: str):
        """Remove the available form from the available forms dictionary."""
        if form in self.available_forms:
            del self.available_forms[form]

    def remove_all_available_forms(self):
        """Remove all available forms from the available forms dictionary."""
        self.available_forms = {}

    def get_available_forms_list(self):
        """Get the list of available forms."""
        return list(self.available_forms.keys())

    def add_selected_form(self, form: str):
        """Add the selected form to the selected forms dict."""
        # add the form from data to the selected forms dict
        if form in self.data:
            self.selected_forms[form] = CLForm(form)
            # add items from data to the selected form, excluding the items in static_available_common_items
            for item in self.data[form].columns:
                if item not in self.static_available_common_items:
                    self.selected_forms[form].set_form_item_state(item, selected=False)
                    # print(f"Adding item {item} to selected form {form}")
            if form in self.available_forms:
                # remove the form from available forms
                del self.available_forms[form]

    def add_all_selected_forms(self):
        """Add all available forms to the selected forms dict."""
        for form_name in self.data.keys():
            self.add_selected_form(form_name)

    def remove_selected_form(self, form: str):
        """Remove the selected form from the selected forms dict."""
        if form in self.selected_forms:
            del self.selected_forms[form]

    def remove_all_selected_forms(self):
        """Remove all selected forms from the selected forms dict."""
        self.selected_forms = {}

    def get_selected_forms_list(self):
        """Get the list of selected forms."""
        return list(self.selected_forms.keys())

    def add_all_available_common_items(self):
        """Add all static available common items to the available common items list."""
        for item in self.static_available_common_items:
            self.set_common_item_state(item, selected=False)

    def remove_all_available_common_items(self):
        """Remove all available common items from the available common items list."""
        self.available_common_items = []

    def get_available_common_items(self):
        """Get the list of available common items."""
        return self.available_common_items

    def set_common_item_state(self, item: str, *, selected: bool) -> bool:
        """Ensure ``item`` only exists in one of the common item collections."""

        source, target = (
            (self.available_common_items, self.selected_common_items)
            if selected
            else (self.selected_common_items, self.available_common_items)
        )
        return self._move_between_lists(item, source, target)

    def get_selected_common_items(self):
        """Get the list of selected common items."""
        return self.selected_common_items

    def set_order_list(self, order_list: list):
        """Set the order list for the report."""
        self.order_list = order_list

    def get_order_list(self):
        """Get the order list for the report."""
        return self.order_list

    def get_rename_dict(self):
        """Get the rename dictionary for the report."""
        return self.rename_dict

    def set_rename_dict(self, rename_dict: dict):
        """Set the rename dictionary for the report."""
        self.rename_dict = rename_dict

    def set_rename_item(self, original_name: str, new_name: str) -> None:
        """Set or update a single rename mapping.

        If ``new_name`` is falsy or identical to ``original_name``, the mapping
        is removed to avoid no-op entries.
        """
        if not new_name or new_name == original_name:
            self.rename_dict.pop(original_name, None)
            return
        self.rename_dict[original_name] = new_name

    def remove_rename_item(self, original_name: str) -> None:
        """Remove a single rename mapping if it exists."""
        self.rename_dict.pop(original_name, None)

    def set_file_path(self, file_path: str):
        """Set the file path for the report."""
        self.file_path = file_path

    def get_selected_items_order_list(self):
        """Get the ordered list of selected items."""
        return self.selected_items_order_list

    def set_selected_items_order_list(self, order_list: list):
        """Set the ordered list of selected items."""
        self.selected_items_order_list = order_list

    def update_selected_items_order_list(self):
        """Update the selected items order list with all currently selected items."""
        # Create a new list that will contain all selected items
        all_selected_items = []

        # Add all selected common items
        all_selected_items.extend(self.selected_common_items)

        # Add all selected form items with form name prefix
        for form_name in self.selected_forms:
            form = self.selected_forms[form_name]
            for item in form.get_selected_form_items():
                all_selected_items.append(f"{form_name}.{item}")

        # Keep existing order for items that are still selected
        new_order_list = []

        # First add items that are in both the current order list and the all_selected_items
        for item in self.selected_items_order_list:
            if item in all_selected_items:
                new_order_list.append(item)
                all_selected_items.remove(item)

        # Then add any new items that weren't in the order list before
        new_order_list.extend(all_selected_items)

        # Update the order list
        self.selected_items_order_list = new_order_list

        return self.selected_items_order_list

    @staticmethod
    def _serialize_form(form: CLForm) -> Dict[str, Any]:
        """Convert a CLForm instance into a JSON-serializable dictionary."""

        return {
            "name": form.get_name(),
            "available_form_items": deepcopy(form.get_available_form_items()),
            "selected_form_items": deepcopy(form.get_selected_form_items()),
            "join_items": deepcopy(form.get_join_items()),
            "join_order": form.get_join_order(),
            "join_how": form.get_join_how(),
        }

    @staticmethod
    def _deserialize_form(form_name: str, data: Dict[str, Any]) -> CLForm:
        """Recreate a CLForm instance from persisted data."""

        form = CLForm(data.get("name", form_name))
        form.available_form_items = deepcopy(data.get("available_form_items", []))
        form.selected_form_items = deepcopy(data.get("selected_form_items", []))
        form.join_items = deepcopy(data.get("join_items", []))
        form.join_order = data.get("join_order")
        form.join_how = data.get("join_how")
        return form

    def save_setting_to_json(self, file_path: str, setting_name: Optional[str] = None):
        """Save the report settings to a JSON file.

        Only persist selected forms/items and user-configured settings. Do not
        persist available items or unselected forms since those are derived from
        the current input data and can be reconstructed when loading.
        """

        # Serialize only selected forms with their selected items and join config
        selected_forms_payload = {}
        for name, form in self.selected_forms.items():
            selected_forms_payload[name] = {
                "name": form.get_name(),
                # Only the items the user selected
                "selected_form_items": deepcopy(form.get_selected_form_items()),
                # Join configuration
                "join_items": deepcopy(form.get_join_items()),
                "join_order": form.get_join_order(),
                "join_how": form.get_join_how(),
            }

        settings = {
            "study_name": self.study_name,
            "setting_name": setting_name,
            # Only selected forms; available/unselected forms are omitted
            "selected_forms": selected_forms_payload,
            # Only the selected common items; available/common pools are omitted
            "selected_common_items": deepcopy(self.selected_common_items),
            # User-configured settings
            "new_items": deepcopy(self.new_items),
            "order_list": deepcopy(self.order_list),
            "rename_dict": deepcopy(self.rename_dict),
            "static_filter_items": [list(item) for item in self.static_filter_items],
            "dynamic_filter_items": [list(item) for item in self.dynamic_filter_items],
            "selected_items_order_list": deepcopy(self.selected_items_order_list),
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)

    def load_setting_from_json(self, file_path: str) -> Dict[str, Any]:
        """Load the report settings from a JSON file."""

        with open(file_path, "r", encoding="utf-8") as f:
            settings = json.load(f)

        self.study_name = settings.get("study_name", self.study_name)

        # Only selected forms are persisted; available forms are reconstructed later
        selected_forms_data = settings.get("selected_forms", {})
        self.selected_forms = {
            name: self._deserialize_form(name, form_data) for name, form_data in selected_forms_data.items()
        }

        # Only selected common items are persisted; available/common pools are reconstructed later
        self.selected_common_items = list(settings.get("selected_common_items", []))
        self.new_items = list(settings.get("new_items", []))
        self.order_list = list(settings.get("order_list", []))
        self.rename_dict = dict(settings.get("rename_dict", {}))

        static_filters = settings.get("static_filter_items")
        if static_filters is not None:
            self.static_filter_items = [tuple(item) for item in static_filters]
        else:
            self.static_filter_items = []

        dynamic_filters = settings.get("dynamic_filter_items")
        if dynamic_filters is not None:
            self.dynamic_filter_items = [tuple(item) for item in dynamic_filters]
        else:
            self.dynamic_filter_items = []

        selected_items_order_list = settings.get("selected_items_order_list")
        if selected_items_order_list is not None:
            self.selected_items_order_list = list(selected_items_order_list)
        else:
            self.update_selected_items_order_list()

        return settings

    def reconcile_with_current_data(self) -> Dict[str, list[str]]:
        """Align loaded settings with the currently available study data."""

        missing_forms: set[str] = set()
        missing_items: set[str] = set()

        data_forms = set(self.data.keys())

        # Determine the true common items from the loaded data.
        actual_common_items: set[str] = set()
        if self.data:
            iter_forms = iter(self.data.values())
            first_form = next(iter_forms, None)
            if first_form is not None:
                actual_common_items = set(first_form.columns)
                for form_df in iter_forms:
                    actual_common_items &= set(form_df.columns)

        self.static_available_common_items = sorted(actual_common_items)

        self.available_common_items = sorted(actual_common_items)
        for item in list(self.selected_common_items):
            if item not in self.available_common_items:
                self.selected_common_items.remove(item)
                missing_items.add(item)

        self.available_common_items = [
            item for item in self.available_common_items if item not in self.selected_common_items
        ]

        valid_selected_forms: dict[str, CLForm] = {}
        for form_name, form in list(self.selected_forms.items()):
            if form_name not in data_forms:
                missing_forms.add(form_name)
                continue

            form_columns = set(self.data[form_name].columns)

            form.available_form_items = sorted(column for column in form_columns if column not in actual_common_items)

            for item in list(form.get_selected_form_items()):
                if item not in form.available_form_items:
                    form.remove_form_item(item)
                    missing_items.add(f"{form_name}.{item}")

            selected_items = set(form.get_selected_form_items())
            form.available_form_items = [column for column in form.available_form_items if column not in selected_items]
            valid_selected_forms[form_name] = form

        self.selected_forms = valid_selected_forms

        valid_selected_form_names = set(self.selected_forms.keys())
        self.available_forms = {}
        for form_name in sorted(data_forms - valid_selected_form_names):
            new_form = CLForm(form_name)
            form_columns = set(self.data[form_name].columns)
            new_form.available_form_items = sorted(
                column for column in form_columns if column not in actual_common_items
            )
            self.available_forms[form_name] = new_form

        # Build a set of valid identifiers for filters and ordering.
        valid_identifiers: set[str] = set(self.selected_common_items)
        for form_name, form in self.selected_forms.items():
            for item in form.get_selected_form_items():
                valid_identifiers.add(item)
                valid_identifiers.add(f"{form_name}.{item}")

        self.order_list = [item for item in self.order_list if item in valid_identifiers]
        self.selected_items_order_list = [item for item in self.selected_items_order_list if item in valid_identifiers]
        self.rename_dict = {key: value for key, value in self.rename_dict.items() if key in valid_identifiers}

        self.static_filter_items = [item for item in self.static_filter_items if item and item[0] in valid_identifiers]
        self.dynamic_filter_items = [
            item
            for item in self.dynamic_filter_items
            if item and item[0] in valid_identifiers and item[2] in valid_identifiers
        ]

        return {
            "forms": sorted(missing_forms),
            "items": sorted(missing_items),
        }

    def get_join_list(self):
        """Get the list of join items."""
        join_list = []
        for form in self.selected_forms.keys():
            join_list.extend(
                [
                    self.selected_forms[form].get_name(),
                    self.selected_forms[form].get_join_items(),
                    self.selected_forms[form].get_join_order(),
                    self.selected_forms[form].get_join_how(),
                ]
            )

        return join_list

    def get_join_list_dict(self) -> Dict[str, Dict[str, Any]]:
        """Return the join configuration keyed by form name.

        The refactored join UI works with dictionaries so that it can look up
        a specific form's existing join items, order, and join strategy when
        populating table widgets.  The original implementation only exposed a
        flattened list; this helper simply repackages the same information in a
        structure that is easier for the UI to consume while keeping behaviour
        identical to the previous widget.
        """

        join_data: Dict[str, Dict[str, Any]] = {}
        for form_name, form in self.selected_forms.items():
            join_data[form_name] = {
                "items": list(form.get_join_items()),
                "order": form.get_join_order(),
                "how": form.get_join_how(),
            }
        return join_data

    def add_join_item(self, form: str, item: str, order: int, how: str):
        """Add a join item to the form."""
        if form in self.selected_forms.keys():
            self.selected_forms[form].set_join_item_state(item, include=True)
            self.selected_forms[form].set_join_order(order)
            self.selected_forms[form].set_join_how(how)

    def update_join_items(self, form: str, items: list, order: int, how: str):
        """Update the join items for a form."""
        if form in self.selected_forms.keys():
            self.selected_forms[form].set_join_items(items)
            self.selected_forms[form].set_join_order(order)
            self.selected_forms[form].set_join_how(how)

    def update_join_list(self, join_list: list):
        """Update the join list for all forms."""
        for form, items, order, how in join_list:
            self.update_join_items(form, items, order, how)

    def get_all_selected_items(self):
        """Get all items from all selected forms and common items."""
        all_items = []
        for form in self.selected_forms.values():
            all_items.extend(form.get_selected_form_items())
        all_items.extend(self.selected_common_items)
        return list(set(all_items))

    def get_static_filter_items(self):
        """Get the list of static filter items."""
        return self.static_filter_items

    def add_static_filter_item(self, item: str, operator: str, value: str):
        """Add a static filter item."""
        # Check if the item is a common item or a form-prefixed item
        if item in self.get_selected_common_items():
            # Item is a common item
            if (item, operator, value) not in self.static_filter_items:
                self.static_filter_items.append((item, operator, value))
        elif "." in item:
            # Item is form-prefixed (e.g. "DM.Legal Sex (ig_DM1.SEX)")
            form_name, item_name = item.split(".", 1)
            if form_name in self.selected_forms:
                if item_name in self.selected_forms[form_name].get_selected_form_items():
                    if (item, operator, value) not in self.static_filter_items:
                        self.static_filter_items.append((item, operator, value))
        else:
            # Check if the item is in any form's selected items
            for form_name, form in self.selected_forms.items():
                if item in form.get_selected_form_items():
                    if (item, operator, value) not in self.static_filter_items:
                        self.static_filter_items.append((item, operator, value))
                    break

        # Add debug print
        print(f"After adding filter: {self.static_filter_items}")

    def remove_static_filter_item(self, item: str, operator: str = None, value: str = None):
        """Remove a static filter item."""
        self.static_filter_items = [
            f
            for f in self.static_filter_items
            if not (f[0] == item and (operator is None or f[1] == operator) and (value is None or f[2] == value))
        ]

    def set_static_filter_items(self, items: list):
        """Set the static filter items."""
        self.static_filter_items = deepcopy(items)

    def get_dynamic_filter_items(self):
        """Get the list of dynamic filter items."""
        return self.dynamic_filter_items

    def add_dynamic_filter_item(self, item1: str, operator: str, item2: str):
        """Add a dynamic filter item.

        This creates a filter between two items with the specified operator.
        """
        # Both items need to exist either as common items or form items (with or without prefix)
        # For form items, they can be in format "form_name.item_name" or just "item_name"

        # Always add the filter - we'll validate it at runtime when the report is created
        if (item1, operator, item2) not in self.dynamic_filter_items:
            # Add the item to the dynamic filter items
            self.dynamic_filter_items.append((item1, operator, item2))
            print(f"Added dynamic filter: {item1} {operator} {item2}")

    def remove_dynamic_filter_item(self, item1: str = None, operator: str = None, item2: str = None):
        """Remove a dynamic filter item.

        If any parameter is None, it matches any value for that position.
        """
        self.dynamic_filter_items = [
            f
            for f in self.dynamic_filter_items
            if not (
                (item1 is None or f[0] == item1)
                and (operator is None or f[1] == operator)
                and (item2 is None or f[2] == item2)
            )
        ]

    def set_dynamic_filter_items(self, items: list):
        """Set the dynamic filter items."""
        self.dynamic_filter_items = deepcopy(items)

    def update_dynamic_filter_item(self, row: int, item1: str, operator: str, item2: str) -> None:
        """Update or append a dynamic filter item by row.

        If ``row`` is within the current list bounds, replace that entry.
        If ``row`` is at or beyond the end, append a new entry.
        """
        new_item = (item1, operator, item2)

        if row < 0:
            return

        if row < len(self.dynamic_filter_items):
            self.dynamic_filter_items[row] = new_item
        else:
            # Append when adding a brand new dynamic filter row from the UI
            self.dynamic_filter_items.append(new_item)

    def create_report(self):
        """Create the report based on the stored info.
        This method should be implemented to generate the report based on the selected forms,
        common items, form items, join items, and filters, and rename.
        For each form within the join list, sorted based on the join order:
            Get the data from self.data dictionary for all selected columns(common items and selected
            items of that form)
            Filter the table with static filter items if items within the list is in the form
            Join with the previously joined table (if applicable since the first table would not needed to join) based on join type
        Once all tables are joined:
            Filter the table using dynamic filter item list (filter based on other values within joined table)
            Rename the items with the rename items list

        Return:
        The joined table
        """
        import pandas as pd

        from clinical_reporting.services.util import apply_dynamic_filter, apply_static_filter

        # Initialize result dataframe
        result_df = None

        # Get selected forms and sort by join order
        selected_forms = self.get_selected_forms_list()

        # Create a list of forms with their join order for sorting
        form_order_list = [(form, self.selected_forms[form].get_join_order() or 999) for form in selected_forms]

        # Sort forms by join order
        form_order_list.sort(key=lambda x: x[1])

        # Process each form in order
        for form_name, _ in form_order_list:
            form = self.selected_forms[form_name]

            # Get columns to select from this form
            columns_to_select = []

            # Add selected common items
            for item in self.selected_common_items:
                if item in self.data[form_name].columns:
                    columns_to_select.append(item)

            # Add join items if they exist in this form
            for item in form.get_join_items():
                if item and item in self.data[form_name].columns and item not in columns_to_select:
                    columns_to_select.append(item)

            # Add form-specific items
            for item in form.get_selected_form_items():
                if item in self.data[form_name].columns and item not in columns_to_select:
                    columns_to_select.append(item)

            # Get data for this form with selected columns
            if columns_to_select:
                form_df = self.data[form_name][columns_to_select].copy()
            else:
                # If no columns selected, continue to next form
                continue

            # Apply static filters to this form's data
            for item, operator, value in self.static_filter_items:
                # Check if the filter item is in this form (without form prefix)
                if item in form_df.columns:
                    form_df = apply_static_filter(form_df, item, operator, value)
                # Check if the filter item is form-prefixed and matches this form
                elif "." in item:
                    prefix, col_name = item.split(".", 1)
                    if prefix == form_name and col_name in form_df.columns:
                        form_df = apply_static_filter(form_df, col_name, operator, value)

            # If this is the first form, set it as the result and continue
            if result_df is None:
                # Add form prefix to non-common columns
                rename_cols = {}
                for col in form_df.columns:
                    if col not in self.selected_common_items:
                        rename_cols[col] = f"{form_name}.{col}"

                if rename_cols:
                    form_df = form_df.rename(columns=rename_cols)

                result_df = form_df
                continue

            # For subsequent forms, prepare for join
            # Add form prefix to non-common columns
            rename_cols = {}
            for col in form_df.columns:
                if col not in self.selected_common_items and col not in form.get_join_items():
                    rename_cols[col] = f"{form_name}.{col}"

            if rename_cols:
                form_df = form_df.rename(columns=rename_cols)

            # Get join type
            join_how = form.get_join_how() or "Left join"

            # Convert join_how string to pandas merge method
            if join_how == "Left join":
                how = "left"
            elif join_how == "Right join":
                how = "right"
            elif join_how == "Inner join":
                how = "inner"
            elif join_how == "Outer join":
                how = "outer"
            else:
                how = "left"  # Default to left join

            # Get join items
            join_items = [item for item in form.get_join_items() if item]

            # drop index
            form_df = form_df.reset_index(drop=True)

            # remove duplicate
            form_df = form_df.drop_duplicates()
            # If no join items, skip this form
            if not join_items:
                continue

            # Align join column dtypes to prevent merge errors (e.g., object vs datetime)
            for join_col in join_items:
                if join_col in result_df.columns and join_col in form_df.columns:
                    left_series = result_df[join_col]
                    right_series = form_df[join_col]
                    is_date_column = (
                        "date" in join_col.lower()
                        or pd.api.types.is_datetime64_any_dtype(left_series)
                        or pd.api.types.is_datetime64_any_dtype(right_series)
                    )
                    if is_date_column:
                        result_df[join_col] = pd.to_datetime(left_series, errors="coerce")
                        form_df[join_col] = pd.to_datetime(right_series, errors="coerce")
                    elif left_series.dtype != right_series.dtype:
                        result_df[join_col] = left_series.astype(str)
                        form_df[join_col] = right_series.astype(str)

            # Perform the join
            result_df = pd.merge(result_df, form_df, on=join_items, how=how)

        # Apply dynamic filters after all joins
        if result_df is not None:
            # print(f"Applying dynamic filters: {self.dynamic_filter_items}")
            # print(f"Available columns: {result_df.columns.tolist()}")

            for item1, operator, item2 in self.dynamic_filter_items:
                # Handle both with and without form prefix
                item1_col = None
                item2_col = None

                # Check if items exist directly in columns
                if item1 in result_df.columns:
                    item1_col = item1
                if item2 in result_df.columns:
                    item2_col = item2

                # If items have form prefixes, they should already be in the columns
                # If not found, try checking if they're common items without form prefix
                if item1_col is None and "." not in item1:
                    # Check if any column ends with this item name (after form prefix)
                    for col in result_df.columns:
                        if "." in col and col.split(".", 1)[1] == item1:
                            item1_col = col
                            break

                if item2_col is None and "." not in item2:
                    # Check if any column ends with this item name (after form prefix)
                    for col in result_df.columns:
                        if "." in col and col.split(".", 1)[1] == item2:
                            item2_col = col
                            break

                # Apply filter if both columns were found
                if item1_col is not None and item2_col is not None:
                    print(f"Applying filter: {item1_col} {operator} {item2_col}")
                    result_df = apply_dynamic_filter(result_df, item1_col, operator, item2_col)
                else:
                    print(f"Could not find columns for filter: {item1} {operator} {item2}")
                    print(f"item1_col: {item1_col}, item2_col: {item2_col}")

        # Reorder columns according to order_list if it exists (before renaming)
        if result_df is not None and self.order_list:
            # Filter order_list to only include columns that exist in result_df
            valid_order = [col for col in self.order_list if col in result_df.columns]

            # Get columns that are in result_df but not in order_list
            remaining_cols = [col for col in result_df.columns if col not in valid_order]

            # Reorder columns
            if valid_order:
                result_df = result_df[valid_order + remaining_cols]

        # Use the selected_items_order_list if it exists (priority over order_list)
        elif result_df is not None and self.selected_items_order_list:
            # Filter selected_items_order_list to only include columns that exist in result_df
            valid_order = [col for col in self.selected_items_order_list if col in result_df.columns]

            # Get columns that are in result_df but not in the order list
            remaining_cols = [col for col in result_df.columns if col not in valid_order]

            # Reorder columns
            if valid_order:
                result_df = result_df[valid_order + remaining_cols]

        # Rename columns according to rename_dict (after reordering)
        if result_df is not None and self.rename_dict:
            # Create a mapping dict for renaming
            rename_mapping = {}
            for orig_name, new_name in self.rename_dict.items():
                if orig_name in result_df.columns and new_name:
                    rename_mapping[orig_name] = new_name

            # Apply renaming
            if rename_mapping:
                result_df = result_df.rename(columns=rename_mapping)

        # make sure all date columns are formatted to %m-%d-%Y
        if result_df is not None:
            # Use a more comprehensive approach to catch all date columns
            date_cols = []

            # Method 1: Using select_dtypes with all datetime types
            date_cols.extend(result_df.select_dtypes(include=["datetime64", "datetime", np.datetime64]).columns)

            # Method 2: Check column names containing 'Date'/'date'
            for col in result_df.columns:
                if "date" in col.lower() and col not in date_cols:
                    try:
                        # Attempt to convert to datetime to confirm it's a date column,
                        # prefer using a mixed format to avoid inference warnings.
                        inferred_datetime = False
                        if pd.api.types.is_datetime64_dtype(result_df[col]):
                            inferred_datetime = True
                        else:
                            try:
                                parsed = pd.to_datetime(result_df[col], errors="coerce", format="mixed")
                            except TypeError:
                                # Older pandas may not support format="mixed"; fall back and suppress warning
                                import warnings as _warnings

                                with _warnings.catch_warnings():
                                    _warnings.simplefilter("ignore", category=UserWarning)
                                    parsed = pd.to_datetime(result_df[col], errors="coerce")
                            inferred_datetime = parsed.notna().any()

                        if inferred_datetime:
                            date_cols.append(col)
                    except Exception:
                        pass

            # Format each identified date column
            for col in date_cols:
                try:
                    # Convert to datetime first (in case it's not already), avoiding format inference warnings
                    try:
                        parsed = pd.to_datetime(result_df[col], errors="coerce", format="mixed")
                    except TypeError:
                        import warnings as _warnings

                        with _warnings.catch_warnings():
                            _warnings.simplefilter("ignore", category=UserWarning)
                            parsed = pd.to_datetime(result_df[col], errors="coerce")

                    result_df[col] = parsed
                    # Format without leading zeros
                    result_df[col] = result_df[col].apply(
                        lambda x: f"{x.month}/{x.day}/{x.year}" if pd.notnull(x) else ""
                    )
                except Exception:
                    print(f"Could not format column {col} as date")

        # * Remove possible duplicate within result_df
        if result_df is not None:
            result_df = result_df.reset_index(drop=True)
            # Remove duplicate rows
            result_df = result_df.drop_duplicates()

        # * If Subject is in 1 of the column, sort by Subject
        if result_df is not None and "Subject" in result_df.columns:
            result_df = result_df.sort_values(by="Subject")

        return result_df
