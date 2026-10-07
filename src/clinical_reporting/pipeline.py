"""Report execution pipeline and its DataFrame filter operations.

Separates report *execution* (joining forms, applying filters, ordering,
renaming, date formatting) from the report *state* held by
:class:`~clinical_reporting.report.CLReport`. ``CLReport.create_report``
delegates here; the steps are small and can be tested one at a time.
"""

from __future__ import annotations

import logging
import warnings

import numpy as np
import pandas as pd

from clinical_reporting import report_columns
from clinical_reporting.export import to_short_date_string
from clinical_reporting.models import (
    SUBJECT_COLUMN,
    JoinHow,
    Operator,
    is_qualified,
    qualify,
    split_qualified,
)

logger = logging.getLogger(__name__)


def apply_static_filter(df, item, operator, value):
    """Filter rows by comparing one column with a configured value."""
    if df is None or df.empty or item not in df.columns:
        return df

    is_numeric = False
    try:
        numeric_value = pd.to_numeric(value)
        numeric_column = pd.to_numeric(df[item], errors="coerce")
        is_numeric = True
    except Exception:
        pass

    if operator == Operator.EQ:
        if is_numeric:
            return df[numeric_column == numeric_value]
        return df[df[item].astype(str).str.lower() == str(value).lower()]
    if operator == Operator.NE:
        if is_numeric:
            return df[numeric_column != numeric_value]
        return df[df[item].astype(str).str.lower() != str(value).lower()]
    if operator == Operator.GT:
        return (
            df[numeric_column > numeric_value] if is_numeric else df[df[item] > value]
        )
    if operator == Operator.GE:
        return (
            df[numeric_column >= numeric_value] if is_numeric else df[df[item] >= value]
        )
    if operator == Operator.LT:
        return (
            df[numeric_column < numeric_value] if is_numeric else df[df[item] < value]
        )
    if operator == Operator.LE:
        return (
            df[numeric_column <= numeric_value] if is_numeric else df[df[item] <= value]
        )
    if operator == Operator.CONTAINS:
        return df[df[item].astype(str).str.contains(str(value), case=False, na=False)]
    if operator == Operator.NOT_CONTAINS:
        return df[~df[item].astype(str).str.contains(str(value), case=False, na=False)]
    if operator in {Operator.IN, Operator.NOT_IN}:
        value_list = [part.strip() for part in str(value).split(",")]
        if is_numeric:
            try:
                matches = numeric_column.isin(
                    [pd.to_numeric(part) for part in value_list]
                )
            except Exception:
                matches = (
                    df[item]
                    .astype(str)
                    .str.lower()
                    .isin([part.lower() for part in value_list])
                )
        else:
            matches = (
                df[item]
                .astype(str)
                .str.lower()
                .isin([part.lower() for part in value_list])
            )
        return df[matches] if operator == Operator.IN else df[~matches]
    if operator == Operator.IS_NULL:
        return df[df[item].isnull()]
    if operator == Operator.IS_NOT_NULL:
        return df[~df[item].isnull()]
    return df


def _looks_numeric(sample) -> bool:
    """Return whether sampled non-null values use the legacy numeric format."""
    return all(
        isinstance(value, (int, float))
        or (isinstance(value, str) and value.replace(".", "", 1).isdigit())
        for value in sample
        if value is not None and pd.notna(value)
    )


