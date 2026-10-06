import warnings
import zipfile
from contextlib import contextmanager

import numpy as np
import pandas as pd
import pytest

import cci_automation.dsmb.DSMB_util as dsmb_util
from cci_automation.util import (
    add_rename_column_corelisting,
    add_rename_column_df,
    age_calculation,
    convert_integers_to_strings,
    get_data_from_dict_first,
    get_stats_df,
    remove_leading_zeros_from_dates,
)
from clinical_reporting.data import read_data_dict_zip_corelisting

_PANDAS_FUTURE_WARNING_CATEGORIES = tuple(
    warning_category
    for warning_category in (
        FutureWarning,
        DeprecationWarning,
        getattr(pd.errors, "Pandas4Warning", None),
    )
    if warning_category is not None
)


@contextmanager
def pandas_future_warnings_as_errors():
    with warnings.catch_warnings():
        for warning_category in _PANDAS_FUTURE_WARNING_CATEGORIES:
            warnings.simplefilter("error", warning_category)
        yield


def test_read_data_dict_zip_corelisting_filters_submitted_non_ilb_and_cutoff(tmp_path):
    df = pd.DataFrame(
        {
            "Subject": ["100-15420-01", "100-15420-02", "100-15420-03", "100-15420-04"],
            "Event Date": ["2024-01-01", "2024-02-01", "2024-01-10", "2024-01-15"],
            "Form Status": ["Submitted", "Submitted", "Draft", "Submitted"],
            "Form ILB Status": [False, False, False, True],
            "Value": ["keep", "after cutoff", "draft", "ilb"],
        }
    )
    zip_path = tmp_path / "core_listing.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("Core_Listings_DM.csv", df.to_csv(index=False))

    result = read_data_dict_zip_corelisting(str(zip_path), cut_off_date="2024-01-31")

    expected = pd.DataFrame(
        {
            "Subject": ["15420-01"],
            "Event Date": [pd.Timestamp("2024-01-01")],
            "Form Status": ["Submitted"],
            "Form ILB Status": [False],
            "Value": ["keep"],
        }
    )
    pd.testing.assert_frame_equal(result["DM"].reset_index(drop=True), expected)


def test_add_rename_column_corelisting_left_merges_non_ilb_rows():
    current_df = pd.DataFrame({"Subject": ["S1", "S2"]})
    input_data = {
        "FORM": pd.DataFrame(
            {
                "Subject": ["S1", "S2", "S2"],
                "Form ILB Status": [False, True, False],
                "Raw Column": ["A", "ignore", "B"],
            }
        )
    }

    result = add_rename_column_corelisting(
        current_df, input_data, "FORM", "Raw Column", "Renamed Column"
    )

    expected = pd.DataFrame({"Subject": ["S1", "S2"], "Renamed Column": ["A", "B"]})
    pd.testing.assert_frame_equal(result.reset_index(drop=True), expected)


def test_add_rename_column_df_left_merges_on_compound_key():
    current_df = pd.DataFrame({"Subject": ["S1", "S2"], "Visit": ["V1", "V1"]})
    input_df = pd.DataFrame(
        {"Subject": ["S1", "S2"], "Visit": ["V1", "V2"], "Dose": [10, 20]}
    )

    result = add_rename_column_df(
        current_df, input_df, "FORM", "Dose", "Dose Level", key2="Visit"
    )

    expected = pd.DataFrame(
        {"Subject": ["S1", "S2"], "Visit": ["V1", "V1"], "Dose Level": [10.0, np.nan]}
    )
    pd.testing.assert_frame_equal(result.reset_index(drop=True), expected)


def test_get_stats_df_coerces_numeric_values_and_formats_summary():
    result = get_stats_df("Age", pd.DataFrame({"Age": ["10", "bad", "20"]}))

    assert result.iloc[0, 0] == "15.00 (7.07)"
    assert result.iloc[1, 0] == 15.0
    assert result.iloc[2, 0] == "10.00 - 20.00"


def test_convert_integers_to_strings_preserves_strings_booleans_and_missing_values():
    df = pd.DataFrame({"Day": [1, 2.0, 2.5, True, np.nan, "Day 3"]})

    result = convert_integers_to_strings(df.copy(), "Day")

    assert result.loc[0, "Day"] == "1"
    assert result.loc[1, "Day"] == "2"
    assert result.loc[2, "Day"] == "2.5"
    assert result.loc[3, "Day"] is True
    assert pd.isna(result.loc[4, "Day"])
    assert result.loc[5, "Day"] == "Day 3"


