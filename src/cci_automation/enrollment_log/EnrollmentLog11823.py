import pandas as pd
from dateutil.relativedelta import relativedelta


def EnrollmentLog11823(final_data):
    # DM
    # Check missing
    if "DM" in final_data:
        DM_df = final_data["DM"][
            [
                "Subject",
                "Race (IG_NS_NA_DM1.CL_NS_YH_RACE_cl_NS_DMRACE1)",
                "Ethnicity (IG_NS_NA_DM1.CL_NS_NH_ETHNIC_cl_NS_DMETHNIC1)",
                "Sex Assigned at Birth (IG_NS_NA_DM1.CL_NS_NH_BRTHSEX_cl_NS_DMSEX3)",
                "Legal Sex (IG_NS_NA_DM1.CL_NS_YH_SEX_cl_NS_DMSEX1)",
                "Date of Birth (IG_NS_NA_DM1.DT_NS_NH_BRTHDAT)",
                "Apheresis Consent Date (IG_NS_NA_DM1.DT_NS_YH_RFICDAT)",
            ]
        ].copy()
        DM_new_col_name = {
            "Race (IG_NS_NA_DM1.CL_NS_YH_RACE_cl_NS_DMRACE1)": "Race",
            "Ethnicity (IG_NS_NA_DM1.CL_NS_NH_ETHNIC_cl_NS_DMETHNIC1)": "Ethnicity",
            "Sex Assigned at Birth (IG_NS_NA_DM1.CL_NS_NH_BRTHSEX_cl_NS_DMSEX3)": "Sex Assigned at Birth",
            "Legal Sex (IG_NS_NA_DM1.CL_NS_YH_SEX_cl_NS_DMSEX1)": "Legal Sex",
            "Date of Birth (IG_NS_NA_DM1.DT_NS_NH_BRTHDAT)": "Date of Birth",
            "Apheresis Consent Date (IG_NS_NA_DM1.DT_NS_YH_RFICDAT)": "Apheresis Consent Date",
        }
        DM_df = DM_df.rename(columns=DM_new_col_name)
        DM_df["Apheresis Consent Date"] = pd.to_datetime(
            DM_df["Apheresis Consent Date"]
        )
        sorted_DM_df = DM_df.sort_values(["Subject"])
        merged_df = sorted_DM_df

    # DSDLA
    if "DSDLA" in final_data:
        DSDLA_df = final_data["DSDLA"][
            [
                "Subject",
                "Dose Level Assignment (IG_NS_NA_DSDLA1.CL_NS_YH_DLADOSELV_cl_NS_DOSELV1)",
            ]
        ].copy()
        DSDLA_new_col_name = {
            "Dose Level Assignment (IG_NS_NA_DSDLA1.CL_NS_YH_DLADOSELV_cl_NS_DOSELV1)": "Assigned Dose Level"
        }
        DSDLA_df = DSDLA_df.rename(columns=DSDLA_new_col_name)
        merged_df = pd.merge(merged_df, DSDLA_df, on="Subject", how="left")
        index_reference = merged_df.columns.get_loc("Race")
        merged_df.insert(
            index_reference, "Assigned Dose Level", merged_df.pop("Assigned Dose Level")
        )

    # IE
    if "IE" in final_data:
        # Subset and rename columns simultaneously
        IE_cols_to_select = {
            "Subject": "Subject",
            "Main Consent Date (IG_NS_NA_IE1.DT_NS_NH_MAINCDAT)": "Main Consent Date",
            "Subject Meets All Study Eligibility (IG_NS_NA_IE3.CL_NS_YH_ELIGYN_cl_YS_YN1)": "Subject Meets All Study Eligibility",
            "Date of Eligibility Confirmation by Physician-Investigator (IG_NS_NA_IE5.DT_NS_YH_ELIGPIDAT)": "Date Physician-Investigator Confirmed Eligibility",
            "Date of Completion of Monitoring Visit for Eligibility (IG_NS_NA_IE5.DT_NS_YH_ELIGMONDAT)": "Date of Monitoring Visit for Eligibility",
        }
        IE_df = final_data["IE"][list(IE_cols_to_select.keys())].rename(
            columns=IE_cols_to_select
        )
        # Filter Subject Meets All Study Eligibility == Yes
        IE_df = IE_df[IE_df["Subject Meets All Study Eligibility"] == "Yes"].drop(
            "Subject Meets All Study Eligibility", axis=1
        )
        # convert date columsn to datetime type
        IE_df["Date Physician-Investigator Confirmed Eligibility"] = pd.to_datetime(
            IE_df["Date Physician-Investigator Confirmed Eligibility"]
        ).dt.strftime("%m/%d/%Y")
        IE_df["Date of Monitoring Visit for Eligibility"] = pd.to_datetime(
            IE_df["Date of Monitoring Visit for Eligibility"]
        ).dt.strftime("%m/%d/%Y")
        merged_df = pd.merge(merged_df, IE_df, on="Subject", how="left")
        merged_df["Main Consent Date"] = pd.to_datetime(merged_df["Main Consent Date"])
        merged_df["Date of Birth"] = pd.to_datetime(merged_df["Date of Birth"])

        # find mask for non-NaT values in the two columns
        mask = ~merged_df[["Apheresis Consent Date", "Date of Birth"]].isnull().any(
            axis=1
        )
        # apply relativedelta only to rows with non-NaT values in both columns
        merged_df.loc[mask, "Age at Consent"] = merged_df[mask].apply(
            lambda x: (
                relativedelta(x["Apheresis Consent Date"], x["Date of Birth"]).years
            ),
            axis=1,
        )
        # for rows that 'Apheresis Consent Date' isnull but 'Main Consent Date' is not null, then use 'Main Consent Date' instead to calculate age
        merged_df.loc[
            (
                merged_df["Apheresis Consent Date"].isnull()
                & merged_df["Main Consent Date"].notnull()
            ),
            "Age at Consent",
        ] = merged_df.loc[
            (
                merged_df["Apheresis Consent Date"].isnull()
                & merged_df["Main Consent Date"].notnull()
            )
        ].apply(
            lambda x: relativedelta(x["Main Consent Date"], x["Date of Birth"]).years,
            axis=1,
        )

        merged_df["Apheresis Consent Date"] = merged_df[
            "Apheresis Consent Date"
        ].dt.strftime("%m/%d/%Y")
        merged_df["Main Consent Date"] = merged_df["Main Consent Date"].dt.strftime(
            "%m/%d/%Y"
        )
        merged_df = merged_df.drop("Date of Birth", axis=1)
        # move the column
        index_reference = merged_df.columns.get_loc("Apheresis Consent Date")
        merged_df.insert(
            index_reference, "Age at Consent", merged_df.pop("Age at Consent")
        )

    # APH
    if "PRAPH" in final_data:
        PRAPH_cols_to_select = {
            "Subject": "Subject",
            "Event Group Label": "Event Group Label",
            "Apheresis Type (IG_NS_NA_PRAPH1.CL_NS_YH_APHTP_cl_NS_APHTP1)": "Apheresis Type (Fresh or Historical)",
            "Apheresis Date (IG_NS_NA_PRAPH1.DT_NS_NH_APHDAT)": "Date of Apheresis Collection",
        }
        PRAPH_df = final_data["PRAPH"][list(PRAPH_cols_to_select.keys())].rename(
            columns=PRAPH_cols_to_select
        )

        # Filter rows and drop unnecessary column
        PRAPH_df = PRAPH_df[
            PRAPH_df["Event Group Label"] == "Initial Study Enrollment/Apheresis"
        ].drop("Event Group Label", axis=1)
        merged_df = pd.merge(merged_df, PRAPH_df, on="Subject", how="left")
        merged_df["Date of Apheresis Collection"] = pd.to_datetime(
            merged_df["Date of Apheresis Collection"]
        ).dt.strftime("%m/%d/%Y")

    # EXCHMO
    if "EXCHMO" in final_data:
        EXCHMO_df = final_data["EXCHMO"][
            [
                "Subject",
                "Event Group Label",
                "Start Date (IG_NS_NA_EXCHMO2.DT_NS_NH_EXSTDAT)",
            ]
        ].copy()
        EXCHMO_df = EXCHMO_df[
            EXCHMO_df["Start Date (IG_NS_NA_EXCHMO2.DT_NS_NH_EXSTDAT)"] != "NaN"
        ]
        EXCHMO_df = EXCHMO_df[
            EXCHMO_df["Event Group Label"] == "Lymphodepleting Chemotherapy"
        ]
        EXCHMO_df = EXCHMO_df.drop_duplicates(subset=["Subject"])
        EXCHMO_new_col_name = {
            "Start Date (IG_NS_NA_EXCHMO2.DT_NS_NH_EXSTDAT)": "Date of Initiation of LD Chemo"
        }
        EXCHMO_df = EXCHMO_df.rename(columns=EXCHMO_new_col_name)
        EXCHMO_df = EXCHMO_df.sort_values(["Subject"])
        EXCHMO_df = EXCHMO_df.drop("Event Group Label", axis=1)
        merged_df = pd.merge(merged_df, EXCHMO_df, on="Subject", how="left")
        merged_df["Date of Initiation of LD Chemo"] = pd.to_datetime(
            merged_df["Date of Initiation of LD Chemo"]
        ).dt.strftime("%m/%d/%Y")

    # INF
    if "EXINF" in final_data:
        EXINF_df = final_data["EXINF"][
            [
                "Subject",
                "Event Group Label",
                "Infusion Date (IG_NS_NA_EXINF1.DT_NS_NH_INFDAT)",
            ]
        ].copy()
        EXINF_df = EXINF_df[EXINF_df["Event Group Label"] != "Day 0-R"]
        EXINF_new_col_name = {
            "Infusion Date (IG_NS_NA_EXINF1.DT_NS_NH_INFDAT)": "CAR T cell Infusion Date [Day 0]"
        }
        EXINF_df = EXINF_df.rename(columns=EXINF_new_col_name)
        EXINF_df = EXINF_df.drop("Event Group Label", axis=1)
        merged_df = pd.merge(merged_df, EXINF_df, on="Subject", how="left")
        merged_df["CAR T cell Infusion Date [Day 0]"] = pd.to_datetime(
            merged_df["CAR T cell Infusion Date [Day 0]"]
        ).dt.strftime("%m/%d/%Y")

    # DSINITLF
    if "DSINITLF" in final_data:
        DSINITLF_cols_to_select = {
            "Subject": "Subject",
            "From which Phase is the Subject entering Long-Term Follow-Up? (IG_NS_NA_DSINITLF1.CL_NS_NH_PHASELTFU_cl_NS_PHASE1)": "Phase Entering LTFU",
            "Last Study Visit Completed in Primary Follow-Up (IG_NS_NA_DSINITLF1.CL_NS_NH_LVCPFU_cl_YS_LVCPFU1)": "Last Study Visit Completed in Primary Follow-Up",
            "End of Primary Follow-Up Date (IG_NS_NA_DSINITLF1.DT_NS_YH_INITLFPFUENDDAT)": "Initiation of LTFU Date",
        }
        DSINITLF_df = final_data["DSINITLF"][
            list(DSINITLF_cols_to_select.keys())
        ].rename(columns=DSINITLF_cols_to_select)

        # Filter rows and drop unnecessary column
        DSINITLF_df = DSINITLF_df[
            DSINITLF_df["Phase Entering LTFU"] == "Primary Follow-Up"
        ].drop("Phase Entering LTFU", axis=1)
        # Merge dataframes
        merged_df = pd.merge(merged_df, DSINITLF_df, on="Subject", how="left")
        # Format date
        merged_df["Initiation of LTFU Date"] = pd.to_datetime(
            merged_df["Initiation of LTFU Date"]
        ).dt.strftime("%m/%d/%Y")

    # DSINITRT
    if "DSINITRT" in final_data:
        DSINITRT_cols_to_select = {
            "Subject": "Subject",
            "Last Visit Completed in Primary Follow-Up (IG_NS_NA_DSINITRT1.CL_NS_NH_RELVCPFU_cl_YS_LVCPFU1)": "Last Visit Completed in PFU",
            "From which Phase is the Subject entering Retreatment? (IG_NS_NA_DSINITRT1.CL_NS_NH_PHASER_cl_NS_PHASE2)": "Phase",
            "End of Primary Follow-Up Date (IG_NS_NA_DSINITRT1.DT_NS_YH_PFUENDDAT)": "Initiation of Retx Date",
            "End of Long-Term Follow-Up Date (IG_NS_NA_DSINITRT1.DT_NS_YH_LTFUENDDAT)": "End of Long-Term Follow-Up Date",
        }
        DSINITRT_df = final_data["DSINITRT"][
            list(DSINITRT_cols_to_select.keys())
        ].rename(columns=DSINITRT_cols_to_select)
        merged_df = pd.merge(merged_df, DSINITRT_df, on="Subject", how="left")
        # if 'Phase' = Primary Follow-Up, convert Initiation of LTFU Date to N/A
        merged_df.loc[
            merged_df["Phase"] == "Primary Follow-Up", "Initiation of LTFU Date"
        ] = "N/A"
        merged_df["Last Study Visit Completed in Primary Follow-Up"] = merged_df[
            "Last Study Visit Completed in Primary Follow-Up"
        ].fillna(merged_df["Last Visit Completed in PFU"])
        merged_df = merged_df.drop("Last Visit Completed in PFU", axis=1)
        merged_df["Initiation of Retx Date"] = merged_df[
            "Initiation of Retx Date"
        ].fillna(merged_df["End of Long-Term Follow-Up Date"])
        # drop End of Long-Term Follow-Up Date column
        merged_df = merged_df.drop(["End of Long-Term Follow-Up Date", "Phase"], axis=1)
        merged_df["Initiation of Retx Date"] = pd.to_datetime(
            merged_df["Initiation of Retx Date"]
        ).dt.strftime("%m/%d/%Y")

    # EXCHMO Retreatment
    if "EXCHMO" in final_data:
        # Subset and rename columns simultaneously
        EXCHMO_cols_to_select = {
            "Subject": "Subject",
            "Event Group Label": "Event Group Label",
            "Start Date (IG_NS_NA_EXCHMO2.DT_NS_NH_EXSTDAT)": "Date of Initiation of Retx LD Chemo",
        }
        EXCHMO_df = final_data["EXCHMO"][list(EXCHMO_cols_to_select.keys())].rename(
            columns=EXCHMO_cols_to_select
        )

        # Filter rows
        EXCHMO_df = EXCHMO_df[
            (EXCHMO_df["Date of Initiation of Retx LD Chemo"] != "NaN")
            & (
                EXCHMO_df["Event Group Label"]
                == "Retreatment Lymphodepleting Chemotherapy"
            )
        ]

        # Drop duplicates and unnecessary columns
        EXCHMO_df = EXCHMO_df.drop_duplicates(subset=["Subject"]).drop(
            "Event Group Label", axis=1
        )
        # Sort by Subject
        EXCHMO_df = EXCHMO_df.sort_values(["Subject"])
        merged_df = pd.merge(merged_df, EXCHMO_df, on="Subject", how="left")
        merged_df["Date of Initiation of Retx LD Chemo"] = pd.to_datetime(
            merged_df["Date of Initiation of Retx LD Chemo"]
        ).dt.strftime("%m/%d/%Y")

    # EXINF Retx
    if "EXINF" in final_data:
        EXINF_df = final_data["EXINF"][
            [
                "Subject",
                "Event Group Label",
                "Infusion Date (IG_NS_NA_EXINF1.DT_NS_NH_INFDAT)",
            ]
        ].copy()
        EXINF_df = EXINF_df[EXINF_df["Event Group Label"] == "Day 0-R"]
        EXINF_new_col_name = {
            "Infusion Date (IG_NS_NA_EXINF1.DT_NS_NH_INFDAT)": "CAR T cell Infusion Date [Day 0-R]"
        }
        EXINF_df = EXINF_df.rename(columns=EXINF_new_col_name)
        EXINF_df = EXINF_df.drop("Event Group Label", axis=1)
        merged_df = pd.merge(merged_df, EXINF_df, on="Subject", how="left")
        merged_df["CAR T cell Infusion Date [Day 0-R]"] = pd.to_datetime(
            merged_df["CAR T cell Infusion Date [Day 0-R]"]
        ).dt.strftime("%m/%d/%Y")

    # INITLF Retx
    if "DSINITLF" in final_data:
        # Subset and rename columns simultaneously
        DSINITLF_cols_to_select = {
            "Subject": "Subject",
            "From which Phase is the Subject entering Long-Term Follow-Up? (IG_NS_NA_DSINITLF1.CL_NS_NH_PHASELTFU_cl_NS_PHASE1)": "Phase Entering LTFU",
            "Last Study Visit Completed in Retreatment (IG_NS_NA_DSINITLF1.CL_NS_NH_LVCRETX_cl_NS_LVCPFUR1)": "Last Study Visit Completed in Retreatment",
            "End of Retreatment Date (IG_NS_NA_DSINITLF1.DT_NS_YH_RETXENDDAT)": "Initiation of Retreatment LTFU Date",
        }
        DSINITLF_df = final_data["DSINITLF"][
            list(DSINITLF_cols_to_select.keys())
        ].rename(columns=DSINITLF_cols_to_select)

        # Filter rows and drop unnecessary column
        DSINITLF_df = DSINITLF_df[
            DSINITLF_df["Phase Entering LTFU"] == "Retreatment"
        ].drop("Phase Entering LTFU", axis=1)

        # Merge dataframes
        merged_df = pd.merge(merged_df, DSINITLF_df, on="Subject", how="left")

        # Format date
        merged_df["Initiation of Retreatment LTFU Date"] = pd.to_datetime(
            merged_df["Initiation of Retreatment LTFU Date"]
        ).dt.strftime("%m/%d/%Y")

    # EOS
    if "DSEOS" in final_data:
        DSEOS_df = final_data["DSEOS"][
            ["Subject", "End of Study Date (IG_NS_NA_DSEOS1.DT_NS_YH_EOSDAT)"]
        ].copy()
        DSEOS_new_col_name = {
            "End of Study Date (IG_NS_NA_DSEOS1.DT_NS_YH_EOSDAT)": "End of Study Date"
        }
        DSEOS_df = DSEOS_df.rename(columns=DSEOS_new_col_name)
        merged_df = pd.merge(merged_df, DSEOS_df, on="Subject", how="left")
        merged_df["End of Study Date"] = pd.to_datetime(
            merged_df["End of Study Date"]
        ).dt.strftime("%m/%d/%Y")

    # Remove all duplicates
    merged_df = merged_df.drop_duplicates(subset=["Subject"])
    # update headers and fill N/A
    merged_df = merged_df.rename(columns={"Subject": "Subject ID#"})
    return merged_df
