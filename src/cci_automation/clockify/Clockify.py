#!/usr/bin/env python3
import os
from datetime import date

import numpy as np
import pandas as pd
import requests
from xlsxwriter.utility import xl_col_to_name

from cci_automation.clockify.roles import roles_list  # Import roles_list from roles.py
from cci_automation.clockify.tags import tags_list  # Import tags_list from tags.py
from cci_automation.clockify.tasks import task_list
from cci_automation.util import (
    clockify_get_api_key,
    clockify_get_detailed_report,
    clockify_get_project_id,
    clockify_get_task_df,
    clockify_get_workplace_id,
    clockify_sort_tasks,
)


def clockify_create_tasks(api_key, workspace_id, project_name):
    """
    Create tasks in Clockify for a given project using the shared task list.
    """
    # task_list is now imported from tasks.py
    # Get the project ID
    project_id = clockify_get_project_id(api_key, workspace_id, project_name)

    headers = {"Content-Type": "application/json", "X-Api-Key": api_key}
    url = f"https://api.clockify.me/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks"

    # Create tasks in Clockify using the shared task list
    for task_name in task_list:
        data = {"name": task_name}
        response = requests.post(url, headers=headers, json=data)
        print(response.json())


class ClockifyDashboard:
    def __init__(
        self, project_name, output_dir, input_file_path=None
    ):  # self.selected_option2, self.input_folder_name, self.output_folder_name, self.output_file_name
        self.project_name = project_name
        self.tasks = clockify_get_task_df(clockify_get_api_key(), clockify_get_workplace_id(), project_name)
        self.input_file_path = input_file_path
        self.output_dir = output_dir
        self.current_dir = os.getcwd()
        if input_file_path is not None:
            self.read_data()
        else:
            self.raw_data = clockify_get_detailed_report(
                clockify_get_api_key(), clockify_get_workplace_id(), project_name
            )
        self.define_input_lists()
        self.sorted_tasks = clockify_sort_tasks(self.tasks, self.template_tasks)
        sorted_tasks_new_col_name = {"Task ID": "Task"}
        self.sorted_tasks = self.sorted_tasks.rename(columns=sorted_tasks_new_col_name)
        self.error_message = False
        self.collect_data()
        self.output()

    def read_data(self):
        # Read data to self.data using read_csv for raw data
        self.raw_data = pd.read_csv(self.input_file_path)

    def define_input_lists(self):
        """
        Define tasks, tags, and roles using the imported lists.
        """
        self.template_tasks = pd.DataFrame({"Task": task_list})
        self.tags = pd.DataFrame({"Tags": tags_list})
        self.roles = pd.DataFrame({"Roles": roles_list})

    def collect_data(self):
        ### Filter data
        # filter the raw data to selected columns
        filter_data = self.raw_data[["Project", "Task", "User", "Tags", "Duration (h)", "Duration (decimal)"]].copy()
        # Replace NA values with empty strings
        filter_data["Project"] = filter_data["Project"].fillna("")
        filter_data["Task"] = filter_data["Task"].fillna("")
        filter_data["Tags"] = filter_data["Tags"].fillna("")
        filter_data["Duration (decimal)"] = pd.to_numeric(filter_data["Duration (decimal)"], errors="coerce").fillna(0)
        # Filter to the study selected
        filter_data = filter_data[filter_data["Project"].str.contains(self.project_name, regex=False, na=False)].copy()
        filter_data = filter_data.reset_index(drop=True)
        # assign the filtered data to self.filter_data
        self.filter_data = filter_data
        self.missing_tag_rows = self.filter_data["Tags"].eq("")

        ### DF1
        # create a dataframe that shows total hours per task

        sum_per_task = self.filter_data.groupby("Task")["Duration (decimal)"].sum()
        self.df1 = pd.merge(self.sorted_tasks, sum_per_task, on="Task", how="left")
        # Replace NaN values with 0
        self.df1["Duration (decimal)"] = self.df1["Duration (decimal)"].replace(np.nan, 0)
        # rename the 'Duration (decimal)' column to 'Total Task Hours'
        df1_new_col_name = {"Duration (decimal)": "Total Task Hours"}
        self.df1 = self.df1.rename(columns=df1_new_col_name)
        self.df6 = self.df1.copy()
        self.df1 = self.df1[self.df1["Total Task Hours"] != 0]
        self.df1["Total Task Hours"] = pd.to_numeric(self.df1["Total Task Hours"]).round(1)
        # calculate the percentage
        df1_total_hours = self.df1["Total Task Hours"].sum()
        self.df1["Total Hours Percentage per Task"] = (
            self.df1["Total Task Hours"] / df1_total_hours if df1_total_hours else 0
        )
        total_instance = {
            "Task": "Total Project Hours",
            "Total Task Hours": df1_total_hours,
            "Total Hours Percentage per Task": "",
        }
        self.df1 = pd.concat([self.df1, pd.DataFrame([total_instance])], ignore_index=True)
        # self.df1.loc[len(self.df1)] = {'Task': 'Total Project Hours', 'Total Task Hours': df1_total_hours, 'Total Hours Percentage per Task': ''}

        ### DF 2 hours per tag
        # create a dataframe that shows total hours per project milestone
        sum_per_tag = self.filter_data.groupby("Tags")["Duration (decimal)"].sum()
        self.df2 = pd.merge(self.tags, sum_per_tag, on="Tags", how="left")
        # Replace NaN values with 0
        self.df2["Duration (decimal)"] = self.df2["Duration (decimal)"].replace(np.nan, 0)
        # rename the columns to match the desired output
        df2_new_col_name = {"Tags": "Project Milestone", "Duration (decimal)": "Total Hours by Project Milestone"}
        self.df2 = self.df2.rename(columns=df2_new_col_name)
        # calculate the total hours and percentage of hours per project milestone
        total_hours = sum_per_tag.sum()
        percent_hours = sum_per_tag / total_hours if total_hours else sum_per_tag * 0
        # add a new column to the existing DataFrame
        self.df2["Project Milestone Percentage of Project"] = self.df2["Project Milestone"].map(percent_hours)
        # Replace NaN values with 0
        self.df2["Project Milestone Percentage of Project"] = self.df2[
            "Project Milestone Percentage of Project"
        ].replace(np.nan, 0)

        ### DF3 hours per role
        # create a dataframe that shows total hours per role
        new_cols = self.filter_data["Task"].fillna("").astype(str).str.split(")", n=1, expand=True)
        new_cols = new_cols.reindex(columns=[0, 1], fill_value="")
        new_cols.columns = ["Roles", "Work"]
        new_cols["Roles"] = new_cols["Roles"].fillna("").str.replace("(", "", regex=False)
        self.df3 = pd.concat([self.filter_data, new_cols], axis=1)
        self.df4 = self.df3.copy()
        sum_per_role = self.df3.groupby("Roles")["Duration (decimal)"].sum()
        self.df3 = pd.merge(self.roles, sum_per_role, on="Roles", how="left")
        # Replace NaN values with 0
        self.df3["Duration (decimal)"] = self.df3["Duration (decimal)"].replace(np.nan, 0)
        # rename the columns to match the desired output
        df3_new_col_name = {"Roles": "Role", "Duration (decimal)": "Total Hours by Role"}
        self.df3 = self.df3.rename(columns=df3_new_col_name)
        # calculate the total hours and percentage of hours per role
        role_total_hours = sum_per_role.sum()
        role_percent_hours = sum_per_role / role_total_hours if role_total_hours else sum_per_role * 0
        # add a new column to the existing DataFrame
        self.df3["Total Hours Percentage of Project"] = self.df3["Role"].map(role_percent_hours)
        self.df3["Total Hours Percentage of Project"] = self.df3["Total Hours Percentage of Project"].replace(np.nan, 0)

        # print(self.df3)

        ### DF4 validation tab
        self.df4 = self.df4[["User", "Roles"]].drop_duplicates(subset=["User", "Roles"])
        # print(self.df4)

        ### DF5 validation tab
        self.df5 = self.filter_data.copy()
        self.df5 = self.df5[self.df5["Tags"].isna() | (self.df5["Tags"] == "")]
        df5_new_col_name = {"Task": "Tasks with no tags selected."}
        self.df5 = self.df5.rename(columns=df5_new_col_name)
        # print(self.df5)

        ### DF6 validation tab
        self.df6 = self.df6[self.df6["Total Task Hours"] == 0]
        self.df6 = self.df6[["Task"]]
        df6_new_col_name = {"Task": "Tasks expected but not entered."}
        self.df6 = self.df6.rename(columns=df6_new_col_name)

    def output(self):
        project_label = self.filter_data.iloc[0, 0] if not self.filter_data.empty else self.project_name
        self.output_file_name = date.today().strftime("%y%m%d") + "-" + project_label + "-Clockify Dashboard"
        with pd.ExcelWriter(self.output_dir + "/" + self.output_file_name + ".xlsx", engine="xlsxwriter") as writer:
            self.raw_data.to_excel(writer, sheet_name="Detailed Report", index=False, startcol=0)
            self.filter_data.to_excel(writer, sheet_name="Filtered Report", index=False, startcol=0)
            self.df1.to_excel(writer, sheet_name="Dashboard", index=False, startcol=1, startrow=3)
            self.df2.to_excel(writer, sheet_name="Dashboard", index=False, startcol=5, startrow=3)
            self.df3.to_excel(writer, sheet_name="Dashboard", index=False, startcol=5, startrow=11)
            self.df4.to_excel(writer, sheet_name="Validation Tab", index=False, startcol=0, startrow=0)
            self.df5.to_excel(writer, sheet_name="Validation Tab", index=False, startcol=3, startrow=0)
            self.df6.to_excel(writer, sheet_name="Validation Tab", index=False, startcol=10, startrow=0)

            worksheet1 = writer.sheets["Detailed Report"]
            worksheet1.autofit()
            worksheet2 = writer.sheets["Filtered Report"]
            worksheet2.autofit()
            worksheet3 = writer.sheets["Dashboard"]
            worksheet3.autofit()
            worksheet4 = writer.sheets["Validation Tab"]
            worksheet4.autofit()

            ## formating
            # coloring
            no_border_white = writer.book.add_format({"bg_color": "#FFFFFF", "border": 0})
            missing_tag_format = writer.book.add_format({"bg_color": "#FFFF00", "border": 1})
            listing_header_format = writer.book.add_format(
                {
                    "bg_color": "#DCE6F1",
                    "text_wrap": True,
                    "valign": "vcenter",
                    "align": "center",
                    "bold": True,
                    "font_name": "Calibri",
                    "font_size": 11,
                    "border": 1,
                }
            )
            listing_data_format = writer.book.add_format(
                {
                    "text_wrap": True,
                    "valign": "top",
                    "align": "left",
                    "font_name": "Calibri",
                    "font_size": 11,
                    "border": 1,
                }
            )
            blue_header_format = writer.book.add_format(
                {
                    "bg_color": "#DCE6F1",
                    "text_wrap": True,
                    "valign": "vcenter",
                    "align": "center",
                    "bold": True,
                    "font_name": "Calibri",
                    "font_size": 11,
                    "border": 1,
                }
            )
            pink_header_format = writer.book.add_format(
                {
                    "bg_color": "#F2DCDB",
                    "text_wrap": True,
                    "valign": "vcenter",
                    "align": "center",
                    "bold": True,
                    "font_name": "Calibri",
                    "font_size": 18,
                    "border": 1,
                }
            )
            pink_data_format = writer.book.add_format(
                {
                    "bg_color": "#F2DCDB",
                    "text_wrap": True,
                    "valign": "vcenter",
                    "align": "right",
                    "bold": True,
                    "font_name": "Calibri",
                    "font_size": 11,
                    "border": 1,
                }
            )
            grey_left_format = writer.book.add_format(
                {
                    "bg_color": "#F2F2F2",
                    "text_wrap": True,
                    "valign": "vcenter",
                    "align": "left",
                    "font_name": "Calibri",
                    "font_size": 11,
                    "border": 1,
                }
            )
            grey_perc_left_format = writer.book.add_format(
                {
                    "bg_color": "#F2F2F2",
                    "text_wrap": True,
                    "valign": "vcenter",
                    "align": "left",
                    "font_name": "Calibri",
                    "font_size": 11,
                    "border": 1,
                    "num_format": "0%",
                }
            )
            blue_header_format = writer.book.add_format(
                {
                    "bg_color": "#DCE6F1",
                    "text_wrap": True,
                    "valign": "vcenter",
                    "align": "center",
                    "bold": True,
                    "font_name": "Calibri",
                    "font_size": 18,
                    "border": 1,
                }
            )

            def write_bordered_dataframe(worksheet, df, startrow=0, startcol=0):
                for col_idx, column_name in enumerate(df.columns):
                    worksheet.write(startrow, startcol + col_idx, column_name, listing_header_format)
                for row_idx, row in enumerate(df.itertuples(index=False), start=1):
                    for col_idx, value in enumerate(row):
                        if pd.isna(value):
                            value = ""
                        worksheet.write(startrow + row_idx, startcol + col_idx, value, listing_data_format)

            write_bordered_dataframe(worksheet1, self.raw_data)
            write_bordered_dataframe(worksheet2, self.filter_data)
            write_bordered_dataframe(worksheet4, self.df4, startcol=0)
            write_bordered_dataframe(worksheet4, self.df5, startcol=3)
            write_bordered_dataframe(worksheet4, self.df6, startcol=10)

            if not self.filter_data.empty and "Tags" in self.filter_data.columns:
                tags_column = xl_col_to_name(self.filter_data.columns.get_loc("Tags"))
                worksheet2.conditional_format(
                    1,
                    0,
                    len(self.filter_data),
                    len(self.filter_data.columns) - 1,
                    {
                        "type": "formula",
                        "criteria": f'=${tags_column}2=""',
                        "format": missing_tag_format,
                    },
                )

            # BACK GROUND COLOR WHITE
            for j in range(len(self.df1) + 5 if len(self.df1) + 3 > 22 else 22):
                for i in range(9):
                    worksheet3.write(j, i, None, no_border_white)
            # MERGE HEADER AND FORMAT
            worksheet3.merge_range(
                "B2:H2",
                self.filter_data.iloc[0, 0]
                + " Clockify Dashboard\nDate generated: "
                + date.today().strftime("%m/%d/%Y"),
                pink_header_format,
            )

            # FORMATTING WORKSHEET 3
            # print(self.df1)
            # HEADER
            for i in range(3):
                worksheet3.write(3, i + 1, self.df1.columns.values[i], blue_header_format)
                worksheet3.write(3, i + 5, self.df2.columns.values[i], blue_header_format)
                worksheet3.write(11, i + 5, self.df3.columns.values[i], blue_header_format)
                worksheet3.write(len(self.df1) + 3, i + 1, self.df1.iloc[len(self.df1) - 1, i], pink_data_format)

            # TABLE 1
            for j in range(len(self.df1) - 1):
                worksheet3.write(4 + j, 0 + 1, self.df1.iloc[j, 0], grey_left_format)
                worksheet3.write(4 + j, 1 + 1, self.df1.iloc[j, 1], grey_left_format)
                worksheet3.write(4 + j, 2 + 1, self.df1.iloc[j, 2], grey_perc_left_format)

            # TABLE 2
            for j in range(len(self.df2)):
                worksheet3.write(4 + j, 0 + 5, self.df2.iloc[j, 0], grey_left_format)
                worksheet3.write(4 + j, 1 + 5, self.df2.iloc[j, 1], grey_left_format)
                worksheet3.write(4 + j, 2 + 5, self.df2.iloc[j, 2], grey_perc_left_format)

            # TABLE 3
            for j in range(len(self.df3)):
                worksheet3.write(12 + j, 0 + 5, self.df3.iloc[j, 0], grey_left_format)
                worksheet3.write(12 + j, 1 + 5, self.df3.iloc[j, 1], grey_left_format)
                worksheet3.write(12 + j, 2 + 5, self.df3.iloc[j, 2], grey_perc_left_format)

            # Set column width for columns J to the last column and rows
            worksheet3.set_column("J:XFD", None, None, {"hidden": True})
            for i in range(0, 20):
                worksheet3.set_row(i, None, None)

            # Hide rows below row 24
            worksheet3.set_default_row(hide_unused_rows=True)
            worksheet3.set_row(len(self.df1) + 5 if len(self.df1) + 5 > 23 else 23, None, None, {"hidden": True})

            # SET ZOOM TO 90%
            worksheet3.set_zoom(90)

            # set the row height of row 2 to 70
            worksheet3.set_row(1, 70)


# if __name__ == '__main__':
#     ClockifyDashboard("15420 Amendment V4", "C:/Users/hmn39/Downloads")
#     # ClockifyDashboard("15420 Amendment V4", "C:/Users/hmn39/Downloads","C:/Users/hmn39/Downloads/15420_Clockify_Time_Report_Detailed_09_25_2022-05_11_2023.csv")
