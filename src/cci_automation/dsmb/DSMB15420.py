import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

from cci_automation.dsmb.DSMB_util import (
    get_stats_df,
    get_stats_perc_df,
    get_stats_percentage,
)
from cci_automation.util import (
    add_rename_column_corelisting,
    add_rename_column_df,
    convert_float_2_sci_notation,
    convert_integers_to_strings,
    remove_leading_zeros_from_dates,
)
from clinical_reporting.export import get_named_excel_formats


def DSMB15420(
    data,
    output_dir,
    output_file_name,
):
    # Subject
    enrollment_df = data["DM"][["Subject"]].copy()
    enrollment_df = enrollment_df.sort_values(["Subject"])
    # Cohort Assignment
    enrollment_df = add_rename_column_corelisting(
        enrollment_df,
        data,
        "DSCA",
        "Cohort Assignment (IG_NS_NA_DSCA1.CL_NS_NH_CACHASCOD_cl_NS_COHORT1)",
        "Cohort Assignment",
    )
    # Split Cohort Assignment by ":", keep the first part
    enrollment_df["Cohort Assignment"] = (
        enrollment_df["Cohort Assignment"].str.split(":").str[0]
    )
    # Disease
    enrollment_df = add_rename_column_corelisting(
        enrollment_df,
        data,
        "PRDIAG",
        "Primary Diagnosis of CLL (ig_PRDIAG2.PRDIAGCLL)",
        "Disease CLL",
    )
    enrollment_df = add_rename_column_corelisting(
        enrollment_df,
        data,
        "PRDIAG",
        "Specify Other Diagnosis (ig_PRDIAG2.PRDIAGCLLOTH)",
        "Disease CLL2",
    )
    enrollment_df = add_rename_column_corelisting(
        enrollment_df,
        data,
        "PRDIAG",
        "Primary Diagnosis of NHL (ig_PRDIAG3.PRDIAGNHL)",
        "Disease NHL",
    )
    enrollment_df = add_rename_column_corelisting(
        enrollment_df,
        data,
        "PRDIAG",
        "Specify Other Diagnosis (ig_PRDIAG3.PRDIAGNHLOTH)",
        "Disease NHL2",
    )
    enrollment_df = add_rename_column_corelisting(
        enrollment_df,
        data,
        "PRDIAGALL",
        "Primary Diagnosis of ALL (ig_PRDIAGALL1.PRDIAGALL)",
        "Disease ALL",
    )
    enrollment_df = add_rename_column_corelisting(
        enrollment_df,
        data,
        "PRDIAGALL",
        "Specify Other Diagnosis (ig_PRDIAGALL1.PRDIAGALLOTH)",
        "Disease ALL2",
    )
    enrollment_df = add_rename_column_corelisting(
        enrollment_df,
        data,
        "PRDIAG",
        "Primary Diagnosis at Enrollment (ig_PRDIAG5.PRDIAGRICH)",
        "Disease RICH",
    )
    enrollment_df["Disease"] = None
    # List the columns in the order you want to use them for filling 'Disease'
    columns_to_fill_from = [
        "Disease CLL2",
        "Disease CLL",
        "Disease NHL2",
        "Disease NHL",
        "Disease ALL2",
        "Disease ALL",
        "Disease RICH",
    ]
    # Use fillna() in a loop to fill 'Disease' from the specified columns
    for col in columns_to_fill_from:
        enrollment_df["Disease"] = enrollment_df["Disease"].fillna(enrollment_df[col])
    enrollment_df = enrollment_df.drop(
        columns=[
            "Disease CLL",
            "Disease CLL2",
            "Disease NHL2",
            "Disease NHL",
            "Disease ALL2",
            "Disease ALL",
            "Disease RICH",
        ]
    )
    # Dose Level
    enrollment_df = add_rename_column_corelisting(
        enrollment_df,
        data,
        "DLA",
        "Dose Level Assignment (ig_DLA1.DLADOSELVL)",
        "Dose Level",
    )
    # Legal Sex
    enrollment_df = add_rename_column_corelisting(
        enrollment_df, data, "DM", "Legal Sex (ig_DM1.SEX)", "Legal Sex"
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
        "Gender Identity (ig_DM1.GENDERID2)",
        "Gender Identity",
    )
    # Age
    enrollment_df = add_rename_column_corelisting(
        enrollment_df, data, "DM", "Date of Birth (ig_DM1.BRTHDAT)", "Date of Birth"
    )
    enrollment_df = add_rename_column_corelisting(
        enrollment_df, data, "IE", "Consent Date (ig_IE1.MAINCDAT)", "Consent Date"
    )
    enrollment_df["Consent Date"] = pd.to_datetime(enrollment_df["Consent Date"])
    enrollment_df["Date of Birth"] = pd.to_datetime(enrollment_df["Date of Birth"])
    mask = ~enrollment_df[["Consent Date", "Date of Birth"]].isnull().any(axis=1)
    enrollment_df.loc[mask, "Age"] = enrollment_df[mask].apply(
        lambda x: relativedelta(x["Consent Date"], x["Date of Birth"]).years, axis=1
    )
    enrollment_df = enrollment_df.drop(columns=["Consent Date", "Date of Birth"])
    # Race
    enrollment_df = add_rename_column_corelisting(
        enrollment_df, data, "DM", "Race (ig_DM1.RACE)", "Race"
    )
    # Subject meets all study eligibility?
    enrollment_df = add_rename_column_corelisting(
        enrollment_df,
        data,
        "IE",
        "Subject Meets All Study Eligibility (ig_IE3.IEYN)",
        "Subject meets all study eligibility?",
    )
    # Reason for Screen Failure
    enrollment_df = add_rename_column_corelisting(
        enrollment_df,
        data,
        "IE",
        "Other Screen Fail Reason (ig_IE4.OTHRSFREAS)",
        "Reason for Screen Failure",
    )
    enrollment_df = add_rename_column_corelisting(
        enrollment_df, data, "IE", "Screen Failure Reason (ig_IE4.IECAT)", "SF1"
    )
    enrollment_df = add_rename_column_corelisting(
        enrollment_df,
        data,
        "IE",
        "Select the primary inclusion criterion excluding this subject  (ig_IE4.ITESTCD)",
        "SF2",
    )
    enrollment_df["SF2"] = enrollment_df[enrollment_df["SF2"].notna()]["SF2"].astype(
        int
    )
    enrollment_df = add_rename_column_corelisting(
        enrollment_df,
        data,
        "IE",
        "Select the primary exclusion criterion excluding this subject (ig_IE4.ETESTCD)",
        "SF3",
    )
    enrollment_df["SF3"] = enrollment_df[enrollment_df["SF3"].notna()]["SF3"].astype(
        int
    )
    enrollment_df["SF4"] = (
        enrollment_df["SF1"].fillna("").astype(str)
        + " "
        + enrollment_df["SF2"].round().fillna("").astype(str)
        + enrollment_df["SF3"].round().fillna("").astype(str)
    )
    enrollment_df["Reason for Screen Failure"] = enrollment_df[
        "Reason for Screen Failure"
    ].fillna(enrollment_df["SF4"])
    enrollment_df = enrollment_df.drop(columns=["SF1", "SF2", "SF3", "SF4"])
    # Infused
    enrollment_df = add_rename_column_corelisting(
        enrollment_df, data, "INF", "Event Group Label", "Event Group Label"
    )
    enrollment_df = add_rename_column_corelisting(
        enrollment_df,
        data,
        "INF",
        "Was Infusion Administered? (ig_INF1.INFOCCUR)",
        "Infused",
    )
    enrollment_df = enrollment_df[enrollment_df["Event Group Label"] != "Day 0-R"]
    enrollment_df = enrollment_df.drop(columns=["Event Group Label"])
    enrollment_df = add_rename_column_corelisting(
        enrollment_df,
        data,
        "EOS",
        "End of Study Date (ig_EOS1.EOSDAT)",
        "End of Study Date (ig_EOS1.EOSDAT)",
    )
    # Update 'Infused' column based on the conditions:
    enrollment_df.loc[
        (enrollment_df["Infused"] != "Yes")
        & (enrollment_df["End of Study Date (ig_EOS1.EOSDAT)"].isnull()),
        "Infused",
    ] = "Pending"
    enrollment_df.loc[
        (enrollment_df["Infused"] != "Yes")
        & (~enrollment_df["End of Study Date (ig_EOS1.EOSDAT)"].isnull()),
        "Infused",
    ] = "No"
    enrollment_df = enrollment_df.drop(columns=["End of Study Date (ig_EOS1.EOSDAT)"])
    enrollment_df = enrollment_df.drop_duplicates()

    final_enrollment_df = enrollment_df.copy()

    # Demo Stats Table
    # Calculate Stats of enrollment table
    TT = enrollment_df["Subject"].count()
    TT_df = enrollment_df.copy()

    # Screen Failed
    SF_filter = enrollment_df["Subject meets all study eligibility?"] == "No"
    SF_df = enrollment_df[SF_filter]
    SF = SF_df.count()["Subject"]

    # Function to calculate cohort statistics
    def get_cohort_stats(df, cohort_letter):
        """
        Calculate enrollment statistics for a specific cohort.

        Args:
            df: DataFrame with enrollment data
            cohort_letter: Cohort letter (e.g., 'A', 'B', 'C', 'D')

        Returns:
            tuple: (enrolled_count, infused_count, enrolled_df, infused_df)
        """
        # Prepare DataFrame with empty strings instead of NaN
        df_filled = df.fillna("")

        # Filter for enrolled subjects
        enrolled_filter = df_filled["Cohort Assignment"].str.contains(
            f"Cohort {cohort_letter}"
        ) & (df_filled["Subject meets all study eligibility?"] == "Yes")
        enrolled_df = df_filled.loc[enrolled_filter]
        enrolled_count = enrolled_df.count()["Subject"]

        # Filter for infused subjects
        infused_filter = df_filled["Cohort Assignment"].str.contains(
            f"Cohort {cohort_letter}"
        ) & (df_filled["Infused"] == "Yes")
        infused_df = df_filled.loc[infused_filter]
        infused_count = infused_df.count()["Subject"]

        return enrolled_count, infused_count, enrolled_df, infused_df

    # Calculate statistics for cohorts A, B, C, D
    CAE, CAI, CAE_df, CAI_df = get_cohort_stats(enrollment_df, "A")
    CBE, CBI, CBE_df, CBI_df = get_cohort_stats(enrollment_df, "B")
    CCE, CCI, CCE_df, CCI_df = get_cohort_stats(enrollment_df, "C")
    CDE, CDI, CDE_df, CDI_df = get_cohort_stats(enrollment_df, "D")

    # Fill NaN with empty string for enrollment_df
    final_enrollment_df = final_enrollment_df.fillna("")

    # Define a dictionary containing the status of each variable
    final_status = {
        "Total Screened": TT,
        "Screen Failed": SF,
        "Cohort A Enrolled": CAE,
        "Cohort A Infused": CAI,
        "Cohort B Enrolled": CBE,
        "Cohort B Infused": CBI,
        "Cohort C Enrolled": CCE,
        "Cohort C Infused": CCI,
        "Cohort D Enrolled": CDE,
        "Cohort D Infused": CDI,
    }

    # Create demographic statistics tables
    # Note: The get_stats_percentage and get_stats_df functions need to be updated
    # to include Cohort D statistics (CDE_df, CDI_df)

    # Create a new dataframe for Legal Sex table
    final_LegalSex_df = get_stats_percentage(
        "Legal Sex",
        TT_df,
        SF_df,
        CAE_df,
        CAI_df,
        CBE_df,
        CBI_df,
        CCE_df,
        CCI_df,
        CDE_df,
        CDI_df,
    )

    # Create a new dataframe for Age table
    final_Age_df = get_stats_df(
        "Age",
        TT_df,
        SF_df,
        CAE_df,
        CAI_df,
        CBE_df,
        CBI_df,
        CCE_df,
        CCI_df,
        CDE_df,
        CDI_df,
    )
    final_Age_df = final_Age_df.replace([np.inf, -np.inf], "")
    final_Age_df = final_Age_df.fillna("")

    # Create a new dataframe for Race table
    final_Race_df = get_stats_percentage(
        "Race",
        TT_df,
        SF_df,
        CAE_df,
        CAI_df,
        CBE_df,
        CBI_df,
        CCE_df,
        CCI_df,
        CDE_df,
        CDI_df,
    )

    # * ===== NEW CODE: Create Cohort D only stats tables =====
    # filter to only cohort D
    TTD_df = TT_df[TT_df["Cohort Assignment"].str.contains("Cohort D")]
    SFD_df = SF_df[SF_df["Cohort Assignment"].str.contains("Cohort D")]
    TTD = TTD_df["Subject"].count()
    SFD = SFD_df["Subject"].count()
    # Create demo stats tables for Cohort D only
    final_LegalSex_df_D = get_stats_percentage(
        "Legal Sex", TTD_df, SFD_df, CDE_df, CDI_df
    )
    final_Age_df_D = get_stats_df("Age", TTD_df, SFD_df, CDE_df, CDI_df)
    final_Age_df_D = final_Age_df_D.replace([np.inf, -np.inf], "")
    final_Age_df_D = final_Age_df_D.fillna("")
    final_Race_df_D = get_stats_percentage("Race", TTD_df, SFD_df, CDE_df, CDI_df)

    # Status dictionary for Cohort D
    final_status_D = {
        "Total Screened": TTD,
        "Screen Failed": SFD,
        "Cohort D Enrolled": CDE,
        "Cohort D Infused": CDI,
    }

    # * ===== NEW CODE: Create Cohorts A, B, C combined stats tables =====
    # Filter out cohort D
    TTABC_df = TT_df[~TT_df["Cohort Assignment"].str.contains("Cohort D")]
    SFABC_df = SF_df[~SF_df["Cohort Assignment"].str.contains("Cohort D")]
    TTABC = TTABC_df["Subject"].count()
    SFABC = SFABC_df["Subject"].count()
    # Create demo stats tables for Cohorts A, B, C combined
    final_LegalSex_df_ABC = get_stats_percentage(
        "Legal Sex", TTABC_df, SFABC_df, CAE_df, CAI_df, CBE_df, CBI_df, CCE_df, CCI_df
    )
    final_Age_df_ABC = get_stats_df(
        "Age", TTABC_df, SFABC_df, CAE_df, CAI_df, CBE_df, CBI_df, CCE_df, CCI_df
    )
    final_Age_df_ABC = final_Age_df_ABC.replace([np.inf, -np.inf], "")
    final_Age_df_ABC = final_Age_df_ABC.fillna("")
    final_Race_df_ABC = get_stats_percentage(
        "Race", TTABC_df, SFABC_df, CAE_df, CAI_df, CBE_df, CBI_df, CCE_df, CCI_df
    )

    # Status dictionary for Cohorts A, B, C combined
    final_status_ABC = {
        "Total Screened": TTABC,
        "Screen Failed": SFABC,
        "Cohort A Enrolled": CAE,
        "Cohort A Infused": CAI,
        "Cohort B Enrolled": CBE,
        "Cohort B Infused": CBI,
        "Cohort C Enrolled": CCE,
        "Cohort C Infused": CCI,
    }

    # INFUSION LISTING
    # adding Target Cell Dose dictionary
    TCD_dict = {
        "Dose Level 1a (DL1a)": 3000000,
        "Dose Level 1b (DL1b)": 3000000,
        "Dose Level 2 (DL2)": 7000000,
        "Dose Level 3 (DL3)": 30000000,
        "Dose Level 4 (DL4)": 70000000,
        "Dose Level 5 (DL5)": 300000000,
        "Not Assigned": "Not Assigned",
    }

    # PREPARE DATA FOR INFUSION LISTING
    EXCHMO_df = data["EXCHMO"].copy()
    EXCHMO_df = EXCHMO_df.sort_values(
        ["Subject", "Event Group Label", "Medication (ig_EXCHMO2.EXCCAT)"]
    )
    # select unique subject and Event Group Label
    grouped_df = EXCHMO_df.groupby(["Subject", "Event Group Label"])[
        "Medication (ig_EXCHMO2.EXCCAT)"
    ].unique()
    # convert the unique list to string by joining the list with '+' if the list has more than 1 medication
    grouped_df = grouped_df.apply(
        lambda x: (
            " + ".join(str(val) for val in x if pd.notna(val)) if len(x) > 1 else x[0]
        )
    ).reset_index()
    # replace the Event Group Label with Day 0 and Day 0-R
    grouped_df.loc[
        (grouped_df["Event Group Label"] == "Lymphodepleting Chemotherapy")
        | (grouped_df["Event Group Label"] == "Lymphodepleting Chemotherapy - ALL"),
        "Event Group Label",
    ] = "Day 0"
    grouped_df.loc[
        (grouped_df["Event Group Label"] == "Retreatment Lymphodepleting Chemotherapy")
        | (
            grouped_df["Event Group Label"]
            == "Retreatment Lymphodepleting Chemotherapy - ALL"
        ),
        "Event Group Label",
    ] = "Day 0-R"
    grouped_df.loc[grouped_df["Subject"] == "100-15420-01", "Event Group Label"] = (
        "Day 0-R"
    )
    # reassign the dataframe to EXCHMO_df with subject, Study Day, and Medication
    EXCHMO_df = grouped_df

    # INFUSION LISTING Day 0
    # Subject
    infusion_df = data["DM"][["Subject"]].copy()
    infusion_df = infusion_df.sort_values(["Subject"])
    infusion_df = add_rename_column_corelisting(
        infusion_df, data, "INF", "Event Group Label", "Event Group Label"
    )
    infusion_df = infusion_df[infusion_df["Event Group Label"] == "Day 0"]

    # Cohort Assignment
    infusion_df = add_rename_column_corelisting(
        infusion_df,
        data,
        "DSCA",
        "Cohort Assignment (IG_NS_NA_DSCA1.CL_NS_NH_CACHASCOD_cl_NS_COHORT1)",
        "Cohort Assignment",
    )
    # Dose Level
    infusion_df = add_rename_column_corelisting(
        infusion_df,
        data,
        "DLA",
        "Dose Level Assignment (ig_DLA1.DLADOSELVL)",
        "Dose Level Assignment",
    )
    # Lymphodepleting Chemotherapy Regimen
    infusion_df = add_rename_column_df(
        infusion_df,
        EXCHMO_df[EXCHMO_df["Event Group Label"] == "Day 0"],
        "Medication (ig_EXCHMO2.EXCCAT)",
        "Lymphodepleting Chemotherapy Regimen",
    )
    # Fill NaN with
    # Infusion Date
    infusion_df = add_rename_column_corelisting(
        infusion_df,
        data,
        "INF",
        "Infusion Date (ig_INF1.INFDAT)",
        "Date of huCART19-IL18 Infusion",
        "Subject",
        "Event Group Label",
    )
    # convert the date to datetime object and format it to MM-DD-YYYY
    infusion_df = remove_leading_zeros_from_dates(infusion_df)

    # adding Target Cell Dose using TCD_dict
    infusion_df["Target Cell Dose"] = infusion_df["Dose Level Assignment"].map(TCD_dict)

    # Total huCart19-IL18 Cell Dose
    infusion_df = add_rename_column_corelisting(
        infusion_df,
        data,
        "INF",
        "CAR T Cell Dose Administered (ig_INF1.INFDOS)",
        "Total huCAR T Cell Dose Administered",
        "Subject",
        "Event Group Label",
    )
    infusion_df = add_rename_column_corelisting(
        infusion_df,
        data,
        "INF",
        "x 10 to the power of (ig_INF1.INFDOSXP)",
        "x 10 to the power of (ig_INF1.INFDOSXP)",
        "Subject",
        "Event Group Label",
    )
    # combine Total huCart19-IL18 Cell Dose and x 10 to the power of (ig_INF1.INFDOSXP) columns, compare the new value with 'Target Cell Dose', and convert the Total huCart19-IL18 Cell Dose column to string
    infusion_df["Total huCAR T Cell Dose Administered"] = infusion_df[
        "Total huCAR T Cell Dose Administered"
    ].multiply(10 ** infusion_df["x 10 to the power of (ig_INF1.INFDOSXP)"])
    infusion_df = infusion_df.drop(columns=["x 10 to the power of (ig_INF1.INFDOSXP)"])

    # Total Cell Dose Administered column
    infusion_df = add_rename_column_corelisting(
        infusion_df,
        data,
        "INF",
        "Total Cell Dose Administered (ig_INF1.INFDOSTOT)",
        "Total Cell Dose Administered",
        "Subject",
        "Event Group Label",
    )
    infusion_df = add_rename_column_corelisting(
        infusion_df,
        data,
        "INF",
        "x 10 to the power of (ig_INF1.INFDOSTOTXP)",
        "x 10 to the power of (ig_INF1.INFDOSTOTXP)",
        "Subject",
        "Event Group Label",
    )
    infusion_df["Total Cell Dose Administered"] = infusion_df[
        "Total Cell Dose Administered"
    ].multiply(10 ** infusion_df["x 10 to the power of (ig_INF1.INFDOSTOTXP)"])
    infusion_df = infusion_df.drop(
        columns=["x 10 to the power of (ig_INF1.INFDOSTOTXP)"]
    )

    # Adding Met Target Dose column based on the condition of Total Cell Dose Administered and Total huCAR T Cell Dose Administered if 'Target Cell Dose' is integer
    infusion_df["Met Target Dose"] = infusion_df.apply(
        lambda row: (
            "Y"
            if isinstance(row["Target Cell Dose"], int)
            and row["Total huCAR T Cell Dose Administered"] >= row["Target Cell Dose"]
            else ""
        ),
        axis=1,
    )
    infusion_df["Met Target Dose"] = infusion_df.apply(
        lambda row: (
            "N"
            if isinstance(row["Target Cell Dose"], int)
            and row["Total huCAR T Cell Dose Administered"] < row["Target Cell Dose"]
            else row["Met Target Dose"]
        ),
        axis=1,
    )

    # %scFv Flow
    infusion_df = add_rename_column_corelisting(
        infusion_df,
        data,
        "INF",
        "Transduction Efficiency (%) (ig_INF1.INFTEFFP)",
        "%scFv Flow",
        "Subject",
        "Event Group Label",
    )

    # adding Met Target %scFv
    infusion_df = add_rename_column_corelisting(
        infusion_df,
        data,
        "INF",
        "Transduction Efficiency (%) (ig_INF1.INFTEFFP)",
        "Met Target %scFv",
        "Subject",
        "Event Group Label",
    )
    # fillter out the rows that have NaN in Met Target %scFv
    infusion_df["Met Target %scFv"] = infusion_df[
        infusion_df["Met Target %scFv"].notna()
    ]["Met Target %scFv"].apply(lambda x: "Y" if x >= 2 else "N")
    # fill NaN with empty string
    infusion_df = infusion_df.fillna("")

    # Only keep the rows that have Event Group Label
    infusion_df = infusion_df[infusion_df["Event Group Label"] != ""]

    # Infusion Listing Day 0-R
    # Subject
    infusionR_df = data["DM"][["Subject"]].copy()
    infusionR_df = infusionR_df.sort_values(["Subject"])
    infusionR_df = add_rename_column_corelisting(
        infusionR_df, data, "INF", "Event Group Label", "Event Group Label"
    )
    infusionR_df = infusionR_df[infusionR_df["Event Group Label"] != "Day 0"]

    # Cohort Assignment
    infusionR_df = add_rename_column_corelisting(
        infusionR_df,
        data,
        "DSCA",
        "Cohort Assignment (IG_NS_NA_DSCA1.CL_NS_NH_CACHASCOD_cl_NS_COHORT1)",
        "Cohort Assignment",
    )
    # Lymphodepleting Chemotherapy Regimen
    infusionR_df = add_rename_column_df(
        infusionR_df,
        EXCHMO_df[EXCHMO_df["Event Group Label"] != "Day 0"],
        "Medication (ig_EXCHMO2.EXCCAT)",
        "Lymphodepleting Chemotherapy Regimen",
    )
    # Infusion Date
    infusionR_df = add_rename_column_corelisting(
        infusionR_df,
        data,
        "INF",
        "Infusion Date (ig_INF1.INFDAT)",
        "Date of huCART19-IL18 Infusion",
        "Subject",
        "Event Group Label",
    )
    # convert the date to datetime object and format it to MM-DD-YYYY
    infusionR_df = remove_leading_zeros_from_dates(infusionR_df)

    # Total huCart19-IL18 Cell Dose
    infusionR_df = add_rename_column_corelisting(
        infusionR_df,
        data,
        "INF",
        "CAR T Cell Dose Administered (ig_INF1.INFDOS)",
        "Total huCAR T Cell Dose Administered",
        "Subject",
        "Event Group Label",
    )
    infusionR_df = add_rename_column_corelisting(
        infusionR_df,
        data,
        "INF",
        "x 10 to the power of (ig_INF1.INFDOSXP)",
        "x 10 to the power of (ig_INF1.INFDOSXP)",
        "Subject",
        "Event Group Label",
    )
    # combine Total huCart19-IL18 Cell Dose and x 10 to the power of (ig_INF1.INFDOSXP) columns, compare the new value with 'Target Cell Dose', and convert the Total huCart19-IL18 Cell Dose column to string
    infusionR_df["Total huCAR T Cell Dose Administered"] = infusionR_df[
        "Total huCAR T Cell Dose Administered"
    ].multiply(10 ** infusionR_df["x 10 to the power of (ig_INF1.INFDOSXP)"])
    infusionR_df = infusionR_df.drop(
        columns=["x 10 to the power of (ig_INF1.INFDOSXP)"]
    )

    # Total Cell Dose Administered column
    infusionR_df = add_rename_column_corelisting(
        infusionR_df,
        data,
        "INF",
        "Total Cell Dose Administered (ig_INF1.INFDOSTOT)",
        "Total Cell Dose Administered",
        "Subject",
        "Event Group Label",
    )
    infusionR_df = add_rename_column_corelisting(
        infusionR_df,
        data,
        "INF",
        "x 10 to the power of (ig_INF1.INFDOSTOTXP)",
        "x 10 to the power of (ig_INF1.INFDOSTOTXP)",
        "Subject",
        "Event Group Label",
    )
    infusionR_df["Total Cell Dose Administered"] = infusionR_df[
        "Total Cell Dose Administered"
    ].multiply(10 ** infusionR_df["x 10 to the power of (ig_INF1.INFDOSTOTXP)"])
    infusionR_df = infusionR_df.drop(
        columns=["x 10 to the power of (ig_INF1.INFDOSTOTXP)"]
    )

    # %scFv Flow
    infusionR_df = add_rename_column_corelisting(
        infusionR_df,
        data,
        "INF",
        "Transduction Efficiency (%) (ig_INF1.INFTEFFP)",
        "%scFv Flow",
        "Subject",
        "Event Group Label",
    )

    # adding Met Target %scFv
    infusionR_df = add_rename_column_corelisting(
        infusionR_df,
        data,
        "INF",
        "Transduction Efficiency (%) (ig_INF1.INFTEFFP)",
        "Met Target %scFv",
        "Subject",
        "Event Group Label",
    )
    # fillter out the rows that have NaN in Met Target %scFv
    infusionR_df["Met Target %scFv"] = infusionR_df[
        infusionR_df["Met Target %scFv"].notna()
    ]["Met Target %scFv"].apply(lambda x: "Y" if x >= 2 else "N")
    # fill NaN with empty string
    infusionR_df = infusionR_df.fillna("")

    # Only keep the rows that have Event Group Label
    infusionR_df = infusionR_df[infusionR_df["Event Group Label"] != ""]

    # INFUSION STATISTICS
    def calculate_cohort_infusion_stats(infusion_df, cohort_filter):
        """
        Calculate infusion statistics for a specific cohort.

        Parameters:
        -----------
        infusion_df : pd.DataFrame
            The main infusion dataframe
        cohort_filter : str or callable
            Either a string to match "Cohort Assignment" column or a callable filter function

        Returns:
        --------
        tuple: (combined_stats_df, subject_count)
            - combined_stats_df: DataFrame with all statistics
            - subject_count: Number of unique subjects in the cohort
        """
        # Filter the dataframe based on cohort
        if isinstance(cohort_filter, str):
            cohort_df = infusion_df[infusion_df["Cohort Assignment"] == cohort_filter]
        else:
            cohort_df = infusion_df[cohort_filter(infusion_df)]

        # Get subject count
        total_subject_count = cohort_df["Subject"].nunique()

        # If no subjects, return empty stats
        if total_subject_count == 0:
            empty_df = pd.DataFrame()
            return empty_df, 0

        # Calculate statistics for Total huCAR T Cell Dose Administered
        stat1 = get_stats_df("Total huCAR T Cell Dose Administered", cohort_df)

        # Calculate statistics for Total Cell Dose Administered
        stat2 = get_stats_df("Total Cell Dose Administered", cohort_df)

        # Calculate Met Target Dose percentage
        met_target_dose_count = cohort_df[cohort_df["Met Target Dose"] == "Y"][
            "Subject"
        ].nunique()
        met_target_dose_pct = (
            round(met_target_dose_count / total_subject_count * 100, 2)
            if total_subject_count > 0
            else 0
        )
        stat2["Met Target Dose"] = f"{met_target_dose_count} ({met_target_dose_pct}%)"

        # Calculate statistics for %scFv Flow
        stat3 = get_stats_perc_df("%scFv Flow", cohort_df)

        # Calculate Met Target %scFv percentage
        met_target_scfv_count = cohort_df[cohort_df["Met Target %scFv"] == "Y"][
            "Subject"
        ].nunique()
        met_target_scfv_pct = (
            round(met_target_scfv_count / total_subject_count * 100, 2)
            if total_subject_count > 0
            else 0
        )
        stat3["Met Target %scFv"] = f"{met_target_scfv_count} ({met_target_scfv_pct}%)"

        # Combine all statistics
        combined_stats = pd.concat([stat1, stat2, stat3], axis=1)
        combined_stats = combined_stats.replace([np.inf, -np.inf], "")
        combined_stats = combined_stats.fillna("")

        return combined_stats, total_subject_count

    # INFUSION STATISTICS - REFACTORED VERSION
    # Define cohort mappings
    cohort_mappings = {
        "A": "Cohort A: Non-Hodgkin Lymphoma (NHL)",
        "B": "Cohort B: Chronic Lymphocytic Leukemia (CLL)",
        "C": "Cohort C: Acute Lymphoblastic Leukemia (ALL)",
        "D": "Cohort D",  # Add the exact string used for Cohort D in your data
    }

    # Initialize storage for results
    infusion_stats = {}
    infusion_count = []

    # Process each cohort
    for cohort_key, cohort_filter in cohort_mappings.items():
        stats_df, subject_count = calculate_cohort_infusion_stats(
            infusion_df, cohort_filter
        )

        # Store results using the naming convention from original code
        infusion_stats[f"infusion_stat{cohort_key}"] = stats_df
        infusion_count.append(subject_count)

    # Assign to individual variables for backward compatibility
    final_infusion_statA = infusion_stats.get("infusion_statA", pd.DataFrame())
    final_infusion_statB = infusion_stats.get("infusion_statB", pd.DataFrame())
    final_infusion_statC = infusion_stats.get("infusion_statC", pd.DataFrame())
    final_infusion_statD = infusion_stats.get("infusion_statD", pd.DataFrame())

    # FORMATTING THE DATAFRAME
    # Day 0
    # Convert the columns to scientific notation if the value is not NaN
    infusion_df["Target Cell Dose"] = infusion_df["Target Cell Dose"].apply(
        lambda x: (
            convert_float_2_sci_notation(x) if isinstance(x, int) and pd.notna(x) else x
        )
    )
    infusion_df["Total huCAR T Cell Dose Administered"] = infusion_df[
        "Total huCAR T Cell Dose Administered"
    ].apply(
        lambda x: (
            convert_float_2_sci_notation(x)
            if isinstance(x, float) and pd.notna(x)
            else x
        )
    )
    infusion_df["Total Cell Dose Administered"] = infusion_df[
        "Total Cell Dose Administered"
    ].apply(
        lambda x: (
            convert_float_2_sci_notation(x)
            if isinstance(x, float) and pd.notna(x)
            else x
        )
    )
    # adding '%' sign to %scFv Flow
    infusion_df["%scFv Flow"] = infusion_df.apply(
        lambda row: str(x) + "%" if pd.notna(x := row["%scFv Flow"]) else x, axis=1
    )

    # Day 0-R
    # Convert the columns to scientific notation if the value is not NaN
    infusionR_df["Total huCAR T Cell Dose Administered"] = infusionR_df[
        "Total huCAR T Cell Dose Administered"
    ].apply(
        lambda x: (
            convert_float_2_sci_notation(x)
            if isinstance(x, float) and pd.notna(x)
            else x
        )
    )
    infusionR_df["Total Cell Dose Administered"] = infusionR_df[
        "Total Cell Dose Administered"
    ].apply(
        lambda x: (
            convert_float_2_sci_notation(x)
            if isinstance(x, float) and pd.notna(x)
            else x
        )
    )
    # adding '%' sign to %scFv Flow
    infusionR_df["%scFv Flow"] = infusionR_df.apply(
        lambda row: str(x) + "%" if pd.notna(x := row["%scFv Flow"]) else x, axis=1
    )

    # ASSIGNING THE DATAFRAME TO THE CLASS VARIABLE
    final_infusion_df = infusion_df
    final_infusionR_df = infusionR_df

    # RESPONSE LISTING
    # PREPARE
    # Disease Response NHL PET based dictionary
    DR_NHL_PET_dict = {
        "Complete Metabolic Response (CMR)": 1,
        "Partial Metabolic Response (PMR)": 2,
        "No Metabolic Response (NMR)": 3,
        "Indeterminate Response (IR)": 4,
        "Progressive Metabolic Disease (PMD)": 5,
        "Not Assessed": 6,
        "Not Evaluable": 7,
        "Not Reported": 10,
    }
    # Disease Response NHL CT based dictionary
    DR_NHL_CT_dict = {
        "Complete Radiologic Response (CR)": 1,
        "Partial Response (PR)": 2,
        "Stable Disease (SD)": 3,
        "Indeterminate Response (IR)": 4,
        "Progressive Disease (PD)": 5,
        "Not Assessed": 6,
        "Not Evaluable": 7,
        "Not Reported": 10,
    }
    # Disease Response CLL Overall dictionary
    DR_CLL_OV_dict = {
        "Complete Remission (CR)": 1,
        "Complete Remission with Incomplete Marrow Recovery (CRi)": 2,
        "Partial Remission (PR)": 3,
        "Stable Disease (SD)": 4,
        "Progressive Disease (PD)": 5,
        "Not Assessed": 6,
        "Not Evaluable": 7,
        "Not Reported": 10,
    }
    # Disease Response CLL Bone Marrow dictionary
    DR_CLL_BM_dict = {
        "Complete Remission (CR)": 1,
        "Partial Remission (PR)": 2,
        "Progressive Disease (PD)": 3,
        "Stable Disease (SD)": 4,
        "Not Assessed": 5,
        "Not Evaluable": 6,
        "Not Reported": 10,
    }
    # Disease Response ALL Overall Resposne dictionary
    DR_ALL_OV_dict = {
        "Complete Remission (CR)": 1,
        "Complete Remission with Incomplete Blood Count Recovery (CRi)": 2,
        "Complete Remission with Residual Mediastinal Disease (CRu)": 3,
        "Treatment Failure (TF)": 4,
        "Relapsed Disease (RD)": 5,
        "Extramedullary Disease Without Bone Marrow Involvement": 6,
        "No Clinical Evidence of Relapse": 7,
        "Unknown/Not Assessed": 8,
        "Not Reported": 9,
        "Not Applicable": 10,
    }
    # Disease Response ALL Extramedullary Disease without Bone Marrow Involvement dictionary
    DR_ALL_ED_dict = {
        "Complete Remission (CR)": 1,
        "Partial Remission (PR)": 2,
        "Stable Disease (SD)": 3,
        "Indeterminate Response": 4,
        "Progressive Disease (PD)": 5,
        "Not Assessed": 6,
        "Not Reported": 9,
        "Not Applicable": 10,
    }
    # Event Label Update dictionary for cohort A and B
    event_AB_dict = {
        "Primary Treatment and Follow-Up": "Primary Treatment",
        "Primary Retreatment and Follow-up": "Primary Retreatment",
        "Pre-Retreatment Safety Visit": "Pre-Retreatment",
        "Long Term Follow-up Months 3-60": "Long Term Follow-up",
        "Retreatment Long Term Follow-up Months 3-60": "Retreatment Long Term Follow-up",
    }
    # Event Label Update dictionary for cohort C
    event_C_dict = {
        "Primary Treatment and Follow-up - ALL": "Primary Treatment",
        "Primary Retreatment and Follow-up - ALL": "Primary Retreatment",
        "Pre-Retreatment Safety Visit - ALL": "Pre-Retreatment",
        "Retreatment Lymphodepleting Chemotherapy - ALL": "Retreatment Lymphodepleting",
        " Long Term Follow-up Months 3-60 - ALL": "Long Term Follow-up",
        "Retreatment Long Term Follow-up Months 3-60 - ALL": "Retreatment Long Term Follow-up",
    }

    # Get data from Initiation of Long Term Follow up
    PD_df = data["INITLF"][
        [
            "Subject",
            "From which Phase is the Subject entering Long-Term Follow-Up? (ig_INITLF1.DSPHASE)",
            "End of Primary Follow-Up Date (ig_INITLF1.DSENPFUDAT)",
            "Provide reason the Subject is entering into the Long-Term Follow-Up Phase (ig_INITLF2.DSLTFURE)",
        ]
    ].copy()
    # Filter the data to only subject with 'Disease progression' in Provide reason the Subject is entering into the Long-Term Follow-Up Phase (ig_INITLF2.DSLTFURE) column
    PD_df = PD_df[
        PD_df[
            "Provide reason the Subject is entering into the Long-Term Follow-Up Phase (ig_INITLF2.DSLTFURE)"
        ]
        == "Disease progression"
    ]
    # Filter the data to subject in Primary Follow up
    PD_df = PD_df[
        PD_df[
            "From which Phase is the Subject entering Long-Term Follow-Up? (ig_INITLF1.DSPHASE)"
        ]
        == "Primary Follow-Up"
    ]
    # Convert End of Primary Follow-Up Date (ig_INITLF1.DSENPFUDAT) to datetime object
    PD_df["End of Primary Follow-Up Date (ig_INITLF1.DSENPFUDAT)"] = pd.to_datetime(
        PD_df["End of Primary Follow-Up Date (ig_INITLF1.DSENPFUDAT)"]
    )

    # Get data from Initiation of Long Term Follow up
    PD_Retx_df = data["INITLF"][
        [
            "Subject",
            "From which Phase is the Subject entering Long-Term Follow-Up? (ig_INITLF1.DSPHASE)",
            "End of Retreatment Date (ig_INITLF1.DSENRETXDAT)",
            "Provide reason the Subject is entering into the Long-Term Follow-Up Phase (ig_INITLF2.DSLTFURE)",
        ]
    ].copy()
    # Filter the data to only subject with 'Disease progression' in Provide reason the Subject is entering into the Long-Term Follow-Up Phase (ig_INITLF2.DSLTFURE) column
    PD_Retx_df = PD_Retx_df[
        PD_Retx_df[
            "Provide reason the Subject is entering into the Long-Term Follow-Up Phase (ig_INITLF2.DSLTFURE)"
        ]
        == "Disease progression"
    ]
    # Filter the data to subject in Retreatment
    PD_Retx_df = PD_Retx_df[
        PD_Retx_df[
            "From which Phase is the Subject entering Long-Term Follow-Up? (ig_INITLF1.DSPHASE)"
        ]
        == "Retreatment"
    ]
    # Convert End of Retreatment Date (ig_INITLF1.DSENRETXDAT) to datetime object
    PD_Retx_df["End of Retreatment Date (ig_INITLF1.DSENRETXDAT)"] = pd.to_datetime(
        PD_Retx_df["End of Retreatment Date (ig_INITLF1.DSENRETXDAT)"]
    )

    # Get data from DSINITRT
    DSINITRT_df = data["DSINITRT"][
        [
            "Subject",
            "Will the Subject receive Retreatment? (ig_DSINITRT1.DSRTYN)",
            "From which Phase is the Subject entering Retreatment? (ig_DSINITRT1.DSPHASER)",
            "End of Primary Follow-Up Date (ig_DSINITRT1.DSRENPFUDAT)",
        ]
    ].copy()
    # Filter out subjects that will not receive retreatment
    DSINITRT_df = DSINITRT_df[
        DSINITRT_df["Will the Subject receive Retreatment? (ig_DSINITRT1.DSRTYN)"]
        != "No"
    ]
    # Convert End of Primary Follow-Up Date (ig_DSINITRT1.DSRENPFUDAT) to datetime object
    DSINITRT_df["End of Primary Follow-Up Date (ig_DSINITRT1.DSRENPFUDAT)"] = (
        pd.to_datetime(
            DSINITRT_df["End of Primary Follow-Up Date (ig_DSINITRT1.DSRENPFUDAT)"]
        )
    )

    # RESPONSE LISTING NHL ONLY
    # Response data dataframe for NHL only
    response_df = data["RS"][
        [
            "Subject",
            "Event Group Label",
            "Event Date",
            "Disease Type (ig_RS1.RSCAT)",
            "Study Phase (ig_RS1.STUDYPHS2)",
            "Primary Treatment Time Point (ig_RS1.RSTPT)",
            "For Unscheduled Primary Treatment Time Point, Specify Day #  (ig_RS1.RSTPTDY)",
            "Retreatment Time Point (ig_RS1.RSTPTR)",
            "For Unscheduled Retreatment Time Point, Specify Day # (ig_RS1.UNSDAYR)",
            "PET-Based Response (ig_RS3.RSIMAGTYP1)",
            "CT-Based Response (ig_RS3.RSIMAGTYP2)",
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)",
            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)",
        ]
    ].copy()
    responseA_df = response_df[
        response_df["Disease Type (ig_RS1.RSCAT)"] == "Non-Hodgkin Lymphoma"
    ]
    responseA_df = responseA_df.sort_values(by=["Subject", "Event Date"])
    # replace Not Assessed with Not Reported in all columns
    responseA_df = responseA_df.replace("Not Assessed", "Not Reported")
    # replace Not Evaluable with Not Reported in all columns
    responseA_df = responseA_df.replace("Not Evaluable", "Not Reported")
    # Filter to Richter's Transformation
    responseBRT_df = response_df[
        response_df["Disease Type (ig_RS1.RSCAT)"] == "Richter's Transformation"
    ]
    responseBRT_df = responseBRT_df.sort_values(by=["Subject", "Event Date"])
    # replace Not Assessed with Not Reported in all columns
    responseBRT_df = responseBRT_df.replace("Not Assessed", "Not Reported")
    # replace Not Evaluable with Not Reported in all columns
    responseBRT_df = responseBRT_df.replace("Not Evaluable", "Not Reported")

    # Cohort A - NHL Primary
    # Filter to only Primary Treatment
    responseA_primary_df = responseA_df[
        responseA_df["Study Phase (ig_RS1.STUDYPHS2)"] == "Primary Treatment"
    ]
    # Replace value of "Unscheduled" in column Primary Treatment Time Point (ig_RS1.RSTPT) with value of "Unscheduled Primary Treatment Time Point, Specify Day #  (ig_RS1.RSTPTDY)"
    temp_mask = (
        responseA_primary_df["Primary Treatment Time Point (ig_RS1.RSTPT)"]
        == "Unscheduled"
    )
    responseA_primary_df = convert_integers_to_strings(
        responseA_primary_df,
        "For Unscheduled Primary Treatment Time Point, Specify Day #  (ig_RS1.RSTPTDY)",
    )

    responseA_primary_df.loc[
        temp_mask, "Primary Treatment Time Point (ig_RS1.RSTPT)"
    ] = responseA_primary_df.loc[
        temp_mask,
        "For Unscheduled Primary Treatment Time Point, Specify Day #  (ig_RS1.RSTPTDY)",
    ].apply(lambda x: f"Day {x}" if pd.notna(x) and str(x).strip().isdigit() else x)
    # Remove rows with Pre-Treatment Safety Visit
    responseA_primary_df = responseA_primary_df[
        responseA_primary_df["Primary Treatment Time Point (ig_RS1.RSTPT)"]
        != "Pre-Treatment Safety Visit"
    ]
    # Convert Event Date to datetime object
    responseA_primary_df["Event Date"] = pd.to_datetime(
        responseA_primary_df["Event Date"]
    )
    # Snapshot the responseA_primary_df
    responseA_primary_df_snapshot = responseA_primary_df.copy()
    # check the number of subject for cohort B - CLL Retreatment
    final_subject_A_prim_count = len(responseA_primary_df["Subject"].unique())

    # Check if there is any subject. If yes, then proceed, else skip
    if final_subject_A_prim_count > 0:
        # Fill NaN with "Not Reported" in column PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)
        responseA_primary_df["PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"] = (
            responseA_primary_df[
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
            ].fillna("Not Reported")
        )
        # Fill NaN with "Not Reported" in column CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)
        responseA_primary_df["CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"] = (
            responseA_primary_df[
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
            ].fillna("Not Reported")
        )
        # Convert PET-Based NHL Disease Response and CT-Based NHL Disease Response to numeric values
        responseA_primary_df["PET-Score"] = responseA_primary_df[
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
        ].map(DR_NHL_PET_dict)
        responseA_primary_df["CT-Score"] = responseA_primary_df[
            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
        ].map(DR_NHL_CT_dict)

        # * CURRENT RESPONSE
        # Get the indices of the rows with the maximum 'Event Date' for each 'Subject'
        idx = responseA_primary_df.groupby("Subject")["Event Date"].idxmax()
        # Select these rows for the current response
        responseA_primary_current_df = responseA_primary_df.loc[idx].copy()
        # Fill NaN with "Not Reported" in column PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)
        responseA_primary_current_df[
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
        ] = responseA_primary_current_df[
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
        ].fillna("Not Reported")
        # Fill NaN with "Not Reported" in column CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)
        responseA_primary_current_df[
            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
        ] = responseA_primary_current_df[
            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
        ].fillna("Not Reported")

        # * BEST RESPONSE
        ## Best PET-Based NHL Disease Response primary
        # Get the indices of the rows with the minimum 'PET-Best' for each 'Subject'
        responseA_best_PET_idx = responseA_primary_df.groupby("Subject")[
            "PET-Score"
        ].idxmin()
        # Select these rows for the best PET-based response
        responseA_best_PET_df = responseA_primary_df.loc[responseA_best_PET_idx].copy()
        # Select the columns subject and PET-Based NHL Disease Response from responseA_best_PET_df
        responseA_best_PET_df = responseA_best_PET_df[
            [
                "Subject",
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)",
                "Primary Treatment Time Point (ig_RS1.RSTPT)",
            ]
        ]
        # Rename the column PET-Based NHL Disease Response to PET-Based Response
        responseA_best_PET_df.rename(
            columns={
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)": "PET-Based Response",
                "Primary Treatment Time Point (ig_RS1.RSTPT)": "Best PET Time Point",
            },
            inplace=True,
        )
        # Merge left with the primary current response dataframe
        final_response_NHL_primary_df = pd.merge(
            responseA_primary_current_df,
            responseA_best_PET_df,
            on="Subject",
            how="left",
        )

        ## Best CT-Based NHL Disease Response primary
        # Get the indices of the rows with the minimum 'CT-Best' for each 'Subject'
        responseA_best_CT_idx = responseA_primary_df.groupby("Subject")[
            "CT-Score"
        ].idxmin()
        # Select these rows for the best CT-based response
        responseA_best_CT_df = responseA_primary_df.loc[responseA_best_CT_idx]
        # Select the columns subject and CT-Based NHL Disease Response from responseA_best_CT_df
        responseA_best_CT_df = responseA_best_CT_df[
            [
                "Subject",
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)",
                "Primary Treatment Time Point (ig_RS1.RSTPT)",
            ]
        ]
        # Rename the column CT-Based NHL Disease Response to CT-Based Response
        responseA_best_CT_df.rename(
            columns={
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)": "CT-Based Response",
                "Primary Treatment Time Point (ig_RS1.RSTPT)": "Best CT Time Point",
            },
            inplace=True,
        )
        # Merge left with the primary response dataframe
        final_response_NHL_primary_df = pd.merge(
            final_response_NHL_primary_df,
            responseA_best_CT_df,
            on="Subject",
            how="left",
        )

        ## Overall NHL Disease Response at Month 3 primary
        # Filter responseA_primary_df to only Month 3
        responseA_primary_M3_df = responseA_df[
            responseA_df["Primary Treatment Time Point (ig_RS1.RSTPT)"] == "Month 3"
        ]
        # Selec the columns subject and PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) from responseA_primary_M3_df
        responseA_primary_M3_df = responseA_primary_M3_df[
            [
                "Subject",
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)",
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)",
                "Event Date",
            ]
        ]
        # Compare responseA_primary_M3_df with responseA_df, and add the subjects (do it once) that are not in responseA_primary_M3_df to responseA_primary_M3_df
        responseA_primary_M3_df = pd.concat(
            [
                responseA_primary_M3_df,
                responseA_df[
                    ~responseA_df["Subject"].isin(responseA_primary_M3_df["Subject"])
                ][["Subject"]],
            ]
        )
        # Remove duplicates
        responseA_primary_M3_df = responseA_primary_M3_df.drop_duplicates(
            subset=["Subject"]
        )
        # Copy snapshot of responseA_primary_df to a temporary dataframe
        temp_df = responseA_primary_df_snapshot
        # Sort the temporary dataframe by Subject and Event Date
        temp_df = temp_df.sort_values(by=["Subject", "Event Date"])
        # remove all the rows that have nan in PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) and CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)
        temp_df = temp_df[
            temp_df["PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"].notna()
            | temp_df["CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"].notna()
        ]
        # Create a for loop that will check the PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) and CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT) of each subject in responseA_primary_M3_df
        for index, row in responseA_primary_M3_df.iterrows():
            # check if the PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) of the subject is nan, and check if the CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT) of the subject is nan
            if pd.isna(
                row["PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"]
            ) and pd.isna(row["CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"]):
                # if yes, check to see if the subject in in PD_df
                if row["Subject"] in PD_df["Subject"].values:
                    # get the End of Primary Follow-Up Date (ig_INITLF1.DSENPFUDAT) date of the subject in PD_df
                    end_date = PD_df[PD_df["Subject"] == row["Subject"]][
                        "End of Primary Follow-Up Date (ig_INITLF1.DSENPFUDAT)"
                    ].values[0]
                    # find the response of the same subject with the latest event date that is before the Month 3 event date
                    filtered_df = temp_df[
                        (temp_df["Subject"] == row["Subject"])
                        & (temp_df["Event Date"] <= end_date)
                    ]
                    # Check if the filtered DataFrame is empty
                    if not filtered_df.empty:
                        # Access the last row if the DataFrame is not empty
                        temp_row = filtered_df.iloc[-1]
                        # Replace the PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) of the subject with the PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) of the temp_row
                        responseA_primary_M3_df.loc[
                            index, "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
                        ] = temp_row[
                            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
                        ]
                        # Replace the CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT) of the subject with the CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT) of the temp_row
                        responseA_primary_M3_df.loc[
                            index, "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
                        ] = temp_row[
                            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
                        ]
                # check if the subject is in Initiation of REtx before month 3
                elif row["Subject"] in DSINITRT_df["Subject"].values:
                    # get the End of Primary Follow-Up Date (ig_INITLF1.DSENPFUDAT) date of the subject in DSINITRT_df
                    end_date = DSINITRT_df[DSINITRT_df["Subject"] == row["Subject"]][
                        "End of Primary Follow-Up Date (ig_DSINITRT1.DSRENPFUDAT)"
                    ].values[0]
                    # find the response of the same subject with the latest event date that is before the Month 3 event date
                    filtered_df = temp_df[
                        (temp_df["Subject"] == row["Subject"])
                        & (temp_df["Event Date"] <= end_date)
                    ]
                    # Check if the filtered DataFrame is empty
                    if not filtered_df.empty:
                        # Access the last row if the DataFrame is not empty
                        temp_row = filtered_df.iloc[-1]
                        # Replace the PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) of the subject with the PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) of the temp_row
                        responseA_primary_M3_df.loc[
                            index, "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
                        ] = temp_row[
                            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
                        ]
                        # Replace the CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT) of the subject with the CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT) of the temp_row
                        responseA_primary_M3_df.loc[
                            index, "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
                        ] = temp_row[
                            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
                        ]
        # Rename the column PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) to PET-Based ORR
        responseA_primary_M3_df.rename(
            columns={
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)": "PET-Based ORR",
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)": "CT-Based ORR",
            },
            inplace=True,
        )
        # Merge left with the current response dataframe
        final_response_NHL_primary_df = pd.merge(
            final_response_NHL_primary_df,
            responseA_primary_M3_df,
            on="Subject",
            how="left",
        )
        # Fill NaN with "Not Reported" in column PET-Based ORR
        final_response_NHL_primary_df["PET-Based ORR"] = final_response_NHL_primary_df[
            "PET-Based ORR"
        ].fillna("Not Reported")
        # Fill NaN with "Not Reported" in column CT-Based ORR
        final_response_NHL_primary_df["CT-Based ORR"] = final_response_NHL_primary_df[
            "CT-Based ORR"
        ].fillna("Not Reported")

        ## Checking AE and SAE for NHL primary
        # Getting AE and SAE dataframes
        responseA_primary_AE_df = data["AE"][
            [
                "Subject",
                "Form ILB Status",
                "AE or SAE? (ig_AE2.AESEV)",
                "Event Onset (ig_AE1.AEONSET)",
            ]
        ]
        # Check responseA_primary_AE_df if the subject of responseA_primary_df is in the AE dataframe. If yes, then add 'Y' to the column 'AE' in responseA_primary_df, else add 'N'
        final_response_NHL_primary_df["AE"] = final_response_NHL_primary_df[
            "Subject"
        ].apply(
            lambda x: "Y" if x in responseA_primary_AE_df["Subject"].values else "N"
        )
        # Check responseA_primary_AE_df if the subject of responseA_primary_df has SAE in column 'AE or SAE? (ig_AE2.AESEV)' . If yes, then add 'Y' to the column 'SAE' in responseA_primary_df, else add 'N'
        final_response_NHL_primary_df["SAE"] = final_response_NHL_primary_df[
            "Subject"
        ].apply(
            lambda x: (
                "Y"
                if x
                in responseA_primary_AE_df[
                    responseA_primary_AE_df["AE or SAE? (ig_AE2.AESEV)"] == "SAE"
                ]["Subject"].values
                else "N"
            )
        )

        ## Checking Study Status for NHL primary
        # Getting Study Status dataframe from SV, column Subject, Event Label and Event Date
        responseA_primary_SV_df = data["SV"][["Subject", "Event Label", "Event Date"]]
        # Getting Study Status dataframe from DSSVLTFU, column Subject, Event Label and Event Date
        responseA_primary_DSSVLTFU_df = data["DSSVLTFU"][
            ["Subject", "Event Label", "Event Date"]
        ]
        # Getting End of Study status from EOS,
        responseA_primary_EOS_df = data["EOS"][
            ["Subject", "End of Study Date (ig_EOS1.EOSDAT)"]
        ]
        # Combine DSSVLTFU with SV dataframe vertically
        responseA_primary_SV_df = pd.concat(
            [responseA_primary_SV_df, responseA_primary_DSSVLTFU_df]
        )
        # Sort the dataframe by Subject and Event Date
        responseA_primary_SV_df = responseA_primary_SV_df.sort_values(
            by=["Subject", "Event Date"]
        )
        # For each unique subject, get the last row of the dataframe
        responseA_primary_SV_df = responseA_primary_SV_df.groupby("Subject").tail(1)
        # Merge with EOS data to get End of Study Date
        responseA_primary_SV_df = pd.merge(
            responseA_primary_SV_df, responseA_primary_EOS_df, on="Subject", how="left"
        )
        # Format the End of Study Date if available
        responseA_primary_SV_df = remove_leading_zeros_from_dates(
            responseA_primary_SV_df
        )
        # Merge left with the current response dataframe
        final_response_NHL_primary_df = pd.merge(
            final_response_NHL_primary_df,
            responseA_primary_SV_df[
                ["Subject", "Event Label", "End of Study Date (ig_EOS1.EOSDAT)"]
            ],
            on="Subject",
            how="left",
        )
        # Rename the column Event Label to Event Label (Study Status)
        final_response_NHL_primary_df["Event Label"] = final_response_NHL_primary_df[
            "Event Label"
        ].map(event_AB_dict)
        # Add End of Study Date to Event Label if available
        final_response_NHL_primary_df["Event Label"] = (
            final_response_NHL_primary_df.apply(
                lambda row: (
                    f"{row['Event Label']} (EOS:{row['End of Study Date (ig_EOS1.EOSDAT)']})"
                    if row["End of Study Date (ig_EOS1.EOSDAT)"]
                    else row["Event Label"]
                ),
                axis=1,
            )
        )
        # Select the columns needed only
        final_response_NHL_primary_df = final_response_NHL_primary_df[
            [
                "Subject",
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)",
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)",
                "Primary Treatment Time Point (ig_RS1.RSTPT)",
                "PET-Based Response",
                "Best PET Time Point",
                "CT-Based Response",
                "Best CT Time Point",
                "PET-Based ORR",
                "CT-Based ORR",
                "AE",
                "SAE",
                "Event Label",
            ]
        ]
        final_response_NHL_primary_df = final_response_NHL_primary_df.replace(
            [np.nan, np.inf, -np.inf], ""
        )
        # Find subjects in Cohort D from enrollment listing
        cohort_D_subjects = final_enrollment_df[
            final_enrollment_df["Cohort Assignment"].str.contains("Cohort D")
        ]["Subject"].tolist()
        # Cohort A
        cohort_A_subjects = final_enrollment_df[
            final_enrollment_df["Cohort Assignment"].str.contains("Cohort A")
        ]["Subject"].tolist()
        # Subjects in Cohort D
        final_responseD_NHL_df = final_response_NHL_primary_df[
            final_response_NHL_primary_df["Subject"].isin(cohort_D_subjects)
        ].copy()

        # Subjects in Cohort A
        final_responseA_primary_df = final_response_NHL_primary_df[
            final_response_NHL_primary_df["Subject"].isin(cohort_A_subjects)
        ].copy()

        # * Formatting the dataframe

    # Cohort A - NHL Retreatment
    # Filter to only Primary Treatment
    responseA_retreatment_df = responseA_df[
        responseA_df["Study Phase (ig_RS1.STUDYPHS2)"] == "Retreatment"
    ]
    # Replace value of "Unscheduled" in column Retreatment Time Point (ig_RS1.RSTPT) with value of "Unscheduled Retreatment  Treatment Time Point, Specify Day #  (ig_RS1.RSTPTDY)"
    temp_mask = (
        responseA_retreatment_df["Retreatment Time Point (ig_RS1.RSTPTR)"]
        == "Unscheduled"
    )
    # Convert the column For Unscheduled Retreatment Time Point, Specify Day # (ig_RS1.UNSDAYR) to string
    responseA_retreatment_df = convert_integers_to_strings(
        responseA_retreatment_df,
        "For Unscheduled Retreatment Time Point, Specify Day # (ig_RS1.UNSDAYR)",
    )
    responseA_retreatment_df.loc[
        temp_mask, "Retreatment Time Point (ig_RS1.RSTPTR)"
    ] = responseA_retreatment_df.loc[
        temp_mask,
        "For Unscheduled Retreatment Time Point, Specify Day # (ig_RS1.UNSDAYR)",
    ].apply(
        lambda x: (
            f"Day {x}"
            if pd.notna(x) and str(x).strip().replace("-R", "").isdigit()
            else x
        )
    )
    # Remove rows with Pre-Treatment Safety Visit
    responseA_retreatment_df = responseA_retreatment_df[
        responseA_retreatment_df["Retreatment Time Point (ig_RS1.RSTPTR)"]
        != "Pre-Retreatment Safety Visit"
    ]
    # Convert Event Date to datetime object
    responseA_retreatment_df["Event Date"] = pd.to_datetime(
        responseA_retreatment_df["Event Date"]
    )
    # Snapshot the responseA_retreatment_df
    responseA_retreatment_df_snapshot = responseA_retreatment_df.copy()
    # check the number of subject for cohort B - CLL Retreatment
    final_subject_A_retx_count = len(responseA_retreatment_df["Subject"].unique())

    # Check if there is any subject. If yes, then proceed, else skip
    if final_subject_A_retx_count > 0:
        # Fill NaN with "Not Reported" in column PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)
        responseA_retreatment_df[
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
        ] = responseA_retreatment_df[
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
        ].fillna("Not Reported")
        # Fill NaN with "Not Reported" in column CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)
        responseA_retreatment_df[
            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
        ] = responseA_retreatment_df[
            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
        ].fillna("Not Reported")
        # Convert PET-Based NHL Disease Response and CT-Based NHL Disease Response to numeric values
        responseA_retreatment_df["PET-Score"] = responseA_retreatment_df[
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
        ].map(DR_NHL_PET_dict)
        responseA_retreatment_df["CT-Score"] = responseA_retreatment_df[
            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
        ].map(DR_NHL_CT_dict)

        # * CURRENT RESPONSE
        # Get the indices of the rows with the maximum 'Event Date' for each 'Subject'
        idx = responseA_retreatment_df.groupby("Subject")["Event Date"].idxmax()
        # Select these rows for the current response
        responseA_retreatment_current_df = responseA_retreatment_df.loc[idx].copy()
        # Fill NaN with "Not Reported" in column PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)
        responseA_retreatment_current_df[
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
        ] = responseA_retreatment_current_df[
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
        ].fillna("Not Reported")
        # Fill NaN with "Not Reported" in column CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)
        responseA_retreatment_current_df[
            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
        ] = responseA_retreatment_current_df[
            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
        ].fillna("Not Reported")

        # * BEST RESPONSE
        ## Best PET-Based NHL Disease Response primary
        # Get the indices of the rows with the minimum 'PET-Best' for each 'Subject'
        responseA_best_PET_idx = responseA_retreatment_df.groupby("Subject")[
            "PET-Score"
        ].idxmin()
        # Select these rows for the best PET-based response
        responseA_best_PET_df = responseA_retreatment_df.loc[
            responseA_best_PET_idx
        ].copy()
        # Select the columns subject and PET-Based NHL Disease Response from responseA_best_PET_df
        responseA_best_PET_df = responseA_best_PET_df[
            [
                "Subject",
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)",
                "Retreatment Time Point (ig_RS1.RSTPTR)",
            ]
        ]
        # Rename the column PET-Based NHL Disease Response to PET-Based Response
        responseA_best_PET_df.rename(
            columns={
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)": "PET-Based Response",
                "Retreatment Time Point (ig_RS1.RSTPTR)": "Best PET Time Point",
            },
            inplace=True,
        )
        # Fill NaN with "Not Reported" in column PET-Based Response
        responseA_best_PET_df["PET-Based Response"] = responseA_best_PET_df[
            "PET-Based Response"
        ].fillna("Not Reported")
        # Merge left with the primary current response dataframe
        final_responseA_retreatment_df = pd.merge(
            responseA_retreatment_current_df,
            responseA_best_PET_df,
            on="Subject",
            how="left",
        )

        ## Best CT-Based NHL Disease Response primary
        # Get the indices of the rows with the minimum 'CT-Best' for each 'Subject'
        responseA_best_CT_idx = responseA_retreatment_df.groupby("Subject")[
            "CT-Score"
        ].idxmin()
        # Select these rows for the best CT-based response
        responseA_best_CT_df = responseA_retreatment_df.loc[responseA_best_CT_idx]
        # Select the columns subject and CT-Based NHL Disease Response from responseA_best_CT_df
        responseA_best_CT_df = responseA_best_CT_df[
            [
                "Subject",
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)",
                "Retreatment Time Point (ig_RS1.RSTPTR)",
            ]
        ]
        # Rename the column CT-Based NHL Disease Response to CT-Based Response
        responseA_best_CT_df.rename(
            columns={
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)": "CT-Based Response",
                "Retreatment Time Point (ig_RS1.RSTPTR)": "Best CT Time Point",
            },
            inplace=True,
        )
        # Fill NaN with "Not Reported" in column CT-Based Response
        responseA_best_CT_df["CT-Based Response"] = responseA_best_CT_df[
            "CT-Based Response"
        ].fillna("Not Reported")
        # Merge left with the primary response dataframe
        final_responseA_retreatment_df = pd.merge(
            final_responseA_retreatment_df,
            responseA_best_CT_df,
            on="Subject",
            how="left",
        )

        ## * Overall NHL Disease Response at Month 3-R
        # Filter responseA_retreatment_df to only Month 3-R
        responseA_retreatment_M3_df = responseA_df[
            responseA_df["Retreatment Time Point (ig_RS1.RSTPTR)"] == "Month 3-R"
        ]
        # Selec the columns subject and PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) from responseA_retreatment_M3_df
        responseA_retreatment_M3_df = responseA_retreatment_M3_df[
            [
                "Subject",
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)",
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)",
                "Event Date",
            ]
        ]
        # Compare responseA_retreatment_M3_df with responseA_df, and add the subjects (do it once) that are not in responseA_retreatment_M3_df to responseA_retreatment_M3_df
        responseA_retreatment_M3_df = pd.concat(
            [
                responseA_retreatment_M3_df,
                responseA_df[
                    ~responseA_df["Subject"].isin(
                        responseA_retreatment_M3_df["Subject"]
                    )
                ][["Subject"]],
            ]
        )
        # Remove duplicates
        responseA_retreatment_M3_df = responseA_retreatment_M3_df.drop_duplicates(
            subset=["Subject"]
        )

        # Copy snapshot of responseA_retreatment_df to a temporary dataframe
        temp_df = responseA_retreatment_df_snapshot
        # Sort the temporary dataframe by Subject and Event Date
        temp_df = temp_df.sort_values(by=["Subject", "Event Date"])
        # remove all the rows that have nan in PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) and CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)
        temp_df = temp_df[
            temp_df["PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"].notna()
            | temp_df["CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"].notna()
        ]
        # Create a for loop that will check the PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) and CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT) of each subject in responseA_retreatment_M3_df
        for index, row in responseA_retreatment_M3_df.iterrows():
            # check if the PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) of the subject is nan, and check if the CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT) of the subject is nan
            if pd.isna(
                row["PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"]
            ) and pd.isna(row["CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"]):
                # if yes, check to see if the subject in in PD_Retx_df
                if row["Subject"] in PD_Retx_df["Subject"].values:
                    # get the End of Retreatment Date (ig_INITLF1.DSENRETXDAT) date of the subject in PD_Retx_df
                    end_date = PD_Retx_df[PD_Retx_df["Subject"] == row["Subject"]][
                        "End of Retreatment Date (ig_INITLF1.DSENRETXDAT)"
                    ].values[0]
                    # if yes, find the response of the same subject with the latest event date that is before the Month 3 event date
                    filtered_df = temp_df[
                        (temp_df["Subject"] == row["Subject"])
                        & (temp_df["Event Date"] <= end_date)
                    ]
                    # Check if the filtered DataFrame is empty
                    if not filtered_df.empty:
                        # Access the last row if the DataFrame is not empty
                        temp_row = filtered_df.iloc[-1]
                        # Replace the PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) of the subject with the PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) of the temp_row
                        responseA_retreatment_M3_df.loc[
                            index, "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
                        ] = temp_row[
                            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
                        ]
                        # Replace the CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT) of the subject with the CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT) of the temp_row
                        responseA_retreatment_M3_df.loc[
                            index, "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
                        ] = temp_row[
                            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
                        ]
        # Rename the column PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) to PET-Based ORR
        responseA_retreatment_M3_df.rename(
            columns={
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)": "PET-Based ORR",
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)": "CT-Based ORR",
            },
            inplace=True,
        )
        # Merge left with the current response dataframe
        final_responseA_retreatment_df = pd.merge(
            final_responseA_retreatment_df,
            responseA_retreatment_M3_df,
            on="Subject",
            how="left",
        )
        # Fill NaN with "Not Reported" in column PET-Based ORR
        final_responseA_retreatment_df["PET-Based ORR"] = (
            final_responseA_retreatment_df["PET-Based ORR"].fillna("Not Reported")
        )
        # Fill NaN with "Not Reported" in column CT-Based ORR
        final_responseA_retreatment_df["CT-Based ORR"] = final_responseA_retreatment_df[
            "CT-Based ORR"
        ].fillna("Not Reported")

        ## Checking AE and SAE for NHL primary
        # Getting AE and SAE dataframes
        responseA_retreatment_AE_df = data["AE"][
            [
                "Subject",
                "Form ILB Status",
                "AE or SAE? (ig_AE2.AESEV)",
                "Event Onset (ig_AE1.AEONSET)",
            ]
        ]
        # Check responseA_retreatment_AE_df if the subject of responseA_retreatment_df is in the AE dataframe. If yes, then add 'Y' to the column 'AE' in responseA_retreatment_df, else add 'N'
        final_responseA_retreatment_df["AE"] = final_responseA_retreatment_df[
            "Subject"
        ].apply(
            lambda x: "Y" if x in responseA_retreatment_AE_df["Subject"].values else "N"
        )
        # Check responseA_retreatment_AE_df if the subject of responseA_retreatment_df has SAE in column 'AE or SAE? (ig_AE2.AESEV)' . If yes, then add 'Y' to the column 'SAE' in responseA_retreatment_df, else add 'N'
        final_responseA_retreatment_df["SAE"] = final_responseA_retreatment_df[
            "Subject"
        ].apply(
            lambda x: (
                "Y"
                if x
                in responseA_retreatment_AE_df[
                    responseA_retreatment_AE_df["AE or SAE? (ig_AE2.AESEV)"] == "SAE"
                ]["Subject"].values
                else "N"
            )
        )

        ## Checking Study Status for NHL primary
        # Getting Study Status dataframe from SV, column Subject, Event Label and Event Date
        responseA_retreatment_SV_df = data["SV"][
            ["Subject", "Event Label", "Event Date"]
        ]
        # Getting Study Status dataframe from DSSVLTFU, column Subject, Event Label and Event Date
        responseA_retreatment_DSSVLTFU_df = data["DSSVLTFU"][
            ["Subject", "Event Label", "Event Date"]
        ]
        # Getting End of Study status from EOS
        responseA_retreatment_EOS_df = data["EOS"][
            ["Subject", "End of Study Date (ig_EOS1.EOSDAT)"]
        ]
        # Combine DSSVLTFU with SV dataframe vertically
        responseA_retreatment_SV_df = pd.concat(
            [responseA_retreatment_SV_df, responseA_retreatment_DSSVLTFU_df]
        )
        # Sort the dataframe by Subject and Event Date
        responseA_retreatment_SV_df = responseA_retreatment_SV_df.sort_values(
            by=["Subject", "Event Date"]
        )
        # For each unique subject, get the last row of the dataframe
        responseA_retreatment_SV_df = responseA_retreatment_SV_df.groupby(
            "Subject"
        ).tail(1)
        # Merge with EOS data to get End of Study Date
        responseA_retreatment_SV_df = pd.merge(
            responseA_retreatment_SV_df,
            responseA_retreatment_EOS_df,
            on="Subject",
            how="left",
        )
        # Format the End of Study Date if available
        responseA_retreatment_SV_df = remove_leading_zeros_from_dates(
            responseA_retreatment_SV_df
        )
        # Merge left with the current response dataframe
        final_responseA_retreatment_df = pd.merge(
            final_responseA_retreatment_df,
            responseA_retreatment_SV_df[
                ["Subject", "Event Label", "End of Study Date (ig_EOS1.EOSDAT)"]
            ],
            on="Subject",
            how="left",
        )

        # * Formatting the dataframe
        # Rename the column Event Label to Event Label (Study Status)
        final_responseA_retreatment_df["Event Label"] = final_responseA_retreatment_df[
            "Event Label"
        ].map(event_AB_dict)
        # Add End of Study Date to Event Label if available
        final_responseA_retreatment_df["Event Label"] = (
            final_responseA_retreatment_df.apply(
                lambda row: (
                    f"{row['Event Label']} (EOS:{row['End of Study Date (ig_EOS1.EOSDAT)']})"
                    if row["End of Study Date (ig_EOS1.EOSDAT)"]
                    else row["Event Label"]
                ),
                axis=1,
            )
        )
        # Select the columns needed only
        final_responseA_retreatment_df = final_responseA_retreatment_df[
            [
                "Subject",
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)",
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)",
                "Retreatment Time Point (ig_RS1.RSTPTR)",
                "PET-Based Response",
                "Best PET Time Point",
                "CT-Based Response",
                "Best CT Time Point",
                "PET-Based ORR",
                "CT-Based ORR",
                "AE",
                "SAE",
                "Event Label",
            ]
        ]
        final_responseA_retreatment_df = final_responseA_retreatment_df.replace(
            [np.nan, np.inf, -np.inf], ""
        )
    # Cohort B - CLL for Primary
    # RESPONSE LISTING CLL ONLY
    # Response data dataframe for CLL only
    response_df = data["RS"][
        [
            "Subject",
            "Form Status",
            "Event Group Label",
            "Event Date",
            "Disease Type (ig_RS1.RSCAT)",
            "Study Phase (ig_RS1.STUDYPHS2)",
            "Primary Treatment Time Point (ig_RS1.RSTPT)",
            "For Unscheduled Primary Treatment Time Point, Specify Day #  (ig_RS1.RSTPTDY)",
            "Retreatment Time Point (ig_RS1.RSTPTR)",
            "For Unscheduled Retreatment Time Point, Specify Day # (ig_RS1.UNSDAYR)",
            "Overall CLL Disease Response (ig_RS2.RSCLLCAT)",
            "Disease Response Date (ig_RS2.RSDAT)",
            "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)",
        ]
    ].copy()
    response_df = response_df[response_df["Form Status"] == "Submitted"]
    # Filter to Chronic Lymphocytic Leukemia
    responseB_df = response_df[
        response_df["Disease Type (ig_RS1.RSCAT)"] == "Chronic Lymphocytic Leukemia"
    ]
    responseB_df = responseB_df.sort_values(by=["Subject", "Event Date"])
    # Convert Event Date to datetime object
    responseB_df["Event Date"] = pd.to_datetime(responseB_df["Event Date"])
    # Replace Not Assessed with Not Reported in all columns
    responseB_df = responseB_df.replace("Not Assessed", "Not Reported")
    # Replace Not Evaluable with Not Reported in all columns
    responseB_df = responseB_df.replace("Not Evaluable", "Not Reported")

    # Cohort B - CLL Primary
    # Filter to only Primary Treatment
    responseB_primary_df = responseB_df[
        responseB_df["Study Phase (ig_RS1.STUDYPHS2)"] == "Primary Treatment"
    ]
    # Remove rows with Pre-Treatment Safety Visit
    responseB_primary_df = responseB_primary_df[
        responseB_primary_df["Primary Treatment Time Point (ig_RS1.RSTPT)"]
        != "Pre-Treatment Safety Visit"
    ]
    # Snapshot the responseB_primary_df
    responseB_primary_df_snapshot = responseB_primary_df.copy()
    # check the number of subject for cohort B - CLL Retreatment
    final_subject_B_prim_count = len(responseB_primary_df["Subject"].unique())

    # Check if there is any subject. If yes, then proceed, else skip
    if final_subject_B_prim_count > 0:
        # Replace value of "Unscheduled" in column Primary Treatment Time Point (ig_RS1.RSTPT) with value of "Unscheduled Primary Treatment Time Point, Specify Day #  (ig_RS1.RSTPTDY)"
        temp_mask = (
            responseB_primary_df["Primary Treatment Time Point (ig_RS1.RSTPT)"]
            == "Unscheduled"
        )
        # Convert the column For Unscheduled Primary Treatment Time Point, Specify Day #  (ig_RS1.RSTPTDY) to string
        responseB_primary_df = convert_integers_to_strings(
            responseB_primary_df,
            "For Unscheduled Primary Treatment Time Point, Specify Day #  (ig_RS1.RSTPTDY)",
        )
        responseB_primary_df.loc[
            temp_mask, "Primary Treatment Time Point (ig_RS1.RSTPT)"
        ] = responseB_primary_df.loc[
            temp_mask,
            "For Unscheduled Primary Treatment Time Point, Specify Day #  (ig_RS1.RSTPTDY)",
        ].apply(lambda x: f"Day {x}" if pd.notna(x) and str(x).strip().isdigit() else x)

        # Fill NaN with "Not Reported" in column Overall CLL Disease Response (ig_RS2.RSCLLCAT)
        responseB_primary_df["Overall CLL Disease Response (ig_RS2.RSCLLCAT)"] = (
            responseB_primary_df[
                "Overall CLL Disease Response (ig_RS2.RSCLLCAT)"
            ].fillna("Not Reported")
        )
        # Fill NaN with "Not Reported" in column CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)
        responseB_primary_df["CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)"] = (
            responseB_primary_df[
                "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)"
            ].fillna("Not Reported")
        )
        # Convert OV-Based CLL Disease Response and CT-Based CLL Disease Response to numeric values
        responseB_primary_df["OV-Score"] = responseB_primary_df[
            "Overall CLL Disease Response (ig_RS2.RSCLLCAT)"
        ].map(DR_CLL_OV_dict)
        responseB_primary_df["BM-Score"] = responseB_primary_df[
            "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)"
        ].map(DR_CLL_BM_dict)

        # * CURRENT RESPONSE
        # Get the indices of the rows with the maximum 'Event Date' for each 'Subject'
        idx = responseB_primary_df.groupby("Subject")["Event Date"].idxmax()
        # Select these rows for the current response
        responseB_primary_current_df = responseB_primary_df.loc[idx].copy()
        # Fill NaN with "Not Reported" in column Overall CLL Disease Response (ig_RS2.RSCLLCAT)
        responseB_primary_current_df[
            "Overall CLL Disease Response (ig_RS2.RSCLLCAT)"
        ] = responseB_primary_current_df[
            "Overall CLL Disease Response (ig_RS2.RSCLLCAT)"
        ].fillna("Not Reported")
        # Fill NaN with "Not Reported" in column CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)
        responseB_primary_current_df[
            "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)"
        ] = responseB_primary_current_df[
            "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)"
        ].fillna("Not Reported")

        # * BEST RESPONSE
        ## Best OV-Based CLL Disease Response primary
        # Get the indices of the rows with the minimum 'OV-Best' for each 'Subject'
        responseB_best_OV_idx = responseB_primary_df.groupby("Subject")[
            "OV-Score"
        ].idxmin()
        # Select these rows for the best OV-based response
        responseB_best_OV_df = responseB_primary_df.loc[responseB_best_OV_idx].copy()
        # Select the columns subject and OV-Based CLL Disease Response from responseB_best_OV_df
        responseB_best_OV_df = responseB_best_OV_df[
            [
                "Subject",
                "Overall CLL Disease Response (ig_RS2.RSCLLCAT)",
                "Primary Treatment Time Point (ig_RS1.RSTPT)",
            ]
        ]
        # Rename the column OV-Based CLL Disease Response to OV-Based Response
        responseB_best_OV_df.rename(
            columns={
                "Overall CLL Disease Response (ig_RS2.RSCLLCAT)": "OV-Best Response",
                "Primary Treatment Time Point (ig_RS1.RSTPT)": "Best OV Time Point",
            },
            inplace=True,
        )
        # Merge left with the primary current response dataframe
        final_responseB_primary_df = pd.merge(
            responseB_primary_current_df, responseB_best_OV_df, on="Subject", how="left"
        )

        ## Best CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)
        # Get the indices of the rows with the minimum 'CT-Best' for each 'Subject'
        responseB_best_CT_idx = responseB_primary_df.groupby("Subject")[
            "BM-Score"
        ].idxmin()
        # Select these rows for the best CT-based response
        responseB_best_CT_df = responseB_primary_df.loc[responseB_best_CT_idx]
        # Select the columns subject and CT-Based CLL Disease Response from responseB_best_CT_df
        responseB_best_CT_df = responseB_best_CT_df[
            [
                "Subject",
                "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)",
                "Primary Treatment Time Point (ig_RS1.RSTPT)",
            ]
        ]
        # Rename the column CT-Based CLL Disease Response to CT-Based Response
        responseB_best_CT_df.rename(
            columns={
                "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)": "BM-Best Response",
                "Primary Treatment Time Point (ig_RS1.RSTPT)": "Best BM Time Point",
            },
            inplace=True,
        )
        # Merge left with the primary response dataframe
        final_responseB_primary_df = pd.merge(
            final_responseB_primary_df, responseB_best_CT_df, on="Subject", how="left"
        )

        ## * Overall CLL Disease Response at Month 3 primary
        # Filter responseB_primary_df to only Month 3
        responseB_primary_M3_df = responseB_df[
            responseB_df["Primary Treatment Time Point (ig_RS1.RSTPT)"] == "Month 3"
        ]
        # Selec the columns subject and Overall CLL Disease Response (ig_RS2.RSCLLCAT) from responseB_primary_M3_df
        responseB_primary_M3_df = responseB_primary_M3_df[
            [
                "Subject",
                "Overall CLL Disease Response (ig_RS2.RSCLLCAT)",
                "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)",
            ]
        ]
        # Compare responseB_primary_M3_df with responseB_df, and add the subjects (do it once) that are not in responseB_primary_M3_df to responseB_primary_M3_df
        responseB_primary_M3_df = pd.concat(
            [
                responseB_primary_M3_df,
                responseB_df[
                    ~responseB_df["Subject"].isin(responseB_primary_M3_df["Subject"])
                ][["Subject"]],
            ]
        )
        # Remove duplicates
        responseB_primary_M3_df = responseB_primary_M3_df.drop_duplicates(
            subset=["Subject"]
        )
        # Copy snapshot of responseB_primary_df to a temporary dataframe
        temp_df = responseB_primary_df_snapshot
        # Sort the temporary dataframe by Subject and Event Date
        temp_df = temp_df.sort_values(by=["Subject", "Event Date"])
        # remove all the rows that have nan in Overall CLL Disease Response (ig_RS2.RSCLLCAT) and CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)
        temp_df = temp_df[
            temp_df["Overall CLL Disease Response (ig_RS2.RSCLLCAT)"].notna()
            | temp_df["CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)"].notna()
        ]
        # Create a for loop that will check the Overall CLL Disease Response (ig_RS2.RSCLLCAT) and CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP) of each subject in responseB_primary_M3_df
        for index, row in responseB_primary_M3_df.iterrows():
            # check if the Overall CLL Disease Response (ig_RS2.RSCLLCAT) of the subject is nan, and check if the CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP) of the subject is nan
            if pd.isna(
                row["Overall CLL Disease Response (ig_RS2.RSCLLCAT)"]
            ) and pd.isna(row["CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)"]):
                # if yes, check to see if the subject in in PD_df
                if row["Subject"] in PD_df["Subject"].values:
                    # get the End of Primary Follow-Up Date (ig_INITLF1.DSENPFUDAT) date of the subject in PD_df
                    end_date = PD_df[PD_df["Subject"] == row["Subject"]][
                        "End of Primary Follow-Up Date (ig_INITLF1.DSENPFUDAT)"
                    ].values[0]
                    # if yes, find the response of the same subject with the latest event date that is before the Month 3 event date
                    filtered_df = temp_df[
                        (temp_df["Subject"] == row["Subject"])
                        & (temp_df["Event Date"] <= end_date)
                    ]
                    # Check if the filtered DataFrame is empty
                    if not filtered_df.empty:
                        # Access the last row if the DataFrame is not empty
                        temp_row = filtered_df.iloc[-1]
                        # Replace the Overall CLL Disease Response (ig_RS2.RSCLLCAT) of the subject with the Overall CLL Disease Response (ig_RS2.RSCLLCAT) of the temp_row
                        responseB_primary_M3_df.loc[
                            index, "Overall CLL Disease Response (ig_RS2.RSCLLCAT)"
                        ] = temp_row["Overall CLL Disease Response (ig_RS2.RSCLLCAT)"]
                        # Replace the CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP) of the subject with the CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP) of the temp_row
                        responseB_primary_M3_df.loc[
                            index, "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)"
                        ] = temp_row["CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)"]
                # check if the subject is in Initiation of REtx before month 3
                elif row["Subject"] in DSINITRT_df["Subject"].values:
                    # get the End of Primary Follow-Up Date (ig_INITLF1.DSENPFUDAT) of the subject in DSINITRT_df
                    end_date = DSINITRT_df[DSINITRT_df["Subject"] == row["Subject"]][
                        "End of Primary Follow-Up Date (ig_INITLF1.DSENPFUDAT)"
                    ].values[0]
                    # if yes, find the response of the same subject with the latest event date that is before the Month 3 event date
                    filtered_df = temp_df[
                        (temp_df["Subject"] == row["Subject"])
                        & (temp_df["Event Date"] <= end_date)
                    ]
                    # Check if the filtered DataFrame is empty
                    if not filtered_df.empty:
                        # Access the last row if the DataFrame is not empty
                        temp_row = filtered_df.iloc[-1]
                        # Replace the Overall CLL Disease Response (ig_RS2.RSCLLCAT) of the subject with the Overall CLL Disease Response (ig_RS2.RSCLLCAT) of the temp_row
                        responseB_primary_M3_df.loc[
                            index, "Overall CLL Disease Response (ig_RS2.RSCLLCAT)"
                        ] = temp_row["Overall CLL Disease Response (ig_RS2.RSCLLCAT)"]
                        # Replace the CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP) of the subject with the CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP) of the temp_row
                        responseB_primary_M3_df.loc[
                            index, "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)"
                        ] = temp_row["CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)"]
        # Rename the column CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP) to OV-Based ORR
        responseB_primary_M3_df.rename(
            columns={
                "Overall CLL Disease Response (ig_RS2.RSCLLCAT)": "Overall Response",
                "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)": "Bone Marrow Response",
            },
            inplace=True,
        )
        # Merge left with the current response dataframe
        final_responseB_primary_df = pd.merge(
            final_responseB_primary_df,
            responseB_primary_M3_df,
            on="Subject",
            how="left",
        )
        # Fill NaN with "Not Reported" in column Overall Response
        final_responseB_primary_df["Overall Response"] = final_responseB_primary_df[
            "Overall Response"
        ].fillna("Not Reported")
        # Fill NaN with "Not Reported" in column Bone Marrow Response
        final_responseB_primary_df["Bone Marrow Response"] = final_responseB_primary_df[
            "Bone Marrow Response"
        ].fillna("Not Reported")

        ## Checking AE and SAE for CLL primary
        # Getting AE and SAE dataframes
        responseB_primary_AE_df = data["AE"][
            [
                "Subject",
                "Form ILB Status",
                "AE or SAE? (ig_AE2.AESEV)",
                "Event Onset (ig_AE1.AEONSET)",
            ]
        ]
        # Check responseB_primary_AE_df if the subject of responseB_primary_df is in the AE dataframe. If yes, then add 'Y' to the column 'AE' in responseB_primary_df, else add 'N'
        final_responseB_primary_df["AE"] = final_responseB_primary_df["Subject"].apply(
            lambda x: "Y" if x in responseB_primary_AE_df["Subject"].values else "N"
        )
        # Check responseB_primary_AE_df if the subject of responseB_primary_df has SAE in column 'AE or SAE? (ig_AE2.AESEV)' . If yes, then add 'Y' to the column 'SAE' in responseB_primary_df, else add 'N'
        final_responseB_primary_df["SAE"] = final_responseB_primary_df["Subject"].apply(
            lambda x: (
                "Y"
                if x
                in responseB_primary_AE_df[
                    responseB_primary_AE_df["AE or SAE? (ig_AE2.AESEV)"] == "SAE"
                ]["Subject"].values
                else "N"
            )
        )

        ## Checking Study Status for CLL primary
        # Getting Study Status dataframe from SV, column Subject, Event Label and Event Date
        responseB_primary_SV_df = data["SV"][["Subject", "Event Label", "Event Date"]]
        # Getting Study Status dataframe from DSSVLTFU, column Subject, Event Label and Event Date
        responseB_primary_DSSVLTFU_df = data["DSSVLTFU"][
            ["Subject", "Event Label", "Event Date"]
        ]
        # Getting End of Study status from EOS
        responseB_primary_EOS_df = data["EOS"][
            ["Subject", "End of Study Date (ig_EOS1.EOSDAT)"]
        ]
        # Combine DSSVLTFU with SV dataframe vertically
        responseB_primary_SV_df = pd.concat(
            [responseB_primary_SV_df, responseB_primary_DSSVLTFU_df]
        )
        # Sort the dataframe by Subject and Event Date
        responseB_primary_SV_df = responseB_primary_SV_df.sort_values(
            by=["Subject", "Event Date"]
        )
        # For each unique subject, get the last row of the dataframe
        responseB_primary_SV_df = responseB_primary_SV_df.groupby("Subject").tail(1)
        # Merge with EOS data to get End of Study Date
        responseB_primary_SV_df = pd.merge(
            responseB_primary_SV_df, responseB_primary_EOS_df, on="Subject", how="left"
        )
        # Format the End of Study Date if available
        responseB_primary_SV_df = remove_leading_zeros_from_dates(
            responseB_primary_SV_df
        )
        # Merge left with the current response dataframe
        final_responseB_primary_df = pd.merge(
            final_responseB_primary_df,
            responseB_primary_SV_df[
                ["Subject", "Event Label", "End of Study Date (ig_EOS1.EOSDAT)"]
            ],
            on="Subject",
            how="left",
        )
        # * Formatting the dataframe
        # Rename the column Event Label to Event Label (Study Status)
        final_responseB_primary_df["Event Label"] = final_responseB_primary_df[
            "Event Label"
        ].map(event_AB_dict)
        # Add End of Study Date to Event Label if available
        final_responseB_primary_df["Event Label"] = final_responseB_primary_df.apply(
            lambda row: (
                f"{row['Event Label']} (EOS:{row['End of Study Date (ig_EOS1.EOSDAT)']})"
                if row["End of Study Date (ig_EOS1.EOSDAT)"]
                else row["Event Label"]
            ),
            axis=1,
        )
        # Select the columns needed only
        final_responseB_primary_df = final_responseB_primary_df[
            [
                "Subject",
                "Overall CLL Disease Response (ig_RS2.RSCLLCAT)",
                "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)",
                "Primary Treatment Time Point (ig_RS1.RSTPT)",
                "OV-Best Response",
                "Best OV Time Point",
                "BM-Best Response",
                "Best BM Time Point",
                "Overall Response",
                "Bone Marrow Response",
                "AE",
                "SAE",
                "Event Label",
            ]
        ]
        final_responseB_primary_df = final_responseB_primary_df.replace(
            [np.nan, np.inf, -np.inf], ""
        )

    # Cohort B - CLL Retreatment
    # Filter to only Primary Treatment
    responseB_retreatment_df = responseB_df[
        responseB_df["Study Phase (ig_RS1.STUDYPHS2)"] == "Retreatment"
    ]
    # Replace value of "Unscheduled" in column Primary Treatment Time Point (ig_RS1.RSTPT) with value of "Unscheduled Primary Treatment Time Point, Specify Day #  (ig_RS1.RSTPTDY)"
    temp_mask = (
        responseB_retreatment_df["Retreatment Time Point (ig_RS1.RSTPTR)"]
        == "Unscheduled"
    )
    # Convert the column For Unscheduled Retreatment Time Point, Specify Day # (ig_RS1.UNSDAYR) to string
    responseB_retreatment_df = convert_integers_to_strings(
        responseB_retreatment_df,
        "For Unscheduled Retreatment Time Point, Specify Day # (ig_RS1.UNSDAYR)",
    )
    responseB_retreatment_df.loc[
        temp_mask, "Retreatment Time Point (ig_RS1.RSTPTR)"
    ] = responseB_retreatment_df.loc[
        temp_mask,
        "For Unscheduled Retreatment Time Point, Specify Day # (ig_RS1.UNSDAYR)",
    ].apply(
        lambda x: (
            f"Day {x}"
            if pd.notna(x) and str(x).strip().replace("-R", "").isdigit()
            else x
        )
    )
    # Remove rows with Pre-Treatment Safety Visit
    responseB_retreatment_df = responseB_retreatment_df[
        responseB_retreatment_df["Retreatment Time Point (ig_RS1.RSTPTR)"]
        != "Pre-Retreatment Safety Visit"
    ]
    # Snapshot the responseB_retreatment_df
    responseB_retreatment_df_snapshot = responseB_retreatment_df.copy()
    # check the number of subject for cohort B - CLL Retreatment
    final_subject_B_retx_count = len(responseB_retreatment_df["Subject"].unique())

    # Check if there is any subject. If yes, then proceed, else skip
    if final_subject_B_retx_count > 0:
        # Fill NaN with "Not Reported" in column Overall CLL Disease Response (ig_RS2.RSCLLCAT)
        responseB_retreatment_df["Overall CLL Disease Response (ig_RS2.RSCLLCAT)"] = (
            responseB_retreatment_df[
                "Overall CLL Disease Response (ig_RS2.RSCLLCAT)"
            ].fillna("Not Reported")
        )
        # Fill NaN with "Not Reported" in column CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)
        responseB_retreatment_df["CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)"] = (
            responseB_retreatment_df[
                "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)"
            ].fillna("Not Reported")
        )
        # Convert OV-Based CLL Disease Response and CT-Based CLL Disease Response to numeric values
        responseB_retreatment_df["OV-Score"] = responseB_retreatment_df[
            "Overall CLL Disease Response (ig_RS2.RSCLLCAT)"
        ].map(DR_CLL_OV_dict)
        responseB_retreatment_df["BM-Score"] = responseB_retreatment_df[
            "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)"
        ].map(DR_CLL_BM_dict)

        # * CURRENT RESPONSE
        # Get the indices of the rows with the maximum 'Event Date' for each 'Subject'
        idx = responseB_retreatment_df.groupby("Subject")["Event Date"].idxmax()
        # Select these rows for the current response
        responseB_retreatment_current_df = responseB_retreatment_df.loc[idx].copy()
        # Fill NaN with "Not Reported" in column Overall CLL Disease Response (ig_RS2.RSCLLCAT)
        responseB_retreatment_current_df[
            "Overall CLL Disease Response (ig_RS2.RSCLLCAT)"
        ] = responseB_retreatment_current_df[
            "Overall CLL Disease Response (ig_RS2.RSCLLCAT)"
        ].fillna("Not Reported")
        # Fill NaN with "Not Reported" in column CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)
        responseB_retreatment_current_df[
            "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)"
        ] = responseB_retreatment_current_df[
            "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)"
        ].fillna("Not Reported")

        # * BEST RESPONSE
        ## Best OV-Based CLL Disease Response primary
        # Get the indices of the rows with the minimum 'OV-Best' for each 'Subject'
        responseB_best_OV_idx = responseB_retreatment_df.groupby("Subject")[
            "OV-Score"
        ].idxmin()
        # Select these rows for the best OV-based response
        responseB_best_OV_df = responseB_retreatment_df.loc[
            responseB_best_OV_idx
        ].copy()
        # Select the columns subject and OV-Based CLL Disease Response from responseB_best_OV_df
        responseB_best_OV_df = responseB_best_OV_df[
            [
                "Subject",
                "Overall CLL Disease Response (ig_RS2.RSCLLCAT)",
                "Primary Treatment Time Point (ig_RS1.RSTPT)",
            ]
        ]
        # Rename the column OV-Based CLL Disease Response to OV-Based Response
        responseB_best_OV_df.rename(
            columns={
                "Overall CLL Disease Response (ig_RS2.RSCLLCAT)": "OV-Best Response",
                "Primary Treatment Time Point (ig_RS1.RSTPT)": "Best OV Time Point",
            },
            inplace=True,
        )
        # Merge left with the primary current response dataframe
        final_responseB_retreatment_df = pd.merge(
            responseB_retreatment_current_df,
            responseB_best_OV_df,
            on="Subject",
            how="left",
        )

        ## Best CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)
        # Get the indices of the rows with the minimum 'CT-Best' for each 'Subject'
        responseB_best_CT_idx = responseB_retreatment_df.groupby("Subject")[
            "BM-Score"
        ].idxmin()
        # Select these rows for the best CT-based response
        responseB_best_CT_df = responseB_retreatment_df.loc[responseB_best_CT_idx]
        # Select the columns subject and CT-Based CLL Disease Response from responseB_best_CT_df
        responseB_best_CT_df = responseB_best_CT_df[
            [
                "Subject",
                "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)",
                "Primary Treatment Time Point (ig_RS1.RSTPT)",
            ]
        ]
        # Rename the column CT-Based CLL Disease Response to CT-Based Response
        responseB_best_CT_df.rename(
            columns={
                "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)": "BM-Best Response",
                "Primary Treatment Time Point (ig_RS1.RSTPT)": "Best BM Time Point",
            },
            inplace=True,
        )
        # Merge left with the primary response dataframe
        final_responseB_retreatment_df = pd.merge(
            final_responseB_retreatment_df,
            responseB_best_CT_df,
            on="Subject",
            how="left",
        )

        ## * Overall CLL Disease Response at Month 3 primary
        # Filter responseB_retreatment_df to only Month 3
        responseB_retreatment_M3_df = responseB_df[
            responseB_df["Primary Treatment Time Point (ig_RS1.RSTPT)"] == "Month 3"
        ]
        # Selec the columns subject and Overall CLL Disease Response (ig_RS2.RSCLLCAT) from responseB_retreatment_M3_df
        responseB_retreatment_M3_df = responseB_retreatment_M3_df[
            [
                "Subject",
                "Overall CLL Disease Response (ig_RS2.RSCLLCAT)",
                "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)",
            ]
        ]
        # Compare responseB_retreatment_M3_df with responseB_df, and add the subjects (do it once) that are not in responseB_retreatment_M3_df to responseB_retreatment_M3_df
        responseB_retreatment_M3_df = pd.concat(
            [
                responseB_retreatment_M3_df,
                responseB_df[
                    ~responseB_df["Subject"].isin(
                        responseB_retreatment_M3_df["Subject"]
                    )
                ][["Subject"]],
            ]
        )
        # Remove duplicates
        responseB_retreatment_M3_df = responseB_retreatment_M3_df.drop_duplicates(
            subset=["Subject"]
        )
        # Copy snapshot of responseB_retreatment_df to a temporary dataframe
        temp_df = responseB_retreatment_df_snapshot
        # Sort the temporary dataframe by Subject and Event Date
        temp_df = temp_df.sort_values(by=["Subject", "Event Date"])
        # remove all the rows that have nan in Overall CLL Disease Response (ig_RS2.RSCLLCAT) and CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)
        temp_df = temp_df[
            temp_df["Overall CLL Disease Response (ig_RS2.RSCLLCAT)"].notna()
            | temp_df["CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)"].notna()
        ]
        # Create a for loop that will check the Overall CLL Disease Response (ig_RS2.RSCLLCAT) and CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP) of each subject in responseB_retreatment_M3_df
        for index, row in responseB_retreatment_M3_df.iterrows():
            # check if the Overall CLL Disease Response (ig_RS2.RSCLLCAT) of the subject is nan, and check if the CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP) of the subject is nan
            if pd.isna(
                row["Overall CLL Disease Response (ig_RS2.RSCLLCAT)"]
            ) and pd.isna(row["CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)"]):
                # if yes, check to see if the subject in in PD_Retx_df
                if row["Subject"] in PD_Retx_df["Subject"].values:
                    # get the End of Retreatment Date (ig_INITLF1.DSENRETXDAT) date of the subject in PD_Retx_df
                    end_date = PD_Retx_df[PD_Retx_df["Subject"] == row["Subject"]][
                        "End of Retreatment Date (ig_INITLF1.DSENRETXDAT)"
                    ].values[0]
                    # if yes, find the response of the same subject with the latest event date that is before the Month 3 event date
                    filtered_df = temp_df[
                        (temp_df["Subject"] == row["Subject"])
                        & (temp_df["Event Date"] <= end_date)
                    ]
                    # Check if the filtered DataFrame is empty
                    if not filtered_df.empty:
                        # Access the last row if the DataFrame is not empty
                        temp_row = filtered_df.iloc[-1]
                        # Replace the Overall CLL Disease Response (ig_RS2.RSCLLCAT) of the subject with the Overall CLL Disease Response (ig_RS2.RSCLLCAT) of the temp_row
                        responseB_retreatment_M3_df.loc[
                            index, "Overall CLL Disease Response (ig_RS2.RSCLLCAT)"
                        ] = temp_row["Overall CLL Disease Response (ig_RS2.RSCLLCAT)"]
                        # Replace the CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP) of the subject with the CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP) of the temp_row
                        responseB_retreatment_M3_df.loc[
                            index, "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)"
                        ] = temp_row["CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)"]
        # Rename the column CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP) to OV-Based ORR
        responseB_retreatment_M3_df.rename(
            columns={
                "Overall CLL Disease Response (ig_RS2.RSCLLCAT)": "Overall Response",
                "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)": "Bone Marrow Response",
            },
            inplace=True,
        )
        # Merge left with the current response dataframe
        final_responseB_retreatment_df = pd.merge(
            final_responseB_retreatment_df,
            responseB_retreatment_M3_df,
            on="Subject",
            how="left",
        )
        # Fill NaN with "Not Reported" in column Overall Response and Bone Marrow Response
        final_responseB_retreatment_df["Overall Response"] = (
            final_responseB_retreatment_df["Overall Response"].fillna("Not Reported")
        )
        final_responseB_retreatment_df["Bone Marrow Response"] = (
            final_responseB_retreatment_df["Bone Marrow Response"].fillna(
                "Not Reported"
            )
        )

        ## Checking AE and SAE for CLL primary
        # Getting AE and SAE dataframes
        responseB_retreatment_AE_df = data["AE"][
            [
                "Subject",
                "Form ILB Status",
                "AE or SAE? (ig_AE2.AESEV)",
                "Event Onset (ig_AE1.AEONSET)",
            ]
        ]
        # Check responseB_retreatment_AE_df if the subject of responseB_retreatment_df is in the AE dataframe. If yes, then add 'Y' to the column 'AE' in responseB_retreatment_df, else add 'N'
        final_responseB_retreatment_df["AE"] = final_responseB_retreatment_df[
            "Subject"
        ].apply(
            lambda x: "Y" if x in responseB_retreatment_AE_df["Subject"].values else "N"
        )
        # Check responseB_retreatment_AE_df if the subject of responseB_retreatment_df has SAE in column 'AE or SAE? (ig_AE2.AESEV)' . If yes, then add 'Y' to the column 'SAE' in responseB_retreatment_df, else add 'N'
        final_responseB_retreatment_df["SAE"] = final_responseB_retreatment_df[
            "Subject"
        ].apply(
            lambda x: (
                "Y"
                if x
                in responseB_retreatment_AE_df[
                    responseB_retreatment_AE_df["AE or SAE? (ig_AE2.AESEV)"] == "SAE"
                ]["Subject"].values
                else "N"
            )
        )

        ## Checking Study Status for CLL primary
        # Getting Study Status dataframe from SV, column Subject, Event Label and Event Date
        responseB_retreatment_SV_df = data["SV"][
            ["Subject", "Event Label", "Event Date"]
        ]
        # Getting Study Status dataframe from DSSVLTFU, column Subject, Event Label and Event Date
        responseB_retreatment_DSSVLTFU_df = data["DSSVLTFU"][
            ["Subject", "Event Label", "Event Date"]
        ]
        # Getting End of Study status from EOS
        responseB_retreatment_EOS_df = data["EOS"][
            ["Subject", "End of Study Date (ig_EOS1.EOSDAT)"]
        ]
        # Combine DSSVLTFU with SV dataframe vertically
        responseB_retreatment_SV_df = pd.concat(
            [responseB_retreatment_SV_df, responseB_retreatment_DSSVLTFU_df]
        )
        # Sort the dataframe by Subject and Event Date
        responseB_retreatment_SV_df = responseB_retreatment_SV_df.sort_values(
            by=["Subject", "Event Date"]
        )
        # For each unique subject, get the last row of the dataframe
        responseB_retreatment_SV_df = responseB_retreatment_SV_df.groupby(
            "Subject"
        ).tail(1)
        # Merge with EOS data to get End of Study Date
        responseB_retreatment_SV_df = pd.merge(
            responseB_retreatment_SV_df,
            responseB_retreatment_EOS_df,
            on="Subject",
            how="left",
        )
        # Format the End of Study Date if available
        responseB_retreatment_SV_df = remove_leading_zeros_from_dates(
            responseB_retreatment_SV_df
        )

        # Merge left with the current response dataframe
        final_responseB_retreatment_df = pd.merge(
            final_responseB_retreatment_df,
            responseB_retreatment_SV_df[
                ["Subject", "Event Label", "End of Study Date (ig_EOS1.EOSDAT)"]
            ],
            on="Subject",
            how="left",
        )

        # * Formatting the dataframe
        # Rename the column Event Label to Event Label (Study Status)
        final_responseB_retreatment_df["Event Label"] = final_responseB_retreatment_df[
            "Event Label"
        ].map(event_AB_dict)
        # Add End of Study Date to Event Label if available
        final_responseB_retreatment_df["Event Label"] = (
            final_responseB_retreatment_df.apply(
                lambda row: (
                    f"{row['Event Label']} (EOS:{row['End of Study Date (ig_EOS1.EOSDAT)']})"
                    if row["End of Study Date (ig_EOS1.EOSDAT)"]
                    else row["Event Label"]
                ),
                axis=1,
            )
        )
        # Select the columns needed only
        final_responseB_retreatment_df = final_responseB_retreatment_df[
            [
                "Subject",
                "Overall CLL Disease Response (ig_RS2.RSCLLCAT)",
                "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)",
                "Primary Treatment Time Point (ig_RS1.RSTPT)",
                "OV-Best Response",
                "Best OV Time Point",
                "BM-Best Response",
                "Best BM Time Point",
                "Overall Response",
                "Bone Marrow Response",
                "AE",
                "SAE",
                "Event Label",
            ]
        ]
        final_responseB_retreatment_df = final_responseB_retreatment_df.replace(
            [np.nan, np.inf, -np.inf], ""
        )

    # RESPONSE LISTING RICHTER'S TRANSFORMATION ONLY
    # Cohort B - RESPONSE LISTING RICHTER'S TRANSFORMATION
    # Filter to only Primary Treatment
    responseBRT_primary_df = responseBRT_df[
        responseBRT_df["Study Phase (ig_RS1.STUDYPHS2)"] == "Primary Treatment"
    ]
    # Replace value of "Unscheduled" in column Primary Treatment Time Point (ig_RS1.RSTPT) with value of "Unscheduled Primary Treatment Time Point, Specify Day #  (ig_RS1.RSTPTDY)"
    temp_mask = (
        responseBRT_primary_df["Primary Treatment Time Point (ig_RS1.RSTPT)"]
        == "Unscheduled"
    )
    # Convert the column For Unscheduled Primary Treatment Time Point, Specify Day #  (ig_RS1.RSTPTDY) to string
    responseBRT_primary_df = convert_integers_to_strings(
        responseBRT_primary_df,
        "For Unscheduled Primary Treatment Time Point, Specify Day #  (ig_RS1.RSTPTDY)",
    )
    responseBRT_primary_df.loc[
        temp_mask, "Primary Treatment Time Point (ig_RS1.RSTPT)"
    ] = responseBRT_primary_df.loc[
        temp_mask,
        "For Unscheduled Primary Treatment Time Point, Specify Day #  (ig_RS1.RSTPTDY)",
    ].apply(lambda x: f"Day {x}" if pd.notna(x) and str(x).strip().isdigit() else x)
    # Remove rows with Pre-Treatment Safety Visit
    responseBRT_primary_df = responseBRT_primary_df[
        responseBRT_primary_df["Primary Treatment Time Point (ig_RS1.RSTPT)"]
        != "Pre-Treatment Safety Visit"
    ]
    # Snapshot the responseBRT_primary_df
    responseBRT_primary_df_snapshot = responseBRT_primary_df.copy()
    # check the number of subject for cohort B - Richter's Transformation
    final_subject_BRT_prim_count = len(responseBRT_primary_df["Subject"].unique())

    # Check if there is any subject. If yes, then proceed, else skip
    if final_subject_BRT_prim_count > 0:
        # Fill NaN with "Not Reported" in column PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)
        responseBRT_primary_df[
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
        ] = responseBRT_primary_df[
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
        ].fillna("Not Reported")
        # Fill NaN with "Not Reported" in column CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)
        responseBRT_primary_df["CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"] = (
            responseBRT_primary_df[
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
            ].fillna("Not Reported")
        )
        # Convert PET-Based NHL Disease Response and CT-Based NHL Disease Response to numeric values
        responseBRT_primary_df["PET-Score"] = responseBRT_primary_df[
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
        ].map(DR_NHL_PET_dict)
        responseBRT_primary_df["CT-Score"] = responseBRT_primary_df[
            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
        ].map(DR_NHL_CT_dict)

        # * CURRENT RESPONSE
        # Get the indices of the rows with the maximum 'Event Date' for each 'Subject'
        idx = responseBRT_primary_df.groupby("Subject")["Event Date"].idxmax()
        # Select these rows for the current response
        responseBRT_primary_current_df = responseBRT_primary_df.loc[idx].copy()
        # Fill NaN with "Not Reported" in column PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)
        responseBRT_primary_current_df[
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
        ] = responseBRT_primary_current_df[
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
        ].fillna("Not Reported")
        # Fill NaN with "Not Reported" in column CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)
        responseBRT_primary_current_df[
            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
        ] = responseBRT_primary_current_df[
            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
        ].fillna("Not Reported")

        # * BEST RESPONSE
        ## Best PET-Based NHL Disease Response primary
        # Get the indices of the rows with the minimum 'PET-Best' for each 'Subject'
        responseBRT_best_PET_idx = responseBRT_primary_df.groupby("Subject")[
            "PET-Score"
        ].idxmin()
        # Select these rows for the best PET-based response
        responseBRT_best_PET_df = responseBRT_primary_df.loc[
            responseBRT_best_PET_idx
        ].copy()
        # Select the columns subject and PET-Based NHL Disease Response from responseBRT_best_PET_df
        responseBRT_best_PET_df = responseBRT_best_PET_df[
            [
                "Subject",
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)",
                "Primary Treatment Time Point (ig_RS1.RSTPT)",
            ]
        ]
        # Rename the column PET-Based NHL Disease Response to PET-Based Response
        responseBRT_best_PET_df.rename(
            columns={
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)": "PET-Based Response",
                "Primary Treatment Time Point (ig_RS1.RSTPT)": "Best PET Time Point",
            },
            inplace=True,
        )
        # Merge left with the primary current response dataframe
        final_responseBRT_primary_df = pd.merge(
            responseBRT_primary_current_df,
            responseBRT_best_PET_df,
            on="Subject",
            how="left",
        )

        ## Best CT-Based NHL Disease Response primary
        # Get the indices of the rows with the minimum 'CT-Best' for each 'Subject'
        responseBRT_best_CT_idx = responseBRT_primary_df.groupby("Subject")[
            "CT-Score"
        ].idxmin()
        # Select these rows for the best CT-based response
        responseBRT_best_CT_df = responseBRT_primary_df.loc[responseBRT_best_CT_idx]
        # Select the columns subject and CT-Based NHL Disease Response from responseBRT_best_CT_df
        responseBRT_best_CT_df = responseBRT_best_CT_df[
            [
                "Subject",
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)",
                "Primary Treatment Time Point (ig_RS1.RSTPT)",
            ]
        ]
        # Rename the column CT-Based NHL Disease Response to CT-Based Response
        responseBRT_best_CT_df.rename(
            columns={
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)": "CT-Based Response",
                "Primary Treatment Time Point (ig_RS1.RSTPT)": "Best CT Time Point",
            },
            inplace=True,
        )
        # Merge left with the primary response dataframe
        final_responseBRT_primary_df = pd.merge(
            final_responseBRT_primary_df,
            responseBRT_best_CT_df,
            on="Subject",
            how="left",
        )

        ## Overall NHL Disease Response at Month 3 primary
        # Filter responseBRT_primary_df to only Month 3
        responseBRT_primary_M3_df = responseBRT_df[
            responseBRT_df["Primary Treatment Time Point (ig_RS1.RSTPT)"] == "Month 3"
        ]
        # Selec the columns subject and PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) from responseBRT_primary_M3_df
        responseBRT_primary_M3_df = responseBRT_primary_M3_df[
            [
                "Subject",
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)",
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)",
            ]
        ]
        # Compare responseBRT_primary_M3_df with responseBRT_df, and add the subjects (do it once) that are not in responseBRT_primary_M3_df to responseBRT_primary_M3_df
        responseBRT_primary_M3_df = pd.concat(
            [
                responseBRT_primary_M3_df,
                responseBRT_df[
                    ~responseBRT_df["Subject"].isin(
                        responseBRT_primary_M3_df["Subject"]
                    )
                ][["Subject"]],
            ]
        )
        # Remove duplicates
        responseBRT_primary_M3_df = responseBRT_primary_M3_df.drop_duplicates(
            subset=["Subject"]
        )

        # Copy snapshot of responseBRT_primary_df to a temporary dataframe
        temp_df = responseBRT_primary_df_snapshot
        # Sort the temporary dataframe by Subject and Event Date
        temp_df = temp_df.sort_values(by=["Subject", "Event Date"])
        # remove all the rows that have nan in PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) and CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)
        temp_df = temp_df[
            temp_df["PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"].notna()
            | temp_df["CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"].notna()
        ]
        # Create a for loop that will check the PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) and CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT) of each subject in responseBRT_primary_M3_df
        for index, row in responseBRT_primary_M3_df.iterrows():
            # check if the PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) of the subject is nan, and check if the CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT) of the subject is nan
            if pd.isna(
                row["PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"]
            ) and pd.isna(row["CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"]):
                # if yes, check to see if the subject in in PD_df
                if row["Subject"] in PD_df["Subject"].values:
                    # get the End of Primary Follow-Up Date (ig_INITLF1.DSENPFUDAT) date of the subject in PD_df
                    end_date = PD_df[PD_df["Subject"] == row["Subject"]][
                        "End of Primary Follow-Up Date (ig_INITLF1.DSENPFUDAT)"
                    ].values[0]
                    # if yes, find the response of the same subject with the latest event date that is before the Month 3 event date
                    filtered_df = temp_df[
                        (temp_df["Subject"] == row["Subject"])
                        & (temp_df["Event Date"] <= end_date)
                    ]
                    # Check if the filtered DataFrame is empty
                    if not filtered_df.empty:
                        # Access the last row if the DataFrame is not empty
                        temp_row = filtered_df.iloc[-1]
                        # Replace the PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) of the subject with the PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) of the temp_row
                        responseBRT_primary_M3_df.loc[
                            index, "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
                        ] = temp_row[
                            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
                        ]
                        # Replace the CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT) of the subject with the CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT) of the temp_row
                        responseBRT_primary_M3_df.loc[
                            index, "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
                        ] = temp_row[
                            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
                        ]
                # check if the subject is in Initiation of REtx before month 3
                elif row["Subject"] in DSINITRT_df["Subject"].values:
                    # get the End of Primary Follow-Up Date (ig_INITLF1.DSENPFUDAT) date of the subject in DSINITRT_df
                    end_date = DSINITRT_df[DSINITRT_df["Subject"] == row["Subject"]][
                        "End of Primary Follow-Up Date (ig_DSINITRT1.DSRENPFUDAT)"
                    ].values[0]
                    # if yes, find the response of the same subject with the latest event date that is before the Month 3 event date
                    filtered_df = temp_df[
                        (temp_df["Subject"] == row["Subject"])
                        & (temp_df["Event Date"] <= end_date)
                    ]
                    # Check if the filtered DataFrame is empty
                    if not filtered_df.empty:
                        # Access the last row if the DataFrame is not empty
                        temp_row = filtered_df.iloc[-1]
                        # Replace the PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) of the subject with the PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) of the temp_row
                        responseBRT_primary_M3_df.loc[
                            index, "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
                        ] = temp_row[
                            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
                        ]
                        # Replace the CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT) of the subject with the CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT) of the temp_row
                        responseBRT_primary_M3_df.loc[
                            index, "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
                        ] = temp_row[
                            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
                        ]
        # Rename the column PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) to PET-Based ORR
        responseBRT_primary_M3_df.rename(
            columns={
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)": "PET-Based ORR",
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)": "CT-Based ORR",
            },
            inplace=True,
        )
        # Merge left with the current response dataframe
        final_responseBRT_primary_df = pd.merge(
            final_responseBRT_primary_df,
            responseBRT_primary_M3_df,
            on="Subject",
            how="left",
        )
        # Fill NaN with "Not Reported" in column PET-Based ORR and CT-Based ORR
        final_responseBRT_primary_df["PET-Based ORR"] = final_responseBRT_primary_df[
            "PET-Based ORR"
        ].fillna("Not Reported")
        final_responseBRT_primary_df["CT-Based ORR"] = final_responseBRT_primary_df[
            "CT-Based ORR"
        ].fillna("Not Reported")

        ## Checking AE and SAE for NHL primary
        # Getting AE and SAE dataframes
        responseBRT_primary_AE_df = data["AE"][
            [
                "Subject",
                "Form ILB Status",
                "AE or SAE? (ig_AE2.AESEV)",
                "Event Onset (ig_AE1.AEONSET)",
            ]
        ]
        # Check responseBRT_primary_AE_df if the subject of responseBRT_primary_df is in the AE dataframe. If yes, then add 'Y' to the column 'AE' in responseBRT_primary_df, else add 'N'
        final_responseBRT_primary_df["AE"] = final_responseBRT_primary_df[
            "Subject"
        ].apply(
            lambda x: "Y" if x in responseBRT_primary_AE_df["Subject"].values else "N"
        )
        # Check responseBRT_primary_AE_df if the subject of responseBRT_primary_df has SAE in column 'AE or SAE? (ig_AE2.AESEV)' . If yes, then add 'Y' to the column 'SAE' in responseBRT_primary_df, else add 'N'
        final_responseBRT_primary_df["SAE"] = final_responseBRT_primary_df[
            "Subject"
        ].apply(
            lambda x: (
                "Y"
                if x
                in responseBRT_primary_AE_df[
                    responseBRT_primary_AE_df["AE or SAE? (ig_AE2.AESEV)"] == "SAE"
                ]["Subject"].values
                else "N"
            )
        )

        ## Checking Study Status for NHL primary
        # Getting Study Status dataframe from SV, column Subject, Event Label and Event Date
        responseBRT_primary_SV_df = data["SV"][["Subject", "Event Label", "Event Date"]]
        # Getting Study Status dataframe from DSSVLTFU, column Subject, Event Label and Event Date
        responseBRT_primary_DSSVLTFU_df = data["DSSVLTFU"][
            ["Subject", "Event Label", "Event Date"]
        ]
        # Getting End of Study status from EOS
        responseBRT_primary_EOS_df = data["EOS"][
            ["Subject", "End of Study Date (ig_EOS1.EOSDAT)"]
        ]
        # Combine DSSVLTFU with SV dataframe vertically
        responseBRT_primary_SV_df = pd.concat(
            [responseBRT_primary_SV_df, responseBRT_primary_DSSVLTFU_df]
        )
        # Sort the dataframe by Subject and Event Date
        responseBRT_primary_SV_df = responseBRT_primary_SV_df.sort_values(
            by=["Subject", "Event Date"]
        )
        # For each unique subject, get the last row of the dataframe
        responseBRT_primary_SV_df = responseBRT_primary_SV_df.groupby("Subject").tail(1)
        # Merge with EOS data to get End of Study Date
        responseBRT_primary_SV_df = pd.merge(
            responseBRT_primary_SV_df,
            responseBRT_primary_EOS_df,
            on="Subject",
            how="left",
        )
        # Format the End of Study Date if available
        responseBRT_primary_SV_df = remove_leading_zeros_from_dates(
            responseBRT_primary_SV_df
        )
        # Merge left with the current response dataframe
        final_responseBRT_primary_df = pd.merge(
            final_responseBRT_primary_df,
            responseBRT_primary_SV_df[
                ["Subject", "Event Label", "End of Study Date (ig_EOS1.EOSDAT)"]
            ],
            on="Subject",
            how="left",
        )
        # Rename the column Event Label to Event Label (Study Status)
        final_responseBRT_primary_df["Event Label"] = final_responseBRT_primary_df[
            "Event Label"
        ].map(event_AB_dict)
        # Add End of Study Date to Event Label if available
        final_responseBRT_primary_df["Event Label"] = (
            final_responseBRT_primary_df.apply(
                lambda row: (
                    f"{row['Event Label']} (EOS:{row['End of Study Date (ig_EOS1.EOSDAT)']})"
                    if row["End of Study Date (ig_EOS1.EOSDAT)"]
                    else row["Event Label"]
                ),
                axis=1,
            )
        )
        # Select the columns needed only
        final_responseBRT_primary_df = final_responseBRT_primary_df[
            [
                "Subject",
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)",
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)",
                "Primary Treatment Time Point (ig_RS1.RSTPT)",
                "PET-Based Response",
                "Best PET Time Point",
                "CT-Based Response",
                "Best CT Time Point",
                "PET-Based ORR",
                "CT-Based ORR",
                "AE",
                "SAE",
                "Event Label",
            ]
        ]
        final_responseBRT_primary_df = final_responseBRT_primary_df.replace(
            [np.nan, np.inf, -np.inf], ""
        )
        # * Formatting the dataframe

    # Cohort B - RT Retreatment
    # Filter to only Primary Treatment
    responseBRT_retreatment_df = responseBRT_df[
        responseBRT_df["Study Phase (ig_RS1.STUDYPHS2)"] == "Retreatment"
    ]
    # Replace value of "Unscheduled" in column Retreatment Time Point (ig_RS1.RSTPT) with value of "Unscheduled Retreatment  Treatment Time Point, Specify Day #  (ig_RS1.RSTPTDY)"
    temp_mask = (
        responseBRT_retreatment_df["Retreatment Time Point (ig_RS1.RSTPTR)"]
        == "Unscheduled"
    )
    # Convert the column For Unscheduled Retreatment Time Point, Specify Day #  (ig_RS1.UNSDAYR) to string
    responseBRT_retreatment_df = convert_integers_to_strings(
        responseBRT_retreatment_df,
        "For Unscheduled Retreatment Time Point, Specify Day # (ig_RS1.UNSDAYR)",
    )
    responseBRT_retreatment_df.loc[
        temp_mask, "Retreatment Time Point (ig_RS1.RSTPTR)"
    ] = responseBRT_retreatment_df.loc[
        temp_mask,
        "For Unscheduled Retreatment Time Point, Specify Day # (ig_RS1.UNSDAYR)",
    ].apply(
        lambda x: (
            f"Day {x}"
            if pd.notna(x) and str(x).strip().replace("-R", "").isdigit()
            else x
        )
    )
    # Remove rows with Pre-Treatment Safety Visit
    responseBRT_retreatment_df = responseBRT_retreatment_df[
        responseBRT_retreatment_df["Retreatment Time Point (ig_RS1.RSTPTR)"]
        != "Pre-Retreatment Safety Visit"
    ]
    # Snapshot the responseBRT_retreatment_df
    responseBRT_retreatment_df_snapshot = responseBRT_retreatment_df.copy()
    # check the number of subject for cohort B - CLL Retreatment
    final_subject_BRT_retx_count = len(responseBRT_retreatment_df["Subject"].unique())

    # Check if there is any subject. If yes, then proceed, else skip
    if final_subject_BRT_retx_count > 0:
        # Fill NaN with "Not Reported" in column PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)
        responseBRT_retreatment_df[
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
        ] = responseBRT_retreatment_df[
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
        ].fillna("Not Reported")
        # Fill NaN with "Not Reported" in column CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)
        responseBRT_retreatment_df[
            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
        ] = responseBRT_retreatment_df[
            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
        ].fillna("Not Reported")
        # Convert PET-Based NHL Disease Response and CT-Based NHL Disease Response to numeric values
        responseBRT_retreatment_df["PET-Score"] = responseBRT_retreatment_df[
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
        ].map(DR_NHL_PET_dict)
        responseBRT_retreatment_df["CT-Score"] = responseBRT_retreatment_df[
            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
        ].map(DR_NHL_CT_dict)

        # * CURRENT RESPONSE
        # Get the indices of the rows with the maximum 'Event Date' for each 'Subject'
        idx = responseBRT_retreatment_df.groupby("Subject")["Event Date"].idxmax()
        # Select these rows for the current response
        responseBRT_retreatment_current_df = responseBRT_retreatment_df.loc[idx].copy()
        # Fill NaN with "Not Reported" in column PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)
        responseBRT_retreatment_current_df[
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
        ] = responseBRT_retreatment_current_df[
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
        ].fillna("Not Reported")
        # Fill NaN with "Not Reported" in column CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)
        responseBRT_retreatment_current_df[
            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
        ] = responseBRT_retreatment_current_df[
            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
        ].fillna("Not Reported")

        # * BEST RESPONSE
        ## Best PET-Based NHL Disease Response primary
        # Get the indices of the rows with the minimum 'PET-Best' for each 'Subject'
        responseBRT_best_PET_idx = responseBRT_retreatment_df.groupby("Subject")[
            "PET-Score"
        ].idxmin()
        # Select these rows for the best PET-based response
        responseBRT_best_PET_df = responseBRT_retreatment_df.loc[
            responseBRT_best_PET_idx
        ].copy()
        # Select the columns subject and PET-Based NHL Disease Response from responseBRT_best_PET_df
        responseBRT_best_PET_df = responseBRT_best_PET_df[
            [
                "Subject",
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)",
                "Retreatment Time Point (ig_RS1.RSTPTR)",
            ]
        ]
        # Rename the column PET-Based NHL Disease Response to PET-Based Response
        responseBRT_best_PET_df.rename(
            columns={
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)": "PET-Based Response",
                "Retreatment Time Point (ig_RS1.RSTPTR)": "Best PET Time Point",
            },
            inplace=True,
        )
        # Fill NaN with "Not Reported" in column PET-Based Response
        responseBRT_best_PET_df["PET-Based Response"] = responseBRT_best_PET_df[
            "PET-Based Response"
        ].fillna("Not Reported")
        # Merge left with the primary current response dataframe
        final_responseBRT_retreatment_df = pd.merge(
            responseBRT_retreatment_current_df,
            responseBRT_best_PET_df,
            on="Subject",
            how="left",
        )

        ## Best CT-Based NHL Disease Response primary
        # Get the indices of the rows with the minimum 'CT-Best' for each 'Subject'
        responseBRT_best_CT_idx = responseBRT_retreatment_df.groupby("Subject")[
            "CT-Score"
        ].idxmin()
        # Select these rows for the best CT-based response
        responseBRT_best_CT_df = responseBRT_retreatment_df.loc[responseBRT_best_CT_idx]
        # Select the columns subject and CT-Based NHL Disease Response from responseBRT_best_CT_df
        responseBRT_best_CT_df = responseBRT_best_CT_df[
            [
                "Subject",
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)",
                "Retreatment Time Point (ig_RS1.RSTPTR)",
            ]
        ]
        # Rename the column CT-Based NHL Disease Response to CT-Based Response
        responseBRT_best_CT_df.rename(
            columns={
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)": "CT-Based Response",
                "Retreatment Time Point (ig_RS1.RSTPTR)": "Best CT Time Point",
            },
            inplace=True,
        )
        # Fill NaN with "Not Reported" in column CT-Based Response
        responseBRT_best_CT_df["CT-Based Response"] = responseBRT_best_CT_df[
            "CT-Based Response"
        ].fillna("Not Reported")
        # Merge left with the primary response dataframe
        final_responseBRT_retreatment_df = pd.merge(
            final_responseBRT_retreatment_df,
            responseBRT_best_CT_df,
            on="Subject",
            how="left",
        )

        ## * Overall NHL Disease Response at Month 3 R
        # Filter responseBRT_retreatment_df to only Month 3
        responseBRT_retreatment_M3_df = responseBRT_df[
            responseBRT_df["Retreatment Time Point (ig_RS1.RSTPTR)"] == "Month 3"
        ]
        # Selec the columns subject and PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) from responseBRT_retreatment_M3_df
        responseBRT_retreatment_M3_df = responseBRT_retreatment_M3_df[
            [
                "Subject",
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)",
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)",
            ]
        ]
        # Compare responseBRT_retreatment_M3_df with responseBRT_df, and add the subjects (do it once) that are not in responseBRT_retreatment_M3_df to responseBRT_retreatment_M3_df
        responseBRT_retreatment_M3_df = pd.concat(
            [
                responseBRT_retreatment_M3_df,
                responseBRT_df[
                    ~responseBRT_df["Subject"].isin(
                        responseBRT_retreatment_M3_df["Subject"]
                    )
                ][["Subject"]],
            ]
        )
        # Remove duplicates
        responseBRT_retreatment_M3_df = responseBRT_retreatment_M3_df.drop_duplicates(
            subset=["Subject"]
        )
        # Copy snapshot of responseBRT_retreatment_df to a temporary dataframe
        temp_df = responseBRT_retreatment_df_snapshot
        # Sort the temporary dataframe by Subject and Event Date
        temp_df = temp_df.sort_values(by=["Subject", "Event Date"])
        # remove all the rows that have nan in PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) and CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)
        temp_df = temp_df[
            temp_df["PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"].notna()
            | temp_df["CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"].notna()
        ]
        # Create a for loop that will check the PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) and CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT) of each subject in responseBRT_retreatment_M3_df
        for index, row in responseBRT_retreatment_M3_df.iterrows():
            # check if the PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) of the subject is nan, and check if the CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT) of the subject is nan
            if pd.isna(
                row["PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"]
            ) and pd.isna(row["CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"]):
                # if yes, check to see if the subject in in PD_Retx_df
                if row["Subject"] in PD_Retx_df["Subject"].values:
                    # get the End of Retreatment Date (ig_INITLF1.DSENRETXDAT) date of the subject in PD_Retx_df
                    end_date = PD_Retx_df[PD_Retx_df["Subject"] == row["Subject"]][
                        "End of Retreatment Date (ig_INITLF1.DSENRETXDAT)"
                    ].values[0]
                    # if yes, find the response of the same subject with the latest event date that is before the Month 3 event date
                    filtered_df = temp_df[
                        (temp_df["Subject"] == row["Subject"])
                        & (temp_df["Event Date"] <= end_date)
                    ]
                    # Check if the filtered DataFrame is empty
                    if not filtered_df.empty:
                        # Access the last row if the DataFrame is not empty
                        temp_row = filtered_df.iloc[-1]
                        # Replace the PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) of the subject with the PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) of the temp_row
                        responseBRT_retreatment_M3_df.loc[
                            index, "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
                        ] = temp_row[
                            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)"
                        ]
                        # Replace the CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT) of the subject with the CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT) of the temp_row
                        responseBRT_retreatment_M3_df.loc[
                            index, "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
                        ] = temp_row[
                            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)"
                        ]
        # Rename the column PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT) to PET-Based ORR
        responseBRT_retreatment_M3_df.rename(
            columns={
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)": "PET-Based ORR",
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)": "CT-Based ORR",
            },
            inplace=True,
        )
        # Merge left with the current response dataframe
        final_responseBRT_retreatment_df = pd.merge(
            final_responseBRT_retreatment_df,
            responseBRT_retreatment_M3_df,
            on="Subject",
            how="left",
        )
        final_responseBRT_retreatment_df["PET-Based ORR"] = (
            final_responseBRT_retreatment_df["PET-Based ORR"].fillna("Not Reported")
        )
        # Fill NaN with "Not Reported" in column CT-Based ORR
        final_responseBRT_retreatment_df["CT-Based ORR"] = (
            final_responseBRT_retreatment_df["CT-Based ORR"].fillna("Not Reported")
        )

        ## Checking AE and SAE for NHL primary
        # Getting AE and SAE dataframes
        responseBRT_retreatment_AE_df = data["AE"][
            [
                "Subject",
                "Form ILB Status",
                "AE or SAE? (ig_AE2.AESEV)",
                "Event Onset (ig_AE1.AEONSET)",
            ]
        ]
        # Check responseBRT_retreatment_AE_df if the subject of responseBRT_retreatment_df is in the AE dataframe. If yes, then add 'Y' to the column 'AE' in responseBRT_retreatment_df, else add 'N'
        final_responseBRT_retreatment_df["AE"] = final_responseBRT_retreatment_df[
            "Subject"
        ].apply(
            lambda x: (
                "Y" if x in responseBRT_retreatment_AE_df["Subject"].values else "N"
            )
        )
        # Check responseBRT_retreatment_AE_df if the subject of responseBRT_retreatment_df has SAE in column 'AE or SAE? (ig_AE2.AESEV)' . If yes, then add 'Y' to the column 'SAE' in responseBRT_retreatment_df, else add 'N'
        final_responseBRT_retreatment_df["SAE"] = final_responseBRT_retreatment_df[
            "Subject"
        ].apply(
            lambda x: (
                "Y"
                if x
                in responseBRT_retreatment_AE_df[
                    responseBRT_retreatment_AE_df["AE or SAE? (ig_AE2.AESEV)"] == "SAE"
                ]["Subject"].values
                else "N"
            )
        )

        ## Checking Study Status for NHL primary
        # Getting Study Status dataframe from SV, column Subject, Event Label and Event Date
        responseBRT_retreatment_SV_df = data["SV"][
            ["Subject", "Event Label", "Event Date"]
        ]
        # Getting Study Status dataframe from DSSVLTFU, column Subject, Event Label and Event Date
        responseBRT_retreatment_DSSVLTFU_df = data["DSSVLTFU"][
            ["Subject", "Event Label", "Event Date"]
        ]
        # Getting End of Study status from EOS
        responseBRT_retreatment_EOS_df = data["EOS"][
            ["Subject", "End of Study Date (ig_EOS1.EOSDAT)"]
        ]
        # Combine DSSVLTFU with SV dataframe vertically
        responseBRT_retreatment_SV_df = pd.concat(
            [responseBRT_retreatment_SV_df, responseBRT_retreatment_DSSVLTFU_df]
        )
        # Sort the dataframe by Subject and Event Date
        responseBRT_retreatment_SV_df = responseBRT_retreatment_SV_df.sort_values(
            by=["Subject", "Event Date"]
        )
        # For each unique subject, get the last row of the dataframe
        responseBRT_retreatment_SV_df = responseBRT_retreatment_SV_df.groupby(
            "Subject"
        ).tail(1)
        # Merge with EOS data to get End of Study Date
        responseBRT_retreatment_SV_df = pd.merge(
            responseBRT_retreatment_SV_df,
            responseBRT_retreatment_EOS_df,
            on="Subject",
            how="left",
        )
        # Format the End of Study Date if available
        responseBRT_retreatment_SV_df = remove_leading_zeros_from_dates(
            responseBRT_retreatment_SV_df
        )

        # Merge left with the current response dataframe
        final_responseBRT_retreatment_df = pd.merge(
            final_responseBRT_retreatment_df,
            responseBRT_retreatment_SV_df[
                ["Subject", "Event Label", "End of Study Date (ig_EOS1.EOSDAT)"]
            ],
            on="Subject",
            how="left",
        )

        # * Formatting the dataframe
        # Rename the column Event Label to Event Label (Study Status)
        final_responseBRT_retreatment_df["Event Label"] = (
            final_responseBRT_retreatment_df["Event Label"].map(event_AB_dict)
        )
        # Add End of Study Date to Event Label if available
        final_responseBRT_retreatment_df["Event Label"] = (
            final_responseBRT_retreatment_df.apply(
                lambda row: (
                    f"{row['Event Label']} (EOS:{row['End of Study Date (ig_EOS1.EOSDAT)']})"
                    if row["End of Study Date (ig_EOS1.EOSDAT)"]
                    else row["Event Label"]
                ),
                axis=1,
            )
        )
        # Select the columns needed only
        final_responseBRT_retreatment_df = final_responseBRT_retreatment_df[
            [
                "Subject",
                "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)",
                "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)",
                "Retreatment Time Point (ig_RS1.RSTPTR)",
                "PET-Based Response",
                "Best PET Time Point",
                "CT-Based Response",
                "Best CT Time Point",
                "PET-Based ORR",
                "CT-Based ORR",
                "AE",
                "SAE",
                "Event Label",
            ]
        ]
        final_responseBRT_retreatment_df = final_responseBRT_retreatment_df.replace(
            [np.nan, np.inf, -np.inf], ""
        )

    # RESPONSE LISTING ALL ONLY
    # Response data dataframe for NHL only
    responseC_df = data["RSALL"][
        [
            "Subject",
            "Event Date",
            "Study Phase (ig_RSALL1.STUDYPHS2)",
            "Primary Treatment Time Point (ig_RSALL1.RSALLTPT)",
            "For Unscheduled Primary Treatment Time Point, Specify Day # (ig_RSALL1.UNSDAY)",
            "Retreatment Time Point (ig_RSALL1.RSALLTPTR)",
            "For Unscheduled Retreatment Time Point, Specify Day # (ig_RSALL1.UNSDAYR)",
            "Overall Disease Response (ig_RSALL2.RSALLCAT)",
            "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)",
        ]
    ].copy()
    responseC_df = responseC_df.sort_values(by=["Subject", "Event Date"])
    # Replace Unknown/Not Assessed with Not Reported in all columns
    responseC_df = responseC_df.replace("Unknown/Not Assessed", "Not Reported")
    # Replace Not Assessed with Not Reported in all columns
    responseC_df = responseC_df.replace("Not Assessed", "Not Reported")

    # Cohort C - ALL Primary
    # Filter to only Primary Treatment
    responseC_primary_df = responseC_df[
        responseC_df["Study Phase (ig_RSALL1.STUDYPHS2)"] == "Primary Treatment"
    ]
    # Replace value of "Unscheduled" in column Primary Treatment Time Point (ig_RS1.RSTPT) with value of "Unscheduled Primary Treatment Time Point, Specify Day #  (ig_RS1.RSTPTDY)"
    temp_mask = (
        responseC_primary_df["Primary Treatment Time Point (ig_RSALL1.RSALLTPT)"]
        == "Unscheduled"
    )
    # Convert the column For Unscheduled Primary Treatment Time Point, Specify Day #  (ig_RSALL1.UNSDAY) to string
    responseC_primary_df = convert_integers_to_strings(
        responseC_primary_df,
        "For Unscheduled Primary Treatment Time Point, Specify Day # (ig_RSALL1.UNSDAY)",
    )
    responseC_primary_df.loc[
        temp_mask, "Primary Treatment Time Point (ig_RSALL1.RSALLTPT)"
    ] = responseC_primary_df.loc[
        temp_mask,
        "For Unscheduled Primary Treatment Time Point, Specify Day # (ig_RSALL1.UNSDAY)",
    ].apply(lambda x: f"Day {x}" if pd.notna(x) and str(x).strip().isdigit() else x)
    # Remove rows with Pre-Treatment Safety Visit
    responseC_primary_df = responseC_primary_df[
        responseC_primary_df["Primary Treatment Time Point (ig_RSALL1.RSALLTPT)"]
        != "Pre-Treatment Safety Visit"
    ]
    # Remove rows with Post-Lymphodepleting Chemotherapy
    responseC_primary_df = responseC_primary_df[
        responseC_primary_df["Primary Treatment Time Point (ig_RSALL1.RSALLTPT)"]
        != "Post-Lymphodepleting Chemotherapy"
    ]
    # replace all rows with Extramedullary Disease Without Bone Marrow Involvement to Not Applicable
    responseC_primary_df["Overall Disease Response (ig_RSALL2.RSALLCAT)"] = (
        responseC_primary_df["Overall Disease Response (ig_RSALL2.RSALLCAT)"].replace(
            "Extramedullary Disease Without Bone Marrow Involvement", "Not Applicable"
        )
    )

    # Snapshot the responseC_primary_df
    responseC_primary_df_snapshot = responseC_primary_df.copy()
    # check the number of subject for cohort C - ALL Primary
    final_subject_C_prim_count = len(responseC_primary_df["Subject"].unique())

    # Check if there is any subject. If yes, then proceed, else skip
    if final_subject_C_prim_count > 0:
        # Fill NaN with "Not Applicable" in column Overall Disease Response (ig_RSALL2.RSALLCAT)
        responseC_primary_df["Overall Disease Response (ig_RSALL2.RSALLCAT)"] = (
            responseC_primary_df[
                "Overall Disease Response (ig_RSALL2.RSALLCAT)"
            ].fillna("Not Applicable")
        )
        # Fill NaN with "Not Applicable" in column Radiographic Tumor Response for Extramedullary Disease (ig_RSALL2.RADTURESEXDS)
        responseC_primary_df[
            "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)"
        ] = responseC_primary_df[
            "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)"
        ].fillna("Not Applicable")
        # Convert PET-Based NHL Disease Response and CT-Based NHL Disease Response to numeric values
        responseC_primary_df["OV-Score"] = responseC_primary_df[
            "Overall Disease Response (ig_RSALL2.RSALLCAT)"
        ].map(DR_ALL_OV_dict)
        responseC_primary_df["ED-Score"] = responseC_primary_df[
            "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)"
        ].map(DR_ALL_ED_dict)

        # * CURRENT RESPONSE
        # Get the indices of the rows with the maximum 'Event Date' for each 'Subject'
        idx = responseC_primary_df.groupby("Subject")["Event Date"].idxmax()
        # Select these rows for the current response
        responseC_primary_current_df = responseC_primary_df.loc[idx].copy()
        # Fill NaN with "Not Applicable" in column PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)
        responseC_primary_current_df[
            "Overall Disease Response (ig_RSALL2.RSALLCAT)"
        ] = responseC_primary_current_df[
            "Overall Disease Response (ig_RSALL2.RSALLCAT)"
        ].fillna("Not Applicable")
        # Fill NaN with "Not Applicable" in column CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)
        responseC_primary_current_df[
            "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)"
        ] = responseC_primary_current_df[
            "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)"
        ].fillna("Not Applicable")
        # rename the column Overall Disease Response (ig_RSALL2.RSALLCAT) to Current Response
        responseC_primary_current_df.rename(
            columns={
                "Overall Disease Response (ig_RSALL2.RSALLCAT)": "Current Overall Response",
                "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)": "Current ED Response",
                "Primary Treatment Time Point (ig_RSALL1.RSALLTPT)": "Current Response Time Point",
            },
            inplace=True,
        )

        # * BEST RESPONSE
        ## Best OV ALL Disease Response primary
        # Get the indices of the rows with the minimum 'OV-Score' for each 'Subject'
        responseC_best_OV_idx = responseC_primary_df.groupby("Subject")[
            "OV-Score"
        ].idxmin()
        # Select these rows for the best OV response
        responseC_best_OV_df = responseC_primary_df.loc[responseC_best_OV_idx].copy()
        # Select the columns subject and OV-Based NHL Disease Response from responseC_best_OV_df
        responseC_best_OV_df = responseC_best_OV_df[
            [
                "Subject",
                "Overall Disease Response (ig_RSALL2.RSALLCAT)",
                "Primary Treatment Time Point (ig_RSALL1.RSALLTPT)",
            ]
        ]
        # Rename the column OV-Based NHL Disease Response to OV-Based Response
        responseC_best_OV_df.rename(
            columns={
                "Overall Disease Response (ig_RSALL2.RSALLCAT)": "Best Overall Response",
                "Primary Treatment Time Point (ig_RSALL1.RSALLTPT)": "Best Overall Response Time Point",
            },
            inplace=True,
        )
        # Replace Nan with Not Applicable
        responseC_best_OV_df["Best Overall Response"] = responseC_best_OV_df[
            "Best Overall Response"
        ].fillna("Not Applicable")
        # Merge left with the primary current response dataframe
        final_response_ALL_primary_df = pd.merge(
            responseC_primary_current_df, responseC_best_OV_df, on="Subject", how="left"
        )

        ## Best ED ALL Disease Response primary
        # Get the indices of the rows with the minimum 'ED-Score' for each 'Subject'
        responseC_best_ED_idx = responseC_primary_df.groupby("Subject")[
            "ED-Score"
        ].idxmin()
        # Select these rows for the best CT-based response
        responseC_best_ED_df = responseC_primary_df.loc[responseC_best_ED_idx]
        # Select the columns subject and CT-Based NHL Disease Response from responseC_best_CT_df
        responseC_best_ED_df = responseC_best_ED_df[
            [
                "Subject",
                "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)",
                "Primary Treatment Time Point (ig_RSALL1.RSALLTPT)",
            ]
        ]
        # Rename the column CT-Based NHL Disease Response to CT-Based Response
        responseC_best_ED_df.rename(
            columns={
                "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)": "Best ED Response",
                "Primary Treatment Time Point (ig_RSALL1.RSALLTPT)": "Best ED Time Point",
            },
            inplace=True,
        )
        # Replace Nan with Not Applicable
        responseC_best_ED_df["Best ED Response"] = responseC_best_ED_df[
            "Best ED Response"
        ].fillna("Not Applicable")
        # Merge left with the primary response dataframe
        final_response_ALL_primary_df = pd.merge(
            final_response_ALL_primary_df,
            responseC_best_ED_df,
            on="Subject",
            how="left",
        )

        ## * Overall ALL Disease Response at Day 28 primary
        # Filter responseC_primary_df to only Month 3
        responseC_primary_M3_df = responseC_df[
            responseC_df["Primary Treatment Time Point (ig_RSALL1.RSALLTPT)"]
            == "Day 28"
        ]
        # Selec the columns subject and OV, ED from responseC_primary_M3_df
        responseC_primary_M3_df = responseC_primary_M3_df[
            [
                "Subject",
                "Overall Disease Response (ig_RSALL2.RSALLCAT)",
                "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)",
            ]
        ]
        # Compare responseC_primary_M3_df with responseC_df, and add the subjects (do it once) that are not in responseC_primary_M3_df to responseC_primary_M3_df
        responseC_primary_M3_df = pd.concat(
            [
                responseC_primary_M3_df,
                responseC_df[
                    ~responseC_df["Subject"].isin(responseC_primary_M3_df["Subject"])
                ][["Subject"]],
            ]
        )
        # Remove duplicates
        responseC_primary_M3_df = responseC_primary_M3_df.drop_duplicates(
            subset=["Subject"]
        )
        # Copy snapshot of responseC_primary_df to a temporary dataframe
        temp_df = responseC_primary_df_snapshot
        # Sort the temporary dataframe by Subject and Event Date
        temp_df = temp_df.sort_values(by=["Subject", "Event Date"])
        # remove all the rows that have nan in Overall Disease Response (ig_RSALL2.RSALLCAT) and Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)
        temp_df = temp_df[
            temp_df["Overall Disease Response (ig_RSALL2.RSALLCAT)"].notna()
            | temp_df[
                "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)"
            ].notna()
        ]
        # Create a for loop that will check the Overall Disease Response (ig_RSALL2.RSALLCAT) and Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS) of each subject in responseC_primary_M3_df
        for index, row in responseC_primary_M3_df.iterrows():
            # check if the Overall Disease Response (ig_RSALL2.RSALLCAT) of the subject is nan, and check if the Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS) of the subject is nan
            if pd.isna(
                row["Overall Disease Response (ig_RSALL2.RSALLCAT)"]
            ) and pd.isna(
                row[
                    "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)"
                ]
            ):
                # if yes, check to see if the subject in in PD_df
                if row["Subject"] in PD_df["Subject"].values:
                    # get the End of Primary Follow-Up Date (ig_INITLF1.DSENPFUDAT) date of the subject in PD_Primary_df
                    end_date = PD_df[PD_df["Subject"] == row["Subject"]][
                        "End of Primary Follow-Up Date (ig_INITLF1.DSENPFUDAT)"
                    ].values[0]
                    # if yes, find the response of the same subject with the latest event date that is before the Month 3 event date
                    filtered_df = temp_df[
                        (temp_df["Subject"] == row["Subject"])
                        & (temp_df["Event Date"] <= end_date)
                    ]
                    # Check if the filtered DataFrame is empty
                    if not filtered_df.empty:
                        # Access the last row if the DataFrame is not empty
                        temp_row = filtered_df.iloc[-1]
                        # Replace the Overall Disease Response (ig_RSALL2.RSALLCAT) of the subject with the Overall Disease Response (ig_RSALL2.RSALLCAT) of the temp_row
                        responseC_primary_M3_df.loc[
                            index, "Overall Disease Response (ig_RSALL2.RSALLCAT)"
                        ] = temp_row["Overall Disease Response (ig_RSALL2.RSALLCAT)"]
                        # Replace the Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS) of the subject with the Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS) of the temp_row
                        responseC_primary_M3_df.loc[
                            index,
                            "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)",
                        ] = temp_row[
                            "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)"
                        ]
                # check if the subject is in Initiation of REtx before month 3
                elif row["Subject"] in DSINITRT_df["Subject"].values:
                    # get the End of Primary Follow-Up Date (ig_DSINITRT1.DSRENPFUDAT) date of the subject in DSINITRT_df
                    end_date = DSINITRT_df[DSINITRT_df["Subject"] == row["Subject"]][
                        "End of Primary Follow-Up Date (ig_DSINITRT1.DSRENPFUDAT)"
                    ].values[0]
                    # if yes, find the response of the same subject with the latest event date that is before the Month 3 event date
                    filtered_df = temp_df[
                        (temp_df["Subject"] == row["Subject"])
                        & (temp_df["Event Date"] <= end_date)
                    ]
                    # Check if the filtered DataFrame is empty
                    if not filtered_df.empty:
                        # Access the last row if the DataFrame is not empty
                        temp_row = filtered_df.iloc[-1]
                        # Replace the Overall Disease Response (ig_RSALL2.RSALLCAT) of the subject with the Overall Disease Response (ig_RSALL2.RSALLCAT) of the temp_row
                        responseC_primary_M3_df.loc[
                            index, "Overall Disease Response (ig_RSALL2.RSALLCAT)"
                        ] = temp_row["Overall Disease Response (ig_RSALL2.RSALLCAT)"]
                        # Replace the Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS) of the subject with the Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS) of the temp_row
                        responseC_primary_M3_df.loc[
                            index,
                            "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)",
                        ] = temp_row[
                            "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)"
                        ]
        # Rename the column Overall Disease Response (ig_RSALL2.RSALLCAT) to OV ORR
        responseC_primary_M3_df.rename(
            columns={
                "Overall Disease Response (ig_RSALL2.RSALLCAT)": "OV ORR",
                "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)": "ED ORR",
            },
            inplace=True,
        )
        # Merge left with the current response dataframe
        final_response_ALL_primary_df = pd.merge(
            final_response_ALL_primary_df,
            responseC_primary_M3_df,
            on="Subject",
            how="left",
        )
        # Fill NaN with "Not Applicable" in column OV ORR
        final_response_ALL_primary_df["OV ORR"] = final_response_ALL_primary_df[
            "OV ORR"
        ].fillna("Not Applicable")
        # Fill NaN with "Not Applicable" in column ED ORR
        final_response_ALL_primary_df["ED ORR"] = final_response_ALL_primary_df[
            "ED ORR"
        ].fillna("Not Applicable")
        # Replace Extramedullary Disease Without Bone Marrow Involvement with Not Applicable
        final_response_ALL_primary_df["OV ORR"] = final_response_ALL_primary_df[
            "OV ORR"
        ].replace(
            "Extramedullary Disease Without Bone Marrow Involvement", "Not Applicable"
        )

        ## Checking AE and SAE for NHL primary
        # Getting AE and SAE dataframes
        responseC_primary_AE_df = data["AE"][
            [
                "Subject",
                "Form ILB Status",
                "AE or SAE? (ig_AE2.AESEV)",
                "Event Onset (ig_AE1.AEONSET)",
            ]
        ]
        # Check responseC_primary_AE_df if the subject of responseC_primary_df is in the AE dataframe. If yes, then add 'Y' to the column 'AE' in responseC_primary_df, else add 'N'
        final_response_ALL_primary_df["AE"] = final_response_ALL_primary_df[
            "Subject"
        ].apply(
            lambda x: "Y" if x in responseC_primary_AE_df["Subject"].values else "N"
        )
        # Check responseC_primary_AE_df if the subject of responseC_primary_df has SAE in column 'AE or SAE? (ig_AE2.AESEV)' . If yes, then add 'Y' to the column 'SAE' in responseC_primary_df, else add 'N'
        final_response_ALL_primary_df["SAE"] = final_response_ALL_primary_df[
            "Subject"
        ].apply(
            lambda x: (
                "Y"
                if x
                in responseC_primary_AE_df[
                    responseC_primary_AE_df["AE or SAE? (ig_AE2.AESEV)"] == "SAE"
                ]["Subject"].values
                else "N"
            )
        )

        ## Checking Study Status for NHL primary
        # Getting Study Status dataframe from SVALL, column Subject, Event Label and Event Date
        responseC_primary_SV_df = data["SVALL"][
            ["Subject", "Event Label", "Event Date"]
        ]
        # Getting Study Status dataframe from DSSVLTFUALL, column Subject, Event Label and Event Date
        responseC_primary_DSSVLTFU_df = data["DSSVLTFUALL"][
            ["Subject", "Event Label", "Event Date"]
        ]
        # Getting End of Study status from EOS
        responseC_primary_EOS_df = data["EOS"][
            ["Subject", "End of Study Date (ig_EOS1.EOSDAT)"]
        ]
        # Drop columns that are entirely NA from both DataFrames
        responseC_primary_SV_df = responseC_primary_SV_df.dropna(axis=1, how="all")
        responseC_primary_DSSVLTFU_df = responseC_primary_DSSVLTFU_df.dropna(
            axis=1, how="all"
        )
        # Combine DSSVLTFU with SV dataframe vertically
        responseC_primary_SV_df = pd.concat(
            [responseC_primary_SV_df, responseC_primary_DSSVLTFU_df]
        )
        # Sort the dataframe by Subject and Event Date
        responseC_primary_SV_df = responseC_primary_SV_df.sort_values(
            by=["Subject", "Event Date"]
        )
        # For each unique subject, get the last row of the dataframe
        responseC_primary_SV_df = responseC_primary_SV_df.groupby("Subject").tail(1)
        # Merge with EOS data to get End of Study Date
        responseC_primary_SV_df = pd.merge(
            responseC_primary_SV_df, responseC_primary_EOS_df, on="Subject", how="left"
        )
        # Format the End of Study Date if available
        responseC_primary_SV_df = remove_leading_zeros_from_dates(
            responseC_primary_SV_df
        )

        # Merge left with the current response dataframe
        final_response_ALL_primary_df = pd.merge(
            final_response_ALL_primary_df,
            responseC_primary_SV_df[
                ["Subject", "Event Label", "End of Study Date (ig_EOS1.EOSDAT)"]
            ],
            on="Subject",
            how="left",
        )
        # Rename the column Event Label to Event Label (Study Status)
        final_response_ALL_primary_df["Event Label"] = final_response_ALL_primary_df[
            "Event Label"
        ].map(event_C_dict)
        # Add End of Study Date to Event Label if available
        final_response_ALL_primary_df["End of Study Date (ig_EOS1.EOSDAT)"] = (
            final_response_ALL_primary_df["End of Study Date (ig_EOS1.EOSDAT)"].fillna(
                ""
            )
        )
        final_response_ALL_primary_df["Event Label"] = (
            final_response_ALL_primary_df.apply(
                lambda row: (
                    f"{row['Event Label']} (EOS:{row['End of Study Date (ig_EOS1.EOSDAT)']})"
                    if row["End of Study Date (ig_EOS1.EOSDAT)"]
                    else row["Event Label"]
                ),
                axis=1,
            )
        )
        # Select the columns needed only
        final_response_ALL_primary_df = final_response_ALL_primary_df[
            [
                "Subject",
                "Current Overall Response",
                "Current ED Response",
                "Current Response Time Point",
                "Best Overall Response",
                "Best Overall Response Time Point",
                "Best ED Response",
                "Best ED Time Point",
                "OV ORR",
                "ED ORR",
                "AE",
                "SAE",
                "Event Label",
            ]
        ]
        final_response_ALL_primary_df = final_response_ALL_primary_df.replace(
            [np.nan, np.inf, -np.inf], ""
        )

        cohort_C_subjects = final_enrollment_df[
            final_enrollment_df["Cohort Assignment"].str.contains("Cohort C")
        ]["Subject"].tolist()

        # Subjects in Cohort D
        final_responseD_ALL_df = final_response_ALL_primary_df[
            final_response_ALL_primary_df["Subject"].isin(cohort_D_subjects)
        ].copy()

        # Subjects in cohort C
        final_responseC_primary_df = final_response_ALL_primary_df[
            final_response_ALL_primary_df["Subject"].isin(cohort_C_subjects)
        ].copy()

        # Count number of subject of column 'Best Overall Response' that is not 'Not Applicable' for cohort C
        final_subject_C_prim_OR_count = len(
            final_responseC_primary_df[
                final_responseC_primary_df["Best Overall Response"] != "Not Applicable"
            ]["Subject"].unique()
        )
        # Count number of subject of column 'Best ED Response' that is not 'Not Applicable' for cohort C
        final_subject_C_prim_ED_count = len(
            final_responseC_primary_df[
                final_responseC_primary_df["Best ED Response"] != "Not Applicable"
            ]["Subject"].unique()
        )

        # Count number of subject of column 'Best Overall Response' that is not 'Not Applicable' for cohort D
        final_subject_D_prim_OR_count = len(
            final_responseD_ALL_df[
                final_responseD_ALL_df["Best Overall Response"] != "Not Applicable"
            ]["Subject"].unique()
        )
        # Count number of subject of column 'Best ED Response' that is not 'Not Applicable' for cohort D
        final_subject_D_prim_ED_count = len(
            final_responseD_ALL_df[
                final_responseD_ALL_df["Best ED Response"] != "Not Applicable"
            ]["Subject"].unique()
        )

        # Cohort C - ALL Retreatment
    # Filter to only Retreatment
    responseC_retreatment_df = responseC_df[
        responseC_df["Study Phase (ig_RSALL1.STUDYPHS2)"] == "Retreatment"
    ].copy()
    # Replace value of "Unscheduled" in column Retreatment Time Point with value of "For Unscheduled Retreatment Time Point, Specify Day #"
    temp_mask = (
        responseC_retreatment_df["Retreatment Time Point (ig_RSALL1.RSALLTPTR)"]
        == "Unscheduled"
    )
    # Convert the column For Unscheduled Retreatment Time Point, Specify Day # to string
    responseC_retreatment_df = convert_integers_to_strings(
        responseC_retreatment_df,
        "For Unscheduled Retreatment Time Point, Specify Day # (ig_RSALL1.UNSDAYR)",
    )
    responseC_retreatment_df.loc[
        temp_mask, "Retreatment Time Point (ig_RSALL1.RSALLTPTR)"
    ] = responseC_retreatment_df.loc[
        temp_mask,
        "For Unscheduled Retreatment Time Point, Specify Day # (ig_RSALL1.UNSDAYR)",
    ].apply(
        lambda x: (
            f"Day {x}-R"
            if pd.notna(x) and str(x).strip().replace("-R", "").isdigit()
            else x
        )
    )
    # Remove rows with Pre-Retreatment Safety Visit
    responseC_retreatment_df = responseC_retreatment_df[
        responseC_retreatment_df["Retreatment Time Point (ig_RSALL1.RSALLTPTR)"]
        != "Pre-Retreatment Safety Visit"
    ].copy()
    # Remove rows with Post-Lymphodepleting Chemotherapy
    responseC_retreatment_df = responseC_retreatment_df[
        responseC_retreatment_df["Retreatment Time Point (ig_RSALL1.RSALLTPTR)"]
        != "Post-Lymphodepleting Chemotherapy"
    ].copy()
    # replace all rows with Extramedullary Disease Without Bone Marrow Involvement to Not Applicable
    responseC_retreatment_df["Overall Disease Response (ig_RSALL2.RSALLCAT)"] = (
        responseC_retreatment_df[
            "Overall Disease Response (ig_RSALL2.RSALLCAT)"
        ].replace(
            "Extramedullary Disease Without Bone Marrow Involvement", "Not Applicable"
        )
    )

    # Convert Event Date to datetime object
    responseC_retreatment_df["Event Date"] = pd.to_datetime(
        responseC_retreatment_df["Event Date"]
    )
    # Snapshot the responseC_retreatment_df
    responseC_retreatment_df_snapshot = responseC_retreatment_df.copy()
    # check the number of subject for cohort C - ALL Retreatment
    final_subject_C_retx_count = len(responseC_retreatment_df["Subject"].unique())

    # Check if there is any subject. If yes, then proceed, else skip
    if final_subject_C_retx_count > 0:
        # Fill NaN with "Not Applicable" in column Overall Disease Response (ig_RSALL2.RSALLCAT)
        responseC_retreatment_df["Overall Disease Response (ig_RSALL2.RSALLCAT)"] = (
            responseC_retreatment_df[
                "Overall Disease Response (ig_RSALL2.RSALLCAT)"
            ].fillna("Not Applicable")
        )
        # Fill NaN with "Not Applicable" in column Radiographic Tumor Response for Extramedullary Disease
        responseC_retreatment_df[
            "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)"
        ] = responseC_retreatment_df[
            "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)"
        ].fillna("Not Applicable")
        # Convert to numeric values
        responseC_retreatment_df["OV-Score"] = (
            responseC_retreatment_df["Overall Disease Response (ig_RSALL2.RSALLCAT)"]
            .map(DR_ALL_OV_dict)
            .fillna(DR_ALL_OV_dict["Not Applicable"])
        )
        responseC_retreatment_df["ED-Score"] = (
            responseC_retreatment_df[
                "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)"
            ]
            .map(DR_ALL_ED_dict)
            .fillna(DR_ALL_ED_dict["Not Applicable"])
        )

        # * CURRENT RESPONSE
        # Get the indices of the rows with the maximum 'Event Date' for each 'Subject'
        idx = responseC_retreatment_df.groupby("Subject")["Event Date"].idxmax()
        # Select these rows for the current response
        responseC_retreatment_current_df = responseC_retreatment_df.loc[idx].copy()
        # Fill NaN with "Not Applicable"
        responseC_retreatment_current_df[
            "Overall Disease Response (ig_RSALL2.RSALLCAT)"
        ] = responseC_retreatment_current_df[
            "Overall Disease Response (ig_RSALL2.RSALLCAT)"
        ].fillna("Not Applicable")
        responseC_retreatment_current_df[
            "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)"
        ] = responseC_retreatment_current_df[
            "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)"
        ].fillna("Not Applicable")
        # rename the columns
        responseC_retreatment_current_df.rename(
            columns={
                "Overall Disease Response (ig_RSALL2.RSALLCAT)": "Current Overall Response",
                "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)": "Current ED Response",
                "Retreatment Time Point (ig_RSALL1.RSALLTPTR)": "Current Response Time Point",
            },
            inplace=True,
        )

        # * BEST RESPONSE
        ## Best OV ALL Disease Response retreatment
        # Get the indices of the rows with the minimum 'OV-Score' for each 'Subject'
        responseC_best_OV_idx = responseC_retreatment_df.groupby("Subject")[
            "OV-Score"
        ].idxmin()
        # Select these rows for the best OV response
        responseC_best_OV_df = responseC_retreatment_df.loc[
            responseC_best_OV_idx
        ].copy()
        # Select the columns
        responseC_best_OV_df = responseC_best_OV_df[
            [
                "Subject",
                "Overall Disease Response (ig_RSALL2.RSALLCAT)",
                "Retreatment Time Point (ig_RSALL1.RSALLTPTR)",
            ]
        ]
        # Rename the columns
        responseC_best_OV_df.rename(
            columns={
                "Overall Disease Response (ig_RSALL2.RSALLCAT)": "Best Overall Response",
                "Retreatment Time Point (ig_RSALL1.RSALLTPTR)": "Best Overall Response Time Point",
            },
            inplace=True,
        )
        # Replace Nan with Not Applicable
        responseC_best_OV_df["Best Overall Response"] = responseC_best_OV_df[
            "Best Overall Response"
        ].fillna("Not Applicable")
        # Merge left with the current response dataframe
        final_responseC_retreatment_df = pd.merge(
            responseC_retreatment_current_df,
            responseC_best_OV_df,
            on="Subject",
            how="left",
        )

        ## Best ED ALL Disease Response retreatment
        # Get the indices of the rows with the minimum 'ED-Score' for each 'Subject'
        responseC_best_ED_idx = responseC_retreatment_df.groupby("Subject")[
            "ED-Score"
        ].idxmin()
        # Select these rows for the best ED response
        responseC_best_ED_df = responseC_retreatment_df.loc[
            responseC_best_ED_idx
        ].copy()
        # Select the columns
        responseC_best_ED_df = responseC_best_ED_df[
            [
                "Subject",
                "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)",
                "Retreatment Time Point (ig_RSALL1.RSALLTPTR)",
            ]
        ]
        # Rename the columns
        responseC_best_ED_df.rename(
            columns={
                "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)": "Best ED Response",
                "Retreatment Time Point (ig_RSALL1.RSALLTPTR)": "Best ED Time Point",
            },
            inplace=True,
        )
        # Replace Nan with Not Applicable
        responseC_best_ED_df["Best ED Response"] = responseC_best_ED_df[
            "Best ED Response"
        ].fillna("Not Applicable")
        # Merge left with the retreatment response dataframe
        final_responseC_retreatment_df = pd.merge(
            final_responseC_retreatment_df,
            responseC_best_ED_df,
            on="Subject",
            how="left",
        )

        ## * Overall ALL Disease Response at Day 28-R retreatment
        # Filter responseC_retreatment_df to only Day 28-R
        responseC_retreatment_M3_df = responseC_df[
            responseC_df["Retreatment Time Point (ig_RSALL1.RSALLTPTR)"] == "Day 28-R"
        ].copy()
        # Select the columns
        responseC_retreatment_M3_df = responseC_retreatment_M3_df[
            [
                "Subject",
                "Overall Disease Response (ig_RSALL2.RSALLCAT)",
                "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)",
            ]
        ].copy()
        # Add subjects that are not in responseC_retreatment_M3_df
        responseC_retreatment_M3_df = pd.concat(
            [
                responseC_retreatment_M3_df,
                responseC_retreatment_df[
                    ~responseC_retreatment_df["Subject"].isin(
                        responseC_retreatment_M3_df["Subject"]
                    )
                ][["Subject"]],
            ]
        )
        # Remove duplicates
        responseC_retreatment_M3_df = responseC_retreatment_M3_df.drop_duplicates(
            subset=["Subject"]
        )

        # Copy snapshot of responseC_retreatment_df to a temporary dataframe
        temp_df = responseC_retreatment_df_snapshot
        # Sort the temporary dataframe by Subject and Event Date
        temp_df = temp_df.sort_values(by=["Subject", "Event Date"])
        # remove all the rows that have nan in both responses
        temp_df = temp_df[
            temp_df["Overall Disease Response (ig_RSALL2.RSALLCAT)"].notna()
            | temp_df[
                "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)"
            ].notna()
        ]

        # Check for PD in retreatment
        for index, row in responseC_retreatment_M3_df.iterrows():
            # check if both responses are nan
            if pd.isna(
                row["Overall Disease Response (ig_RSALL2.RSALLCAT)"]
            ) and pd.isna(
                row[
                    "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)"
                ]
            ):
                # if yes, check to see if the subject in in PD_Retx_df
                if row["Subject"] in PD_Retx_df["Subject"].values:
                    # get the End of Retreatment Date
                    end_date = PD_Retx_df[PD_Retx_df["Subject"] == row["Subject"]][
                        "End of Retreatment Date (ig_INITLF1.DSENRETXDAT)"
                    ].values[0]
                    # find the response of the same subject with the latest event date that is before the end date
                    filtered_df = temp_df[
                        (temp_df["Subject"] == row["Subject"])
                        & (temp_df["Event Date"] <= end_date)
                    ]
                    # Check if the filtered DataFrame is empty
                    if not filtered_df.empty:
                        # Access the last row if the DataFrame is not empty
                        temp_row = filtered_df.iloc[-1]
                        # Replace the responses
                        responseC_retreatment_M3_df.loc[
                            index, "Overall Disease Response (ig_RSALL2.RSALLCAT)"
                        ] = temp_row["Overall Disease Response (ig_RSALL2.RSALLCAT)"]
                        responseC_retreatment_M3_df.loc[
                            index,
                            "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)",
                        ] = temp_row[
                            "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)"
                        ]

        # Rename the columns
        responseC_retreatment_M3_df.rename(
            columns={
                "Overall Disease Response (ig_RSALL2.RSALLCAT)": "OV ORR",
                "Radiographic Tumor Response for	Extramedullary Disease (ig_RSALL2.RADTURESEXDS)": "ED ORR",
            },
            inplace=True,
        )
        # Merge left with the current response dataframe
        final_responseC_retreatment_df = pd.merge(
            final_responseC_retreatment_df,
            responseC_retreatment_M3_df,
            on="Subject",
            how="left",
        )
        # Fill NaN with "Not Applicable"
        final_responseC_retreatment_df["OV ORR"] = final_responseC_retreatment_df[
            "OV ORR"
        ].fillna("Not Applicable")
        final_responseC_retreatment_df["ED ORR"] = final_responseC_retreatment_df[
            "ED ORR"
        ].fillna("Not Applicable")
        # Replace Extramedullary Disease Without Bone Marrow Involvement with Not Applicable
        final_responseC_retreatment_df["OV ORR"] = final_responseC_retreatment_df[
            "OV ORR"
        ].replace(
            "Extramedullary Disease Without Bone Marrow Involvement", "Not Applicable"
        )

        ## Checking AE and SAE for ALL retreatment
        # Getting AE and SAE dataframes
        responseC_retreatment_AE_df = data["AE"][
            [
                "Subject",
                "Form ILB Status",
                "AE or SAE? (ig_AE2.AESEV)",
                "Event Onset (ig_AE1.AEONSET)",
            ]
        ]
        # Check if subject is in the AE dataframe
        final_responseC_retreatment_df["AE"] = final_responseC_retreatment_df[
            "Subject"
        ].apply(
            lambda x: "Y" if x in responseC_retreatment_AE_df["Subject"].values else "N"
        )
        # Check if subject has SAE
        final_responseC_retreatment_df["SAE"] = final_responseC_retreatment_df[
            "Subject"
        ].apply(
            lambda x: (
                "Y"
                if x
                in responseC_retreatment_AE_df[
                    responseC_retreatment_AE_df["AE or SAE? (ig_AE2.AESEV)"] == "SAE"
                ]["Subject"].values
                else "N"
            )
        )

        ## Checking Study Status for ALL retreatment
        # Getting Study Status dataframe from SVALL
        responseC_retreatment_SV_df = data["SVALL"][
            ["Subject", "Event Label", "Event Date"]
        ]
        # Getting Study Status dataframe from DSSVLTFUALL
        responseC_retreatment_DSSVLTFU_df = data["DSSVLTFUALL"][
            ["Subject", "Event Label", "Event Date"]
        ]
        # Getting End of Study status from EOS
        responseC_retreatment_EOS_df = data["EOS"][
            ["Subject", "End of Study Date (ig_EOS1.EOSDAT)"]
        ]
        # Drop columns that are entirely NA from both DataFrames
        responseC_retreatment_SV_df = responseC_retreatment_SV_df.dropna(
            axis=1, how="all"
        )
        responseC_retreatment_DSSVLTFU_df = responseC_retreatment_DSSVLTFU_df.dropna(
            axis=1, how="all"
        )
        # Combine DSSVLTFU with SV dataframe vertically
        responseC_retreatment_SV_df = pd.concat(
            [responseC_retreatment_SV_df, responseC_retreatment_DSSVLTFU_df]
        )
        # Sort the dataframe by Subject and Event Date
        responseC_retreatment_SV_df = responseC_retreatment_SV_df.sort_values(
            by=["Subject", "Event Date"]
        )
        # For each unique subject, get the last row of the dataframe
        responseC_retreatment_SV_df = responseC_retreatment_SV_df.groupby(
            "Subject"
        ).tail(1)
        # Merge with EOS data to get End of Study Date
        responseC_retreatment_SV_df = pd.merge(
            responseC_retreatment_SV_df,
            responseC_retreatment_EOS_df,
            on="Subject",
            how="left",
        )
        responseC_retreatment_SV_df = responseC_retreatment_SV_df.fillna("")
        # Format the End of Study Date if available
        responseC_retreatment_SV_df = remove_leading_zeros_from_dates(
            responseC_retreatment_SV_df
        )

        # Merge left with the current response dataframe
        final_responseC_retreatment_df = pd.merge(
            final_responseC_retreatment_df,
            responseC_retreatment_SV_df[
                ["Subject", "Event Label", "End of Study Date (ig_EOS1.EOSDAT)"]
            ],
            on="Subject",
            how="left",
        )
        # Add End of Study Date to Event Label if available
        final_responseC_retreatment_df["End of Study Date (ig_EOS1.EOSDAT)"] = (
            final_responseC_retreatment_df["End of Study Date (ig_EOS1.EOSDAT)"].fillna(
                ""
            )
        )
        # Map Event Label using event_C_dict
        final_responseC_retreatment_df["Event Label"] = final_responseC_retreatment_df[
            "Event Label"
        ].map(event_C_dict)
        # replace all NaT of pandas with ""
        final_responseC_retreatment_df["Event Label"] = (
            final_responseC_retreatment_df.apply(
                lambda row: (
                    f"{row['Event Label']} (EOS:{row['End of Study Date (ig_EOS1.EOSDAT)']})"
                    if row["End of Study Date (ig_EOS1.EOSDAT)"] != ""
                    else row["Event Label"]
                ),
                axis=1,
            )
        )

        # Select the columns needed only
        final_responseC_retreatment_df = final_responseC_retreatment_df[
            [
                "Subject",
                "Current Overall Response",
                "Current ED Response",
                "Current Response Time Point",
                "Best Overall Response",
                "Best Overall Response Time Point",
                "Best ED Response",
                "Best ED Time Point",
                "OV ORR",
                "ED ORR",
                "AE",
                "SAE",
                "Event Label",
            ]
        ]
        final_responseC_retreatment_df = final_responseC_retreatment_df.replace(
            [np.nan, np.inf, -np.inf], ""
        )

        # Count number of subjects with responses

    # REPONSE STATS
    # SAFETY STATS

    # Gather all stats of Cohort A, B and C
    total_infused_df = final_infusion_df.copy()
    # Getting AE and SAE dataframes
    AE_df = data["AE"][
        [
            "Subject",
            "Form ILB Status",
            "AE or SAE? (ig_AE2.AESEV)",
            "Event Onset (ig_AE1.AEONSET)",
        ]
    ].copy()
    # Check responseA_primary_AE_df if the subject of responseA_primary_df is in the AE dataframe. If yes, then add 'Y' to the column 'AE' in responseA_primary_df, else add 'N'
    total_infused_df["AE"] = total_infused_df["Subject"].apply(
        lambda x: "Y" if x in AE_df["Subject"].values else "N"
    )
    # Check responseA_primary_AE_df if the subject of responseA_primary_df has SAE in column 'AE or SAE? (ig_AE2.AESEV)' . If yes, then add 'Y' to the column 'SAE' in responseA_primary_df, else add 'N'
    total_infused_df["SAE"] = total_infused_df["Subject"].apply(
        lambda x: (
            "Y"
            if x in AE_df[AE_df["AE or SAE? (ig_AE2.AESEV)"] == "SAE"]["Subject"].values
            else "N"
        )
    )
    # UPDATED: Filter for only Cohorts A, B, and C for ABC stats
    abc_infused_df = total_infused_df[
        total_infused_df["Cohort Assignment"].str.contains("Cohort A|Cohort B|Cohort C")
    ].copy()

    # Total number of subjects in cohort A, B, and C only
    AE_abc_total_count = get_stats_percentage("AE", abc_infused_df).T
    SAE_abc_total_count = get_stats_percentage("SAE", abc_infused_df).T
    # merge AE and SAE dataframes
    final_safety_abc_total_df = pd.concat(
        [AE_abc_total_count, SAE_abc_total_count], axis=1
    )

    # get stats for cohort A, B, and C
    AE_A_count = get_stats_percentage(
        "AE",
        abc_infused_df[
            abc_infused_df["Cohort Assignment"]
            == "Cohort A: Non-Hodgkin Lymphoma (NHL)"
        ],
    ).T
    SAE_A_count = get_stats_percentage(
        "SAE",
        abc_infused_df[
            abc_infused_df["Cohort Assignment"]
            == "Cohort A: Non-Hodgkin Lymphoma (NHL)"
        ],
    ).T
    # merge AE and SAE dataframes
    final_safety_A_df = pd.concat([AE_A_count, SAE_A_count], axis=1)

    AE_B_count = get_stats_percentage(
        "AE",
        abc_infused_df[
            abc_infused_df["Cohort Assignment"]
            == "Cohort B: Chronic Lymphocytic Leukemia (CLL)"
        ],
    ).T
    SAE_B_count = get_stats_percentage(
        "SAE",
        abc_infused_df[
            abc_infused_df["Cohort Assignment"]
            == "Cohort B: Chronic Lymphocytic Leukemia (CLL)"
        ],
    ).T
    # merge AE and SAE dataframes
    final_safety_B_df = pd.concat([AE_B_count, SAE_B_count], axis=1)

    AE_C_count = get_stats_percentage(
        "AE",
        abc_infused_df[
            abc_infused_df["Cohort Assignment"]
            == "Cohort C: Acute Lymphoblastic Leukemia (ALL)"
        ],
    ).T
    SAE_C_count = get_stats_percentage(
        "SAE",
        abc_infused_df[
            abc_infused_df["Cohort Assignment"]
            == "Cohort C: Acute Lymphoblastic Leukemia (ALL)"
        ],
    ).T
    # merge AE and SAE dataframes
    final_safety_C_df = pd.concat([AE_C_count, SAE_C_count], axis=1)

    final_safety_df = pd.concat(
        [
            final_safety_abc_total_df,
            final_safety_A_df,
            final_safety_B_df,
            final_safety_C_df,
        ],
        axis=0,
    )

    # NEW: Create safety statistics for Cohort D only
    d_infused_df = total_infused_df[
        total_infused_df["Cohort Assignment"].str.contains("Cohort D")
    ].copy()

    if len(d_infused_df) > 0:
        AE_D_total_count = get_stats_percentage("AE", d_infused_df).T
        SAE_D_total_count = get_stats_percentage("SAE", d_infused_df).T
        final_safety_D_df = pd.concat([AE_D_total_count, SAE_D_total_count], axis=1)
    else:
        # Create empty dataframe with proper structure if no Cohort D subjects
        final_safety_D_df = pd.DataFrame(
            {"Y": ["0 (0%)"], "N": ["0 (0%)"]}, index=["Y"]
        )

    # RESPONSE STATS
    if final_subject_A_prim_count > 0:
        responseA_stat = final_responseA_primary_df.copy()
        # replace 'Not Assessed' with 'Not Reported' for all columns in responseA_stat
        responseA_stat = responseA_stat.replace("Not Assessed", "Not Reported")
        final_response_stat_A_BOR_PET = get_stats_percentage(
            "PET-Based Response", responseA_stat
        )
        final_response_stat_A_BOR_CT = get_stats_percentage(
            "CT-Based Response", responseA_stat
        )
        final_response_stat_A_ORR_PET = get_stats_percentage(
            "PET-Based ORR", responseA_stat
        )
        final_response_stat_A_ORR_CT = get_stats_percentage(
            "CT-Based ORR", responseA_stat
        )

    if final_subject_B_prim_count > 0:
        responseB_stat = final_responseB_primary_df.copy()
        # replace 'Not Assessed' with 'Not Reported' for all columns in responseB_stat
        responseB_stat = responseB_stat.replace("Not Assessed", "Not Reported")
        responseB_stat = responseB_stat.replace("Not Evaluable", "Not Reported")
        final_response_stat_B_BOR_OV = get_stats_percentage(
            "OV-Best Response", responseB_stat
        )
        final_response_stat_B_BOR_BM = get_stats_percentage(
            "BM-Best Response", responseB_stat
        )
        final_response_stat_B_ORR_OV = get_stats_percentage(
            "Overall Response", responseB_stat
        )
        final_response_stat_B_ORR_BM = get_stats_percentage(
            "Bone Marrow Response", responseB_stat
        )

    if final_subject_C_prim_count > 0:
        responseC_stat = final_responseC_primary_df.copy()
        # replace 'Extramedullary Disease Without Bone Marrow Involvement', 'No Clinical Evidence of Relapse', 'Unknown/Not Assessed' with 'Not Reported' for all columns in responseC_stat
        responseC_stat = responseC_stat.replace(
            "Extramedullary Disease Without Bone Marrow Involvement", "Not Applicable"
        )
        responseC_stat = responseC_stat.replace(
            "No Clinical Evidence of Relapse", "Not Reported"
        )
        responseC_stat = responseC_stat.replace("Unknown/Not Assessed", "Not Reported")
        responseC_stat = responseC_stat.replace("Not Assessed", "Not Reported")
        final_response_stat_C_BOR_OV = get_stats_percentage(
            "Best Overall Response", responseC_stat
        )
        final_response_stat_C_BOR_ED = get_stats_percentage(
            "Best ED Response", responseC_stat
        )
        final_response_stat_C_ORR_OV = get_stats_percentage("OV ORR", responseC_stat)
        final_response_stat_C_ORR_ED = get_stats_percentage("ED ORR", responseC_stat)

    if final_subject_BRT_prim_count > 0:
        responseBRT_stat = final_responseBRT_primary_df.copy()
        # replace 'Not Assessed' with 'Not Reported' for all columns in responseBRT_stat
        responseBRT_stat = responseBRT_stat.replace("Not Assessed", "Not Reported")
        final_response_stat_BRT_BOR_PET = get_stats_percentage(
            "PET-Based Response", responseBRT_stat
        )
        final_response_stat_BRT_BOR_CT = get_stats_percentage(
            "CT-Based Response", responseBRT_stat
        )
        final_response_stat_BRT_ORR_PET = get_stats_percentage(
            "PET-Based ORR", responseBRT_stat
        )
        final_response_stat_BRT_ORR_CT = get_stats_percentage(
            "CT-Based ORR", responseBRT_stat
        )

    # NEW: Create response statistics for Cohort D
    # For Cohort D NHL subjects
    if len(final_responseD_NHL_df) > 0:
        responseD_NHL_stat = final_responseD_NHL_df.copy()
        responseD_NHL_stat = responseD_NHL_stat.replace("Not Assessed", "Not Reported")
        responseD_NHL_stat = responseD_NHL_stat.replace("Not Evaluable", "Not Reported")
        final_response_stat_D_NHL_BOR_PET = get_stats_percentage(
            "PET-Based Response", responseD_NHL_stat
        )
        final_response_stat_D_NHL_BOR_CT = get_stats_percentage(
            "CT-Based Response", responseD_NHL_stat
        )
        final_response_stat_D_NHL_ORR_PET = get_stats_percentage(
            "PET-Based ORR", responseD_NHL_stat
        )
        final_response_stat_D_NHL_ORR_CT = get_stats_percentage(
            "CT-Based ORR", responseD_NHL_stat
        )
        final_subject_D_NHL_count = len(final_responseD_NHL_df["Subject"].unique())
    else:
        # Create empty dataframes if no Cohort D NHL subjects
        empty_response_df = pd.DataFrame({"N": ["0 (0%)"]}, index=["Not Reported"])
        final_response_stat_D_NHL_BOR_PET = empty_response_df.copy()
        final_response_stat_D_NHL_BOR_CT = empty_response_df.copy()
        final_response_stat_D_NHL_ORR_PET = empty_response_df.copy()
        final_response_stat_D_NHL_ORR_CT = empty_response_df.copy()
        final_subject_D_NHL_count = 0

    if len(final_responseD_ALL_df) > 0:
        responseD_ALL_stat = final_responseD_ALL_df.copy()
        responseD_ALL_stat = responseD_ALL_stat.replace(
            "Extramedullary Disease Without Bone Marrow Involvement", "Not Applicable"
        )
        responseD_ALL_stat = responseD_ALL_stat.replace(
            "No Clinical Evidence of Relapse", "Not Reported"
        )
        responseD_ALL_stat = responseD_ALL_stat.replace(
            "Unknown/Not Assessed", "Not Reported"
        )
        responseD_ALL_stat = responseD_ALL_stat.replace("Not Assessed", "Not Reported")
        final_response_stat_D_ALL_BOR_OV = get_stats_percentage(
            "Best Overall Response", responseD_ALL_stat
        )
        final_response_stat_D_ALL_BOR_ED = get_stats_percentage(
            "Best ED Response", responseD_ALL_stat
        )
        final_response_stat_D_ALL_ORR_OV = get_stats_percentage(
            "OV ORR", responseD_ALL_stat
        )
        final_response_stat_D_ALL_ORR_ED = get_stats_percentage(
            "ED ORR", responseD_ALL_stat
        )

        # Count subjects for headers
        final_subject_D_ALL_OR_count = len(
            final_responseD_ALL_df[
                final_responseD_ALL_df["Best Overall Response"] != "Not Applicable"
            ]["Subject"].unique()
        )
        final_subject_D_ALL_ED_count = len(
            final_responseD_ALL_df[
                final_responseD_ALL_df["Best ED Response"] != "Not Applicable"
            ]["Subject"].unique()
        )
    else:
        # Create empty dataframes if no Cohort D ALL subjects
        empty_response_df = pd.DataFrame({"N": ["0 (0%)"]}, index=["Not Reported"])
        final_response_stat_D_ALL_BOR_OV = empty_response_df.copy()
        final_response_stat_D_ALL_BOR_ED = empty_response_df.copy()
        final_response_stat_D_ALL_ORR_OV = empty_response_df.copy()
        final_response_stat_D_ALL_ORR_ED = empty_response_df.copy()
        final_subject_D_ALL_OR_count = 0
        final_subject_D_ALL_ED_count = 0

    # UPDATE FORMAT FOR NHL, CLL, and ALL after getting the stats

    if final_subject_A_prim_count > 0:
        final_responseA_primary_df.loc[
            (
                final_responseA_primary_df["Event Label"]
                == "Retreatment Long Term Follow-up"
            )
            | (final_responseA_primary_df["Event Label"] == "Primary Retreatment")
            | (final_responseA_primary_df["Event Label"] == "Pre-Retreatment"),
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)",
        ] = "Transitioned to Retreatment"
        final_responseA_primary_df.loc[
            (
                final_responseA_primary_df["Event Label"]
                == "Retreatment Long Term Follow-up"
            )
            | (final_responseA_primary_df["Event Label"] == "Primary Retreatment")
            | (final_responseA_primary_df["Event Label"] == "Pre-Retreatment"),
            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)",
        ] = "Transitioned to Retreatment"
        final_responseA_primary_df.loc[
            (
                final_responseA_primary_df["Event Label"]
                == "Retreatment Long Term Follow-up"
            )
            | (final_responseA_primary_df["Event Label"] == "Primary Retreatment")
            | (final_responseA_primary_df["Event Label"] == "Pre-Retreatment"),
            "Primary Treatment Time Point (ig_RS1.RSTPT)",
        ] = "Transitioned to Retreatment"

    if final_subject_B_prim_count > 0:
        final_responseB_primary_df.loc[
            (
                final_responseB_primary_df["Event Label"]
                == "Retreatment Long Term Follow-up"
            )
            | (final_responseB_primary_df["Event Label"] == "Primary Retreatment")
            | (final_responseB_primary_df["Event Label"] == "Pre-Retreatment"),
            "Overall CLL Disease Response (ig_RS2.RSCLLCAT)",
        ] = "Transitioned to Retreatment"
        final_responseB_primary_df.loc[
            (
                final_responseB_primary_df["Event Label"]
                == "Retreatment Long Term Follow-up"
            )
            | (final_responseB_primary_df["Event Label"] == "Primary Retreatment")
            | (final_responseB_primary_df["Event Label"] == "Pre-Retreatment"),
            "CLL Bone Marrow Response (ig_RS2.RSCLLBMRESP)",
        ] = "Transitioned to Retreatment"
        final_responseB_primary_df.loc[
            (
                final_responseB_primary_df["Event Label"]
                == "Retreatment Long Term Follow-up"
            )
            | (final_responseB_primary_df["Event Label"] == "Primary Retreatment")
            | (final_responseB_primary_df["Event Label"] == "Pre-Retreatment"),
            "Primary Treatment Time Point (ig_RS1.RSTPT)",
        ] = "Transitioned to Retreatment"

    if final_subject_C_prim_count > 0:
        final_responseC_primary_df.loc[
            (
                final_responseC_primary_df["Event Label"]
                == "Retreatment Long Term Follow-up"
            )
            | (final_responseC_primary_df["Event Label"] == "Primary Retreatment")
            | (final_responseC_primary_df["Event Label"] == "Pre-Retreatment"),
            "Current Overall Response",
        ] = "Transitioned to Retreatment"
        final_responseC_primary_df.loc[
            (
                final_responseC_primary_df["Event Label"]
                == "Retreatment Long Term Follow-up"
            )
            | (final_responseC_primary_df["Event Label"] == "Primary Retreatment")
            | (final_responseC_primary_df["Event Label"] == "Pre-Retreatment"),
            "Current ED Response",
        ] = "Transitioned to Retreatment"
        final_responseC_primary_df.loc[
            (
                final_responseC_primary_df["Event Label"]
                == "Retreatment Long Term Follow-up"
            )
            | (final_responseC_primary_df["Event Label"] == "Primary Retreatment")
            | (final_responseC_primary_df["Event Label"] == "Pre-Retreatment"),
            "Current Response Time Point",
        ] = "Transitioned to Retreatment"

    if final_subject_BRT_prim_count > 0:
        final_responseBRT_primary_df.loc[
            (
                final_responseBRT_primary_df["Event Label"]
                == "Retreatment Long Term Follow-up"
            )
            | (final_responseBRT_primary_df["Event Label"] == "Primary Retreatment")
            | (final_responseBRT_primary_df["Event Label"] == "Pre-Retreatment"),
            "PET-Based NHL Disease Response (ig_RS3.RSNHLPETCAT)",
        ] = "Transitioned to Retreatment"
        final_responseBRT_primary_df.loc[
            (
                final_responseBRT_primary_df["Event Label"]
                == "Retreatment Long Term Follow-up"
            )
            | (final_responseBRT_primary_df["Event Label"] == "Primary Retreatment")
            | (final_responseBRT_primary_df["Event Label"] == "Pre-Retreatment"),
            "CT-Based NHL Disease Response (ig_RS3.RSNHLCTCAT)",
        ] = "Transitioned to Retreatment"
        final_responseBRT_primary_df.loc[
            (
                final_responseBRT_primary_df["Event Label"]
                == "Retreatment Long Term Follow-up"
            )
            | (final_responseBRT_primary_df["Event Label"] == "Primary Retreatment")
            | (final_responseBRT_primary_df["Event Label"] == "Pre-Retreatment"),
            "Primary Treatment Time Point (ig_RS1.RSTPT)",
        ] = "Transitioned to Retreatment"

    with pd.ExcelWriter(
        output_dir + "/" + output_file_name + ".xlsx", engine="xlsxwriter"
    ) as writer:
        # Get the workbook
        workbook = writer.book
        # Get all format objects from util.py function
        formats = get_named_excel_formats(workbook)
        ## * FORMATING AND COLORING
        # Extract individual formats for easier use
        bold_11_format = formats["bold_11_format"]
        bold_12_format = formats["bold_12_format"]
        bold_12_wrap_format = formats["bold_12_wrap_format"]
        bold_11_wrap_format = formats["bold_11_wrap_format"]
        normal_data_format = formats["normal_data_format"]
        # Create a format for a black cell
        black_cell = writer.book.add_format({"bg_color": "black"})

        # DSMB-Demo Stats Table
        # * WRITING DATA: LegalSex_df, Age_df, Race_df
        final_LegalSex_df.to_excel(
            writer,
            sheet_name="DSMB-Demo Stats Table",
            index=False,
            startcol=1,
            startrow=2,
        )
        final_Age_df.to_excel(
            writer,
            sheet_name="DSMB-Demo Stats Table",
            index=False,
            startcol=1,
            startrow=7,
        )
        final_Race_df.to_excel(
            writer,
            sheet_name="DSMB-Demo Stats Table",
            index=False,
            startcol=1,
            startrow=11,
        )
        # assign worksheet to variable
        worksheet1 = writer.sheets["DSMB-Demo Stats Table"]

        # * FORMAT DATA
        for i in range(0, len(final_LegalSex_df)):
            for j in range(0, len(final_LegalSex_df.columns)):
                worksheet1.write(
                    i + 3, j + 1, final_LegalSex_df.iloc[i, j], normal_data_format
                )
            for k in range(0, 8 - len(final_Age_df.columns)):
                worksheet1.write(
                    i + 3, len(final_Age_df.columns) + k + 1, "", normal_data_format
                )
        for i in range(0, len(final_Age_df)):
            for j in range(0, len(final_Age_df.columns)):
                worksheet1.write(
                    i + 8, j + 1, final_Age_df.iloc[i, j], normal_data_format
                )
            for k in range(0, 8 - len(final_Age_df.columns)):
                worksheet1.write(
                    i + 8, len(final_Age_df.columns) + k + 1, "", normal_data_format
                )
        for i in range(0, len(final_Race_df)):
            for j in range(0, len(final_Race_df.columns)):
                worksheet1.write(
                    i + 12, j + 1, final_Race_df.iloc[i, j], normal_data_format
                )
            for k in range(0, 8 - len(final_Age_df.columns)):
                worksheet1.write(
                    i + 12, len(final_Age_df.columns) + k + 1, "", normal_data_format
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
        for i in range(0, len(Sex_order)):
            worksheet1.write(i + 3, 0, Sex_order[i], bold_11_format)
        for i in range(0, len(Age_order)):
            worksheet1.write(i + 8, 0, Age_order[i], bold_11_format)
        for i in range(0, len(Race_order)):
            worksheet1.write(i + 12, 0, Race_order[i], bold_11_format)

        worksheet1.merge_range("D1:E1", "Cohort A (NHL)", bold_12_format)
        worksheet1.merge_range("F1:G1", "Cohort B (CLL)", bold_12_format)
        worksheet1.merge_range("H1:I1", "Cohort C (ALL)", bold_12_format)
        worksheet1.merge_range("J1:K1", "Cohort D (NHL/ALL)", bold_12_format)
        worksheet1.write(1, 0, "Status", bold_11_format)
        worksheet1.write(
            1,
            1,
            "Total Screened\nN=" + str(final_status["Total Screened"]),
            bold_11_wrap_format,
        )
        worksheet1.write(
            1,
            2,
            "Screen Failed\nN=" + str(final_status["Screen Failed"]),
            bold_11_wrap_format,
        )
        worksheet1.write(
            1,
            3,
            "Eligible\nN=" + str(final_status["Cohort A Enrolled"]),
            bold_11_wrap_format,
        )
        worksheet1.write(
            1,
            4,
            "Infused\nN=" + str(final_status["Cohort A Infused"]),
            bold_11_wrap_format,
        )
        worksheet1.write(
            1,
            5,
            "Eligible\nN=" + str(final_status["Cohort B Enrolled"]),
            bold_11_wrap_format,
        )
        worksheet1.write(
            1,
            6,
            "Infused\nN=" + str(final_status["Cohort B Infused"]),
            bold_11_wrap_format,
        )
        worksheet1.write(
            1,
            7,
            "Eligible\nN=" + str(final_status["Cohort C Enrolled"]),
            bold_11_wrap_format,
        )
        worksheet1.write(
            1,
            8,
            "Infused\nN=" + str(final_status["Cohort C Infused"]),
            bold_11_wrap_format,
        )
        worksheet1.write(
            1,
            9,
            "Eligible\nN=" + str(final_status["Cohort D Enrolled"]),
            bold_11_wrap_format,
        )
        worksheet1.write(
            1,
            10,
            "Infused\nN=" + str(final_status["Cohort D Infused"]),
            bold_11_wrap_format,
        )
        worksheet1.merge_range("A3:K3", "Legal Sex", bold_11_format)
        worksheet1.merge_range("A8:K8", "Age at Consent", bold_11_format)
        worksheet1.merge_range("A12:K12", "Race", bold_11_format)

        # ===== NEW CODE: Write Cohort D only and Cohorts A,B,C tables side-by-side =====

        # Calculate starting positions
        # Original table spans columns A-K (0-10), so 11 columns total
        original_table_width = 11  # A to K
        gap_columns = 1  # One empty column between tables

        # Cohort D table starts after original + gap
        cohort_d_start_col = original_table_width + gap_columns  # Column M (index 12)

        # Cohort D table width (same structure as original but fewer columns)
        # Total Screened, Screen Failed, Enrolled, Infused = 4 columns + row header = 5 columns
        cohort_d_width = 5  # Adjust based on actual D-only table structure

        # Cohorts ABC table starts after Cohort D + gap
        cohorts_abc_start_col = cohort_d_start_col + cohort_d_width + gap_columns

        # ===== Write Cohort D Only Table =====

        # Write the data
        final_LegalSex_df_D.to_excel(
            writer,
            sheet_name="DSMB-Demo Stats Table",
            index=False,
            startcol=cohort_d_start_col + 1,
            startrow=2,
        )
        final_Age_df_D.to_excel(
            writer,
            sheet_name="DSMB-Demo Stats Table",
            index=False,
            startcol=cohort_d_start_col + 1,
            startrow=7,
        )
        final_Race_df_D.to_excel(
            writer,
            sheet_name="DSMB-Demo Stats Table",
            index=False,
            startcol=cohort_d_start_col + 1,
            startrow=11,
        )

        # Format Cohort D data
        for i in range(0, len(final_LegalSex_df_D)):
            for j in range(0, len(final_LegalSex_df_D.columns)):
                worksheet1.write(
                    i + 3,
                    j + cohort_d_start_col + 1,
                    final_LegalSex_df_D.iloc[i, j],
                    normal_data_format,
                )
            # Fill empty cells if needed
            for k in range(len(final_LegalSex_df_D.columns), 4):
                worksheet1.write(
                    i + 3, k + cohort_d_start_col + 1, "", normal_data_format
                )

        for i in range(0, len(final_Age_df_D)):
            for j in range(0, len(final_Age_df_D.columns)):
                worksheet1.write(
                    i + 8,
                    j + cohort_d_start_col + 1,
                    final_Age_df_D.iloc[i, j],
                    normal_data_format,
                )
            for k in range(len(final_Age_df_D.columns), 4):
                worksheet1.write(
                    i + 8, k + cohort_d_start_col + 1, "", normal_data_format
                )

        for i in range(0, len(final_Race_df_D)):
            for j in range(0, len(final_Race_df_D.columns)):
                worksheet1.write(
                    i + 12,
                    j + cohort_d_start_col + 1,
                    final_Race_df_D.iloc[i, j],
                    normal_data_format,
                )
            for k in range(len(final_Race_df_D.columns), 4):
                worksheet1.write(
                    i + 12, k + cohort_d_start_col + 1, "", normal_data_format
                )

        # Write Cohort D headers
        # Row labels (Sex, Age, Race categories)
        for i in range(0, len(Sex_order)):
            worksheet1.write(i + 3, cohort_d_start_col, Sex_order[i], bold_11_format)
        for i in range(0, len(Age_order)):
            worksheet1.write(i + 8, cohort_d_start_col, Age_order[i], bold_11_format)
        for i in range(0, len(Race_order)):
            worksheet1.write(i + 12, cohort_d_start_col, Race_order[i], bold_11_format)

        # Column headers for Cohort D
        d_end_col = cohort_d_start_col + 4  # Adjust based on actual columns
        worksheet1.merge_range(
            0, cohort_d_start_col, 0, d_end_col, "Cohort D (NHL/ALL)", bold_12_format
        )
        worksheet1.write(1, cohort_d_start_col, "Status", bold_11_format)
        worksheet1.write(
            1,
            cohort_d_start_col + 1,
            f"Total Screened\nN={final_status_D['Total Screened']}",
            bold_11_wrap_format,
        )
        worksheet1.write(
            1,
            cohort_d_start_col + 2,
            f"Screen Failed\nN={final_status_D['Screen Failed']}",
            bold_11_wrap_format,
        )
        worksheet1.write(
            1,
            cohort_d_start_col + 3,
            f"Eligible\nN={final_status_D['Cohort D Enrolled']}",
            bold_11_wrap_format,
        )
        worksheet1.write(
            1,
            cohort_d_start_col + 4,
            f"Infused\nN={final_status_D['Cohort D Infused']}",
            bold_11_wrap_format,
        )

        # Section headers for Cohort D
        worksheet1.merge_range(
            2, cohort_d_start_col, 2, d_end_col, "Legal Sex", bold_11_format
        )
        worksheet1.merge_range(
            7, cohort_d_start_col, 7, d_end_col, "Age at Consent", bold_11_format
        )
        worksheet1.merge_range(
            11, cohort_d_start_col, 11, d_end_col, "Race", bold_11_format
        )

        # ===== Write Cohorts A, B, C Combined Table =====

        # Write the data
        final_LegalSex_df_ABC.to_excel(
            writer,
            sheet_name="DSMB-Demo Stats Table",
            index=False,
            startcol=cohorts_abc_start_col + 1,
            startrow=2,
        )
        final_Age_df_ABC.to_excel(
            writer,
            sheet_name="DSMB-Demo Stats Table",
            index=False,
            startcol=cohorts_abc_start_col + 1,
            startrow=7,
        )
        final_Race_df_ABC.to_excel(
            writer,
            sheet_name="DSMB-Demo Stats Table",
            index=False,
            startcol=cohorts_abc_start_col + 1,
            startrow=11,
        )

        # Format Cohorts ABC data
        for i in range(0, len(final_LegalSex_df_ABC)):
            for j in range(0, len(final_LegalSex_df_ABC.columns)):
                worksheet1.write(
                    i + 3,
                    j + cohorts_abc_start_col + 1,
                    final_LegalSex_df_ABC.iloc[i, j],
                    normal_data_format,
                )
            # Fill empty cells if columns are fewer than expected
            for k in range(len(final_LegalSex_df_ABC.columns), 8):
                worksheet1.write(
                    i + 3, k + cohorts_abc_start_col + 1, "", normal_data_format
                )

        for i in range(0, len(final_Age_df_ABC)):
            for j in range(0, len(final_Age_df_ABC.columns)):
                worksheet1.write(
                    i + 8,
                    j + cohorts_abc_start_col + 1,
                    final_Age_df_ABC.iloc[i, j],
                    normal_data_format,
                )
            for k in range(len(final_Age_df_ABC.columns), 8):
                worksheet1.write(
                    i + 8, k + cohorts_abc_start_col + 1, "", normal_data_format
                )

        for i in range(0, len(final_Race_df_ABC)):
            for j in range(0, len(final_Race_df_ABC.columns)):
                worksheet1.write(
                    i + 12,
                    j + cohorts_abc_start_col + 1,
                    final_Race_df_ABC.iloc[i, j],
                    normal_data_format,
                )
            for k in range(len(final_Race_df_ABC.columns), 8):
                worksheet1.write(
                    i + 12, k + cohorts_abc_start_col + 1, "", normal_data_format
                )

        # Write Cohorts ABC headers
        # Row labels (Sex, Age, Race categories)
        for i in range(0, len(Sex_order)):
            worksheet1.write(i + 3, cohorts_abc_start_col, Sex_order[i], bold_11_format)
        for i in range(0, len(Age_order)):
            worksheet1.write(i + 8, cohorts_abc_start_col, Age_order[i], bold_11_format)
        for i in range(0, len(Race_order)):
            worksheet1.write(
                i + 12, cohorts_abc_start_col, Race_order[i], bold_11_format
            )

        # Column headers for Cohorts ABC
        worksheet1.write(1, cohorts_abc_start_col, "Status", bold_11_format)
        worksheet1.write(
            1,
            cohorts_abc_start_col + 1,
            f"Total Screened\nN={final_status_ABC['Total Screened']}",
            bold_11_wrap_format,
        )
        worksheet1.write(
            1,
            cohorts_abc_start_col + 2,
            f"Screen Failed\nN={final_status_ABC['Screen Failed']}",
            bold_11_wrap_format,
        )

        # Cohort-specific headers for A, B, C
        worksheet1.merge_range(
            0,
            cohorts_abc_start_col + 3,
            0,
            cohorts_abc_start_col + 4,
            "Cohort A (NHL)",
            bold_12_format,
        )
        worksheet1.write(
            1,
            cohorts_abc_start_col + 3,
            f"Eligible\nN={final_status_ABC['Cohort A Enrolled']}",
            bold_11_wrap_format,
        )
        worksheet1.write(
            1,
            cohorts_abc_start_col + 4,
            f"Infused\nN={final_status_ABC['Cohort A Infused']}",
            bold_11_wrap_format,
        )

        worksheet1.merge_range(
            0,
            cohorts_abc_start_col + 5,
            0,
            cohorts_abc_start_col + 6,
            "Cohort B (CLL)",
            bold_12_format,
        )
        worksheet1.write(
            1,
            cohorts_abc_start_col + 5,
            f"Eligible\nN={final_status_ABC['Cohort B Enrolled']}",
            bold_11_wrap_format,
        )
        worksheet1.write(
            1,
            cohorts_abc_start_col + 6,
            f"Infused\nN={final_status_ABC['Cohort B Infused']}",
            bold_11_wrap_format,
        )

        worksheet1.merge_range(
            0,
            cohorts_abc_start_col + 7,
            0,
            cohorts_abc_start_col + 8,
            "Cohort C (ALL)",
            bold_12_format,
        )
        worksheet1.write(
            1,
            cohorts_abc_start_col + 7,
            f"Eligible\nN={final_status_ABC['Cohort C Enrolled']}",
            bold_11_wrap_format,
        )
        worksheet1.write(
            1,
            cohorts_abc_start_col + 8,
            f"Infused\nN={final_status_ABC['Cohort C Infused']}",
            bold_11_wrap_format,
        )

        # Section headers for Cohorts ABC
        abc_end_col = cohorts_abc_start_col + 8
        worksheet1.merge_range(
            2, cohorts_abc_start_col, 2, abc_end_col, "Legal Sex", bold_11_format
        )
        worksheet1.merge_range(
            7, cohorts_abc_start_col, 7, abc_end_col, "Age at Consent", bold_11_format
        )
        worksheet1.merge_range(
            11, cohorts_abc_start_col, 11, abc_end_col, "Race", bold_11_format
        )

        # Now call autofit after all tables are written
        worksheet1.autofit()

        # Enrollment Listing
        # * WRITING DATA: enrollment_df
        final_enrollment_df.to_excel(
            writer, sheet_name="DSMB-Enrollment Listing", index=False, startcol=0
        )
        # assign worksheet to variable
        worksheet2 = writer.sheets["DSMB-Enrollment Listing"]

        # * FORMAT DATA
        for i in range(0, len(final_enrollment_df)):
            for j in range(0, len(final_enrollment_df.columns)):
                worksheet2.write(
                    i + 1, j, final_enrollment_df.iloc[i, j], normal_data_format
                )
        # Autofit
        worksheet2.autofit()

        # DSMB-New Infusion Statistics
        # * WRITING DATA: new_infusion_df
        final_infusion_statA.to_excel(
            writer,
            sheet_name="DSMB-New Infusion Statistics",
            index=False,
            startrow=2,
            startcol=0,
        )
        final_infusion_statB.to_excel(
            writer,
            sheet_name="DSMB-New Infusion Statistics",
            index=False,
            startrow=6,
            startcol=0,
        )
        final_infusion_statC.to_excel(
            writer,
            sheet_name="DSMB-New Infusion Statistics",
            index=False,
            startrow=10,
            startcol=0,
        )
        final_infusion_statD.to_excel(
            writer,
            sheet_name="DSMB-New Infusion Statistics",
            index=False,
            startrow=14,
            startcol=0,
        )
        # assign worksheet to variable
        worksheet3 = writer.sheets["DSMB-New Infusion Statistics"]

        # * FORMATING DATA
        for i in range(0, len(final_infusion_statA)):
            for j in range(0, len(final_infusion_statA.columns)):
                worksheet3.write(
                    i + 3, j + 1, final_infusion_statA.iloc[i, j], normal_data_format
                )
        for i in range(0, len(final_infusion_statB)):
            for j in range(0, len(final_infusion_statB.columns)):
                worksheet3.write(
                    i + 7, j + 1, final_infusion_statB.iloc[i, j], normal_data_format
                )
        for i in range(0, len(final_infusion_statC)):
            for j in range(0, len(final_infusion_statC.columns)):
                worksheet3.write(
                    i + 11, j + 1, final_infusion_statC.iloc[i, j], normal_data_format
                )
        for i in range(0, len(final_infusion_statD)):
            for j in range(0, len(final_infusion_statD.columns)):
                worksheet3.write(
                    i + 15, j + 1, final_infusion_statD.iloc[i, j], normal_data_format
                )
        # * WRITING HEADER AND FORMATTING
        stat_order = ["Mean SD", "Median", "Range"]

        worksheet3.merge_range("B1:D1", "Cells Infused", bold_12_wrap_format)
        worksheet3.merge_range("E1:F1", "Transduction Efficiency", bold_12_wrap_format)
        worksheet3.write("B2", "Total Cells", bold_12_wrap_format)
        worksheet3.write("C2", "huCART19-IL18 Cells", bold_12_wrap_format)
        worksheet3.write("D2", "Met Target Dose", bold_12_wrap_format)
        worksheet3.write("E2", "%scFv Flow", bold_12_wrap_format)
        worksheet3.write("F2", "Met Target %scFv", bold_12_wrap_format)
        # Cohort headers with counts
        cohort_a_count = infusion_count[0] if len(infusion_count) > 0 else 0
        cohort_b_count = infusion_count[1] if len(infusion_count) > 1 else 0
        cohort_c_count = infusion_count[2] if len(infusion_count) > 2 else 0
        cohort_d_count = infusion_count[3] if len(infusion_count) > 3 else 0

        worksheet3.merge_range(
            "A3:F3", f"Cohort A (N={cohort_a_count})", bold_12_wrap_format
        )
        worksheet3.merge_range(
            "A7:F7", f"Cohort B (N={cohort_b_count})", bold_12_wrap_format
        )
        worksheet3.merge_range(
            "A11:F11", f"Cohort C (N={cohort_c_count})", bold_12_wrap_format
        )
        worksheet3.merge_range(
            "A15:F15", f"Cohort D (N={cohort_d_count})", bold_12_wrap_format
        )

        # Merge and format "Met Target" data cells
        if len(final_infusion_statA) > 0:
            worksheet3.merge_range(
                "D4:D6", final_infusion_statA.iloc[0, 2], normal_data_format
            )
            worksheet3.merge_range(
                "F4:F6", final_infusion_statA.iloc[0, 4], normal_data_format
            )

        if len(final_infusion_statB) > 0:
            worksheet3.merge_range(
                "D8:D10", final_infusion_statB.iloc[0, 2], normal_data_format
            )
            worksheet3.merge_range(
                "F8:F10", final_infusion_statB.iloc[0, 4], normal_data_format
            )

        if len(final_infusion_statC) > 0:
            worksheet3.merge_range(
                "D12:D14", final_infusion_statC.iloc[0, 2], normal_data_format
            )
            worksheet3.merge_range(
                "F12:F14", final_infusion_statC.iloc[0, 4], normal_data_format
            )

        if len(final_infusion_statD) > 0:
            worksheet3.merge_range(
                "D16:D18", final_infusion_statD.iloc[0, 2], normal_data_format
            )
            worksheet3.merge_range(
                "F16:F18", final_infusion_statD.iloc[0, 4], normal_data_format
            )

        # Row labels for all cohorts
        for i in range(0, len(stat_order)):
            worksheet3.write(i + 3, 0, stat_order[i], bold_11_format)  # Cohort A
            worksheet3.write(i + 7, 0, stat_order[i], bold_11_format)  # Cohort B
            worksheet3.write(i + 11, 0, stat_order[i], bold_11_format)  # Cohort C
            worksheet3.write(i + 15, 0, stat_order[i], bold_11_format)  # Cohort D

        # * Autofit
        worksheet3.autofit()

        # DSMB-Infusion Listing
        # * WRITING DATA: infusion_df, infusionR_df
        final_infusion_df.to_excel(
            writer,
            sheet_name="DSMB-Infusion Listing",
            index=False,
            startrow=1,
            startcol=0,
        )
        final_infusionR_df.to_excel(
            writer,
            sheet_name="DSMB-Infusion Listing",
            index=False,
            startrow=1,
            startcol=14,
        )
        # assign worksheet to variable
        worksheet4 = writer.sheets["DSMB-Infusion Listing"]
        # * FORMATING DATA
        for i in range(0, len(final_infusion_df)):
            for j in range(0, len(final_infusion_df.columns)):
                worksheet4.write(
                    i + 2, j, final_infusion_df.iloc[i, j], normal_data_format
                )
        for i in range(0, len(final_infusionR_df)):
            for j in range(0, len(final_infusionR_df.columns)):
                worksheet4.write(
                    i + 2, j + 14, final_infusionR_df.iloc[i, j], normal_data_format
                )
        # * WRITING HEADER AND FORMATTING
        worksheet4.merge_range("A1:A2", "Subject ID", bold_12_wrap_format)
        worksheet4.merge_range("B1:B2", "Study Day (Primary)", bold_12_wrap_format)
        worksheet4.merge_range("C1:C2", "Cohort Assignment", bold_12_wrap_format)
        worksheet4.merge_range("D1:D2", "Dose Level Assignment", bold_12_wrap_format)
        worksheet4.merge_range(
            "E1:E2", "Lymphodepleting Chemotherapy Regimen", bold_12_wrap_format
        )
        worksheet4.merge_range(
            "F1:F2", "Date of huCART19-IL18 Infusion", bold_12_wrap_format
        )
        worksheet4.merge_range("G1:J1", "Cells Infused", bold_12_wrap_format)
        worksheet4.merge_range("K1:L1", "Transduction Efficiency", bold_12_wrap_format)

        worksheet4.merge_range("O1:O2", "Subject ID", bold_12_wrap_format)
        worksheet4.merge_range("P1:P2", "Study Day (Retreatment)", bold_12_wrap_format)
        worksheet4.merge_range("Q1:Q2", "Cohort Assignment", bold_12_wrap_format)
        worksheet4.merge_range(
            "R1:R2", "Lymphodepleting Chemotherapy Regimen", bold_12_wrap_format
        )
        worksheet4.merge_range(
            "S1:S2", "Date of huCART19-IL18 Retreatment Infusion", bold_12_wrap_format
        )
        worksheet4.merge_range("T1:U1", "Cells Infused", bold_12_wrap_format)
        worksheet4.merge_range("V1:W1", "Transduction Efficiency", bold_12_wrap_format)

        # Autofit
        worksheet4.autofit()

        # DSMB-Response Stats
        # * WRITING DATA
        # Safety Data
        final_safety_df.to_excel(
            writer,
            sheet_name="Cohorts ABC Response Stats",
            index=False,
            startrow=2,
            startcol=1,
        )
        # Response Data Cohort A
        if final_subject_A_prim_count > 0:
            final_response_stat_A_BOR_PET.to_excel(
                writer,
                sheet_name="Cohorts ABC Response Stats",
                index=False,
                startrow=10,
                startcol=1,
            )
            final_response_stat_A_BOR_CT.to_excel(
                writer,
                sheet_name="Cohorts ABC Response Stats",
                index=False,
                startrow=10,
                startcol=3,
            )
            final_response_stat_A_ORR_PET.to_excel(
                writer,
                sheet_name="Cohorts ABC Response Stats",
                index=False,
                startrow=17,
                startcol=1,
            )
            final_response_stat_A_ORR_CT.to_excel(
                writer,
                sheet_name="Cohorts ABC Response Stats",
                index=False,
                startrow=17,
                startcol=3,
            )
        # Resposne Data Cohort B
        if final_subject_B_prim_count > 0:
            final_response_stat_B_BOR_OV.to_excel(
                writer,
                sheet_name="Cohorts ABC Response Stats",
                index=False,
                startrow=10,
                startcol=5,
            )
            final_response_stat_B_BOR_BM.to_excel(
                writer,
                sheet_name="Cohorts ABC Response Stats",
                index=False,
                startrow=10,
                startcol=7,
            )
            final_response_stat_B_ORR_OV.to_excel(
                writer,
                sheet_name="Cohorts ABC Response Stats",
                index=False,
                startrow=17,
                startcol=5,
            )
            final_response_stat_B_ORR_BM.to_excel(
                writer,
                sheet_name="Cohorts ABC Response Stats",
                index=False,
                startrow=17,
                startcol=7,
            )
        # Resposne Data Cohort C

        # assign worksheet to variable
        worksheet5 = writer.sheets["Cohorts ABC Response Stats"]

        # * FORMATING DATA
        # Safety Data
        for i in range(0, len(final_safety_df)):
            for j in range(0, len(final_safety_df.columns)):
                worksheet5.write(
                    i + 3, j + 1, final_safety_df.iloc[i, j], normal_data_format
                )
        # Response Data Cohort A
        for i in range(0, len(final_response_stat_A_BOR_PET)):
            for j in range(0, len(final_response_stat_A_BOR_PET.columns)):
                worksheet5.write(
                    i + 11,
                    j + 1,
                    final_response_stat_A_BOR_PET.iloc[i, j],
                    normal_data_format,
                )
        for i in range(0, len(final_response_stat_A_BOR_CT)):
            for j in range(0, len(final_response_stat_A_BOR_CT.columns)):
                worksheet5.write(
                    i + 11,
                    j + 3,
                    final_response_stat_A_BOR_CT.iloc[i, j],
                    normal_data_format,
                )
        for i in range(0, len(final_response_stat_A_ORR_PET)):
            for j in range(0, len(final_response_stat_A_ORR_PET.columns)):
                worksheet5.write(
                    i + 18,
                    j + 1,
                    final_response_stat_A_ORR_PET.iloc[i, j],
                    normal_data_format,
                )
        for i in range(0, len(final_response_stat_A_ORR_CT)):
            for j in range(0, len(final_response_stat_A_ORR_CT.columns)):
                worksheet5.write(
                    i + 18,
                    j + 3,
                    final_response_stat_A_ORR_CT.iloc[i, j],
                    normal_data_format,
                )
        if final_subject_B_prim_count == 0:
            for i in range(0, 6):
                worksheet5.write(i + 11, 5, "0 (0%)", normal_data_format)
                worksheet5.write(i + 11, 7, "0 (0%)", normal_data_format)
                worksheet5.write(i + 18, 5, "0 (0%)", normal_data_format)
                worksheet5.write(i + 18, 7, "0 (0%)", normal_data_format)
        elif final_subject_B_prim_count > 0:
            # Response Data Cohort B
            for i in range(0, len(final_response_stat_B_BOR_OV)):
                for j in range(0, len(final_response_stat_B_BOR_OV.columns)):
                    worksheet5.write(
                        i + 11,
                        j + 5,
                        final_response_stat_B_BOR_OV.iloc[i, j],
                        normal_data_format,
                    )
            for i in range(0, len(final_response_stat_B_BOR_BM)):
                for j in range(0, len(final_response_stat_B_BOR_BM.columns)):
                    worksheet5.write(
                        i + 11,
                        j + 7,
                        final_response_stat_B_BOR_BM.iloc[i, j],
                        normal_data_format,
                    )
            for i in range(0, len(final_response_stat_B_ORR_OV)):
                for j in range(0, len(final_response_stat_B_ORR_OV.columns)):
                    worksheet5.write(
                        i + 18,
                        j + 5,
                        final_response_stat_B_ORR_OV.iloc[i, j],
                        normal_data_format,
                    )
            for i in range(0, len(final_response_stat_B_ORR_BM)):
                for j in range(0, len(final_response_stat_B_ORR_BM.columns)):
                    worksheet5.write(
                        i + 18,
                        j + 7,
                        final_response_stat_B_ORR_BM.iloc[i, j],
                        normal_data_format,
                    )
        if final_subject_C_prim_count == 0:
            for i in range(0, 6):
                worksheet5.write(i + 11, 9, "0 (0%)", normal_data_format)
                worksheet5.write(i + 11, 11, "0 (0%)", normal_data_format)
                worksheet5.write(i + 18, 9, "0 (0%)", normal_data_format)
                worksheet5.write(i + 18, 11, "0 (0%)", normal_data_format)
        elif final_subject_C_prim_count > 0:
            # Response Data Cohort C
            for i in range(0, len(final_response_stat_C_BOR_OV)):
                for j in range(0, len(final_response_stat_C_BOR_OV.columns)):
                    worksheet5.write(
                        i + 11,
                        j + 9,
                        final_response_stat_C_BOR_OV.iloc[i, j],
                        normal_data_format,
                    )
            for i in range(0, len(final_response_stat_C_BOR_ED)):
                for j in range(0, len(final_response_stat_C_BOR_ED.columns)):
                    worksheet5.write(
                        i + 11,
                        j + 11,
                        final_response_stat_C_BOR_ED.iloc[i, j],
                        normal_data_format,
                    )
            for i in range(0, len(final_response_stat_C_ORR_OV)):
                for j in range(0, len(final_response_stat_C_ORR_OV.columns)):
                    worksheet5.write(
                        i + 18,
                        j + 9,
                        final_response_stat_C_ORR_OV.iloc[i, j],
                        normal_data_format,
                    )
            for i in range(0, len(final_response_stat_C_ORR_ED)):
                for j in range(0, len(final_response_stat_C_ORR_ED.columns)):
                    worksheet5.write(
                        i + 18,
                        j + 11,
                        final_response_stat_C_ORR_ED.iloc[i, j],
                        normal_data_format,
                    )
        if final_subject_BRT_prim_count == 0:
            for i in range(0, 6):
                worksheet5.write(i + 28, 1, "0 (0%)", normal_data_format)
                worksheet5.write(i + 28, 3, "0 (0%)", normal_data_format)
                worksheet5.write(i + 35, 1, "0 (0%)", normal_data_format)
                worksheet5.write(i + 35, 3, "0 (0%)", normal_data_format)
        elif final_subject_BRT_prim_count > 0:
            # Response Data Cohort B- RT
            for i in range(0, len(final_response_stat_BRT_BOR_PET)):
                for j in range(0, len(final_response_stat_BRT_BOR_PET.columns)):
                    worksheet5.write(
                        i + 28,
                        j + 1,
                        final_response_stat_BRT_BOR_PET.iloc[i, j],
                        normal_data_format,
                    )
            for i in range(0, len(final_response_stat_BRT_BOR_CT)):
                for j in range(0, len(final_response_stat_BRT_BOR_CT.columns)):
                    worksheet5.write(
                        i + 28,
                        j + 3,
                        final_response_stat_BRT_BOR_CT.iloc[i, j],
                        normal_data_format,
                    )
            for i in range(0, len(final_response_stat_BRT_ORR_PET)):
                for j in range(0, len(final_response_stat_BRT_ORR_PET.columns)):
                    worksheet5.write(
                        i + 35,
                        j + 1,
                        final_response_stat_BRT_ORR_PET.iloc[i, j],
                        normal_data_format,
                    )
            for i in range(0, len(final_response_stat_BRT_ORR_CT)):
                for j in range(0, len(final_response_stat_BRT_ORR_CT.columns)):
                    worksheet5.write(
                        i + 35,
                        j + 3,
                        final_response_stat_BRT_ORR_CT.iloc[i, j],
                        normal_data_format,
                    )
        # * WRITING HEADER AND FORMATTING
        # Safety Headers
        # number of subject of final_safety_total_df
        safety_abc_subject_count = len(abc_infused_df["Subject"].unique())
        worksheet5.merge_range(
            "B1:E1",
            "Safety Statistics - Cohorts A, B, C (N="
            + str(safety_abc_subject_count)
            + ")",
            bold_12_wrap_format,
        )
        worksheet5.merge_range("B2:C2", "Adverse Events", bold_11_format)
        worksheet5.merge_range("D2:E2", "Serious Adverse Events ", bold_11_format)
        worksheet5.write("B3", "Yes", bold_11_format)
        worksheet5.write("C3", "No", bold_11_format)
        worksheet5.write("D3", "Yes", bold_11_format)
        worksheet5.write("E3", "No", bold_11_format)
        worksheet5.write("A4", "All Cohorts", bold_11_format)
        worksheet5.write("A5", "Cohort A", bold_11_format)
        worksheet5.write("A6", "Cohort B", bold_11_format)
        worksheet5.write("A7", "Cohort C", bold_11_format)

        # Response Headers
        worksheet5.merge_range(
            "A9:D9",
            "NHL Subject Response (N=" + str(final_subject_A_prim_count) + ")",
            bold_12_format,
        )
        worksheet5.merge_range(
            "E9:H9",
            "CLL Subject Response (N=" + str(final_subject_B_prim_count) + ")",
            bold_12_format,
        )
        worksheet5.merge_range("I9:L9", "ALL Subject Response", bold_12_format)
        worksheet5.merge_range(
            "A26:D26",
            "Richter's Transformation Subject Response (N="
            + str(final_subject_BRT_prim_count)
            + ")",
            bold_12_format,
        )
        worksheet5.merge_range("A10:B10", "PET-Based Response", bold_11_format)
        worksheet5.merge_range("C10:D10", "CT-Based Response", bold_11_format)
        worksheet5.merge_range("E10:F10", "Overall Response", bold_11_format)
        worksheet5.merge_range("G10:H10", "Bone Marrow Response", bold_11_format)
        if final_subject_C_prim_count > 0:
            worksheet5.merge_range(
                "I10:J10",
                "Overall Response (N=" + str(final_subject_C_prim_OR_count) + ")",
                bold_11_format,
            )
            worksheet5.merge_range(
                "K10:L10",
                "Extramedullary Disease without Bone Marrow Involvement (N="
                + str(final_subject_C_prim_ED_count)
                + ")",
                bold_11_format,
            )
        else:
            worksheet5.merge_range("I10:J10", "Overall Response (N=0)", bold_11_format)
            worksheet5.merge_range(
                "K10:L10",
                "Extramedullary Disease without Bone Marrow Involvement (N=0)",
                bold_11_format,
            )
        worksheet5.merge_range("A27:B27", "PET-Based Response", bold_11_format)
        worksheet5.merge_range("C27:D27", "CT-Based Response", bold_11_format)
        worksheet5.merge_range("A11:D11", "Best Overall Response (BOR)", bold_11_format)
        worksheet5.merge_range("E11:H11", "Best Overall Response (BOR)", bold_11_format)
        worksheet5.merge_range("I11:L11", "Best Overall Response (BOR)", bold_11_format)
        worksheet5.merge_range("A28:D28", "Best Overall Response (BOR)", bold_11_format)
        worksheet5.merge_range(
            "A18:D18", "Overall Response Rate (ORR) at Month 3", bold_11_format
        )
        worksheet5.merge_range(
            "E18:H18", "Overall Response Rate (ORR) at Month 3", bold_11_format
        )
        worksheet5.merge_range(
            "I18:L18", "Overall Response Rate (ORR) at Day 28", bold_11_format
        )
        worksheet5.merge_range(
            "A35:D35", "Overall Response Rate (ORR) at Month 3", bold_11_format
        )
        # Listing Response Criteria
        response_A_PET = [
            "Complete Metabolic Response (CMR)",
            "Partial Metabolic Response (PMR)",
            "No Metabolic Response (NMR)",
            "Indeterminate Response (IR)",
            "Progressive Metabolic Disease (PMD)",
            "Not Reported",
        ]
        response_A_CT = [
            "Complete Radiologic Response (CR)",
            "Partial Response (PR)",
            "Stable Disease (SD)",
            "Indeterminate Response (IR)",
            "Progressive Disease (PD)",
            "Not Reported",
        ]
        resposne_B_OV = [
            "Complete Remission (CR)",
            "Complete Remission with Incomplete Marrow Recovery (CRi)",
            "Partial Remission (PR)",
            "Stable Disease (SD)",
            "Progressive Disease (PD)",
            "Not Reported",
        ]
        response_B_BM = [
            "Complete Remission (CR)",
            "Partial Remission (PR)",
            "Progressive Disease (PD)",
            "Stable Disease (SD)",
            "Not Reported",
        ]
        response_C_OV = [
            "Complete Remission (CR)",
            "Complete Remission with Incomplete Blood Count Recovery (CRi)",
            "Complete Remission with Residual Mediastinal Disease (CRu)",
            "Treatment Failure (TF)",
            "Relapsed Disease (RD)",
            "Not Reported",
        ]
        response_C_ED = [
            "Complete Remission (CR)",
            "Partial Remission (PR)",
            "Stable Disease (SD)",
            "Indeterminate Response",
            "Progressive Disease (PD)",
            "Not Reported",
        ]
        for i in range(0, len(response_A_PET)):
            worksheet5.write(i + 11, 0, response_A_PET[i], bold_11_format)
            worksheet5.write(i + 18, 0, response_A_PET[i], bold_11_format)
            worksheet5.write(i + 28, 0, response_A_PET[i], bold_11_format)
            worksheet5.write(i + 35, 0, response_A_PET[i], bold_11_format)
        for i in range(0, len(response_A_CT)):
            worksheet5.write(i + 11, 2, response_A_CT[i], bold_11_format)
            worksheet5.write(i + 18, 2, response_A_CT[i], bold_11_format)
            worksheet5.write(i + 28, 2, response_A_CT[i], bold_11_format)
            worksheet5.write(i + 35, 2, response_A_CT[i], bold_11_format)
        for i in range(0, len(resposne_B_OV)):
            worksheet5.write(i + 11, 4, resposne_B_OV[i], bold_11_format)
            worksheet5.write(i + 18, 4, resposne_B_OV[i], bold_11_format)
        for i in range(0, len(response_B_BM)):
            worksheet5.write(i + 11, 6, response_B_BM[i], bold_11_format)
            worksheet5.write(i + 18, 6, response_B_BM[i], bold_11_format)
        worksheet5.write("G17", "black cell", black_cell)
        worksheet5.write("H17", "black cell", black_cell)
        worksheet5.write("G24", "black cell", black_cell)
        worksheet5.write("H24", "black cell", black_cell)
        for i in range(0, len(response_C_OV)):
            worksheet5.write(i + 11, 8, response_C_OV[i], bold_11_format)
            worksheet5.write(i + 18, 8, response_C_OV[i], bold_11_format)
        for i in range(0, len(response_C_ED)):
            worksheet5.write(i + 11, 10, response_C_ED[i], bold_11_format)
            worksheet5.write(i + 18, 10, response_C_ED[i], bold_11_format)

        worksheet5.autofit()

        ## NEW: COHORT D RESPONSE STATS WORKSHEET
        # Create worksheet for Cohort D Response Stats

        # Write Safety Data for Cohort D
        final_safety_D_df.to_excel(
            writer,
            sheet_name="Cohort D Response Stats",
            index=False,
            startrow=2,
            startcol=1,
        )

        # Write NHL Response Data for Cohort D
        if final_subject_D_NHL_count > 0:
            final_response_stat_D_NHL_BOR_PET.to_excel(
                writer,
                sheet_name="Cohort D Response Stats",
                index=False,
                startrow=7,
                startcol=1,
            )
            final_response_stat_D_NHL_BOR_CT.to_excel(
                writer,
                sheet_name="Cohort D Response Stats",
                index=False,
                startrow=7,
                startcol=3,
            )
            final_response_stat_D_NHL_ORR_PET.to_excel(
                writer,
                sheet_name="Cohort D Response Stats",
                index=False,
                startrow=14,
                startcol=1,
            )
            final_response_stat_D_NHL_ORR_CT.to_excel(
                writer,
                sheet_name="Cohort D Response Stats",
                index=False,
                startrow=14,
                startcol=3,
            )

        # Write ALL Response Data for Cohort D (side by side with NHL)
        if final_subject_D_ALL_OR_count > 0 or final_subject_D_ALL_ED_count > 0:
            final_response_stat_D_ALL_BOR_OV.to_excel(
                writer,
                sheet_name="Cohort D Response Stats",
                index=False,
                startrow=7,
                startcol=6,
            )
            final_response_stat_D_ALL_BOR_ED.to_excel(
                writer,
                sheet_name="Cohort D Response Stats",
                index=False,
                startrow=7,
                startcol=8,
            )
            final_response_stat_D_ALL_ORR_OV.to_excel(
                writer,
                sheet_name="Cohort D Response Stats",
                index=False,
                startrow=14,
                startcol=6,
            )
            final_response_stat_D_ALL_ORR_ED.to_excel(
                writer,
                sheet_name="Cohort D Response Stats",
                index=False,
                startrow=14,
                startcol=8,
            )

        # Get worksheet
        worksheet_d_stats = writer.sheets["Cohort D Response Stats"]

        # FORMAT DATA
        # Safety Data
        for i in range(0, len(final_safety_D_df)):
            for j in range(0, len(final_safety_D_df.columns)):
                worksheet_d_stats.write(
                    i + 3, j + 1, final_safety_D_df.iloc[i, j], normal_data_format
                )

        # NHL Response Data
        if final_subject_D_NHL_count > 0:
            for i in range(0, len(final_response_stat_D_NHL_BOR_PET)):
                for j in range(0, len(final_response_stat_D_NHL_BOR_PET.columns)):
                    worksheet_d_stats.write(
                        i + 8,
                        j + 1,
                        final_response_stat_D_NHL_BOR_PET.iloc[i, j],
                        normal_data_format,
                    )
            for i in range(0, len(final_response_stat_D_NHL_BOR_CT)):
                for j in range(0, len(final_response_stat_D_NHL_BOR_CT.columns)):
                    worksheet_d_stats.write(
                        i + 8,
                        j + 3,
                        final_response_stat_D_NHL_BOR_CT.iloc[i, j],
                        normal_data_format,
                    )
            for i in range(0, len(final_response_stat_D_NHL_ORR_PET)):
                for j in range(0, len(final_response_stat_D_NHL_ORR_PET.columns)):
                    worksheet_d_stats.write(
                        i + 15,
                        j + 1,
                        final_response_stat_D_NHL_ORR_PET.iloc[i, j],
                        normal_data_format,
                    )
            for i in range(0, len(final_response_stat_D_NHL_ORR_CT)):
                for j in range(0, len(final_response_stat_D_NHL_ORR_CT.columns)):
                    worksheet_d_stats.write(
                        i + 15,
                        j + 3,
                        final_response_stat_D_NHL_ORR_CT.iloc[i, j],
                        normal_data_format,
                    )
        else:
            # Write zeros if no data
            for i in range(0, 6):
                worksheet_d_stats.write(i + 8, 1, "0 (0%)", normal_data_format)
                worksheet_d_stats.write(i + 8, 3, "0 (0%)", normal_data_format)
                worksheet_d_stats.write(i + 15, 1, "0 (0%)", normal_data_format)
                worksheet_d_stats.write(i + 15, 3, "0 (0%)", normal_data_format)

        # ALL Response Data
        if final_subject_D_ALL_OR_count > 0 or final_subject_D_ALL_ED_count > 0:
            for i in range(0, len(final_response_stat_D_ALL_BOR_OV)):
                for j in range(0, len(final_response_stat_D_ALL_BOR_OV.columns)):
                    worksheet_d_stats.write(
                        i + 8,
                        j + 6,
                        final_response_stat_D_ALL_BOR_OV.iloc[i, j],
                        normal_data_format,
                    )
            for i in range(0, len(final_response_stat_D_ALL_BOR_ED)):
                for j in range(0, len(final_response_stat_D_ALL_BOR_ED.columns)):
                    worksheet_d_stats.write(
                        i + 8,
                        j + 8,
                        final_response_stat_D_ALL_BOR_ED.iloc[i, j],
                        normal_data_format,
                    )
            for i in range(0, len(final_response_stat_D_ALL_ORR_OV)):
                for j in range(0, len(final_response_stat_D_ALL_ORR_OV.columns)):
                    worksheet_d_stats.write(
                        i + 15,
                        j + 6,
                        final_response_stat_D_ALL_ORR_OV.iloc[i, j],
                        normal_data_format,
                    )
            for i in range(0, len(final_response_stat_D_ALL_ORR_ED)):
                for j in range(0, len(final_response_stat_D_ALL_ORR_ED.columns)):
                    worksheet_d_stats.write(
                        i + 15,
                        j + 8,
                        final_response_stat_D_ALL_ORR_ED.iloc[i, j],
                        normal_data_format,
                    )
        else:
            # Write zeros if no data
            for i in range(0, 6):
                worksheet_d_stats.write(i + 8, 6, "0 (0%)", normal_data_format)
                worksheet_d_stats.write(i + 8, 8, "0 (0%)", normal_data_format)
                worksheet_d_stats.write(i + 15, 6, "0 (0%)", normal_data_format)
                worksheet_d_stats.write(i + 15, 8, "0 (0%)", normal_data_format)

        # WRITE HEADERS AND FORMATTING
        # Safety Headers for Cohort D
        safety_d_subject_count = len(d_infused_df["Subject"].unique())
        worksheet_d_stats.merge_range(
            "B1:E1",
            f"Safety Statistics - Cohort D (N={safety_d_subject_count})",
            bold_12_wrap_format,
        )
        worksheet_d_stats.merge_range("B2:C2", "Adverse Events", bold_11_format)
        worksheet_d_stats.merge_range("D2:E2", "Serious Adverse Events", bold_11_format)
        worksheet_d_stats.write("B3", "Yes", bold_11_format)
        worksheet_d_stats.write("C3", "No", bold_11_format)
        worksheet_d_stats.write("D3", "Yes", bold_11_format)
        worksheet_d_stats.write("E3", "No", bold_11_format)
        worksheet_d_stats.write("A4", "Cohort D", bold_11_format)

        # Response Headers
        worksheet_d_stats.merge_range(
            "A6:D6",
            f"NHL Subject Response (N={final_subject_D_NHL_count})",
            bold_12_format,
        )
        worksheet_d_stats.merge_range("F6:I6", "ALL Subject Response", bold_12_format)

        # NHL Headers
        worksheet_d_stats.merge_range("A7:B7", "PET-Based Response", bold_11_format)
        worksheet_d_stats.merge_range("C7:D7", "CT-Based Response", bold_11_format)
        worksheet_d_stats.merge_range(
            "A8:D8", "Best Overall Response (BOR)", bold_11_format
        )
        worksheet_d_stats.merge_range(
            "A15:D15", "Overall Response Rate (ORR) at Month 3", bold_11_format
        )

        # ALL Headers
        worksheet_d_stats.merge_range(
            "F7:G7",
            f"Overall Response (N={final_subject_D_ALL_OR_count})",
            bold_11_format,
        )
        worksheet_d_stats.merge_range(
            "H7:I7",
            f"Extramedullary Disease without Bone Marrow Involvement (N={final_subject_D_ALL_ED_count})",
            bold_11_format,
        )
        worksheet_d_stats.merge_range(
            "F8:I8", "Best Overall Response (BOR)", bold_11_format
        )
        worksheet_d_stats.merge_range(
            "F15:I15", "Overall Response Rate (ORR) at Day 28", bold_11_format
        )

        # Response criteria labels for NHL
        response_D_NHL_PET = [
            "Complete Metabolic Response (CMR)",
            "Partial Metabolic Response (PMR)",
            "No Metabolic Response (NMR)",
            "Indeterminate Response (IR)",
            "Progressive Metabolic Disease (PMD)",
            "Not Reported",
        ]
        response_D_NHL_CT = [
            "Complete Radiologic Response (CR)",
            "Partial Response (PR)",
            "Stable Disease (SD)",
            "Indeterminate Response (IR)",
            "Progressive Disease (PD)",
            "Not Reported",
        ]

        # Response criteria labels for ALL
        response_D_ALL_OV = [
            "Complete Remission (CR)",
            "Complete Remission with Incomplete Blood Count Recovery (CRi)",
            "Complete Remission with Residual Mediastinal Disease (CRu)",
            "Treatment Failure (TF)",
            "Relapsed Disease (RD)",
            "Not Reported",
        ]
        response_D_ALL_ED = [
            "Complete Remission (CR)",
            "Partial Remission (PR)",
            "Stable Disease (SD)",
            "Indeterminate Response",
            "Progressive Disease (PD)",
            "Not Reported",
        ]

        # Write NHL labels
        for i in range(0, len(response_D_NHL_PET)):
            worksheet_d_stats.write(i + 8, 0, response_D_NHL_PET[i], bold_11_format)
            worksheet_d_stats.write(i + 15, 0, response_D_NHL_PET[i], bold_11_format)
        for i in range(0, len(response_D_NHL_CT)):
            worksheet_d_stats.write(i + 8, 2, response_D_NHL_CT[i], bold_11_format)
            worksheet_d_stats.write(i + 15, 2, response_D_NHL_CT[i], bold_11_format)

        # Write ALL labels
        for i in range(0, len(response_D_ALL_OV)):
            worksheet_d_stats.write(i + 8, 5, response_D_ALL_OV[i], bold_11_format)
            worksheet_d_stats.write(i + 15, 5, response_D_ALL_OV[i], bold_11_format)
        for i in range(0, len(response_D_ALL_ED)):
            worksheet_d_stats.write(i + 8, 7, response_D_ALL_ED[i], bold_11_format)
            worksheet_d_stats.write(i + 15, 7, response_D_ALL_ED[i], bold_11_format)

        # Autofit the worksheet
        worksheet_d_stats.autofit()

        # Response Listing NHL
        # * WRITING DATA
        if final_subject_A_prim_count > 0:
            final_responseA_primary_df.to_excel(
                writer,
                sheet_name="Response Listing NHL",
                index=False,
                header=False,
                startrow=3,
                startcol=0,
            )
        if final_subject_A_retx_count > 0:
            final_responseA_retreatment_df.to_excel(
                writer,
                sheet_name="Response Listing NHL",
                index=False,
                header=False,
                startrow=3,
                startcol=15,
            )
        # assigning the worksheet
        worksheet6 = writer.sheets["Response Listing NHL"]
        # * FORMATING DATA
        if final_subject_A_prim_count > 0:
            for i in range(0, len(final_responseA_primary_df)):
                for j in range(0, len(final_responseA_primary_df.columns)):
                    worksheet6.write(
                        i + 3,
                        j,
                        final_responseA_primary_df.iloc[i, j],
                        normal_data_format,
                    )
        if final_subject_A_retx_count > 0:
            for i in range(0, len(final_responseA_retreatment_df)):
                for j in range(0, len(final_responseA_retreatment_df.columns)):
                    worksheet6.write(
                        i + 3,
                        j + 15,
                        final_responseA_retreatment_df.iloc[i, j],
                        normal_data_format,
                    )
        # * WRITING HEADER AND FORMATTING
        if final_subject_A_prim_count > 0:
            worksheet6.merge_range(
                "A1:M1", "Cohort A (NHL)- Primary Follow-up", bold_12_format
            )
            worksheet6.merge_range("A2:A3", "Subject ID", bold_11_format)
            worksheet6.merge_range("B2:D2", "Current Response", bold_11_format)
            worksheet6.merge_range("E2:H2", "Best Response/Timepoint", bold_11_format)
            worksheet6.merge_range("I2:J2", "Overall Response/Month 3", bold_11_format)
            worksheet6.write("B3", "PET-Based Response", bold_11_format)
            worksheet6.write("C3", "CT-Based Response", bold_11_format)
            worksheet6.write("D3", "Study Timepoint", bold_11_format)
            worksheet6.write("E3", "PET-Based Response", bold_11_format)
            worksheet6.write("F3", "Study Timepoint", bold_11_format)
            worksheet6.write("G3", "CT-Based Response", bold_11_format)
            worksheet6.write("H3", "Study Timepoint", bold_11_format)
            worksheet6.write("I3", "PET-Based ORR", bold_11_format)
            worksheet6.write("J3", "CT-Based ORR", bold_11_format)
            worksheet6.merge_range(
                "K2:K3", "Adverse Events \n(Y/N)", bold_11_wrap_format
            )
            worksheet6.merge_range(
                "L2:L3", "Serious Adverse Events \n(Y/N)", bold_11_wrap_format
            )
            worksheet6.merge_range("M2:M3", "Study Status", bold_11_wrap_format)
        if final_subject_A_retx_count > 0:
            worksheet6.merge_range(
                "P1:AB1", "Cohort A (NHL)- Retreatment Follow-up", bold_12_format
            )
            worksheet6.merge_range("P2:P3", "Subject ID", bold_11_format)
            worksheet6.merge_range("Q2:S2", "Current Response", bold_11_format)
            worksheet6.merge_range("T2:W2", "Best Response/Timepoint", bold_11_format)
            worksheet6.merge_range(
                "X2:Y2", "Overall Response/Month 3-R", bold_11_format
            )
            worksheet6.write("Q3", "PET-Based Response", bold_11_format)
            worksheet6.write("R3", "CT-Based Response", bold_11_format)
            worksheet6.write("S3", "Study Timepoint", bold_11_format)
            worksheet6.write("T3", "PET-Based Response", bold_11_format)
            worksheet6.write("U3", "Study Timepoint", bold_11_format)
            worksheet6.write("V3", "CT-Based Response", bold_11_format)
            worksheet6.write("W3", "Study Timepoint", bold_11_format)
            worksheet6.write("X3", "PET-Based ORR", bold_11_format)
            worksheet6.write("Y3", "CT-Based ORR", bold_11_format)
            worksheet6.merge_range(
                "Z2:Z3", "Adverse Events \n(Y/N)", bold_11_wrap_format
            )
            worksheet6.merge_range(
                "AA2:AA3", "Serious Adverse Events \n(Y/N)", bold_11_wrap_format
            )
            worksheet6.merge_range("AB2:AB3", "Study Status", bold_11_wrap_format)
        # Autofit
        worksheet6.autofit()

        # Response Listing CLL
        # * WRITING DATA
        if final_subject_B_prim_count > 0:
            final_responseB_primary_df.to_excel(
                writer,
                sheet_name="Response Listing CLL",
                index=False,
                startrow=2,
                startcol=0,
            )
            worksheet7 = writer.sheets["Response Listing CLL"]
            final_responseB_primary_df = final_responseB_primary_df.replace(
                [np.nan, np.inf, -np.inf], ""
            )
            # * FORMATING DATA
            for i in range(0, len(final_responseB_primary_df)):
                for j in range(0, len(final_responseB_primary_df.columns)):
                    worksheet7.write(
                        i + 3,
                        j,
                        final_responseB_primary_df.iloc[i, j],
                        normal_data_format,
                    )

            # * WRITING HEADER AND FORMATTING
            worksheet7.merge_range(
                "A1:M1", "Cohort B (CLL) - Primary Follow-up", bold_12_format
            )
            worksheet7.merge_range("A2:A3", "Subject ID", bold_11_format)
            worksheet7.merge_range("B2:D2", "Current Response", bold_11_format)
            worksheet7.merge_range("E2:H2", "Best Response/Timepoint", bold_11_format)
            worksheet7.merge_range("I2:J2", "Overall Response/Month 3", bold_11_format)
            worksheet7.write("B3", "Overall Response", bold_11_format)
            worksheet7.write("C3", "Bone Marrow Response", bold_11_format)
            worksheet7.write("D3", "Study Timepoint", bold_11_format)
            worksheet7.write("E3", "Overall Response", bold_11_format)
            worksheet7.write("F3", "Study Timepoint", bold_11_format)
            worksheet7.write("G3", "Bone Marrow Response", bold_11_format)
            worksheet7.write("H3", "Study Timepoint", bold_11_format)
            worksheet7.write("I3", "Overall Response", bold_11_format)
            worksheet7.write("J3", "Bone Marrow Response", bold_11_format)
            worksheet7.merge_range(
                "K2:K3", "Adverse Events \n(Y/N)", bold_11_wrap_format
            )
            worksheet7.merge_range(
                "L2:L3", "Serious Adverse Events \n(Y/N)", bold_11_wrap_format
            )
            worksheet7.merge_range("M2:M3", "Study Status", bold_11_wrap_format)

            if final_subject_B_retx_count > 0:
                final_responseB_retreatment_df.to_excel(
                    writer,
                    sheet_name="Response Listing CLL",
                    index=False,
                    startrow=2,
                    startcol=0,
                )
                # * FORMATING DATA
                for i in range(0, len(final_responseB_retreatment_df)):
                    for j in range(0, len(final_responseB_retreatment_df.columns)):
                        worksheet7.write(
                            i + 3,
                            j + 15,
                            final_responseB_retreatment_df.iloc[i, j],
                            normal_data_format,
                        )

                # * WRITING HEADER AND FORMATTING
                if final_subject_B_retx_count > 0:
                    worksheet7.merge_range(
                        "P1:AB1",
                        "Cohort B (CLL) - Retreatment Follow-up",
                        bold_12_format,
                    )
                    worksheet7.merge_range("P2:P3", "Subject ID", bold_11_format)
                    worksheet7.merge_range("Q2:S2", "Current Response", bold_11_format)
                    worksheet7.merge_range(
                        "T2:W2", "Best Response/Timepoint", bold_11_format
                    )
                    worksheet7.merge_range(
                        "X2:Y2", "Overall Response/Month 3", bold_11_format
                    )
                    worksheet7.write("Q3", "Overall Response", bold_11_format)
                    worksheet7.write("R3", "Bone Marrow Response", bold_11_format)
                    worksheet7.write("S3", "Study Timepoint", bold_11_format)
                    worksheet7.write("T3", "Overall Response", bold_11_format)
                    worksheet7.write("U3", "Study Timepoint", bold_11_format)
                    worksheet7.write("V3", "Bone Marrow Response", bold_11_format)
                    worksheet7.write("W3", "Study Timepoint", bold_11_format)
                    worksheet7.write("X3", "Overall Response", bold_11_format)
                    worksheet7.write("Y3", "Bone Marrow Response", bold_11_format)
                    worksheet7.merge_range(
                        "Z2:Z3", "Adverse Events \n(Y/N)", bold_11_wrap_format
                    )
                    worksheet7.merge_range(
                        "AA2:AA3", "Serious Adverse Events \n(Y/N)", bold_11_wrap_format
                    )
                    worksheet7.merge_range(
                        "AB2:AB3", "Study Status", bold_11_wrap_format
                    )
            # Autofit
            worksheet7.autofit()

        # Response Listing Richter's Transformation
        # * WRITING DATA
        if final_subject_BRT_prim_count > 0:
            final_responseBRT_primary_df.to_excel(
                writer,
                sheet_name="Response Listing Richter",
                index=False,
                header=False,
                startrow=3,
                startcol=0,
            )
            # assigning the worksheet
            worksheet8 = writer.sheets["Response Listing Richter"]
            for i in range(0, len(final_responseBRT_primary_df)):
                for j in range(0, len(final_responseBRT_primary_df.columns)):
                    worksheet8.write(
                        i + 3,
                        j,
                        final_responseBRT_primary_df.iloc[i, j],
                        normal_data_format,
                    )
            worksheet8.merge_range(
                "A1:M1",
                "Cohort B (Richter's Transformation)- Primary Follow-up",
                bold_12_format,
            )
            worksheet8.merge_range("A2:A3", "Subject ID", bold_11_format)
            worksheet8.merge_range("B2:D2", "Current Response", bold_11_format)
            worksheet8.merge_range("E2:H2", "Best Response/Timepoint", bold_11_format)
            worksheet8.merge_range("I2:J2", "Overall Response/Month 3", bold_11_format)
            worksheet8.write("B3", "PET-Based Response", bold_11_format)
            worksheet8.write("C3", "CT-Based Response", bold_11_format)
            worksheet8.write("D3", "Study Timepoint", bold_11_format)
            worksheet8.write("E3", "PET-Based Response", bold_11_format)
            worksheet8.write("F3", "Study Timepoint", bold_11_format)
            worksheet8.write("G3", "CT-Based Response", bold_11_format)
            worksheet8.write("H3", "Study Timepoint", bold_11_format)
            worksheet8.write("I3", "PET-Based ORR", bold_11_format)
            worksheet8.write("J3", "CT-Based ORR", bold_11_format)
            worksheet8.merge_range(
                "K2:K3", "Adverse Events \n(Y/N)", bold_11_wrap_format
            )
            worksheet8.merge_range(
                "L2:L3", "Serious Adverse Events \n(Y/N)", bold_11_wrap_format
            )
            worksheet8.merge_range("M2:M3", "Study Status", bold_11_wrap_format)
            worksheet8.autofit()
        if final_subject_BRT_retx_count > 0:
            final_responseBRT_retreatment_df.to_excel(
                writer,
                sheet_name="Response Listing Richter",
                index=False,
                header=False,
                startrow=3,
                startcol=15,
            )
            for i in range(0, len(final_responseBRT_retreatment_df)):
                for j in range(0, len(final_responseBRT_retreatment_df.columns)):
                    worksheet8.write(
                        i + 3,
                        j + 15,
                        final_responseBRT_retreatment_df.iloc[i, j],
                        normal_data_format,
                    )
            worksheet8.merge_range(
                "P1:AB1", "Cohort A (NHL)- Retreatment Follow-up", bold_12_format
            )
            worksheet8.merge_range("P2:P3", "Subject ID", bold_11_format)
            worksheet8.merge_range("Q2:S2", "Current Response", bold_11_format)
            worksheet8.merge_range("T2:W2", "Best Response/Timepoint", bold_11_format)
            worksheet8.merge_range(
                "X2:Y2", "Overall Response/Month 3-R", bold_11_format
            )
            worksheet8.write("Q3", "PET-Based Response", bold_11_format)
            worksheet8.write("R3", "CT-Based Response", bold_11_format)
            worksheet8.write("S3", "Study Timepoint", bold_11_format)
            worksheet8.write("T3", "PET-Based Response", bold_11_format)
            worksheet8.write("U3", "Study Timepoint", bold_11_format)
            worksheet8.write("V3", "CT-Based Response", bold_11_format)
            worksheet8.write("W3", "Study Timepoint", bold_11_format)
            worksheet8.write("X3", "PET-Based ORR", bold_11_format)
            worksheet8.write("Y3", "CT-Based ORR", bold_11_format)
            worksheet8.merge_range(
                "Z2:Z3", "Adverse Events \n(Y/N)", bold_11_wrap_format
            )
            worksheet8.merge_range(
                "AA2:AA3", "Serious Adverse Events \n(Y/N)", bold_11_wrap_format
            )
            worksheet8.merge_range("AB2:AB3", "Study Status", bold_11_wrap_format)
            worksheet8.autofit()

        # Response Listing ALL
        # * WRITING DATA
        if final_subject_C_prim_count > 0:
            final_responseC_primary_df.to_excel(
                writer,
                sheet_name="Response Listing ALL",
                index=False,
                startrow=2,
                startcol=0,
            )
        if final_subject_C_retx_count > 0:
            final_responseC_retreatment_df.to_excel(
                writer,
                sheet_name="Response Listing ALL",
                index=False,
                startrow=2,
                startcol=15,
            )

        worksheet9 = writer.sheets["Response Listing ALL"]

        # * FORMATING DATA
        if final_subject_C_prim_count > 0:
            for i in range(0, len(final_responseC_primary_df)):
                for j in range(0, len(final_responseC_primary_df.columns)):
                    worksheet9.write(
                        i + 3,
                        j,
                        final_responseC_primary_df.iloc[i, j],
                        normal_data_format,
                    )

        if final_subject_C_retx_count > 0:
            for i in range(0, len(final_responseC_retreatment_df)):
                for j in range(0, len(final_responseC_retreatment_df.columns)):
                    worksheet9.write(
                        i + 3,
                        j + 15,
                        final_responseC_retreatment_df.iloc[i, j],
                        normal_data_format,
                    )

        # * WRITING HEADER AND FORMATTING
        # Primary headers
        if final_subject_C_prim_count > 0:
            worksheet9.merge_range(
                "A1:M1", "Cohort C (ALL) - Primary Follow-up", bold_12_format
            )
            worksheet9.merge_range("A2:A3", "Subject ID", bold_11_format)
            worksheet9.merge_range("B2:D2", "Current Response", bold_11_format)
            worksheet9.merge_range("E2:H2", "Best Response/Timepoint", bold_11_format)
            worksheet9.merge_range("I2:J2", "Overall Response/Day 28", bold_11_format)
            worksheet9.write("B3", "Overall Response", bold_11_format)
            worksheet9.write(
                "C3",
                "Extramedullary Disease without Bone Marrow Involvement",
                bold_11_format,
            )
            worksheet9.write("D3", "Study Timepoint", bold_11_format)
            worksheet9.write("E3", "Overall Response", bold_11_format)
            worksheet9.write("F3", "Study Timepoint", bold_11_format)
            worksheet9.write(
                "G3",
                "Extramedullary Disease without Bone Marrow Involvement",
                bold_11_format,
            )
            worksheet9.write("H3", "Study Timepoint", bold_11_format)
            worksheet9.write("I3", "Overall Response", bold_11_format)
            worksheet9.write(
                "J3",
                "Extramedullary Disease without Bone Marrow Involvement",
                bold_11_format,
            )
            worksheet9.merge_range(
                "K2:K3", "Adverse Events \n(Y/N)", bold_11_wrap_format
            )
            worksheet9.merge_range(
                "L2:L3", "Serious Adverse Events \n(Y/N)", bold_11_wrap_format
            )
            worksheet9.merge_range("M2:M3", "Study Status", bold_11_wrap_format)

        # Retreatment headers (starting at column P)
        if final_subject_C_retx_count > 0:
            worksheet9.merge_range(
                "P1:AB1", "Cohort C (ALL) - Retreatment Follow-up", bold_12_format
            )
            worksheet9.merge_range("P2:P3", "Subject ID", bold_11_format)
            worksheet9.merge_range("Q2:S2", "Current Response", bold_11_format)
            worksheet9.merge_range("T2:W2", "Best Response/Timepoint", bold_11_format)
            worksheet9.merge_range("X2:Y2", "Overall Response/Day 28-R", bold_11_format)
            worksheet9.write("Q3", "Overall Response", bold_11_format)
            worksheet9.write(
                "R3",
                "Extramedullary Disease without Bone Marrow Involvement",
                bold_11_format,
            )
            worksheet9.write("S3", "Study Timepoint", bold_11_format)
            worksheet9.write("T3", "Overall Response", bold_11_format)
            worksheet9.write("U3", "Study Timepoint", bold_11_format)
            worksheet9.write(
                "V3",
                "Extramedullary Disease without Bone Marrow Involvement",
                bold_11_format,
            )
            worksheet9.write("W3", "Study Timepoint", bold_11_format)
            worksheet9.write("X3", "Overall Response", bold_11_format)
            worksheet9.write(
                "Y3",
                "Extramedullary Disease without Bone Marrow Involvement",
                bold_11_format,
            )
            worksheet9.merge_range(
                "Z2:Z3", "Adverse Events \n(Y/N)", bold_11_wrap_format
            )
            worksheet9.merge_range(
                "AA2:AA3", "Serious Adverse Events \n(Y/N)", bold_11_wrap_format
            )
            worksheet9.merge_range("AB2:AB3", "Study Status", bold_11_wrap_format)

        # Autofit
        worksheet9.autofit()

        # * WRITE TO EXCEL
        final_subject_D_ALL_count = (
            final_subject_D_prim_OR_count + final_subject_D_prim_ED_count
        )
        final_subject_D_NHL_count = len(final_responseD_NHL_df["Subject"].unique())
        if final_subject_D_NHL_count > 0 or final_subject_D_ALL_count > 0:
            # Create the worksheet
            if final_subject_D_NHL_count > 0:
                final_responseD_NHL_df.to_excel(
                    writer,
                    sheet_name="Response Listing Cohort D",
                    index=False,
                    header=False,
                    startrow=3,
                    startcol=0,
                )

            if final_subject_D_ALL_count > 0:
                # ALL table starts at column 15 (NHL table is columns 0-12, 2 empty columns 13-14)
                final_responseD_ALL_df.to_excel(
                    writer,
                    sheet_name="Response Listing Cohort D",
                    index=False,
                    header=False,
                    startrow=3,
                    startcol=15,
                )

            # Get the worksheet
            worksheet10 = writer.sheets["Response Listing Cohort D"]

            # * FORMAT DATA
            # Format NHL data
            if final_subject_D_NHL_count > 0:
                for i in range(0, len(final_responseD_NHL_df)):
                    for j in range(0, len(final_responseD_NHL_df.columns)):
                        worksheet10.write(
                            i + 3,
                            j,
                            final_responseD_NHL_df.iloc[i, j],
                            normal_data_format,
                        )

            # Format ALL data
            if final_subject_D_ALL_count > 0:
                for i in range(0, len(final_responseD_ALL_df)):
                    for j in range(0, len(final_responseD_ALL_df.columns)):
                        worksheet10.write(
                            i + 3,
                            j + 15,
                            final_responseD_ALL_df.iloc[i, j],
                            normal_data_format,
                        )

            # * WRITE HEADERS AND FORMATTING

            # NHL Headers (columns A-M)
            worksheet10.merge_range(
                "A1:M1",
                f"Cohort D (NHL) - Primary Follow-up (N={final_subject_D_NHL_count})",
                bold_12_format,
            )
            worksheet10.merge_range("A2:A3", "Subject ID", bold_11_format)
            worksheet10.merge_range("B2:D2", "Current Response", bold_11_format)
            worksheet10.merge_range("E2:H2", "Best Response/Timepoint", bold_11_format)
            worksheet10.merge_range("I2:J2", "Overall Response/Month 3", bold_11_format)
            worksheet10.write("B3", "PET-Based Response", bold_11_format)
            worksheet10.write("C3", "CT-Based Response", bold_11_format)
            worksheet10.write("D3", "Study Timepoint", bold_11_format)
            worksheet10.write("E3", "PET-Based Response", bold_11_format)
            worksheet10.write("F3", "Study Timepoint", bold_11_format)
            worksheet10.write("G3", "CT-Based Response", bold_11_format)
            worksheet10.write("H3", "Study Timepoint", bold_11_format)
            worksheet10.write("I3", "PET-Based ORR", bold_11_format)
            worksheet10.write("J3", "CT-Based ORR", bold_11_format)
            worksheet10.merge_range(
                "K2:K3", "Adverse Events \n(Y/N)", bold_11_wrap_format
            )
            worksheet10.merge_range(
                "L2:L3", "Serious Adverse Events \n(Y/N)", bold_11_wrap_format
            )
            worksheet10.merge_range("M2:M3", "Study Status", bold_11_wrap_format)

            # ALL Headers (starting at column P, which is index 15)
            worksheet10.merge_range(
                "P1:AB1",
                f"Cohort D (ALL) - Primary Follow-up (N={final_subject_D_ALL_count})",
                bold_12_format,
            )
            worksheet10.merge_range("P2:P3", "Subject ID", bold_11_format)
            worksheet10.merge_range("Q2:S2", "Current Response", bold_11_format)
            worksheet10.merge_range("T2:W2", "Best Response/Timepoint", bold_11_format)
            worksheet10.merge_range("X2:Y2", "Overall Response/Day 28", bold_11_format)
            worksheet10.write("Q3", "Overall Response", bold_11_format)
            worksheet10.write(
                "R3",
                "Extramedullary Disease without Bone Marrow Involvement",
                bold_11_format,
            )
            worksheet10.write("S3", "Study Timepoint", bold_11_format)
            worksheet10.write("T3", "Overall Response", bold_11_format)
            worksheet10.write("U3", "Study Timepoint", bold_11_format)
            worksheet10.write(
                "V3",
                "Extramedullary Disease without Bone Marrow Involvement",
                bold_11_format,
            )
            worksheet10.write("W3", "Study Timepoint", bold_11_format)
            worksheet10.write("X3", "Overall Response", bold_11_format)
            worksheet10.write(
                "Y3",
                "Extramedullary Disease without Bone Marrow Involvement",
                bold_11_format,
            )
            worksheet10.merge_range(
                "Z2:Z3", "Adverse Events \n(Y/N)", bold_11_wrap_format
            )
            worksheet10.merge_range(
                "AA2:AA3", "Serious Adverse Events \n(Y/N)", bold_11_wrap_format
            )
            worksheet10.merge_range("AB2:AB3", "Study Status", bold_11_wrap_format)

            # Autofit the worksheet
            worksheet10.autofit()
