from CLForm import CLForm
from copy import deepcopy
import json


class CLReport:
    """A class to represent a report that contains multiple forms and columns."""

    def __init__(self):
        self.data = {}
        self.available_forms = {}
        self.selected_forms = {}
        self.available_common_items = []
        self.selected_common_items = []
        self.new_items = []
        self.order_list = []
        self.rename_dict = {}
        self.file_path = None
        self.static_available_common_items = [
            "Study",
            "Study Country",
            "Study Site",
            "Subject",
            "Event Group Label",
            "Event Group Name",
            "Event Group Sequence Number",
            "Event Label",
            "Event Name",
            "Event Date",
            "Form Casebook Version",
            "Form Label",
            "Form Name",
            "Form Sequence Number",
            "Form Status",
            "Datetime of Form Creation",
            "Form First Submission Date",
            "Form Last Submission Date",
            "Form ILB Status",
            "Form ILB Reason",
            "Item Group Sequence Number",
            "Datetime of Last Data Change",
            "Data Listing As Of",
            "Opened Queries",
            "Closed Queries",
            "Form SDV Status",
            "Form SDV Datetime",
            "Form DMR Status",
            "Form DMR Datetime",
            "Form Frozen Status",
            "Form Frozen Datetime",
            "Form Locked Status",
            "Form Locked Datetime",
            "Form Signed Status",
            "Form Signed Datetime",
            "Visit Method",
            "LINKEDTO",
        ]
        self.static_filter_items = []  # Static filter items: Item Name, Operator, Value
        self.dynamic_filter_items = []  # Dynamic filter items: Item Name 1 , Operator, Item Name 2
        self.selected_items_order_list = []

        # Add Subject to selected common items by default
        self.selected_common_items.append("Subject")

    def set_data(self, data: dict):
        """Set the data for the report."""
        self.data = data
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
                    self.selected_forms[form].add_available_form_item(item)
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

    def add_available_common_item(self, item: str):
        """Add the available common item to the available common items list."""
        if item not in self.available_common_items:
            self.available_common_items.append(item)
            self.remove_selected_common_item(item)

    def add_all_available_common_items(self):
        """Add all static available common items to the available common items list."""
        for item in self.static_available_common_items:
            self.add_available_common_item(item)

    def remove_available_common_item(self, item: str):
        """Remove the available common item from the available common items list."""
        if item in self.available_common_items:
            self.available_common_items.remove(item)

    def remove_all_available_common_items(self):
        """Remove all available common items from the available common items list."""
        self.available_common_items = []

    def get_available_common_items(self):
        """Get the list of available common items."""
        return self.available_common_items

    def add_selected_common_item(self, item: str):
        """Add the selected common item to the selected common items list."""
        if item not in self.selected_common_items:
            self.selected_common_items.append(item)
            self.remove_available_common_item(item)

    def remove_selected_common_item(self, item: str):
        """Remove the selected common item from the selected common items list."""
        if item in self.selected_common_items:
            self.selected_common_items.remove(item)

    def get_selected_common_items(self):
        """Get the list of selected common items."""
        return self.selected_common_items

    def add_selected_form_item(self, item: str):
        """Add the selected form item to the selected form items list."""
        for form in self.selected_forms.keys():
            if (
                item not in self.selected_forms[form].get_selected_form_items()
                and item in self.available_forms[form].get_available_form_items()
            ):
                self.selected_forms[form].add_selected_form_item(item)

    def add_all_selected_form_items(self):
        """Add all available form items to the selected form items list."""
        for form in self.selected_forms.keys():
            # get all available form items from the selected form
            items = self.selected_forms[form].get_available_form_items()
            for item in items:
                self.selected_forms[form].add_selected_form_item(item)

    def remove_selected_form_item(self, item: str):
        """Remove the selected form item from the selected form items list."""
        for form in self.selected_forms.keys():
            if item in self.selected_forms[form].get_selected_form_items():
                self.selected_forms[form].add_available_form_item(item)

    def remove_all_selected_form_items(self):
        """Remove all selected form items from the selected form items list."""
        for form in self.selected_forms.keys():
            for item in self.selected_forms[form].get_selected_form_items():
                self.selected_forms[form].add_available_form_item(item)

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

    def save_setting_to_json(self, file_path: str):
        """Save the report settings to a JSON file."""

        settings = {
            "available_forms": {k: v.__dict__ for k, v in self.available_forms.items()},
            "selected_forms": {k: v.__dict__ for k, v in self.selected_forms.items()},
            "available_common_items": self.available_common_items,
            "selected_common_items": self.selected_common_items,
            "new_items": self.new_items,
            "order_list": self.order_list,
            "rename_dict": self.rename_dict,
            "static_filter_items": self.static_filter_items,
            "dynamic_filter_items": self.dynamic_filter_items,
            "selected_items_order_list": self.selected_items_order_list,
        }
        with open(file_path, "w") as f:
            json.dump(settings, f, indent=4)

    def load_setting_from_json(self, file_path: str):
        """Load the report settings from a JSON file."""
        with open(file_path, "r") as f:
            settings = json.load(f)
            self.available_forms = {
                k: CLForm(**v) for k, v in settings["available_forms"].items()
            }
            self.selected_forms = {
                k: CLForm(**v) for k, v in settings["selected_forms"].items()
            }
            self.available_common_items = settings["available_common_items"]
            self.selected_common_items = settings["selected_common_items"]
            self.new_items = settings["new_items"]
            self.order_list = settings["order_list"]
            self.rename_dict = settings["rename_dict"]
            # Load filter items if they exist in the settings
            if "static_filter_items" in settings:
                self.static_filter_items = settings["static_filter_items"]
            if "dynamic_filter_items" in settings:
                self.dynamic_filter_items = settings["dynamic_filter_items"]
            if "selected_items_order_list" in settings:
                self.selected_items_order_list = settings["selected_items_order_list"]
            else:
                self.update_selected_items_order_list()

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

    def add_join_item(self, form: str, item: str, order: int, how: str):
        """Add a join item to the form."""
        if form in self.selected_forms.keys():
            self.selected_forms[form].add_join_item(item)
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
                if (
                    item_name
                    in self.selected_forms[form_name].get_selected_form_items()
                ):
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

    def remove_static_filter_item(
        self, item: str, operator: str = None, value: str = None
    ):
        """Remove a static filter item."""
        self.static_filter_items = [
            f
            for f in self.static_filter_items
            if not (
                f[0] == item
                and (operator is None or f[1] == operator)
                and (value is None or f[2] == value)
            )
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

    def remove_dynamic_filter_item(
        self, item1: str = None, operator: str = None, item2: str = None
    ):
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
        from util import apply_static_filter, apply_dynamic_filter

        # Initialize result dataframe
        result_df = None

        # Get selected forms and sort by join order
        selected_forms = self.get_selected_forms_list()

        # Create a list of forms with their join order for sorting
        form_order_list = [
            (form, self.selected_forms[form].get_join_order() or 999)
            for form in selected_forms
        ]

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
                if (
                    item
                    and item in self.data[form_name].columns
                    and item not in columns_to_select
                ):
                    columns_to_select.append(item)

            # Add form-specific items
            for item in form.get_selected_form_items():
                if (
                    item in self.data[form_name].columns
                    and item not in columns_to_select
                ):
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
                        form_df = apply_static_filter(
                            form_df, col_name, operator, value
                        )

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
                if (
                    col not in self.selected_common_items
                    and col not in form.get_join_items()
                ):
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
            print(f"form {form_name} before merge:\n{form_df}")
            # If no join items, skip this form
            if not join_items:
                continue

            # Perform the join
            result_df = pd.merge(result_df, form_df, on=join_items, how=how)

        # Apply dynamic filters after all joins
        if result_df is not None:
            print(f"Applying dynamic filters: {self.dynamic_filter_items}")
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
                    result_df = apply_dynamic_filter(
                        result_df, item1_col, operator, item2_col
                    )
                else:
                    print(
                        f"Could not find columns for filter: {item1} {operator} {item2}"
                    )
                    print(f"item1_col: {item1_col}, item2_col: {item2_col}")

        # Reorder columns according to order_list if it exists (before renaming)
        if result_df is not None and self.order_list:
            # Filter order_list to only include columns that exist in result_df
            valid_order = [col for col in self.order_list if col in result_df.columns]

            # Get columns that are in result_df but not in order_list
            remaining_cols = [
                col for col in result_df.columns if col not in valid_order
            ]

            # Reorder columns
            if valid_order:
                result_df = result_df[valid_order + remaining_cols]

        # Use the selected_items_order_list if it exists (priority over order_list)
        elif result_df is not None and self.selected_items_order_list:
            # Filter selected_items_order_list to only include columns that exist in result_df
            valid_order = [
                col
                for col in self.selected_items_order_list
                if col in result_df.columns
            ]

            # Get columns that are in result_df but not in the order list
            remaining_cols = [
                col for col in result_df.columns if col not in valid_order
            ]

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

        # * Remove possible duplicate within result_df
        # remove index as well
        if result_df is not None:
            result_df = result_df.reset_index(drop=True)
            # Remove duplicate rows
            result_df = result_df.drop_duplicates()

        # * If Subject is in 1 of the column, sort by Subject
        if result_df is not None and "Subject" in result_df.columns:
            result_df = result_df.sort_values(by="Subject")

        return result_df
