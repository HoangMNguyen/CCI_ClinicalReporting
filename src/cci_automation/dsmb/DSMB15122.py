import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

from cci_automation.dsmb.DSMB_util import (
    add_rename_column_corelisting,
    convert_float_2_sci_notation,
    get_stats_df,
    get_stats_perc_df,
    get_stats_percentage,
)
from cci_automation.util import remove_leading_zeros_from_dates


def DSMB15122(
    data,
    export,
    output_dir,
    output_file_name,
):
    # DEMO ENROLLMENT LISTING
    if not data["DM"].empty:
        # DM data
        DM_df = data["DM"][
            [
                "Subject",
                "Legal Sex (IG_NS_NA_DM1.CL_NS_YH_SEX_cl_NS_DMSEX1)",
                "Sex Assigned at Birth (IG_NS_NA_DM1.CL_NS_NH_BRTHSEX_cl_NS_DMSEX3)",
                "Gender Identity (IG_NS_NA_DM1.CL_NS_NH_GENDERID_cl_NS_DMSEX2)",
                "Specify Other Gender Identity (IG_NS_NA_DM1.TX_NS_NH_GENDERIDOTH)",
                "Race (IG_NS_NA_DM1.CL_NS_YH_RACE_cl_NS_DMRACE1)",
                "Specify Other or Multiple Races (IG_NS_NA_DM1.TX_NS_NH_RACEOTH)",
                "Ethnicity (IG_NS_NA_DM1.CL_NS_NH_ETHNIC_cl_NS_DMETHNIC1)",
                "Date of Birth (IG_NS_NA_DM1.DT_NS_NH_BRTHDAT)",
                "Pre-Screening Consent Date (IG_NS_NA_DM1.DT_NS_YH_RFICDAT)",
                "Event Date",
            ]
        ].copy()
        DM_new_col_name = {
            "Race (IG_NS_NA_DM1.CL_NS_YH_RACE_cl_NS_DMRACE1)": "Race",
            "Specify Other or Multiple Races (IG_NS_NA_DM1.TX_NS_NH_RACEOTH)": "Race other",
            "Ethnicity (IG_NS_NA_DM1.CL_NS_NH_ETHNIC_cl_NS_DMETHNIC1)": "Ethnicity",
            "Sex Assigned at Birth (IG_NS_NA_DM1.CL_NS_NH_BRTHSEX_cl_NS_DMSEX3)": "Sex Assigned at Birth",
            "Legal Sex (IG_NS_NA_DM1.CL_NS_YH_SEX_cl_NS_DMSEX1)": "Legal Sex",
            "Gender Identity (IG_NS_NA_DM1.CL_NS_NH_GENDERID_cl_NS_DMSEX2)": "Gender Identity",
            "Specify Other Gender Identity (IG_NS_NA_DM1.TX_NS_NH_GENDERIDOTH)": "Gender Identity SP",
            "Date of Birth (IG_NS_NA_DM1.DT_NS_NH_BRTHDAT)": "Date of Birth",
            "Pre-Screening Consent Date (IG_NS_NA_DM1.DT_NS_YH_RFICDAT)": "Consent Date",
            "Event Date": "Event Date DM",
        }
        DM_df = DM_df.rename(columns=DM_new_col_name)
        # replace race with "Specify Other or Multiple Races" field when race selected "Other" or "Multiple Races" option
        DM_df["Race1"] = DM_df["Race"]
        DM_df.loc[
            (DM_df["Race"] == "Other") | (DM_df["Race"] == "Multiple Races"),
            "Race1",
        ] = ""

        DM_df["Race"] = DM_df[DM_df["Race"].notna()]["Race"].astype(str)
        DM_df["Race1"] = DM_df[DM_df["Race1"].notna()]["Race1"].astype(str)
        DM_df["Race other"] = DM_df[DM_df["Race other"].notna()]["Race other"].astype(
            str
        )

        DM_df["Race1"] = DM_df["Race1"].fillna("") + DM_df["Race other"].fillna("")
        DM_df["Race1"] = DM_df["Race1"].fillna(DM_df["Race1"])
        DM_df = DM_df.drop(
            columns=[
                "Race other",
            ]
        )
        # Replace "Gender Identity" with "Specify Other Gender Identity" when "Other" is selected
        DM_df.loc[
            DM_df["Gender Identity"] == "Other",
            "Gender Identity",
        ] = ""
        DM_df["Gender Identity SP"] = DM_df[DM_df["Gender Identity SP"].notna()][
            "Gender Identity SP"
        ].astype(str)
        DM_df["Gender Identity"] = DM_df["Gender Identity"].fillna("") + DM_df[
            "Gender Identity SP"
        ].fillna("")

        DM_df["Gender Identity"] = DM_df["Gender Identity"].fillna(
            DM_df["Gender Identity"]
        )
        DM_df = DM_df.drop(columns=["Gender Identity SP"])

        # # when there are two DM entered, use the latest DM
        DM_df["Event Date DM"] = pd.to_datetime(DM_df["Event Date DM"])
        DM_df = DM_df.sort_values(["Event Date DM"])
        DM_df = DM_df.drop_duplicates(subset=["Subject"], keep="last")
        DM_df = DM_df.drop(columns=["Event Date DM"])
        DM_df = DM_df.drop_duplicates()
        DM_df["Consent Date"] = pd.to_datetime(DM_df["Consent Date"])
        DM_df["Date of Birth"] = pd.to_datetime(DM_df["Date of Birth"])
        mask = ~DM_df[["Consent Date", "Date of Birth"]].isnull().any(axis=1)
        DM_df.loc[mask, "Age at Consent"] = DM_df[mask].apply(
            lambda x: relativedelta(x["Consent Date"], x["Date of Birth"]).years, axis=1
        )
        sorted_DM_df = DM_df.sort_values(["Subject"])
    # DSCA, assuming only one cohort assignment form will be entered.
    if not data["DSCA"].empty:
        DSCA_df = data["DSCA"][
            [
                "Subject",
                "Cohort Assignment (IG_NS_NA_DSCA1.CL_NS_YH_CACHASCOD_cl_NS_COHORT1)",
            ]
        ].copy()
        DSCA_new_col_name = {
            "Cohort Assignment (IG_NS_NA_DSCA1.CL_NS_YH_CACHASCOD_cl_NS_COHORT1)": "Cohort Assignment"
        }
        DSCA_df = DSCA_df.rename(columns=DSCA_new_col_name)
        enrollment_df = pd.merge(sorted_DM_df, DSCA_df, on="Subject", how="left")
        index_reference = enrollment_df.columns.get_loc("Legal Sex")
        enrollment_df.insert(
            index_reference, "Cohort Assignment", enrollment_df.pop("Cohort Assignment")
        )

    # when 2 dose level assignment forms are entered, use the latest data
    if not data["DSDLA"].empty:
        DSDLA_df = data["DSDLA"][
            [
                "Subject",
                "Dose Level Assignment (IG_NS_NA_DSDLA1.CL_NS_YH_DLADOSELV_cl_NS_DOSELV1)",
                "Form Sequence Number",
            ]
        ].copy()
        DSDLA_new_col_name = {
            "Dose Level Assignment (IG_NS_NA_DSDLA1.CL_NS_YH_DLADOSELV_cl_NS_DOSELV1)": "Dose Level Assignment"
        }
        DSDLA_df = DSDLA_df.rename(columns=DSDLA_new_col_name)
        DSDLA_df = DSDLA_df.sort_values(["Form Sequence Number"])
        DSDLA_df = DSDLA_df.drop_duplicates(subset=["Subject"], keep="last")
        enrollment_df = pd.merge(enrollment_df, DSDLA_df, on="Subject", how="left")
        index_reference = enrollment_df.columns.get_loc("Legal Sex")
        enrollment_df.insert(
            index_reference,
            "Dose Level Assignment",
            enrollment_df.pop("Dose Level Assignment"),
        )

    if not data["MHDIAG"].empty:
        MHDIAG_df = data["MHDIAG"][
            [
                "Subject",
                "Primary Diagnosis (IG_NS_NA_MHDIAG1.CL_NS_YH_PRMDIAG_cl_NS_PRMDIAG)",
                "Specify Other Diagnosis (IG_NS_NA_MHDIAG1.TX_NS_NH_PRMDIAGOTH)",
                "Event Date",
            ]
        ].copy()
        MHDIAG_new_col_name = {
            "Primary Diagnosis (IG_NS_NA_MHDIAG1.CL_NS_YH_PRMDIAG_cl_NS_PRMDIAG)": "Disease",
            "Specify Other Diagnosis (IG_NS_NA_MHDIAG1.TX_NS_NH_PRMDIAGOTH)": "Disease other",
            "Event Date": "Event Date DIAG",
        }
        MHDIAG_df = MHDIAG_df.rename(columns=MHDIAG_new_col_name)
        # when there are two diagnosis entered, use the latest
        MHDIAG_df["Event Date DIAG"] = pd.to_datetime(MHDIAG_df["Event Date DIAG"])
        MHDIAG_df = MHDIAG_df.sort_values(["Event Date DIAG"])
        MHDIAG_df = MHDIAG_df.drop_duplicates(subset=["Subject"], keep="last")
        MHDIAG_df = MHDIAG_df.drop(columns=["Event Date DIAG"])
        MHDIAG_df = MHDIAG_df.drop_duplicates()
        MHDIAG_df["Disease Type"] = None
        # Replace ""Primary Diagnosis" with "Specify Other Diagnosis" when "Other" is selected
        MHDIAG_df.loc[
            MHDIAG_df["Disease"] == "Other",
            "Disease",
        ] = ""

        MHDIAG_df["Disease"] = MHDIAG_df[MHDIAG_df["Disease"].notna()][
            "Disease"
        ].astype(str)
        MHDIAG_df["Disease other"] = MHDIAG_df[MHDIAG_df["Disease other"].notna()][
            "Disease other"
        ].astype(str)

        enrollment_df = pd.merge(enrollment_df, MHDIAG_df, on="Subject", how="left")
        index_reference = enrollment_df.columns.get_loc("Legal Sex")
        enrollment_df.insert(
            index_reference,
            "Disease Type",
            enrollment_df.pop("Disease Type"),
        )

        # combine disease and disease other into disease type
        enrollment_df["Disease Type"] = enrollment_df["Disease"].fillna(
            ""
        ) + enrollment_df["Disease other"].fillna("")
        enrollment_df["Disease Type"] = enrollment_df["Disease Type"].fillna(
            enrollment_df["Disease Type"]
        )
        enrollment_df = enrollment_df.drop(
            columns=[
                "Disease",
                "Disease other",
            ]
        )

    # Subject meets all study eligibility? Only get data eligibility data from IE when IE is entered, otherwise check DSEOS
    if not data["IE"].empty:
        IE_df = data["IE"][
            [
                "Subject",
                "Subject Meets All Study Eligibility (IG_NS_NA_IE3.CL_NS_YH_ELIGYN_cl_YS_YN1)",
                "Other Screen Fail Reason (IG_NS_NA_IE4.TX_NS_YH_OTHRSFREAS)",
                "Screen Failure Reason (IG_NS_NA_IE4.CL_NS_YH_IECAT_cl_NS_IEREASSF1)",
                "Select the Primary Inclusion Criterion Excluding this Subject (IG_NS_NA_IE4.CL_NS_NH_ITESTCD_cl_NS_IEINCL1)",
                "Select the Primary Exclusion Criterion Excluding this Subject (IG_NS_NA_IE4.CL_NS_NH_ETESTCD_cl_NS_IEEXCL1)",
                "Main Consent Date (IG_NS_NA_IE1.DT_NS_NH_MAINCDAT)",
            ]
        ].copy()
        IE_new_col_name = {
            "Subject Meets All Study Eligibility (IG_NS_NA_IE3.CL_NS_YH_ELIGYN_cl_YS_YN1)": "Subject meets all study eligibility?IE",
            "Other Screen Fail Reason (IG_NS_NA_IE4.TX_NS_YH_OTHRSFREAS)": "SF4",
            "Screen Failure Reason (IG_NS_NA_IE4.CL_NS_YH_IECAT_cl_NS_IEREASSF1)": "SF1",
            "Select the Primary Inclusion Criterion Excluding this Subject (IG_NS_NA_IE4.CL_NS_NH_ITESTCD_cl_NS_IEINCL1)": "SF2",
            "Select the Primary Exclusion Criterion Excluding this Subject (IG_NS_NA_IE4.CL_NS_NH_ETESTCD_cl_NS_IEEXCL1)": "SF3",
            "Main Consent Date (IG_NS_NA_IE1.DT_NS_NH_MAINCDAT)": "Main Consent Date",
        }
        IE_df = IE_df.rename(columns=IE_new_col_name)
        # Combine "Reason for Screen FailureIE" from 4 different fields: screen failure reason, other screen failure reason, primary inclusion criteria excluding the subject, and primary excluding criteria excluding the subject
        IE_df["Reason for Screen FailureIE"] = None
        IE_df.loc[
            IE_df["SF1"] == "Other",
            "SF1",
        ] = ""
        IE_df["SF2"] = IE_df[IE_df["SF2"].notna()]["SF2"].astype(str)
        IE_df["SF3"] = IE_df[IE_df["SF3"].notna()]["SF3"].astype(str)
        IE_df["SF4"] = IE_df[IE_df["SF4"].notna()]["SF4"].astype(str)

        IE_df.insert(
            index_reference,
            "Reason for Screen FailureIE",
            IE_df.pop("Reason for Screen FailureIE"),
        )
        IE_df["Reason for Screen FailureIE"] = (
            IE_df["SF1"].fillna("")
            + IE_df["SF2"].fillna("")
            + IE_df["SF3"].fillna("")
            + IE_df["SF4"].fillna("")
        )

        IE_df["Reason for Screen FailureIE"] = IE_df[
            "Reason for Screen FailureIE"
        ].fillna(IE_df["Reason for Screen FailureIE"])
        IE_df = IE_df.drop(columns=["SF1", "SF2", "SF3", "SF4"])

        # for two IEs, use the latest IE
        IE_df["Main Consent Date"] = pd.to_datetime(IE_df["Main Consent Date"])
        IE_df = IE_df.sort_values(["Main Consent Date", "Subject"])
        IE_df = IE_df.drop_duplicates(subset=["Subject"], keep="last")
        IE_df = IE_df.drop_duplicates()

        enrollment_df = pd.merge(enrollment_df, IE_df, on="Subject", how="left")

        # for rows that 'Pre-Screening Consent Date' isnull but 'Main Consent Date' is not null, then use 'Main Consent Date' instead to calculate age
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

        # get study treatment administered data from EXINF for subjects did not end of study before infusion
    EXINF_df = data["EXINF"][
        [
            "Subject",
            "Was study treatment administered? (IG_NS_NA_EXINF1.CL_NS_NH_INFADMIN_cl_YS_YN1)",
        ]
    ].copy()
    EXINF_new_col_name = {
        "Was study treatment administered? (IG_NS_NA_EXINF1.CL_NS_NH_INFADMIN_cl_YS_YN1)": "Study Treatment AdministeredINF"
    }
    EXINF_df = EXINF_df.rename(columns=EXINF_new_col_name)
    enrollment_df = pd.merge(enrollment_df, EXINF_df, on="Subject", how="left")

    if not data["DSEOS"].empty:
        DSEOS_df = data["DSEOS"][
            [
                "Subject",
                "Did the Subject receive the investigational product? (IG_NS_NA_DSEOS1.CL_NS_NH_EOSRIP_cl_YS_YN1)",
                "Did the Subject sign the main consent form? (IG_NS_NA_DSEOS1.CL_NS_NH_MCNSNT_cl_YS_YN1)",
                "Provide Supportive Information (IG_NS_NA_DSEOS2.TX_NS_YH_EOSTERM)",
                "End of Study Date (IG_NS_NA_DSEOS1.DT_NS_YH_EOSDAT)",
                "Last Study Visit Completed in Primary Treatment (IG_NS_NA_DSEOS1.CL_NS_YH_EOSLSVPR_cl_NS_EOSTP1)",
                "Reason for End of Study? (IG_NS_NA_DSEOS2.CL_NS_NH_EOSCOD1_cl_NS_EOSREAS1)",
            ]
        ].copy()
        DSEOS_new_col_name = {
            "Did the Subject receive the investigational product? (IG_NS_NA_DSEOS1.CL_NS_NH_EOSRIP_cl_YS_YN1)": "Study Treatment AdministeredEOS",
            "Did the Subject sign the main consent form? (IG_NS_NA_DSEOS1.CL_NS_NH_MCNSNT_cl_YS_YN1)": "Subject meets all study eligibility?EOS",  # if subject did not sign main consent form, implies subject screen failured before IE is entered
            "Provide Supportive Information (IG_NS_NA_DSEOS2.TX_NS_YH_EOSTERM)": "Reason for Screen FailureEOS",
            "End of Study Date (IG_NS_NA_DSEOS1.DT_NS_YH_EOSDAT)": "End of Study Date",
            "Last Study Visit Completed in Primary Treatment (IG_NS_NA_DSEOS1.CL_NS_YH_EOSLSVPR_cl_NS_EOSTP1)": "Last Study Visit",
            "Reason for End of Study? (IG_NS_NA_DSEOS2.CL_NS_NH_EOSCOD1_cl_NS_EOSREAS1)": "Off-Study Reason",
        }
        DSEOS_df = DSEOS_df.rename(columns=DSEOS_new_col_name)
        DSEOS_df["Study Treatment AdministeredEOS"] = DSEOS_df[
            DSEOS_df["Study Treatment AdministeredEOS"].notna()
        ]["Study Treatment AdministeredEOS"].astype(str)
        # for two DSEOSs, use the latest DSEOS
        DSEOS_df["End of Study Date"] = pd.to_datetime(DSEOS_df["End of Study Date"])
        DSEOS_df = DSEOS_df.sort_values(["End of Study Date", "Subject"])
        DSEOS_df = DSEOS_df.drop_duplicates(subset=["Subject"], keep="last")
        DSEOS_df = DSEOS_df.drop_duplicates()

        enrollment_df = pd.merge(enrollment_df, DSEOS_df, on="Subject", how="left")

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
    # If infusion CRF is entered, set the "Study Treatment AdministeredEOS" to blank
    enrollment_df.loc[
        enrollment_df["Study Treatment AdministeredINF"] == "Yes",
        "Study Treatment AdministeredEOS",
    ] = ""

    # combine the data from IE and DSEOS
    enrollment_df["Subject meets all study eligibility?"] = enrollment_df[
        "Subject meets all study eligibility?IE"
    ].fillna("") + enrollment_df["Subject meets all study eligibility?EOS"].fillna("")
    enrollment_df["Subject meets all study eligibility?"] = enrollment_df[
        "Subject meets all study eligibility?"
    ].fillna(enrollment_df["Subject meets all study eligibility?"])
    enrollment_df = enrollment_df.drop(
        columns=[
            "Subject meets all study eligibility?IE",
            "Subject meets all study eligibility?EOS",
        ]
    )
    enrollment_df["Reason for Screen Failure"] = enrollment_df[
        "Reason for Screen FailureIE"
    ].fillna("") + enrollment_df["Reason for Screen FailureEOS"].fillna("")
    enrollment_df["Reason for Screen Failure"] = enrollment_df[
        "Reason for Screen Failure"
    ].fillna(enrollment_df["Reason for Screen Failure"])
    enrollment_df = enrollment_df.drop(
        columns=[
            "Reason for Screen FailureIE",
            "Reason for Screen FailureEOS",
        ]
    )
    # Combine the Infusion and EOS data for "Study Treatment Administered"
    enrollment_df["Study Treatment Administered"] = enrollment_df[
        "Study Treatment AdministeredINF"
    ].fillna("") + enrollment_df["Study Treatment AdministeredEOS"].fillna("")
    enrollment_df["Study Treatment Administered"] = enrollment_df[
        "Study Treatment Administered"
    ].fillna(enrollment_df["Study Treatment Administered"])
    enrollment_df = enrollment_df.drop(
        columns=[
            "Study Treatment AdministeredINF",
            "Study Treatment AdministeredEOS",
        ]
    )

    # When EOS is not entered and "Study Treatment Administered" is not Yes, set "Study Treatment Administered" to pending
    enrollment_df.loc[
        (
            enrollment_df["Study Treatment Administered"]
            .fillna("")
            .astype(str)
            .str.strip()
            != "Yes"
        )
        & (enrollment_df["End of Study Date"].isnull()),
        "Study Treatment Administered",
    ] = "Pending"
    # when subject EOS after screening visit, and study tx admin is blank, set it to No
    enrollment_df.loc[
        (enrollment_df["Study Treatment Administered"] == "")
        & (enrollment_df["Last Study Visit"] != "Pre-Screening")
        & (enrollment_df["Last Study Visit"] != "Screening/Eligibility Confirmation")
        & (~enrollment_df["End of Study Date"].isnull()),
        "Study Treatment Administered",
    ] = "No"
    enrollment_df = enrollment_df.drop(
        columns=[
            "Last Study Visit",
        ]
    )
    enrollment_df = enrollment_df.replace([np.nan, np.inf, -np.inf], "")
    enrollment_df = enrollment_df.fillna("")
    # DSMB-Demographics Statistics
    # !Update this filter options to each cohort
    filter_options = [
        enrollment_df["Consent Date"].notna()
        | enrollment_df["Main Consent Date"].notna(),
        enrollment_df["Cohort Assignment"] == "Cohort 1",
    ]
    status_list = []
    LegalSex_list = []
    Age_at_Consent_list = []
    Race_list = []
    Ethnicity_list = []

    for filter_option in filter_options:
        # Apply the filter to the dataframe
        filtered_df = enrollment_df[filter_option].copy()
        filtered_df = filtered_df[
            (filtered_df["Consent Date"].notna())
            | (filtered_df["Main Consent Date"].notna())
        ]

        # Calculate the stats
        ## Total Consented
        TT_df = filtered_df.copy()
        TT = filtered_df["Subject"].count()
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
        # Study Treatment Administered, convert to str and strip the space
        INF_df = filtered_df[
            filtered_df["Study Treatment Administered"]
            .fillna("")
            .astype(str)
            .str.strip()
            == "Yes"
        ].copy()
        INF = INF_df["Subject"].count()

        # Define a dictionary containing the status of each variable
        status_list.append(
            {
                "Total Consented": TT,
                "Screen Failed": SF,
                "Eligible": EL,
                "Study Treatment Administered": INF,
            }
        )

        # Calculate the stats for the filtered dataframe
        LegalSex_list.append(
            get_stats_percentage("Legal Sex", TT_df, SF_df, EL_df, INF_df)
        )
        Age_at_Consent_list.append(
            get_stats_df("Age at Consent", TT_df, SF_df, EL_df, INF_df)
        )
        Race_list.append(get_stats_percentage("Race", TT_df, SF_df, EL_df, INF_df))
        Ethnicity_list.append(
            get_stats_percentage("Ethnicity", TT_df, SF_df, EL_df, INF_df)
        )

    # *: remove after calculating the stats
    enrollment_df = enrollment_df.drop(
        columns=[
            "Consent Date",
            "Date of Birth",
            "Form Sequence Number",
            "Race",
        ]
    )
    update_race_column = {"Race1": "Race"}
    enrollment_df = enrollment_df.rename(columns=update_race_column)

    # DSMB-Study Tx & AE Listing
    # adding Target Cell Dose dictionary
    # !: Update this dictionary when new dose level and their dose are added
    TCD_dict = {
        "Dose Level -1 (DL-1)": 3000000,
        "Dose Level 1 (DL1)": 30000000,
        #  "Dose Level 2 (DL2)": 20000000,
        #  "Dose Level 3 (DL3)": 60000000,
        "Not Assigned": "Not Assigned",
    }

    # Study Tx & AE Listing Day 0
    # Subject: get subject from enrollment_df instead of data["DM"] because enrollment_df already removed duplicate DM if more than 1 DM is entered.
    infusion_df = enrollment_df["Subject"].copy()
    infusion_df = add_rename_column_corelisting(
        infusion_df, data, "EXINF", "Event Label", "Event Label"
    )
    infusion_df = infusion_df[infusion_df["Event Label"] == "Day 0"]
    # Cohort Assignment, use DSCA_df above
    infusion_df = pd.merge(infusion_df, DSCA_df, on="Subject", how="left")

    # Dose Level, use the DSDLA_df from above that dropped duplicate and using the latest data
    DSDLA_df = DSDLA_df.drop(
        columns=[
            "Form Sequence Number",
        ]
    )
    infusion_df = pd.merge(infusion_df, DSDLA_df, on="Subject", how="left")

    # Fill NaN with
    # Infusion Date
    infusion_df = add_rename_column_corelisting(
        infusion_df,
        data,
        "EXINF",
        "Date Study Treatment Administered (IG_NS_NA_EXINF1.DT_NS_NH_INFDAT)",
        "Date Study Treatment Administered",
        "Subject",
        "Event Label",
    )
    # convert the date to datetime object and format it to MM-DD-YYYY
    infusion_df = remove_leading_zeros_from_dates(infusion_df)

    # adding Target Cell Dose using TCD_dict
    infusion_df["Target Cell Dose"] = infusion_df["Dose Level Assignment"].map(TCD_dict)

    # Total huCart19-IL18 Cell Dose
    infusion_df = add_rename_column_corelisting(
        infusion_df,
        data,
        "EXINF",
        "CAR T Cell Dose Administered (IG_NS_NA_EXINF1.NM_NS_NH_TDOS)",
        "Total huCART-meso Administered",
        "Subject",
        "Event Label",
    )
    infusion_df = add_rename_column_corelisting(
        infusion_df,
        data,
        "EXINF",
        "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TDOSXP_cl_YS_EX10POW1)",
        "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TDOSXP_cl_YS_EX10POW1)",
        "Subject",
        "Event Label",
    )
    # combine Total huCART-meso CAR T Cell Dose Administered and x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TDOSXP_cl_YS_EX10POW1) columns, compare the new value with 'Target Cell Dose', and convert the Total huCART-meso CAR T Cell Dose Administered column to string
    infusion_df["Total huCART-meso Administered"] = infusion_df[
        "Total huCART-meso Administered"
    ].multiply(
        10
        ** infusion_df[
            "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TDOSXP_cl_YS_EX10POW1)"
        ]
    )
    infusion_df = infusion_df.drop(
        columns=[
            "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TDOSXP_cl_YS_EX10POW1)"
        ]
    )

    # Total Cell Dose Administered column
    infusion_df = add_rename_column_corelisting(
        infusion_df,
        data,
        "EXINF",
        "Total Cell Dose Administered (IG_NS_NA_EXINF1.NM_NS_NH_TOTDOS)",
        "Total Cell Dose Administered",
        "Subject",
        "Event Label",
    )
    infusion_df = add_rename_column_corelisting(
        infusion_df,
        data,
        "EXINF",
        "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TOTDOSXP_cl_YS_EX10POW1)",
        "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TOTDOSXP_cl_YS_EX10POW1)",
        "Subject",
        "Event Label",
    )
    infusion_df["Total Cell Dose Administered"] = infusion_df[
        "Total Cell Dose Administered"
    ].multiply(
        10
        ** infusion_df[
            "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TOTDOSXP_cl_YS_EX10POW1)"
        ]
    )
    infusion_df = infusion_df.drop(
        columns=[
            "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TOTDOSXP_cl_YS_EX10POW1)"
        ]
    )
    infusion_df = add_rename_column_corelisting(
        infusion_df,
        data,
        "EXINF",
        "Total Volume Administered (mL) (IG_NS_NA_EXINF1.NM_NS_NH_TOTVOL)",
        "Total Volume Administered",
        "Subject",
        "Event Label",
    )
    # Adding Met Target Dose column based on the condition of Total Cell Dose Administered and Total huCART-meso CAR T Cell Dose Administered if 'Target Cell Dose' is integer
    infusion_df["Met Target Dose"] = infusion_df.apply(
        lambda row: (
            "Y"
            if isinstance(row["Target Cell Dose"], int)
            and row["Total huCART-meso Administered"] >= row["Target Cell Dose"]
            else ""
        ),
        axis=1,
    )
    infusion_df["Met Target Dose"] = infusion_df.apply(
        lambda row: (
            "N"
            if isinstance(row["Target Cell Dose"], int)
            and row["Total huCART-meso Administered"] < row["Target Cell Dose"]
            else row["Met Target Dose"]
        ),
        axis=1,
    )

    # %scFv Flow
    infusion_df = add_rename_column_corelisting(
        infusion_df,
        data,
        "EXINF",
        "Transduction Efficiency (%) (IG_NS_NA_EXINF1.NM_NS_NH_TRANSEFFP)",
        "%scFv Flow",
        "Subject",
        "Event Label",
    )

    # adding Met Target %scFv
    infusion_df = add_rename_column_corelisting(
        infusion_df,
        data,
        "EXINF",
        "Transduction Efficiency (%) (IG_NS_NA_EXINF1.NM_NS_NH_TRANSEFFP)",
        "Met Target %scFv",
        "Subject",
        "Event Label",
    )
    # fillter out the rows that have NaN in Met Target %scFv
    infusion_df["Met Target %scFv"] = infusion_df[
        infusion_df["Met Target %scFv"].notna()
    ]["Met Target %scFv"].apply(lambda x: "Y" if x >= 2 else "N")
    # fill NaN with empty string
    infusion_df = infusion_df.fillna("").infer_objects()

    # Only keep the rows that have Event Group Label
    infusion_df = infusion_df[infusion_df["Event Label"] != ""]

    # AE and SAE data
    AE_df = data["AE"][
        [
            "Subject",
            "AE or SAE? (IG_NS_NA_AE2.CL_YS_YH_AESEV_cl_YS_AESAE1)",
            "Event Onset (IG_NS_NA_AE1.CL_NS_YH_AEONSET_cl_NS_AEONSET1)",
        ]
    ].copy()
    AE_new_col_name = {
        "AE or SAE? (IG_NS_NA_AE2.CL_YS_YH_AESEV_cl_YS_AESAE1)": "AE or SAE?",
        "Event Onset (IG_NS_NA_AE1.CL_NS_YH_AEONSET_cl_NS_AEONSET1)": "Event Onset",
    }
    AE_df = AE_df.rename(columns=AE_new_col_name)
    status_df = EL_df[["Subject", "Cohort Assignment"]]
    # Check AE_df if the subject of status_df is in the AE dataframe. If yes, then add 'Y' to the column 'AE' in status_df, else add 'N'
    status_df["AE"] = status_df["Subject"].apply(
        lambda x: "Y" if x in AE_df["Subject"].values else "N"
    )
    # Check AE_df if the subject of status_df has SAE in column 'AE or SAE?' . If yes, then add 'Y' to the column 'SAE', else add 'N'
    status_df["SAE"] = status_df["Subject"].apply(
        lambda x: (
            "Y" if x in AE_df[AE_df["AE or SAE?"] == "SAE"]["Subject"].values else "N"
        )
    )
    # replaces all occurrences of NaN, positive infinity, and negative infinity in the infusion_df dataframe with empty strings.
    status_df = status_df.replace([np.nan, np.inf, -np.inf], "")

    # Event Label Update dictionary for cohort 1
    event_1_dict = {
        "Primary Treatment and Follow Up": "Primary Follow-up",
        "Pre-Treatment Safety Visit": "Pre-Treatment",
        "LTFU (Ongoing Persistence)": "LTFU (Ongoing Persistence)",
        "LTFU (Loss of Persistence)": "LTFU (Loss of Persistence)",
    }

    # Add the pattern match as a separate key
    def map_event(event):
        if event in event_1_dict:
            return event_1_dict[event]
        elif "Loss of Persistence" in event:
            return "LTFU (Loss of Persistence)"
        elif "Ongoing Persistence" in event:
            return "LTFU (Ongoing Persistence)"
        else:
            return event

    # Getting Study Status dataframe from SV, column Subject, Event Label and Event Date
    status_SV_df = data["DSSV"][["Subject", "Event Group Label", "Event Date"]]
    # Getting Study Status dataframe from DSSVLTFU, column Subject, Event Label and Event Date
    status_DSSVLTFU_df = data["DSSVLTFU"][["Subject", "Event Label", "Event Date"]]
    status_DSSVLTFU_df["Event Group Label"] = status_DSSVLTFU_df["Event Label"].apply(
        map_event
    )
    # Combine DSSVLTFU with SV dataframe vertically
    status_SV_df = pd.concat([status_SV_df, status_DSSVLTFU_df])
    # Sort the dataframe by Subject and Event Date
    status_SV_df = status_SV_df.sort_values(by=["Subject", "Event Date"])
    # For each unique subject, get the last row of the dataframe
    status_SV_df = status_SV_df.groupby("Subject").tail(1)
    # Merge left with the current response dataframe
    status_df = pd.merge(
        status_df,
        status_SV_df[["Subject", "Event Group Label"]],
        on="Subject",
        how="left",
    )
    # Rename the column Event Label to Event Label (Study Status)
    status_df["Event Group Label"] = status_df["Event Group Label"].map(event_1_dict)

    status_df["Event Group Label3"] = status_df["Subject"].apply(
        lambda x: (
            "Pre-Treatment"
            if (
                enrollment_df[enrollment_df["Subject"] == x][
                    "Study Treatment Administered"
                ]
                .fillna("")
                .str.strip()
                .values[0]
                == "Pending"
            )
            else ""
        )
    )
    status_df["Event Group Label4"] = status_df["Subject"].apply(
        lambda x: (
            "Withdrawn Prior to Study Treatment"
            if (
                enrollment_df[enrollment_df["Subject"] == x][
                    "Study Treatment Administered"
                ]
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
    status_df["Event Group Label"] = (
        status_df["Event Group Label"].fillna("")
        + status_df["Event Group Label3"].fillna("")
        + status_df["Event Group Label4"].fillna("")
    )
    status_df["Event Group Label"] = status_df["Event Group Label"].fillna(
        status_df["Event Group Label"]
    )
    status_df = status_df.drop(
        columns=[
            "Event Group Label3",
            "Event Group Label4",
        ]
    )
    # filter the data frame to only include subjects whose end of study date is later than or equal to main consent date
    filteredemrollment_df = enrollment_df[
        enrollment_df["End of Study Date"] >= enrollment_df["Main Consent Date"]
    ]
    filteredDSEOS_df = DSEOS_df[
        (DSEOS_df["Last Study Visit"] != "Pre-Screening")
        & (DSEOS_df["Subject"].isin(filteredemrollment_df["Subject"].values))
    ].copy()

    status_df["Event Group Label"] = status_df.apply(
        lambda row: (
            "Off Study"
            if (row["Subject"] in filteredDSEOS_df["Subject"].values)
            & (row["Event Group Label"] != "Withdrawn Prior to Study Treatment")
            else "On Study/" + row["Event Group Label"]
        ),
        axis=1,
    )
    status_df = status_df.replace(
        "On Study/Withdrawn Prior to Study Treatment",
        "Withdrawn Prior to Study Treatment",
    )
    status_df = pd.merge(
        status_df,
        filteredDSEOS_df[["Subject", "Off-Study Reason", "Last Study Visit"]],
        on="Subject",
        how="left",
    )
    # replaces all occurrences of NaN, positive infinity, and negative infinity in the infusion_df dataframe with empty strings.
    status_df = status_df.replace([np.nan, np.inf, -np.inf], "")

    # DSMB-Study Tx & AE STATISTICS
    infusion_count = []
    # * Cohort 1
    # Create a new dataframe for Total huCAR T Cell Dose Administered table with infusion_df
    infusionA_df = infusion_df[infusion_df["Cohort Assignment"] == "Cohort 1"]
    infusion_statA1 = get_stats_df("Total huCART-meso Administered", infusionA_df)
    # Create a new dataframe for Total Cell Dose Administered table with infusion_df
    infusion_statA2 = get_stats_df("Total Cell Dose Administered", infusionA_df)
    # Count the number of subjects that met the target dose
    met_target_count = infusionA_df[infusionA_df["Met Target Dose"] == "Y"].count()[
        "Subject"
    ]
    # Count the number of subjects
    total_subject_count = infusionA_df["Subject"].nunique()
    infusion_statA2["Met Target Dose"] = (
        str(met_target_count)
        + " ("
        + str(round(met_target_count / total_subject_count * 100, 2))
        + "%)"
    )
    # Create a new dataframe for %scFv Flow table with infusion_df
    infusion_statA3 = get_stats_perc_df("%scFv Flow", infusionA_df)
    # Count the number of subjects that met the target %scFv
    met_target_count = infusionA_df[infusionA_df["Met Target %scFv"] == "Y"].count()[
        "Subject"
    ]
    infusion_statA3["Met Target %scFv"] = (
        str(met_target_count)
        + " ("
        + str(round(met_target_count / total_subject_count * 100, 2))
        + "%)"
    )
    # Combine the three dataframes
    infusion_statA = pd.concat(
        [infusion_statA1, infusion_statA2, infusion_statA3], axis=1
    )
    infusion_statA = infusion_statA.replace([np.inf, -np.inf], "")
    infusion_statA = infusion_statA.fillna("")
    infusion_count.append(total_subject_count)

    # FORMATTING THE DATAFRAME
    # Day 0
    # Convert the columns to scientific notation if the value is not NaN

    infusion_df["Target Cell Dose"] = infusion_df["Target Cell Dose"].apply(
        lambda x: (
            convert_float_2_sci_notation(x)
            if not isinstance(x, str) and pd.notna(x)
            else x
        )
    )
    infusion_df["Total huCART-meso Administered"] = infusion_df[
        "Total huCART-meso Administered"
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
    # adding '%' sign to %scFv Flow
    infusion_df["%scFv Flow"] = infusion_df.apply(
        lambda row: str(x) + "%" if pd.notna(x := row["%scFv Flow"]) else x, axis=1
    )
    infusion_df = infusion_df.drop(columns=["Target Cell Dose"])

    if export:
        with pd.ExcelWriter(
            output_dir + "/" + output_file_name + ".xlsx",
            engine="xlsxwriter",
            engine_kwargs={"options": {"nan_inf_to_errors": True}},
        ) as writer:
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
                # DSMB-Demo Stats Table
                if enrollment_df["Subject"].count() > 0:
                    # * WRITING DATA: LegalSex_list, Age_at_Consent_list, Race_list, Ethnicity_list
                    worksheet1 = writer.book.add_worksheet(
                        "DSMB-Demographics Statistics"
                    )

                    # * FORMAT DATA
                    for i in range(0, len(status_list)):
                        for j in range(0, len(LegalSex_list[i])):
                            for k in range(0, len(LegalSex_list[i].columns)):
                                worksheet1.write(
                                    j + 3,
                                    k + 1 + i * 4,
                                    LegalSex_list[i].iloc[j, k],
                                    normal_data_format,
                                )
                        for j in range(0, len(Age_at_Consent_list[i])):
                            for k in range(0, len(Age_at_Consent_list[i].columns)):
                                worksheet1.write(
                                    j + 8,
                                    k + 1 + i * 4,
                                    Age_at_Consent_list[i].iloc[j, k],
                                    normal_data_format,
                                )
                        for j in range(0, len(Race_list[i])):
                            for k in range(0, len(Race_list[i].columns)):
                                worksheet1.write(
                                    j + 12,
                                    k + 1 + i * 4,
                                    Race_list[i].iloc[j, k],
                                    normal_data_format,
                                )
                        for j in range(0, len(Ethnicity_list[i])):
                            for k in range(0, len(Ethnicity_list[i].columns)):
                                worksheet1.write(
                                    j + 22,
                                    k + 1 + i * 4,
                                    Ethnicity_list[i].iloc[j, k],
                                    normal_data_format,
                                )

                    # * WRITING HEADER AND FORMATTING
                    Sex_order = ["Male", "Female", "Nonbinary (X)", "Not Reported"]
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
                        worksheet1.write(i + 3, 0, Sex_order[i], bold_11_format)
                    for i in range(0, len(Age_order)):
                        worksheet1.write(i + 8, 0, Age_order[i], bold_11_format)
                    for i in range(0, len(Race_order)):
                        worksheet1.write(i + 12, 0, Race_order[i], bold_11_format)
                    for i in range(0, len(Ethnicity_order)):
                        worksheet1.write(i + 22, 0, Ethnicity_order[i], bold_11_format)

                    worksheet1.merge_range(
                        "B1:E1", "Overall Study Enrollment", bold_12_format
                    )
                    worksheet1.merge_range(
                        "F1:I1", "Cohort 1 Enrollment", bold_12_format
                    )
                    worksheet1.write(1, 0, "Status", bold_11_format)
                    for i in range(len(status_list)):
                        worksheet1.write(
                            1,
                            1 + i * 4,
                            "Total Consented\nN="
                            + str(status_list[i]["Total Consented"]),
                            bold_11_wrap_format,
                        )
                        worksheet1.write(
                            1,
                            2 + i * 4,
                            "Screen Failed\nN=" + str(status_list[i]["Screen Failed"]),
                            bold_11_wrap_format,
                        )
                        worksheet1.write(
                            1,
                            3 + i * 4,
                            "Eligible\nN=" + str(status_list[i]["Eligible"]),
                            bold_11_wrap_format,
                        )
                        worksheet1.write(
                            1,
                            4 + i * 4,
                            "Study Treatment Administered\nN="
                            + str(status_list[i]["Study Treatment Administered"]),
                            bold_11_wrap_format,
                        )

                    worksheet1.merge_range("A3:I3", "Legal Sex", bold_11_format)
                    worksheet1.merge_range("A8:I8", "Age at Consent", bold_11_format)
                    worksheet1.merge_range("A12:I12", "Race", bold_11_format)
                    worksheet1.merge_range("A22:I22", "Ethnicity", bold_11_format)
                    worksheet1.autofit()

                    # Enrollment Listing
                    # * WRITING DATA: enrollment_df
                    worksheet2 = writer.book.add_worksheet("DSMB-Enrollment Listing")
                    # * WRITING HEADER AND FORMATTING
                    # Assuming 'enrollment_df' is your DataFrame
                    enrollment_df = enrollment_df.drop(
                        columns=[
                            "Off-Study Reason",
                            "End of Study Date",
                            "Main Consent Date",
                        ]
                    )

                    enrollment_df.replace(
                        [np.inf, -np.inf], np.nan, inplace=True
                    )  # Replace INF with NaN
                    enrollment_df = enrollment_df.fillna(
                        ""
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

                    # DSMB-New Infusion Statistics
                    # * WRITING DATA: new_infusion_df
                    # * WRITING DATA: enrollment_df
                    worksheet3 = writer.book.add_worksheet("DSMB-Study Tx Statistics")

                    # * FORMATING DATA
                    for i in range(0, len(infusion_statA)):
                        for j in range(0, len(infusion_statA.columns)):
                            worksheet3.write(
                                i + 3,
                                j + 1,
                                infusion_statA.iloc[i, j],
                                normal_data_format,
                            )

                    # * WRITING HEADER AND FORMATTING
                    stat_order = ["Mean SD", "Median", "Range"]

                    worksheet3.merge_range(
                        "B1:D1", "Cells Administered", bold_12_wrap_format
                    )
                    worksheet3.merge_range(
                        "E1:F1", "Transduction Efficiency", bold_12_wrap_format
                    )
                    worksheet3.write("B2", "huCART-meso Cells", bold_12_wrap_format)
                    worksheet3.write("C2", "Total Cells", bold_12_wrap_format)
                    worksheet3.write("D2", "Met Target Dose", bold_12_wrap_format)
                    worksheet3.write("E2", "%scFv Flow", bold_12_wrap_format)
                    worksheet3.write("F2", "Met Target %scFv", bold_12_wrap_format)
                    worksheet3.merge_range(
                        "A3:F3",
                        "Cohort 1 (N=" + str(infusion_count[0]) + ")",
                        bold_12_wrap_format,
                    )

                    # Merge and format data
                    if infusion_df["Event Label"].count() > 0:
                        infusion_df = infusion_df.drop(columns=["Event Label"])
                        if (
                            not infusion_statA.empty
                            and len(infusion_statA) > 0
                            and infusion_statA.shape[1] > 2
                        ):
                            worksheet3.merge_range(
                                "D4:D6", infusion_statA.iloc[0, 2], normal_data_format
                            )
                        if (
                            not infusion_statA.empty
                            and len(infusion_statA) > 0
                            and infusion_statA.shape[1] > 4
                        ):
                            worksheet3.merge_range(
                                "F4:F6",
                                infusion_statA.iloc[0, 4],
                                normal_data_format,
                            )

                        for i in range(0, len(stat_order)):
                            worksheet3.write(i + 3, 0, stat_order[i], bold_11_format)

                    # * Autofit
                    worksheet3.autofit()

                    # DSMB-Study Tx & AE Listing
                    worksheet4 = writer.book.add_worksheet("DSMB-Study Tx Listing")
                    # * WRITING AND FORMATING DATA
                    for i in range(0, len(infusion_df)):
                        for j in range(0, len(infusion_df.columns)):
                            worksheet4.write(
                                i + 2, j, infusion_df.iloc[i, j], normal_data_format
                            )

                    # * WRITING HEADER AND FORMATTING
                    worksheet4.merge_range("A1:A2", "Subject ID", bold_12_wrap_format)
                    worksheet4.merge_range(
                        "B1:B2", "Cohort Assignment", bold_12_wrap_format
                    )
                    worksheet4.merge_range(
                        "C1:C2", "Dose Level Assignment", bold_12_wrap_format
                    )

                    worksheet4.merge_range(
                        "D1:D2",
                        "Date Study Treatment Administered",
                        bold_12_wrap_format,
                    )
                    worksheet4.merge_range(
                        "E1:H1", "Cells Administered", bold_12_wrap_format
                    )
                    worksheet4.merge_range(
                        "I1:J1", "Transduction Efficiency", bold_12_wrap_format
                    )

                    worksheet4.write(
                        "E2",
                        "Total huCART-meso Dose Administered",
                        bold_12_wrap_format,
                    )
                    worksheet4.write(
                        "F2", "Total Cell Dose Administered", bold_12_wrap_format
                    )
                    worksheet4.write(
                        "G2", "Total Volume Administered", bold_12_wrap_format
                    )
                    worksheet4.write("H2", "Met Target Dose", bold_12_wrap_format)
                    worksheet4.write("I2", "%scFv Flow", bold_12_wrap_format)
                    worksheet4.write("J2", "Met Target %scFv", bold_12_wrap_format)

                    # Autofit
                    worksheet4.autofit()

                    # Summary of Protocol Status
                    worksheet5 = writer.book.add_worksheet(
                        "Status for Eligible Subjects"
                    )
                    # * WRITING AND FORMATING DATA
                    for i in range(0, len(status_df)):
                        for j in range(0, len(status_df.columns)):
                            worksheet5.write(
                                i + 2, j, status_df.iloc[i, j], normal_data_format
                            )

                    # * WRITING HEADER AND FORMATTING
                    worksheet5.merge_range("A1:A2", "Subject ID", bold_12_wrap_format)
                    worksheet5.merge_range(
                        "B1:B2", "Cohort Assignment", bold_12_wrap_format
                    )
                    worksheet5.merge_range(
                        "C1:C2", "Adverse Events (Y/N)", bold_12_wrap_format
                    )
                    worksheet5.merge_range(
                        "D1:D2", "Serious Adverse Events (Y/N)", bold_12_wrap_format
                    )
                    worksheet5.merge_range("E1:E2", "Study Status", bold_12_wrap_format)
                    worksheet5.merge_range(
                        "F1:F2", "Off-Study Reason", bold_12_wrap_format
                    )
                    worksheet5.merge_range(
                        "G1:G2",
                        "Last Study Visit Performed for Off-Study Subject",
                        bold_12_wrap_format,
                    )

                    # Autofit
                    worksheet5.autofit()
