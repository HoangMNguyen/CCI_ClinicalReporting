"""What a Clinical Reporting report is made of: :class:`CLReport`.

A report holds a study's forms, the forms and items chosen from them, how the
forms join (the common items each joins on, the join order and the join
type), the filters and comparisons, and the column order and names. Its
stacked forms (:mod:`clinical_reporting.stacking`) and then its coalesced
items (:mod:`clinical_reporting.coalescing`) are built with its data, so they
are forms and items like any other. It turns into a saved setting and back
(:meth:`CLReport.settings_to_dict`, :meth:`CLReport.load_setting_from_dict`),
and :meth:`CLReport.create_report` hands the building of the table to
:class:`clinical_reporting.pipeline.ReportEngine`.
"""

import logging
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from clinical_reporting import coalescing, report_columns, stacking
from clinical_reporting.models import (
    SUBJECT_COLUMN,
    CLForm,
    JoinHow,
    common_items,
    is_qualified,
    move_item,
    qualify,
    split_qualified,
)

if TYPE_CHECKING:
    from clinical_reporting.validation import ReportValidationIssue

logger = logging.getLogger(__name__)


class CLReport:
    """A class to represent a report that contains multiple forms and columns."""

    def __init__(self):
        self.study_name = None
        self.data = {}
        # The forms as loaded (the Corelisting ZIP and additional inputs);
        # ``stacked_data`` is these plus the stacked forms built from them,
        # and ``data`` is those with the coalesced items made over them.
        self.loaded_data = {}
        self.stacked_data = {}
        # The stacked forms and coalesced items applied to the report, and
        # what building them last gave (stacking.build_all,
        # coalescing.build_all).
        self.stacked_forms: List[stacking.StackedForm] = []
        self.stacked_build = stacking.Built()
        self.coalesced_items: List[coalescing.CoalescedItem] = []
        self.coalesced_build = coalescing.Built()
        self.available_forms = {}
        self.selected_forms = {}
        self.available_common_items = []
        self.selected_common_items = []
        self.new_items = []
        self.rename_dict = {}
        self.static_available_common_items = []  # Initialize as empty, will be populated dynamically
        self.static_filter_items = []  # Filters: Item Name, Operator, Value
        self.dynamic_filter_items = []  # Comparisons: Item Name 1, Operator, Item Name 2
        self.selected_items_order_list = []
        # True once the user rearranged items on the Order & rename page. Until
        # then the order list is re-derived from the default layout (common
        # items first, then form items grouped by join order).
        self.order_list_customized = False
        # Renames and filters whose items are currently deselected (or whose
        # FORM.item column went because the form now joins on that common
        # item). They are kept out of validation, execution, and saved
        # settings, and restored by ``sync_with_selection`` once their items
        # are back.
        self._inactive_rename_dict = {}
        self._inactive_static_filters = []
        self._inactive_dynamic_filters = []

    def set_study_name(self, study_name: str):
        """Set the study name for the report."""
        self.study_name = study_name

    def identify_common_items(self):
        """Identify columns that exist in all forms of the data."""
        if not self.data:
            return

        # Update static_available_common_items with the common columns
        self.static_available_common_items = common_items(self.data)

        if SUBJECT_COLUMN in self.static_available_common_items:
            # Move "Subject" to the front of the list
            self.set_common_item_state(SUBJECT_COLUMN, selected=True)

    def set_data(self, data: dict):
        """Set the data for the report: the forms as loaded.

        The report's stacked forms are built from them and added, then its
        coalesced items are made over those forms, giving ``data``;
        ``loaded_data`` keeps the forms as loaded and ``stacked_data`` the
        forms before coalescing.
        """
        self.loaded_data = data
        self.stacked_build = stacking.build_all(self.stacked_forms, data)
        self.stacked_data = (
            {**data, **self.stacked_build.forms} if self.stacked_build.forms else data
        )
        self.coalesced_build = coalescing.build_all(
            self.coalesced_items, self.stacked_data
        )
        self.data = (
            {**self.stacked_data, **self.coalesced_build.forms}
            if self.coalesced_build.forms
            else self.stacked_data
        )

        # Reset form collections to match the new dataset.
        self.remove_all_available_forms()
        self.remove_all_selected_forms()

        # Identify common columns across all forms
        self.identify_common_items()

        # by default, all forms are available.
        # for each form in data, create a CLForm object
        self.add_all_available_forms()

        # by default, all common items are available.
        self.add_all_available_common_items()

    def set_stacked_forms(self, stacked_forms) -> None:
        """Apply these stacked forms, rebuilding the data when some is loaded.

        Rebuilding resets the selections, as :meth:`set_data` does; see
        :func:`clinical_reporting.session.apply_stacked_forms` to keep them.
        """
        self.stacked_forms = list(stacked_forms)
        if self.loaded_data:
            self.set_data(self.loaded_data)

    def set_coalesced_items(self, coalesced_items) -> None:
        """Apply these coalesced items, rebuilding the data when some is loaded.

        Rebuilding resets the selections, as :meth:`set_data` does; see
        :func:`clinical_reporting.session.apply_coalesced_items` to keep them.
        """
        self.coalesced_items = list(coalesced_items)
        if self.loaded_data:
            self.set_data(self.loaded_data)

    def add_available_form(self, form: str):
        """Add the available form to the available forms dictionary."""
        self.available_forms[form] = CLForm(form)
        self.remove_selected_form(form)

    def add_all_available_forms(self):
        """Add all available forms from the data to the available forms dictionary."""
        for form_name in self.data.keys():
            self.add_available_form(form_name)

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
            new_form = CLForm(form)
            # Remember the input file order of the form's own (non-common)
            # columns so the item lists keep that order from here on.
            new_form.column_order = self._own_columns(
                form, self.static_available_common_items
            )
            for item in new_form.column_order:
                new_form.set_form_item_state(item, selected=False)
            self.selected_forms[form] = new_form
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

    def get_available_common_items(self):
        """Get the list of available common items."""
        return self.available_common_items

    def set_common_item_state(self, item: str, *, selected: bool) -> bool:
        """Ensure ``item`` only exists in one of the common item collections.

        Both collections are kept in the original input column order
        (``static_available_common_items``) regardless of the order in which
        items are (de)selected.
        """

        source, target = (
            (self.available_common_items, self.selected_common_items)
            if selected
            else (self.selected_common_items, self.available_common_items)
        )
        return move_item(item, source, target, self.static_available_common_items)

    def get_selected_common_items(self):
        """Get the list of selected common items."""
        return self.selected_common_items

    def get_rename_dict(self):
        """Get the rename dictionary for the report."""
        return self.rename_dict

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

    def get_selected_items_order_list(self):
        """Get the ordered list of selected items."""
        return self.selected_items_order_list

    def set_selected_items_order_list(self, order_list: list):
        """Set the ordered list of selected items.

        Called when the user rearranges items on the Order & rename page, so the
        arrangement is treated as manual from here on and no longer re-derived
        from the default (join-order based) layout.
        """
        self.selected_items_order_list = order_list
        self.order_list_customized = True

    def update_selected_items_order_list(self):
        """Update the selected items order list with all currently selected items.

        The default layout is: selected common items first (leftmost, in input
        column order), followed by each form's columns grouped by join (merge)
        order: the common items it doesn't join on, then its selected items
        (:func:`clinical_reporting.report_columns.output_identifiers`, the
        columns the engine puts out). This default is re-derived on every call
        — changing a form's join order re-groups the list — until the user
        rearranges items on the Order & rename page (``order_list_customized``).
        From then on the manual arrangement is preserved and new columns are
        inserted at their default position (next to their form's other
        columns) rather than appended.
        """
        # Canonical default order: common items, then each form's columns.
        canonical_order = report_columns.output_identifiers(self)

        canonical_set = set(canonical_order)

        new_order_list: List[str] = []
        if self.order_list_customized:
            # Keep the user's arrangement for items still selected; once none
            # of it survives there is nothing manual left to preserve.
            new_order_list = [
                item for item in self.selected_items_order_list if item in canonical_set
            ]
            if not new_order_list:
                self.order_list_customized = False

        if not self.order_list_customized:
            self.selected_items_order_list = canonical_order
            return self.selected_items_order_list

        placed = set(new_order_list)

        common = set(self.selected_common_items)

        def form_of(identifier: str) -> Optional[str]:
            # FORM.item (form names have no "."); common items have no form.
            return None if identifier in common else split_qualified(identifier)[0]

        # Insert each new item where it goes by default, so common items stay
        # leftmost and a form's columns stay together: right after the column
        # before it when that is its form's; else just before the first placed
        # column of its form that follows (past others of its form that are
        # new too); else right after the column before it.
        for index, item in enumerate(canonical_order):
            if item in placed:
                continue
            form = form_of(item)
            previous = canonical_order[index - 1] if index else None
            position = None
            if form is not None and previous is not None and form_of(previous) == form:
                position = new_order_list.index(previous) + 1
            elif form is not None:
                for later in canonical_order[index + 1 :]:
                    if form_of(later) != form:
                        break
                    if later in placed:
                        position = new_order_list.index(later)
                        break
            if position is None:
                position = 0 if previous is None else new_order_list.index(previous) + 1
            new_order_list.insert(position, item)
            placed.add(item)

        # Update the order list
        self.selected_items_order_list = new_order_list

        return self.selected_items_order_list

    @staticmethod
    def _deserialize_form(form_name: str, data: Dict[str, Any]) -> CLForm:
        """Recreate a CLForm instance from persisted data."""

        form = CLForm(data.get("name", form_name))
        form.available_form_items = deepcopy(data.get("available_form_items", []))
        form.selected_form_items = deepcopy(data.get("selected_form_items", []))
        form.join_items = list(data.get("join_items") or [])
        form.join_order = data.get("join_order")
        form.join_how = data.get("join_how")
        return form

    def _own_columns(self, form_name: str, common) -> List[str]:
        """The columns of *form_name* that aren't in *common*, in input file order."""
        return [
            column for column in self.data[form_name].columns if column not in common
        ]

    def settings_to_dict(self, setting_name: Optional[str] = None) -> Dict[str, Any]:
        """Return the saved-settings dictionary for this report, without file I/O.

        Only selected forms/items and user-configured settings are included.
        Available items and unselected forms are left out because they are
        derived from the input data and rebuilt when the settings are loaded.
        The result holds no local file paths, so it can be stored anywhere.

        This first calls :meth:`sync_with_selection`, which changes the report:
        renames and filters for deselected items are set aside and the order
        list is trimmed, exactly as when the user deselects them.
        """

        # Never persist renames or filters for deselected forms/items.
        self.sync_with_selection()

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
            "rename_dict": deepcopy(self.rename_dict),
            "static_filter_items": [list(item) for item in self.static_filter_items],
            "dynamic_filter_items": [list(item) for item in self.dynamic_filter_items],
            "selected_items_order_list": deepcopy(self.selected_items_order_list),
            "order_list_customized": self.order_list_customized,
        }
        # Only when there are stacked forms or coalesced items, so other
        # settings save as before.
        stacking.to_settings(settings, self.stacked_forms)
        return coalescing.to_settings(settings, self.coalesced_items)

    def load_setting_from_dict(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Apply an in-memory settings dictionary to this report.

        It performs no I/O, so any program that builds the settings schema can
        drive it; :func:`~clinical_reporting.session.apply_saved_setting` also
        lines the setting up with the report's data, as the desktop does.

        The setting's stacked forms and coalesced items come first: when they
        differ from the report's, the data is rebuilt (resetting the
        selections) before the setting's selections are read, so those on a
        stacked form or a coalesced item find it.
        """

        stacked_forms = stacking.from_settings(settings)
        coalesced_items = coalescing.from_settings(settings)
        if (
            stacked_forms != self.stacked_forms
            or coalesced_items != self.coalesced_items
        ):
            self.stacked_forms = stacked_forms
            self.coalesced_items = coalesced_items
            if self.loaded_data:
                self.set_data(self.loaded_data)

        self.study_name = settings.get("study_name", self.study_name)

        # Only selected forms are persisted; available forms are reconstructed later
        selected_forms_data = settings.get("selected_forms", {})
        self.selected_forms = {
            name: self._deserialize_form(name, form_data)
            for name, form_data in selected_forms_data.items()
        }

        # Only selected common items are persisted; available/common pools are reconstructed later
        self.selected_common_items = list(settings.get("selected_common_items", []))
        self.new_items = list(settings.get("new_items", []))
        self.rename_dict = dict(settings.get("rename_dict", {}))
        # A newly loaded setting replaces anything parked from the previous one.
        self._inactive_rename_dict = {}
        self._inactive_static_filters = []
        self._inactive_dynamic_filters = []

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

        saved_order = settings.get("selected_items_order_list")
        # Settings saved before the flag existed carry a hand-tuned order, so a
        # non-empty saved list defaults to "customized" and replays exactly.
        customized = bool(settings.get("order_list_customized", bool(saved_order)))
        # A column order kept in "order_list" (no current version writes one)
        # is the setting's own arrangement unless its saved order counts as
        # customized (above).
        legacy_order = list(settings.get("order_list") or [])
        if legacy_order and not customized:
            self.selected_items_order_list = legacy_order
            self.order_list_customized = True
        else:
            self.order_list_customized = customized
            if saved_order is not None:
                self.selected_items_order_list = list(saved_order)
            else:
                self.update_selected_items_order_list()

        return settings

    def reconcile_with_current_data(self) -> Dict[str, list[str]]:
        """Align loaded settings with the currently available study data.

        Returns the forms and items the setting needs that the data lacks,
        including the members any stacked form is missing, built or not (as
        forms; one named like a loaded form isn't built and records none),
        the matched items a present member of a built one no longer has (as
        ``MEMBER.item``), and the forms and items its coalesced items lack
        (as forms and ``FORM.item``).
        """

        missing_forms: set[str] = set()
        missing_items: set[str] = set()

        data_forms = set(self.data.keys())

        # Determine the true common items from the loaded data (input column order).
        actual_common_items = common_items(self.data)
        common_lookup = set(actual_common_items)

        self.static_available_common_items = list(actual_common_items)

        for item in list(self.selected_common_items):
            if item not in common_lookup:
                self.selected_common_items.remove(item)
                missing_items.add(item)

        # Keep both pools in the input column order.
        selected_lookup = set(self.selected_common_items)
        self.selected_common_items = [
            item for item in actual_common_items if item in selected_lookup
        ]
        self.available_common_items = [
            item for item in actual_common_items if item not in selected_lookup
        ]

        valid_selected_forms: dict[str, CLForm] = {}
        for form_name, form in list(self.selected_forms.items()):
            if form_name not in data_forms:
                missing_forms.add(form_name)
                continue

            # The form's own columns, in input file order.
            form.column_order = self._own_columns(form_name, common_lookup)

            for item in list(form.get_selected_form_items()):
                if item not in form.column_order:
                    form.remove_form_item(item)
                    missing_items.add(qualify(form_name, item))

            selected_items = set(form.get_selected_form_items())
            form.selected_form_items = [
                column for column in form.column_order if column in selected_items
            ]
            form.available_form_items = [
                column for column in form.column_order if column not in selected_items
            ]
            valid_selected_forms[form_name] = form

        self.selected_forms = valid_selected_forms

        valid_selected_form_names = set(self.selected_forms.keys())
        self.available_forms = {}
        for form_name in self.data.keys():
            if form_name in valid_selected_form_names:
                continue
            new_form = CLForm(form_name)
            new_form.column_order = self._own_columns(form_name, common_lookup)
            new_form.available_form_items = list(new_form.column_order)
            self.available_forms[form_name] = new_form

        # Build a set of valid identifiers for filters and ordering.
        valid_identifiers = self._active_identifiers(include_unqualified=True)

        self.selected_items_order_list = [
            item for item in self.selected_items_order_list if item in valid_identifiers
        ]
        self.rename_dict = {
            key: value
            for key, value in self.rename_dict.items()
            if key in valid_identifiers
        }

        self.static_filter_items = [
            item
            for item in self.static_filter_items
            if item and item[0] in valid_identifiers
        ]
        self.dynamic_filter_items = [
            item
            for item in self.dynamic_filter_items
            if item and item[0] in valid_identifiers and item[2] in valid_identifiers
        ]

        built = self.stacked_build
        for members in built.missing_members.values():
            missing_forms.update(members)
        for name in built.forms:
            missing_items.update(
                qualify(member, item)
                for member, item in built.missing_items.get(name, ())
            )
            # A matched item a member replaced with another of the match's
            # items is missing all the same: the setting saved the other one.
            missing_items.update(
                qualify(member, item)
                for member, item, _used in built.replaced.get(name, ())
            )

        coalesced = self.coalesced_build
        missing_forms.update(coalesced.missing_forms)
        for position, items in coalesced.missing_items.items():
            form = self.coalesced_items[position].form
            missing_items.update(qualify(form, item) for item in items)

        return {
            "forms": sorted(missing_forms),
            "items": sorted(missing_items),
        }

    def _active_identifiers(self, *, include_unqualified: bool) -> set[str]:
        """Return the report's output columns (renames, filters and order use them).

        The selected common items and, as qualified ``form.item`` names, each
        form's selected items and a later form's copy of a common item it
        doesn't join on (:func:`clinical_reporting.report_columns.output_identifiers`).
        With ``include_unqualified`` the bare form item names are added too,
        since filters may reference a form item without its form prefix.
        """
        identifiers = set(report_columns.output_identifiers(self))
        if include_unqualified:
            for form in self.selected_forms.values():
                identifiers.update(form.get_selected_form_items())
        return identifiers

    @staticmethod
    def _partition_filters(
        active: list, parked: list, identifiers: set[str], operand_indexes: tuple
    ):
        """Split ``active`` + ``parked`` filters by whether all operands are selected.

        Parked filters that duplicate an active one are dropped. Malformed
        entries are left active so validation still reports them.
        """
        active_keys = {
            tuple(item) for item in active if isinstance(item, (list, tuple))
        }
        merged = list(active) + [
            item for item in parked if tuple(item) not in active_keys
        ]

        still_active, inactive = [], []
        for item in merged:
            well_formed = isinstance(item, (list, tuple)) and len(item) == 3
            if well_formed and not all(
                item[index] in identifiers for index in operand_indexes
            ):
                inactive.append(item)
            else:
                still_active.append(item)
        return still_active, inactive

    def sync_with_selection(self) -> None:
        """Align renames, filters, and ordering with the current selection.

        Renames and filters that reference a column the report no longer has
        (a deselected form, form item, or common item, or a form's copy of a
        common item it now joins on) are parked: they are excluded from
        validation, report execution, and saved settings, but restored here
        once their columns are back. An active rename always wins over a parked
        one for the same item. The order list is simply pruned, since a column
        that comes back is re-inserted at its default position. Safe to call
        repeatedly.

        The join setters below call this themselves, since joins decide which
        ``FORM.item`` columns exist; after selection changes the caller does
        (the window's ``update_items_dependent_ui``).
        """
        selected = self._active_identifiers(include_unqualified=False)
        filterable = self._active_identifiers(include_unqualified=True)

        renames = {**self._inactive_rename_dict, **self.rename_dict}
        self.rename_dict = {
            key: value for key, value in renames.items() if key in selected
        }
        self._inactive_rename_dict = {
            key: value for key, value in renames.items() if key not in selected
        }

        self.static_filter_items, self._inactive_static_filters = (
            self._partition_filters(
                self.static_filter_items,
                self._inactive_static_filters,
                filterable,
                (0,),
            )
        )
        self.dynamic_filter_items, self._inactive_dynamic_filters = (
            self._partition_filters(
                self.dynamic_filter_items,
                self._inactive_dynamic_filters,
                filterable,
                (0, 2),
            )
        )

        self.selected_items_order_list = [
            item for item in self.selected_items_order_list if item in selected
        ]

    def get_join_list_dict(self) -> Dict[str, Dict[str, Any]]:
        """The join settings of each selected form, keyed by form name.

        Each entry holds the common items the form joins on (``items``), its
        join order (``order``) and its join type (``how``).
        """

        join_data: Dict[str, Dict[str, Any]] = {}
        for form_name, form in self.selected_forms.items():
            join_data[form_name] = {
                "items": list(form.get_join_items()),
                "order": form.get_join_order(),
                "how": form.get_join_how(),
            }
        return join_data

    # The common items a form joins on decide which of them it puts out as
    # FORM.item (clinical_reporting.report_columns), so every join change
    # re-syncs renames, filters and the column order with the columns that now
    # exist (sync_with_selection). Change several forms' joins with one
    # update_join_list call: a column that is gone between two calls loses
    # its place in a customized order.

    def _set_join(self, form: str, items: list, order: int, how: str) -> None:
        if form in self.selected_forms.keys():
            self.selected_forms[form].set_join_items(items)
            self.selected_forms[form].set_join_order(order)
            self.selected_forms[form].set_join_how(how)

    def update_join_items(self, form: str, items: list, order: int, how: str):
        """Update the join items for a form, then re-sync (see above)."""
        self._set_join(form, items, order, how)
        self.sync_with_selection()

    def update_join_list(self, join_list: list):
        """Update several forms' joins, then re-sync once (see above)."""
        for form, items, order, how in join_list:
            self._set_join(form, items, order, how)
        self.sync_with_selection()

    def normalize_joins(self) -> None:
        """Tidy every selected form's joins with one rule, then re-sync once.

        The join order is clamped to 1..N (N selected forms; anything that
        isn't a number counts as 1). A form at order 1 joins on nothing, with
        a left join. Every other form keeps at most three join items, taken
        from its first three, that are selected common items, each once; an
        unknown join type becomes a left join. The desktop's join table shows
        and keeps this whenever it is rebuilt (a selection change or a loaded
        setting).
        """
        last = max(1, len(self.selected_forms))
        common = set(self.selected_common_items)
        for form_name, form in self.selected_forms.items():
            try:
                order = int(form.get_join_order() or 1)
            except TypeError, ValueError, OverflowError:
                order = 1
            order = min(max(1, order), last)
            if order == 1:
                self._set_join(form_name, [], 1, JoinHow.LEFT)
                continue
            items: list[str] = []
            for item in form.get_join_items()[:3]:
                if item in common and item not in items:
                    items.append(item)
            how = form.get_join_how()
            self._set_join(
                form_name, items, order, how if how in JoinHow.ALL else JoinHow.LEFT
            )
        self.sync_with_selection()

    def get_static_filter_items(self):
        """Get the list of filters."""
        return self.static_filter_items

    def add_static_filter_item(self, item: str, operator: str, value: str):
        """Add a filter."""
        # Check if the item is a common item or a form-prefixed item
        if item in self.get_selected_common_items():
            # Item is a common item
            if (item, operator, value) not in self.static_filter_items:
                self.static_filter_items.append((item, operator, value))
        elif is_qualified(item):
            # Item is form-prefixed (e.g. "DM.Legal Sex (ig_DM1.SEX)"): a form's
            # selected item, or its own copy of a common item it doesn't join on.
            if item in self._active_identifiers(include_unqualified=False):
                if (item, operator, value) not in self.static_filter_items:
                    self.static_filter_items.append((item, operator, value))
        else:
            # Check if the item is in any form's selected items
            for form in self.selected_forms.values():
                if item in form.get_selected_form_items():
                    if (item, operator, value) not in self.static_filter_items:
                        self.static_filter_items.append((item, operator, value))
                    break

        logger.debug("After adding static filter: %s", self.static_filter_items)

    def remove_static_filter_item(
        self, item: str, operator: str = None, value: str = None
    ):
        """Remove a filter."""
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
        """Set the filters."""
        self.static_filter_items = deepcopy(items)

    def get_dynamic_filter_items(self):
        """Get the list of comparisons."""
        return self.dynamic_filter_items

    def add_dynamic_filter_item(self, item1: str, operator: str, item2: str):
        """Add a comparison.

        This keeps the rows where *item1* compares with *item2* by *operator*.
        """
        # Both items need to exist either as common items or form items (with or without prefix)
        # For form items, they can be in format "form_name.item_name" or just "item_name"

        # Always add the comparison - we'll validate it at runtime when the report is created
        if (item1, operator, item2) not in self.dynamic_filter_items:
            # Add the comparison
            self.dynamic_filter_items.append((item1, operator, item2))
            logger.debug("Added dynamic filter: %s %s %s", item1, operator, item2)

    def remove_dynamic_filter_item(
        self, item1: str = None, operator: str = None, item2: str = None
    ):
        """Remove a comparison.

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
        """Set the comparisons."""
        self.dynamic_filter_items = deepcopy(items)

    def create_report(self):
        """Create the report from the stored selections, filters, joins, and renames.

        Execution is delegated to
        :class:`clinical_reporting.pipeline.ReportEngine`, which performs the
        join (with filters) -> comparisons -> reorder -> rename -> date-format
        -> finalize pipeline. See that class for the step-by-step details.

        Returns:
            The assembled report DataFrame, or ``None`` if nothing was produced.

        Raises:
            ReportValidationError: If the current selections, joins, filters,
                ordering, or output names do not form an executable report.
        """
        from clinical_reporting.pipeline import ReportEngine

        return ReportEngine(self).run()

    def validate(self) -> List["ReportValidationIssue"]:
        """Return structured issues that currently prevent report execution."""

        from clinical_reporting.validation import validate_report

        return validate_report(self)