def test_get_data_from_dict_first_keeps_earliest_event_per_subject():
    data = {
        "INF": pd.DataFrame(
            {
                "Subject": ["S1", "S1", "S2"],
                "Event Date": ["2024-02-01", "2024-01-01", "2024-03-01"],
                "Dose": ["late", "early", "only"],
            }
        )
    }
    input_dict = {"INF": {"Dose": "First Dose"}}

    result = get_data_from_dict_first(data, input_dict)

    expected = pd.DataFrame({"Subject": ["S1", "S2"], "First Dose": ["early", "only"]})
    pd.testing.assert_frame_equal(result.reset_index(drop=True), expected)


def test_age_calculation_uses_primary_date_then_fallback_date():
    df = pd.DataFrame(
        {
            "Date of Birth": [pd.Timestamp("2000-06-15"), pd.Timestamp("2000-06-15")],
            "Consent Date": [pd.Timestamp("2020-06-14"), pd.NaT],
            "Main Consent Date": [pd.NaT, pd.Timestamp("2020-06-15")],
        }
    )

    result = age_calculation(
        df, "Age", "Date of Birth", "Consent Date", "Main Consent Date"
    )

    assert result["Age"].tolist() == [19, 20]


def test_remove_leading_zeros_from_dates_formats_date_columns_only():
    df = pd.DataFrame(
        {"Visit Date": ["2024-01-05", pd.NaT], "Comment": ["2024-01-05", "keep"]}
    )

    result = remove_leading_zeros_from_dates(df)

    expected = pd.DataFrame(
        {"Visit Date": ["1/5/2024", ""], "Comment": ["2024-01-05", "keep"]}
    )
    pd.testing.assert_frame_equal(result, expected)


def test_dsmb_add_rename_column_corelisting_left_merges_non_ilb_rows():
    current_df = pd.DataFrame({"Subject": ["S1", "S2"]})
    input_data = {
        "FORM": pd.DataFrame(
            {
                "Subject": ["S1", "S2", "S2"],
                "Form ILB Status": [False, True, False],
                "Raw Column": ["A", "ignore", "B"],
            }
        )
    }

    result = dsmb_util.add_rename_column_corelisting(
        current_df, input_data, "FORM", "Raw Column", "Renamed Column"
    )

    expected = pd.DataFrame({"Subject": ["S1", "S2"], "Renamed Column": ["A", "B"]})
    pd.testing.assert_frame_equal(result, expected)


def test_dsmb_get_stats_percentage_counts_and_percentages_codelist_values():
    df = pd.DataFrame({"Subject": ["S1", "S2", "S3"], "AE": ["Y", "N", "Y"]})

    result = dsmb_util.get_stats_percentage("AE", df)

    assert result.loc["Y", "Subject"] == "2 (66.7%)"
    assert result.loc["N", "Subject"] == "1 (33.3%)"


def test_dsmb_get_stats_percentage2_reindexes_to_custom_group_order():
    df = pd.DataFrame({"Subject": ["S1", "S2"], "Legal Sex": ["Male", "Female"]})

    result = dsmb_util.get_stats_percentage2(
        "Legal Sex", ["Male", "Female", "Unknown"], df
    )

    assert result.index.tolist() == ["Male", "Female", "Unknown"]
    assert result.loc["Male", "Subject"] == "1 (50.0%)"
    assert result.loc["Unknown", "Subject"] == "0 (0.0%)"


def test_dsmb_get_stats_df_coerces_numeric_values_and_formats_summary():
    result = dsmb_util.get_stats_df("Age", pd.DataFrame({"Age": ["10", "bad", "20"]}))

    assert result.iloc[0, 0] == "15.00 (7.07)"
    assert result.iloc[1, 0] == 15.0
    assert result.iloc[2, 0] == "10.00 - 20.00"


def test_dsmb_get_stats_perc_df_formats_percentage_summary():
    result = dsmb_util.get_stats_perc_df(
        "Percent", pd.DataFrame({"Percent": [1, 2, 3]})
    )

    assert result.iloc[0, 0] == "2.00% (1.00%)"
    assert result.iloc[1, 0] == "2.00%"
    assert result.iloc[2, 0] == "1.00% - 3.00%"


def test_dsmb_convert_float_2_sci_notation_uses_half_up_rounding():
    assert dsmb_util.convert_float_2_sci_notation(1.005) == "1.01x10^0"


