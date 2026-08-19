#!/usr/bin/env python3
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta


def EnrollmentLog16321(final_data):
    # DM
    # if 'DM' in final_data:
    DM_df = final_data["DM"][
        [
            "Subject",
            "Race (ig_DM1.RACE)",
            "Ethnicity (ig_DM1.ETHNIC)",
            "Sex Assigned at Birth (ig_DM1.BRTHSEX)",
            "Legal Sex (ig_DM1.SEX)",
            "Date of Birth (ig_DM1.BRTHDAT)",
            "Apheresis Consent Date (ig_DM1.RFICDAT)",
        ]
    ].copy()
    DM_new_col_name = {
        "Race (ig_DM1.RACE)": "Race",
        "Ethnicity (ig_DM1.ETHNIC)": "Ethnicity",
        "Sex Assigned at Birth (ig_DM1.BRTHSEX)": "Sex Assigned at Birth",
        "Legal Sex (ig_DM1.SEX)": "Legal Sex",
        "Date of Birth (ig_DM1.BRTHDAT)": "Date of Birth",
        "Apheresis Consent Date (ig_DM1.RFICDAT)": "Apheresis Consent Date",
    }
    DM_df = DM_df.rename(columns=DM_new_col_name)
    sorted_DM_df = DM_df.sort_values(["Subject"])

    # DSCAS

    DSCA_df = final_data["DSCA"][["Subject", "Cohort Assignment (ig_DSCA1.CACHASCOD)"]].copy()
    DSCA_new_col_name = {"Cohort Assignment (ig_DSCA1.CACHASCOD)": "Assigned Cohort"}
    DSCA_df = DSCA_df.rename(columns=DSCA_new_col_name)
    merged_df = pd.merge(sorted_DM_df, DSCA_df, on="Subject", how="left")
    index_reference = merged_df.columns.get_loc("Race")
    merged_df.insert(index_reference, "Assigned Cohort", merged_df.pop("Assigned Cohort"))
    # print(merged_df)

    # IE
    IE_df = final_data["IE"][
        [
            "Subject",
            "Main Consent Date (ig_IE1.MAINCDAT)",
            "Date of Eligibility Confirmation by Physician-Investigator (ig_IE5.ELIGPIDAT)",
            "Date of Completion of Monitoring Visit for Eligibility (ig_IE5.ELIGMONDAT)",
        ]
    ].copy()
    IE_new_col_name = {
        "Main Consent Date (ig_IE1.MAINCDAT)": "Main Consent Date",
        "Date of Eligibility Confirmation by Physician-Investigator (ig_IE5.ELIGPIDAT)": "Date Physician-Investigator Confirmed Eligibility",
        "Date of Completion of Monitoring Visit for Eligibility (ig_IE5.ELIGMONDAT)": "Date of Monitoring Visit for Eligibility",
    }
    IE_df = IE_df.rename(columns=IE_new_col_name)
    merged_df = pd.merge(merged_df, IE_df, on="Subject", how="left")
    # convert date columsn to datetime type
    merged_df["Apheresis Consent Date"] = pd.to_datetime(merged_df["Apheresis Consent Date"])
    merged_df["Main Consent Date"] = pd.to_datetime(merged_df["Main Consent Date"])
    merged_df["Date of Birth"] = pd.to_datetime(merged_df["Date of Birth"])
    # Calculate time difference in days and convert to years
    # create a mask for non-NaT values in the two columns
    mask = ~merged_df[["Apheresis Consent Date", "Date of Birth"]].isnull().any(axis=1)

    # apply relativedelta only to rows with non-NaT values in both columns
    merged_df.loc[mask, "Age at Consent"] = merged_df[mask].apply(
        lambda x: relativedelta(x["Apheresis Consent Date"], x["Date of Birth"]).years, axis=1
    )
    # for rows where 'Apheresis Consent Date' isnull but 'Main Consent Date' is not null, use 'Main Consent Date' to calculate age
    merged_df.loc[
        (merged_df["Apheresis Consent Date"].isnull() & merged_df["Main Consent Date"].notnull()), "Age at Consent"
    ] = merged_df.loc[(merged_df["Apheresis Consent Date"].isnull() & merged_df["Main Consent Date"].notnull())].apply(
        lambda x: relativedelta(x["Main Consent Date"], x["Date of Birth"]).years, axis=1
    )

    merged_df["Apheresis Consent Date"] = pd.to_datetime(merged_df["Apheresis Consent Date"]).dt.strftime("%m/%d/%Y")
    merged_df["Main Consent Date"] = pd.to_datetime(merged_df["Main Consent Date"]).dt.strftime("%m/%d/%Y")
    merged_df["Date Physician-Investigator Confirmed Eligibility"] = pd.to_datetime(
        merged_df["Date Physician-Investigator Confirmed Eligibility"]
    ).dt.strftime("%m/%d/%Y")
    merged_df["Date of Monitoring Visit for Eligibility"] = pd.to_datetime(
        merged_df["Date of Monitoring Visit for Eligibility"]
    ).dt.strftime("%m/%d/%Y")
    merged_df = merged_df.drop("Date of Birth", axis=1)
    # move the column
    index_reference = merged_df.columns.get_loc("Apheresis Consent Date")
    merged_df.insert(index_reference, "Age at Consent", merged_df.pop("Age at Consent"))

    # PRAPH
    APH_df = final_data["PRAPH"][
        ["Subject", "Apheresis Type (ig_PRAPH1.APHCAT)", "Apheresis Date (ig_PRAPH1.APHDAT)"]
    ].copy()
    APH_new_col_name = {
        "Apheresis Type (ig_PRAPH1.APHCAT)": "Apheresis Type (Fresh or Historical)",
        "Apheresis Date (ig_PRAPH1.APHDAT)": "Date of Apheresis Collection",
    }
    APH_df = APH_df.rename(columns=APH_new_col_name)
    merged_df = pd.merge(merged_df, APH_df, on="Subject", how="left")
    merged_df["Date of Apheresis Collection"] = pd.to_datetime(merged_df["Date of Apheresis Collection"]).dt.strftime(
        "%m/%d/%Y"
    )
    # print(merged_df)

    # EXINF
    EXINF_df = final_data["EXINF"][["Subject", "Event Group Label", "Study Treatment Date (ig_EXINF1.INFDAT)"]].copy()
    EXINF_df = EXINF_df[EXINF_df["Event Group Label"] == "Day 0"]
    EXINF_new_col_name = {"Study Treatment Date (ig_EXINF1.INFDAT)": "CAR T cell Injection #1 Date (Day 0)"}
    EXINF_df = EXINF_df.rename(columns=EXINF_new_col_name)
    EXINF_df = EXINF_df.drop("Event Group Label", axis=1)
    merged_df = pd.merge(merged_df, EXINF_df, on="Subject", how="left")
    merged_df["CAR T cell Injection #1 Date (Day 0)"] = pd.to_datetime(
        merged_df["CAR T cell Injection #1 Date (Day 0)"]
    ).dt.strftime("%m/%d/%Y")
    # print(merged_df)

    # EXINF2
    EXINF_df = final_data["EXINF"][["Subject", "Event Group Label", "Study Treatment Date (ig_EXINF1.INFDAT)"]].copy()
    EXINF_df = EXINF_df[EXINF_df["Event Group Label"] == "Injection 2"]
    EXINF_new_col_name = {"Study Treatment Date (ig_EXINF1.INFDAT)": "CAR T cell Injection #2 Date (Day 14)"}
    EXINF_df = EXINF_df.rename(columns=EXINF_new_col_name)
    EXINF_df = EXINF_df.drop("Event Group Label", axis=1)
    merged_df = pd.merge(merged_df, EXINF_df, on="Subject", how="left")
    merged_df["CAR T cell Injection #2 Date (Day 14)"] = pd.to_datetime(
        merged_df["CAR T cell Injection #2 Date (Day 14)"]
    ).dt.strftime("%m/%d/%Y")
    # print(merged_df)

    # DSINITLF
    INITLF_df = final_data["DSINITLF"][
        [
            "Subject",
            "From which Phase is the Subject entering Long-Term Follow-Up? (ig_DSINITLF1.DSPHASE)",
            "Last Study Visit Completed in Primary Follow-Up (ig_DSINITLF1.DSLVCPFU)",
            "End of Primary Follow-Up Date (ig_DSINITLF1.DSENPFUDAT)",
        ]
    ].copy()
    INITLF_df = INITLF_df[
        INITLF_df["From which Phase is the Subject entering Long-Term Follow-Up? (ig_DSINITLF1.DSPHASE)"]
        != "Retreatment"
    ]
    INITLF_new_col_name = {
        "Last Study Visit Completed in Primary Follow-Up (ig_DSINITLF1.DSLVCPFU)": "Last Study Visit Completed in Primary Follow-Up",
        "End of Primary Follow-Up Date (ig_DSINITLF1.DSENPFUDAT)": "Initiation of LTFU Date",
    }
    INITLF_df = INITLF_df.rename(columns=INITLF_new_col_name)
    INITLF_df = INITLF_df.drop(
        "From which Phase is the Subject entering Long-Term Follow-Up? (ig_DSINITLF1.DSPHASE)", axis=1
    )
    merged_df = pd.merge(merged_df, INITLF_df, on="Subject", how="left")
    merged_df["Initiation of LTFU Date"] = pd.to_datetime(merged_df["Initiation of LTFU Date"]).dt.strftime("%m/%d/%Y")
    # print(merged_df)

    # DSINITRT
    DSINITRT_df = final_data["DSINITRT"][
        [
            "Subject",
            "Last Visit Completed in Primary Follow-Up (ig_DSINITRT1.DSLVCPFUR)",
            "Will the Subject receive Retreatment? (ig_DSINITRT1.DSRTYN)",
            "From which Phase is the Subject entering Retreatment? (ig_DSINITRT1.DSPHASER)",
            "End of Primary Follow-Up Date (ig_DSINITRT1.DSRENPFUDAT)",
            "End of Long-Term Follow-Up Date (ig_DSINITRT1.DSRENLTFUDAT)",
            "Retreatment Cycle Number (ig_DSINITRT1.RETXCYCLEINITRT)",
            "End of Retreatment Long-Term Follow-Up Date (ig_DSINITRT1.DSRENRETXLTFUDAT)",
        ]
    ].copy()

    # Rename columns
    DSINITRT_new_col_name = {
        "Will the Subject receive Retreatment? (ig_DSINITRT1.DSRTYN)": "Retreatment?",
        "From which Phase is the Subject entering Retreatment? (ig_DSINITRT1.DSPHASER)": "Phase",
        "End of Primary Follow-Up Date (ig_DSINITRT1.DSRENPFUDAT)": "Initiation of Retx Date",
    }
    DSINITRT_df = DSINITRT_df.rename(columns=DSINITRT_new_col_name)

    # Override "Retreatment?" and create "Second Retreatment?"
    DSINITRT_df.loc[
        DSINITRT_df["Retreatment Cycle Number (ig_DSINITRT1.RETXCYCLEINITRT)"] == "Retreatment-R1", "Retreatment?"
    ] = "Yes"

    DSINITRT_df["Second Retreatment?"] = None
    DSINITRT_df.loc[
        DSINITRT_df["Retreatment Cycle Number (ig_DSINITRT1.RETXCYCLEINITRT)"] == "Retreatment-R2",
        "Second Retreatment?",
    ] = "Yes"

    # Fill Initiation of Retx Date conditionally
    DSINITRT_df.loc[
        (DSINITRT_df["Initiation of Retx Date"].isna())
        & (DSINITRT_df["Retreatment Cycle Number (ig_DSINITRT1.RETXCYCLEINITRT)"] != "Retreatment-R2"),
        "Initiation of Retx Date",
    ] = DSINITRT_df["End of Long-Term Follow-Up Date (ig_DSINITRT1.DSRENLTFUDAT)"]

    DSINITRT_df.loc[
        (DSINITRT_df["Initiation of Retx Date"].isna())
        & (DSINITRT_df["Retreatment Cycle Number (ig_DSINITRT1.RETXCYCLEINITRT)"] == "Retreatment-R2"),
        "Initiation of Retx Date",
    ] = DSINITRT_df["End of Retreatment Long-Term Follow-Up Date (ig_DSINITRT1.DSRENRETXLTFUDAT)"]

    # Create separate columns for Retx 1 and Retx 2 dates
    DSINITRT_df["Initiation of Retx 1 Date"] = DSINITRT_df.loc[
        DSINITRT_df["Retreatment Cycle Number (ig_DSINITRT1.RETXCYCLEINITRT)"] == "Retreatment-R1",
        "Initiation of Retx Date",
    ]
    DSINITRT_df["Initiation of Retx 2 Date"] = DSINITRT_df.loc[
        DSINITRT_df["Retreatment Cycle Number (ig_DSINITRT1.RETXCYCLEINITRT)"] == "Retreatment-R2",
        "Initiation of Retx Date",
    ]

    # Keep only necessary columns
    DSINITRT_df = DSINITRT_df[
        [
            "Subject",
            "Last Visit Completed in Primary Follow-Up (ig_DSINITRT1.DSLVCPFUR)",
            "Retreatment?",
            "Second Retreatment?",
            "Phase",
            "Initiation of Retx 1 Date",
            "Initiation of Retx 2 Date",
        ]
    ]

    # Aggregate to one row per Subject
    DSINITRT_df = (
        DSINITRT_df.groupby("Subject").agg(lambda x: x.dropna().iloc[0] if x.notna().any() else None).reset_index()
    )

    # Merge into main dataframe
    merged_df = pd.merge(merged_df, DSINITRT_df, on="Subject", how="left")

    # Apply your N/A rule
    merged_df.loc[merged_df["Phase"] == "Primary Follow-Up", "Initiation of LTFU Date"] = "N/A"

    # Fill in visit completion data
    merged_df["Last Study Visit Completed in Primary Follow-Up"] = merged_df[
        "Last Study Visit Completed in Primary Follow-Up"
    ].fillna(merged_df["Last Visit Completed in Primary Follow-Up (ig_DSINITRT1.DSLVCPFUR)"])

    # Drop extra columns
    merged_df = merged_df.drop(
        [
            "Last Visit Completed in Primary Follow-Up (ig_DSINITRT1.DSLVCPFUR)",
            "Phase",
            #  "Retreatment Cycle Number (ig_DSINITRT1.RETXCYCLEINITRT)",
            #  "End of Retreatment Long-Term Follow-Up Date (ig_DSINITRT1.DSRENRETXLTFUDAT)",
        ],
        axis=1,
    )

    # Format dates to m/d/yyyy (no leading zeros for month/day)
    date_cols = ["Initiation of Retx 1 Date", "Initiation of Retx 2 Date"]
    for col in date_cols:
        merged_df[col] = pd.to_datetime(merged_df[col], errors="coerce").dt.strftime("%m/%d/%Y")

    # EXINF Retx Day 0-R1
    EXINF_df = final_data["EXINF"][["Subject", "Event Group Label", "Study Treatment Date (ig_EXINF1.INFDAT)"]].copy()
    EXINF_df = EXINF_df[EXINF_df["Event Group Label"] == "Day 0-R1"]
    EXINF_new_col_name = {"Study Treatment Date (ig_EXINF1.INFDAT)": "CAR T Cell Retreatment Date (Day 0-R1)"}
    EXINF_df = EXINF_df.rename(columns=EXINF_new_col_name)
    EXINF_df = EXINF_df.drop("Event Group Label", axis=1)
    merged_df = pd.merge(merged_df, EXINF_df, on="Subject", how="left")
    merged_df["CAR T Cell Retreatment Date (Day 0-R1)"] = pd.to_datetime(
        merged_df["CAR T Cell Retreatment Date (Day 0-R1)"]
    ).dt.strftime("%m/%d/%Y")
    # print(merged_df)

    # EXINF Retx Day 0-R2
    EXINF_df = final_data["EXINF"][["Subject", "Event Group Label", "Study Treatment Date (ig_EXINF1.INFDAT)"]].copy()
    EXINF_df = EXINF_df[EXINF_df["Event Group Label"] == "Day 0-R2"]
    EXINF_new_col_name = {"Study Treatment Date (ig_EXINF1.INFDAT)": "CAR T Cell Retreatment Date (Day 0-R2)"}
    EXINF_df = EXINF_df.rename(columns=EXINF_new_col_name)
    EXINF_df = EXINF_df.drop("Event Group Label", axis=1)
    merged_df = pd.merge(merged_df, EXINF_df, on="Subject", how="left")
    merged_df["CAR T Cell Retreatment Date (Day 0-R2)"] = pd.to_datetime(
        merged_df["CAR T Cell Retreatment Date (Day 0-R2)"]
    ).dt.strftime("%m/%d/%Y")
    # print(merged_df)

    # INITLF Retx
    import re

    INITLF_df = final_data["DSINITLF"][
        [
            "Subject",
            "From which Phase is the Subject entering Long-Term Follow-Up? (ig_DSINITLF1.DSPHASE)",
            "Retreatment Cycle Number (ig_DSINITLF1.RETXCYCLEINITLT)",
            "Last Study Visit Completed in Retreatment (ig_DSINITLF1.DSLVCRETX)",
            "End of Retreatment Date (ig_DSINITLF1.DSENRETXDAT)",
        ]
    ].copy()

    # Filter for Retreatment phase only
    INITLF_df = INITLF_df[
        INITLF_df["From which Phase is the Subject entering Long-Term Follow-Up? (ig_DSINITLF1.DSPHASE)"]
        == "Retreatment"
    ]

    def process_retx_cycle(df, cycle_label):
        """
        cycle_label examples: 'Retreatment-R1', 'Retreatment-R2', ...
        Produces:
        - 'Last Study Visit Completed in Retreatment (-R1)' (keeps the R)
        - 'Initiation of Retreatment 1 LTFU Date' (number comes before LTFU)
        """
        sub = df[df["Retreatment Cycle Number (ig_DSINITLF1.RETXCYCLEINITLT)"] == cycle_label].copy()
        if sub.empty:
            return sub

        suffix = cycle_label.split("-")[-1]  # e.g., 'R1'
        m = re.search(r"(\d+)$", suffix)
        n = m.group(1) if m else suffix  # e.g., '1'

        last_visit_col = f"Last Study Visit Completed in Retreatment (-{suffix})"
        ltfu_date_col = f"Initiation of Retreatment {n} LTFU Date"

        sub.rename(
            columns={
                "Last Study Visit Completed in Retreatment (ig_DSINITLF1.DSLVCRETX)": last_visit_col,
                "End of Retreatment Date (ig_DSINITLF1.DSENRETXDAT)": ltfu_date_col,
            },
            inplace=True,
        )
        sub.drop(
            [
                "From which Phase is the Subject entering Long-Term Follow-Up? (ig_DSINITLF1.DSPHASE)",
                "Retreatment Cycle Number (ig_DSINITLF1.RETXCYCLEINITLT)",
            ],
            axis=1,
            inplace=True,
        )

        # Reformat date to MM/DD/YYYY
        sub[ltfu_date_col] = pd.to_datetime(sub[ltfu_date_col], errors="coerce").dt.strftime("%m/%d/%Y")
        return sub

    # Process and merge each cycle automatically
    for cycle in INITLF_df["Retreatment Cycle Number (ig_DSINITLF1.RETXCYCLEINITLT)"].dropna().unique():
        merged_df = pd.merge(merged_df, process_retx_cycle(INITLF_df, cycle), on="Subject", how="left")

    # Safety pass: ensure any matching 'Initiation of Retreatment {n} LTFU Date' in merged_df are formatted
    for col in [
        c for c in merged_df.columns if c.startswith("Initiation of Retreatment ") and c.endswith(" LTFU Date")
    ]:
        merged_df[col] = pd.to_datetime(merged_df[col], errors="coerce").dt.strftime("%m/%d/%Y")

    # EOS
    EOS_df = final_data["DSEOS"][["Subject", "End of Study Date (ig_DSEOS1.EOSDAT)"]].copy()
    EOS_new_col_name = {"End of Study Date (ig_DSEOS1.EOSDAT)": "End of Study Date"}
    EOS_df = EOS_df.rename(columns=EOS_new_col_name)
    merged_df = pd.merge(merged_df, EOS_df, on="Subject", how="left")
    merged_df["End of Study Date"] = pd.to_datetime(merged_df["End of Study Date"]).dt.strftime("%m/%d/%Y")
    # update headers and fill N/A
    merged_df = merged_df.rename(columns={"Subject": "Subject ID#"})
    merged_df.loc[merged_df["End of Study Date"].notna(), merged_df.columns.tolist()] = merged_df.loc[
        merged_df["End of Study Date"].notna(), merged_df.columns.tolist()
    ].fillna("N/A")
    # Remove duplicate rows based on both columns
    merged_df.drop_duplicates(inplace=True)
    # return merged_df
    # select and reorder columns
    column_list = [
        "Subject ID#",
        "Assigned Cohort",
        "Race",
        "Ethnicity",
        "Sex Assigned at Birth",
        "Legal Sex",
        "Age at Consent",
        "Apheresis Consent Date",
        "Main Consent Date",
        "Date Physician-Investigator Confirmed Eligibility",
        "Date of Monitoring Visit for Eligibility",
        "Apheresis Type (Fresh or Historical)",
        "Date of Apheresis Collection",
        "CAR T cell Injection #1 Date (Day 0)",
        "CAR T cell Injection #2 Date (Day 14)",
        "Last Study Visit Completed in Primary Follow-Up",
        "Initiation of LTFU Date",
        "Retreatment?",
        "Initiation of Retx 1 Date",
        "CAR T Cell Retreatment Date (Day 0-R1)",
        "Last Study Visit Completed in Retreatment (-R1)",
        "Initiation of Retreatment 1 LTFU Date",
        "Second Retreatment?",
        "Initiation of Retx 2 Date",
        "CAR T Cell Retreatment Date (Day 0-R2)",
        "Last Study Visit Completed in Retreatment (-R2)",
        "Initiation of Retreatment 2 LTFU Date",
        "End of Study Date",
    ]
    # if merged_df does not have all the columns in column_list, add the missing columns
    for col in column_list:
        if col not in merged_df.columns:
            merged_df[col] = np.nan
    merged_df = merged_df[column_list]
    # create an empty dataframe
    output_df = pd.DataFrame()
    # merge the dataframes with the output dataframe
    output_df = pd.concat([output_df, merged_df], ignore_index=True)
    # sort based on 'Subject ID#'
    output_df = output_df.sort_values(["Subject ID#"]).reset_index(drop=True)
    # convert the date columns to string format
    # for col in output_df.columns:
    #     if "Date" in col:
    #         output_df[col] = pd.to_datetime(output_df[col])
    #         output_df[col] = output_df[col].dt.strftime("%m/%d/%Y")

    return output_df