def apply_dynamic_filter(df, item1, operator, item2):
    """Filter rows by comparing two columns with compatible inferred types."""
    if df is None or df.empty:
        return df
    if item1 not in df.columns or item2 not in df.columns:
        logger.warning("Columns '%s' or '%s' not found in dataframe.", item1, item2)
        return df

    df_copy = df.copy()
    date_tokens = ("Date", "date", "DATE")
    date_columns = any(token in item1 for token in date_tokens) or any(
        token in item2 for token in date_tokens
    )
    if date_columns:
        try:
            df_copy[item1] = pd.to_datetime(df_copy[item1], errors="coerce")
            df_copy[item2] = pd.to_datetime(df_copy[item2], errors="coerce")
            logger.debug(
                "Converted columns %s and %s to datetime for comparison",
                item1,
                item2,
            )
        except Exception as error:
            logger.debug("Could not convert columns to datetime: %s", error)
            date_columns = False

    numeric_columns = False
    if not date_columns:
        try:
            sample1 = df_copy[item1].dropna().head(10)
            sample2 = df_copy[item2].dropna().head(10)
            if _looks_numeric(sample1) and _looks_numeric(sample2):
                df_copy[item1] = pd.to_numeric(df_copy[item1], errors="coerce")
                df_copy[item2] = pd.to_numeric(df_copy[item2], errors="coerce")
                numeric_columns = True
                logger.debug(
                    "Converted columns %s and %s to numeric for comparison",
                    item1,
                    item2,
                )
        except Exception as error:
            logger.debug("Error converting numeric columns: %s", error)

    left = df_copy[item1]
    right = df_copy[item2]
    string_columns = not date_columns and not numeric_columns
    if string_columns and operator in {Operator.EQ, Operator.NE}:
        left = left.astype(str).str.lower().str.strip()
        right = right.astype(str).str.lower().str.strip()

    operations = {
        Operator.EQ: lambda: left == right,
        Operator.NE: lambda: left != right,
        Operator.GT: lambda: left > right,
        Operator.GE: lambda: left >= right,
        Operator.LT: lambda: left < right,
        Operator.LE: lambda: left <= right,
    }
    result = df_copy[operations[operator]()] if operator in operations else df_copy
    logger.debug("Dynamic filter reduced rows from %s to %s", len(df_copy), len(result))

    for column in result.select_dtypes(include=[np.datetime64]).columns:
        result.loc[:, column] = result[column].dt.strftime("%m-%d-%Y")
    return result


