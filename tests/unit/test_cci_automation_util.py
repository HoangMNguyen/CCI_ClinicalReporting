import pandas as pd
import pytest

from cci_automation.util import (
    convert_float_2_sci_notation_2dp,
    get_data_from_dict,
)


def test_convert_float_2_sci_notation_2dp_zero():
    # Test when input is zero
    assert convert_float_2_sci_notation_2dp(0) == "0"


def test_convert_float_2_sci_notation_2dp_positive_integer():
    # Test when input is a positive integer
    assert convert_float_2_sci_notation_2dp(100) == "1x10^2"


def test_convert_float_2_sci_notation_2dp_negative_integer():
    # Test when input is a negative integer
    assert convert_float_2_sci_notation_2dp(-100) == "-1x10^2"


def test_convert_float_2_sci_notation_2dp_positive_float():
    # Test when input is a positive float
    assert convert_float_2_sci_notation_2dp(0.0256) == "2.56x10^-2"


def test_convert_float_2_sci_notation_2dp_negative_float():
    # Test when input is a negative float
    assert convert_float_2_sci_notation_2dp(-0.0256) == "-2.56x10^-2"


def test_convert_float_2_sci_notation_2dp_positive_float_integer_mantissa():
    # Test when input is a positive float with integer mantissa
    assert convert_float_2_sci_notation_2dp(5) == "5x10^0"


def test_convert_float_2_sci_notation_2dp_negative_float_integer_mantissa():
    # Test when input is a negative float with integer mantissa
    assert convert_float_2_sci_notation_2dp(-5) == "-5x10^0"


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
