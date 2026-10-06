#!/usr/bin/env python3

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

from cci_automation.dsmb.DSMB_util import (
    add_rename_column_corelisting,
    convert_float_2_sci_notation,
    get_stats_df,
    get_stats_percentage,
)
from cci_automation.util import (
    add_rename_column_df,
    remove_leading_zeros_from_dates,
)


def DSMB03821(
    data,
    export,
    output_dir,
    output_file_name,
    # debug,
):
    # TODO: DEMO ENROLLMENT LISTING
    if not data["DM"].empty:
        # Subject
        enrollment_df = data["DM"][["Subject"]].copy()
        enrollment_df = enrollment_df.sort_values(["Subject"])
        # Study Assignment
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "DSCA",
            "Study Phase (ig_DSCA1.CL_NS_NH_STDPHS_cl_NS_STDPHS1)",
            "Study Phase",
        )
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "DSCA",
            "Cohort/Treatment Arm Assignment (ig_DSCA1.CACHASCOD)",
            "Study Assignment",
        )
        # Disease Type
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "MHDIAG",
            "Disease Type (ig_MHDIAG1.RSCAT)",
            "Disease Type",
        )

        # Legal Sex
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "DM",
            "Legal Sex (ig_DM1.SEX)",
            "Legal Sex",
        )
        # Sex Assigned at Birth
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "DM",
            "Sex Assigned at Birth (ig_DM1.BRTHSEX)",
            "Sex Assigned at Birth",
        )
        # Gender Identity
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "DM",
            "Gender Identity (ig_DM1.GENDERID)",
            "Gender Identity",
        )
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "DM",
            "Specify Other Gender Identity (ig_DM1.GENDERIDOTH)",
            "Gender Identity SP",
        )
        enrollment_df.loc[
            enrollment_df["Gender Identity"] == "Other",
            "Gender Identity",
        ] = ""
        enrollment_df["Gender Identity SP"] = enrollment_df[
            enrollment_df["Gender Identity SP"].notna()
        ]["Gender Identity SP"].astype(str)
        enrollment_df["Gender Identity"] = enrollment_df["Gender Identity"].fillna(
            ""
        ) + enrollment_df["Gender Identity SP"].fillna("")

        enrollment_df["Gender Identity"] = enrollment_df["Gender Identity"].fillna(
            enrollment_df["Gender Identity"]
        )
        enrollment_df = enrollment_df.drop(columns=["Gender Identity SP"])
        # Age at Consent
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "DM",
            "Date of Birth (ig_DM1.BRTHDAT)",
            "Date of Birth",
        )
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "DM",
            "Apheresis Consent Date (ig_DM1.RFICDAT)",
            "Consent Date",
        )
        enrollment_df["Consent Date"] = pd.to_datetime(enrollment_df["Consent Date"])
        enrollment_df["Date of Birth"] = pd.to_datetime(enrollment_df["Date of Birth"])
        mask = ~enrollment_df[["Consent Date", "Date of Birth"]].isnull().any(axis=1)
        enrollment_df.loc[mask, "Age at Consent"] = enrollment_df[mask].apply(
            lambda x: relativedelta(x["Consent Date"], x["Date of Birth"]).years, axis=1
        )
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "IE",
            "Main Consent Date (ig_IE1.MAINCDAT)",
            "Main Consent Date",
        )
        enrollment_df["Main Consent Date"] = pd.to_datetime(
            enrollment_df["Main Consent Date"]
        )
        # for rows that 'Apheresis Consent Date' isnull but 'Main Consent Date' is not null, then use 'Main Consent Date' instead to calculate age
        enrollment_df.loc[
            (
                enrollment_df["Consent Date"].isnull()
                & enrollment_df["Main Consent Date"].notnull()
            ),
            "Age at Consent",
        ] = enrollment_df.loc[
            (
                enrollment_df["Consent Date"].isnull()
                & enrollment_df["Main Consent Date"].notnull()
            )
        ].apply(
            lambda x: relativedelta(x["Main Consent Date"], x["Date of Birth"]).years,
            axis=1,
        )

        # Race
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "DM",
            "Race (ig_DM1.RACE)",
            "Race",
        )
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "DM",
            "Specify Other or Multiple Races (ig_DM1.RACEOTH)",
            "Race other",
        )
        enrollment_df["Race1"] = enrollment_df["Race"]
        enrollment_df.loc[
            (enrollment_df["Race"] == "Other")
            | (enrollment_df["Race"] == "Multiple Races"),
            "Race1",
        ] = ""

        enrollment_df["Race"] = enrollment_df[enrollment_df["Race"].notna()][
            "Race"
        ].astype(str)
        enrollment_df["Race1"] = enrollment_df[enrollment_df["Race1"].notna()][
            "Race1"
        ].astype(str)
        enrollment_df["Race other"] = enrollment_df[
            enrollment_df["Race other"].notna()
        ]["Race other"].astype(str)

        enrollment_df["Race1"] = enrollment_df["Race1"].fillna("") + enrollment_df[
            "Race other"
        ].fillna("")
        enrollment_df["Race1"] = enrollment_df["Race1"].fillna(enrollment_df["Race1"])
        enrollment_df = enrollment_df.drop(
            columns=[
                "Race other",
            ]
        )
        # Ethnicity
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "DM",
            "Ethnicity (ig_DM1.ETHNIC)",
            "Ethnicity",
        )
        # Subject meets all study eligibility?
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "IE",
            "Subject meets all study eligibility (ig_IE3.IEYN)",
            "Subject meets all study eligibility?IE",
        )
        # Reason for Screen Failure
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "IE",
            "Other Screen Fail Reason (ig_IE4.OTHRSFREAS)",
            "SF4",
        )
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "IE",
            "Screen Failure Reason (ig_IE4.IECAT)",
            "SF1",
        )
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "IE",
            "Select the primary inclusion criterion excluding this subject  (ig_IE4.ITESTCD)",
            "SF2",
        )
        enrollment_df["SF2"] = enrollment_df[enrollment_df["SF2"].notna()][
            "SF2"
        ].astype(str)
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "IE",
            "Select the primary exclusion criterion excluding this subject (ig_IE4.ETESTCD)",
            "SF3",
        )
        enrollment_df["SF3"] = enrollment_df[enrollment_df["SF3"].notna()][
            "SF3"
        ].astype(str)
        enrollment_df["SF4"] = enrollment_df[enrollment_df["SF4"].notna()][
            "SF4"
        ].astype(str)
        enrollment_df.loc[
            enrollment_df["SF1"] == "Other",
            "SF1",
        ] = ""
        enrollment_df["Reason for Screen FailureIE"] = None
        index_reference = enrollment_df.columns.get_loc(
            "Subject meets all study eligibility?IE"
        )
        enrollment_df.insert(
            index_reference + 1,
            "Reason for Screen FailureIE",
            enrollment_df.pop("Reason for Screen FailureIE"),
        )
        enrollment_df["Reason for Screen FailureIE"] = (
            enrollment_df["SF1"].fillna("")
            #      + " "
            + enrollment_df["SF2"].fillna("")
            + enrollment_df["SF3"].fillna("")
            + enrollment_df["SF4"].fillna("")
        )
        enrollment_df["Reason for Screen FailureIE"].fillna(
            enrollment_df["Reason for Screen FailureIE"]  # , inplace=True
        )
        enrollment_df = enrollment_df.drop(columns=["SF1", "SF2", "SF3", "SF4"])

        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "DSEOS",
            "End of Study Date (ig_DSEOS1.EOSDAT)",
            "End of Study Date",
        )
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "DSEOS",
            "Did the Subject sign the main consent form? (ig_DSEOS1.SIGNMAINC)",
            "Subject meets all study eligibility?EOS",  # if subject did not sign main consent form, implies subject screen failured before IE is entered
        )
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "DSEOS",
            "Provide Supportive Information (ig_DSEOS2.EOSTERM)",
            "Reason for Screen FailureEOS",
        )
        # when subject sign main consent is not "No" in DSEOS or subject is eligible in IE, set the following 2 data from DSEOS to ""
        enrollment_df.loc[
            (enrollment_df["Subject meets all study eligibility?EOS"] != "No")
            | (enrollment_df["Subject meets all study eligibility?IE"] == "Yes"),
            "Subject meets all study eligibility?EOS",
        ] = ""
        enrollment_df.loc[
            (enrollment_df["Subject meets all study eligibility?EOS"] != "No")
            | (enrollment_df["Subject meets all study eligibility?IE"] == "Yes"),
            "Reason for Screen FailureEOS",
        ] = ""
        # combine the data from IE and DSEOS
        enrollment_df["Subject meets all study eligibility?"] = (
            enrollment_df["Subject meets all study eligibility?IE"].fillna("")
            + " "
            + enrollment_df["Subject meets all study eligibility?EOS"].fillna("")
        )
        enrollment_df["Subject meets all study eligibility?"] = enrollment_df[
            "Subject meets all study eligibility?"
        ].fillna(enrollment_df["Subject meets all study eligibility?"])
        enrollment_df = enrollment_df.drop(
            columns=[
                "Subject meets all study eligibility?IE",
                "Subject meets all study eligibility?EOS",
            ]
        )
        enrollment_df["Reason for Screen Failure"] = (
            enrollment_df["Reason for Screen FailureIE"].fillna("")
            + " "
            + enrollment_df["Reason for Screen FailureEOS"].fillna("")
        )
        enrollment_df["Reason for Screen Failure"] = enrollment_df[
            "Reason for Screen Failure"
        ].fillna(enrollment_df["Reason for Screen Failure"])
        enrollment_df = enrollment_df.drop(
            columns=[
                "Reason for Screen FailureIE",
                "Reason for Screen FailureEOS",
            ]
        )
        # Infused
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "EXMESOINF",
            "Event Group Label",
            "Event Group Label",
        )
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "EXVCNINF",
            "Was Infusion Administered? (ig_EXVCNINF1.INFOCCUR)",
            "VCN-01 Infusion",
        )
        enrollment_df = add_rename_column_corelisting(
            enrollment_df,
            data,
            "EXMESOINF",
            "Was Infusion Administered? (ig_EXMESOINF1.INFOCCUR)",
            "huCART-meso Infusion",
        )
        enrollment_df = enrollment_df[enrollment_df["Event Group Label"] != "Day 0-R"]
        enrollment_df = enrollment_df.drop(columns=["Event Group Label"])
        # Update 'Infused' column based on the conditions:
        enrollment_df.loc[
            (enrollment_df["VCN-01 Infusion"] != "Yes")
            & (enrollment_df["End of Study Date"].isnull()),
            "VCN-01 Infusion",
        ] = "Pending"
        enrollment_df.loc[
            (enrollment_df["VCN-01 Infusion"] != "Yes")
            & (~enrollment_df["End of Study Date"].isnull()),
            "VCN-01 Infusion",
        ] = "No"
        enrollment_df.loc[
            (enrollment_df["huCART-meso Infusion"] != "Yes")
            & (enrollment_df["End of Study Date"].isnull()),
            "huCART-meso Infusion",
        ] = "Pending"
        enrollment_df.loc[
            (enrollment_df["huCART-meso Infusion"] != "Yes")
            & (~enrollment_df["End of Study Date"].isnull()),
            "huCART-meso Infusion",
        ] = "No"
        # Combine VCN infused and Meso infused into one column Treated
        # Initialize the 'Treated' column
        enrollment_df["Treated"] = None

        # Define conditions and corresponding values
        conditions = [
            (enrollment_df["VCN-01 Infusion"].fillna("Unknown") == "No")
            & (enrollment_df["huCART-meso Infusion"].fillna("Unknown") == "No"),
            (enrollment_df["VCN-01 Infusion"] == "Yes")
            | (enrollment_df["huCART-meso Infusion"] == "Yes"),
            (enrollment_df["VCN-01 Infusion"] == "Pending")
            & (enrollment_df["huCART-meso Infusion"] == "Pending"),
        ]

        values = [
            "No",
            "Yes",
            "Pending",
        ]

        # Use np.select to assign values based on conditions
        enrollment_df["Treated"] = np.select(conditions, values, default="Unknown")

        enrollment_df = enrollment_df.drop_duplicates()

        ### TODO: Demo Stats Table
        # !Update this filter options to each cohort
        filter_options = [
            enrollment_df["Consent Date"].notna()
            | enrollment_df["Main Consent Date"].notna(),
            enrollment_df["Study Assignment"] == "Cohort 1",
            enrollment_df["Study Assignment"] == "Cohort 2",
            enrollment_df["Study Assignment"] == "Treatment Arm A",
            enrollment_df["Study Assignment"] == "Treatment Arm B",
        ]
        status_list = []
        LegalSex_list = []
        Age_at_Consent_list = []
        Race_list = []
        Ethnicity_list = []

        for filter_index, filter_option in enumerate(filter_options):
            # Apply the filter to the dataframe
            filtered_df = enrollment_df[filter_option].copy()
            filtered_df = filtered_df[
                (filtered_df["Consent Date"].notna())
                | (filtered_df["Main Consent Date"].notna())
            ]
            # Calculate the stats
            # Fill blank age at consent with 0

            # filtered_df["Age at Consent"] = filtered_df["Age at Consent"].fillna(0).astype(int)

            ## Total Consented
            TT_df = filtered_df.copy()
            TT = TT_df["Subject"].count()

            ## Screen Failed, convert to str and strip the space
            SF_df = filtered_df[
                filtered_df["Subject meets all study eligibility?"]
                .fillna("")
                .astype(str)
                .str.strip()
                == "No"
            ].copy()
            SF = SF_df["Subject"].count()
            # Eligible, convert to str and strip the space
            EL_df = filtered_df[
                filtered_df["Subject meets all study eligibility?"]
                .fillna("")
                .astype(str)
                .str.strip()
                == "Yes"
            ].copy()
            EL = EL_df["Subject"].count()
            ## Infused
            INFV_df = filtered_df[filtered_df["Treated"] == "Yes"].copy()
            INFV = INFV_df["Subject"].count()
            # INFM_df = filtered_df[filtered_df["huCART-meso Infusion"] == "Yes"].copy()
            # INFM = INFM_df["Subject"].count()

            # Define a dictionary containing the status of each variable
            status_list.append(
                {
                    "Total Consented": TT,
                    "Screen Failed": SF,
                    "Eligible": EL,
                    "Treated": INFV,
                    #     "huCART-meso Infusion": INFM,
                }
            )

            # Calculate the stats for the filtered dataframe
            LegalSex_list.append(
                get_stats_percentage("Legal Sex", TT_df, SF_df, EL_df, INFV_df)
            )
            Age_at_Consent_list.append(
                get_stats_df("Age at Consent", TT_df, SF_df, EL_df, INFV_df)
            )
            Race_list.append(get_stats_percentage("Race", TT_df, SF_df, EL_df, INFV_df))
            Ethnicity_list.append(
                get_stats_percentage("Ethnicity", TT_df, SF_df, EL_df, INFV_df)
            )

        # *: remove after calculating the stats
        # enrollment_df = enrollment_df.drop(columns=["Consent Date", "Date of Birth", "Main Consent Date", "Race"])
        enrollment_df = enrollment_df.drop(
            columns=["Consent Date", "Date of Birth", "Race"]
        )
        update_race_column = {"Race1": "Race"}
        enrollment_df = enrollment_df.rename(columns=update_race_column)
        ### TODO: INFUSION LISTING
        # adding Target Cell Dose dictionary
        # !: Update this dictionary to the new study, dose level for VCN-01
        TCD_dict = {
            "Cohort -1": "3.3x10^12",
            "Cohort 1": "3.3x10^12",
            "Cohort 2": "1x10^13",
            "Treatment Arm A": "Recommended Expansion Dose",  # will receive the recommended expansion dose of VCN-01, confirm with PM what dose it is for Arm A
            "Treatment Arm B": "Recommended Expansion Dose",  # will receive the recommended expansion dose of VCN-01, confirm with PM what dose it is for Arm B
            "Not Assigned": "Not Assigned",
        }

        # *: PREPARE DATA FOR INFUSION LISTING
        EXCHMO_df = data["EXCHMO"].copy()
        # select unique subject and Event Group Label
        grouped_df = EXCHMO_df.groupby(["Subject", "Event Group Label"])[
            "Medication (IG_NS_NA_EXCHMO2.CL_NS_NH_EXCCAT_cl_NS_EXCCAT1)"
        ].unique()
        # convert the unique list to string by joining the list with '+' if the list has more than 1 medication
        grouped_df = grouped_df.apply(
            lambda x: (
                " + ".join(str(val) for val in x if pd.notna(val))
                if len(x) > 1
                else x[0]
            )
        ).reset_index()
        # # replace the Event Group Label with Day 0-R
        grouped_df.loc[
            (grouped_df["Event Group Label"] == "Lymphodepleting Chemotherapy"),
            "Event Group Label",
        ] = "Day 0-R"
        # reassign the dataframe to EXCHMO_df with subject, Study Day, and Medication
        EXCHMO_df = grouped_df

        # TODO: INFUSION LISTING Infusion 2
        # Subject
        infusion_df = enrollment_df[enrollment_df["Treated"] == "Yes"]["Subject"].copy()
        infusion_df = infusion_df.sort_values()

        # # Study Assignment
        infusion_df = add_rename_column_corelisting(
            infusion_df,
            data,
            "DSCA",
            "Study Phase (ig_DSCA1.CL_NS_NH_STDPHS_cl_NS_STDPHS1)",
            "Study Phase",
        )
        infusion_df = add_rename_column_corelisting(
            infusion_df,
            data,
            "DSCA",
            "Cohort/Treatment Arm Assignment (ig_DSCA1.CACHASCOD)",
            "Study Assignment",
        )
        if not data["EXVCNINF"].empty:
            infusionV_df = data["EXVCNINF"][
                [
                    "Subject",
                    "Was Infusion Administered? (ig_EXVCNINF1.INFOCCUR)",
                    "Infusion Date (ig_EXVCNINF1.INFDAT)",
                ]
            ].copy()
            EXVCNINF_new_col_name = {
                "Was Infusion Administered? (ig_EXVCNINF1.INFOCCUR)": "VCN-01 Infusion Complete (Y/N)",
                "Infusion Date (ig_EXVCNINF1.INFDAT)": "Date of VCN-01 Infusion",
            }
            infusionV_df = infusionV_df.rename(columns=EXVCNINF_new_col_name)
            # convert the date to datetime object and format it to MM-DD-YYYY
            infusionV_df = remove_leading_zeros_from_dates(infusionV_df)
            infusion_df = pd.merge(infusion_df, infusionV_df, on="Subject", how="left")

            # adding VCN-01 Dose Received using TCD_dict
            infusion_df["VCN-01 Dose Received"] = infusion_df["Study Assignment"].map(
                TCD_dict
            )

        if not data["EXMESOINF"].empty:
            infusionM_df = data["EXMESOINF"][
                [
                    "Subject",
                    "Event Group Label",
                    "Was Infusion Administered? (ig_EXMESOINF1.INFOCCUR)",
                    "Infusion Date (ig_EXMESOINF1.INFDAT)",
                    "CAR T Cell Dose Administered (ig_EXMESOINF1.INFDOS)",
                    "x 10 to the power of (ig_EXMESOINF1.INFDOSXP)",
                    "Total Cell Dose Administered (ig_EXMESOINF1.INFDOSTOT)",
                    "x 10 to the power of (ig_EXMESOINF1.INFDOSTOTXP)",
                ]
            ].copy()
            EXMESOINF_new_col_name = {
                "Was Infusion Administered? (ig_EXMESOINF1.INFOCCUR)": "HuCART-meso Infusion Complete (Y/N)",
                "Infusion Date (ig_EXMESOINF1.INFDAT)": "Date of HuCART-meso Infusion",
                "CAR T Cell Dose Administered (ig_EXMESOINF1.INFDOS)": "Total huCART-meso Cell Dose Administered",
                "Total Cell Dose Administered (ig_EXMESOINF1.INFDOSTOT)": "Total Cell Dose Administered",
            }
            infusionM_df = infusionM_df.rename(columns=EXMESOINF_new_col_name)
            # convert the date to datetime object and format it to MM-DD-YYYY
            infusionM_df = remove_leading_zeros_from_dates(infusionM_df)
            # combine Total huCART-Meso Cell Dose Administered and x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TDOSXP_cl_YS_EX10POW1) columns
            infusionM_df["Total huCART-meso Cell Dose Administered"] = infusionM_df[
                "Total huCART-meso Cell Dose Administered"
            ].multiply(
                10 ** infusionM_df["x 10 to the power of (ig_EXMESOINF1.INFDOSXP)"]
            )
            infusionM_df = infusionM_df.drop(
                columns=["x 10 to the power of (ig_EXMESOINF1.INFDOSXP)"]
            )
            infusionM_df["Total Cell Dose Administered"] = infusionM_df[
                "Total Cell Dose Administered"
            ].multiply(
                10 ** infusionM_df["x 10 to the power of (ig_EXMESOINF1.INFDOSTOTXP)"]
            )
            infusionM_df = infusionM_df.drop(
                columns=["x 10 to the power of (ig_EXMESOINF1.INFDOSTOTXP)"]
            )
            infusionM_df = infusionM_df[
                (infusionM_df["Event Group Label"] == "Day 0")
                | (infusionM_df["Event Group Label"] == "Infusion 2")
            ]
            #  Outer join to keep subjects in infusion_df or infusionM_df
            infusion_df = pd.merge(infusion_df, infusionM_df, on="Subject", how="outer")

        # fill NaN with empty string
        pd.set_option("future.no_silent_downcasting", True)
        infusion_df = infusion_df.fillna("").infer_objects(copy=False)

        # Only keep the rows that have Event Group Label
        #  infusion_df = infusion_df[infusion_df["Event Group Label"] != ""]

        # # TODO: Infusion Listing Day 0-R

        # Subject
        infusionR_df = data["DM"][["Subject"]].copy()
        infusionR_df = infusionR_df.sort_values(["Subject"])
        infusionR_df = add_rename_column_corelisting(
            infusionR_df, data, "EXMESOINF", "Event Group Label", "Event Group Label"
        )
        infusionR_df = infusionR_df[infusionR_df["Event Group Label"] == "Day 0-R"]

        infusionR_df = add_rename_column_corelisting(
            infusionR_df,
            data,
            "DSCA",
            "Study Phase (ig_DSCA1.CL_NS_NH_STDPHS_cl_NS_STDPHS1)",
            "Study Phase",
        )
        # Study Assignment
        infusionR_df = add_rename_column_corelisting(
            infusionR_df,
            data,
            "DSCA",
            "Cohort/Treatment Arm Assignment (ig_DSCA1.CACHASCOD)",
            "Study Assignment",
        )

        # Lymphodepleting Chemotherapy Regimen
        infusionR_df = add_rename_column_df(
            infusionR_df,
            EXCHMO_df[EXCHMO_df["Event Group Label"] == "Day 0-R"],
            "EXCHMO",
            "Medication (IG_NS_NA_EXCHMO2.CL_NS_NH_EXCCAT_cl_NS_EXCCAT1)",
            "Lymphodepleting Chemotherapy Regimen",
        )
        # Set Lymphodepleting Chemotherapy Regimen to N/A for cohort 1 an cohort 2
        infusionR_df.loc[
            (infusionR_df["Study Assignment"] == "Cohort 1")
            | (infusionR_df["Study Assignment"] == "Cohort 2"),
            "Lymphodepleting Chemotherapy Regimen",
        ] = "N/A"
        # Infusion Date
        infusionR_df = add_rename_column_corelisting(
            infusionR_df,
            data,
            "EXMESOINF",
            "Infusion Date (ig_EXMESOINF1.INFDAT)",
            "Date of HuCART-meso Retreatment Infusion",
            "Subject",
            "Event Group Label",
        )
        # convert the date to datetime object and format it to MM-DD-YYYY
        infusionR_df = remove_leading_zeros_from_dates(infusionR_df)

        # Total huCart19-IL18 Cell Dose
        infusionR_df = add_rename_column_corelisting(
            infusionR_df,
            data,
            "EXMESOINF",
            "CAR T Cell Dose Administered (ig_EXMESOINF1.INFDOS)",
            "Total huCART-meso Cell Dose Administered",
            "Subject",
            "Event Group Label",
        )
        infusionR_df = add_rename_column_corelisting(
            infusionR_df,
            data,
            "EXMESOINF",
            "x 10 to the power of (ig_EXMESOINF1.INFDOSXP)",
            "x 10 to the power of (ig_EXMESOINF1.INFDOSXP)",
            "Subject",
            "Event Group Label",
        )
        # combine Total huCART-Meso Cell Dose Administered and x 10 to the power of (ig_EXMESOINF1.INFDOSXP) columns
        infusionR_df["Total huCART-meso Cell Dose Administered"] = infusionR_df[
            "Total huCART-meso Cell Dose Administered"
        ].multiply(10 ** infusionR_df["x 10 to the power of (ig_EXMESOINF1.INFDOSXP)"])
        infusionR_df = infusionR_df.drop(
            columns=["x 10 to the power of (ig_EXMESOINF1.INFDOSXP)"]
        )

        # Total Cell Dose Administered column
        infusionR_df = add_rename_column_corelisting(
            infusionR_df,
            data,
            "EXMESOINF",
            "Total Cell Dose Administered (ig_EXMESOINF1.INFDOSTOT)",
            "Total Cell Dose Administered",
            "Subject",
            "Event Group Label",
        )
        infusionR_df = add_rename_column_corelisting(
            infusionR_df,
            data,
            "EXMESOINF",
            "x 10 to the power of (ig_EXMESOINF1.INFDOSTOTXP)",
            "x 10 to the power of (ig_EXMESOINF1.INFDOSTOTXP)",
            "Subject",
            "Event Group Label",
        )
        infusionR_df["Total Cell Dose Administered"] = infusionR_df[
            "Total Cell Dose Administered"
        ].multiply(
            10 ** infusionR_df["x 10 to the power of (ig_EXMESOINF1.INFDOSTOTXP)"]
        )
        infusionR_df = infusionR_df.drop(
            columns=["x 10 to the power of (ig_EXMESOINF1.INFDOSTOTXP)"]
        )

        # fill NaN with empty string
        pd.set_option("future.no_silent_downcasting", True)
        infusionR_df = infusionR_df.fillna("").infer_objects(copy=False)

        # Only keep the rows that have Event Group Label
        infusionR_df = infusionR_df[infusionR_df["Event Group Label"] != ""]

        ## TODO: FORMATTING THE DATAFRAME
        # TODO: Day 0
        # Convert the columns to scientific notation if the value is not NaN

        infusion_df["Total huCART-meso Cell Dose Administered"] = infusion_df[
            "Total huCART-meso Cell Dose Administered"
        ].apply(
            lambda x: (
                convert_float_2_sci_notation(x)
                if not isinstance(x, str) and pd.notna(x)
                else x
            )
        )
        infusion_df["Total Cell Dose Administered"] = infusion_df[
            "Total Cell Dose Administered"
        ].apply(
            lambda x: (
                convert_float_2_sci_notation(x)
                if not isinstance(x, str) and pd.notna(x)
                else x
            )
        )

        infusionR_df["Total huCART-meso Cell Dose Administered"] = infusionR_df[
            "Total huCART-meso Cell Dose Administered"
        ].apply(
            lambda x: (
                convert_float_2_sci_notation(x)
                if not isinstance(x, str) and pd.notna(x)
                else x
            )
        )
        infusionR_df["Total Cell Dose Administered"] = infusionR_df[
            "Total Cell Dose Administered"
        ].apply(
            lambda x: (
                convert_float_2_sci_notation(x)
                if not isinstance(x, str) and pd.notna(x)
                else x
            )
        )

        # Replace "Yes" with "Y", "No" with "N"
        conditionsV = [
            (infusion_df["VCN-01 Infusion Complete (Y/N)"] == "Yes"),
            (infusion_df["VCN-01 Infusion Complete (Y/N)"] == "No")
            | (infusion_df["VCN-01 Infusion Complete (Y/N)"] == ""),
        ]

        valuesV = [
            "Y",
            "N",
        ]
        # Replace "Yes" with "Y", "No" with "N"
        conditionsM = [
            (infusion_df["HuCART-meso Infusion Complete (Y/N)"] == "Yes"),
            (infusion_df["HuCART-meso Infusion Complete (Y/N)"] == "No")
            | (infusion_df["HuCART-meso Infusion Complete (Y/N)"] == ""),
        ]

        valuesM = [
            "Y",
            "N",
        ]

        # Use np.select to assign values based on conditions
        infusion_df["VCN-01 Infusion Complete (Y/N)"] = np.select(
            conditionsV, valuesV, default="Unknown"
        )
        infusion_df["HuCART-meso Infusion Complete (Y/N)"] = np.select(
            conditionsM, valuesM, default="Unknown"
        )

        # Replace empty strings with "N/A" in the specified column
        infusion_df["Date of HuCART-meso Infusion"] = infusion_df[
            "Date of HuCART-meso Infusion"
        ].replace("", "N/A")
        infusion_df["Total huCART-meso Cell Dose Administered"] = infusion_df[
            "Total huCART-meso Cell Dose Administered"
        ].replace("", "N/A")
        infusion_df["Total Cell Dose Administered"] = infusion_df[
            "Total Cell Dose Administered"
        ].replace("", "N/A")

        # # # TODO: PREPARE
        # Filter for Cohort 1&2 response data frame
        response_df = infusion_df[
            (infusion_df["Study Assignment"] == "Cohort 1")
            | (infusion_df["Study Assignment"] == "Cohort 2")
        ]["Subject"].copy()
        response_df = response_df.sort_values()

        # Find subjects that infusion #2 did not occur
        INF2_df = infusion_df[
            (infusion_df["Event Group Label"] == "Infusion 2")
            # & (
            #     (infusion_df["VCN-01 Infusion Complete (Y/N)"].strip() == "N")
            #     | (infusion_df["HuCART-meso Infusion Complete (Y/N)"].strip() == "N")
            # )
        ].copy()
        DSEOS_df = data["DSEOS"][
            [
                "Subject",
                "Reason for End of Study? (ig_DSEOS2.EOSCOD1)",
                "Last Study Phase Completed (ig_DSEOS1.STUDYPSEOS)",
                "Last Primary Follow-Up Specific Study Timepoint Completed (ig_DSEOS1.PFUPTXTPTEOS)",
                "Last Long-Term Follow-Up Specific Study Timepoint Completed (ig_DSEOS1.LFUPTXTPTEOS)",
                "Last Primary Retreatment Follow-Up Specific Study Timepoint Completed (ig_DSEOS1.PFUPRTXTPTEOS)",
                "Last Retreatment Long-Term Follow-Up Specific Study Timepoint Completed (ig_DSEOS1.LFUPRTXTPTEOS)",
            ]
        ].copy()
        DSEOS_new_col_name = {
            "Reason for End of Study? (ig_DSEOS2.EOSCOD1)": "Off-Study Reason",
            "Last Study Phase Completed (ig_DSEOS1.STUDYPSEOS)": "Last Study Phase Completed",
            "Last Primary Follow-Up Specific Study Timepoint Completed (ig_DSEOS1.PFUPTXTPTEOS)": "Last Primary FUP",
            "Last Long-Term Follow-Up Specific Study Timepoint Completed (ig_DSEOS1.LFUPTXTPTEOS)": "Last LTFU",
            "Last Primary Retreatment Follow-Up Specific Study Timepoint Completed (ig_DSEOS1.PFUPRTXTPTEOS)": "Last Primary Retreatment",
            "Last Retreatment Long-Term Follow-Up Specific Study Timepoint Completed (ig_DSEOS1.LFUPRTXTPTEOS)": "Last Retreatment LTFU",
        }
        DSEOS_df = DSEOS_df.rename(columns=DSEOS_new_col_name)
        # End of study on primary treatment
        EOS_df = DSEOS_df[
            (DSEOS_df["Last Study Phase Completed"] == "Primary Treatment")
            | (DSEOS_df["Last Study Phase Completed"] == "Primary Follow-Up")
        ].copy()
        # Combine "Last Primary FUP" and "Last LTFU" into "Last Visit"
        EOS_df.loc[
            EOS_df["Last Study Phase Completed"] == "Primary Treatment",
            "Last Visit",
        ] = "Month 2"
        EOS_df["Last Primary FUP"] = EOS_df[EOS_df["Last Primary FUP"].notna()][
            "Last Primary FUP"
        ].astype(str)

        EOS_df["Last LTFU"] = EOS_df[EOS_df["Last LTFU"].notna()]["Last LTFU"].astype(
            str
        )

        EOS_df["Last Visit"] = None
        EOS_df["Last Visit"] = EOS_df["Last Primary FUP"].fillna("") + EOS_df[
            "Last LTFU"
        ].fillna("")
        # If subject end of study during primary tx, set last visit=Month 2
        EOS_df.loc[
            EOS_df["Last Study Phase Completed"] == "Primary Treatment",
            "Last Visit",
        ] = "Month 2"
        EOS_df = EOS_df.drop(
            columns=[
                "Last Primary FUP",
                "Last LTFU",
                "Last Study Phase Completed",
                "Last Primary Retreatment",
                "Last Retreatment LTFU",
                "Off-Study Reason",
            ]
        )

        pd.set_option("future.no_silent_downcasting", True)
        EOS_df = EOS_df.fillna("").infer_objects(copy=False)

        # End of study on retreatment
        EOSR_df = DSEOS_df[
            (
                (
                    DSEOS_df["Last Study Phase Completed"]
                    == "Primary Retreatment Follow-Up"
                )
                | (
                    DSEOS_df["Last Study Phase Completed"]
                    == "Retreatment Long-Term Follow-Up"
                )
                | (DSEOS_df["Last Study Phase Completed"] == "Retreatment")
                | (DSEOS_df["Last Study Phase Completed"] == "Pre-Retreatment")
            )
        ].copy()
        # Combine "Last Primary Retreatment" and "Last Retreatment LTFU" into "Last Visit"
        EOSR_df["Last Primary Retreatment"] = EOSR_df[
            EOSR_df["Last Primary Retreatment"].notna()
        ]["Last Primary Retreatment"].astype(str)

        EOSR_df["Last Retreatment LTFU"] = EOSR_df[
            EOSR_df["Last Retreatment LTFU"].notna()
        ]["Last Retreatment LTFU"].astype(str)

        EOSR_df["Last Visit"] = None
        EOSR_df["Last Visit"] = EOSR_df["Last Primary Retreatment"].fillna(
            ""
        ) + EOSR_df["Last Retreatment LTFU"].fillna("")
        # If subject end of study during primary Retx, set last visit= "Before Day-28R"
        EOSR_df.loc[
            (EOSR_df["Last Study Phase Completed"] == "Retreatment")
            | (EOSR_df["Last Study Phase Completed"] == "Pre-Retreatment"),
            "Last Visit",
        ] = "Before Day 28-R"
        EOSR_df = EOSR_df.drop(
            columns=[
                "Last Primary Retreatment",
                "Last Retreatment LTFU",
                "Last Study Phase Completed",
                "Last Primary FUP",
                "Last LTFU",
                "Off-Study Reason",
            ]
        )

        pd.set_option("future.no_silent_downcasting", True)
        EOSR_df = EOSR_df.fillna("").infer_objects(copy=False)

        # # Combine Last Visit from EOS_df and EOSR_df
        # DSEOS_df["Last Visit"] = EOS_df["Last Visit"].fillna("") + EOSR_df["Last Visit"].fillna("")

        response_df = add_rename_column_corelisting(
            response_df,
            data,
            "DSCA",
            "Cohort/Treatment Arm Assignment (ig_DSCA1.CACHASCOD)",
            "Study Assignment",
        )
        if not data["DSINITRT"].empty:
            # Primary FUP Response
            initRetxLastVisit_df = data["DSINITRT"][
                [
                    "Subject",
                    "Last Visit Completed in Primary Follow-Up (ig_DSINITRT1.DSLVCPFUR)",
                    "Last Visit Completed in Long-Term Follow-Up (ig_DSINITRT1.DSLVCLTFUR)",
                ]
            ].copy()
            DSINITRT_new_col_name = {
                "Last Visit Completed in Primary Follow-Up (ig_DSINITRT1.DSLVCPFUR)": "Last Visit Completed in Primary FUP",
                "Last Visit Completed in Long-Term Follow-Up (ig_DSINITRT1.DSLVCLTFUR)": "Last Visit Completed in LTFU",
            }
            initRetxLastVisit_df = initRetxLastVisit_df.rename(
                columns=DSINITRT_new_col_name
            )

            initRetxLastVisit_df["Last Visit Completed in Primary FUP"] = (
                initRetxLastVisit_df[
                    initRetxLastVisit_df["Last Visit Completed in Primary FUP"].notna()
                ]["Last Visit Completed in Primary FUP"].astype(str)
            )

            initRetxLastVisit_df["Last Visit Completed in LTFU"] = initRetxLastVisit_df[
                initRetxLastVisit_df["Last Visit Completed in LTFU"].notna()
            ]["Last Visit Completed in LTFU"].astype(str)

            initRetxLastVisit_df["Last Visit"] = None
            initRetxLastVisit_df["Last Visit"] = initRetxLastVisit_df[
                "Last Visit Completed in Primary FUP"
            ].fillna("") + initRetxLastVisit_df["Last Visit Completed in LTFU"].fillna(
                ""
            )

            initRetxLastVisit_df = initRetxLastVisit_df.drop(
                columns=[
                    "Last Visit Completed in Primary FUP",
                    "Last Visit Completed in LTFU",
                ]
            )

            pd.set_option("future.no_silent_downcasting", True)
            initRetxLastVisit_df = initRetxLastVisit_df.fillna("").infer_objects(
                copy=False
            )

        if not data["RS"].empty:
            # Primary FUP Response
            responseP_df = data["RS"][
                [
                    "Subject",
                    "Event Group Label",
                    "Study Phase (ig_STUDYPHS.STUDYPS2)",
                    "Primary Follow-Up Specific Study Timepoint (ig_STUDYPHS.PFUPTXTPT)",
                    "Primary Treatment Specific Study Timepoint (ig_STUDYPHS.PRMTXTPT)",
                    "Overall Tumor Response (ig_RS2.RSOTRESP)",
                ]
            ].copy()
            RS_new_col_name = {
                "Study Phase (ig_STUDYPHS.STUDYPS2)": "Study Phase",
                "Primary Follow-Up Specific Study Timepoint (ig_STUDYPHS.PFUPTXTPT)": "Primary Follow-Up Specific Study Timepoint",
                "Primary Treatment Specific Study Timepoint (ig_STUDYPHS.PRMTXTPT)": "Primary Treatment Specific Study Timepoint",
                "Overall Tumor Response (ig_RS2.RSOTRESP)": "Overall Tumor Response",
            }
            responseP_df = responseP_df.rename(columns=RS_new_col_name)

            drop_RSCH_columns = [
                "Event Group Label",
                "Study Phase",
                "Primary Follow-Up Specific Study Timepoint",
                "Primary Treatment Specific Study Timepoint",
            ]
            drop_RSCH_LASTV_columns = [
                "Event Group Label",
                "Study Phase",
                "Primary Follow-Up Specific Study Timepoint",
                "Primary Treatment Specific Study Timepoint",
                "Last Visit",
            ]

            Preinf_df = responseP_df[
                responseP_df["Event Group Label"] == "Pre-Infusion Safety"
            ].copy()
            Preinf_df = Preinf_df.drop(columns=drop_RSCH_columns)
            response_df = pd.merge(response_df, Preinf_df, on="Subject", how="left")

            D10PINF2_df = responseP_df[
                responseP_df["Event Group Label"] == "Day +10 Post Infusion 2"
            ].copy()

            D10PINF2_df = D10PINF2_df.drop(columns=drop_RSCH_columns)
            response_df = pd.merge(
                response_df,
                D10PINF2_df,
                on="Subject",
                how="left",
                suffixes=("", "_D10PINF2"),
            )

            response_df["Overall Tumor Response_D10PINF2"] = response_df.apply(
                lambda row: (
                    "N/A - Infusion #2 Not Received"
                    if row["Subject"] not in INF2_df["Subject"].values
                    else row["Overall Tumor Response_D10PINF2"]
                ),
                axis=1,
            )

            M3_df = responseP_df[responseP_df["Event Group Label"] == "Month 3"].copy()

            M3_df = pd.merge(M3_df, initRetxLastVisit_df, on="Subject", how="outer")

            M3_df["Overall Tumor Response"] = M3_df.apply(
                lambda row: (
                    "Transitioned to Retreatment"
                    if pd.notna(row["Last Visit"])
                    and row["Last Visit"].strip() == "Month 2"
                    else row["Overall Tumor Response"]
                ),
                axis=1,
            )
            M3_df = M3_df.drop(columns=drop_RSCH_LASTV_columns)
            M3_df = pd.merge(M3_df, EOS_df, on="Subject", how="outer")

            # Replace "Overall Tumor Response" to "Off-Study", handling possible trailing spaces and NaN values
            M3_df["Overall Tumor Response"] = M3_df.apply(
                lambda row: (
                    "Off-Study"
                    if pd.notna(row["Last Visit"])
                    and (row["Last Visit"].strip() == "Month 2")
                    else row["Overall Tumor Response"]
                ),
                axis=1,
            )
            M3_df = M3_df.drop(
                columns=[
                    "Last Visit",
                ]
            )
            response_df = pd.merge(
                response_df, M3_df, on="Subject", how="left", suffixes=("", "_M3")
            )

            M6_df = responseP_df[responseP_df["Event Group Label"] == "Month 6"].copy()
            M6_df = pd.merge(M6_df, initRetxLastVisit_df, on="Subject", how="outer")

            # Replace "Overall Tumor Response" to "Transitioned to Retreatment", handling possible trailing spaces and NaN values
            M6_df["Overall Tumor Response"] = M6_df.apply(
                lambda row: (
                    "Transitioned to Retreatment"
                    if pd.notna(row["Last Visit"])
                    and (
                        (row["Last Visit"].strip() == "Month 2")
                        | (row["Last Visit"].strip() == "Month 3")
                    )
                    else row["Overall Tumor Response"]
                ),
                axis=1,
            )
            M6_df = M6_df.drop(columns=drop_RSCH_LASTV_columns)
            M6_df = pd.merge(M6_df, EOS_df, on="Subject", how="outer")

            # Replace "Overall Tumor Response" to "Off-Study", handling possible trailing spaces and NaN values
            M6_df["Overall Tumor Response"] = M6_df.apply(
                lambda row: (
                    "Off-Study"
                    if pd.notna(row["Last Visit"])
                    and (
                        (row["Last Visit"].strip() == "Month 2")
                        | (row["Last Visit"].strip() == "Month 3")
                    )
                    else row["Overall Tumor Response"]
                ),
                axis=1,
            )
            M6_df = M6_df.drop(
                columns=[
                    "Last Visit",
                ]
            )
            response_df = pd.merge(
                response_df, M6_df, on="Subject", how="left", suffixes=("", "_M6")
            )

            M9_df = responseP_df[responseP_df["Event Group Label"] == "Month 9"].copy()
            M9_df = pd.merge(M9_df, initRetxLastVisit_df, on="Subject", how="outer")

            # Replace "Overall Tumor Response" to "Transitioned to Retreatment", handling possible trailing spaces and NaN values
            M9_df["Overall Tumor Response"] = M9_df.apply(
                lambda row: (
                    "Transitioned to Retreatment"
                    if pd.notna(row["Last Visit"])
                    and (
                        (row["Last Visit"].strip() == "Month 2")
                        | (row["Last Visit"].strip() == "Month 3")
                        | (row["Last Visit"].strip() == "Month 6")
                    )
                    else row["Overall Tumor Response"]
                ),
                axis=1,
            )
            M9_df = M9_df.drop(columns=drop_RSCH_LASTV_columns)
            M9_df = pd.merge(M9_df, EOS_df, on="Subject", how="outer")

            # Replace "Overall Tumor Response" to "Off-Study", handling possible trailing spaces and NaN values
            M9_df["Overall Tumor Response"] = M9_df.apply(
                lambda row: (
                    "Off-Study"
                    if pd.notna(row["Last Visit"])
                    and (
                        (row["Last Visit"].strip() == "Month 2")
                        | (row["Last Visit"].strip() == "Month 3")
                        | (row["Last Visit"].strip() == "Month 6")
                    )
                    else row["Overall Tumor Response"]
                ),
                axis=1,
            )
            M9_df = M9_df.drop(
                columns=[
                    "Last Visit",
                ]
            )
            response_df = pd.merge(
                response_df, M9_df, on="Subject", how="left", suffixes=("", "_M9")
            )

            M12_df = responseP_df[
                responseP_df["Event Group Label"] == "Month 12"
            ].copy()
            M12_df = pd.merge(M12_df, initRetxLastVisit_df, on="Subject", how="outer")

            # Replace "Overall Tumor Response" to "Transitioned to Retreatment", handling possible trailing spaces and NaN values
            M12_df["Overall Tumor Response"] = M12_df.apply(
                lambda row: (
                    "Transitioned to Retreatment"
                    if pd.notna(row["Last Visit"])
                    and (
                        (row["Last Visit"].strip() == "Month 2")
                        | (row["Last Visit"].strip() == "Month 3")
                        | (row["Last Visit"].strip() == "Month 6")
                        | (row["Last Visit"].strip() == "Month 9")
                    )
                    else row["Overall Tumor Response"]
                ),
                axis=1,
            )
            M12_df = M12_df.drop(columns=drop_RSCH_LASTV_columns)
            M12_df = pd.merge(M12_df, EOS_df, on="Subject", how="outer")

            # Replace "Overall Tumor Response" to "Off-Study", handling possible trailing spaces and NaN values
            M12_df["Overall Tumor Response"] = M12_df.apply(
                lambda row: (
                    "Off-Study"
                    if pd.notna(row["Last Visit"])
                    and (
                        (row["Last Visit"].strip() == "Month 2")
                        | (row["Last Visit"].strip() == "Month 3")
                        | (row["Last Visit"].strip() == "Month 6")
                        | (row["Last Visit"].strip() == "Month 9")
                    )
                    else row["Overall Tumor Response"]
                ),
                axis=1,
            )
            M12_df = M12_df.drop(
                columns=[
                    "Last Visit",
                ]
            )
            response_df = pd.merge(
                response_df, M12_df, on="Subject", how="left", suffixes=("", "_M12")
            )

            UNS_df = responseP_df[
                (responseP_df["Event Group Label"] == "Unscheduled")
                & (
                    (responseP_df["Study Phase"] == "Primary Treatment")
                    | (responseP_df["Study Phase"] == "Primary Follow-Up")
                )
            ].copy()

            # Add Day in front of unscheduedled Day#
            # Define a function to handle conversion safely
            def safe_int_conversion(value):
                try:
                    # Attempt to convert the value to an integer
                    return "Day " + str(int(value))
                except ValueError, TypeError:
                    # Return an empty string if conversion fails
                    return "Day " + str(value)

            UNS_df["Primary Follow-Up Specific Study Timepoint"] = UNS_df[
                UNS_df["Primary Follow-Up Specific Study Timepoint"].notna()
            ]["Primary Follow-Up Specific Study Timepoint"].astype(str)
            UNS_df["Primary Treatment Specific Study Timepoint"] = UNS_df[
                UNS_df["Primary Treatment Specific Study Timepoint"].notna()
            ]["Primary Treatment Specific Study Timepoint"].astype(str)

            UNS_df["Overall Tumor Response"] = (
                UNS_df["Primary Follow-Up Specific Study Timepoint"].fillna("")
                + UNS_df["Primary Treatment Specific Study Timepoint"].fillna("")
                + " "
                + UNS_df["Overall Tumor Response"].fillna("")
            )

            UNS_df = UNS_df.drop(columns=drop_RSCH_columns)
            response_df = pd.merge(
                response_df, UNS_df, on="Subject", how="left", suffixes=("", "_UNS")
            )

            pd.set_option("future.no_silent_downcasting", True)
            response_df = response_df.fillna("").infer_objects(copy=False)
            # replace "-" for blank unscheduled response
            response_df["Overall Tumor Response_UNS"] = response_df[
                "Overall Tumor Response_UNS"
            ].replace("", "-")

        # Retx FUP Response
        responseR_df = infusionR_df[
            (infusionR_df["Study Assignment"] == "Cohort 1")
            | (infusionR_df["Study Assignment"] == "Cohort 2")
        ]["Subject"].copy()
        responseR_df = responseR_df.sort_values()

        responseR_df = add_rename_column_corelisting(
            responseR_df,
            data,
            "DSCA",
            "Cohort/Treatment Arm Assignment (ig_DSCA1.CACHASCOD)",
            "Study Assignment",
        )
        responsePR_df = data["RS"][
            [
                "Subject",
                "Event Group Label",
                "Study Phase (ig_STUDYPHS.STUDYPS2)",
                "Primary Retreatment Follow-Up Specific Study Timepoint (ig_STUDYPHS.PFUPRTXTPT)",
                "For Unscheduled Primary Retreatment Follow-Up Timepoint, Specify Day # (ig_STUDYPHS.PFUPRTXUNSDAY)",
                "For Unscheduled Retreatment Long-Term Follow-Up Timepoint, Specify Day # (ig_STUDYPHS.LFUPRTXUNSDAY)",
                "Overall Tumor Response (ig_RS2.RSOTRESP)",
            ]
        ].copy()
        RSR_new_col_name = {
            "Study Phase (ig_STUDYPHS.STUDYPS2)": "Study Phase",
            "Primary Retreatment Follow-Up Specific Study Timepoint (ig_STUDYPHS.PFUPRTXTPT)": "Primary Retreatment FUP Timepoint",
            "For Unscheduled Primary Retreatment Follow-Up Timepoint, Specify Day # (ig_STUDYPHS.PFUPRTXUNSDAY)": "Unscheduled Primary Retreatment FUP Day #",
            "For Unscheduled Retreatment Long-Term Follow-Up Timepoint, Specify Day # (ig_STUDYPHS.LFUPRTXUNSDAY)": "Unscheduled Retreatment LTFU Day #",
            "Overall Tumor Response (ig_RS2.RSOTRESP)": "Overall Tumor Response",
        }
        responsePR_df = responsePR_df.rename(columns=RSR_new_col_name)

        drop_RSCHR_columns = [
            "Event Group Label",
            "Study Phase",
            "Primary Retreatment FUP Timepoint",
            "Unscheduled Primary Retreatment FUP Day #",
            "Unscheduled Retreatment LTFU Day #",
        ]
        drop_RSCHR_LASTV_columns = [
            "Event Group Label",
            "Study Phase",
            "Primary Retreatment FUP Timepoint",
            "Unscheduled Primary Retreatment FUP Day #",
            "Unscheduled Retreatment LTFU Day #",
            "Last Visit",
        ]

        PreinfR_df = responsePR_df[
            responsePR_df["Event Group Label"] == "Pre-Retreatment Safety"
        ].copy()
        PreinfR_df = PreinfR_df.drop(columns=drop_RSCHR_columns)
        responseR_df = pd.merge(responseR_df, PreinfR_df, on="Subject", how="left")

        D28R_df = responsePR_df[responsePR_df["Event Group Label"] == "Day 28-R"].copy()
        D28R_df = pd.merge(D28R_df, EOSR_df, on="Subject", how="outer")

        # Replace "Overall Tumor Response" to "Off-Study", handling possible trailing spaces and NaN values
        D28R_df["Overall Tumor Response"] = D28R_df.apply(
            lambda row: (
                "Off-Study"
                if pd.notna(row["Last Visit"])
                and (row["Last Visit"].strip() == "Before Day 28-R")
                else row["Overall Tumor Response"]
            ),
            axis=1,
        )
        D28R_df = D28R_df.drop(columns=drop_RSCHR_LASTV_columns)
        responseR_df = pd.merge(
            responseR_df, D28R_df, on="Subject", how="left", suffixes=("", "_D28R")
        )

        M3R_df = responsePR_df[responsePR_df["Event Group Label"] == "Month 3-R"].copy()
        M3R_df = pd.merge(M3R_df, EOSR_df, on="Subject", how="outer")

        # Replace "Overall Tumor Response" to "Off-Study", handling possible trailing spaces and NaN values
        M3R_df["Overall Tumor Response"] = M3R_df.apply(
            lambda row: (
                "Off-Study"
                if pd.notna(row["Last Visit"])
                and (
                    (row["Last Visit"].strip() == "Month 2-R")
                    | (row["Last Visit"].strip() == "Day 28-R")
                    | (row["Last Visit"].strip() == "Before Day 28-R")
                )
                else row["Overall Tumor Response"]
            ),
            axis=1,
        )
        M3R_df = M3R_df.drop(columns=drop_RSCHR_LASTV_columns)
        responseR_df = pd.merge(
            responseR_df, M3R_df, on="Subject", how="left", suffixes=("", "_M3R")
        )

        M6R_df = responsePR_df[responsePR_df["Event Group Label"] == "Month 6-R"].copy()
        M6R_df = pd.merge(M6R_df, EOSR_df, on="Subject", how="outer")

        # Replace "Overall Tumor Response" to "Off-Study", handling possible trailing spaces and NaN values
        M6R_df["Overall Tumor Response"] = M6R_df.apply(
            lambda row: (
                "Off-Study"
                if pd.notna(row["Last Visit"])
                and (
                    (row["Last Visit"].strip() == "Month 2-R")
                    | (row["Last Visit"].strip() == "Month 3-R")
                    | (row["Last Visit"].strip() == "Day 28-R")
                    | (row["Last Visit"].strip() == "Before Day 28-R")
                )
                else row["Overall Tumor Response"]
            ),
            axis=1,
        )

        M6R_df = M6R_df.drop(columns=drop_RSCHR_LASTV_columns)
        responseR_df = pd.merge(
            responseR_df, M6R_df, on="Subject", how="left", suffixes=("", "_M6R")
        )

        M9R_df = responsePR_df[responsePR_df["Event Group Label"] == "Month 9-R"].copy()

        M9R_df = pd.merge(M9R_df, EOSR_df, on="Subject", how="outer")

        # Replace "Overall Tumor Response" to "Off-Study", handling possible trailing spaces and NaN values
        M9R_df["Overall Tumor Response"] = M9R_df.apply(
            lambda row: (
                "Off-Study"
                if pd.notna(row["Last Visit"])
                and (
                    (row["Last Visit"].strip() == "Month 2-R")
                    | (row["Last Visit"].strip() == "Month 3-R")
                    | (row["Last Visit"].strip() == "Month 6-R")
                    | (row["Last Visit"].strip() == "Day 28-R")
                    | (row["Last Visit"].strip() == "Before Day 28-R")
                )
                else row["Overall Tumor Response"]
            ),
            axis=1,
        )

        M9R_df = M9R_df.drop(columns=drop_RSCHR_LASTV_columns)
        responseR_df = pd.merge(
            responseR_df, M9R_df, on="Subject", how="left", suffixes=("", "_M9R")
        )

        M12R_df = responsePR_df[
            responsePR_df["Event Group Label"] == "Month 12-R"
        ].copy()
        M12R_df = pd.merge(M12R_df, EOSR_df, on="Subject", how="outer")

        # Replace "Overall Tumor Response" to "Off-Study", handling possible trailing spaces and NaN values
        M12R_df["Overall Tumor Response"] = M12R_df.apply(
            lambda row: (
                "Off-Study"
                if pd.notna(row["Last Visit"])
                and (
                    (row["Last Visit"].strip() == "Month 2-R")
                    | (row["Last Visit"].strip() == "Month 3-R")
                    | (row["Last Visit"].strip() == "Month 6-R")
                    | (row["Last Visit"].strip() == "Month 9-R")
                    | (row["Last Visit"].strip() == "Day 28-R")
                    | (row["Last Visit"].strip() == "Before Day 28-R")
                )
                else row["Overall Tumor Response"]
            ),
            axis=1,
        )
        M12R_df = M12R_df.drop(columns=drop_RSCHR_LASTV_columns)
        responseR_df = pd.merge(
            responseR_df, M12R_df, on="Subject", how="left", suffixes=("", "_M12R")
        )

        UNSR_df = responsePR_df[
            (responsePR_df["Event Group Label"] == "Unscheduled")
            & (
                (responsePR_df["Study Phase"] == "Primary Retreatment Follow-Up")
                | (responsePR_df["Study Phase"] == "Retreatment Long-Term Follow-Up")
            )
        ].copy()

        pd.set_option("future.no_silent_downcasting", True)
        UNSR_df = UNSR_df.fillna("").infer_objects(copy=False)

        UNSR_df["Primary Retreatment FUP Timepoint"] = UNSR_df[
            UNSR_df["Primary Retreatment FUP Timepoint"].notna()
        ]["Primary Retreatment FUP Timepoint"].astype(str)

        UNSR_df.loc[
            UNSR_df["Primary Retreatment FUP Timepoint"] == "Unscheduled",
            "Primary Retreatment FUP Timepoint",
        ] = ""

        # Apply the function to the DataFrame
        UNSR_df["Unscheduled Primary Retreatment FUP Day #"] = UNSR_df.apply(
            lambda row: (
                safe_int_conversion(row["Unscheduled Primary Retreatment FUP Day #"])
                if pd.notna(row["Unscheduled Primary Retreatment FUP Day #"])
                and row["Unscheduled Primary Retreatment FUP Day #"] != ""
                else ""
            ),
            axis=1,
        )

        UNSR_df["Unscheduled Retreatment LTFU Day #"] = UNSR_df.apply(
            lambda row: (
                safe_int_conversion(row["Unscheduled Retreatment LTFU Day #"])
                if pd.notna(row["Unscheduled Retreatment LTFU Day #"])
                and row["Unscheduled Retreatment LTFU Day #"] != ""
                else ""
            ),
            axis=1,
        )

        UNSR_df["Overall Tumor Response"] = (
            UNSR_df["Primary Retreatment FUP Timepoint"].fillna("")
            + UNSR_df["Unscheduled Primary Retreatment FUP Day #"].fillna("")
            + UNSR_df["Unscheduled Retreatment LTFU Day #"].fillna("")
            + " "
            + UNSR_df["Overall Tumor Response"].fillna("")
        )

        UNSR_df = UNSR_df.drop(columns=drop_RSCHR_columns)
        responseR_df = pd.merge(
            responseR_df, UNSR_df, on="Subject", how="left", suffixes=("", "_UNSR")
        )

        pd.set_option("future.no_silent_downcasting", True)
        responseR_df = responseR_df.fillna("").infer_objects(copy=False)
        # replace "-" for blank unscheduled response
        responseR_df["Overall Tumor Response_UNSR"] = responseR_df[
            "Overall Tumor Response_UNSR"
        ].replace("", "-")

        # check the number of subject for cohort 1 and 2
        subject_ACH12_prim_count = len(response_df["Subject"].unique())
        subject_ACH12_primR_count = len(responseR_df["Subject"].unique())

        # Filter for Arm A and B response data frame
        responseAB_df = infusion_df[
            (infusion_df["Study Assignment"] == "Treatment Arm A")
            | (infusion_df["Study Assignment"] == "Treatment Arm B")
        ]["Subject"].copy()
        responseAB_df = responseAB_df.sort_values()

        DSEOSAB_df = data["DSEOS"][
            [
                "Subject",
                "Reason for End of Study? (ig_DSEOS2.EOSCOD1)",
                "Last Study Phase Completed (ig_DSEOS1.STUDYPSEOS)",
                "Last Primary Follow-Up Specific Study Timepoint Completed (ig_DSEOS1.PFUPTXTPTEOS)",
                "Last Long-Term Follow-Up Specific Study Timepoint Completed (ig_DSEOS1.LFUPTXTPTEOS)",
                "Last Primary Retreatment Follow-Up Specific Study Timepoint Completed (ig_DSEOS1.PFUPRTXTPTEOS)",
                "Last Retreatment Long-Term Follow-Up Specific Study Timepoint Completed (ig_DSEOS1.LFUPRTXTPTEOS)",
            ]
        ].copy()
        DSEOSAB_new_col_name = {
            "Reason for End of Study? (ig_DSEOS2.EOSCOD1)": "Off-Study Reason",
            "Last Study Phase Completed (ig_DSEOS1.STUDYPSEOS)": "Last Study Phase Completed",
            "Last Primary Follow-Up Specific Study Timepoint Completed (ig_DSEOS1.PFUPTXTPTEOS)": "Last Primary FUP",
            "Last Long-Term Follow-Up Specific Study Timepoint Completed (ig_DSEOS1.LFUPTXTPTEOS)": "Last LTFU",
            "Last Primary Retreatment Follow-Up Specific Study Timepoint Completed (ig_DSEOS1.PFUPRTXTPTEOS)": "Last Primary Retreatment",
            "Last Retreatment Long-Term Follow-Up Specific Study Timepoint Completed (ig_DSEOS1.LFUPRTXTPTEOS)": "Last Retreatment LTFU",
        }
        DSEOSAB_df = DSEOSAB_df.rename(columns=DSEOSAB_new_col_name)
        # End of study on primary treatment
        EOSAB_df = DSEOSAB_df[
            (DSEOSAB_df["Last Study Phase Completed"] == "Primary Treatment")
            | (DSEOSAB_df["Last Study Phase Completed"] == "Primary Follow-Up")
        ].copy()
        # Combine "Last Primary FUP" and "Last LTFU" into "Last Visit"
        EOSAB_df.loc[
            EOSAB_df["Last Study Phase Completed"] == "Primary Treatment",
            "Last Visit",
        ] = "Month 2"
        EOSAB_df["Last Primary FUP"] = EOSAB_df[EOSAB_df["Last Primary FUP"].notna()][
            "Last Primary FUP"
        ].astype(str)

        EOSAB_df["Last LTFU"] = EOSAB_df[EOSAB_df["Last LTFU"].notna()][
            "Last LTFU"
        ].astype(str)

        EOSAB_df["Last Visit"] = None
        EOSAB_df["Last Visit"] = EOSAB_df["Last Primary FUP"].fillna("") + EOSAB_df[
            "Last LTFU"
        ].fillna("")
        # If subject end of study during primary tx, set last visit=Month 2
        EOSAB_df.loc[
            EOSAB_df["Last Study Phase Completed"] == "Primary Treatment",
            "Last Visit",
        ] = "Month 2"
        EOSAB_df = EOSAB_df.drop(
            columns=[
                "Last Primary FUP",
                "Last LTFU",
                "Last Study Phase Completed",
                "Last Primary Retreatment",
                "Last Retreatment LTFU",
                "Off-Study Reason",
            ]
        )

        pd.set_option("future.no_silent_downcasting", True)
        EOSAB_df = EOSAB_df.fillna("").infer_objects(copy=False)

        # End of study on retreatment
        EOSRAB_df = DSEOSAB_df[
            (
                (
                    DSEOSAB_df["Last Study Phase Completed"]
                    == "Primary Retreatment Follow-Up"
                )
                | (
                    DSEOSAB_df["Last Study Phase Completed"]
                    == "Retreatment Long-Term Follow-Up"
                )
                | (DSEOSAB_df["Last Study Phase Completed"] == "Retreatment")
                | (DSEOSAB_df["Last Study Phase Completed"] == "Pre-Retreatment")
            )
        ].copy()
        # Combine "Last Primary Retreatment" and "Last Retreatment LTFU" into "Last Visit"
        EOSRAB_df["Last Primary Retreatment"] = EOSRAB_df[
            EOSRAB_df["Last Primary Retreatment"].notna()
        ]["Last Primary Retreatment"].astype(str)

        EOSRAB_df["Last Retreatment LTFU"] = EOSRAB_df[
            EOSRAB_df["Last Retreatment LTFU"].notna()
        ]["Last Retreatment LTFU"].astype(str)

        EOSRAB_df["Last Visit"] = None
        EOSRAB_df["Last Visit"] = EOSRAB_df["Last Primary Retreatment"].fillna(
            ""
        ) + EOSRAB_df["Last Retreatment LTFU"].fillna("")
        # If subject end of study during primary Retx, set last visit= "Before Day-28R"
        EOSRAB_df.loc[
            (EOSRAB_df["Last Study Phase Completed"] == "Retreatment")
            | (EOSRAB_df["Last Study Phase Completed"] == "Pre-Retreatment"),
            "Last Visit",
        ] = "Before Day 28-R"
        EOSRAB_df = EOSRAB_df.drop(
            columns=[
                "Last Primary Retreatment",
                "Last Retreatment LTFU",
                "Last Study Phase Completed",
                "Last Primary FUP",
                "Last LTFU",
                "Off-Study Reason",
            ]
        )

        pd.set_option("future.no_silent_downcasting", True)
        EOSRAB_df = EOSRAB_df.fillna("").infer_objects(copy=False)

        # Combine Last Visit from EOS_df and EOSR_df
        DSEOS_df["Last Visit"] = EOS_df["Last Visit"].fillna("") + EOSR_df[
            "Last Visit"
        ].fillna("")

        responseAB_df = add_rename_column_corelisting(
            responseAB_df,
            data,
            "DSCA",
            "Cohort/Treatment Arm Assignment (ig_DSCA1.CACHASCOD)",
            "Study Assignment",
        )
        if not data["DSINITRT"].empty:
            # Primary FUP Response
            initRetxLastVisitAB_df = data["DSINITRT"][
                [
                    "Subject",
                    "Last Visit Completed in Primary Follow-Up (ig_DSINITRT1.DSLVCPFUR)",
                    "Last Visit Completed in Long-Term Follow-Up (ig_DSINITRT1.DSLVCLTFUR)",
                ]
            ].copy()
            DSINITRTAB_new_col_name = {
                "Last Visit Completed in Primary Follow-Up (ig_DSINITRT1.DSLVCPFUR)": "Last Visit Completed in Primary FUP",
                "Last Visit Completed in Long-Term Follow-Up (ig_DSINITRT1.DSLVCLTFUR)": "Last Visit Completed in LTFU",
            }
            initRetxLastVisitAB_df = initRetxLastVisitAB_df.rename(
                columns=DSINITRTAB_new_col_name
            )

            initRetxLastVisitAB_df["Last Visit Completed in Primary FUP"] = (
                initRetxLastVisitAB_df[
                    initRetxLastVisitAB_df[
                        "Last Visit Completed in Primary FUP"
                    ].notna()
                ]["Last Visit Completed in Primary FUP"].astype(str)
            )

            initRetxLastVisitAB_df["Last Visit Completed in LTFU"] = (
                initRetxLastVisitAB_df[
                    initRetxLastVisitAB_df["Last Visit Completed in LTFU"].notna()
                ]["Last Visit Completed in LTFU"].astype(str)
            )

            initRetxLastVisitAB_df["Last Visit"] = None
            initRetxLastVisitAB_df["Last Visit"] = initRetxLastVisitAB_df[
                "Last Visit Completed in Primary FUP"
            ].fillna("") + initRetxLastVisitAB_df[
                "Last Visit Completed in LTFU"
            ].fillna("")

            initRetxLastVisitAB_df = initRetxLastVisitAB_df.drop(
                columns=[
                    "Last Visit Completed in Primary FUP",
                    "Last Visit Completed in LTFU",
                ]
            )

            pd.set_option("future.no_silent_downcasting", True)
            initRetxLastVisitAB_df = initRetxLastVisitAB_df.fillna("").infer_objects(
                copy=False
            )

        if not data["RS"].empty:
            # Primary FUP Response
            responsePAB_df = data["RS"][
                [
                    "Subject",
                    "Event Group Label",
                    "Study Phase (ig_STUDYPHS.STUDYPS2)",
                    "Primary Follow-Up Specific Study Timepoint (ig_STUDYPHS.PFUPTXTPT)",
                    "Primary Treatment Specific Study Timepoint (ig_STUDYPHS.PRMTXTPT)",
                    "For Unscheduled Primary Follow-Up Timepoint, Specify Day # (ig_STUDYPHS.PFUPTXUNSDAY)",
                    "Overall Tumor Response (ig_RS2.RSOTRESP)",
                ]
            ].copy()
            RSAB_new_col_name = {
                "Study Phase (ig_STUDYPHS.STUDYPS2)": "Study Phase",
                "Primary Follow-Up Specific Study Timepoint (ig_STUDYPHS.PFUPTXTPT)": "Primary Follow-Up Specific Study Timepoint",
                "Primary Treatment Specific Study Timepoint (ig_STUDYPHS.PRMTXTPT)": "Primary Treatment Specific Study Timepoint",
                "For Unscheduled Primary Follow-Up Timepoint, Specify Day # (ig_STUDYPHS.PFUPTXUNSDAY)": "Unscheduled Primary Follow-Up Day",
                "Overall Tumor Response (ig_RS2.RSOTRESP)": "Overall Tumor Response",
            }
            responsePAB_df = responsePAB_df.rename(columns=RSAB_new_col_name)

            drop_RS_columns = [
                "Event Group Label",
                "Study Phase",
                "Primary Follow-Up Specific Study Timepoint",
                "Primary Treatment Specific Study Timepoint",
                "Unscheduled Primary Follow-Up Day",
            ]
            drop_RS_LASTV_columns = [
                "Event Group Label",
                "Study Phase",
                "Primary Follow-Up Specific Study Timepoint",
                "Primary Treatment Specific Study Timepoint",
                "Unscheduled Primary Follow-Up Day",
                "Last Visit",
            ]

            PreinfAB_df = responsePAB_df[
                responsePAB_df["Event Group Label"] == "Pre-Infusion Safety"
            ].copy()
            PreinfAB_df = PreinfAB_df.drop(columns=drop_RS_columns)
            responseAB_df = pd.merge(
                responseAB_df, PreinfAB_df, on="Subject", how="left"
            )

            D28_df = responsePAB_df[
                responsePAB_df["Event Group Label"]
                == "Post Study Treatment Day 28 (for Arm A&B)"
            ].copy()

            D28_df = D28_df.drop(columns=drop_RS_columns)
            responseAB_df = pd.merge(
                responseAB_df, D28_df, on="Subject", how="left", suffixes=("", "_D28")
            )

            M3AB_df = responsePAB_df[
                responsePAB_df["Event Group Label"] == "Month 3"
            ].copy()

            M3AB_df = pd.merge(
                M3AB_df, initRetxLastVisitAB_df, on="Subject", how="outer"
            )

            M3AB_df["Overall Tumor Response"] = M3AB_df.apply(
                lambda row: (
                    "Transitioned to Retreatment"
                    if pd.notna(row["Last Visit"])
                    and (
                        (row["Last Visit"].strip() == "Day 28")
                        | (row["Last Visit"].strip() == "Month 2")
                    )
                    else row["Overall Tumor Response"]
                ),
                axis=1,
            )
            M3AB_df = M3AB_df.drop(columns=drop_RS_LASTV_columns)
            M3AB_df = pd.merge(M3AB_df, EOSAB_df, on="Subject", how="outer")

            # Replace "Overall Tumor Response" to "Off-Study", handling possible trailing spaces and NaN values
            M3AB_df["Overall Tumor Response"] = M3AB_df.apply(
                lambda row: (
                    "Off-Study"
                    if pd.notna(row["Last Visit"])
                    and (
                        (row["Last Visit"].strip() == "Day 28")
                        | (row["Last Visit"].strip() == "Month 2")
                    )
                    else row["Overall Tumor Response"]
                ),
                axis=1,
            )
            M3AB_df = M3AB_df.drop(
                columns=[
                    "Last Visit",
                ]
            )
            responseAB_df = pd.merge(
                responseAB_df, M3AB_df, on="Subject", how="left", suffixes=("", "_M3AB")
            )

            M6AB_df = responsePAB_df[
                responsePAB_df["Event Group Label"] == "Month 6"
            ].copy()
            M6AB_df = pd.merge(
                M6AB_df, initRetxLastVisitAB_df, on="Subject", how="outer"
            )

            # Replace "Overall Tumor Response" to "Transitioned to Retreatment", handling possible trailing spaces and NaN values
            M6AB_df["Overall Tumor Response"] = M6AB_df.apply(
                lambda row: (
                    "Transitioned to Retreatment"
                    if pd.notna(row["Last Visit"])
                    and (
                        (row["Last Visit"].strip() == "Day 28")
                        | (row["Last Visit"].strip() == "Month 2")
                        | (row["Last Visit"].strip() == "Month 3")
                    )
                    else row["Overall Tumor Response"]
                ),
                axis=1,
            )
            M6AB_df = M6AB_df.drop(columns=drop_RS_LASTV_columns)
            M6AB_df = pd.merge(M6AB_df, EOSAB_df, on="Subject", how="outer")

            # Replace "Overall Tumor Response" to "Off-Study", handling possible trailing spaces and NaN values
            M6AB_df["Overall Tumor Response"] = M6AB_df.apply(
                lambda row: (
                    "Off-Study"
                    if pd.notna(row["Last Visit"])
                    and (
                        (row["Last Visit"].strip() == "Day 28")
                        | (row["Last Visit"].strip() == "Month 2")
                        | (row["Last Visit"].strip() == "Month 3")
                    )
                    else row["Overall Tumor Response"]
                ),
                axis=1,
            )
            M6AB_df = M6AB_df.drop(
                columns=[
                    "Last Visit",
                ]
            )
            responseAB_df = pd.merge(
                responseAB_df, M6AB_df, on="Subject", how="left", suffixes=("", "_M6AB")
            )

            M9AB_df = responsePAB_df[
                responsePAB_df["Event Group Label"] == "Month 9"
            ].copy()
            M9AB_df = pd.merge(
                M9AB_df, initRetxLastVisitAB_df, on="Subject", how="outer"
            )

            # Replace "Overall Tumor Response" to "Transitioned to Retreatment", handling possible trailing spaces and NaN values
            M9AB_df["Overall Tumor Response"] = M9AB_df.apply(
                lambda row: (
                    "Transitioned to Retreatment"
                    if pd.notna(row["Last Visit"])
                    and (
                        (row["Last Visit"].strip() == "Day 28")
                        | (row["Last Visit"].strip() == "Month 2")
                        | (row["Last Visit"].strip() == "Month 3")
                        | (row["Last Visit"].strip() == "Month 6")
                    )
                    else row["Overall Tumor Response"]
                ),
                axis=1,
            )
            M9AB_df = M9AB_df.drop(columns=drop_RS_LASTV_columns)
            M9AB_df = pd.merge(M9AB_df, EOSAB_df, on="Subject", how="outer")

            # Replace "Overall Tumor Response" to "Off-Study", handling possible trailing spaces and NaN values
            M9AB_df["Overall Tumor Response"] = M9AB_df.apply(
                lambda row: (
                    "Off-Study"
                    if pd.notna(row["Last Visit"])
                    and (
                        (row["Last Visit"].strip() == "Day 28")
                        | (row["Last Visit"].strip() == "Month 2")
                        | (row["Last Visit"].strip() == "Month 3")
                        | (row["Last Visit"].strip() == "Month 6")
                    )
                    else row["Overall Tumor Response"]
                ),
                axis=1,
            )
            M9AB_df = M9AB_df.drop(
                columns=[
                    "Last Visit",
                ]
            )
            responseAB_df = pd.merge(
                responseAB_df, M9AB_df, on="Subject", how="left", suffixes=("", "_M9AB")
            )

            M12AB_df = responsePAB_df[
                responsePAB_df["Event Group Label"] == "Month 12"
            ].copy()
            M12AB_df = pd.merge(
                M12AB_df, initRetxLastVisitAB_df, on="Subject", how="outer"
            )

            # Replace "Overall Tumor Response" to "Transitioned to Retreatment", handling possible trailing spaces and NaN values
            M12AB_df["Overall Tumor Response"] = M12AB_df.apply(
                lambda row: (
                    "Transitioned to Retreatment"
                    if pd.notna(row["Last Visit"])
                    and (
                        (row["Last Visit"].strip() == "Day 28")
                        | (row["Last Visit"].strip() == "Month 2")
                        | (row["Last Visit"].strip() == "Month 3")
                        | (row["Last Visit"].strip() == "Month 6")
                        | (row["Last Visit"].strip() == "Month 9")
                    )
                    else row["Overall Tumor Response"]
                ),
                axis=1,
            )
            M12AB_df = M12AB_df.drop(columns=drop_RS_LASTV_columns)
            M12AB_df = pd.merge(M12AB_df, EOSAB_df, on="Subject", how="outer")

            # Replace "Overall Tumor Response" to "Off-Study", handling possible trailing spaces and NaN values
            M12AB_df["Overall Tumor Response"] = M12AB_df.apply(
                lambda row: (
                    "Off-Study"
                    if pd.notna(row["Last Visit"])
                    and (
                        (row["Last Visit"].strip() == "Day 28")
                        | (row["Last Visit"].strip() == "Month 2")
                        | (row["Last Visit"].strip() == "Month 3")
                        | (row["Last Visit"].strip() == "Month 6")
                        | (row["Last Visit"].strip() == "Month 9")
                    )
                    else row["Overall Tumor Response"]
                ),
                axis=1,
            )
            M12AB_df = M12AB_df.drop(
                columns=[
                    "Last Visit",
                ]
            )
            responseAB_df = pd.merge(
                responseAB_df,
                M12AB_df,
                on="Subject",
                how="left",
                suffixes=("", "_M12AB"),
            )

            UNSAB_df = responsePAB_df[
                (responsePAB_df["Event Group Label"] == "Unscheduled")
                & (
                    (responsePAB_df["Study Phase"] == "Primary Treatment")
                    | (responsePAB_df["Study Phase"] == "Primary Follow-Up")
                )
            ].copy()

            pd.set_option("future.no_silent_downcasting", True)
            UNSAB_df = UNSAB_df.fillna("").infer_objects(copy=False)

            UNSAB_df["Primary Follow-Up Specific Study Timepoint"] = UNSAB_df[
                UNSAB_df["Primary Follow-Up Specific Study Timepoint"].notna()
            ]["Primary Follow-Up Specific Study Timepoint"].astype(str)

            UNSAB_df.loc[
                UNSAB_df["Primary Follow-Up Specific Study Timepoint"] == "Unscheduled",
                "Primary Follow-Up Specific Study Timepoint",
            ] = ""

            UNSAB_df["Primary Treatment Specific Study Timepoint"] = UNSAB_df[
                UNSAB_df["Primary Treatment Specific Study Timepoint"].notna()
            ]["Primary Treatment Specific Study Timepoint"].astype(str)

            # Apply the function to the DataFrame
            UNSAB_df["Unscheduled Primary Follow-Up Day"] = UNSAB_df.apply(
                lambda row: (
                    safe_int_conversion(row["Unscheduled Primary Follow-Up Day"])
                    if pd.notna(row["Unscheduled Primary Follow-Up Day"])
                    and row["Unscheduled Primary Follow-Up Day"] != ""
                    else ""
                ),
                axis=1,
            )

            UNSAB_df["Overall Tumor Response"] = (
                UNSAB_df["Primary Follow-Up Specific Study Timepoint"].fillna("")
                + UNSAB_df["Primary Treatment Specific Study Timepoint"].fillna("")
                + UNSAB_df["Unscheduled Primary Follow-Up Day"].fillna("")
                + " "
                + UNSAB_df["Overall Tumor Response"].fillna("")
            )

            UNSAB_df = UNSAB_df.drop(columns=drop_RS_columns)
            responseAB_df = pd.merge(
                responseAB_df,
                UNSAB_df,
                on="Subject",
                how="left",
                suffixes=("", "_UNSAB"),
            )

            pd.set_option("future.no_silent_downcasting", True)
            responseAB_df = responseAB_df.fillna("").infer_objects(copy=False)
            # replace "-" for blank unscheduled response
            responseAB_df["Overall Tumor Response_UNSAB"] = responseAB_df[
                "Overall Tumor Response_UNSAB"
            ].replace("", "-")

        # Retx FUP Response for Arm A and B
        responseRAB_df = infusionR_df[
            (infusionR_df["Study Assignment"] == "Treatment Arm A")
            | (infusionR_df["Study Assignment"] == "Treatment Arm B")
        ]["Subject"].copy()
        responseRAB_df = responseRAB_df.sort_values()

        responseRAB_df = add_rename_column_corelisting(
            responseRAB_df,
            data,
            "DSCA",
            "Cohort/Treatment Arm Assignment (ig_DSCA1.CACHASCOD)",
            "Study Assignment",
        )
        responsePRAB_df = data["RS"][
            [
                "Subject",
                "Event Group Label",
                "Study Phase (ig_STUDYPHS.STUDYPS2)",
                "Retreatment Specific Study Timepoint (ig_STUDYPHS.RTXTPT)",
                "Primary Retreatment Follow-Up Specific Study Timepoint (ig_STUDYPHS.PFUPRTXTPT)",
                "For Unscheduled Primary Retreatment Follow-Up Timepoint, Specify Day # (ig_STUDYPHS.PFUPRTXUNSDAY)",
                "For Unscheduled Retreatment Long-Term Follow-Up Timepoint, Specify Day # (ig_STUDYPHS.LFUPRTXUNSDAY)",
                "Overall Tumor Response (ig_RS2.RSOTRESP)",
            ]
        ].copy()
        RSRAB_new_col_name = {
            "Study Phase (ig_STUDYPHS.STUDYPS2)": "Study Phase",
            "Retreatment Specific Study Timepoint (ig_STUDYPHS.RTXTPT)": "Retreatment Specific Study Timepoint",
            "Primary Retreatment Follow-Up Specific Study Timepoint (ig_STUDYPHS.PFUPRTXTPT)": "Primary Retreatment FUP Timepoint",
            "For Unscheduled Primary Retreatment Follow-Up Timepoint, Specify Day # (ig_STUDYPHS.PFUPRTXUNSDAY)": "Unscheduled Primary Retreatment FUP Day #",
            "For Unscheduled Retreatment Long-Term Follow-Up Timepoint, Specify Day # (ig_STUDYPHS.LFUPRTXUNSDAY)": "Unscheduled Retreatment LTFU Day #",
            "Overall Tumor Response (ig_RS2.RSOTRESP)": "Overall Tumor Response",
        }
        responsePRAB_df = responsePRAB_df.rename(columns=RSRAB_new_col_name)

        # Define columns need to be dropped for RSAB_df
        drop_RSAB_columns = [
            "Event Group Label",
            "Study Phase",
            "Primary Retreatment FUP Timepoint",
            "Unscheduled Primary Retreatment FUP Day #",
            "Unscheduled Retreatment LTFU Day #",
            "Retreatment Specific Study Timepoint",
        ]
        drop_RSAB_LASTV_columns = [
            "Event Group Label",
            "Study Phase",
            "Primary Retreatment FUP Timepoint",
            "Unscheduled Primary Retreatment FUP Day #",
            "Unscheduled Retreatment LTFU Day #",
            "Retreatment Specific Study Timepoint",
            "Last Visit",
        ]

        PreinfRAB_df = responsePRAB_df[
            responsePR_df["Event Group Label"] == "Pre-Retreatment Safety"
        ].copy()
        PreinfRAB_df = PreinfRAB_df.drop(columns=drop_RSAB_columns)
        responseRAB_df = pd.merge(
            responseRAB_df, PreinfRAB_df, on="Subject", how="left"
        )

        D28RAB_df = responsePRAB_df[
            responsePRAB_df["Event Group Label"] == "Day 28-R"
        ].copy()
        D28RAB_df = pd.merge(D28RAB_df, EOSRAB_df, on="Subject", how="outer")

        # Replace "Overall Tumor Response" to "Off-Study", handling possible trailing spaces and NaN values
        D28RAB_df["Overall Tumor Response"] = D28RAB_df.apply(
            lambda row: (
                "Off-Study"
                if pd.notna(row["Last Visit"])
                and (row["Last Visit"].strip() == "Before Day 28-R")
                else row["Overall Tumor Response"]
            ),
            axis=1,
        )
        D28RAB_df = D28RAB_df.drop(columns=drop_RSAB_LASTV_columns)
        responseRAB_df = pd.merge(
            responseRAB_df,
            D28RAB_df,
            on="Subject",
            how="left",
            suffixes=("", "_D28RAB"),
        )

        M3RAB_df = responsePRAB_df[
            responsePRAB_df["Event Group Label"] == "Month 3-R"
        ].copy()
        M3RAB_df = pd.merge(M3RAB_df, EOSRAB_df, on="Subject", how="outer")

        # Replace "Overall Tumor Response" to "Off-Study", handling possible trailing spaces and NaN values
        M3RAB_df["Overall Tumor Response"] = M3RAB_df.apply(
            lambda row: (
                "Off-Study"
                if pd.notna(row["Last Visit"])
                and (
                    (row["Last Visit"].strip() == "Month 2-R")
                    | (row["Last Visit"].strip() == "Day 28-R")
                    | (row["Last Visit"].strip() == "Before Day 28-R")
                )
                else row["Overall Tumor Response"]
            ),
            axis=1,
        )
        M3RAB_df = M3RAB_df.drop(columns=drop_RSAB_LASTV_columns)
        responseRAB_df = pd.merge(
            responseRAB_df, M3RAB_df, on="Subject", how="left", suffixes=("", "_M3RAB")
        )

        M6RAB_df = responsePRAB_df[
            responsePRAB_df["Event Group Label"] == "Month 6-R"
        ].copy()
        M6RAB_df = pd.merge(M6RAB_df, EOSRAB_df, on="Subject", how="outer")

        # Replace "Overall Tumor Response" to "Off-Study", handling possible trailing spaces and NaN values
        M6RAB_df["Overall Tumor Response"] = M6RAB_df.apply(
            lambda row: (
                "Off-Study"
                if pd.notna(row["Last Visit"])
                and (
                    (row["Last Visit"].strip() == "Month 2-R")
                    | (row["Last Visit"].strip() == "Month 3-R")
                    | (row["Last Visit"].strip() == "Day 28-R")
                    | (row["Last Visit"].strip() == "Before Day 28-R")
                )
                else row["Overall Tumor Response"]
            ),
            axis=1,
        )

        M6RAB_df = M6RAB_df.drop(columns=drop_RSAB_LASTV_columns)
        responseRAB_df = pd.merge(
            responseRAB_df, M6RAB_df, on="Subject", how="left", suffixes=("", "_M6RAB")
        )

        M9RAB_df = responsePRAB_df[
            responsePRAB_df["Event Group Label"] == "Month 9-R"
        ].copy()

        M9RAB_df = pd.merge(M9RAB_df, EOSRAB_df, on="Subject", how="outer")

        # Replace "Overall Tumor Response" to "Off-Study", handling possible trailing spaces and NaN values
        M9RAB_df["Overall Tumor Response"] = M9RAB_df.apply(
            lambda row: (
                "Off-Study"
                if pd.notna(row["Last Visit"])
                and (
                    (row["Last Visit"].strip() == "Month 2-R")
                    | (row["Last Visit"].strip() == "Month 3-R")
                    | (row["Last Visit"].strip() == "Month 6-R")
                    | (row["Last Visit"].strip() == "Day 28-R")
                    | (row["Last Visit"].strip() == "Before Day 28-R")
                )
                else row["Overall Tumor Response"]
            ),
            axis=1,
        )

        M9RAB_df = M9RAB_df.drop(columns=drop_RSAB_LASTV_columns)
        responseRAB_df = pd.merge(
            responseRAB_df, M9RAB_df, on="Subject", how="left", suffixes=("", "_M9RAB")
        )

        M12RAB_df = responsePRAB_df[
            responsePRAB_df["Event Group Label"] == "Month 12-R"
        ].copy()
        M12RAB_df = pd.merge(M12RAB_df, EOSRAB_df, on="Subject", how="outer")

        # Replace "Overall Tumor Response" to "Off-Study", handling possible trailing spaces and NaN values
        M12RAB_df["Overall Tumor Response"] = M12RAB_df.apply(
            lambda row: (
                "Off-Study"
                if pd.notna(row["Last Visit"])
                and (
                    (row["Last Visit"].strip() == "Month 2-R")
                    | (row["Last Visit"].strip() == "Month 3-R")
                    | (row["Last Visit"].strip() == "Month 6-R")
                    | (row["Last Visit"].strip() == "Month 9-R")
                    | (row["Last Visit"].strip() == "Day 28-R")
                    | (row["Last Visit"].strip() == "Before Day 28-R")
                )
                else row["Overall Tumor Response"]
            ),
            axis=1,
        )
        M12RAB_df = M12RAB_df.drop(columns=drop_RSAB_LASTV_columns)
        responseRAB_df = pd.merge(
            responseRAB_df,
            M12RAB_df,
            on="Subject",
            how="left",
            suffixes=("", "_M12RAB"),
        )

        UNSRAB_df = responsePRAB_df[
            (responsePRAB_df["Event Group Label"] == "Unscheduled")
            & (
                (responsePRAB_df["Study Phase"] == "Primary Retreatment Follow-Up")
                | (responsePRAB_df["Study Phase"] == "Retreatment Long-Term Follow-Up")
                | (responsePRAB_df["Study Phase"] == "Retreatment")
            )
        ].copy()

        pd.set_option("future.no_silent_downcasting", True)
        UNSRAB_df = UNSRAB_df.fillna("").infer_objects(copy=False)

        UNSRAB_df["Retreatment Specific Study Timepoint"] = UNSRAB_df[
            UNSRAB_df["Retreatment Specific Study Timepoint"].notna()
        ]["Retreatment Specific Study Timepoint"].astype(str)

        UNSRAB_df["Primary Retreatment FUP Timepoint"] = UNSRAB_df[
            UNSRAB_df["Primary Retreatment FUP Timepoint"].notna()
        ]["Primary Retreatment FUP Timepoint"].astype(str)

        UNSRAB_df.loc[
            UNSRAB_df["Primary Retreatment FUP Timepoint"] == "Unscheduled",
            "Primary Retreatment FUP Timepoint",
        ] = ""

        UNSRAB_df["Unscheduled Primary Retreatment FUP Day #"] = UNSRAB_df.apply(
            lambda row: (
                safe_int_conversion(row["Unscheduled Primary Retreatment FUP Day #"])
                if pd.notna(row["Unscheduled Primary Retreatment FUP Day #"])
                and row["Unscheduled Primary Retreatment FUP Day #"] != ""
                else ""
            ),
            axis=1,
        )

        UNSRAB_df["Unscheduled Retreatment LTFU Day #"] = UNSRAB_df.apply(
            lambda row: (
                safe_int_conversion(row["Unscheduled Retreatment LTFU Day #"])
                if pd.notna(row["Unscheduled Retreatment LTFU Day #"])
                and row["Unscheduled Retreatment LTFU Day #"] != ""
                else ""
            ),
            axis=1,
        )

        # Convert each column to string and fill NaN values with an empty string
        UNSRAB_df["Overall Tumor Response"] = (
            UNSRAB_df["Primary Retreatment FUP Timepoint"].astype(str).fillna("")
            + UNSRAB_df["Unscheduled Primary Retreatment FUP Day #"]
            .astype(str)
            .fillna("")
            + UNSRAB_df["Unscheduled Retreatment LTFU Day #"].astype(str).fillna("")
            + UNSRAB_df["Retreatment Specific Study Timepoint"].astype(str).fillna("")
            + " "
            + UNSRAB_df["Overall Tumor Response"].astype(str).fillna("")
        )

        UNSRAB_df = UNSRAB_df.drop(columns=drop_RSAB_columns)
        responseRAB_df = pd.merge(
            responseRAB_df,
            UNSRAB_df,
            on="Subject",
            how="left",
            suffixes=("", "_UNSRAB"),
        )

        pd.set_option("future.no_silent_downcasting", True)
        responseRAB_df = responseRAB_df.fillna("").infer_objects(copy=False)
        # replace "-" for blank unscheduled response
        responseRAB_df["Overall Tumor Response_UNSRAB"] = responseRAB_df[
            "Overall Tumor Response_UNSRAB"
        ].replace("", "-")

        # check the number of subject for cohort 1 and 2
        subject_ACH12_prim_count = len(response_df["Subject"].unique())
        subject_ACH12_primR_count = len(responseR_df["Subject"].unique())

        # check the number of subject for Arm A and B
        subject_ARMAB_prim_count = len(responseAB_df["Subject"].unique())
        subject_ARMAB_primR_count = len(responseRAB_df["Subject"].unique())

        # AE and SAE data
        #    if not data["AE"].empty:
        AE_df = data["AE"][
            [
                "Subject",
                "AE or SAE? (ig_AE2.AESEV)",
            ]
        ].copy()
        AE_new_col_name = {
            "AE or SAE? (ig_AE2.AESEV)": "AE or SAE?",
        }
        AE_df = AE_df.rename(columns=AE_new_col_name)

        # # replaces all occurrences of NaN, positive infinity, and negative infinity in the infusion_df dataframe with empty strings.
        # infusion_df = infusion_df.replace([np.nan, np.inf, -np.inf], "N/A")
        status_df = enrollment_df[
            enrollment_df["Subject meets all study eligibility?"].str.strip() == "Yes"
        ][["Subject", "Study Assignment"]]

        # Check filtered_AE_df if the subject of status_df is in the filtered_AE dataframe. If yes, then add 'Y' to the column 'AE' in infusion_df, else add 'N'
        status_df["AE"] = status_df["Subject"].apply(
            lambda x: "Y" if x in AE_df["Subject"].values else "N"
        )
        # Check filtered_AE_df if the subject of infusion_df has SAE in column 'AE or SAE?' . If yes, then add 'Y' to the column 'SAE', else add 'N'
        status_df["SAE"] = status_df["Subject"].apply(
            lambda x: (
                "Y"
                if x in AE_df[AE_df["AE or SAE?"] == "SAE"]["Subject"].values
                else "N"
            )
        )
        # replaces all occurrences of NaN, positive infinity, and negative infinity in the infusion_df dataframe with empty strings.
        status_df = status_df.replace([np.nan, np.inf, -np.inf], "")

        # Event Label Update dictionary
        event_1_dict = {
            "Pre-Infusion Safety": "Pre-Treatment",
            "Infusion 2 Safety Follow-up for Cohorts 1 and 2": "Primary Follow-up",
            "Infusions and Safety Follow-up for Cohorts 1 and 2": "Primary Follow-up",
            "Arm A&B Infusions and Safety Follow-up": "Primary Follow-up",
            "Arm A&B Infusion 2 Safety Follow-up": "Primary Follow-up",
            "Post Study Treatment": "Primary Follow-up",
            "Post Study Treatment Day 28 (for Arm A&B)": "Primary Follow-up",
            "Long Term Follow-up Months 3-60": "LTFU",
            "Pre-Retreatment Safety": "Pre-Retreatment",
            "Lymphodepleting Chemotherapy": "Pre-Retreatment",
            "Primary Retreatment Follow-up": "Primary Retreatment Follow-up",
            "Retreatment Infusion and Safety Follow-up": "Primary Retreatment Follow-up",
            "Retreatment Long Term Follow-up Months 3-60": "Retreatment LTFU",
        }

        # Getting Study Status dataframe from SV, column Subject, Event Label and Event Date
        status_SV_df = data["DSSV"][["Subject", "Event Label", "Event Date"]]
        # Getting Study Status dataframe from DSSVLTFU, column Subject, Event Label and Event Date
        status_DSSVLTFU_df = data["DSSVLTFU"][["Subject", "Event Label", "Event Date"]]

        # status_DSSVLTFU_df["Event Group Label"] = status_DSSVLTFU_df["Event Label"].apply(map_event)

        # Combine DSSVLTFU with SV dataframe vertically
        status_SV_df = pd.concat([status_SV_df, status_DSSVLTFU_df])
        # Sort the dataframe by Subject and Event Date
        status_SV_df = status_SV_df.sort_values(by=["Subject", "Event Date"])

        # For each unique subject, get the last row of the dataframe
        status_SV_df = status_SV_df.groupby("Subject").tail(1)

        # Merge left with the current response dataframe
        status_df = pd.merge(
            status_df,
            status_SV_df[["Subject", "Event Label"]],
            on="Subject",
            how="left",
        )

        # Rename the column Event Label to Event Label (Study Status)
        status_df["Event Label"] = status_df["Event Label"].map(event_1_dict)

        status_df["Event Label3"] = status_df["Subject"].apply(
            lambda x: (
                "Pre-Treatment"
                if (
                    enrollment_df[enrollment_df["Subject"] == x]["Treated"]
                    .fillna("")
                    .str.strip()
                    .values[0]
                    == "Pending"
                )
                else ""
            )
        )

        status_df["Event Label4"] = status_df["Subject"].apply(
            lambda x: (
                "Withdrawn Prior to Study Treatment"
                if (
                    enrollment_df[enrollment_df["Subject"] == x]["Treated"]
                    .fillna("")
                    .str.strip()
                    .values[0]
                    == "No"
                )
                & (
                    enrollment_df[enrollment_df["Subject"] == x][
                        "Subject meets all study eligibility?"
                    ]
                    .fillna("")
                    .str.strip()
                    .values[0]
                    == "Yes"
                )
                else ""
            )
        )
        # Merge all event group label into study status
        status_df["Event Label"] = (
            status_df["Event Label"].fillna("")
            + status_df["Event Label3"].fillna("")
            + status_df["Event Label4"].fillna("")
        )
        status_df["Event Label"] = status_df["Event Label"].fillna(
            status_df["Event Label"]
        )
        status_df = status_df.drop(
            columns=[
                "Event Label3",
                "Event Label4",
            ]
        )

        # filter the data frame to only include subjects whose end of study date is later than or equal to main consent date
        filteredemrollment_df = enrollment_df[
            enrollment_df["End of Study Date"] >= enrollment_df["Main Consent Date"]
        ]

        filteredDSEOS_df = DSEOS_df[
            (DSEOS_df["Last Study Phase Completed"] != "Pre-Study Treatment")
            & (DSEOS_df["Subject"].isin(filteredemrollment_df["Subject"].values))
        ].copy()
        filteredDSEOS_df = DSEOS_df[
            (DSEOS_df["Subject"].isin(filteredemrollment_df["Subject"].values))
        ].copy()

        status_df["Event Label"] = status_df.apply(
            lambda row: (
                "Off Study"
                if (row["Subject"] in filteredDSEOS_df["Subject"].values)
                & (row["Event Label"] != "Withdrawn Prior to Study Treatment")
                else "On Study/" + row["Event Label"]
            ),
            axis=1,
        )
        status_df = status_df.replace(
            "On Study/Withdrawn Prior to Study Treatment",
            "Withdrawn Prior to Study Treatment",
        )
        status_df = pd.merge(
            status_df,
            filteredDSEOS_df[
                ["Subject", "Off-Study Reason", "Last Study Phase Completed"]
            ],
            on="Subject",
            how="left",
        )
        status_df = status_df.replace(
            "On Study/Pre-TreatmentPre-Treatment", "On Study/Pre-Treatment"
        )

        # replaces all occurrences of NaN, positive infinity, and negative infinity in the infusion_df dataframe with empty strings.
        status_df = status_df.replace([np.nan, np.inf, -np.inf], "N/A")

        # Gather all stats of each cohort (currently only has cohort 1)
        total_status_df = status_df.copy()

        totalCH1_status_df = total_status_df[
            total_status_df["Study Assignment"].isin(["Cohort 1"])
        ].copy()

        # Total number of subjects for Cohort 1
        AECH1_total_count = get_stats_percentage("AE", totalCH1_status_df).T
        SAECH1_total_count = get_stats_percentage("SAE", totalCH1_status_df).T
        # merge AE and SAE dataframes
        safetyCH1_total_df = pd.concat([AECH1_total_count, SAECH1_total_count], axis=1)

        totalCH2_status_df = total_status_df[
            total_status_df["Study Assignment"].isin(["Cohort 2"])
        ].copy()
        # Total number of subjects for Cohort 2
        AECH2_total_count = get_stats_percentage("AE", totalCH2_status_df).T
        SAECH2_total_count = get_stats_percentage("SAE", totalCH2_status_df).T
        # merge AE and SAE dataframes
        safetyCH2_total_df = pd.concat([AECH2_total_count, SAECH2_total_count], axis=1)

        totalARMA_status_df = total_status_df[
            total_status_df["Study Assignment"].isin(["Treatment Arm A"])
        ].copy()
        # Total number of subjects for Treatment Arm A
        AEARMA_total_count = get_stats_percentage("AE", totalARMA_status_df).T
        SAEARMA_total_count = get_stats_percentage("SAE", totalARMA_status_df).T
        # merge AE and SAE dataframes
        safetyARMA_total_df = pd.concat(
            [AEARMA_total_count, SAEARMA_total_count], axis=1
        )

        totalARMB_status_df = total_status_df[
            total_status_df["Study Assignment"].isin(["Treatment Arm B"])
        ].copy()
        # Total number of subjects for Treatment Arm A
        AEARMB_total_count = get_stats_percentage("AE", totalARMB_status_df).T
        SAEARMB_total_count = get_stats_percentage("SAE", totalARMB_status_df).T
        # merge AE and SAE dataframes
        safetyARMB_total_df = pd.concat(
            [AEARMB_total_count, SAEARMB_total_count], axis=1
        )

        enrollment_df = enrollment_df.drop(
            columns=[
                "End of Study Date",
                "Main Consent Date",
            ]
        )

    if export:
        with pd.ExcelWriter(
            output_dir + "/" + output_file_name + ".xlsx", engine="xlsxwriter"
        ) as writer:
            # TODO: - Add formatting and coloring
            # TODO: - for each tab: write data, format data, write header, format header

            ## * FORMATING AND COLORING
            bold_11_format = writer.book.add_format(
                {
                    "bg_color": "#FFFFFF",
                    "text_wrap": True,
                    "valign": "vcenter",
                    "align": "center",
                    "bold": True,
                    "font_name": "Calibri",
                    "font_size": 11,
                    "border": 1,
                }
            )
            bold_12_format = writer.book.add_format(
                {
                    "bg_color": "#FFFFFF",
                    "text_wrap": False,
                    "valign": "vcenter",
                    "align": "center",
                    "bold": True,
                    "font_name": "Calibri",
                    "font_size": 12,
                    "border": 1,
                }
            )
            bold_12_wrap_format = writer.book.add_format(
                {
                    "bg_color": "#FFFFFF",
                    "text_wrap": True,
                    "valign": "vcenter",
                    "align": "center",
                    "bold": True,
                    "font_name": "Calibri",
                    "font_size": 12,
                    "border": 1,
                }
            )
            bold_11_wrap_format = writer.book.add_format(
                {
                    "bg_color": "#FFFFFF",
                    "text_wrap": True,
                    "valign": "vcenter",
                    "align": "center",
                    "bold": True,
                    "font_name": "Calibri",
                    "font_size": 11,
                    "border": 1,
                }
            )
            normal_data_format = writer.book.add_format(
                {
                    "bg_color": "#FFFFFF",
                    "text_wrap": False,
                    "valign": "vcenter",
                    "align": "center",
                    "bold": False,
                    "font_name": "Calibri",
                    "font_size": 11,
                    "border": 1,
                }
            )
            # Create a format for a black cell
            if data["DM"]["Subject"].count() > 0:
                ## TODO: DSMB-Demo Stats Table
                if enrollment_df["Subject"].count() > 0:
                    # * WRITING DATA: LegalSex_list, Age_at_Consent_list, Race_list, Ethnicity_list
                    worksheet1 = writer.book.add_worksheet("DSMB-Demo Stats Table")

                    # * FORMAT DATA
                    for i in range(0, len(status_list)):
                        for j in range(0, len(LegalSex_list[i])):
                            for k in range(0, len(LegalSex_list[i].columns)):
                                worksheet1.write(
                                    j + 4,
                                    k + 1 + i * 4,
                                    LegalSex_list[i].iloc[j, k],
                                    normal_data_format,
                                )
                        for j in range(0, len(Age_at_Consent_list[i])):
                            for k in range(0, len(Age_at_Consent_list[i].columns)):
                                worksheet1.write(
                                    j + 9,
                                    k + 1 + i * 4,
                                    Age_at_Consent_list[i].iloc[j, k],
                                    normal_data_format,
                                )
                        for j in range(0, len(Race_list[i])):
                            for k in range(0, len(Race_list[i].columns)):
                                worksheet1.write(
                                    j + 13,
                                    k + 1 + i * 4,
                                    Race_list[i].iloc[j, k],
                                    normal_data_format,
                                )
                        for j in range(0, len(Ethnicity_list[i])):
                            for k in range(0, len(Ethnicity_list[i].columns)):
                                worksheet1.write(
                                    j + 23,
                                    k + 1 + i * 4,
                                    Ethnicity_list[i].iloc[j, k],
                                    normal_data_format,
                                )

                    # * WRITING HEADER AND FORMATTING
                    Sex_order = ["Male", "Female", "X (Nonbinary)", "Not Reported"]
                    Age_order = ["Mean SD", "Median", "Range"]
                    Race_order = [
                        "African American",
                        "Alaska Native",
                        "American Indian",
                        "Asian",
                        "Caucasian",
                        "Multiple Races",
                        "Pacific Islander",
                        "Other",
                        "Unknown",
                    ]
                    Ethnicity_order = ["Hispanic", "Non-Hispanic", "Unknown"]

                    for i in range(0, len(Sex_order)):
                        worksheet1.write(i + 4, 0, Sex_order[i], bold_11_format)
                    for i in range(0, len(Age_order)):
                        worksheet1.write(i + 9, 0, Age_order[i], bold_11_format)
                    for i in range(0, len(Race_order)):
                        worksheet1.write(i + 13, 0, Race_order[i], bold_11_format)
                    for i in range(0, len(Ethnicity_order)):
                        worksheet1.write(i + 23, 0, Ethnicity_order[i], bold_11_format)

                    worksheet1.merge_range(
                        "F1:M1", "Dose Finding Phase", bold_12_format
                    )
                    worksheet1.merge_range("N1:U1", "Expansion Phase", bold_12_format)
                    worksheet1.merge_range(
                        "B2:E2", "Overall Study Enrollment", bold_12_format
                    )
                    worksheet1.merge_range(
                        "F2:I2", "Cohort 1 Enrollment", bold_12_format
                    )
                    worksheet1.merge_range(
                        "J2:M2", "Cohort 2 Enrollment", bold_12_format
                    )
                    worksheet1.merge_range(
                        "N2:Q2", "Treatment Arm A Enrollment", bold_12_format
                    )
                    worksheet1.merge_range(
                        "R2:U2", "Treatment Arm B Enrollment", bold_12_format
                    )
                    worksheet1.write(2, 0, "Status", bold_11_format)
                    for i in range(len(status_list)):
                        worksheet1.write(
                            2,
                            1 + i * 4,
                            "Total Consented\nN="
                            + str(status_list[i]["Total Consented"]),
                            bold_11_wrap_format,
                        )
                        worksheet1.write(
                            2,
                            2 + i * 4,
                            "Screen Failed\nN=" + str(status_list[i]["Screen Failed"]),
                            bold_11_wrap_format,
                        )
                        worksheet1.write(
                            2,
                            3 + i * 4,
                            "Eligible\nN=" + str(status_list[i]["Eligible"]),
                            bold_11_wrap_format,
                        )
                        worksheet1.write(
                            2,
                            4 + i * 4,
                            "Treated\nN=" + str(status_list[i]["Treated"]),
                            bold_11_wrap_format,
                        )

                    worksheet1.merge_range("A4:U4", "Legal Sex", bold_11_format)
                    worksheet1.merge_range("A9:U9", "Age at Consent", bold_11_format)
                    worksheet1.merge_range("A13:U13", "Race", bold_11_format)
                    worksheet1.merge_range("A23:U23", "Ethnicity", bold_11_format)
                    worksheet1.autofit()

                    ## TODO: Enrollment Listing
                    # * WRITING DATA: enrollment_df
                    worksheet2 = writer.book.add_worksheet("DSMB-Enrollment Listing")
                    enrollment_df = enrollment_df.drop(columns=["Treated"])
                    # * WRITING HEADER AND FORMATTING
                    # Assuming 'enrollment_df' is your DataFrame
                    enrollment_df.replace(
                        [np.inf, -np.inf], np.nan, inplace=True
                    )  # Replace INF with NaN
                    enrollment_df = enrollment_df.fillna(
                        "N/A"
                    )  # Replace NaN with a placeholder
                    for i in range(0, len(enrollment_df.columns)):
                        worksheet2.write(0, i, enrollment_df.columns[i], bold_11_format)
                    # * FORMAT DATA
                    for i in range(0, len(enrollment_df)):
                        for j in range(0, len(enrollment_df.columns)):
                            worksheet2.write(
                                i + 1, j, enrollment_df.iloc[i, j], normal_data_format
                            )
                    # Autofit
                    worksheet2.autofit()

                    ## TODO: DSMB-Infusion Listing
                    worksheet3 = writer.book.add_worksheet("DSMB-Infusion Listing")
                    # * WRITING AND FORMATING DATA
                    infusion_df = infusion_df.drop(columns=["Event Group Label"])
                    infusionR_df = infusionR_df.drop(columns=["Event Group Label"])
                    # # replace "N/A" for blank coulumns
                    # infusion_df = infusion_df.fillna("N/A")
                    for i in range(0, len(infusion_df)):
                        for j in range(0, len(infusion_df.columns)):
                            worksheet3.write(
                                i + 1, j, infusion_df.iloc[i, j], normal_data_format
                            )
                    for i in range(0, len(infusionR_df)):
                        for j in range(0, len(infusionR_df.columns)):
                            worksheet3.write(
                                i + 1,
                                j + 13,
                                infusionR_df.iloc[i, j],
                                normal_data_format,
                            )
                    # * WRITING HEADER AND FORMATTING
                    worksheet3.write("A1", "Subject ID", bold_12_wrap_format)
                    # worksheet3.merge_range(
                    #     "B1:B2", "Study Day (Primary)", bold_12_wrap_format
                    # )
                    worksheet3.write("B1", "Study Phase", bold_12_wrap_format)
                    worksheet3.write("C1", "Study Assignment", bold_12_wrap_format)
                    worksheet3.write(
                        "D1", "VCN-01 Infusion Complete (Y/N)", bold_12_wrap_format
                    )
                    worksheet3.write(
                        "E1",
                        "Date of VCN-01 Infusion",
                        bold_12_wrap_format,
                    )
                    worksheet3.write("F1", "VCN-01 Dose Received", bold_12_wrap_format)
                    worksheet3.write(
                        "G1", "HuCART-meso Infusion Complete (Y/N)", bold_12_wrap_format
                    )
                    worksheet3.write(
                        "H1", "Date of HuCART-meso Infusion", bold_12_wrap_format
                    )
                    worksheet3.write(
                        "I1",
                        "Total huCART-meso Cell Dose Administered",
                        bold_12_wrap_format,
                    )
                    worksheet3.write(
                        "J1", "Total Cell Dose Administered", bold_12_wrap_format
                    )

                    worksheet3.write("N1", "Subject ID", bold_12_wrap_format)
                    worksheet3.write("O1", "Study Phase", bold_12_wrap_format)
                    worksheet3.write("P1", "Study Assignment", bold_12_wrap_format)
                    worksheet3.write(
                        "Q1",
                        "Lymphodepleting Chemotherapy Regimen",
                        bold_12_wrap_format,
                    )
                    worksheet3.write(
                        "R1",
                        "Date of HuCART-meso Retreatment Infusion",
                        bold_12_wrap_format,
                    )
                    worksheet3.write(
                        "S1",
                        "Total huCART-meso Cell Dose Administered",
                        bold_12_wrap_format,
                    )
                    worksheet3.write(
                        "T1", "Total Cell Dose Administered", bold_12_wrap_format
                    )

                    # Autofit
                    worksheet3.autofit()

                    ## TODO: Response Listing for Cohorts 1&2
                    worksheet4 = writer.book.add_worksheet(
                        "Cohorts 1 & 2 Response Listing"
                    )
                    # Primary follow-up
                    worksheet4.merge_range(
                        "A1:I1",
                        "Dose Finding Phase (Primary Follow-up) \nN="
                        + str(subject_ACH12_prim_count),
                        bold_12_format,
                    )
                    worksheet4.merge_range("A2:A3", "Subject ID", bold_11_format)
                    worksheet4.merge_range("B2:B3", "Study Assignment", bold_11_format)
                    worksheet4.merge_range(
                        "C2:I2", "Overall Tumor Response", bold_11_format
                    )
                    worksheet4.write(
                        "C3",
                        "Pre-Infusion Safety (Baseline Disease Status)",
                        bold_11_format,
                    )
                    worksheet4.write("D3", "Day +10 Post Infusion #2", bold_11_format)
                    worksheet4.write("E3", "Month 3", bold_11_format)
                    worksheet4.write("F3", "Month 6", bold_11_format)
                    worksheet4.write("G3", "Month 9", bold_11_format)
                    worksheet4.write("H3", "Month 12", bold_11_format)
                    worksheet4.write("I3", "Unscheduled", bold_11_format)

                    for i in range(0, len(response_df)):
                        for j in range(0, len(response_df.columns)):
                            worksheet4.write(
                                i + 3,
                                j,
                                response_df.iloc[i, j],
                                normal_data_format,
                            )

                    # Retreatment follow-up
                    worksheet4.merge_range(
                        "L1:T1",
                        "Dose Finding Phase (Retreatment Follow-up) \nN="
                        + str(subject_ACH12_primR_count),
                        bold_12_format,
                    )
                    worksheet4.merge_range("L2:L3", "Subject ID", bold_11_format)
                    worksheet4.merge_range("M2:M3", "Study Assignment", bold_11_format)
                    worksheet4.merge_range(
                        "N2:T2", "Overall Tumor Response", bold_11_format
                    )
                    worksheet4.write(
                        "N3",
                        "Pre-Retreatment Safety (Baseline Retreatment Disease Status)",
                        bold_11_format,
                    )
                    worksheet4.write("O3", "Day 28-R", bold_11_format)
                    worksheet4.write("P3", "Month 3-R", bold_11_format)
                    worksheet4.write("Q3", "Month 6-R", bold_11_format)
                    worksheet4.write("R3", "Month 9-R", bold_11_format)
                    worksheet4.write("S3", "Month 12-R", bold_11_format)
                    worksheet4.write("T3", "Unscheduled", bold_11_format)

                    for i in range(0, len(responseR_df)):
                        for j in range(0, len(responseR_df.columns)):
                            worksheet4.write(
                                i + 3,
                                j + 11,
                                responseR_df.iloc[i, j],
                                normal_data_format,
                            )
                    worksheet4.autofit()

                    ## TODO: Response Listing for Arms A & B
                    worksheet5 = writer.book.add_worksheet(
                        "Arms A & B Response Listing"
                    )
                    # Primary follow-up
                    worksheet5.merge_range(
                        "A1:I1",
                        "Expansion Phase (Primary Follow-up) \nN="
                        + str(subject_ARMAB_prim_count),
                        bold_12_format,
                    )
                    worksheet5.merge_range("A2:A3", "Subject ID", bold_11_format)
                    worksheet5.merge_range("B2:B3", "Study Assignment", bold_11_format)
                    worksheet5.merge_range(
                        "C2:I2", "Overall Tumor Response", bold_11_format
                    )
                    worksheet5.write(
                        "C3",
                        "Pre-Infusion Safety (Baseline Disease Status)",
                        bold_11_format,
                    )
                    worksheet5.write("D3", "Day 28", bold_11_format)
                    worksheet5.write("E3", "Month 3", bold_11_format)
                    worksheet5.write("F3", "Month 6", bold_11_format)
                    worksheet5.write("G3", "Month 9", bold_11_format)
                    worksheet5.write("H3", "Month 12", bold_11_format)
                    worksheet5.write("I3", "Unscheduled", bold_11_format)

                    for i in range(0, len(responseAB_df)):
                        for j in range(0, len(responseAB_df.columns)):
                            worksheet5.write(
                                i + 3,
                                j,
                                responseAB_df.iloc[i, j],
                                normal_data_format,
                            )

                    # Retreatment follow-up
                    worksheet5.merge_range(
                        "L1:T1",
                        "Expansion Phase (Retreatment Follow-up) \nN="
                        + str(subject_ARMAB_primR_count),
                        bold_12_format,
                    )
                    worksheet5.merge_range("L2:L3", "Subject ID", bold_11_format)
                    worksheet5.merge_range("M2:M3", "Study Assignment", bold_11_format)
                    worksheet5.merge_range(
                        "N2:T2", "Overall Tumor Response", bold_11_format
                    )
                    worksheet5.write(
                        "N3",
                        "Pre-Retreatment Safety (Baseline Retreatment Disease Status)",
                        bold_11_format,
                    )
                    worksheet5.write("O3", "Day 28-R", bold_11_format)
                    worksheet5.write("P3", "Month 3-R", bold_11_format)
                    worksheet5.write("Q3", "Month 6-R", bold_11_format)
                    worksheet5.write("R3", "Month 9-R", bold_11_format)
                    worksheet5.write("S3", "Month 12-R", bold_11_format)
                    worksheet5.write("T3", "Unscheduled", bold_11_format)

                    for i in range(0, len(responseRAB_df)):
                        for j in range(0, len(responseRAB_df.columns)):
                            worksheet5.write(
                                i + 3,
                                j + 11,
                                responseRAB_df.iloc[i, j],
                                normal_data_format,
                            )
                    worksheet5.autofit()

                    ## TODO: Summary of Protocol Status
                    worksheet6 = writer.book.add_worksheet(
                        "Status for Eligible Subjects"
                    )
                    # * WRITING AND FORMATING DATA
                    for i in range(0, len(status_df)):
                        for j in range(0, len(status_df.columns)):
                            worksheet6.write(
                                i + 2, j, status_df.iloc[i, j], normal_data_format
                            )

                    # * WRITING HEADER AND FORMATTING
                    worksheet6.merge_range("A1:A2", "Subject ID", bold_12_wrap_format)
                    worksheet6.merge_range(
                        "B1:B2", "Study Assignment", bold_12_wrap_format
                    )
                    worksheet6.merge_range(
                        "C1:C2", "Adverse Events (Y/N)", bold_12_wrap_format
                    )
                    worksheet6.merge_range(
                        "D1:D2", "Serious Adverse Events (Y/N)", bold_12_wrap_format
                    )
                    worksheet6.merge_range("E1:E2", "Study Status", bold_12_wrap_format)
                    worksheet6.merge_range(
                        "F1:F2", "Off-Study Reason", bold_12_wrap_format
                    )
                    worksheet6.merge_range(
                        "G1:G2",
                        "Last Study Visit Performed for Off-Study Subject",
                        bold_12_wrap_format,
                    )

                    # Safety Headers
                    # number of subject of safety_total_df
                    safety_total_df_subject_count = len(status_df["Subject"].unique())
                    worksheet6.merge_range(
                        "K1:N1",
                        "Safety Statistics (N="
                        + str(safety_total_df_subject_count)
                        + ")",
                        bold_12_wrap_format,
                    )
                    worksheet6.merge_range("K2:L2", "Adverse Events", bold_11_format)
                    worksheet6.merge_range(
                        "M2:N2", "Serious Adverse Events ", bold_11_format
                    )
                    worksheet6.write("K3", "Yes", bold_11_format)
                    worksheet6.write("L3", "No", bold_11_format)
                    worksheet6.write("M3", "Yes", bold_11_format)
                    worksheet6.write("N3", "No", bold_11_format)
                    worksheet6.write("J4", "Cohort 1", bold_11_format)
                    worksheet6.write("J5", "Cohort 2", bold_11_format)
                    worksheet6.write("J6", "Treatment Arm A", bold_11_format)
                    worksheet6.write("J7", "Treatment Arm B", bold_11_format)
                    # Safety Data
                    # Cohort 1
                    for i in range(0, len(safetyCH1_total_df)):
                        for j in range(0, len(safetyCH1_total_df.columns)):
                            worksheet6.write(
                                i + 3,
                                j + 10,
                                safetyCH1_total_df.iloc[i, j],
                                normal_data_format,
                            )
                    # Cohort 2
                    for i in range(0, len(safetyCH2_total_df)):
                        for j in range(0, len(safetyCH2_total_df.columns)):
                            worksheet6.write(
                                i + 4,
                                j + 10,
                                safetyCH2_total_df.iloc[i, j],
                                normal_data_format,
                            )
                    # ARM A
                    for i in range(0, len(safetyARMA_total_df)):
                        for j in range(0, len(safetyARMA_total_df.columns)):
                            worksheet6.write(
                                i + 5,
                                j + 10,
                                safetyARMA_total_df.iloc[i, j],
                                normal_data_format,
                            )
                    # ARM B
                    for i in range(0, len(safetyARMB_total_df)):
                        for j in range(0, len(safetyARMB_total_df.columns)):
                            worksheet6.write(
                                i + 6,
                                j + 10,
                                safetyARMB_total_df.iloc[i, j],
                                normal_data_format,
                            )
                    worksheet6.autofit()