class ReportEngine:
    """Builds the final report DataFrame from a configured :class:`CLReport`."""

    def __init__(self, report):
        # ``report`` supplies the data dict and the selection/filter/join state.
        self.report = report

    def run(self):
        """Execute the full pipeline and return the report DataFrame (or ``None``)."""
        # Keep direct engine use as safe as ``CLReport.create_report``. Invalid
        # mutable UI state must never be interpreted as permission to silently
        # omit a form, filter, or join from the output.
        from clinical_reporting.validation import raise_for_report

        raise_for_report(self.report)
        result_df = self._build_joined_table()
        if result_df is None:
            return None
        result_df = self._apply_dynamic_filters(result_df)
        result_df = self._reorder_columns(result_df)
        result_df = self._apply_renames(result_df)
        result_df = self._format_date_columns(result_df)
        result_df = self._finalize(result_df)
        return result_df

    # ------------------------------------------------------------------
    # Join phase

    def _select_filtered_columns(self, form_name, form):
        """Select a form's contributing columns and apply its filters.

        Returns the trimmed/filtered DataFrame, or ``None`` when the form
        contributes no columns.
        """
        report = self.report
        source = report.data[form_name]

        columns_to_select = []
        # Selected common items present in this form.
        for item in report.selected_common_items:
            if item in source.columns:
                columns_to_select.append(item)
        # Join items present in this form.
        for item in form.get_join_items():
            if item and item in source.columns and item not in columns_to_select:
                columns_to_select.append(item)
        # Selected form items.
        for item in form.get_selected_form_items():
            if item in source.columns and item not in columns_to_select:
                columns_to_select.append(item)

        if not columns_to_select:
            return None

        form_df = source[columns_to_select].copy()

        # Apply the filters whose item belongs to this form.
        for item, operator, value in report.static_filter_items:
            if item in form_df.columns:
                form_df = apply_static_filter(form_df, item, operator, value)
            elif is_qualified(item):
                prefix, col_name = split_qualified(item)
                if prefix == form_name and col_name in form_df.columns:
                    form_df = apply_static_filter(form_df, col_name, operator, value)

        return form_df

    def _prefix_first_form(self, form_df, form_name):
        """Prefix non-common columns of the first form with ``form_name.``."""
        report = self.report
        rename_cols = {
            col: qualify(form_name, col)
            for col in form_df.columns
            if col not in report.selected_common_items
        }
        if rename_cols:
            form_df = form_df.rename(columns=rename_cols)
        return form_df

    def _merge_subsequent_form(self, result_df, form_df, form_name, form):
        """Prefix, align join dtypes, and merge a non-first form into ``result_df``."""
        join_items = [item for item in form.get_join_items() if item]

        # Prefix every column but the join keys, including a common item this
        # form doesn't join on: its values are this form's own, so they go out
        # as FORM.item and the plain column keeps the earlier forms' values
        # (instead of pandas' _x/_y). See clinical_reporting.report_columns.
        rename_cols = {
            col: qualify(form_name, col)
            for col in form_df.columns
            if col not in join_items
        }
        if rename_cols:
            form_df = form_df.rename(columns=rename_cols)

        how = JoinHow.to_pandas(form.get_join_how())

        form_df = form_df.reset_index(drop=True)
        form_df = form_df.drop_duplicates()

        # Without join items there is nothing to merge on; keep the prior result.
        if not join_items:
            return result_df

        # Align join column dtypes to prevent merge errors (e.g., object vs datetime).
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

        return pd.merge(result_df, form_df, on=join_items, how=how)

    def _build_joined_table(self):
        """Join all selected forms in join order; return the merged DataFrame or ``None``."""
        report = self.report
        result_df = None
        for form_name in report_columns.forms_in_join_order(report.selected_forms):
            form = report.selected_forms[form_name]
            form_df = self._select_filtered_columns(form_name, form)
            if form_df is None:
                continue
            if result_df is None:
                result_df = self._prefix_first_form(form_df, form_name)
                continue
            result_df = self._merge_subsequent_form(result_df, form_df, form_name, form)
        return result_df

    # ------------------------------------------------------------------
    # Post-join phases

    @staticmethod
    def _resolve_filter_column(name, columns):
        """Resolve a comparison operand to an actual column name, or ``None``.

        Matches a column directly, or (for an unqualified operand) a column whose
        item part equals ``name`` after stripping its form prefix.
        """
        if name in columns:
            return name
        if not is_qualified(name):
            for col in columns:
                if is_qualified(col) and split_qualified(col)[1] == name:
                    return col
        return None

    def _apply_dynamic_filters(self, result_df):
        for item1, operator, item2 in self.report.dynamic_filter_items:
            item1_col = self._resolve_filter_column(item1, result_df.columns)
            item2_col = self._resolve_filter_column(item2, result_df.columns)
            if item1_col is not None and item2_col is not None:
                logger.debug(
                    "Applying filter: %s %s %s", item1_col, operator, item2_col
                )
                result_df = apply_dynamic_filter(
                    result_df, item1_col, operator, item2_col
                )
            else:
                logger.warning(
                    "Could not find columns for dynamic filter: %s %s %s (resolved item1=%s, item2=%s)",
                    item1,
                    operator,
                    item2,
                    item1_col,
                    item2_col,
                )
        return result_df

    def _reorder_columns(self, result_df):
        """Put the columns in ``selected_items_order_list`` order; others go last."""
        order = self.report.selected_items_order_list
        if not order:
            return result_df
        valid_order = [col for col in order if col in result_df.columns]
        if not valid_order:
            return result_df
        remaining_cols = [col for col in result_df.columns if col not in valid_order]
        return result_df[valid_order + remaining_cols]

    def _apply_renames(self, result_df):
        report = self.report
        if not report.rename_dict:
            return result_df
        rename_mapping = {
            orig_name: new_name
            for orig_name, new_name in report.rename_dict.items()
            if orig_name in result_df.columns and new_name
        }
        if rename_mapping:
            result_df = result_df.rename(columns=rename_mapping)
        return result_df

    @staticmethod
    def _to_datetime_quiet(series):
        """Parse to datetime preferring ``format="mixed"`` and suppressing warnings."""
        try:
            return pd.to_datetime(series, errors="coerce", format="mixed")
        except TypeError:
            # Older pandas may not support format="mixed"; fall back and suppress the warning.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=UserWarning)
                return pd.to_datetime(series, errors="coerce")

    def _format_date_columns(self, result_df):
        """Render date columns as ``m/d/yyyy`` strings (no leading zeros)."""
        # Datetime-typed columns, plus any 'date'-named column that parses as dates.
        date_cols = list(
            result_df.select_dtypes(
                include=["datetime64", "datetime", np.datetime64]
            ).columns
        )

        for col in result_df.columns:
            if "date" in col.lower() and col not in date_cols:
                try:
                    if pd.api.types.is_datetime64_dtype(result_df[col]):
                        inferred_datetime = True
                    else:
                        inferred_datetime = (
                            self._to_datetime_quiet(result_df[col]).notna().any()
                        )
                    if inferred_datetime:
                        date_cols.append(col)
                except Exception:
                    pass

        for col in date_cols:
            try:
                result_df[col] = self._to_datetime_quiet(result_df[col])
                result_df[col] = result_df[col].apply(to_short_date_string)
            except Exception:
                logger.debug("Could not format column %s as date", col)
        return result_df

    def _finalize(self, result_df):
        """Drop duplicate rows and sort by subject when present."""
        result_df = result_df.reset_index(drop=True)
        result_df = result_df.drop_duplicates()
        if SUBJECT_COLUMN in result_df.columns:
            result_df = result_df.sort_values(by=SUBJECT_COLUMN)
        return result_df
