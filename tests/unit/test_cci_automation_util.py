import numpy as np
import pandas as pd
import pytest

from cci_automation.util import (
    convert_float_2_sci_notation,
    convert_sci_notation_2_float,
    get_data_from_dict,
    get_stats_perc_df,
)


def setup_module(module):
    # Setup for the module. Runs once for each module
    pass


def teardown_module(module):
    # Teardown for the module. Runs once for each module
    pass


def setup_function(function):
    # Setup for each function. Runs before each function
    pass


def teardown_function(function):
    # Teardown for each function. Runs after each function
    pass


def test_convert_float_2_sci_notation_zero():
    # Test when input is zero
    assert convert_float_2_sci_notation(0) == "0"


def test_convert_float_2_sci_notation_positive_integer():
    # Test when input is a positive integer
    assert convert_float_2_sci_notation(100) == "1x10^2"


def test_convert_float_2_sci_notation_negative_integer():
    # Test when input is a negative integer
    assert convert_float_2_sci_notation(-100) == "-1x10^2"


def test_convert_float_2_sci_notation_positive_float():
    # Test when input is a positive float
    assert convert_float_2_sci_notation(0.0256) == "2.56x10^-2"


def test_convert_float_2_sci_notation_negative_float():
    # Test when input is a negative float
    assert convert_float_2_sci_notation(-0.0256) == "-2.56x10^-2"


def test_convert_float_2_sci_notation_positive_float_integer_mantissa():
    # Test when input is a positive float with integer mantissa
    assert convert_float_2_sci_notation(5) == "5x10^0"


def test_convert_float_2_sci_notation_negative_float_integer_mantissa():
    # Test when input is a negative float with integer mantissa
    assert convert_float_2_sci_notation(-5) == "-5x10^0"


def test_convert_sci_notation_2_float_valid_input():
    # Test when input is a valid scientific notation string
    assert convert_sci_notation_2_float("2.56x10^-2") == 0.0256


def test_convert_sci_notation_2_float_invalid_format():
    # Test when input is not in the correct format
    assert np.isnan(convert_sci_notation_2_float("2.56-10^-2"))


def test_convert_sci_notation_2_float_invalid_mantissa():
    # Test when mantissa cannot be converted to float
    assert np.isnan(convert_sci_notation_2_float("abcx10^2"))


def test_convert_sci_notation_2_float_invalid_exponent():
    # Test when exponent cannot be converted to float
    assert np.isnan(convert_sci_notation_2_float("2.56x10^abc"))


def test_convert_sci_notation_2_float_no_exponent():
    # Test when exponent is missing
    assert np.isnan(convert_sci_notation_2_float("2.56x10^"))


def test_convert_sci_notation_2_float_no_mantissa():
    # Test when mantissa is missing
    assert np.isnan(convert_sci_notation_2_float("x10^2"))


def test_convert_sci_notation_2_float_empty_string():
    # Test when input is an empty string
    assert np.isnan(convert_sci_notation_2_float(""))


def test_get_stats_perc_df():
    # Test with DataFrame having all numeric values
    # * Note: Values are percentages, not actual numbers
    df1 = pd.DataFrame({"A": [1, 2, 3, 4, 5]})
    df2 = pd.DataFrame({"A": [6, 7, 8, 9, 10]})
    result = get_stats_perc_df("A", df1, df2)
    print(result)
    assert result.loc["Mean ± SD", 0] == "3.00% (1.58%)"
    assert result.loc["Median", 0] == "3.00%"
    assert result.loc["Range", 0] == "1.00% - 5.00%"
    assert result.loc["Mean ± SD", 1] == "8.00% (1.58%)"
    assert result.loc["Median", 1] == "8.00%"
    assert result.loc["Range", 1] == "6.00% - 10.00%"


def test_get_data_from_dict_single_key():
    data = {
        "DM": pd.DataFrame(
            {
                "Subject": ["A", "B"],
                "Event Date": ["2022-01-01", "2022-01-02"],
                "Legal Sex": ["M", "F"],
            }
        )
    }
    input_dict = {"DM": {"Legal Sex": "Sex"}}
    expected_output = pd.DataFrame({"Subject": ["A", "B"], "Sex": ["M", "F"]})
    pd.testing.assert_frame_equal(get_data_from_dict(data, input_dict), expected_output)


def test_get_data_from_dict_multiple_keys():
    data = {
        "DM": pd.DataFrame(
            {
                "Subject": ["A", "B"],
                "Event Date": ["2022-01-01", "2022-01-02"],
                "Legal Sex": ["M", "F"],
            }
        ),
        "DSCA": pd.DataFrame(
            {
                "Subject": ["A", "B"],
                "Event Date": ["2022-01-01", "2022-01-02"],
                "Cohort Assignment": ["C1", "C2"],
            }
        ),
    }
    input_dict = {"DM": {"Legal Sex": "Sex"}, "DSCA": {"Cohort Assignment": "Cohort"}}
    expected_output = pd.DataFrame(
        {"Subject": ["A", "B"], "Sex": ["M", "F"], "Cohort": ["C1", "C2"]}
    )
    pd.testing.assert_frame_equal(get_data_from_dict(data, input_dict), expected_output)


def test_get_data_from_dict_no_matching_keys():
    data = {
        "DM": pd.DataFrame(
            {
                "Subject": ["A", "B"],
                "Event Date": ["2022-01-01", "2022-01-02"],
                "Legal Sex": ["M", "F"],
            }
        )
    }
    input_dict = {"DSCA": {"Cohort Assignment": "Cohort"}}
    with pytest.raises(UnboundLocalError):
        get_data_from_dict(data, input_dict)


def test_get_data_from_dict_empty_data():
    data = {}
    input_dict = {"DM": {"Legal Sex": "Sex"}}
    with pytest.raises(UnboundLocalError):
        get_data_from_dict(data, input_dict)


def test_get_data_from_dict_empty_input_dict():
    data = {
        "DM": pd.DataFrame(
            {
                "Subject": ["A", "B"],
                "Event Date": ["2022-01-01", "2022-01-02"],
                "Legal Sex": ["M", "F"],
            }
        )
    }
    input_dict = {}
    with pytest.raises(UnboundLocalError):
        get_data_from_dict(data, input_dict)


def test_get_data_from_dict_empty_dataframe_entries():
    data = {"DM": pd.DataFrame(columns=["Subject", "Event Date", "Legal Sex"])}
    input_dict = {"DM": {"Legal Sex": "Sex"}}
    expected_output = pd.DataFrame(columns=["Subject", "Sex"])
    pd.testing.assert_frame_equal(get_data_from_dict(data, input_dict), expected_output)
