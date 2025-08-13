# This Python file uses the following encoding: utf-8
import sys
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QFileDialog,
    QTableWidgetItem,
    QComboBox,
    QLineEdit,
)
from PySide6.QtCore import Qt, QAbstractTableModel
from PySide6.QtWidgets import QAbstractItemView
from PySide6.QtGui import QStandardItemModel, QStandardItem
from CLReport import CLReport
from util import read_data_dict_zip_corelisting, get_excel_formats
import pandas as pd
import numpy as np

# Important:
# You need to run the following command to generate the ui_form.py file
#     pyside6-uic form.ui -o ui_form.py, or
#     pyside2-uic form.ui -o ui_form.py
from ui_form import Ui_Widget


class Widget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setWindowTitle("Clinical Reporting Tool")
        self.study_name = None
        self.report = CLReport()
        self.output_folder_name = None

        # Set up tables
        self._setup_tables()

        # * Setting tab
        self.ui.pushButton_input_file.clicked.connect(self.click_input_file)
        self.ui.pushButton_output_folder.clicked.connect(self.click_output_file)

        # * Form tab
        self.ui.pushButton_select_form.clicked.connect(self.click_select_form)
        self.ui.pushButton_remove_form.clicked.connect(self.click_remove_form)
        self.ui.pushButton_select_all_form.clicked.connect(self.click_select_all_form)
        self.ui.pushButton_remove_all_form.clicked.connect(self.click_remove_all_form)

        # Connect double-click events for form list widgets
        self.ui.listWidget_form_available.itemDoubleClicked.connect(
            self.on_form_available_double_clicked
        )
        self.ui.listWidget_form_selected.itemDoubleClicked.connect(
            self.on_form_selected_double_clicked
        )

        # * Common items tab
        # Connect common item buttons
        self.ui.pushButton_select_common_item.clicked.connect(
            self.click_select_common_item
        )
        self.ui.pushButton_remove_common_item.clicked.connect(
            self.click_remove_common_item
        )
        self.ui.pushButton_select_all_common_item.clicked.connect(
            self.click_select_all_common_item
        )
        self.ui.pushButton_remove_all_common_item.clicked.connect(
            self.click_remove_all_common_item
        )

        # * Form items tab
        # Connect form item buttons
        self.ui.pushButton_select_form_item.clicked.connect(self.click_select_form_item)
        self.ui.pushButton_remove_form_item.clicked.connect(self.click_remove_form_item)
        self.ui.pushButton_select_all_form_item.clicked.connect(
            self.click_select_all_form_item
        )
        self.ui.pushButton_remove_all_form_item.clicked.connect(
            self.click_remove_all_form_item
        )

        # Connect double-click events for form item list widgets
        self.ui.listWidget_form_item_available.itemDoubleClicked.connect(
            self.on_form_item_available_double_clicked
        )
        self.ui.listWidget_form_item_selected.itemDoubleClicked.connect(
            self.on_form_item_selected_double_clicked
        )

        # Connect double-click events for common item list widgets
        self.ui.listWidget_common_item_available.itemDoubleClicked.connect(
            self.on_common_item_available_double_clicked
        )
        self.ui.listWidget_common_item_selected.itemDoubleClicked.connect(
            self.on_common_item_selected_double_clicked
        )

        # Connect form selection change to update form items
        self.ui.listWidget_form_selected.itemSelectionChanged.connect(
            self.update_form_dependent_ui
        )
        # * Filter tab
        # Connect push buttons for filter functionality
        self.ui.pushButton_static_filter_add.clicked.connect(self.static_filter_add)
        self.ui.pushButton_static_filter_remove.clicked.connect(
            self.static_filter_remove
        )

        # * Comparison and Rename tab
        # Connect table cell changes for rename functionality
        self.ui.tableWidget_rename.cellChanged.connect(self.on_rename_cell_changed)

        # Connect buttons for items reordering
        self.ui.pushButton_order_up.clicked.connect(self.click_order_up)
        self.ui.pushButton_order_down.clicked.connect(self.click_order_down)

        # Add connections for dynamic filter buttons
        self.ui.pushButton_dynamic_filter_add.clicked.connect(self.dynamic_filter_add)
        self.ui.pushButton_dynamic_filter_remove.clicked.connect(
            self.dynamic_filter_remove
        )

        # Connect tab change signal to handle preview tab
        self.ui.tabWidget.currentChanged.connect(self.on_tab_changed)

        # Connect Run and Save button
        self.ui.pushButton_run_and_save.clicked.connect(self.click_run_and_save)

        # Set selection behavior for dynamic filter table
        self.ui.tableWidget_dynamic_filter.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self.ui.tableWidget_dynamic_filter.setSelectionMode(
            QAbstractItemView.SingleSelection
        )

        # Set selection behavior for static filter table
        self.ui.tableWidget_static_filter.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self.ui.tableWidget_static_filter.setSelectionMode(
            QAbstractItemView.SingleSelection
        )

        self.add_listWidget_form_available()
        self.add_listWidget_form_selected()
        self.add_listWidget_common_item_available()
        self.add_listWidget_common_item_selected()

    # ---- Hierarchical UI Update System ----

    def update_all_ui(self):
        """Update all UI elements in the correct order based on dependencies."""
        self.update_forms_ui()
        self.update_common_items_ui()  # Add this to ensure common items are updated
        self.update_form_dependent_ui()

    def update_forms_ui(self):
        """Update form-related UI elements."""
        self.add_listWidget_form_available()
        self.add_listWidget_form_selected()

    def update_form_dependent_ui(self):
        """Update UI elements that depend on selected forms."""
        self.update_form_items_ui()
        self.update_join_table_ui()

    def update_form_items_ui(self):
        """Update form items based on selected forms."""
        self.add_listWidget_form_item_available()
        self.add_listWidget_form_item_selected()
        # Also update elements that depend on form items
        self.update_items_dependent_ui()

    def update_common_items_ui(self):
        """Update common items lists."""
        self.add_listWidget_common_item_available()
        self.add_listWidget_common_item_selected()
        # Also update elements that depend on common items
        self.update_items_dependent_ui()
        # Add this line to update the join table when common items change
        self.update_join_table_ui()

    def update_items_dependent_ui(self):
        """Update UI elements that depend on selected items (both common and form items)."""
        self.update_rename_table()
        self.update_static_filter_table()
        self.update_dynamic_filter_table()
        self.update_items_order_list()  # Add this line to update the order list

    def update_join_table_ui(self):
        """Update the join table based on selected forms."""
        self.update_selected_forms_table()

    def update_static_filter_table(self):
        """Update the static filter table based on selected items."""
        # Temporarily disconnect itemChanged signal
        try:
            self.ui.tableWidget_static_filter.itemChanged.disconnect()
        except:
            pass  # It's OK if it wasn't connected

        # Clear the table
        self.ui.tableWidget_static_filter.setRowCount(0)

        # Get all static filter items from the report
        filter_items = self.report.get_static_filter_items()

        # Add each filter item to the table
        for item, operator, value in filter_items:
            row = self.ui.tableWidget_static_filter.rowCount()
            self.ui.tableWidget_static_filter.insertRow(row)

            # Add item dropdown to first column
            self._add_dropdown(row, 0, "item", item)

            # Add operator dropdown to second column
            self._add_dropdown(row, 1, "operator", operator)

            # Add value field to third column
            value_item = QTableWidgetItem(value)
            self.ui.tableWidget_static_filter.setItem(row, 2, value_item)

        # Reconnect itemChanged signal
        self.ui.tableWidget_static_filter.itemChanged.connect(self._on_filter_changed)

        # Adjust column widths after populating the table
        self._adjust_column_widths(self.ui.tableWidget_static_filter)

    def synchronize_static_filters(self):
        """Synchronize the static filter items in the report with the UI table."""
        # Get all current filters from the table
        new_filters = []

        for row in range(self.ui.tableWidget_static_filter.rowCount()):
            item_combo = self.ui.tableWidget_static_filter.cellWidget(row, 0)
            operator_combo = self.ui.tableWidget_static_filter.cellWidget(row, 1)
            value_item = self.ui.tableWidget_static_filter.item(row, 2)

            if item_combo and operator_combo and value_item:
                item = item_combo.currentText()
                operator = operator_combo.currentText()
                value = value_item.text()

                if item and operator:  # Only add if we have at least item and operator
                    new_filters.append((item, operator, value))

        # Clear all existing filters in report
        self.report.set_static_filter_items([])

        # Add all the filters from the table
        for item, operator, value in new_filters:
            self.report.add_static_filter_item(item, operator, value)

        print(f"Synchronized static filters: {self.report.get_static_filter_items()}")

    def _add_dropdown(self, row, column, dropdown_type, selected_value=None):
        """Add a dropdown with the specified type to the table cell.

        Args:
            row: The row index
            column: The column index
            dropdown_type: Either "item" or "operator"
            selected_value: The value to select in the dropdown
        """
        # Create combo box
        combo = QComboBox()

        if dropdown_type == "item":
            # Get all selected items (common items and form items)
            all_items = []

            # Add common items
            for item in self.report.get_selected_common_items():
                all_items.append(item)

            # Add form items with form name prefix
            for form_name in self.report.get_selected_forms_list():
                form = self.report.selected_forms[form_name]
                for item in form.get_selected_form_items():
                    all_items.append(f"{form_name}.{item}")

            # Sort items and add to combo box
            all_items.sort()
            for item in all_items:
                combo.addItem(item)

        elif dropdown_type == "operator":
            # Add operator options
            operators = [
                "=",
                "!=",
                ">",
                ">=",
                "<",
                "<=",
                "Contains",
                "Does not contain",
                "In",
                "Not in",
                "is Null",
                "is not Null",
            ]
            for op in operators:
                combo.addItem(op)

            # Connect special handler for operator changes to manage value column
            combo.currentTextChanged.connect(
                lambda text, r=row: self._on_operator_changed(r, text)
            )

        # Set selected value if provided
        if selected_value:
            combo.setCurrentText(selected_value)

        # Connect signal to update the static filter items when changed
        combo.currentTextChanged.connect(lambda: self._on_filter_changed(row))

        # Add to table
        self.ui.tableWidget_static_filter.setCellWidget(row, column, combo)

        # If this is an operator dropdown, check initial state for null operators
        if dropdown_type == "operator" and selected_value in ["is Null", "is not Null"]:
            self._on_operator_changed(row, selected_value)

    def _on_operator_changed(self, row, operator_text):
        """Handle changes to the operator dropdown to manage value column.

        Args:
            row: The row that changed
            operator_text: The new operator value
        """
        # Get the value column item
        value_item = self.ui.tableWidget_static_filter.item(row, 2)

        # If operator is for null checking, disable value column and clear it
        if operator_text in ["is Null", "is not Null"]:
            # Create an empty item if one doesn't exist
            if not value_item:
                value_item = QTableWidgetItem("")
                self.ui.tableWidget_static_filter.setItem(row, 2, value_item)

            # Clear the value and disable the cell
            value_item.setText("")
            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEnabled)
        else:
            # Enable the cell for editing if it exists
            if value_item:
                value_item.setFlags(
                    value_item.flags() | Qt.ItemIsEnabled | Qt.ItemIsEditable
                )
            else:
                # Create a new editable item if one doesn't exist
                value_item = QTableWidgetItem("")
                value_item.setFlags(
                    value_item.flags() | Qt.ItemIsEnabled | Qt.ItemIsEditable
                )
                self.ui.tableWidget_static_filter.setItem(row, 2, value_item)

    def static_filter_add(self):
        """Add a new row to the static filter table."""
        # Add a new row
        row = self.ui.tableWidget_static_filter.rowCount()
        self.ui.tableWidget_static_filter.insertRow(row)

        # Temporarily disconnect itemChanged signal to avoid triggering events during setup
        try:
            self.ui.tableWidget_static_filter.itemChanged.disconnect()
        except:
            pass  # It's OK if it wasn't connected

        # Add item dropdown to first column
        self._add_dropdown(row, 0, "item")

        # Add operator dropdown to second column
        self._add_dropdown(row, 1, "operator", "=")  # Default to equals

        # Add empty value field to third column
        value_item = QTableWidgetItem("")
        self.ui.tableWidget_static_filter.setItem(row, 2, value_item)

        # Get the selected values from the dropdown (to add to the report's data)
        item_combo = self.ui.tableWidget_static_filter.cellWidget(row, 0)
        operator_combo = self.ui.tableWidget_static_filter.cellWidget(row, 1)

        if item_combo and operator_combo:
            item = item_combo.currentText()
            operator = operator_combo.currentText()
            value = ""  # Empty value initially

            # Add the initial filter to the report (this is the key fix)
            if item:  # Only add if we have a valid item
                self.report.add_static_filter_item(item, operator, value)
                print(f"Added initial filter: {item} {operator} '{value}'")

        # Reconnect itemChanged signal
        self.ui.tableWidget_static_filter.itemChanged.connect(self._on_filter_changed)

        # Set appropriate state for value column based on initial operator
        if operator_combo:
            self._on_operator_changed(row, operator_combo.currentText())

    def static_filter_remove(self):
        """Remove selected rows from the static filter table."""
        # Get selected rows
        selected_rows = set()

        # First try normal selection
        for item in self.ui.tableWidget_static_filter.selectedItems():
            selected_rows.add(item.row())

        # If no rows selected, check current row
        if not selected_rows:
            current_row = self.ui.tableWidget_static_filter.currentRow()
            if current_row >= 0:
                selected_rows.add(current_row)

        # If still no rows selected, show message and return
        if not selected_rows:
            print("No rows selected for removal")
            return

        # Remove rows in reverse order to avoid index shifting
        for row in sorted(selected_rows, reverse=True):
            # Get the filter details before removing
            item_combo = self.ui.tableWidget_static_filter.cellWidget(row, 0)
            operator_combo = self.ui.tableWidget_static_filter.cellWidget(row, 1)
            value_item = self.ui.tableWidget_static_filter.item(row, 2)

            if item_combo and operator_combo and value_item:
                item = item_combo.currentText()
                operator = operator_combo.currentText()
                value = value_item.text()

                # Remove from report
                self.report.remove_static_filter_item(item, operator, value)
                print(f"Removed filter: {item} {operator} '{value}'")

            # Remove row from table
            self.ui.tableWidget_static_filter.removeRow(row)

        # Update dependent UI elements
        self.update_items_dependent_ui()

    def _on_filter_changed(self, row=None):
        """Handle changes to any part of a filter row.

        Args:
            row: The row that changed. If None, the sender is a QTableWidgetItem
                 and we need to get the row from it.
        """
        # Determine the row that changed
        if isinstance(row, QTableWidgetItem):
            # When called from itemChanged signal with a QTableWidgetItem
            item = row
            row = item.row()
        elif row is None and isinstance(self.sender(), QTableWidgetItem):
            # When called from itemChanged signal without arguments
            item = self.sender()
            row = item.row()
        elif row is None:
            # Try to determine row from sender() for combo boxes
            sender = self.sender()
            if sender:
                # Find the row of this widget
                for r in range(self.ui.tableWidget_static_filter.rowCount()):
                    for c in range(2):  # Check first 2 columns (dropdown columns)
                        if self.ui.tableWidget_static_filter.cellWidget(r, c) == sender:
                            row = r
                            break
                    if row is not None:
                        break

        # If we still couldn't determine the row, exit
        if row is None:
            print("Could not determine which row changed")
            return

        # Get the current values from the row
        item_combo = self.ui.tableWidget_static_filter.cellWidget(row, 0)
        operator_combo = self.ui.tableWidget_static_filter.cellWidget(row, 1)
        value_item = self.ui.tableWidget_static_filter.item(row, 2)

        if item_combo and operator_combo and value_item:
            item = item_combo.currentText()
            operator = operator_combo.currentText()
            value = value_item.text()

            # Only process if we have valid item and operator selections
            if item and operator:
                # Get the current filters to find what we need to remove
                current_filters = self.report.get_static_filter_items()

                # If we have more filters than rows, we need to clean up
                if len(current_filters) > self.ui.tableWidget_static_filter.rowCount():
                    # Rebuild the filter list based on the current table state
                    self.synchronize_static_filters()
                    return

                # Otherwise, remove the filter for this row if it exists
                if row < len(current_filters):
                    old_item, old_operator, old_value = current_filters[row]
                    self.report.remove_static_filter_item(
                        old_item, old_operator, old_value
                    )

                # Add the updated filter
                self.report.add_static_filter_item(item, operator, value)
                print(f"Updated filter: {item} {operator} '{value}'")

    def click_input_file(self):
        """Open a file dialog to choose the input file."""
        default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select the input Corelisting zip file",
            default_dir,
            "Zip files (*.zip);;All Files (*)",
        )
        if file_path:
            # Create a new CLReport instance to clear all previous data
            self.report = CLReport()
            file_name = file_path.split("/")[-1]
            self.study_name = file_name.split("_")[2]
            self.report.set_data(read_data_dict_zip_corelisting(file_path))
            # Add Subject to selected common items by default
            self.report.add_selected_common_item("Subject")
            # Update all UI elements after loading data
            self.update_all_ui()
            self.ui.label_input_file.setText("Input path: " + file_path)

    def click_output_file(self):
        default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        output_folder_name = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", default_dir
        )
        # output filename to screen
        if output_folder_name:
            self.ui.label_output_folder.setText("Output path: " + output_folder_name)
            self.output_folder_name = output_folder_name

    def add_listWidget_form_available(self):
        """Add available forms to the list widget."""
        self.ui.listWidget_form_available.clear()
        available_forms = sorted(
            self.report.get_available_forms_list()
        )  # Sort alphabetically
        for form in available_forms:
            self.ui.listWidget_form_available.addItem(form)

    def add_listWidget_form_selected(self):
        """Add selected forms to the list widget."""
        self.ui.listWidget_form_selected.clear()
        selected_forms = self.report.get_selected_forms_list()
        for form in selected_forms:
            self.ui.listWidget_form_selected.addItem(form)

    def click_select_form(self):
        """Select a form from the available forms and add it to the selected forms."""
        selected_items = self.ui.listWidget_form_available.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            form_name = item.text()
            self.report.add_selected_form(form_name)

        # Update UI with hierarchical dependencies
        self.update_forms_ui()
        self.update_common_items_ui()  # Add this to update common items when forms change
        self.update_form_dependent_ui()

    def click_remove_form(self):
        """Remove a form from the selected forms."""
        selected_items = self.ui.listWidget_form_selected.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            form_name = item.text()
            self.report.add_available_form(form_name)

        # Update UI with hierarchical dependencies
        self.update_forms_ui()
        self.update_common_items_ui()  # Add this to update common items when forms change
        self.update_form_dependent_ui()

    def click_select_all_form(self):
        """Select all available forms and add them to the selected forms."""
        self.report.add_all_selected_forms()
        # Update UI with hierarchical dependencies
        self.update_forms_ui()
        self.update_common_items_ui()  # Add this to update common items when forms change
        self.update_form_dependent_ui()

    def click_remove_all_form(self):
        """Remove all selected forms and add them back to the available forms."""
        self.report.add_all_available_forms()
        # Update UI with hierarchical dependencies
        self.update_forms_ui()
        self.update_common_items_ui()  # Add this to update common items when forms change
        self.update_form_dependent_ui()

    def add_listWidget_common_item_available(self):
        """Add available common items to the list widget."""
        self.ui.listWidget_common_item_available.clear()
        # Sort the available items alphabetically
        available_items = sorted(self.report.get_available_common_items())
        for item in available_items:
            self.ui.listWidget_common_item_available.addItem(item)

    def add_listWidget_common_item_selected(self):
        """Add selected common items to the list widget."""
        self.ui.listWidget_common_item_selected.clear()
        selected_items = self.report.get_selected_common_items()
        for item in selected_items:
            self.ui.listWidget_common_item_selected.addItem(item)

    def click_select_common_item(self):
        """Select a common item from the available items and add it to the selected items."""
        selected_items = self.ui.listWidget_common_item_available.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            item_name = item.text()
            self.report.add_selected_common_item(item_name)

        # Update UI with hierarchical dependencies
        self.update_common_items_ui()

    def click_remove_common_item(self):
        """Remove a common item from the selected items."""
        selected_items = self.ui.listWidget_common_item_selected.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            item_name = item.text()
            self.report.add_available_common_item(item_name)

        # Update UI with hierarchical dependencies
        self.update_common_items_ui()

    def click_select_all_common_item(self):
        """Select all available common items and add them to the selected items."""
        available_items = self.report.get_available_common_items()
        for item in available_items[
            :
        ]:  # Create a copy to avoid modification during iteration
            self.report.add_selected_common_item(item)

        # Update UI with hierarchical dependencies
        self.update_common_items_ui()

    def click_remove_all_common_item(self):
        """Remove all selected common items and add them back to the available items."""
        selected_items = self.report.get_selected_common_items()
        for item in selected_items[
            :
        ]:  # Create a copy to avoid modification during iteration
            self.report.add_available_common_item(item)

        # Update UI with hierarchical dependencies
        self.update_common_items_ui()

    def update_form_items(self):
        """Update the form items when forms are selected."""
        # Get all selected forms from the report
        selected_forms = self.report.get_selected_forms_list()

        if selected_forms:
            print(f"Selected forms: {selected_forms}")
            self.add_listWidget_form_item_available()
            self.add_listWidget_form_item_selected()
        else:
            self.ui.listWidget_form_item_available.clear()
            self.ui.listWidget_form_item_selected.clear()

    def add_listWidget_form_item_available(self):
        """Add available form items to the list widget from all selected forms."""
        self.ui.listWidget_form_item_available.clear()

        # Get all selected forms
        selected_forms = self.report.get_selected_forms_list()

        if not selected_forms:
            print("No forms selected")
            return

        # Collect all available items from all selected forms
        all_available_items = set()
        for form_name in selected_forms:
            if form_name in self.report.selected_forms:
                form_items = self.report.selected_forms[
                    form_name
                ].get_available_form_items()
                for item in form_items:
                    all_available_items.add(f"{form_name}.{item}")

        # Sort the available items alphabetically
        sorted_items = sorted(all_available_items)
        print(f"Available items from all forms: {sorted_items}")

        for item in sorted_items:
            self.ui.listWidget_form_item_available.addItem(item)
            print(f"Added item {item} to listWidget_form_item_available")

    def add_listWidget_form_item_selected(self):
        """Add selected form items to the list widget from all selected forms."""
        self.ui.listWidget_form_item_selected.clear()

        # Get all selected forms
        selected_forms = self.report.get_selected_forms_list()

        if not selected_forms:
            return

        # Collect all selected items from all selected forms
        all_selected_items = []
        for form_name in selected_forms:
            if form_name in self.report.selected_forms:
                form_items = self.report.selected_forms[
                    form_name
                ].get_selected_form_items()
                for item in form_items:
                    all_selected_items.append(f"{form_name}.{item}")

        for item in all_selected_items:
            self.ui.listWidget_form_item_selected.addItem(item)

    def click_select_form_item(self):
        """Select a form item from the available items and add it to the selected items."""
        selected_items = self.ui.listWidget_form_item_available.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            item_text = item.text()
            # Parse form name and item name from "form_name.item_name"
            if "." in item_text:
                form_name, item_name = item_text.split(".", 1)
                if form_name in self.report.selected_forms:
                    self.report.selected_forms[form_name].add_selected_form_item(
                        item_name
                    )

        # Update UI with hierarchical dependencies
        self.update_form_items_ui()

    def click_remove_form_item(self):
        """Remove a form item from the selected items."""
        selected_items = self.ui.listWidget_form_item_selected.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            item_text = item.text()
            # Parse form name and item name from "form_name.item_name"
            if "." in item_text:
                form_name, item_name = item_text.split(".", 1)
                if form_name in self.report.selected_forms:
                    self.report.selected_forms[form_name].add_available_form_item(
                        item_name
                    )

        # Update UI with hierarchical dependencies
        self.update_form_items_ui()

    def click_select_all_form_item(self):
        """Select all available form items and add them to the selected items."""
        selected_forms = self.report.get_selected_forms_list()

        for form_name in selected_forms:
            if form_name in self.report.selected_forms:
                available_items = self.report.selected_forms[
                    form_name
                ].get_available_form_items()
                for item in available_items[
                    :
                ]:  # Create a copy to avoid modification during iteration
                    self.report.selected_forms[form_name].add_selected_form_item(item)

        self.add_listWidget_form_item_available()
        self.add_listWidget_form_item_selected()
        # Update UI with hierarchical dependencies
        self.update_form_items_ui()

    def click_remove_all_form_item(self):
        """Remove all selected form items and add them back to the available items."""
        selected_forms = self.report.get_selected_forms_list()

        for form_name in selected_forms:
            if form_name in self.report.selected_forms:
                selected_items = self.report.selected_forms[
                    form_name
                ].get_selected_form_items()
                for item in selected_items[
                    :
                ]:  # Create a copy to avoid modification during iteration
                    self.report.selected_forms[form_name].add_available_form_item(item)

        self.add_listWidget_form_item_available()
        self.add_listWidget_form_item_selected()
        # Update UI with hierarchical dependencies
        self.update_form_items_ui()

    def update_rename_table(self):
        """Update the rename table with all selected items."""
        # Disconnect the signal temporarily to avoid triggering while setting up
        try:
            self.ui.tableWidget_rename.cellChanged.disconnect(
                self.on_rename_cell_changed
            )
        except:
            pass  # Signal might not be connected yet

        # Clear the table
        self.ui.tableWidget_rename.setRowCount(0)

        # Get the rename dictionary
        rename_dict = self.report.get_rename_dict()

        # Row counter
        row = 0

        # Add selected common items
        for item in self.report.get_selected_common_items():
            self.ui.tableWidget_rename.insertRow(row)

            # Original item name (not editable)
            orig_item = QTableWidgetItem(item)
            orig_item.setFlags(orig_item.flags() & ~Qt.ItemIsEditable)
            self.ui.tableWidget_rename.setItem(row, 0, orig_item)

            # New item name (editable)
            new_name = rename_dict.get(item, "")
            new_item = QTableWidgetItem(new_name)
            self.ui.tableWidget_rename.setItem(row, 1, new_item)

            row += 1

        # Add selected form items
        for form_name in self.report.get_selected_forms_list():
            form = self.report.selected_forms[form_name]
            for item in form.get_selected_form_items():
                # Create a combined name with form and item
                combined_name = f"{form_name}.{item}"

                self.ui.tableWidget_rename.insertRow(row)

                # Original item name (not editable)
                orig_item = QTableWidgetItem(combined_name)
                orig_item.setFlags(orig_item.flags() & ~Qt.ItemIsEditable)
                self.ui.tableWidget_rename.setItem(row, 0, orig_item)

                # New item name (editable)
                new_name = rename_dict.get(combined_name, "")
                new_item = QTableWidgetItem(new_name)
                self.ui.tableWidget_rename.setItem(row, 1, new_item)

                row += 1

        # Reconnect the signal
        self.ui.tableWidget_rename.cellChanged.connect(self.on_rename_cell_changed)

        # Adjust column widths after populating the table
        self._adjust_column_widths(self.ui.tableWidget_rename)

    def on_rename_cell_changed(self, row, column):
        """Handle changes to cells in the rename table."""
        # Only process changes to the "New Item Name" column (column 1)
        if column == 1:
            # Get the original item name and new item name
            orig_name = self.ui.tableWidget_rename.item(row, 0).text()
            new_name = self.ui.tableWidget_rename.item(row, 1).text()

            # Get the current rename dictionary
            rename_dict = self.report.get_rename_dict()

            # Update the dictionary with the new value, or remove if empty
            if new_name.strip():
                rename_dict[orig_name] = new_name
            elif orig_name in rename_dict:
                del rename_dict[orig_name]

            # Set the updated dictionary back to the report
            self.report.set_rename_dict(rename_dict)

    def update_selected_forms_table(self):
        """Update the table widget to display all selected forms."""
        # Clear the table
        self.ui.tableWidget_join.setRowCount(0)

        # Get selected forms from the report
        selected_forms = self.report.get_selected_forms_list()

        # Set the number of rows to match the number of selected forms
        self.ui.tableWidget_join.setRowCount(len(selected_forms))

        # Get join list data from report
        join_list = self.report.get_join_list()
        join_data = {}
        # Format the join data into a dictionary for easier access
        for i in range(0, len(join_list), 4):
            if i + 3 < len(join_list):
                form_name = join_list[i]
                join_data[form_name] = {
                    "items": join_list[i + 1],
                    "order": join_list[i + 2],
                    "how": join_list[i + 3],
                }

        # Populate the table with selected forms
        for row, form_name in enumerate(selected_forms):
            # Add form name to the first column ("Form Name")
            form_item = QTableWidgetItem(form_name)
            form_item.setFlags(form_item.flags() & ~Qt.ItemIsEditable)  # Make read-only
            self.ui.tableWidget_join.setItem(row, 0, form_item)

            # Add item dropdowns for columns 1-3 (Item 1, Item 2, Item 3)
            for col in range(1, 4):
                self._add_item_dropdown(row, col, form_name, join_data)

            # Add dropdown for "Join Order" column (column 4)
            join_order_combo = QComboBox()
            # Add options from 1 to the number of selected forms
            for i in range(1, len(selected_forms) + 1):
                join_order_combo.addItem(str(i))

            # Set value from join data if available
            default_order = row + 1
            if form_name in join_data and join_data[form_name]["order"]:
                default_order = join_data[form_name]["order"]
            join_order_combo.setCurrentText(str(default_order))

            # Connect signal to update join list when changed
            join_order_combo.currentTextChanged.connect(self.update_join_list)
            # Add new connection for graying out columns
            join_order_combo.currentTextChanged.connect(
                lambda value, r=row: self.on_join_order_changed(r, value)
            )

            # Set the combo box as a cell widget
            self.ui.tableWidget_join.setCellWidget(row, 4, join_order_combo)

            # Add dropdown for "Join type" column (column 5)
            join_type_combo = QComboBox()
            join_types = ["Left join", "Right join", "Inner join", "Outer join"]
            for join_type in join_types:
                join_type_combo.addItem(join_type)

            # Set value from join data if available
            default_join_type = "Left join"
            if form_name in join_data and join_data[form_name]["how"]:
                default_join_type = join_data[form_name]["how"]
            join_type_combo.setCurrentText(default_join_type)

            # Connect signal to update join list when changed
            join_type_combo.currentTextChanged.connect(self.update_join_list)

            # Set the combo box as a cell widget
            self.ui.tableWidget_join.setCellWidget(row, 5, join_type_combo)

            # Check if this row needs to be disabled initially
            if str(default_order) == "1":
                self.on_join_order_changed(row, "1")

        # Adjust column widths after populating the table
        self._adjust_column_widths(self.ui.tableWidget_join)

    def on_join_order_changed(self, row, value):
        """Handle changes to join order column and gray out columns if order is 1.

        Args:
            row: The row that changed
            value: The new join order value
        """
        # Get the widgets in columns 1-3 (join items) and 5 (join type)
        item_cols = [1, 2, 3]
        join_type_col = 5

        # Enable or disable based on join order value
        enabled = value != "1"

        # If the join order is 1, clear the values in the item and join type columns
        if value == "1":
            # Clear item dropdowns
            for col in item_cols:
                combo = self.ui.tableWidget_join.cellWidget(row, col)
                if combo:
                    combo.setCurrentIndex(0)  # Set to first item (usually empty)

            # Clear join type dropdown
            join_type_combo = self.ui.tableWidget_join.cellWidget(row, join_type_col)
            if join_type_combo:
                join_type_combo.setCurrentIndex(
                    0
                )  # Set to first item (usually "Left join")

            # Update the join list to reflect the cleared values
            self.update_join_list()

        # Update item dropdowns
        for col in item_cols:
            combo = self.ui.tableWidget_join.cellWidget(row, col)
            if combo:
                combo.setEnabled(enabled)

        # Update join type dropdown
        join_type_combo = self.ui.tableWidget_join.cellWidget(row, join_type_col)
        if join_type_combo:
            join_type_combo.setEnabled(enabled)

    def _add_item_dropdown(self, row, col, form_name, join_data):
        """Add an item dropdown to the specified cell in the join table."""
        combo = QComboBox()

        # Add a blank option first
        combo.addItem("")

        # Get all selected common items
        all_items = []

        # Add common items only (instead of all selected items)
        for item in self.report.get_selected_common_items():
            all_items.append(item)

        # Sort items and add to combo box
        all_items.sort()
        for item in all_items:
            combo.addItem(item)

        # Set value from join data if available
        if form_name in join_data and join_data[form_name]["items"]:
            items = join_data[form_name]["items"]
            item_idx = col - 1  # adjust for 0-based indexing

            # Check if there's an item for this column index in the items list
            if item_idx < len(items):
                # Set the selected item for this column
                combo.setCurrentText(items[item_idx])

        # Connect signal to update join list when changed
        combo.currentTextChanged.connect(self.update_join_list)

        # Set the combo box as a cell widget
        self.ui.tableWidget_join.setCellWidget(row, col, combo)

        # Check if this is a first join form (will be disabled later if so)
        join_order = 0
        if form_name in join_data and join_data[form_name]["order"]:
            join_order = join_data[form_name]["order"]
        if str(join_order) == "1":
            combo.setEnabled(False)

    def update_join_list(self):
        """Update the join list in the report based on the current table data."""
        join_list = []

        # Get the number of rows in the table
        row_count = self.ui.tableWidget_join.rowCount()

        for row in range(row_count):
            # Get form name from column 0
            form_name_item = self.ui.tableWidget_join.item(row, 0)
            if not form_name_item:
                continue
            form_name = form_name_item.text()

            # Get join items from columns 1-3
            join_items = []
            for col in range(1, 4):
                combo = self.ui.tableWidget_join.cellWidget(row, col)
                if combo:
                    item_text = combo.currentText()
                    # Always add the item text to preserve column positions
                    # (even if empty)
                    join_items.append(item_text)

            # Get join order from column 4
            join_order_combo = self.ui.tableWidget_join.cellWidget(row, 4)
            join_order = 1
            if join_order_combo:
                try:
                    join_order = int(join_order_combo.currentText())
                except ValueError:
                    pass

            # Get join type from column 5
            join_type_combo = self.ui.tableWidget_join.cellWidget(row, 5)
            join_type = "Left join"
            if join_type_combo:
                join_type = join_type_combo.currentText()

            # Add to join list
            join_list.append([form_name, join_items, join_order, join_type])

        # Update the report with the new join list
        self.report.update_join_list(join_list)

    def update_dynamic_filter_table(self):
        """Update the dynamic filter table based on selected items."""
        # Clear the table
        self.ui.tableWidget_dynamic_filter.setRowCount(0)

        # Get all dynamic filter items from the report
        filter_items = self.report.get_dynamic_filter_items()

        # Add each filter item to the table
        for item1, operator, item2 in filter_items:
            row = self.ui.tableWidget_dynamic_filter.rowCount()
            self.ui.tableWidget_dynamic_filter.insertRow(row)

            # Add item1 dropdown to first column
            self._add_dynamic_dropdown(row, 0, "item", item1)

            # Add operator dropdown to second column
            self._add_dynamic_dropdown(row, 1, "operator", operator)

            # Add item2 dropdown to third column
            self._add_dynamic_dropdown(row, 2, "item", item2)

        # Adjust column widths after populating the table
        self._adjust_column_widths(self.ui.tableWidget_dynamic_filter)

    def _add_dynamic_dropdown(self, row, column, dropdown_type, selected_value=None):
        """Add a dropdown to the dynamic filter table.

        Args:
            row: The row index
            column: The column index
            dropdown_type: Either "item" or "operator"
            selected_value: The value to select in the dropdown
        """
        # Create combo box
        combo = QComboBox()

        if dropdown_type == "item":
            # Get all selected items (common items and form items)
            all_items = []

            # Add common items
            for item in self.report.get_selected_common_items():
                all_items.append(item)

            # Add form items with form name prefix
            for form_name in self.report.get_selected_forms_list():
                form = self.report.selected_forms[form_name]
                for item in form.get_selected_form_items():
                    all_items.append(f"{form_name}.{item}")

            # Sort items and add to combo box
            all_items.sort()
            for item in all_items:
                combo.addItem(item)

        elif dropdown_type == "operator":
            # Add operator options - simpler options for comparing two fields
            operators = ["=", "!=", ">", ">=", "<", "<="]
            for op in operators:
                combo.addItem(op)

        # Set selected value if provided
        if selected_value:
            combo.setCurrentText(selected_value)

        # Connect signal to update the filter items when changed
        combo.currentTextChanged.connect(lambda: self._on_dynamic_filter_changed(row))

        # Add to table
        self.ui.tableWidget_dynamic_filter.setCellWidget(row, column, combo)

    def dynamic_filter_add(self):
        """Add a new row to the dynamic filter table."""
        # Add a new row
        row = self.ui.tableWidget_dynamic_filter.rowCount()
        self.ui.tableWidget_dynamic_filter.insertRow(row)

        # Add item1 dropdown to first column
        self._add_dynamic_dropdown(row, 0, "item")

        # Add operator dropdown to second column
        self._add_dynamic_dropdown(row, 1, "operator", "=")  # Default to equals

        # Add item2 dropdown to third column
        self._add_dynamic_dropdown(row, 2, "item")

    def dynamic_filter_remove(self):
        """Remove selected rows from the dynamic filter table."""
        # Get current selection
        selected_rows = set()

        # First try normal selection
        for item in self.ui.tableWidget_dynamic_filter.selectedItems():
            selected_rows.add(item.row())

        # If no rows selected, check current row
        if not selected_rows:
            current_row = self.ui.tableWidget_dynamic_filter.currentRow()
            if current_row >= 0:
                selected_rows.add(current_row)

        # If still no rows selected, show message and return
        if not selected_rows:
            print("No rows selected for removal")
            return

        # Remove rows in reverse order to avoid index shifting
        for row in sorted(selected_rows, reverse=True):
            # Get the filter details before removing
            item1_combo = self.ui.tableWidget_dynamic_filter.cellWidget(row, 0)
            operator_combo = self.ui.tableWidget_dynamic_filter.cellWidget(row, 1)
            item2_combo = self.ui.tableWidget_dynamic_filter.cellWidget(row, 2)

            if item1_combo and operator_combo and item2_combo:
                item1 = item1_combo.currentText()
                operator = operator_combo.currentText()
                item2 = item2_combo.currentText()

                # Remove from report
                self.report.remove_dynamic_filter_item(item1, operator, item2)
                print(f"Removed filter: {item1} {operator} {item2}")

            # Remove row from table
            self.ui.tableWidget_dynamic_filter.removeRow(row)
            print(f"Removed row {row} from table")

        # Update dependent UI elements
        self.update_items_dependent_ui()

    def _on_dynamic_filter_changed(self, row):
        """Handle changes to any part of a dynamic filter row.

        Args:
            row: The row that changed
        """
        # Get the current values from the row
        item1_combo = self.ui.tableWidget_dynamic_filter.cellWidget(row, 0)
        operator_combo = self.ui.tableWidget_dynamic_filter.cellWidget(row, 1)
        item2_combo = self.ui.tableWidget_dynamic_filter.cellWidget(row, 2)

        if item1_combo and operator_combo and item2_combo:
            item1 = item1_combo.currentText()
            operator = operator_combo.currentText()
            item2 = item2_combo.currentText()

            # Update the dynamic filter items in the report
            # First remove any existing filter for this row
            for i, (old_item1, old_operator, old_item2) in enumerate(
                self.report.get_dynamic_filter_items()
            ):
                if i == row:  # Same row position
                    self.report.remove_dynamic_filter_item(
                        old_item1, old_operator, old_item2
                    )
                    break

            # Add the updated filter if both items are selected
            if item1 and item2:
                self.report.add_dynamic_filter_item(item1, operator, item2)

    # Add tab change handler
    def on_tab_changed(self, index):
        """Handle tab changes and perform actions based on the selected tab."""
        tab_text = self.ui.tabWidget.tabText(index)
        if tab_text == "Pre-view and Run":
            self.preview_report()

    # Add PandasModel class for displaying DataFrames in QTableView
    class PandasModel(QAbstractTableModel):
        """Model for displaying pandas DataFrames in QTableView."""

        def __init__(self, data):
            super().__init__()
            self._data = data

        def rowCount(self, parent=None):
            return len(self._data)

        def columnCount(self, parent=None):
            return len(self._data.columns)

        def data(self, index, role=Qt.DisplayRole):
            if not index.isValid():
                return None

            if role == Qt.DisplayRole:
                value = self._data.iloc[index.row(), index.column()]

                # Handle null values
                if pd.isna(value):
                    return ""

                # Format datetime objects to m/d/yyyy without leading zeros
                if isinstance(value, (pd.Timestamp, datetime, np.datetime64)):
                    date = pd.Timestamp(value)
                    return f"{date.month}/{date.day}/{date.year}"

                # Handle numeric values - display integers without decimal point
                if isinstance(value, (float, np.floating)):
                    # Check if the float has no decimal part
                    if value == int(value):
                        return str(int(value))

                # Convert other values to string
                return str(value)

            return None

        def headerData(self, section, orientation, role=Qt.DisplayRole):
            if role == Qt.DisplayRole:
                if orientation == Qt.Horizontal:
                    return str(self._data.columns[section])
                # Return row number for vertical headers
                elif orientation == Qt.Vertical:
                    return str(section + 1)  # Add 1 to make it 1-based indexing
            return None

    def preview_report(self):
        """Generate a preview of the report and display it in the table view."""
        try:
            # Show status in confirmation label
            self.ui.label_confirmation.setText("Generating preview...")

            # Call create_report to generate the report
            result_df = self.report.create_report()

            if result_df is not None and not result_df.empty:
                # Reset the index to ensure row numbers are sequential after filtering
                result_df = result_df.reset_index(drop=True)

                # Create model from the DataFrame
                model = self.PandasModel(result_df)

                # Set the model for the table view
                self.ui.tableView_preview.setModel(model)

                # Show the vertical header (row numbers)
                self.ui.tableView_preview.verticalHeader().setVisible(True)

                # Resize columns to content
                self.ui.tableView_preview.resizeColumnsToContents()

                # Update confirmation label with success message
                self.ui.label_confirmation.setText(
                    f"Preview generated successfully. Found {len(result_df)} rows with {len(result_df.columns)} columns."
                )
            else:
                # Handle empty result
                self.ui.label_confirmation.setText(
                    "No data found. Please check your form selections, filters, and join settings."
                )
                # Clear the table view
                self.ui.tableView_preview.setModel(None)
        except Exception as e:
            # Handle errors
            import traceback

            error_details = traceback.format_exc()
            print(f"Error generating preview: {error_details}")
            self.ui.label_confirmation.setText(f"Error generating preview: {str(e)}")
            # Clear the table view
            self.ui.tableView_preview.setModel(None)

    # Update the Run and Save button handler to also run the report
    def click_run_and_save(self):
        """Run the report and save the results to a file."""
        try:
            # Generate the report
            result_df = self.report.create_report()

            if result_df is not None and not result_df.empty:
                # Get the file name
                file_name = self.ui.lineEdit_file_name.text()
                # Add timestamp before extension
                timestamp = datetime.now().strftime(" %y%m%d_%H%M%S")
                file_name += timestamp
                if not file_name.endswith(".xlsx"):
                    file_name += ".xlsx"

                # Get the output folder
                if self.output_folder_name:
                    file_path = os.path.join(self.output_folder_name, file_name)

                    # Create a copy of the dataframe for export
                    export_df = result_df.copy()

                    # First handle datetime columns - format to m/d/yyyy without leading zeros
                    for col in export_df.select_dtypes(
                        include=["datetime64", "datetime", np.datetime64]
                    ).columns:
                        # Convert to string format without leading zeros
                        export_df[col] = export_df[col].apply(
                            lambda x: f"{x.month}/{x.day}/{x.year}"
                            if pd.notnull(x)
                            else ""
                        )

                    # Use simple pandas Excel export without xlsxwriter formatting
                    export_df.to_excel(file_path, index=False, sheet_name="Report")

                    # Update confirmation label
                    self.ui.label_confirmation.setText(
                        f"Report saved successfully to {file_path}"
                    )

                    # Save settings if requested
                    if self.ui.checkBox_save_current_setting.isChecked():
                        settings_name = self.ui.lineEdit_setting_name.text()
                        if settings_name:
                            settings_path = os.path.join(
                                self.output_folder_name, f"{settings_name}.json"
                            )
                            self.report.save_setting_to_json(settings_path)
                            self.ui.label_confirmation.setText(
                                f"{self.ui.label_confirmation.text()}\nSettings saved to {settings_path}"
                            )
                else:
                    self.ui.label_confirmation.setText(
                        "Please select an output folder first."
                    )
            else:
                self.ui.label_confirmation.setText(
                    "No data to save. Please check your selections and filters."
                )
        except Exception as e:
            import traceback

            print(f"Error details: {traceback.format_exc()}")
            self.ui.label_confirmation.setText(f"Error saving report: {str(e)}")

    def update_items_order_list(self):
        """Update the items order list widget with all selected items in their current order."""
        # Make sure the order list in report is up to date
        self.report.update_selected_items_order_list()

        # Clear the list widget
        self.ui.listWidget_items_order.clear()

        # Get the current order list from the report
        order_list = self.report.get_selected_items_order_list()

        # Add all items to the list widget in their order
        for item in order_list:
            self.ui.listWidget_items_order.addItem(item)

    def click_order_up(self):
        """Move the selected item up in the order list."""
        # Get the current selected item
        current_row = self.ui.listWidget_items_order.currentRow()
        if current_row <= 0:
            return  # Already at the top or nothing selected

        # Get the item from the list widget
        item = self.ui.listWidget_items_order.takeItem(current_row)
        if not item:
            return

        # Insert it one position up
        self.ui.listWidget_items_order.insertItem(current_row - 1, item)

        # Select the moved item
        self.ui.listWidget_items_order.setCurrentRow(current_row - 1)

        # Update the order list in the report
        self.update_report_order_list_from_widget()

    def click_order_down(self):
        """Move the selected item down in the order list."""
        # Get the current selected item
        current_row = self.ui.listWidget_items_order.currentRow()
        if current_row < 0 or current_row >= self.ui.listWidget_items_order.count() - 1:
            return  # Nothing selected or already at the bottom

        # Get the item from the list widget
        item = self.ui.listWidget_items_order.takeItem(current_row)
        if not item:
            return

        # Insert it one position down
        self.ui.listWidget_items_order.insertItem(current_row + 1, item)

        # Select the moved item
        self.ui.listWidget_items_order.setCurrentRow(current_row + 1)

        # Update the order list in the report
        self.update_report_order_list_from_widget()

    def update_report_order_list_from_widget(self):
        """Update the report's order list from the current order in the widget."""
        # Create a new order list from the widget items
        new_order = []
        for i in range(self.ui.listWidget_items_order.count()):
            item = self.ui.listWidget_items_order.item(i)
            if item:
                new_order.append(item.text())

        # Set the new order in the report
        self.report.set_selected_items_order_list(new_order)

    def on_form_item_available_double_clicked(self, item):
        """Handle double-click on an available form item - select the item."""
        # Select the item that was double-clicked
        self.ui.listWidget_form_item_available.setCurrentItem(item)
        # Call the same function that the select button uses
        self.click_select_form_item()

    def on_form_item_selected_double_clicked(self, item):
        """Handle double-click on a selected form item - remove the item."""
        # Select the item that was double-clicked
        self.ui.listWidget_form_item_selected.setCurrentItem(item)
        # Call the same function that the remove button uses
        self.click_remove_form_item()

    def on_common_item_available_double_clicked(self, item):
        """Handle double-click on an available common item - select the item."""
        # Select the item that was double-clicked
        self.ui.listWidget_common_item_available.setCurrentItem(item)
        # Call the same function that the select button uses
        self.click_select_common_item()

    def on_common_item_selected_double_clicked(self, item):
        """Handle double-click on a selected common item - remove the item."""
        # Select the item that was double-clicked
        self.ui.listWidget_common_item_selected.setCurrentItem(item)
        # Call the same function that the remove button uses
        self.click_remove_common_item()

    def on_form_available_double_clicked(self, item):
        """Handle double-click on an available form - select the form."""
        # Select the item that was double-clicked
        self.ui.listWidget_form_available.setCurrentItem(item)
        # Call the same function that the select button uses
        self.click_select_form()

    def on_form_selected_double_clicked(self, item):
        """Handle double-click on a selected form - remove the form."""
        # Select the item that was double-clicked
        self.ui.listWidget_form_selected.setCurrentItem(item)
        # Call the same function that the remove button uses
        self.click_remove_form()

    def _setup_tables(self):
        """Set up all table widgets with proper column widths and behaviors."""
        # Set up table widget properties
        tables = [
            self.ui.tableWidget_join,
            self.ui.tableWidget_static_filter,
            self.ui.tableWidget_dynamic_filter,
            self.ui.tableWidget_rename,
        ]

        for table in tables:
            # Set selection behavior
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setSelectionMode(QAbstractItemView.SingleSelection)

            # Make columns fit evenly
            self._adjust_column_widths(table)

            # Connect to resizing events
            table.horizontalHeader().sectionResized.connect(
                lambda index, oldSize, newSize, t=table: self._adjust_column_widths(t)
            )

    def _adjust_column_widths(self, table):
        """Adjust column widths to fit evenly in the table."""
        if table.columnCount() == 0:
            return

        # Get available width
        available_width = table.width()

        # Account for vertical header width (row indices)
        if not table.verticalHeader().isHidden():
            available_width -= table.verticalHeader().width()

        # Account for frame width (borders)
        available_width -= 20

        # If vertical scrollbar is visible, adjust width
        if table.verticalScrollBar().isVisible():
            available_width -= table.verticalScrollBar().width()

        # Account for potential grid line widths
        if table.showGrid():
            available_width -= table.columnCount() * 2

        # Calculate column width, ensure it's at least 50 pixels
        column_width = max(50, available_width // table.columnCount())

        # Set each column to the same width
        for col in range(table.columnCount()):
            table.setColumnWidth(col, column_width)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = Widget()
    widget.show()
    sys.exit(app.exec())
    widget = Widget()
    widget.show()
    sys.exit(app.exec())
