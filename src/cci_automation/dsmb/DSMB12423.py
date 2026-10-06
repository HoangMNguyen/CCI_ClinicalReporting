import numpy as np
import pandas as pd

from cci_automation.dsmb.DSMB_util import (
    add_rename_column_corelisting,
    convert_float_2_sci_notation,
    get_stats_df,
    get_stats_perc_df,
    get_stats_percentage,
    get_stats_percentage2,
)
from cci_automation.util import (
    add_rename_column_df,
    age_calculation,
    convert_integers_to_strings,
    get_data_from_dict,
    remove_leading_zeros_from_dates,
)


class DSMB12423:
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
        # process the enrollment listing
        self.enrollment_listing_df_output, self.enrollment_listing_df = (
            self.enrollment_listing()
        )
        self.enrollment_stat_table(self.enrollment_listing_df)
        self.infusion_df, self.infusionR_df = self.infusion_listing()
        self.infusion_stats(self.infusion_df, self.infusionR_df)
        self.response_listing()
        self.response_stats()
        self.export(self.output_dir, self.output_file_name)

    def enrollment_listing(self):
        data = self.data
        # *: PREPARE DATA FOR ENROLLMENT LISTING

        # create dictionary for enrollment listing
        input_dict = {
            "DM": {
                "Legal Sex (IG_NS_NA_DM1.CL_NS_YH_SEX_cl_NS_DMSEX1)": "Legal Sex",
                "Sex Assigned at Birth (IG_NS_NA_DM1.CL_NS_NH_BRTHSEX_cl_NS_DMSEX3)": "Sex Assigned at Birth",
                "Gender Identity (IG_NS_NA_DM1.CL_NS_NH_GENDERID_cl_NS_DMSEX2)": "Gender Identity",
                "Specify Other Gender Identity (IG_NS_NA_DM1.TX_NS_NH_GENDERIDOTH)": "Other Gender",
                "Date of Birth (IG_NS_NA_DM1.DT_NS_NH_BRTHDAT)": "Date of Birth",
                "Apheresis Consent Date (IG_NS_NA_DM1.DT_NS_YH_RFICDAT)": "Consent Date",
                "Race (IG_NS_NA_DM1.CL_NS_YH_RACE_cl_NS_DMRACE1)": "Race",
                "Specify Other or Multiple Races (IG_NS_NA_DM1.TX_NS_NH_RACEOTH)": "Other Race",
                "Ethnicity (IG_NS_NA_DM1.CL_NS_NH_ETHNIC_cl_NS_DMETHNIC1)": "Ethnicity",
            },
            "DSCA": {
                "Cohort Assignment (IG_NS_NA_DSCA1.CL_NS_YH_CACHASCOD_cl_NS_COHORT1)": "Cohort Assignment"
            },
            "DSDLA": {
                "Dose Level Assignment (IG_NS_NA_DSDLA1.CL_NS_YH_DLADOSELV_cl_NS_DOSELV1)": "Dose Level"
            },
            "IE": {
                "Main Consent Date (IG_NS_NA_IE1.DT_NS_NH_MAINCDAT)": "Main Consent Date",
                "Subject Meets All Study Eligibility (IG_NS_NA_IE3.CL_NS_YH_ELIGYN_cl_YS_YN1)": "Subject meets all study eligibility?",
                "Other Screen Fail Reason (IG_NS_NA_IE4.TX_NS_YH_OTHRSFREAS)": "SF3",
                "Screen Failure Reason (IG_NS_NA_IE4.CL_NS_YH_IECAT_cl_NS_IEREASSF1)": "Reason for Screen Failure",
                "Select the Primary Inclusion Criterion Excluding this Subject (IG_NS_NA_IE4.CL_NS_NH_ITESTCD_cl_NS_IEINCL1)": "SF1",
                "Select the Primary Exclusion Criterion Excluding this Subject (IG_NS_NA_IE4.CL_NS_NH_ETESTCD_cl_NS_IEEXCL1)": "SF2",
            },
            "EXINF": {
                "Event Group Label": "Event Group Label",
                "Was infusion administered? (IG_NS_NA_EXINF1.CL_NS_NH_INFADMIN_cl_YS_YN1)": "Infused",
            },
            "DSEOS": {
                "End of Study Date (IG_NS_NA_DSEOS1.DT_NS_YH_EOSDAT)": "End of Study Date",
                "Reason for End of Study? (IG_NS_NA_DSEOS2.CL_NS_NH_EOSCOD1_cl_NS_EOSREAS1)": "End of Study Reason",
                "Provide Supportive Information (IG_NS_NA_DSEOS2.TX_NS_YH_EOSTERM)": "Supportive Information",
            },
            "NHLMHDIAG": {
                "Primary Diagnosis of NHL (IG_NS_NA_NHLMHDIAG1.CL_NS_YH_NHLDIAG_cl_NS_NHLDIAG1)": "Disease NHL",
                "Specify Other Diagnosis (IG_NS_NA_NHLMHDIAG1.TX_NS_NH_NHLDIAGOTH)": "Disease NHL2",
            },
        }

        enrollment_df = get_data_from_dict(data, input_dict)
        enrollment_df = age_calculation(
            enrollment_df,
            "Age at Consent",
            "Date of Birth",
            "Consent Date",
            "Main Consent Date",
        )
        # fill NaN with empty string
        enrollment_df = enrollment_df.fillna("")
        enrollment_df.loc[
            enrollment_df["Disease NHL"] == "Other",
            "Disease NHL",
        ] = ""
        enrollment_df["Disease Type"] = (
            enrollment_df["Disease NHL"].fillna("")
            + " "
            + enrollment_df["Disease NHL2"].fillna("")
        )
        enrollment_df["Disease Type"] = enrollment_df["Disease Type"].fillna("")

        # Convert the entire column to string to avoid data type issues
        enrollment_df["Reason for Screen Failure"] = enrollment_df[
            "Reason for Screen Failure"
        ].astype(str)

        # if "Reason for Screen Failure" in enrollment_df.columns equal "Other", replace the value with SF3
        mask = enrollment_df["Reason for Screen Failure"] == "Other"
        # Replace "Other" with the corresponding values from the "SF3" column
        enrollment_df.loc[mask, "Reason for Screen Failure"] = enrollment_df.loc[
            mask, "SF3"
        ]

        # if "Reason for Screen Failure" in enrollment_df.columns equal "Inclusion Criteria", concat the value of the column with "SF1"
        # Create a mask for rows where "Reason for Screen Failure" is "Inclusion Criteria"
        mask = (enrollment_df["Reason for Screen Failure"] == "Inclusion Criteria") & (
            enrollment_df["SF1"] != ""
        )
        # Use the mask to update the "Reason for Screen Failure" column
        enrollment_df.loc[mask, "Reason for Screen Failure"] = (
            enrollment_df.loc[mask, "Reason for Screen Failure"]
            + " "
            + enrollment_df.loc[mask, "SF1"].astype(str)
        )

        # Create a mask for rows where "Reason for Screen Failure" is "Exclusion Criteria" and "SF2" is not empty
        mask = (enrollment_df["Reason for Screen Failure"] == "Exclusion Criteria") & (
            enrollment_df["SF2"] != ""
        )

        # Use the mask to update the "Reason for Screen Failure" column
        enrollment_df.loc[mask, "Reason for Screen Failure"] = (
            enrollment_df.loc[mask, "Reason for Screen Failure"]
            + " "
            + enrollment_df.loc[mask, "SF2"].astype(str)
        )

        # if subject does not have IE data, check if the subject has DSEOS "End of Study Date" data. If yes, then the subject is "No" for "Subject meets all study eligibility?"

        enrollment_df.loc[
            (enrollment_df["Subject meets all study eligibility?"] != "Yes")
            & (enrollment_df["End of Study Date"].notna()),
            "Subject meets all study eligibility?",
        ] = "No"
        enrollment_df.loc[
            (enrollment_df["Subject meets all study eligibility?"] != "Yes")
            & (enrollment_df["End of Study Date"].notna()),
            "Reason for Screen Failure",
        ] = enrollment_df["Supportive Information"]
        # drop the columns that are not needed
        enrollment_df = enrollment_df.drop(
            columns=[
                "Disease NHL",
                "Disease NHL2",
                "SF1",
                "SF2",
                "SF3",
                "Supportive Information",
                "End of Study Reason",
            ]
        )
        enrollment_df = enrollment_df.drop(columns=["Event Group Label"])
        # Update 'Infused' column based on the conditions:
        enrollment_df.loc[
            (enrollment_df["Infused"] != "Yes")
            & (enrollment_df["End of Study Date"].isnull()),
            "Infused",
        ] = "Pending"
        enrollment_df.loc[
            (enrollment_df["Infused"] != "Yes")
            & (~enrollment_df["End of Study Date"].isnull()),
            "Infused",
        ] = "No"
        enrollment_df = enrollment_df.drop(columns=["End of Study Date"])
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
        # If Race is "Other", replace the value with "Other Race"
        enrollment_output_df.loc[
            enrollment_output_df["Race"] == "Other",
            "Race",
        ] = enrollment_output_df["Other Race"]
        # *Re-order the columns and remove the columns that are not needed
        enrollment_output_df = enrollment_output_df[
            [
                "Subject",
                "Cohort Assignment",
                "Disease Type",
                "Dose Level",
                "Legal Sex",
                "Sex Assigned at Birth",
                "Gender Identity",
                "Age at Consent",
                "Race",
                "Ethnicity",
                "Subject meets all study eligibility?",
                "Reason for Screen Failure",
                "Infused",
            ]
        ]
        return enrollment_output_df, enrollment_df

    def enrollment_stat_table(self, enrollment_df):
        # Demo Stats Table
        # !Update this filter options to each cohort
        filter_options = [
            enrollment_df["Consent Date"].notna()
            | enrollment_df["Main Consent Date"].notna(),
            enrollment_df["Cohort Assignment"] == "Cohort A: Non-Hodgkin Lymphoma",
        ]
        self.status_list = []
        self.LegalSex_list = []
        self.Age_at_Consent_list = []
        self.Race_list = []
        self.Ethnicity_list = []

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
            ## Screen Failed
            SF_df = filtered_df[
                filtered_df["Subject meets all study eligibility?"] == "No"
            ].copy()
            SF = SF_df["Subject"].count()
            ## Eligible
            EL_df = filtered_df[
                filtered_df["Subject meets all study eligibility?"] == "Yes"
            ].copy()
            EL = EL_df["Subject"].count()
            ## Infused
            INF_df = filtered_df[filtered_df["Infused"] == "Yes"].copy()
            INF = INF_df["Subject"].count()

            # Define a dictionary containing the status of each variable
            self.status_list.append(
                {
                    "Total Consented": TT,
                    "Screen Failed": SF,
                    "Eligible": EL,
                    "Infused": INF,
                }
            )

            # Calculate the stats for the filtered dataframe
            Legal_Sex_Codelist = ["Male", "Female", "X (Nonbinary)", "Not Reported"]
            self.LegalSex_list.append(
                get_stats_percentage2(
                    "Legal Sex", Legal_Sex_Codelist, TT_df, SF_df, EL_df, INF_df
                )
            )
            self.Age_at_Consent_list.append(
                get_stats_df("Age at Consent", TT_df, SF_df, EL_df, INF_df)
            )
            self.Race_list.append(
                get_stats_percentage("Race", TT_df, SF_df, EL_df, INF_df)
            )
            self.Ethnicity_list.append(
                get_stats_percentage("Ethnicity", TT_df, SF_df, EL_df, INF_df)
            )

    def infusion_listing(self):
        data = self.data
        # INFUSION LISTING
        # adding Target Cell Dose dictionary
        # !: Update this dictionary to the new study
        TCD_dict = {
            "Dose Level -1 (DL-1)": 2000000,
            "Dose Level 1a (DL1a)": 5000000,
            "Dose Level 1 (DL1)": 7000000,
            "Dose Level 2 (DL2)": 20000000,
            "Dose Level 3 (DL3)": 60000000,
            "Not Assigned": "Not Assigned",
        }

        # *: PREPARE DATA FOR INFUSION LISTING
        EXCHMO_df = data["EXCHMO"].copy()
        EXCHMO_df = EXCHMO_df.sort_values(
            [
                "Subject",
                "Event Group Label",
                "Medication (IG_NS_NA_EXCHMO2.CL_NS_NH_EXCCAT_cl_NS_EXCCAT1)",
            ]
        )
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
        # replace the Event Group Label with Day 0 and Day 0-R
        grouped_df.loc[
            (grouped_df["Event Group Label"] == "Lymphodepleting Chemotherapy"),
            "Event Group Label",
        ] = "Day 0"
        grouped_df.loc[
            (
                grouped_df["Event Group Label"]
                == "Retreatment Lymphodepleting Chemotherapy"
            ),
            "Event Group Label",
        ] = "Day 0-R"
        # reassign the dataframe to EXCHMO_df with subject, Study Day, and Medication
        EXCHMO_df = grouped_df

        # create dictionary for enrollment listing
        input_dict = {
            "EXINF": {
                "Event Group Label": "Event Group Label",
                "Infusion Date (IG_NS_NA_EXINF1.DT_NS_NH_INFDAT)": "Date of TmCD19-IL18 Infusion",
                "CAR T Cell Dose Administered (IG_NS_NA_EXINF1.NM_NS_NH_TDOS)": "Total TmCD19-IL18 CAR T Cell Dose Administered",
                "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TDOSXP_cl_YS_EX10POW1)": "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TDOSXP_cl_YS_EX10POW1)",
                "Total Cell Dose Administered (IG_NS_NA_EXINF1.NM_NS_NH_TOTDOS)": "Total Cell Dose Administered",
                "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TOTDOSXP_cl_YS_EX10POW1)": "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TOTDOSXP_cl_YS_EX10POW1)",
                "Transduction Efficiency (%) (IG_NS_NA_EXINF1.NM_NS_NH_TRANSEFFP)": "%scFv Flow",
            },
            "DSCA": {
                "Cohort Assignment (IG_NS_NA_DSCA1.CL_NS_YH_CACHASCOD_cl_NS_COHORT1)": "Cohort Assignment"
            },
            "DSDLA": {
                "Dose Level Assignment (IG_NS_NA_DSDLA1.CL_NS_YH_DLADOSELV_cl_NS_DOSELV1)": "Dose Level Assignment"
            },
        }
        raw_infusion_df = get_data_from_dict(data, input_dict, "EXINF")
        # convert the date to datetime object and format it to MM-DD-YYYY
        raw_infusion_df = remove_leading_zeros_from_dates(raw_infusion_df)

        # INFUSION LISTING Day 0

        infusion_df = raw_infusion_df[
            raw_infusion_df["Event Group Label"] == "Day 0"
        ].copy()
        # Lymphodepleting Chemotherapy Regimen
        infusion_df = add_rename_column_df(
            infusion_df,
            EXCHMO_df[EXCHMO_df["Event Group Label"] == "Day 0"],
            "Medication (IG_NS_NA_EXCHMO2.CL_NS_NH_EXCCAT_cl_NS_EXCCAT1)",
            "Lymphodepleting Chemotherapy Regimen",
        )

        # adding Target Cell Dose using TCD_dict
        infusion_df["Target Cell Dose"] = infusion_df["Dose Level Assignment"].map(
            TCD_dict
        )

        # combine Total TmCD19-IL18 CAR T Cell Dose Administered and x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TDOSXP_cl_YS_EX10POW1) columns, compare the new value with 'Target Cell Dose', and convert the Total TmCD19-IL18 CAR T Cell Dose Administered column to string
        infusion_df["Total TmCD19-IL18 CAR T Cell Dose Administered"] = infusion_df[
            "Total TmCD19-IL18 CAR T Cell Dose Administered"
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

        # Adding Met Target Dose column based on the condition of Total Cell Dose Administered and Total TmCD19-IL18 CAR T Cell Dose Administered if 'Target Cell Dose' is integer
        infusion_df["Met Target Dose"] = infusion_df.apply(
            lambda row: (
                "Y"
                if isinstance(row["Target Cell Dose"], int)
                and row["Total TmCD19-IL18 CAR T Cell Dose Administered"]
                >= row["Target Cell Dose"]
                else ""
            ),
            axis=1,
        )
        infusion_df["Met Target Dose"] = infusion_df.apply(
            lambda row: (
                "N"
                if isinstance(row["Target Cell Dose"], int)
                and row["Total TmCD19-IL18 CAR T Cell Dose Administered"]
                < row["Target Cell Dose"]
                else row["Met Target Dose"]
            ),
            axis=1,
        )

        # adding Met Target %scFv and fillter out the rows that have NaN in Met Target %scFv
        infusion_df["Met Target %scFv"] = infusion_df[
            infusion_df["%scFv Flow"].notna()
        ]["%scFv Flow"].apply(lambda x: "Y" if x >= 2 else "N")
        # fill NaN with empty string
        infusion_df = infusion_df.fillna(
            "",
        ).infer_objects()

        # Only keep the rows that have Event Group Label
        infusion_df = infusion_df[infusion_df["Event Group Label"] != ""]

        # *Re-order the columns and remove the columns that are not needed
        infusion_df = infusion_df[
            [
                "Subject",
                "Event Group Label",
                "Cohort Assignment",
                "Dose Level Assignment",
                "Lymphodepleting Chemotherapy Regimen",
                "Date of TmCD19-IL18 Infusion",
                "Target Cell Dose",
                "Total TmCD19-IL18 CAR T Cell Dose Administered",
                "Total Cell Dose Administered",
                "Met Target Dose",
                "%scFv Flow",
                "Met Target %scFv",
            ]
        ]

        # Infusion Listing Day 0-R
        infusionR_df = raw_infusion_df[
            raw_infusion_df["Event Group Label"] == "Day 0-R"
        ].copy()
        # Lymphodepleting Chemotherapy Regimen
        infusionR_df = add_rename_column_df(
            infusionR_df,
            EXCHMO_df[EXCHMO_df["Event Group Label"] == "Day 0-R"],
            "Medication (IG_NS_NA_EXCHMO2.CL_NS_NH_EXCCAT_cl_NS_EXCCAT1)",
            "Lymphodepleting Chemotherapy Regimen",
        )
        # combine Total TmCD19-IL18 CAR T Cell Dose Administered and x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TDOSXP_cl_YS_EX10POW1) columns, compare the new value with 'Target Cell Dose', and convert the Total TmCD19-IL18 CAR T Cell Dose Administered column to string
        infusionR_df["Total TmCD19-IL18 CAR T Cell Dose Administered"] = infusionR_df[
            "Total TmCD19-IL18 CAR T Cell Dose Administered"
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

        infusionR_df["Total Cell Dose Administered"] = infusionR_df[
            "Total Cell Dose Administered"
        ].multiply(
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

        # adding Met Target %scFv
        infusionR_df = add_rename_column_corelisting(
            infusionR_df,
            data,
            "EXINF",
            "Transduction Efficiency (%) (IG_NS_NA_EXINF1.NM_NS_NH_TRANSEFFP)",
            "Met Target %scFv",
            "Subject",
            "Event Group Label",
        )
        # adding Met Target %scFv and fillter out the rows that have NaN in Met Target %scFv
        infusion_df["Met Target %scFv"] = infusion_df[
            infusion_df["%scFv Flow"].notna()
        ]["%scFv Flow"].apply(lambda x: "Y" if x >= 2 else "N")
        # fill NaN with empty string
        infusionR_df = infusionR_df.fillna("")

        # Only keep the rows that have Event Group Label
        infusionR_df = infusionR_df[infusionR_df["Event Group Label"] != ""]

        # Order the columns
        infusionR_df = infusionR_df[
            [
                "Subject",
                "Event Group Label",
                "Cohort Assignment",
                "Lymphodepleting Chemotherapy Regimen",
                "Date of TmCD19-IL18 Infusion",
                "Total TmCD19-IL18 CAR T Cell Dose Administered",
                "Total Cell Dose Administered",
                "%scFv Flow",
                "Met Target %scFv",
            ]
        ]
        return infusion_df, infusionR_df

    def infusion_stats(self, infusion_df, infusionR_df):
        # INFUSION STATISTICS
        infusion_count = []
        # * Cohort A: Non-Hodgkin Lymphoma
        # Create a new dataframe for Total huCAR T Cell Dose Administered table with infusion_df
        infusionA_df = self.infusion_df[
            self.infusion_df["Cohort Assignment"] == "Cohort A: Non-Hodgkin Lymphoma"
        ]
        infusion_statA1 = get_stats_df(
            "Total TmCD19-IL18 CAR T Cell Dose Administered", infusionA_df
        )
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
        met_target_count = infusionA_df[
            infusionA_df["Met Target %scFv"] == "Y"
        ].count()["Subject"]
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
        self.infusion_statA = infusion_statA
        infusion_count.append(total_subject_count)
        self.infusion_count = infusion_count

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
        infusion_df["Total TmCD19-IL18 CAR T Cell Dose Administered"] = infusion_df[
            "Total TmCD19-IL18 CAR T Cell Dose Administered"
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

        # Day 0-R
        # Convert the columns to scientific notation if the value is not NaN
        infusionR_df["Total TmCD19-IL18 CAR T Cell Dose Administered"] = infusionR_df[
            "Total TmCD19-IL18 CAR T Cell Dose Administered"
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

    def response_listing(self):
        data = self.data
        # PREPARE
        # Disease Response NHL PET based dictionary
        DR_NHL_PET_dict = {
            "Complete Metabolic Response (CMR)": 1,
            "Partial Metabolic Response (PMR)": 2,
            "No Metabolic Response (NMR)": 3,
            "Progressive Metabolic Disease (PMD)": 5,
            "Not Assessed": 6,
            "Not Reported": 10,
        }
        # Disease Response NHL CT based dictionary
        DR_NHL_CT_dict = {
            "Complete Radiologic Response (CR)": 1,
            "Partial Response (PR)": 2,
            "Stable Disease (SD)": 3,
            "Progressive Disease (PD)": 5,
            "Not Assessed": 6,
            "Not Reported": 10,
        }

        # Event Label Update dictionary for cohort A
        event_A_dict = {
            "Primary Treatment and Follow-up": "Primary Treatment",
            "Primary Retreatment and Follow-up": "Primary Retreatment",
            "Pre-Retreatment Safety Visit": "Pre-Retreatment",
            "Long Term Follow-up Months 3-60": "Long Term Follow-up",
            "Retreatment Long Term Follow-up Months 3-60": "Retreatment Long Term Follow-up",
        }

        # Get data from Initiation of Long Term Follow up
        PD_df = data["DSINITLF"][
            [
                "Subject",
                "From which Phase is the Subject entering Long-Term Follow-Up? (IG_NS_NA_DSINITLF1.CL_NS_NH_PHASELTFU_cl_NS_PHASE1)",
                "End of Primary Follow-Up Date (IG_NS_NA_DSINITLF1.DT_NS_YH_INITLFPFUENDDAT)",
                "Provide reason the Subject is entering into the Long-Term Follow-Up Phase (IG_NS_NA_DSINITLF2.CL_NS_NH_LTFUREAS_cl_NS_LTFURE1)",
            ]
        ].copy()
        # Filter the data to only subject with 'Disease progression' in Provide reason the Subject is entering into the Long-Term Follow-Up Phase (IG_NS_NA_DSINITLF2.CL_NS_NH_LTFUREAS_cl_NS_LTFURE1) column
        PD_df = PD_df[
            PD_df[
                "Provide reason the Subject is entering into the Long-Term Follow-Up Phase (IG_NS_NA_DSINITLF2.CL_NS_NH_LTFUREAS_cl_NS_LTFURE1)"
            ]
            == "Disease progression"
        ]
        # Filter the data to subject in Primary Follow up
        PD_df = PD_df[
            PD_df[
                "From which Phase is the Subject entering Long-Term Follow-Up? (IG_NS_NA_DSINITLF1.CL_NS_NH_PHASELTFU_cl_NS_PHASE1)"
            ]
            == "Primary Follow-Up"
        ]
        # Convert End of Primary Follow-Up Date (IG_NS_NA_DSINITLF1.DT_NS_YH_INITLFPFUENDDAT) to datetime object
        PD_df[
            "End of Primary Follow-Up Date (IG_NS_NA_DSINITLF1.DT_NS_YH_INITLFPFUENDDAT)"
        ] = pd.to_datetime(
            PD_df[
                "End of Primary Follow-Up Date (IG_NS_NA_DSINITLF1.DT_NS_YH_INITLFPFUENDDAT)"
            ]
        )

        # Get data from Initiation of Long Term Follow up
        PD_Retx_df = data["DSINITLF"][
            [
                "Subject",
                "From which Phase is the Subject entering Long-Term Follow-Up? (IG_NS_NA_DSINITLF1.CL_NS_NH_PHASELTFU_cl_NS_PHASE1)",
                "End of Retreatment Date (IG_NS_NA_DSINITLF1.DT_NS_YH_RETXENDDAT)",
                "Provide reason the Subject is entering into the Long-Term Follow-Up Phase (IG_NS_NA_DSINITLF2.CL_NS_NH_LTFUREAS_cl_NS_LTFURE1)",
            ]
        ].copy()
        # Filter the data to only subject with 'Disease progression' in Provide reason the Subject is entering into the Long-Term Follow-Up Phase (IG_NS_NA_DSINITLF2.CL_NS_NH_LTFUREAS_cl_NS_LTFURE1) column
        PD_Retx_df = PD_Retx_df[
            PD_Retx_df[
                "Provide reason the Subject is entering into the Long-Term Follow-Up Phase (IG_NS_NA_DSINITLF2.CL_NS_NH_LTFUREAS_cl_NS_LTFURE1)"
            ]
            == "Disease progression"
        ]
        # Filter the data to subject in Retreatment
        PD_Retx_df = PD_Retx_df[
            PD_Retx_df[
                "From which Phase is the Subject entering Long-Term Follow-Up? (IG_NS_NA_DSINITLF1.CL_NS_NH_PHASELTFU_cl_NS_PHASE1)"
            ]
            == "Retreatment"
        ]
        # Convert End of Retreatment Date (IG_NS_NA_DSINITLF1.DT_NS_YH_RETXENDDAT) to datetime object
        PD_Retx_df[
            "End of Retreatment Date (IG_NS_NA_DSINITLF1.DT_NS_YH_RETXENDDAT)"
        ] = pd.to_datetime(
            PD_Retx_df[
                "End of Retreatment Date (IG_NS_NA_DSINITLF1.DT_NS_YH_RETXENDDAT)"
            ]
        )

        # Get data from DSINITRT
        DSINITRT_df = data["DSINITRT"][
            [
                "Subject",
                "From which Phase is the Subject entering Retreatment? (IG_NS_NA_DSINITRT1.CL_NS_NH_PHASER_cl_NS_PHASE2)",
                "End of Primary Follow-Up Date (IG_NS_NA_DSINITRT1.DT_NS_YH_PFUENDDAT)",
            ]
        ].copy()
        # Convert End of Primary Follow-Up Date (IG_NS_NA_DSINITRT1.DT_NS_YH_PFUENDDAT) to datetime object
        DSINITRT_df[
            "End of Primary Follow-Up Date (IG_NS_NA_DSINITRT1.DT_NS_YH_PFUENDDAT)"
        ] = pd.to_datetime(
            DSINITRT_df[
                "End of Primary Follow-Up Date (IG_NS_NA_DSINITRT1.DT_NS_YH_PFUENDDAT)"
            ]
        )

        # RESPONSE LISTING NHL ONLY
        # Response data dataframe for NHL only
        responseA_df = data["NHLRS"][
            [
                "Subject",
                "Event Group Label",
                "Event Date",
                "Study Phase (IG_NS_NA_NHLRS1.CL_YS_NH_STUDPSRS_cl_NS_STUDYPS2)",
                "Primary Treatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPT_cl_NS_RSTPT1)",
                "For Unscheduled Primary Treatment Time Point, Specify Day #  (IG_NS_NA_NHLRS1.TX_YS_YH_RSTUDYDAY)",
                "Retreatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPTR_cl_NS_RSTPT2)",
                "For Unscheduled Retreatment Time Point, Specify Day # (IG_NS_NA_NHLRS1.TX_NS_YH_RSTUDYDAYR)",
                "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)",
                "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)",
            ]
        ].copy()
        responseA_df = responseA_df.sort_values(by=["Subject", "Event Date"])
        # replace Not Assessed with Not Reported in all columns
        responseA_df = responseA_df.replace("Not Assessed", "Not Reported")

        # Cohort A - NHL Primary
        # Filter to only Primary Treatment
        responseA_primary_df = responseA_df[
            responseA_df[
                "Study Phase (IG_NS_NA_NHLRS1.CL_YS_NH_STUDPSRS_cl_NS_STUDYPS2)"
            ]
            == "Primary Treatment"
        ]
        # Filter out subjects that  have Unscheduled time points is not a number
        responseA_primary_df = responseA_primary_df[
            (
                responseA_primary_df[
                    "For Unscheduled Primary Treatment Time Point, Specify Day #  (IG_NS_NA_NHLRS1.TX_YS_YH_RSTUDYDAY)"
                ].apply(lambda x: str(x).isdigit())
            )
            | (
                responseA_primary_df[
                    "Primary Treatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPT_cl_NS_RSTPT1)"
                ]
                != "Unscheduled"
            )
        ]
        # Replace value of "Unscheduled" in column Primary Treatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPT_cl_NS_RSTPT1)
        # with value of "Unscheduled Primary Treatment Time Point, Specify Day #  (ig_RS1.RSTPTDY)" if the value of
        # "Unscheduled Primary Treatment Time Point, Specify Day #  (ig_RS1.RSTPTDY)" is a number
        temp_mask = responseA_primary_df[
            "For Unscheduled Primary Treatment Time Point, Specify Day #  (IG_NS_NA_NHLRS1.TX_YS_YH_RSTUDYDAY)"
        ].apply(lambda x: str(x).isdigit())
        # Build numeric day values separately so pandas string columns stay strings.
        unscheduled_primary_days = pd.to_numeric(
            responseA_primary_df[
                "For Unscheduled Primary Treatment Time Point, Specify Day #  (IG_NS_NA_NHLRS1.TX_YS_YH_RSTUDYDAY)"
            ],
            errors="coerce",
        )

        # Now safely convert to int, but only for rows that pass the mask.
        temp_mask = temp_mask & unscheduled_primary_days.notna()
        responseA_primary_df = convert_integers_to_strings(
            responseA_primary_df,
            "For Unscheduled Primary Treatment Time Point, Specify Day #  (IG_NS_NA_NHLRS1.TX_YS_YH_RSTUDYDAY)",
        )
        responseA_primary_df.loc[
            temp_mask,
            "Primary Treatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPT_cl_NS_RSTPT1)",
        ] = "Day " + unscheduled_primary_days.loc[temp_mask].astype(int).astype(str)
        responseA_primary_df[
            "Primary Treatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPT_cl_NS_RSTPT1)"
        ] = responseA_primary_df[
            "Primary Treatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPT_cl_NS_RSTPT1)"
        ].fillna(
            responseA_primary_df[
                "For Unscheduled Primary Treatment Time Point, Specify Day #  (IG_NS_NA_NHLRS1.TX_YS_YH_RSTUDYDAY)"
            ]
        )
        # Remove rows with Pre-Treatment Safety Visit
        responseA_primary_df = responseA_primary_df[
            responseA_primary_df[
                "Primary Treatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPT_cl_NS_RSTPT1)"
            ]
            != "Pre-Treatment Safety Visit"
        ]
        # Convert Event Date to datetime object
        responseA_primary_df["Event Date"] = pd.to_datetime(
            responseA_primary_df["Event Date"]
        )
        # Snapshot the responseA_primary_df
        responseA_primary_df_snapshot = responseA_primary_df.copy()
        # check the number of subject for cohort B - CLL Retreatment
        self.subject_A_prim_count = len(responseA_primary_df["Subject"].unique())

        # Check if there is any subject. If yes, then proceed, else skip
        if self.subject_A_prim_count > 0:
            # Fill NaN with "Not Reported" in column PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)
            responseA_primary_df[
                "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)"
            ] = responseA_primary_df[
                "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)"
            ].fillna(
                "Not Reported",
            )
            # Fill NaN with "Not Reported" in column CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)
            responseA_primary_df[
                "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)"
            ] = responseA_primary_df[
                "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)"
            ].fillna(
                "Not Reported",
            )
            # Convert PET-Based NHL Disease Response and CT-Based NHL Disease Response to numeric values
            responseA_primary_df["PET-Score"] = (
                responseA_primary_df[
                    "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)"
                ]
                .map(DR_NHL_PET_dict)
                .fillna(DR_NHL_PET_dict["Not Reported"])
            )
            responseA_primary_df["CT-Score"] = (
                responseA_primary_df[
                    "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)"
                ]
                .map(DR_NHL_CT_dict)
                .fillna(DR_NHL_CT_dict["Not Reported"])
            )

            # * CURRENT RESPONSE
            # Filter responseA_primary_df to only subject with PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1) not equal to "Not Reported"
            responseA_primary_PET_df = responseA_primary_df[
                responseA_primary_df[
                    "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)"
                ]
                != "Not Reported"
            ]
            # Get the indices of the rows with the maximum 'Event Date' for each 'Subject'
            PET_idx = responseA_primary_PET_df.groupby("Subject")["Event Date"].idxmax()
            # Select these rows for the current response
            responseA_primary_current_PET_df = responseA_primary_PET_df.loc[
                PET_idx
            ].copy()
            # Rename the column 'Primary Treatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPT_cl_NS_RSTPT1)' to 'PET Current Time Point'
            responseA_primary_current_PET_df = responseA_primary_current_PET_df.rename(
                columns={
                    "Primary Treatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPT_cl_NS_RSTPT1)": "PET Current Time Point"
                },
            )
            # only keep the columns 'Subject', 'PET Current Time Point', 'PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)'
            responseA_primary_current_PET_df = responseA_primary_current_PET_df[
                [
                    "Subject",
                    "PET Current Time Point",
                    "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)",
                ]
            ]
            unique_subjects = pd.DataFrame(
                responseA_primary_df["Subject"].unique(), columns=["Subject"]
            )
            final_responseA_primary_df = pd.merge(
                unique_subjects,
                responseA_primary_current_PET_df,
                on="Subject",
                how="left",
            )

            # Filter responseA_primary_df to only subject with CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1) not equal to "Not Reported"
            responseA_primary_CT_df = responseA_primary_df[
                responseA_primary_df[
                    "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)"
                ]
                != "Not Reported"
            ]
            # Get the indices of the rows with the maximum 'Event Date' for each 'Subject'
            CT_idx = responseA_primary_CT_df.groupby("Subject")["Event Date"].idxmax()
            # Select these rows for the current response
            responseA_primary_current_CT_df = responseA_primary_CT_df.loc[CT_idx].copy()
            # Rename the column 'Primary Treatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPT_cl_NS_RSTPT1)' to 'CT Current Time Point'
            responseA_primary_current_CT_df = responseA_primary_current_CT_df.rename(
                columns={
                    "Primary Treatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPT_cl_NS_RSTPT1)": "CT Current Time Point"
                },
            )
            # only keep the columns 'Subject', 'CT Current Time Point', 'CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)'
            responseA_primary_current_CT_df = responseA_primary_current_CT_df[
                [
                    "Subject",
                    "CT Current Time Point",
                    "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)",
                ]
            ]

            final_responseA_primary_df = pd.merge(
                final_responseA_primary_df,
                responseA_primary_current_CT_df,
                on="Subject",
                how="left",
            )

            # * BEST RESPONSE
            ## Best PET-Based NHL Disease Response primary
            # Get the indices of the rows with the minimum 'PET-Best' for each 'Subject'
            responseA_best_PET_idx = responseA_primary_df.groupby("Subject")[
                "PET-Score"
            ].idxmin()
            # Select these rows for the best PET-based response
            responseA_best_PET_df = responseA_primary_df.loc[
                responseA_best_PET_idx
            ].copy()
            # Select the columns subject and PET-Based NHL Disease Response from responseA_best_PET_df
            responseA_best_PET_df = responseA_best_PET_df[
                [
                    "Subject",
                    "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)",
                    "Primary Treatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPT_cl_NS_RSTPT1)",
                ]
            ]
            # Rename the column PET-Based NHL Disease Response to PET-Based Response
            responseA_best_PET_df = responseA_best_PET_df.rename(
                columns={
                    "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)": "PET-Based Response",
                    "Primary Treatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPT_cl_NS_RSTPT1)": "Best PET Time Point",
                },
            )
            # Merge left with the primary current response dataframe
            final_responseA_primary_df = pd.merge(
                final_responseA_primary_df,
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
            responseA_best_CT_df = responseA_primary_df.loc[
                responseA_best_CT_idx
            ].copy()
            # Select the columns subject and CT-Based NHL Disease Response from responseA_best_CT_df
            responseA_best_CT_df = responseA_best_CT_df[
                [
                    "Subject",
                    "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)",
                    "Primary Treatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPT_cl_NS_RSTPT1)",
                ]
            ]
            # Rename the column CT-Based NHL Disease Response to CT-Based Response
            responseA_best_CT_df = responseA_best_CT_df.rename(
                columns={
                    "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)": "CT-Based Response",
                    "Primary Treatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPT_cl_NS_RSTPT1)": "Best CT Time Point",
                },
            )
            # Merge left with the primary response dataframe
            final_responseA_primary_df = pd.merge(
                final_responseA_primary_df,
                responseA_best_CT_df,
                on="Subject",
                how="left",
            )

            ## Overall NHL Disease Response at Day 28 primary
            # Filter responseA_primary_df to only Day 28
            responseA_primary_D28_df = responseA_df[
                responseA_df[
                    "Primary Treatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPT_cl_NS_RSTPT1)"
                ]
                == "Day 28"
            ]
            # Selec the columns subject and PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1) from responseA_primary_D28_df
            responseA_primary_D28_df = responseA_primary_D28_df[
                [
                    "Subject",
                    "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)",
                    "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)",
                    "Event Date",
                ]
            ]
            # Compare responseA_primary_D28_df with responseA_df, and add the subjects (do it once) that are not in responseA_primary_D28_df to responseA_primary_D28_df
            responseA_primary_D28_df = pd.concat(
                [
                    responseA_primary_D28_df,
                    responseA_df[
                        ~responseA_df["Subject"].isin(
                            responseA_primary_D28_df["Subject"]
                        )
                    ][["Subject"]],
                ]
            )
            # Remove duplicates
            responseA_primary_D28_df = responseA_primary_D28_df.drop_duplicates(
                subset=["Subject"]
            )
            # Copy snapshot of responseA_primary_df to a temporary dataframe
            temp_df = responseA_primary_df_snapshot
            # Sort the temporary dataframe by Subject and Event Date
            temp_df = temp_df.sort_values(by=["Subject", "Event Date"])
            # remove all the rows that have nan in PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1) and CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)
            temp_df = temp_df[
                temp_df[
                    "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)"
                ].notna()
                | temp_df[
                    "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)"
                ].notna()
            ]
            # Create a for loop that will check the PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1) and CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1) of each subject in responseA_primary_D28_df
            for index, row in responseA_primary_D28_df.iterrows():
                # check if the PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1) of the subject is nan, and check if the CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1) of the subject is nan
                if pd.isna(
                    row[
                        "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)"
                    ]
                ) and pd.isna(
                    row[
                        "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)"
                    ]
                ):
                    # if yes, check to see if the subject in in PD_df
                    if row["Subject"] in PD_df["Subject"].values:
                        # get the End of Primary Follow-Up Date (IG_NS_NA_DSINITLF1.DT_NS_YH_INITLFPFUENDDAT) date of the subject in PD_df
                        end_date = PD_df[PD_df["Subject"] == row["Subject"]][
                            "End of Primary Follow-Up Date (IG_NS_NA_DSINITLF1.DT_NS_YH_INITLFPFUENDDAT)"
                        ].values[0]
                        # find the response of the same subject with the latest event date that is before the Day 28 event date
                        filtered_df = temp_df[
                            (temp_df["Subject"] == row["Subject"])
                            & (temp_df["Event Date"] <= end_date)
                        ]
                        # Check if the filtered DataFrame is empty
                        if not filtered_df.empty:
                            # Access the last row if the DataFrame is not empty
                            temp_row = filtered_df.iloc[-1]
                            # Replace the PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1) of the subject with the PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1) of the temp_row
                            responseA_primary_D28_df.loc[
                                index,
                                "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)",
                            ] = temp_row[
                                "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)"
                            ]
                            # Replace the CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1) of the subject with the CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1) of the temp_row
                            responseA_primary_D28_df.loc[
                                index,
                                "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)",
                            ] = temp_row[
                                "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)"
                            ]
                    # check if the subject is in Initiation of REtx before Day 28
                    elif row["Subject"] in DSINITRT_df["Subject"].values:
                        # get the End of Primary Follow-Up Date (IG_NS_NA_DSINITLF1.DT_NS_YH_INITLFPFUENDDAT) date of the subject in DSINITRT_df
                        end_date = DSINITRT_df[
                            DSINITRT_df["Subject"] == row["Subject"]
                        ][
                            "End of Primary Follow-Up Date (IG_NS_NA_DSINITRT1.DT_NS_YH_PFUENDDAT)"
                        ].values[0]
                        # find the response of the same subject with the latest event date that is before the Day 28 event date
                        filtered_df = temp_df[
                            (temp_df["Subject"] == row["Subject"])
                            & (temp_df["Event Date"] <= end_date)
                        ]
                        # Check if the filtered DataFrame is empty
                        if not filtered_df.empty:
                            # Access the last row if the DataFrame is not empty
                            temp_row = filtered_df.iloc[-1]
                            # Replace the PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1) of the subject with the PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1) of the temp_row
                            responseA_primary_D28_df.loc[
                                index,
                                "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)",
                            ] = temp_row[
                                "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)"
                            ]
                            # Replace the CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1) of the subject with the CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1) of the temp_row
                            responseA_primary_D28_df.loc[
                                index,
                                "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)",
                            ] = temp_row[
                                "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)"
                            ]
            # Rename the column PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1) to PET-Based ORR
            responseA_primary_D28_df = responseA_primary_D28_df.rename(
                columns={
                    "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)": "PET-Based ORR",
                    "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)": "CT-Based ORR",
                },
            )
            # Merge left with the current response dataframe
            final_responseA_primary_df = pd.merge(
                final_responseA_primary_df,
                responseA_primary_D28_df,
                on="Subject",
                how="left",
            )
            # Fill NaN with "Not Reported" in column PET-Based ORR
            final_responseA_primary_df["PET-Based ORR"] = final_responseA_primary_df[
                "PET-Based ORR"
            ].fillna(
                "Not Reported",
            )
            # Fill NaN with "Not Reported" in column CT-Based ORR
            final_responseA_primary_df["CT-Based ORR"] = final_responseA_primary_df[
                "CT-Based ORR"
            ].fillna(
                "Not Reported",
            )

            ## Checking AE and SAE for NHL primary
            # Getting AE and SAE dataframes
            responseA_primary_AE_df = data["AE"][
                [
                    "Subject",
                    "Form ILB Status",
                    "AE or SAE? (IG_NS_NA_AE2.CL_YS_YH_AESEV_cl_NS_AESAE1)",
                    "Event Onset (IG_NS_NA_AE1.CL_NS_YH_AEONSET_cl_NS_AEONSET1)",
                ]
            ]
            # Check responseA_primary_AE_df if the subject of responseA_primary_df is in the AE dataframe. If yes, then add 'Y' to the column 'AE' in responseA_primary_df, else add 'N'
            final_responseA_primary_df["AE"] = final_responseA_primary_df[
                "Subject"
            ].apply(
                lambda x: "Y" if x in responseA_primary_AE_df["Subject"].values else "N"
            )
            # Check responseA_primary_AE_df if the subject of responseA_primary_df has SAE in column 'AE or SAE? (IG_NS_NA_AE2.CL_YS_YH_AESEV_cl_NS_AESAE1)' . If yes, then add 'Y' to the column 'SAE' in responseA_primary_df, else add 'N'
            final_responseA_primary_df["SAE"] = final_responseA_primary_df[
                "Subject"
            ].apply(
                lambda x: (
                    "Y"
                    if x
                    in responseA_primary_AE_df[
                        responseA_primary_AE_df[
                            "AE or SAE? (IG_NS_NA_AE2.CL_YS_YH_AESEV_cl_NS_AESAE1)"
                        ]
                        == "SAE"
                    ]["Subject"].values
                    else "N"
                )
            )

            ## Checking Study Status for NHL primary
            # Getting Study Status dataframe from SV, column Subject, Event Label and Event Date
            responseA_primary_SV_df = data["DSSV"][
                ["Subject", "Event Label", "Event Date"]
            ]
            # Getting Study Status dataframe from DSSVLTFU, column Subject, Event Label and Event Date
            responseA_primary_DSSVLTFU_df = data["DSSVLTFU"][
                ["Subject", "Event Label", "Event Date"]
            ]
            # Drop all-NA columns from both DataFrames
            responseA_primary_SV_df = responseA_primary_SV_df.dropna(axis=1, how="all")
            responseA_primary_DSSVLTFU_df = responseA_primary_DSSVLTFU_df.dropna(
                axis=1, how="all"
            )
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
            # Merge left with the current response dataframe
            final_responseA_primary_df = pd.merge(
                final_responseA_primary_df,
                responseA_primary_SV_df[["Subject", "Event Label"]],
                on="Subject",
                how="left",
            )
            # Rename the column Event Label to Event Label (Study Status)
            final_responseA_primary_df["Event Label"] = final_responseA_primary_df[
                "Event Label"
            ].map(event_A_dict)

            # Select the columns needed only
            final_responseA_primary_df = final_responseA_primary_df[
                [
                    "Subject",
                    "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)",
                    "PET Current Time Point",
                    "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)",
                    "CT Current Time Point",
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
            self.responseA_primary_df = final_responseA_primary_df.replace(
                [np.nan, np.inf, -np.inf], ""
            )
            # * Formatting the dataframe

            # Cohort A - NHL Retreatment
            # Filter to only Primary Treatment
            responseA_retreatment_df = responseA_df[
                responseA_df[
                    "Study Phase (IG_NS_NA_NHLRS1.CL_YS_NH_STUDPSRS_cl_NS_STUDYPS2)"
                ]
                == "Retreatment"
            ]
            # Replace value of "Unscheduled" in column Retreatment Time Point (ig_RS1.RSTPT) with value of "Unscheduled Retreatment  Treatment Time Point, Specify Day #  (ig_RS1.RSTPTDY)"
            temp_mask = (
                responseA_retreatment_df[
                    "Retreatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPTR_cl_NS_RSTPT2)"
                ]
                == "Unscheduled"
            )
            # Convert the column For Unscheduled Retreatment Time Point, Specify Day # (IG_NS_NA_NHLRS1.TX_NS_YH_RSTUDYDAYR) to string
            responseA_retreatment_df = convert_integers_to_strings(
                responseA_retreatment_df,
                "For Unscheduled Retreatment Time Point, Specify Day # (IG_NS_NA_NHLRS1.TX_NS_YH_RSTUDYDAYR)",
            )
            responseA_retreatment_df.loc[
                temp_mask,
                "Retreatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPTR_cl_NS_RSTPT2)",
            ] = "Day " + responseA_retreatment_df.loc[
                temp_mask,
                "For Unscheduled Retreatment Time Point, Specify Day # (IG_NS_NA_NHLRS1.TX_NS_YH_RSTUDYDAYR)",
            ].fillna(0).astype(int).astype(str)
            # Remove rows with Pre-Treatment Safety Visit
            responseA_retreatment_df = responseA_retreatment_df[
                responseA_retreatment_df[
                    "Retreatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPTR_cl_NS_RSTPT2)"
                ]
                != "Pre-Retreatment Safety Visit"
            ]
            # Convert Event Date to datetime object
            responseA_retreatment_df["Event Date"] = pd.to_datetime(
                responseA_retreatment_df["Event Date"]
            )
            # Snapshot the responseA_retreatment_df
            responseA_retreatment_df_snapshot = responseA_retreatment_df.copy()
            # check the number of subject for cohort B - CLL Retreatment
            self.subject_A_retx_count = len(
                responseA_retreatment_df["Subject"].unique()
            )

            # Check if there is any subject. If yes, then proceed, else skip
            if self.subject_A_retx_count > 0:
                responseA_retreatment_df[
                    [
                        "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)",
                        "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)",
                    ]
                ] = responseA_retreatment_df[
                    [
                        "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)",
                        "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)",
                    ]
                ].fillna("Not Reported")
                # Convert PET-Based NHL Disease Response and CT-Based NHL Disease Response to numeric values
                responseA_retreatment_df["PET-Score"] = (
                    responseA_retreatment_df[
                        "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)"
                    ]
                    .map(DR_NHL_PET_dict)
                    .fillna(DR_NHL_PET_dict["Not Reported"])
                )
                responseA_retreatment_df["CT-Score"] = (
                    responseA_retreatment_df[
                        "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)"
                    ]
                    .map(DR_NHL_CT_dict)
                    .fillna(DR_NHL_CT_dict["Not Reported"])
                )

                # * CURRENT RESPONSE
                # Filter responseA_retreatment_df to only subject with PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1) not equal to "Not Reported"
                responseA_retreatment_PET_df = responseA_retreatment_df[
                    responseA_retreatment_df[
                        "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)"
                    ]
                    != "Not Reported"
                ]
                # Get the indices of the rows with the maximum 'Event Date' for each 'Subject'
                PET_idx = responseA_retreatment_PET_df.groupby("Subject")[
                    "Event Date"
                ].idxmax()
                # Select these rows for the current response
                responseA_retreatment_current_PET_df = responseA_retreatment_PET_df.loc[
                    PET_idx
                ].copy()
                # Rename the column 'Retreatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPTR_cl_NS_RSTPT2)' to 'PET Current Time Point'
                responseA_retreatment_current_PET_df = responseA_retreatment_current_PET_df.rename(
                    columns={
                        "Retreatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPTR_cl_NS_RSTPT2)": "PET Current Time Point"
                    },
                )
                # only keep the columns 'Subject', 'PET Current Time Point', 'PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)'
                responseA_retreatment_current_PET_df = responseA_retreatment_current_PET_df[
                    [
                        "Subject",
                        "PET Current Time Point",
                        "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)",
                    ]
                ]

                # Filter responseA_retreatment_df to only subject with CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1) not equal to "Not Reported"
                responseA_retreatment_CT_df = responseA_retreatment_df[
                    responseA_retreatment_df[
                        "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)"
                    ]
                    != "Not Reported"
                ]
                # Get the indices of the rows with the maximum 'Event Date' for each 'Subject'
                CT_idx = responseA_retreatment_CT_df.groupby("Subject")[
                    "Event Date"
                ].idxmax()
                # Select these rows for the current response
                responseA_retreatment_current_CT_df = responseA_retreatment_CT_df.loc[
                    CT_idx
                ].copy()
                # Rename the column 'Retreatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPTR_cl_NS_RSTPT2)' to 'CT Current Time Point'
                responseA_retreatment_current_CT_df = responseA_retreatment_current_CT_df.rename(
                    columns={
                        "Retreatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPTR_cl_NS_RSTPT2)": "CT Current Time Point"
                    },
                )
                # only keep the columns 'Subject', 'CT Current Time Point', 'CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)'
                responseA_retreatment_current_CT_df = responseA_retreatment_current_CT_df[
                    [
                        "Subject",
                        "CT Current Time Point",
                        "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)",
                    ]
                ]

                final_responseA_retreatment_df = pd.merge(
                    responseA_retreatment_current_PET_df,
                    responseA_retreatment_current_CT_df,
                    on="Subject",
                    how="left",
                )

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
                        "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)",
                        "Retreatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPTR_cl_NS_RSTPT2)",
                    ]
                ]
                # Rename the column PET-Based NHL Disease Response to PET-Based Response
                responseA_best_PET_df = responseA_best_PET_df.rename(
                    columns={
                        "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)": "PET-Based Response",
                        "Retreatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPTR_cl_NS_RSTPT2)": "Best PET Time Point",
                    },
                )
                # Fill NaN with "Not Reported" in column PET-Based Response
                responseA_best_PET_df["PET-Based Response"] = responseA_best_PET_df[
                    "PET-Based Response"
                ].fillna(
                    "Not Reported",
                )
                # Merge left with the primary current response dataframe
                final_responseA_retreatment_df = pd.merge(
                    final_responseA_retreatment_df,
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
                responseA_best_CT_df = responseA_retreatment_df.loc[
                    responseA_best_CT_idx
                ].copy()
                # Select the columns subject and CT-Based NHL Disease Response from responseA_best_CT_df
                responseA_best_CT_df = responseA_best_CT_df[
                    [
                        "Subject",
                        "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)",
                        "Retreatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPTR_cl_NS_RSTPT2)",
                    ]
                ]
                # Rename the column CT-Based NHL Disease Response to CT-Based Response
                responseA_best_CT_df = responseA_best_CT_df.rename(
                    columns={
                        "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)": "CT-Based Response",
                        "Retreatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPTR_cl_NS_RSTPT2)": "Best CT Time Point",
                    },
                )
                # Fill NaN with "Not Reported" in column CT-Based Response
                responseA_best_CT_df["CT-Based Response"] = responseA_best_CT_df[
                    "CT-Based Response"
                ].fillna(
                    "Not Reported",
                )
                # Merge left with the primary response dataframe
                final_responseA_retreatment_df = pd.merge(
                    final_responseA_retreatment_df,
                    responseA_best_CT_df,
                    on="Subject",
                    how="left",
                )

                ## * Overall NHL Disease Response at Day 28-R
                # Filter responseA_retreatment_df to only Day 28-R
                responseA_retreatment_D28_df = responseA_df[
                    responseA_df[
                        "Retreatment Time Point (IG_NS_NA_NHLRS1.CL_NS_NH_RSTPTR_cl_NS_RSTPT2)"
                    ]
                    == "Day 28-R"
                ]
                # Selec the columns subject and PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1) from responseA_retreatment_D28_df
                responseA_retreatment_D28_df = responseA_retreatment_D28_df[
                    [
                        "Subject",
                        "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)",
                        "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)",
                        "Event Date",
                    ]
                ]
                # Compare responseA_retreatment_D28_df with responseA_df, and add the subjects (do it once) that are not in responseA_retreatment_D28_df to responseA_retreatment_D28_df
                responseA_retreatment_D28_df = pd.concat(
                    [
                        responseA_retreatment_D28_df,
                        responseA_df[
                            ~responseA_df["Subject"].isin(
                                responseA_retreatment_D28_df["Subject"]
                            )
                        ][["Subject"]],
                    ]
                )
                # Remove duplicates
                responseA_retreatment_D28_df = (
                    responseA_retreatment_D28_df.drop_duplicates(subset=["Subject"])
                )

                # Copy snapshot of responseA_retreatment_df to a temporary dataframe
                temp_df = responseA_retreatment_df_snapshot
                # Sort the temporary dataframe by Subject and Event Date
                temp_df = temp_df.sort_values(by=["Subject", "Event Date"])
                # remove all the rows that have nan in PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1) and CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)
                temp_df = temp_df[
                    temp_df[
                        "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)"
                    ].notna()
                    | temp_df[
                        "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)"
                    ].notna()
                ]
                # Create a for loop that will check the PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1) and CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1) of each subject in responseA_retreatment_D28_df
                for index, row in responseA_retreatment_D28_df.iterrows():
                    # check if the PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1) of the subject is nan, and check if the CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1) of the subject is nan
                    if pd.isna(
                        row[
                            "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)"
                        ]
                    ) and pd.isna(
                        row[
                            "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)"
                        ]
                    ):
                        # if yes, check to see if the subject in in PD_Retx_df
                        if row["Subject"] in PD_Retx_df["Subject"].values:
                            # get the End of Retreatment Date (ig_INITLF1.DSENRETXDAT) date of the subject in PD_Retx_df
                            end_date = PD_Retx_df[
                                PD_Retx_df["Subject"] == row["Subject"]
                            ][
                                "End of Retreatment Date (ig_INITLF1.DSENRETXDAT)"
                            ].values[0]
                            # if yes, find the response of the same subject with the latest event date that is before the Day 28 event date
                            filtered_df = temp_df[
                                (temp_df["Subject"] == row["Subject"])
                                & (temp_df["Event Date"] <= end_date)
                            ]
                            # Check if the filtered DataFrame is empty
                            if not filtered_df.empty:
                                # Access the last row if the DataFrame is not empty
                                temp_row = filtered_df.iloc[-1]
                                # Replace the PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1) of the subject with the PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1) of the temp_row
                                responseA_retreatment_D28_df.loc[
                                    index,
                                    "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)",
                                ] = temp_row[
                                    "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)"
                                ]
                                # Replace the CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1) of the subject with the CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1) of the temp_row
                                responseA_retreatment_D28_df.loc[
                                    index,
                                    "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)",
                                ] = temp_row[
                                    "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)"
                                ]
                # Rename the column PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1) to PET-Based ORR
                responseA_retreatment_D28_df = responseA_retreatment_D28_df.rename(
                    columns={
                        "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)": "PET-Based ORR",
                        "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)": "CT-Based ORR",
                    },
                )
                # Merge left with the current response dataframe
                final_responseA_retreatment_df = pd.merge(
                    final_responseA_retreatment_df,
                    responseA_retreatment_D28_df,
                    on="Subject",
                    how="left",
                )
                final_responseA_retreatment_df[["PET-Based ORR", "CT-Based ORR"]] = (
                    final_responseA_retreatment_df[
                        ["PET-Based ORR", "CT-Based ORR"]
                    ].fillna("Not Reported")
                )
                ## Checking AE and SAE for NHL primary
                # Getting AE and SAE dataframes
                responseA_retreatment_AE_df = data["AE"][
                    [
                        "Subject",
                        "Form ILB Status",
                        "AE or SAE? (IG_NS_NA_AE2.CL_YS_YH_AESEV_cl_NS_AESAE1)",
                        "Event Onset (IG_NS_NA_AE1.CL_NS_YH_AEONSET_cl_NS_AEONSET1)",
                    ]
                ]
                # Check responseA_retreatment_AE_df if the subject of responseA_retreatment_df is in the AE dataframe. If yes, then add 'Y' to the column 'AE' in responseA_retreatment_df, else add 'N'
                final_responseA_retreatment_df["AE"] = final_responseA_retreatment_df[
                    "Subject"
                ].apply(
                    lambda x: (
                        "Y"
                        if x in responseA_retreatment_AE_df["Subject"].values
                        else "N"
                    )
                )
                # Check responseA_retreatment_AE_df if the subject of responseA_retreatment_df has SAE in column 'AE or SAE? (IG_NS_NA_AE2.CL_YS_YH_AESEV_cl_NS_AESAE1)' . If yes, then add 'Y' to the column 'SAE' in responseA_retreatment_df, else add 'N'
                final_responseA_retreatment_df["SAE"] = final_responseA_retreatment_df[
                    "Subject"
                ].apply(
                    lambda x: (
                        "Y"
                        if x
                        in responseA_retreatment_AE_df[
                            responseA_retreatment_AE_df[
                                "AE or SAE? (IG_NS_NA_AE2.CL_YS_YH_AESEV_cl_NS_AESAE1)"
                            ]
                            == "SAE"
                        ]["Subject"].values
                        else "N"
                    )
                )

                ## Checking Study Status for NHL primary
                # Getting Study Status dataframe from SV, column Subject, Event Label and Event Date
                responseA_retreatment_SV_df = data["DSSV"][
                    ["Subject", "Event Label", "Event Date"]
                ]
                # Getting Study Status dataframe from DSSVLTFU, column Subject, Event Label and Event Date
                responseA_retreatment_DSSVLTFU_df = data["DSSVLTFU"][
                    ["Subject", "Event Label", "Event Date"]
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
                # Merge left with the current response dataframe
                final_responseA_retreatment_df = pd.merge(
                    final_responseA_retreatment_df,
                    responseA_retreatment_SV_df[["Subject", "Event Label"]],
                    on="Subject",
                    how="left",
                )

                # * Formatting the dataframe
                # Rename the column Event Label to Event Label (Study Status)
                final_responseA_retreatment_df["Event Label"] = (
                    final_responseA_retreatment_df["Event Label"].map(event_A_dict)
                )

                # Select the columns needed only
                final_responseA_retreatment_df = final_responseA_retreatment_df[
                    [
                        "Subject",
                        "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)",
                        "PET Current Time Point",
                        "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)",
                        "CT Current Time Point",
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
                self.responseA_retreatment_df = final_responseA_retreatment_df.replace(
                    [np.nan, np.inf, -np.inf], ""
                )

    def response_stats(self):
        data = self.data
        # REPONSE STATS
        # SAFETY STATS

        # Gather all stats of Cohort A
        total_infused_df = self.infusion_df.copy()
        # Getting AE and SAE dataframes
        AE_df = data["AE"][
            [
                "Subject",
                "Form ILB Status",
                "AE or SAE? (IG_NS_NA_AE2.CL_YS_YH_AESEV_cl_NS_AESAE1)",
            ]
        ].copy()
        # Check responseA_primary_AE_df if the subject of responseA_primary_df is in the AE dataframe. If yes, then add 'Y' to the column 'AE' in responseA_primary_df, else add 'N'
        total_infused_df["AE"] = total_infused_df["Subject"].apply(
            lambda x: "Y" if x in AE_df["Subject"].values else "N"
        )
        # Check responseA_primary_AE_df if the subject of responseA_primary_df has SAE in column 'AE or SAE? (IG_NS_NA_AE2.CL_YS_YH_AESEV_cl_NS_AESAE1)' . If yes, then add 'Y' to the column 'SAE' in responseA_primary_df, else add 'N'
        total_infused_df["SAE"] = total_infused_df["Subject"].apply(
            lambda x: (
                "Y"
                if x
                in AE_df[
                    AE_df["AE or SAE? (IG_NS_NA_AE2.CL_YS_YH_AESEV_cl_NS_AESAE1)"]
                    == "SAE"
                ]["Subject"].values
                else "N"
            )
        )

        # # Total number of subjects in cohort A, B, and C
        AE_total_count = get_stats_percentage("AE", total_infused_df).T
        SAE_total_count = get_stats_percentage("SAE", total_infused_df).T
        # merge AE and SAE dataframes
        self.safety_total_df = pd.concat([AE_total_count, SAE_total_count], axis=1)

        PET_Response_Codelist = [
            "Complete Metabolic Response (CMR)",
            "Partial Metabolic Response (PMR)",
            "No Metabolic Response (NMR)",
            "Progressive Metabolic Disease (PMD)",
            "Not Reported",
        ]

        CT_Response_Codelist = [
            "Complete Radiologic Response (CR)",
            "Partial Response (PR)",
            "Stable Disease (SD)",
            "Progressive Disease (PD)",
            "Not Reported",
        ]

        # RESPONSE STATS
        if self.subject_A_prim_count > 0:
            responseA_stat = self.responseA_primary_df.copy()
            # replace 'Not Assessed' with 'Not Reported' for all columns in responseA_stat
            responseA_stat = responseA_stat.replace("Not Assessed", "Not Reported")
            self.response_stat_A_BOR_PET = get_stats_percentage2(
                "PET-Based Response", PET_Response_Codelist, responseA_stat
            )
            self.response_stat_A_BOR_CT = get_stats_percentage2(
                "CT-Based Response", CT_Response_Codelist, responseA_stat
            )
            self.response_stat_A_ORR_PET = get_stats_percentage2(
                "PET-Based ORR", PET_Response_Codelist, responseA_stat
            )
            self.response_stat_A_ORR_CT = get_stats_percentage2(
                "CT-Based ORR", CT_Response_Codelist, responseA_stat
            )

        # UPDATE FORMAT for cohort A after getting the stats

        if self.subject_A_prim_count > 0:
            self.responseA_primary_df.loc[
                (
                    self.responseA_primary_df["Event Label"]
                    == "Retreatment Long Term Follow-up"
                )
                | (self.responseA_primary_df["Event Label"] == "Primary Retreatment")
                | (self.responseA_primary_df["Event Label"] == "Pre-Retreatment"),
                "PET-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLPET_cl_NS_RSNHLPET1)",
            ] = "Transitioned to Retreatment"
            self.responseA_primary_df.loc[
                (
                    self.responseA_primary_df["Event Label"]
                    == "Retreatment Long Term Follow-up"
                )
                | (self.responseA_primary_df["Event Label"] == "Primary Retreatment")
                | (self.responseA_primary_df["Event Label"] == "Pre-Retreatment"),
                "CT-Based NHL Disease Response (IG_NS_NA_NHLRS2.CL_NS_NH_NHLCT_cl_NS_RSNHLCT1)",
            ] = "Transitioned to Retreatment"
            self.responseA_primary_df.loc[
                (
                    self.responseA_primary_df["Event Label"]
                    == "Retreatment Long Term Follow-up"
                )
                | (self.responseA_primary_df["Event Label"] == "Primary Retreatment")
                | (self.responseA_primary_df["Event Label"] == "Pre-Retreatment"),
                "PET Current Time Point",
            ] = "Transitioned to Retreatment"
            self.responseA_primary_df.loc[
                (
                    self.responseA_primary_df["Event Label"]
                    == "Retreatment Long Term Follow-up"
                )
                | (self.responseA_primary_df["Event Label"] == "Primary Retreatment")
                | (self.responseA_primary_df["Event Label"] == "Pre-Retreatment"),
                "CT Current Time Point",
            ] = "Transitioned to Retreatment"

    def export(self, output_dir, output_file_name):
        data = self.data
        with pd.ExcelWriter(
            output_dir + "/" + output_file_name + ".xlsx", engine="xlsxwriter"
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
                if self.enrollment_listing_df_output["Subject"].count() > 0:
                    # * WRITING DATA: LegalSex_list, Age_at_Consent_list, Race_list, Ethnicity_list
                    worksheet1 = writer.book.add_worksheet("DSMB-Demo Stats Table")

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
                        "F1:I1", "Cohort A (NHL) Enrollment", bold_12_format
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
                            "Screen Failed\nN="
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
                            "Infused\nN=" + str(self.status_list[i]["Infused"]),
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

                    for i in range(0, len(self.enrollment_listing_df_output.columns)):
                        worksheet2.write(
                            0,
                            i,
                            self.enrollment_listing_df_output.columns[i],
                            bold_11_format,
                        )
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

                    # DSMB-New Infusion Statistics
                    # * WRITING DATA: new_infusion_df
                    worksheet3 = writer.book.add_worksheet(
                        "DSMB-New Infusion Statistics"
                    )

                    # * FORMATING DATA
                    for i in range(0, len(self.infusion_statA)):
                        for j in range(0, len(self.infusion_statA.columns)):
                            worksheet3.write(
                                i + 3,
                                j + 1,
                                self.infusion_statA.iloc[i, j],
                                normal_data_format,
                            )

                    # * WRITING HEADER AND FORMATTING
                    stat_order = ["Mean SD", "Median", "Range"]

                    worksheet3.merge_range(
                        "B1:D1", "Cells Infused", bold_12_wrap_format
                    )
                    worksheet3.merge_range(
                        "E1:F1", "Transduction Efficiency", bold_12_wrap_format
                    )
                    worksheet3.write("B2", "TmCD19-IL18 Cells", bold_12_wrap_format)
                    worksheet3.write("C2", "Total Cells", bold_12_wrap_format)
                    worksheet3.write("D2", "Met Target Dose", bold_12_wrap_format)
                    worksheet3.write("E2", "%scFv Flow", bold_12_wrap_format)
                    worksheet3.write("F2", "Met Target %scFv", bold_12_wrap_format)
                    worksheet3.merge_range(
                        "A3:F3",
                        "Cohort A (N=" + str(self.infusion_count[0]) + ")",
                        bold_12_wrap_format,
                    )

                    # Merge and format data
                    worksheet3.merge_range(
                        "D4:D6", self.infusion_statA.iloc[0, 2], normal_data_format
                    )
                    worksheet3.merge_range(
                        "F4:F6", self.infusion_statA.iloc[0, 4], normal_data_format
                    )

                    for i in range(0, len(stat_order)):
                        worksheet3.write(i + 3, 0, stat_order[i], bold_11_format)

                    # * Autofit
                    worksheet3.autofit()

                    # DSMB-Infusion Listing
                    worksheet4 = writer.book.add_worksheet("DSMB-Infusion Listing")
                    # * WRITING AND FORMATING DATA
                    for i in range(0, len(self.infusion_df)):
                        for j in range(0, len(self.infusion_df.columns)):
                            worksheet4.write(
                                i + 2,
                                j,
                                self.infusion_df.iloc[i, j],
                                normal_data_format,
                            )
                    # if there are subjects in infusionR_df
                    if len(self.infusionR_df) > 0:
                        for i in range(0, len(self.infusionR_df)):
                            for j in range(0, len(self.infusionR_df.columns)):
                                worksheet4.write(
                                    i + 2,
                                    j + 14,
                                    self.infusionR_df.iloc[i, j],
                                    normal_data_format,
                                )
                    # * WRITING HEADER AND FORMATTING
                    worksheet4.merge_range("A1:A2", "Subject ID", bold_12_wrap_format)
                    worksheet4.merge_range(
                        "B1:B2", "Study Day (Primary)", bold_12_wrap_format
                    )
                    worksheet4.merge_range(
                        "C1:C2", "Cohort Assignment", bold_12_wrap_format
                    )
                    worksheet4.merge_range(
                        "D1:D2", "Dose Level Assignment", bold_12_wrap_format
                    )
                    worksheet4.merge_range(
                        "E1:E2",
                        "Lymphodepleting Chemotherapy Regimen",
                        bold_12_wrap_format,
                    )
                    worksheet4.merge_range(
                        "F1:F2", "Date of TmCD19-IL18 Infusion", bold_12_wrap_format
                    )
                    worksheet4.merge_range(
                        "G1:J1", "Cells Infused", bold_12_wrap_format
                    )
                    worksheet4.merge_range(
                        "K1:L1", "Transduction Efficiency", bold_12_wrap_format
                    )
                    worksheet4.write("G2", "Target Cell Dose", bold_12_wrap_format)
                    worksheet4.write(
                        "H2",
                        "Total TmCD19-IL18 CAR T Cell Dose Administered",
                        bold_12_wrap_format,
                    )
                    worksheet4.write(
                        "I2", "Total Cell Dose Administered", bold_12_wrap_format
                    )
                    worksheet4.write("J2", "Met Target Dose", bold_12_wrap_format)
                    worksheet4.write("K2", "%scFv Flow", bold_12_wrap_format)
                    worksheet4.write("L2", "Met Target %scFv", bold_12_wrap_format)
                    if len(self.infusionR_df) > 0:
                        worksheet4.merge_range(
                            "O1:O2", "Subject ID", bold_12_wrap_format
                        )
                        worksheet4.merge_range(
                            "P1:P2", "Study Day (Retreatment)", bold_12_wrap_format
                        )
                        worksheet4.merge_range(
                            "Q1:Q2", "Cohort Assignment", bold_12_wrap_format
                        )
                        worksheet4.merge_range(
                            "R1:R2",
                            "Lymphodepleting Chemotherapy Regimen",
                            bold_12_wrap_format,
                        )
                        worksheet4.merge_range(
                            "S1:S2",
                            "Date of TmCD19-IL18 Retreatment Infusion",
                            bold_12_wrap_format,
                        )
                        worksheet4.merge_range(
                            "T1:U1", "Cells Infused", bold_12_wrap_format
                        )
                        worksheet4.merge_range(
                            "V1:W1", "Transduction Efficiency", bold_12_wrap_format
                        )
                        worksheet4.write(
                            "T2",
                            "Total TmCD19-IL18 CAR T Cell Dose Administered",
                            bold_12_wrap_format,
                        )
                        worksheet4.write(
                            "U2", "Total Cell Dose Administered", bold_12_wrap_format
                        )
                        worksheet4.write("V2", "%scFv Flow", bold_12_wrap_format)
                        worksheet4.write("W2", "Met Target %scFv", bold_12_wrap_format)

                    # Autofit
                    worksheet4.autofit()

                    # DSMB-Response Stats
                    worksheet5 = writer.book.add_worksheet("DSMB-Response Stats")
                    # * WRITING DATA
                    # * FORMATING DATA
                    # Safety Data
                    for i in range(0, len(self.safety_total_df)):
                        for j in range(0, len(self.safety_total_df.columns)):
                            worksheet5.write(
                                i + 3,
                                j + 6,
                                self.safety_total_df.iloc[i, j],
                                normal_data_format,
                            )
                    worksheet5.write("F4", "All Cohorts", bold_11_format)
                    # Response Data Cohort A
                    if self.subject_A_prim_count == 0:
                        for i in range(0, 6):
                            worksheet5.write(i + 3, 1, "0 (0%)", normal_data_format)
                            worksheet5.write(i + 3, 3, "0 (0%)", normal_data_format)
                            worksheet5.write(i + 9, 1, "0 (0%)", normal_data_format)
                            worksheet5.write(i + 9, 3, "0 (0%)", normal_data_format)
                    else:
                        for i in range(0, len(self.response_stat_A_BOR_PET)):
                            for j in range(
                                0, len(self.response_stat_A_BOR_PET.columns)
                            ):
                                worksheet5.write(
                                    i + 3,
                                    j + 1,
                                    self.response_stat_A_BOR_PET.iloc[i, j],
                                    normal_data_format,
                                )
                        for i in range(0, len(self.response_stat_A_BOR_CT)):
                            for j in range(0, len(self.response_stat_A_BOR_CT.columns)):
                                worksheet5.write(
                                    i + 3,
                                    j + 3,
                                    self.response_stat_A_BOR_CT.iloc[i, j],
                                    normal_data_format,
                                )
                        for i in range(0, len(self.response_stat_A_ORR_PET)):
                            for j in range(
                                0, len(self.response_stat_A_ORR_PET.columns)
                            ):
                                worksheet5.write(
                                    i + 9,
                                    j + 1,
                                    self.response_stat_A_ORR_PET.iloc[i, j],
                                    normal_data_format,
                                )
                        for i in range(0, len(self.response_stat_A_ORR_CT)):
                            for j in range(0, len(self.response_stat_A_ORR_CT.columns)):
                                worksheet5.write(
                                    i + 9,
                                    j + 3,
                                    self.response_stat_A_ORR_CT.iloc[i, j],
                                    normal_data_format,
                                )

                    # * WRITING HEADER AND FORMATTING
                    # Safety Headers
                    # number of subject of safety_total_df
                    safety_total_df_subject_count = len(
                        self.infusion_df["Subject"].unique()
                    )
                    worksheet5.merge_range(
                        "G1:J1",
                        "Safety Statistics (N="
                        + str(safety_total_df_subject_count)
                        + ")",
                        bold_12_wrap_format,
                    )
                    worksheet5.merge_range("G2:H2", "Adverse Events", bold_11_format)
                    worksheet5.merge_range(
                        "I2:J2", "Serious Adverse Events ", bold_11_format
                    )
                    worksheet5.write("G3", "Yes", bold_11_format)
                    worksheet5.write("H3", "No", bold_11_format)
                    worksheet5.write("I3", "Yes", bold_11_format)
                    worksheet5.write("J3", "No", bold_11_format)

                    # Response Headers
                    worksheet5.merge_range(
                        "A1:D1",
                        "Cohort A (NHL) Subject Response (N="
                        + str(self.subject_A_prim_count)
                        + ")",
                        bold_12_format,
                    )
                    worksheet5.merge_range(
                        "A2:B2", "PET-Based Response", bold_11_format
                    )
                    worksheet5.merge_range("C2:D2", "CT-Based Response", bold_11_format)
                    worksheet5.merge_range(
                        "A3:D3", "Best Overall Response (BOR)", bold_11_format
                    )
                    worksheet5.merge_range(
                        "A9:D9",
                        "Overall Response Rate (ORR) at Day 28",
                        bold_11_format,
                    )
                    # Listing Response Criteria
                    response_A_PET = [
                        "Complete Metabolic Response (CMR)",
                        "Partial Metabolic Response (PMR)",
                        "No Metabolic Response (NMR)",
                        "Progressive Metabolic Disease (PMD)",
                        "Not Reported",
                    ]
                    response_A_CT = [
                        "Complete Radiologic Response (CR)",
                        "Partial Response (PR)",
                        "Stable Disease (SD)",
                        "Progressive Disease (PD)",
                        "Not Reported",
                    ]
                    for i in range(0, len(response_A_PET)):
                        worksheet5.write(i + 3, 0, response_A_PET[i], bold_11_format)
                        worksheet5.write(i + 9, 0, response_A_PET[i], bold_11_format)
                    for i in range(0, len(response_A_CT)):
                        worksheet5.write(i + 3, 2, response_A_CT[i], bold_11_format)
                        worksheet5.write(i + 9, 2, response_A_CT[i], bold_11_format)
                    worksheet5.autofit()

                    # Response Listing NHL
                    if self.subject_A_prim_count > 0:
                        worksheet6 = writer.book.add_worksheet("Response Listing NHL")
                        # * WRITING DATA
                        # * FORMATING DATA
                        if self.subject_A_prim_count > 0:
                            for i in range(0, len(self.responseA_primary_df)):
                                for j in range(
                                    0, len(self.responseA_primary_df.columns)
                                ):
                                    worksheet6.write(
                                        i + 3,
                                        j,
                                        self.responseA_primary_df.iloc[i, j],
                                        normal_data_format,
                                    )
                            if self.subject_A_retx_count > 0:
                                for i in range(0, len(self.responseA_retreatment_df)):
                                    for j in range(
                                        0, len(self.responseA_retreatment_df.columns)
                                    ):
                                        worksheet6.write(
                                            i + 3,
                                            j + 16,
                                            self.responseA_retreatment_df.iloc[i, j],
                                            normal_data_format,
                                        )
                        # * WRITING HEADER AND FORMATTING
                        if self.subject_A_prim_count > 0:
                            worksheet6.merge_range(
                                "A1:N1",
                                "Cohort A (NHL)- Primary Follow-up",
                                bold_12_format,
                            )
                            worksheet6.merge_range(
                                "A2:A3", "Subject ID", bold_11_format
                            )
                            worksheet6.merge_range(
                                "B2:E2", "Current Response", bold_11_format
                            )
                            worksheet6.merge_range(
                                "F2:I2", "Best Response/Timepoint", bold_11_format
                            )
                            worksheet6.merge_range(
                                "J2:K2", "Overall Response/Day 28", bold_11_format
                            )
                            worksheet6.write("B3", "PET-Based Response", bold_11_format)
                            worksheet6.write("C3", "Study Timepoint", bold_11_format)
                            worksheet6.write("D3", "CT-Based Response", bold_11_format)
                            worksheet6.write("E3", "Study Timepoint", bold_11_format)
                            worksheet6.write("F3", "PET-Based Response", bold_11_format)
                            worksheet6.write("G3", "Study Timepoint", bold_11_format)
                            worksheet6.write("H3", "CT-Based Response", bold_11_format)
                            worksheet6.write("I3", "Study Timepoint", bold_11_format)
                            worksheet6.write("J3", "PET-Based ORR", bold_11_format)
                            worksheet6.write("K3", "CT-Based ORR", bold_11_format)
                            worksheet6.merge_range(
                                "L2:L3", "Adverse Events \n(Y/N)", bold_11_wrap_format
                            )
                            worksheet6.merge_range(
                                "M2:M3",
                                "Serious Adverse Events \n(Y/N)",
                                bold_11_wrap_format,
                            )
                            worksheet6.merge_range(
                                "N2:N3", "Study Status", bold_11_wrap_format
                            )
                            if self.subject_A_retx_count > 0:
                                worksheet6.merge_range(
                                    "Q1:AD1",
                                    "Cohort A (NHL)- Retreatment Follow-up",
                                    bold_12_format,
                                )
                                worksheet6.merge_range(
                                    "Q2:Q3", "Subject ID", bold_11_format
                                )
                                worksheet6.merge_range(
                                    "R2:U2", "Current Response", bold_11_format
                                )
                                worksheet6.merge_range(
                                    "V2:Y2", "Best Response/Timepoint", bold_11_format
                                )
                                worksheet6.merge_range(
                                    "Z2:AA2",
                                    "Overall Response/Day 28-R",
                                    bold_11_format,
                                )
                                worksheet6.write(
                                    "R3", "PET-Based Response", bold_11_format
                                )
                                worksheet6.write(
                                    "S3", "Study Timepoint", bold_11_format
                                )
                                worksheet6.write(
                                    "T3", "CT-Based Response", bold_11_format
                                )
                                worksheet6.write(
                                    "U3", "Study Timepoint", bold_11_format
                                )
                                worksheet6.write(
                                    "V3", "PET-Based Response", bold_11_format
                                )
                                worksheet6.write(
                                    "W3", "Study Timepoint", bold_11_format
                                )
                                worksheet6.write(
                                    "X3", "CT-Based Response", bold_11_format
                                )
                                worksheet6.write(
                                    "Y3", "Study Timepoint", bold_11_format
                                )
                                worksheet6.write("Z3", "PET-Based ORR", bold_11_format)
                                worksheet6.write("AA3", "CT-Based ORR", bold_11_format)
                                worksheet6.merge_range(
                                    "AB2:AB3",
                                    "Adverse Events \n(Y/N)",
                                    bold_11_wrap_format,
                                )
                                worksheet6.merge_range(
                                    "AC2:AC3",
                                    "Serious Adverse Events \n(Y/N)",
                                    bold_11_wrap_format,
                                )
                                worksheet6.merge_range(
                                    "AD2:AD3", "Study Status", bold_11_wrap_format
                                )
                        # Autofit
                        worksheet6.autofit()
