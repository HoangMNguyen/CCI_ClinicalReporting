import os
import re

import pandas as pd


# Function to check if any cell in the column matches the specific pattern
def has_range_pattern(series):
    return series.apply(lambda x: bool(re.match(r"\d+-\d+", str(x)))).any()


# Function to format dates without leading zeros for Windows compatibility
def format_date_without_leading_zeros(date_obj):
    if pd.notnull(date_obj):
        month = date_obj.month
        day = date_obj.day
        year = date_obj.year
        return f"{month}/{day}/{year}"
    return date_obj


def change_type(input_path, output_dir, output_file_name):
    # Check if the input path exists
    if not os.path.exists(input_path):
        raise FileNotFoundError("The specified input path does not exist.")
    else:
        # Determine the file extension
        _, file_extension = os.path.splitext(input_path)

    # Load the file based on its extension
    if file_extension.lower() == ".csv":
        data = pd.read_csv(input_path)
        # Store as dictionary with a single entry for consistency
        all_data = {"Sheet1": data}
    elif file_extension.lower() == ".xlsx":
        all_data = pd.read_excel(input_path, sheet_name=None)
    else:
        raise ValueError("Unsupported file type. Please provide a '.csv' or '.xlsx' file.")

    # Clean column names and process date columns for each sheet/dataframe
    for sheet_name, df in all_data.items():
        # Remove ".#" suffix from column names
        all_data[sheet_name].columns = [re.sub(r"\.\d+$", "", col) for col in df.columns]

        # Process date columns
        for col_name in df.columns:
            if "date" in str(col_name).lower():
                # Convert column to string for pattern matching
                date_strings = df[col_name].astype(str)

                # Check if any values match patterns with leading zeros in month or day (mm/dd/yyyy format)
                has_leading_zeros = date_strings.str.match(r"^0\d/|/0\d/").any()

                if has_leading_zeros:
                    try:
                        # First convert to datetime if not already
                        if not pd.api.types.is_datetime64_any_dtype(df[col_name]):
                            df[col_name] = pd.to_datetime(df[col_name], errors="coerce")
                        df[col_name] = df[col_name].apply(format_date_without_leading_zeros)
                    except Exception as e:
                        # If conversion fails, keep original data
                        print(f"Could not process date column '{col_name}': {e}")

    # Create a Pandas Excel writer using XlsxWriter as the engine
    writer = pd.ExcelWriter(
        output_dir + "/" + output_file_name + ".xlsx",
        engine="xlsxwriter",
        engine_kwargs={"options": {"strings_to_numbers": True}},
    )

    # Process each sheet
    for sheet_name, df in all_data.items():
        # Convert the dataframe to an XlsxWriter Excel object
        df.to_excel(writer, index=False, sheet_name=sheet_name)

        # Get the xlsxwriter workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]

        # Create a format to set matched columns to text type
        text_format = workbook.add_format({"num_format": "@"})

        # Apply formatting to columns based on their content
        for col_num, col_name in enumerate(df.columns):
            if has_range_pattern(df[col_name]):
                worksheet.set_column(col_num, col_num, None, text_format)

    # Close the Pandas Excel writer and output the Excel file
    writer.close()
