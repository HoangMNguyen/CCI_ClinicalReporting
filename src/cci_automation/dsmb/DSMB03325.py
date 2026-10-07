import numpy as np
import pandas as pd

from cci_automation.dsmb.DSMB_util import (
    combine_labs,
    combine_reason,
    convert_float_2_sci_notation,
    fill_na_reason,
    format_date,
    get_stats_df,
    get_stats_perc_df,
    get_stats_percentage,
    get_stats_percentage2,
    pick_last_visit,
)
from cci_automation.util import age_calculation, get_data_from_dict
from clinical_reporting.export import get_named_excel_formats


class DSMB03325:
    def __init__(
        self,
        data,
        output_dir,
        output_file_name,
    ):
        self.data = data
        self.output_dir = output_dir
        self.output_file_name = output_file_name

    def run(self):
        """
        Process the given data and return the processed result.

        Args:
            None

        Returns:
            None
        """
        # process the listings only when Demographics is not empty
        data = self.data
        if not data["DM"].empty:
            # process Demographics Statistics
            self.enrollment_listing_df_output, self.enrollment_listing_df = (
                self.enrollment_listing()
            )
            # process Enrollment Listing
            self.enrollment_stat_table(self.enrollment_listing_df)
            # process the Treatment Listing
            self.infusion_df, self.infusionR_df = self.infusion_listing()
            # process the Treatment Statistics
            self.infusion_stats(self.infusion_df, self.infusionR_df)
            # process EGFR MGMT Listing
            self.EGFR_listing_df_output, _ = self.EGFR_listing()
            # process the Status of Eligible Subjects and Cohort A Safety Statistics
            _, self.status_df, self.safetyCH1_total_df = self.status_listing()
            # process Status of Treated Subjects
            self.TXSUB_status_df = self.TXSUB_status_listing()
            # generate Excel export
            self.export(self.output_dir, self.output_file_name)

    def enrollment_listing(self):
        data = self.data
        # *: PREPARE DATA FOR ENROLLMENT LISTING

        # create dictionary for Enrollment Listing
        input_dict = {
            "DM": {
                "Legal Sex (IG_NS_NA_DM1.CL_NS_YH_SEX_cl_NS_DMSEX1)": "Legal Sex",
                "Sex Assigned at Birth (IG_NS_NA_DM1.CL_NS_NH_BRTHSEX_cl_NS_DMSEX3)": "Sex Assigned at Birth",
                "Gender Identity (IG_NS_NA_DM1.CL_NS_NH_GENDERID_cl_NS_DMSEX2)": "Gender Identity",
                "Specify Other Gender Identity (IG_NS_NA_DM1.TX_NS_NH_GENDERIDOTH)": "Other Gender",
                "Date of Birth (IG_NS_NA_DM1.DT_NS_NH_BRTHDAT)": "Date of Birth",
                "Main Consent Date (IG_NS_NA_DM1.DT_NS_YH_RFICDAT)": "Main Consent Date",
                "Race (IG_NS_NA_DM1.CL_NS_YH_RACE_cl_NS_DMRACE1)": "Race",
                "Specify Other or Multiple Races (IG_NS_NA_DM1.TX_NS_NH_RACEOTH)": "Other Race",
                "Ethnicity (IG_NS_NA_DM1.CL_NS_NH_ETHNIC_cl_NS_DMETHNIC1)": "Ethnicity",
            },
            "DSCA": {
                "Cohort Assignment (IG_NS_NA_DSCA1.CL_NS_YH_CACHASCOD_cl_NS_COHORT1)": "Cohort Assignment"
            },
            "DSDLA": {
                "Dose Level Assignment (IG_NS_NA_DSDLA1.CL_NS_YH_DLADOSELV_cl_NS_DOSELV1)": "Dose Level Assignment"
            },
            "IE": {
                "Event Group Label": "Last Eligibility Step Completed",
                "Subject Meets All Study Eligibility (IG_NS_NA_IE3.CL_NS_YH_ELIGYN_cl_YS_YN1)": "Subject meets all study eligibility?",
                "Other Screen Fail Reason (IG_NS_NA_IE4.TX_NS_YH_OTHRSFREAS)": "SF3",
                "Screen Failure Reason (IG_NS_NA_IE4.CL_NS_YH_IECAT_cl_NS_IEREASSF1)": "Reason for Screen Fail",
                "Select the Primary Inclusion Criterion Excluding this Subject (IG_NS_NA_IE4.CL_NS_NH_ITESTCD_cl_NS_IEINCL1)": "SF1",
                "Select the Primary Exclusion Criterion Excluding this Subject (IG_NS_NA_IE4.CL_NS_NH_ETESTCD_cl_NS_IEEXCL1)": "SF2",
            },
            "EXINF": {
                "Event Group Label": "Event Group Label",
                " Was study treatment administered? (IG_NS_NA_EXINF1.CL_NS_NH_INFADMIN_cl_YS_YN1)": "Treated",
            },
            "DSEOS": {
                "End of Study Date (IG_NS_NA_DSEOS1.DT_NS_YH_EOSDAT)": "End of Study Date",
                "Reason for End of Study? (IG_NS_NA_DSEOS2.CL_NS_YH_EOSCOD1_cl_NS_EOSREAS1)": "End of Study Reason",
                "Provide Supportive Information (IG_NS_NA_DSEOS2.TX_NS_YH_EOSTERM)": "Supportive Information",
            },
        }

        enrollment_df = get_data_from_dict(data, input_dict)
        # Replace missing values in the "Cohort Assignment" and "Dose Level Assignment" columns with "Pending"
        enrollment_df["Cohort Assignment"] = enrollment_df["Cohort Assignment"].fillna(
            "Pending"
        )
        enrollment_df["Dose Level Assignment"] = enrollment_df[
            "Dose Level Assignment"
        ].fillna("Pending")

        enrollment_df = age_calculation(
            enrollment_df,
            "Age at Consent",
            "Date of Birth",
            "Main Consent Date",
        )

        # fill NaN with empty string
        enrollment_df = enrollment_df.fillna("")

        # Convert the entire column to string to avoid data type issues
        enrollment_df["Reason for Screen Fail"] = enrollment_df[
            "Reason for Screen Fail"
        ].astype(str)

        # if "Reason for Screen Fail" in enrollment_df.columns equal "Other", replace the value with SF3
        mask = enrollment_df["Reason for Screen Fail"] == "Other"
        # Replace "Other" with the corresponding values from the "SF3" column
        enrollment_df.loc[mask, "Reason for Screen Fail"] = enrollment_df.loc[
            mask, "SF3"
        ]

        # if "Reason for Screen Fail" in enrollment_df.columns equal "Inclusion Criteria", concat the value of the column with "SF1"
        # Create a mask for rows where "Reason for Screen Fail" is "Inclusion Criteria"
        mask = (enrollment_df["Reason for Screen Fail"] == "Inclusion Criteria") & (
            enrollment_df["SF1"] != ""
        )
        # Use the mask to update the "Reason for Screen Fail" column
        enrollment_df.loc[mask, "Reason for Screen Fail"] = (
            enrollment_df.loc[mask, "Reason for Screen Fail"]
            + " "
            + enrollment_df.loc[mask, "SF1"].astype(str)
        )

        # Create a mask for rows where "Reason for Screen Fail" is "Exclusion Criteria" and "SF2" is not empty
        mask = (enrollment_df["Reason for Screen Fail"] == "Exclusion Criteria") & (
            enrollment_df["SF2"] != ""
        )

        # Use the mask to update the "Reason for Screen Fail" column
        enrollment_df.loc[mask, "Reason for Screen Fail"] = (
            enrollment_df.loc[mask, "Reason for Screen Fail"]
            + " "
            + enrollment_df.loc[mask, "SF2"].astype(str)
        )

        # if subject does not have IE data, check if the subject has DSEOS "End of Study Date" data. If yes, then the subject is "No" for "Subject meets all study eligibility?"
        enrollment_df.loc[
            (enrollment_df["Subject meets all study eligibility?"] != "Yes")
            & (enrollment_df["End of Study Date"].isnull()),
            "Subject meets all study eligibility?",
        ] = "Pending"
        enrollment_df.loc[
            (enrollment_df["Subject meets all study eligibility?"] != "Yes")
            & (enrollment_df["End of Study Date"].notna()),
            "Subject meets all study eligibility?",
        ] = "No"
        enrollment_df.loc[
            (enrollment_df["Subject meets all study eligibility?"] != "Yes")
            & (enrollment_df["End of Study Date"].notna()),
            "Reason for Screen Fail",
        ] = enrollment_df["Supportive Information"]
        # Add Screen Fail column
        enrollment_df["Screen Fail"] = None

        # Define conditions and corresponding values
        conditions = [
            enrollment_df["Subject meets all study eligibility?"].fillna("Unknown")
            == "No",
            enrollment_df["Subject meets all study eligibility?"].fillna("Unknown")
            == "Yes",
            enrollment_df["Subject meets all study eligibility?"].fillna("Unknown")
            == "Pending",
        ]

        values = [
            "Yes",
            "No",
            "Pending",
        ]

        # Use np.select to assign values based on conditions
        enrollment_df["Screen Fail"] = np.select(conditions, values, default="Unknown")

        # Override Screen Fail if DSEOS indicates screen failure ---
        mask_dseos_sf = enrollment_df["End of Study Reason"].str.contains(
            "Screen failure", case=False, na=False
        )

        # If DSEOS says screen failure → Screen Fail must be Yes
        enrollment_df.loc[mask_dseos_sf, "Screen Fail"] = "Yes"

        # Use supportive information as reason if Screen Failure is triggered by DSEOS
        enrollment_df.loc[mask_dseos_sf, "Reason for Screen Fail"] = enrollment_df[
            "Supportive Information"
        ].fillna("")

        enrollment_df.loc[
            (
                enrollment_df["Last Eligibility Step Completed"]
                == "Step #1 Screening/Eligibility"
            )
            & (enrollment_df["Treated"] != "Yes")
            & enrollment_df["Screen Fail"].isin(["No", ""]),
            "Screen Fail",
        ] = "Pending"

        # Add Last Eligibility Step Completed column
        enrollment_df["Last Eligibility Step Completed"] = enrollment_df[
            "Last Eligibility Step Completed"
        ].fillna("")

        # Remove only the trailing " Screening/Eligibility"
        enrollment_df["Last Eligibility Step Completed"] = enrollment_df[
            "Last Eligibility Step Completed"
        ].str.replace(" Screening/Eligibility", "", regex=False)

        # drop the columns that are not needed
        enrollment_df = enrollment_df.drop(
            columns=[
                "SF1",
                "SF2",
                "SF3",
                "Supportive Information",
            ]
        )

        enrollment_df = enrollment_df.drop(columns=["Event Group Label"])
        # Update 'Treated' column based on the conditions:
        enrollment_df.loc[
            (enrollment_df["Treated"] != "Yes")
            & (enrollment_df["End of Study Date"].isnull()),
            "Treated",
        ] = "Pending"
        enrollment_df.loc[
            (enrollment_df["Treated"] != "Yes")
            & (~enrollment_df["End of Study Date"].isnull()),
            "Treated",
        ] = "No"

        screen_fail_series = enrollment_df.get("Screen Fail")
        treated_series = enrollment_df.get("Treated")
        eos_reason_series = enrollment_df.get("End of Study Reason")
        if screen_fail_series is None:
            screen_fail_series = pd.Series(
                [""] * len(enrollment_df), index=enrollment_df.index
            )
        if treated_series is None:
            treated_series = pd.Series(
                [""] * len(enrollment_df), index=enrollment_df.index
            )
        if eos_reason_series is None:
            eos_reason_series = pd.Series(
                [""] * len(enrollment_df), index=enrollment_df.index
            )

        enrollment_df["Reason for Withdrawal Prior to Study Treatment"] = np.where(
            (screen_fail_series.fillna("").astype(str).str.strip() == "No")
            & (treated_series.fillna("").astype(str).str.strip() == "No"),
            eos_reason_series.fillna("").astype(str),
            "",
        )
        enrollment_df = enrollment_df.drop(
            columns=["End of Study Reason"], errors="ignore"
        )

        # Sort
        enrollment_df = enrollment_df.sort_values(["Subject"])

        # prepare the output dataframe
        enrollment_output_df = enrollment_df.copy()
        for col in enrollment_output_df.columns:
            if "Date" in col:
                enrollment_output_df[col] = enrollment_output_df[col].dt.strftime(
                    "%m/%d/%Y"
                )
        # If Gender is "Other", replace the value with "Other Gender"
        enrollment_output_df.loc[
            enrollment_output_df["Gender Identity"] == "Other",
            "Gender Identity",
        ] = enrollment_output_df["Other Gender"]
        # Use `.loc` to filter where Race is "Other" and update it with the value in "Other Race"
        enrollment_output_df.loc[enrollment_output_df["Race"] == "Other", "Race"] = (
            "Other- "
            + enrollment_output_df.loc[
                enrollment_output_df["Race"] == "Other", "Other Race"
            ].astype(str)
        )
        # *Re-order the columns and remove the columns that are not needed
        enrollment_output_df = enrollment_output_df[
            [
                "Subject",
                "Cohort Assignment",
                "Dose Level Assignment",
                "Legal Sex",
                "Sex Assigned at Birth",
                "Gender Identity",
                "Ethnicity",
                "Race",
                "Age at Consent",
                "Screen Fail",
                "Reason for Screen Fail",
                "Treated",
                "Reason for Withdrawal Prior to Study Treatment",
            ]
        ]
        return enrollment_output_df, enrollment_df

    def enrollment_stat_table(self, enrollment_df):
        # Demo Stats Table
        # !Update this filter options to each cohort
        filter_options = [
            enrollment_df["Main Consent Date"].notna(),
            enrollment_df["Cohort Assignment"] == "Cohort A",
        ]
        self.status_list = []
        self.LegalSex_list = []
        self.Age_at_Consent_list = []
        self.Race_list = []
        self.Ethnicity_list = []

        for filter_option in filter_options:
            # Apply the filter to the dataframe
            filtered_df = enrollment_df[filter_option].copy()
            filtered_df = filtered_df[(filtered_df["Main Consent Date"].notna())]
            # Calculate the stats
            ## Total Consented
            TT_df = filtered_df.copy()
            TT = filtered_df["Subject"].count()
            ## Screen Failed
            SF_df = filtered_df[filtered_df["Screen Fail"] == "Yes"].copy()
            SF = SF_df["Subject"].count()
            ## Eligible
            EL_df = filtered_df[filtered_df["Screen Fail"] == "No"].copy()
            EL = EL_df["Subject"].count()
            ## Treated
            INFR_df = filtered_df[filtered_df["Treated"] == "Yes"].copy()
            INF = INFR_df["Subject"].count()

            # Define a dictionary containing the status of each variable
            self.status_list.append(
                {
                    "Total Consented": TT,
                    "Screen Failed": SF,
                    "Eligible": EL,
                    "Treated": INF,
                }
            )

            # Calculate the stats for the filtered dataframe
            Legal_Sex_Codelist = ["Male", "Female", "X (Nonbinary)", "Not Reported"]
            self.LegalSex_list.append(
                get_stats_percentage2(
                    "Legal Sex", Legal_Sex_Codelist, TT_df, SF_df, EL_df, INFR_df
                )
            )
            self.Age_at_Consent_list.append(
                get_stats_df("Age at Consent", TT_df, SF_df, EL_df, INFR_df)
            )
            self.Race_list.append(
                get_stats_percentage("Race", TT_df, SF_df, EL_df, INFR_df)
            )
            self.Ethnicity_list.append(
                get_stats_percentage("Ethnicity", TT_df, SF_df, EL_df, INFR_df)
            )

    def EGFR_listing(self):
        data = self.data
        DM_df = data["DM"][["Subject"]].copy()

        EGFR_df = data["LBEGFR"][
            [
                "Subject",
                "Amplification of EGFR (IG_NS_NA_LBEGFR2.CL_NS_YH_AMPEGFR_cl_YS_DTNDT1)",
                "EGFRvIII Mutation (IG_NS_NA_LBEGFR2.CL_NS_NH_AMPEGFR8_cl_YS_DTNDT1)",
                "EGFR Mutation (IG_NS_NA_LBEGFR2.CL_NS_YH_EGFRMUT_cl_YS_DTNDT1)",
                "Laboratory Name (IG_NS_NA_LBEGFR1.CL_NS_NH_LBNAMEGFR_cl_NS_LBNAME2)",
            ]
        ].copy()

        EGFR_new_col_name = {
            "Amplification of EGFR (IG_NS_NA_LBEGFR2.CL_NS_YH_AMPEGFR_cl_YS_DTNDT1)": "Amplification of EGFR",
            "EGFRvIII Mutation (IG_NS_NA_LBEGFR2.CL_NS_NH_AMPEGFR8_cl_YS_DTNDT1)": "EGFRvIII Mutation",
            "EGFR Mutation (IG_NS_NA_LBEGFR2.CL_NS_YH_EGFRMUT_cl_YS_DTNDT1)": "EGFR Mutation",
            "Laboratory Name (IG_NS_NA_LBEGFR1.CL_NS_NH_LBNAMEGFR_cl_NS_LBNAME2)": "Laboratory Name",
        }

        EGFR_df = EGFR_df.rename(columns=EGFR_new_col_name)

        # Combine results by subject, giving NeoGenomics priority unless its value is "Not Done"
        combined_EGFR_df = (
            EGFR_df.groupby("Subject", dropna=False)
            .apply(combine_labs, include_groups=False)
            .reset_index(drop=True)
        )

        # Merge on "Subject"
        EGFR_final_df = pd.merge(DM_df, combined_EGFR_df, on="Subject", how="left")

        MHDIAG_df = data["MHDIAG"][
            [
                "Subject",
                "MGMT Result (IG_NS_NA_MHDIAG2.CL_NS_NH_MGMTRES_cl_NS_MGMTRES1)",
            ]
        ].copy()
        MHDIAG_new_col_name = {
            "MGMT Result (IG_NS_NA_MHDIAG2.CL_NS_NH_MGMTRES_cl_NS_MGMTRES1)": "MGMT Result",
        }
        MHDIAG_df = MHDIAG_df.rename(columns=MHDIAG_new_col_name)

        EGFR_final2_df = pd.merge(EGFR_final_df, MHDIAG_df, on="Subject", how="right")
        EGFR_final2_df = EGFR_final2_df.sort_values(["Subject"])
        EGFR_final2_df = EGFR_final2_df.fillna("")

        EGFR_output_df = EGFR_final2_df.copy()
        EGFR_output_df = EGFR_output_df[
            [
                "Subject",
                "Amplification of EGFR",
                "EGFRvIII Mutation",
                "EGFR Mutation",
                "MGMT Result",
            ]
        ]
        return EGFR_output_df, EGFR_final2_df

    def infusion_listing(self):
        data = self.data
        # TREATMENT LISTING
        # adding Target Cell Dose dictionary
        # !: Update this dictionary to the new study
        TCD_dict = {
            "Dose Level -1 (DL-1)": 10000000,
            "Dose Level 1 (DL1)": 25000000,
            "Not Assigned": "Not Assigned",
        }

        # *: PREPARE DATA FOR TREATMENT LISTING

        # create dictionary for Treatment listing
        input_dict1 = {
            "EXINF": {
                "Event Label": "Event Label",
                "Study Treatment Date (IG_NS_NA_EXINF1.DT_NS_NH_INFDAT)": "Study Treatment Date",
                "Volume CSF Removed for Cell Product Administration (mL) (IG_NS_NA_EXINF1.NM_NS_NH_CSFVOL)": "Volume CSF Removed",
                "Total Volume Administered (mL) (IG_NS_NA_EXINF1.NM_NS_NH_TOTVOL)": "Volume Administered",
                "CAR T Cell Dose Administered (IG_NS_NA_EXINF1.NM_NS_YH_TDOS)": "CART-EGFR-IL13Ra2 Cell Dose",
                "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TDOSXP_cl_YS_EX10POW1)": "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TDOSXP_cl_YS_EX10POW1)",
                "Total Cell Dose Administered (IG_NS_NA_EXINF1.NM_NS_YH_TOTDOS)": "Total Cell Dose",
                "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TOTDOSXP_cl_YS_EX10POW1)": "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TOTDOSXP_cl_YS_EX10POW1)",
                "EGFR Transduction Efficiency (%) (IG_NS_NA_EXINF1.NM_NS_NH_EGFRINFTEFFP)": "%scFV (EGFR)",
                "IL13Ra2 Transduction Efficiency (%) (IG_NS_NA_EXINF1.NM_NS_NH_IL13INFTEFFP)": "%scFV (IL13Ra2)",
            },
        }

        input_dict2 = {
            "DSCA": {
                "Cohort Assignment (IG_NS_NA_DSCA1.CL_NS_YH_CACHASCOD_cl_NS_COHORT1)": "Cohort Assignment"
            },
        }

        input_dict3 = {
            "DSDLA": {
                "Dose Level Assignment (IG_NS_NA_DSDLA1.CL_NS_YH_DLADOSELV_cl_NS_DOSELV1)": "Dose Level Assignment"
            },
        }

        raw_infusion_df1 = get_data_from_dict(data, input_dict1, keep="first")
        raw_infusion_df2 = get_data_from_dict(data, input_dict2)
        raw_infusion_df3 = get_data_from_dict(data, input_dict3)
        raw_infusion_df_TEMP = pd.merge(
            raw_infusion_df1, raw_infusion_df2, on="Subject", how="left"
        )
        raw_infusion_df = pd.merge(
            raw_infusion_df_TEMP, raw_infusion_df3, on="Subject", how="left"
        )

        # TREATMENT LISTING Day 0

        infusion_df = raw_infusion_df[(raw_infusion_df["Event Label"] == "Day 0")]

        # adding Target Dose using TCD_dict
        infusion_df["Target Dose"] = infusion_df["Dose Level Assignment"].map(TCD_dict)

        # combine CART-EGFR-IL13Rα2 Cell Dose and x 10 to the power of (ig_EXINF1.INFDOSXP) columns, compare the new value with 'Target Cell Dose', and convert the CART-EGFR-IL13Rα2 Cell Dose column to string
        infusion_df["CART-EGFR-IL13Ra2 Cell Dose"] = infusion_df[
            "CART-EGFR-IL13Ra2 Cell Dose"
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
        infusion_df["Total Cell Dose"] = infusion_df["Total Cell Dose"].multiply(
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

        # Adding Met Target Dose column based on the condition of Total Cell Dose and CART-EGFR-IL13Rα2 Cell Dose if 'Target Cell Dose' is integer
        infusion_df["Met Target Dose (Y/N)"] = infusion_df.apply(
            lambda row: (
                "Y"
                if isinstance(row["Target Dose"], int)
                and row["CART-EGFR-IL13Ra2 Cell Dose"] >= row["Target Dose"]
                else ""
            ),
            axis=1,
        )
        infusion_df["Met Target Dose (Y/N)"] = infusion_df.apply(
            lambda row: (
                "N"
                if isinstance(row["Target Dose"], int)
                and row["CART-EGFR-IL13Ra2 Cell Dose"] < row["Target Dose"]
                else row["Met Target Dose (Y/N)"]
            ),
            axis=1,
        )

        # adding Met Target %scFv and filter out the rows that have NaN in Met Target %scFv
        infusion_df["Met Target % scFV Flow (Y/N) (≥2%)"] = infusion_df[
            infusion_df["%scFV (EGFR)"].notna()
        ]["%scFV (EGFR)"].apply(lambda x: "Y" if x >= 2 else "N")
        # fill NaN with empty string
        infusion_df = infusion_df.fillna(
            "",
        ).infer_objects()

        # Only keep the rows that have Event Label
        infusion_df = infusion_df[infusion_df["Event Label"] != ""]

        # *Re-order the columns and remove the columns that are not needed
        infusion_df = infusion_df[
            [
                "Subject",
                "Cohort Assignment",
                "Dose Level Assignment",
                "Study Treatment Date",
                "Volume CSF Removed",
                "Volume Administered",
                "Total Cell Dose",
                "CART-EGFR-IL13Ra2 Cell Dose",
                "Met Target Dose (Y/N)",
                "%scFV (EGFR)",
                "Met Target % scFV Flow (Y/N) (≥2%)",
                "%scFV (IL13Ra2)",
            ]
        ]

        # Treatment Listing Day 0-R

        raw_infusionR_df1 = get_data_from_dict(data, input_dict1)
        raw_infusionR_df2 = get_data_from_dict(data, input_dict2)
        raw_infusionR_df3 = get_data_from_dict(data, input_dict3)
        raw_infusionR_df_TEMP = pd.merge(
            raw_infusionR_df1, raw_infusionR_df2, on="Subject", how="left"
        )
        raw_infusionR_df = pd.merge(
            raw_infusionR_df_TEMP, raw_infusionR_df3, on="Subject", how="left"
        )

        infusionR_df = raw_infusionR_df[
            (raw_infusionR_df["Event Label"] == "Day 0-R")
        ].copy()

        # combine CART-EGFR-IL13Rα2 Cell Dose and x 10 to the power of (ig_EXINF1.INFDOSXP) columns, compare the new value with 'Target Cell Dose', and convert the CART-EGFR-IL13Rα2 Cell Dose column to string
        infusionR_df["CART-EGFR-IL13Ra2 Cell Dose"] = infusionR_df[
            "CART-EGFR-IL13Ra2 Cell Dose"
        ].multiply(
            10
            ** infusionR_df[
                "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TDOSXP_cl_YS_EX10POW1)"
            ]
        )
        infusionR_df = infusionR_df.drop(
            columns=[
                "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TDOSXP_cl_YS_EX10POW1)"
            ]
        )

        infusionR_df["Total Cell Dose"] = infusionR_df["Total Cell Dose"].multiply(
            10
            ** infusionR_df[
                "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TOTDOSXP_cl_YS_EX10POW1)"
            ]
        )
        infusionR_df = infusionR_df.drop(
            columns=[
                "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TOTDOSXP_cl_YS_EX10POW1)"
            ]
        )

        # adding Met Target %scFv and fillter out the rows that have NaN in Met Target %scFv
        infusionR_df["Met Target % scFV Flow (Y/N) (≥2%)"] = infusionR_df[
            infusionR_df["%scFV (EGFR)"].notna()
        ]["%scFV (EGFR)"].apply(lambda x: "Y" if x >= 2 else "N")
        # fill NaN with empty string
        infusionR_df = infusionR_df.fillna(
            "",
        ).infer_objects()

        # Only keep the rows that have Event Label
        infusionR_df = infusionR_df[infusionR_df["Event Label"] != ""]

        # *Re-order the columns and remove the columns that are not needed
        infusionR_df = infusionR_df[
            [
                "Subject",
                "Cohort Assignment",
                "Dose Level Assignment",
                "Study Treatment Date",
                "Volume CSF Removed",
                "Volume Administered",
                "Total Cell Dose",
                "CART-EGFR-IL13Ra2 Cell Dose",
                "%scFV (EGFR)",
                "Met Target % scFV Flow (Y/N) (≥2%)",
                "%scFV (IL13Ra2)",
            ]
        ]

        # Apply formatting
        # format the date field to be no leading 0
        infusion_df["Study Treatment Date"] = pd.to_datetime(
            infusion_df["Study Treatment Date"], errors="coerce"
        ).dt.strftime("%m-%d-%Y")
        infusion_df["Study Treatment Date"] = infusion_df["Study Treatment Date"].apply(
            format_date
        )
        infusionR_df["Study Treatment Date"] = pd.to_datetime(
            infusionR_df["Study Treatment Date"], errors="coerce"
        ).dt.strftime("%m-%d-%Y")
        infusionR_df["Study Treatment Date"] = infusionR_df[
            "Study Treatment Date"
        ].apply(format_date)

        return infusion_df, infusionR_df

    def infusion_stats(self, infusion_df, infusionR_df):
        # TREATMENT STATISTICS
        infusion_count = []
        # * Cohort A
        # Create a new dataframe for Cohort A with infusion_df
        infusion1_df = self.infusion_df[
            self.infusion_df["Cohort Assignment"] == "Cohort A"
        ]
        # Create a new dataframe for Total Cell Dose table with infusion_df
        infusion_statA1 = get_stats_df("Total Cell Dose", infusion1_df)
        # Create a new dataframe for CAR T Cell Dose table with infusion_df
        infusion_statA2 = get_stats_df("CART-EGFR-IL13Ra2 Cell Dose", infusion1_df)
        # Count the number of subjects that met the target dose
        met_targetDose_count = infusion1_df[
            infusion1_df["Met Target Dose (Y/N)"] == "Y"
        ].count()["Subject"]
        # Count the number of subjects
        total_subject_count = infusion1_df["Subject"].nunique()
        # Add column "Met Target Dose (Y/N)" to infusion_statA2 data frame, since data frames are concated, the order of the data frame should match the output order
        infusion_statA2["Met Target Dose (Y/N)"] = (
            str(met_targetDose_count)
            + " ("
            + str(round(met_targetDose_count / total_subject_count * 100, 2))
            + "%)"
        )
        # Create a new dataframe for %scFv Flow table with infusion_df
        infusion_statA3 = get_stats_perc_df("%scFV (EGFR)", infusion1_df)
        # Count the number of subjects that met the target %scFv
        met_targetFlow_count = infusion1_df[
            infusion1_df["Met Target % scFV Flow (Y/N) (≥2%)"] == "Y"
        ].count()["Subject"]
        infusion_statA3["Met Target % scFV Flow (Y/N) (≥2%)"] = (
            str(met_targetFlow_count)
            + " ("
            + str(round(met_targetFlow_count / total_subject_count * 100, 2))
            + "%)"
        )
        # Create a new dataframe for %scFV (Il13Rα2) with infusion_df
        infusion_statA4 = get_stats_perc_df("%scFV (IL13Ra2)", infusion1_df)
        # Combine the three dataframes
        infusion_statA = pd.concat(
            [infusion_statA1, infusion_statA2, infusion_statA3, infusion_statA4],
            axis=1,
        )
        infusion_statA = infusion_statA.replace([np.inf, -np.inf], "")
        infusion_statA = infusion_statA.fillna("")
        self.infusion_statA = infusion_statA
        infusion_count.append(total_subject_count)
        self.infusion_count = infusion_count

        # FORMATTING THE DATAFRAME
        # Day 0
        # Convert the columns to scientific notation if the value is not NaN

        infusion_df["CART-EGFR-IL13Ra2 Cell Dose"] = infusion_df[
            "CART-EGFR-IL13Ra2 Cell Dose"
        ].apply(
            lambda x: (
                convert_float_2_sci_notation(x)
                if not isinstance(x, str) and pd.notna(x)
                else x
            )
        )
        infusion_df["Total Cell Dose"] = infusion_df["Total Cell Dose"].apply(
            lambda x: (
                convert_float_2_sci_notation(x)
                if not isinstance(x, str) and pd.notna(x)
                else x
            )
        )
        # adding '%' sign to %scFv Flow
        infusion_df["%scFV (EGFR)"] = infusion_df.apply(
            lambda row: str(x) + "%" if pd.notna(x := row["%scFV (EGFR)"]) else x,
            axis=1,
        )
        infusion_df["%scFV (IL13Ra2)"] = infusion_df.apply(
            lambda row: str(x) + "%" if pd.notna(x := row["%scFV (IL13Ra2)"]) else x,
            axis=1,
        )

        # Day 0-R
        # Convert the columns to scientific notation if the value is not NaN
        infusionR_df["CART-EGFR-IL13Ra2 Cell Dose"] = infusionR_df[
            "CART-EGFR-IL13Ra2 Cell Dose"
        ].apply(
            lambda x: (
                convert_float_2_sci_notation(x)
                if isinstance(x, float) and pd.notna(x)
                else x
            )
        )
        infusionR_df["Total Cell Dose"] = infusionR_df["Total Cell Dose"].apply(
            lambda x: (
                convert_float_2_sci_notation(x)
                if isinstance(x, float) and pd.notna(x)
                else x
            )
        )
        # adding '%' sign to %scFv Flow
        infusionR_df["%scFV (EGFR)"] = infusionR_df.apply(
            lambda row: str(x) + "%" if pd.notna(x := row["%scFV (EGFR)"]) else x,
            axis=1,
        )
        infusionR_df["%scFV (IL13Ra2)"] = infusionR_df.apply(
            lambda row: str(x) + "%" if pd.notna(x := row["%scFV (IL13Ra2)"]) else x,
            axis=1,
        )

    def status_listing(self):
        data = self.data
        # AE and SAE data
        AE_df = data["AE"][
            [
                "Subject",
                "AE or SAE (IG_NS_NA_AE2.CL_NS_YH_AESEV_cl_NS_AESAE1)",
            ]
        ].copy()
        AE_new_col_name = {
            "AE or SAE (IG_NS_NA_AE2.CL_NS_YH_AESEV_cl_NS_AESAE1)": "AE or SAE?",
        }
        AE_df = AE_df.rename(columns=AE_new_col_name)

        status_df = self.enrollment_listing_df[
            self.enrollment_listing_df["Screen Fail"].str.strip() == "No"
        ][["Subject", "Cohort Assignment", "Dose Level Assignment"]]

        status_df["AE"] = status_df["Subject"].apply(
            lambda x: "Y" if x in AE_df["Subject"].values else "N"
        )

        status_df["SAE"] = status_df["Subject"].apply(
            lambda x: (
                "Y"
                if x in AE_df[AE_df["AE or SAE?"] == "SAE"]["Subject"].values
                else "N"
            )
        )
        # replaces all occurrences of NaN, positive infinity, and negative infinity in the infusion_df dataframe with empty strings.
        status_df = status_df.replace([np.nan, np.inf, -np.inf], "")

        # Event Group Name dictionary for Study Status column
        event_1_dict = {
            "eg_PTS": "Pre-Treatment",
            "eg_CSFVRP": "Pre-Treatment",
            "eg_PRMTX": "Primary Treatment",
            "eg_PRMTXFUP": "Primary Follow-up",
            "eg_DAY21DAY28": "Primary Follow-up",
            "eg_PRMTXFUP2": "Primary Follow-up",
            "eg_LTFUP1": "Long-Term Follow-up",
            "eg_LTFUP2": "Long-Term Follow-up",
            "eg_LTFUEV1": "Long-Term Follow-up",
            "eg_LTFUEV2": "Long-Term Follow-up",
            "eg_LTFUPNV": "Long-Term Follow-up",
            "eg_PTSR": "Pre-Retreatment",
            "eg_PRMTXR": "Primary Retreatment",
            "eg_PRMTXFUPR": "Primary Retreatment Follow-up",
            "eg_PRMTXFUP2R": "Primary Retreatment Follow-up",
            "eg_LTFUP1R": "Retreatment Long-Term Follow-up",
            "eg_LTFUP2R": "Retreatment Long-Term Follow-up",
            "eg_LTFUEV1R": "Retreatment Long-Term Follow-up",
            "eg_LTFUEV2R": "Retreatment Long-Term Follow-up",
            "eg_LTFUPNVR": "Retreatment Long-Term Follow-up",
        }

        # Getting Study Status dataframe from SV, column Subject, Event Group Name and Event Date
        status_SV_df = data["DSSV"][
            [
                "Subject",
                "Event Group Name",
                "Event Date",
            ]
        ]

        # Getting Study Status dataframe from DSSVLTFU, column Subject, Event Label and Event Date
        status_DSSVLTFU_df = data["DSSVLTFU"][
            [
                "Subject",
                "Event Group Name",
                "Event Date",
            ]
        ]

        # Combine DSSVLTFU with SV dataframe vertically
        status_SV_df = pd.concat([status_SV_df, status_DSSVLTFU_df])
        # Sort the dataframe by Subject and Event Date
        status_SV_df = status_SV_df.sort_values(by=["Subject", "Event Date"])

        # For each unique subject, get the last row of the dataframe
        status_SV_df = status_SV_df.groupby("Subject").tail(1)

        # Merge left with the current response dataframe
        status_df = pd.merge(
            status_df,
            status_SV_df[["Subject", "Event Group Name"]],
            on="Subject",
            how="left",
        )

        # Rename the column Event Label to Event Group Name (Study Status)
        status_df["Event Group Name"] = status_df["Event Group Name"].map(event_1_dict)

        status_df["Event Group Name3"] = status_df.apply(
            lambda row: (
                "Pre-Treatment"
                if (
                    row["Event Group Name"] != "Pre-Treatment"  # avoid duplication
                    and self.enrollment_listing_df[
                        self.enrollment_listing_df["Subject"] == row["Subject"]
                    ]["Treated"]
                    .fillna("")
                    .str.strip()
                    .values[0]
                    == "Pending"
                )
                else ""
            ),
            axis=1,
        )
        status_df["Event Group Name4"] = status_df["Subject"].apply(
            lambda x: (
                "Withdrawn Prior to Study Treatment"
                if (
                    self.enrollment_listing_df[
                        self.enrollment_listing_df["Subject"] == x
                    ]["Treated"]
                    .fillna("")
                    .str.strip()
                    .values[0]
                    == "No"
                )
                & (
                    self.enrollment_listing_df[
                        self.enrollment_listing_df["Subject"] == x
                    ]["Screen Fail"]
                    .fillna("")
                    .str.strip()
                    .values[0]
                    == "No"
                )
                else ""
            )
        )

        status_df["Event Group Name"] = np.where(
            status_df["Event Group Name"].isna()
            | (status_df["Event Group Name"] == ""),
            status_df["Event Group Name3"].fillna("")
            + status_df["Event Group Name4"].fillna(""),
            status_df["Event Group Name"],
        )
        status_df["Event Group Name"] = status_df["Event Group Name"].fillna(
            status_df["Event Group Name"]
        )
        status_df = status_df.drop(
            columns=[
                "Event Group Name3",
                "Event Group Name4",
            ]
        )

        # filter the data frame to only include subjects whose end of study date is later than or equal to main consent date
        filteredemrollment_df = self.enrollment_listing_df[
            self.enrollment_listing_df["End of Study Date"]
            >= self.enrollment_listing_df["Main Consent Date"]
        ]
        DSEOS_df = data["DSEOS"][
            [
                "Subject",
                "Reason for End of Study? (IG_NS_NA_DSEOS2.CL_NS_YH_EOSCOD1_cl_NS_EOSREAS1)",
                "Provide Supportive Information (IG_NS_NA_DSEOS2.TX_NS_YH_EOSTERM)",
                "Principal Cause of Death (IG_NS_NA_DSEOS2.CL_NS_NH_PRCDTH_cl_NS_EOSCAD1)",
                "Specify Principal Cause of Death (IG_NS_NA_DSEOS2.TX_NS_NH_PRCDTHOS)",
                "Last Study Phase (IG_NS_NA_DSEOS1.CL_NS_YH_LSTUDYPS_cl_YS_STUDYPS1)",
                "Last Study Visit Completed in Primary Treatment (IG_NS_NA_DSEOS1.CL_NS_YH_EOSLSVPR_cl_NS_EOSTP1)",
                "Last Study Visit Completed in Retreatment (IG_NS_NA_DSEOS1.CL_NS_YH_EOSLSVRE_cl_NS_EOSTP2)",
            ]
        ].copy()
        DSEOS_new_col_name = {
            "Reason for End of Study? (IG_NS_NA_DSEOS2.CL_NS_YH_EOSCOD1_cl_NS_EOSREAS1)": "Off-Study Reason",
            "Provide Supportive Information (IG_NS_NA_DSEOS2.TX_NS_YH_EOSTERM)": "Off-Study Reason sp1",
            "Principal Cause of Death (IG_NS_NA_DSEOS2.CL_NS_NH_PRCDTH_cl_NS_EOSCAD1)": "Off-Study Reason sp2",
            "Specify Principal Cause of Death (IG_NS_NA_DSEOS2.TX_NS_NH_PRCDTHOS)": "Off-Study Reason sp3",
            "Last Study Phase (IG_NS_NA_DSEOS1.CL_NS_YH_LSTUDYPS_cl_YS_STUDYPS1)": "Last Study Phase Completed",
            "Last Study Visit Completed in Primary Treatment (IG_NS_NA_DSEOS1.CL_NS_YH_EOSLSVPR_cl_NS_EOSTP1)": "Last Primary FUP",
            "Last Study Visit Completed in Retreatment (IG_NS_NA_DSEOS1.CL_NS_YH_EOSLSVRE_cl_NS_EOSTP2)": "Last Primary Retreatment",
        }
        DSEOS_df = DSEOS_df.rename(columns=DSEOS_new_col_name)

        # Merge last study visit
        DSEOS_df["Last Study Visit"] = DSEOS_df["Last Primary FUP"].fillna(
            ""
        ) + DSEOS_df["Last Primary Retreatment"].fillna("")

        # Merge off-study reason
        DSEOS_df["Off-Study Reason"] = (
            DSEOS_df["Off-Study Reason"].fillna("")
            + " "
            + DSEOS_df["Off-Study Reason sp1"].fillna("")
            + DSEOS_df["Off-Study Reason sp2"].fillna("")
            + " "
            + DSEOS_df["Off-Study Reason sp3"].fillna("")
        )

        filteredDSEOS_df = DSEOS_df[
            (DSEOS_df["Subject"].isin(filteredemrollment_df["Subject"].values))
        ].copy()
        # on perform the replace when status_df is not empty
        if not status_df.empty:
            eos_subjects = set(filteredDSEOS_df["Subject"].values)

            def update_event_label(row):
                ev = row["Event Group Name"]
                subj = row["Subject"]

                if subj in eos_subjects:
                    if ev == "Pre-Treatment":
                        return "Off Study/Withdrawn Prior to Study Treatment"
                    else:
                        return "Off Study/" + ev
                else:
                    return "On Study/" + ev

            status_df["Event Group Name"] = status_df.apply(update_event_label, axis=1)

            status_df = pd.merge(
                status_df,
                filteredDSEOS_df[["Subject", "Off-Study Reason", "Last Study Visit"]],
                on="Subject",
                how="left",
            )

        # replaces all occurrences of NaN, positive infinity, and negative infinity with empty strings.
        status_df = status_df.replace([np.nan, np.inf, -np.inf], "N/A")

        # Gather all stats of each cohort
        total_status_df = status_df.copy()

        totalCH1_status_df = total_status_df[
            total_status_df["Cohort Assignment"].isin(["Cohort A"])
        ].copy()
        # Total number of subjects for Cohort A
        AECH1_total_count = get_stats_percentage("AE", totalCH1_status_df).T
        SAECH1_total_count = get_stats_percentage("SAE", totalCH1_status_df).T
        # merge AE and SAE dataframes
        safetyCH1_total_df = pd.concat([AECH1_total_count, SAECH1_total_count], axis=1)

        return (
            AE_df,
            status_df,
            safetyCH1_total_df,
        )

    def TXSUB_status_listing(self):
        data = self.data
        # AE and SAE data
        AE_df = data["AE"][
            [
                "Subject",
                "AE or SAE (IG_NS_NA_AE2.CL_NS_YH_AESEV_cl_NS_AESAE1)",
            ]
        ].copy()
        AE_new_col_name = {
            "AE or SAE (IG_NS_NA_AE2.CL_NS_YH_AESEV_cl_NS_AESAE1)": "AE or SAE?",
        }
        AE_df = AE_df.rename(columns=AE_new_col_name)

        TXSUB_status_df = self.infusion_df["Subject"].copy()
        TXSUB_status_df = TXSUB_status_df.sort_values()

        # Merge left with the TXSUB_status_df and keep unique rows
        TXSUB_status_df = (
            pd.merge(
                TXSUB_status_df,
                AE_df,
                on="Subject",
                how="left",
            )
            .drop(columns=["AE or SAE?"], errors="ignore")  # drop if exists
            .drop_duplicates()
            .reset_index(drop=True)
        )

        TXSUB_status_df["AE"] = TXSUB_status_df["Subject"].apply(
            lambda x: "Y" if x in AE_df["Subject"].values else "N"
        )

        TXSUB_status_df["SAE"] = TXSUB_status_df["Subject"].apply(
            lambda x: (
                "Y"
                if x in AE_df[AE_df["AE or SAE?"] == "SAE"]["Subject"].values
                else "N"
            )
        )
        # replaces all occurrences of NaN, positive infinity, and negative infinity in the TXSUB_status_df dataframe with empty strings.
        TXSUB_status_df = TXSUB_status_df.replace([np.nan, np.inf, -np.inf], "")
        # Getting Study Status dataframe from SV, column Subject, Event Label and Event Date
        TXSUB_status_SV_df = data["DSSV"][
            [
                "Subject",
                "Event Group Label",
                "Event Label",
                "Event Date",
                "Did the protocol-specified study visit occur? (IG_NS_NA_DSSV1.CL_YS_NH_SVOCCUR_cl_YS_YN1)",
            ]
        ]
        TXSUB_status_SV_df = TXSUB_status_SV_df[
            TXSUB_status_SV_df[
                "Did the protocol-specified study visit occur? (IG_NS_NA_DSSV1.CL_YS_NH_SVOCCUR_cl_YS_YN1)"
            ]
            == "Yes"
        ]

        # Getting Study Status dataframe from DSSVLTFU, column Subject, Event Label and Event Date
        TXSUB_status_DSSVLTFU_df = data["DSSVLTFU"][
            [
                "Subject",
                "Event Group Label",
                "Event Label",
                "Event Date",
                "Did the protocol-specified study visit occur? (IG_NS_NA_DSSVLTFU1.CL_YS_NH_SVOCCUR_cl_YS_YN1)",
            ]
        ]
        TXSUB_status_DSSVLTFU_df = TXSUB_status_DSSVLTFU_df[
            TXSUB_status_DSSVLTFU_df[
                "Did the protocol-specified study visit occur? (IG_NS_NA_DSSVLTFU1.CL_YS_NH_SVOCCUR_cl_YS_YN1)"
            ]
            == "Yes"
        ]
        # Sort the dataframe by Subject and Event Date
        TXSUB_status_SV_df = TXSUB_status_SV_df.sort_values(
            by=["Subject", "Event Date"]
        )
        TXSUB_status_DSSVLTFU_df = TXSUB_status_DSSVLTFU_df.sort_values(
            by=["Subject", "Event Date"]
        )

        # For each unique subject, get the last row of the dataframe
        TXSUB_status_SV_df = TXSUB_status_SV_df.groupby("Subject").tail(1)
        TXSUB_status_DSSVLTFU_df = TXSUB_status_DSSVLTFU_df.groupby("Subject").tail(1)

        # Merge left with TXSUB_status_df
        TXSUB_status_df = pd.merge(
            TXSUB_status_df,
            TXSUB_status_SV_df[
                ["Subject", "Event Group Label", "Event Label", "Event Date"]
            ],
            on="Subject",
            how="left",
        )
        TXSUB_status_df = pd.merge(
            TXSUB_status_df,
            TXSUB_status_DSSVLTFU_df[
                ["Subject", "Event Group Label", "Event Label", "Event Date"]
            ],
            on="Subject",
            how="left",
        )
        DSEOS_df = data["DSEOS"][
            [
                "Subject",
                "Reason for End of Study? (IG_NS_NA_DSEOS2.CL_NS_YH_EOSCOD1_cl_NS_EOSREAS1)",
                "Provide Supportive Information (IG_NS_NA_DSEOS2.TX_NS_YH_EOSTERM)",
                "Principal Cause of Death (IG_NS_NA_DSEOS2.CL_NS_NH_PRCDTH_cl_NS_EOSCAD1)",
                "Specify Principal Cause of Death (IG_NS_NA_DSEOS2.TX_NS_NH_PRCDTHOS)",
                "End of Study Date (IG_NS_NA_DSEOS1.DT_NS_YH_EOSDAT)",
            ]
        ].copy()
        DSEOS_new_col_name = {
            "Reason for End of Study? (IG_NS_NA_DSEOS2.CL_NS_YH_EOSCOD1_cl_NS_EOSREAS1)": "Off-Study Reason",
            "Provide Supportive Information (IG_NS_NA_DSEOS2.TX_NS_YH_EOSTERM)": "Off-Study Reason sp1",
            "Principal Cause of Death (IG_NS_NA_DSEOS2.CL_NS_NH_PRCDTH_cl_NS_EOSCAD1)": "Off-Study Reason sp2",
            "Specify Principal Cause of Death (IG_NS_NA_DSEOS2.TX_NS_NH_PRCDTHOS)": "Off-Study Reason sp3",
            "End of Study Date (IG_NS_NA_DSEOS1.DT_NS_YH_EOSDAT)": "End of Study Date",
        }
        DSEOS_df = DSEOS_df.rename(columns=DSEOS_new_col_name)

        # Merge off-study reason
        DSEOS_df["Off-Study Reason"] = (
            DSEOS_df["Off-Study Reason"].fillna("")
            + " "
            + DSEOS_df["Off-Study Reason sp1"].fillna("")
            + DSEOS_df["Off-Study Reason sp2"].fillna("")
            + " "
            + DSEOS_df["Off-Study Reason sp3"].fillna("")
        )
        TXSUB_status_df = pd.merge(
            TXSUB_status_df,
            DSEOS_df[["Subject", "Off-Study Reason", "End of Study Date"]],
            on="Subject",
            how="left",
        )
        # Reason for entering LTFU (primary vs retreatment)
        dsinit_cols = [
            "Subject",
            "From which Phase is the Subject entering Long-Term Follow-Up? (IG_NS_NA_DSINITLF1.CL_NS_NH_PHASELTFU_cl_NS_PHASE1)",
            "Provide reason the Subject is entering into the Long-Term Follow-Up Phase (IG_NS_NA_DSINITLF2.CL_NS_NH_LTFUREAS_cl_NS_LTFURE1)",
            "Provide supportive information on the reason for entering Long-Term Follow-Up (IG_NS_NA_DSINITLF2.TX_NS_YH_LTFUREASSP)",
        ]
        dsinit_df = data.get("DSINITLF", pd.DataFrame(columns=dsinit_cols))[
            dsinit_cols
        ].copy()
        dsinit_df = dsinit_df.rename(
            columns={
                "From which Phase is the Subject entering Long-Term Follow-Up? (IG_NS_NA_DSINITLF1.CL_NS_NH_PHASELTFU_cl_NS_PHASE1)": "PhaseLTFU",
                "Provide reason the Subject is entering into the Long-Term Follow-Up Phase (IG_NS_NA_DSINITLF2.CL_NS_NH_LTFUREAS_cl_NS_LTFURE1)": "LTFU Reason",
                "Provide supportive information on the reason for entering Long-Term Follow-Up (IG_NS_NA_DSINITLF2.TX_NS_YH_LTFUREASSP)": "LTFU Support",
            }
        )

        dsinit_df["Combined Reason"] = dsinit_df.apply(combine_reason, axis=1)

        primary_map = (
            dsinit_df[dsinit_df["PhaseLTFU"] == "Primary Follow-Up"]
            .groupby("Subject")["Combined Reason"]
            .apply(lambda s: next((x for x in s if x.strip()), ""))
            .to_dict()
        )
        retx_map = (
            dsinit_df[dsinit_df["PhaseLTFU"] == "Retreatment"]
            .groupby("Subject")["Combined Reason"]
            .apply(lambda s: next((x for x in s if x.strip()), ""))
            .to_dict()
        )

        TXSUB_status_df["Reason for LTFU"] = (
            TXSUB_status_df["Subject"].map(primary_map).fillna("")
        )
        TXSUB_status_df["Reason for Retx LTFU"] = (
            TXSUB_status_df["Subject"].map(retx_map).fillna("")
        )

        TXSUB_status_df["Reason for LTFU"] = TXSUB_status_df["Reason for LTFU"].apply(
            fill_na_reason
        )
        TXSUB_status_df["Reason for Retx LTFU"] = TXSUB_status_df[
            "Reason for Retx LTFU"
        ].apply(fill_na_reason)
        # replaces all occurrences of NaN, positive infinity, and negative infinity with empty strings.
        TXSUB_status_df = TXSUB_status_df.replace([np.nan, np.inf, -np.inf], "N/A")
        # Convert date column to string in M-D-YYYY format without leading zeros
        # Replace "Event Date_y" with your actual column name
        TXSUB_status_df["Event Date_x"] = TXSUB_status_df["Event Date_x"].apply(
            lambda x: "N/A" if x == "N/A" else f"{x.month}-{x.day}-{x.year}"
        )
        TXSUB_status_df["Event Date_y"] = TXSUB_status_df["Event Date_y"].apply(
            lambda x: "N/A" if x == "N/A" else f"{x.month}-{x.day}-{x.year}"
        )

        # Apply formatting
        TXSUB_status_df["Event Date_x Str"] = TXSUB_status_df["Event Date_x"].apply(
            format_date
        )

        # Combine into new column
        TXSUB_status_df["Event Combined_x"] = TXSUB_status_df.apply(
            lambda row: (
                f"{row['Event Group Label_x']} ({row['Event Date_x Str']})"
                if row["Event Group Label_x"]
                in [
                    "Pre-Treatment Safety Visit",
                    "Pre-Retreatment Safety Visit",
                    "CSF-Ventricular Reservoir Placement",
                ]
                else f"{row['Event Group Label_x']}/{row['Event Label_x']} ({row['Event Date_x Str']})"
                if row["Event Group Label_x"]
                else ""
            ),
            axis=1,
        )
        # Apply formatting
        TXSUB_status_df["Event Date_y Str"] = TXSUB_status_df["Event Date_y"].apply(
            format_date
        )

        # Combine into new column
        TXSUB_status_df["Event Combined_y"] = TXSUB_status_df.apply(
            lambda row: (
                f"{row['Event Group Label_y']}/{row['Event Label_y']} ({row['Event Date_y Str']})"
                if row["Event Group Label_y"]
                else ""
            ).replace("N/A/N/A", "N/A"),
            axis=1,
        )
        # Apply formatting
        TXSUB_status_df["End of Study Date Str"] = TXSUB_status_df[
            "End of Study Date"
        ].apply(format_date)

        TXSUB_status_df["Last Study Visit Completed"] = TXSUB_status_df.apply(
            pick_last_visit, axis=1
        )

        # Separate End of Study date and reason for reporting
        TXSUB_status_df["End of Study Date"] = TXSUB_status_df["End of Study Date Str"]
        TXSUB_status_df["Reason for End of Study"] = TXSUB_status_df["Off-Study Reason"]
        TXSUB_status_df = TXSUB_status_df.drop(
            columns=[
                "Event Group Label_x",
                "Event Label_x",
                "Event Date_x",
                "Event Group Label_y",
                "Event Label_y",
                "Event Date_y",
                "Did the protocol-specified study visit occur? (IG_NS_NA_DSSVLTFU1.CL_YS_NH_SVOCCUR_cl_YS_YN1)",
                "Did the protocol-specified study visit occur? (IG_NS_NA_DSSVLTFU1.CL_YS_NH_SVOCCUR_cl_YS_YN1)",
                "Event Combined_x",
                "Event Combined_y",
                "Off-Study Reason",
                "End of Study Date Str",
            ],
            errors="ignore",  # avoids errors if any column is missing
        )

        # Add Study Status from the eligible status listing (if available) so it can be shown on the treated subjects sheet
        study_status_map = {}
        try:
            if (
                hasattr(self, "status_df")
                and "Event Group Name" in self.status_df.columns
            ):
                study_status_map = self.status_df.set_index("Subject")[
                    "Event Group Name"
                ].to_dict()
        except Exception:
            study_status_map = {}
        TXSUB_status_df["Study Status"] = (
            TXSUB_status_df["Subject"].map(study_status_map).fillna("")
        )

        # *Re-order the columns and remove the columns that are not needed
        TXSUB_status_df = TXSUB_status_df[
            [
                "Subject",
                "Study Status",
                "Reason for LTFU",
                "Reason for Retx LTFU",
                "Last Study Visit Completed",
                "End of Study Date",
                "Reason for End of Study",
                "AE",
                "SAE",
            ]
        ]
        # Safety stats for treated subjects
        AE_total_treated = get_stats_percentage("AE", TXSUB_status_df).T
        SAE_total_treated = get_stats_percentage("SAE", TXSUB_status_df).T
        self.safetyTX_total_df = pd.concat(
            [AE_total_treated, SAE_total_treated], axis=1
        )

        TXSUB_status_df = TXSUB_status_df.replace(
            [np.nan, np.inf, -np.inf], "N/A"
        ).replace([r"N/A\s*\(N/A\)", r"N/A\s+N/A"], "N/A", regex=True)

        return TXSUB_status_df

    def export(self, output_dir, output_file_name):
        data = self.data
        with pd.ExcelWriter(
            output_dir + "/" + output_file_name + ".xlsx", engine="xlsxwriter"
        ) as writer:
            ## * FORMATING AND COLORING
            formats = get_named_excel_formats(writer.book)
            bold_11_format = formats["bold_11_format"]
            bold_12_format = formats["bold_12_format"]
            bold_12_wrap_format = formats["bold_12_wrap_format"]
            bold_11_wrap_format = formats["bold_11_wrap_format"]
            normal_data_format = formats["normal_data_format"]
            # Create a format for a black cell
            if data["DM"]["Subject"].count() > 0:
                # DSMB-Demo Stats Table
                if self.enrollment_listing_df_output["Subject"].count() > 0:
                    # * WRITING DATA: LegalSex_list, Age_at_Consent_list, Race_list, Ethnicity_list
                    worksheet1 = writer.book.add_worksheet(
                        "DSMB-Demographics Statistics"
                    )

                    # * FORMAT DATA
                    for i in range(0, len(self.status_list)):
                        for j in range(0, len(self.LegalSex_list[i])):
                            for k in range(0, len(self.LegalSex_list[i].columns)):
                                worksheet1.write(
                                    j + 3,
                                    k + 1 + i * 4,
                                    self.LegalSex_list[i].iloc[j, k],
                                    normal_data_format,
                                )
                        for j in range(0, len(self.Age_at_Consent_list[i])):
                            for k in range(0, len(self.Age_at_Consent_list[i].columns)):
                                worksheet1.write(
                                    j + 8,
                                    k + 1 + i * 4,
                                    self.Age_at_Consent_list[i].iloc[j, k],
                                    normal_data_format,
                                )
                        for j in range(0, len(self.Race_list[i])):
                            for k in range(0, len(self.Race_list[i].columns)):
                                worksheet1.write(
                                    j + 12,
                                    k + 1 + i * 4,
                                    self.Race_list[i].iloc[j, k],
                                    normal_data_format,
                                )
                        for j in range(0, len(self.Ethnicity_list[i])):
                            for k in range(0, len(self.Ethnicity_list[i].columns)):
                                worksheet1.write(
                                    j + 22,
                                    k + 1 + i * 4,
                                    self.Ethnicity_list[i].iloc[j, k],
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
                        "F1:I1", "Cohort A Enrollment", bold_12_format
                    )
                    worksheet1.write(1, 0, "Status", bold_11_format)
                    for i in range(len(self.status_list)):
                        worksheet1.write(
                            1,
                            1 + i * 4,
                            "Total Consented\nN="
                            + str(self.status_list[i]["Total Consented"]),
                            bold_11_wrap_format,
                        )

                        worksheet1.write(
                            1,
                            2 + i * 4,
                            "Screen Fail\nN="
                            + str(self.status_list[i]["Screen Failed"]),
                            bold_11_wrap_format,
                        )
                        worksheet1.write(
                            1,
                            3 + i * 4,
                            "Eligible\nN=" + str(self.status_list[i]["Eligible"]),
                            bold_11_wrap_format,
                        )
                        worksheet1.write(
                            1,
                            4 + i * 4,
                            "Treated\nN=" + str(self.status_list[i]["Treated"]),
                            bold_11_wrap_format,
                        )

                    worksheet1.merge_range("A3:I3", "Legal Sex", bold_11_format)
                    worksheet1.merge_range("A8:I8", "Age at Consent", bold_11_format)
                    worksheet1.merge_range("A12:I12", "Race", bold_11_format)
                    worksheet1.merge_range("A22:I22", "Ethnicity", bold_11_format)

                    worksheet1.autofit()

                    # Enrollment Listing
                    # * WRITING DATA: enrollment_listing_df_output
                    worksheet2 = writer.book.add_worksheet("DSMB-Enrollment Listing")

                    # * WRITING HEADER AND FORMATTING
                    # Assuming 'enrollment_listing_df_output' is your DataFrame
                    self.enrollment_listing_df_output = (
                        self.enrollment_listing_df_output.replace(
                            [np.inf, -np.inf], np.nan
                        )
                    )  # Replace INF with NaN

                    self.enrollment_listing_df_output = (
                        self.enrollment_listing_df_output.fillna("")
                    )  # Replace NaN with a placeholder
                    # Replace column header for A1 from "Subject" to "Subject ID", columns name starting from 1 instead of 0
                    worksheet2.write("A1", "Subject ID", bold_12_wrap_format)
                    for i in range(1, len(self.enrollment_listing_df_output.columns)):
                        header = self.enrollment_listing_df_output.columns[i]
                        header_stripped = str(header).strip()
                        if header_stripped == "Screen Fail":
                            header = "Screen Fail (Y/N)"
                        elif header_stripped == "Treated":
                            header = "Treated (Y/N)"
                        worksheet2.write(0, i, header, bold_11_format)
                    # * FORMAT DATA
                    for i in range(0, len(self.enrollment_listing_df_output)):
                        for j in range(
                            0, len(self.enrollment_listing_df_output.columns)
                        ):
                            worksheet2.write(
                                i + 1,
                                j,
                                self.enrollment_listing_df_output.iloc[i, j],
                                normal_data_format,
                            )
                    # Autofit
                    worksheet2.autofit()

                    # DSMB-Status_Treated Subjects (moved up to follow Enrollment Listing)
                    # * WRITING AND FORMATING DATA (AE/SAE hidden from display)
                    txsub_display = self.TXSUB_status_df.drop(
                        columns=["AE", "SAE"], errors="ignore"
                    )
                    worksheet8 = writer.book.add_worksheet(
                        "DSMB-Status_Treated Subjects"
                    )
                    for i in range(0, len(txsub_display)):
                        for j in range(0, len(txsub_display.columns)):
                            worksheet8.write(
                                i + 2, j, txsub_display.iloc[i, j], normal_data_format
                            )

                    # * WRITING HEADER AND FORMATTING
                    worksheet8.merge_range("A1:A2", "Subject ID", bold_12_wrap_format)
                    worksheet8.merge_range("B1:B2", "Study Status", bold_12_wrap_format)
                    worksheet8.merge_range(
                        "C1:C2", "Reason for LTFU", bold_12_wrap_format
                    )
                    worksheet8.merge_range(
                        "D1:D2", "Reason for Retx LTFU", bold_12_wrap_format
                    )
                    worksheet8.merge_range(
                        "E1:E2", "Last Study Visit Completed", bold_12_wrap_format
                    )
                    worksheet8.merge_range(
                        "F1:F2", "End of Study Date", bold_12_wrap_format
                    )
                    worksheet8.merge_range(
                        "G1:G2", "Reason for End of Study", bold_12_wrap_format
                    )

                    # Safety Headers
                    safety_total_df_subject_count = len(
                        self.TXSUB_status_df["Subject"].unique()
                    )
                    worksheet8.merge_range(
                        "J1:M1",
                        "Safety Statistics (N="
                        + str(safety_total_df_subject_count)
                        + ")",
                        bold_12_wrap_format,
                    )
                    worksheet8.merge_range("J2:K2", "Adverse Events", bold_11_format)
                    worksheet8.merge_range(
                        "L2:M2", "Serious Adverse Events ", bold_11_format
                    )
                    worksheet8.write("J3", "Yes", bold_11_format)
                    worksheet8.write("K3", "No", bold_11_format)
                    worksheet8.write("L3", "Yes", bold_11_format)
                    worksheet8.write("M3", "No", bold_11_format)
                    worksheet8.write("I4", "Cohort A", bold_11_format)

                    # Safety Data
                    safety_df = getattr(
                        self, "safetyTX_total_df", self.safetyCH1_total_df
                    )
                    for i in range(0, len(safety_df)):
                        for j in range(0, len(safety_df.columns)):
                            worksheet8.write(
                                i + 3,  # row 4 (1-based)
                                j + 9,  # start at column J
                                safety_df.iloc[i, j],
                                normal_data_format,
                            )

                    worksheet8.autofit()

                    # Study Tx Statistics
                    worksheet4 = writer.book.add_worksheet("DSMB-Treatment Statistics")

                    # * FORMATING DATA
                    # Cohort A
                    for i in range(0, len(self.infusion_statA)):
                        for j in range(0, len(self.infusion_statA.columns)):
                            worksheet4.write(
                                i + 3,
                                j + 1,
                                self.infusion_statA.iloc[i, j],
                                normal_data_format,
                            )

                    # * WRITING HEADER AND FORMATTING
                    stat_order = ["Mean SD", "Median", "Range"]

                    worksheet4.merge_range(
                        "B1:D1", "Cells Administered", bold_12_wrap_format
                    )
                    worksheet4.merge_range(
                        "E1:G1", "Transduction Efficiency", bold_12_wrap_format
                    )
                    worksheet4.write("B2", "Total Cell Dose", bold_12_wrap_format)
                    worksheet4.write(
                        "C2", "CART-EGFR-IL13Ra2 Cell Dose", bold_12_wrap_format
                    )
                    worksheet4.write("D2", "Met Target Dose (Y/N)", bold_12_wrap_format)
                    worksheet4.write("E2", "%scFV (EGFR)", bold_12_wrap_format)
                    worksheet4.write(
                        "F2",
                        "Met Target % scFV (EGFR) Flow (Y/N) (≥2%)",
                        bold_12_wrap_format,
                    )
                    worksheet4.write("G2", "%scFV (IL13Ra2)", bold_12_wrap_format)
                    worksheet4.merge_range(
                        "A3:G3",
                        "Cohort A (N=" + str(self.infusion_count[0]) + ")",
                        bold_12_wrap_format,
                    )

                    # Merge and format data
                    worksheet4.merge_range(
                        "D4:D6", self.infusion_statA.iloc[0, 2], normal_data_format
                    )
                    worksheet4.merge_range(
                        "F4:F6", self.infusion_statA.iloc[0, 4], normal_data_format
                    )

                    for i in range(0, len(stat_order)):
                        worksheet4.write(
                            i + 3, 0, stat_order[i], bold_11_format
                        )  # Cohort A

                    # * Autofit
                    worksheet4.autofit()

                    # DSMB-Infusion Listing
                    worksheet5 = writer.book.add_worksheet("DSMB-Treatment Listing")
                    # * WRITING AND FORMATING DATA
                    for i in range(0, len(self.infusion_df)):
                        for j in range(0, len(self.infusion_df.columns)):
                            worksheet5.write(
                                i + 2,
                                j,
                                self.infusion_df.iloc[i, j],
                                normal_data_format,
                            )

                    # * WRITING HEADER AND FORMATTING
                    worksheet5.merge_range("A1:A2", "Subject ID", bold_12_wrap_format)
                    worksheet5.merge_range(
                        "B1:B2", "Cohort Assignment", bold_12_wrap_format
                    )
                    worksheet5.merge_range(
                        "C1:C2", "Dose Level Assignment", bold_12_wrap_format
                    )
                    worksheet5.merge_range(
                        "D1:D2", "Study Treatment Date", bold_12_wrap_format
                    )
                    worksheet5.merge_range(
                        "E1:F1", "Product Administration Volumes", bold_12_wrap_format
                    )
                    worksheet5.merge_range(
                        "G1:I1", "Cells Administered", bold_12_wrap_format
                    )
                    worksheet5.merge_range(
                        "J1:L1", "Transduction Efficiency", bold_12_wrap_format
                    )
                    worksheet5.write("E2", "Volume CSF Removed", bold_12_wrap_format)
                    worksheet5.write("F2", "Volume Administered", bold_12_wrap_format)
                    worksheet5.write("G2", "Total Cell Dose", bold_12_wrap_format)
                    worksheet5.write(
                        "H2", "CART-EGFR-IL13Ra2 Cell Dose", bold_12_wrap_format
                    )
                    worksheet5.write("I2", "Met Target Dose (Y/N)", bold_12_wrap_format)
                    worksheet5.write("J2", "%scFV (EGFR)", bold_12_wrap_format)
                    worksheet5.write(
                        "K2",
                        "Met Target % scFV (EGFR) Flow (Y/N) (≥2%)",
                        bold_12_wrap_format,
                    )
                    worksheet5.write("L2", "%scFV (IL13Ra2)", bold_12_wrap_format)

                    worksheet5.autofit()

                    worksheet9 = writer.book.add_worksheet("DSMB-CART Detection_Tissue")

                    # * WRITING HEADER AND FORMATTING
                    worksheet9.write("A1", "Subject ID", bold_12_wrap_format)
                    worksheet9.write("B1", "Study Day", bold_12_wrap_format)
                    worksheet9.write("C1", "Sample Type", bold_12_wrap_format)
                    worksheet9.write(
                        "D1", "Site of Lesion/Laterality", bold_12_wrap_format
                    )
                    worksheet9.write("E1", "Results", bold_12_wrap_format)

                    worksheet9.autofit()

                    # DSMB-Retreatment Listing
                    worksheet6 = writer.book.add_worksheet("DSMB-Retreatment Listing")
                    # * WRITING AND FORMATING DATA
                    for i in range(0, len(self.infusionR_df)):
                        for j in range(0, len(self.infusionR_df.columns)):
                            worksheet6.write(
                                i + 2,
                                j,
                                self.infusionR_df.iloc[i, j],
                                normal_data_format,
                            )

                    # * WRITING HEADER AND FORMATTING
                    worksheet6.merge_range("A1:A2", "Subject ID", bold_12_wrap_format)
                    worksheet6.merge_range(
                        "B1:B2", "Cohort Assignment", bold_12_wrap_format
                    )
                    worksheet6.merge_range(
                        "C1:C2", "Dose Level Assignment", bold_12_wrap_format
                    )
                    worksheet6.merge_range(
                        "D1:D2", "Study Retreatment Date", bold_12_wrap_format
                    )
                    worksheet6.merge_range(
                        "E1:F1", "Product Administration", bold_12_wrap_format
                    )
                    worksheet6.merge_range(
                        "G1:H1", "Cells Administered", bold_12_wrap_format
                    )
                    worksheet6.merge_range(
                        "I1:K1", "Transduction Efficiency", bold_12_wrap_format
                    )
                    worksheet6.write("E2", "Volume CSF Removed", bold_12_wrap_format)
                    worksheet6.write("F2", "Volume Administered", bold_12_wrap_format)
                    worksheet6.write("G2", "Total Cell Dose", bold_12_wrap_format)
                    worksheet6.write(
                        "H2", "CART-EGFR-IL13Ra2 Cell Dose", bold_12_wrap_format
                    )
                    worksheet6.write("I2", "%scFV (EGFR)", bold_12_wrap_format)
                    worksheet6.write(
                        "J2",
                        "Met Target % scFV (EGFR) Flow (Y/N) (≥2%)",
                        bold_12_wrap_format,
                    )
                    worksheet6.write("K2", "%scFV (Il13Ra2)", bold_12_wrap_format)

                    # Autofit
                    worksheet6.autofit()

                    # DSMB-EGFR_MGMT
                    worksheet7 = writer.book.add_worksheet("DSMB-EGFR_MGMT")

                    # * WRITING HEADER AND FORMATTING
                    # Assuming 'EGFR_listing_df_output' is your DataFrame
                    self.EGFR_listing_df_output = self.EGFR_listing_df_output.replace(
                        [np.inf, -np.inf], np.nan
                    )  # Replace INF with NaN

                    self.EGFR_listing_df_output = self.EGFR_listing_df_output.fillna(
                        ""
                    )  # Replace NaN with a placeholder
                    # Replace column header for A1 from "Subject" to "Subject ID", columns name starting from 1 instead of 0
                    worksheet7.write("A1", "Subject ID", bold_12_wrap_format)
                    for i in range(1, len(self.EGFR_listing_df_output.columns)):
                        worksheet7.write(
                            0, i, self.EGFR_listing_df_output.columns[i], bold_11_format
                        )
                    # * FORMAT DATA
                    for i in range(0, len(self.EGFR_listing_df_output)):
                        for j in range(0, len(self.EGFR_listing_df_output.columns)):
                            worksheet7.write(
                                i + 1,
                                j,
                                self.EGFR_listing_df_output.iloc[i, j],
                                normal_data_format,
                            )
                    # Autofit
                    worksheet7.autofit()