def test_dsmb_convert_sci_notation_2_float_valid_input():
    assert dsmb_util.convert_sci_notation_2_float("2.5x10^2") == 250.0


def test_pandas_chained_inplace_fillna_warns_and_does_not_update_parent_dataframe():
    df = pd.DataFrame({"Response": ["CR", None]})

    with pytest.warns(pd.errors.ChainedAssignmentError):
        df["Response"].fillna("Not Applicable", inplace=True)

    assert pd.isna(df.loc[1, "Response"])


def test_pandas_fillna_assignment_updates_parent_dataframe_without_future_warnings():
    df = pd.DataFrame({"Response": ["CR", None]})

    with pandas_future_warnings_as_errors():
        df["Response"] = df["Response"].fillna("Not Applicable")

    assert df["Response"].tolist() == ["CR", "Not Applicable"]


def test_pandas_fillna_infer_objects_without_deprecated_copy_keyword():
    df = pd.DataFrame(
        {
            "Flag": pd.Series([True, None], dtype=object),
            "Count": pd.Series([1, None], dtype=object),
        }
    )

    with pandas_future_warnings_as_errors():
        result = df.fillna({"Flag": False, "Count": 0}).infer_objects()

    assert result["Flag"].dtype == bool
    assert result["Count"].dtype == np.int64
    assert result.to_dict("list") == {"Flag": [True, False], "Count": [1, 0]}


def test_pandas_groupby_idxmin_safe_pattern_skips_all_missing_score_groups():
    df = pd.DataFrame(
        {
            "Subject": ["S1", "S1", "S2", "S2", "S3"],
            "Score": [np.nan, np.nan, 4.0, 2.0, 1.0],
            "Response": ["missing 1", "missing 2", "PR", "CR", "CR"],
        }
    )

    with pandas_future_warnings_as_errors():
        valid_scores = df.dropna(subset=["Score"])
        best_idx = valid_scores.groupby("Subject")["Score"].idxmin()
        result = df.loc[best_idx].sort_values("Subject").reset_index(drop=True)

    expected = pd.DataFrame(
        {
            "Subject": ["S2", "S3"],
            "Score": [2.0, 1.0],
            "Response": ["CR", "CR"],
        }
    )
    pd.testing.assert_frame_equal(result, expected)


def test_pandas_groupby_idxmax_safe_pattern_skips_all_missing_date_groups():
    df = pd.DataFrame(
        {
            "Subject": ["S1", "S1", "S2", "S2", "S3"],
            "Event Date": [
                pd.NaT,
                pd.NaT,
                pd.Timestamp("2024-01-01"),
                pd.Timestamp("2024-02-01"),
                pd.Timestamp("2024-03-01"),
            ],
            "Visit": ["missing 1", "missing 2", "V1", "V2", "V1"],
        }
    )

    with pandas_future_warnings_as_errors():
        valid_dates = df.dropna(subset=["Event Date"])
        current_idx = valid_dates.groupby("Subject")["Event Date"].idxmax()
        result = df.loc[current_idx].sort_values("Subject").reset_index(drop=True)

    expected = pd.DataFrame(
        {
            "Subject": ["S2", "S3"],
            "Event Date": [pd.Timestamp("2024-02-01"), pd.Timestamp("2024-03-01")],
            "Visit": ["V2", "V1"],
        }
    )
    pd.testing.assert_frame_equal(result, expected)


def test_pandas_replace_inf_and_nan_for_report_output_without_future_warnings():
    df = pd.DataFrame(
        {
            "Dose": [1.0, np.inf, -np.inf, np.nan],
            "Comment": ["ok", np.nan, "low", "missing"],
        }
    )

    with pandas_future_warnings_as_errors():
        result = df.replace([np.inf, -np.inf], np.nan).fillna("")

    expected = pd.DataFrame(
        {"Dose": [1.0, "", "", ""], "Comment": ["ok", "", "low", "missing"]}
    )
    pd.testing.assert_frame_equal(result, expected)


def test_pandas_string_concat_uses_fillna_without_stringifying_missing_values():
    df = pd.DataFrame({"Visit": ["Day 1", None, "Day 3"], "Suffix": [None, "-R", None]})

    with pandas_future_warnings_as_errors():
        result = df["Visit"].fillna("") + df["Suffix"].fillna("")

    assert result.tolist() == ["Day 1", "-R", "Day 3"]
