import numpy as np
import pandas as pd

from cci_automation.dsmb.DSMB_util import (
    convert_float_2_sci_notation,
    get_stats_df,
    get_stats_perc_df,
    get_stats_percentage,
    get_stats_percentage2,
)
from cci_automation.util import (
    age_calculation,
    get_data_from_dict,
    remove_leading_zeros_from_dates,
)
from clinical_reporting.export import get_named_excel_formats


class DSMB11823:
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
        self.Enrollment_Listing()
        # process the Demographics Statistics
        self.Demographics_Statistics()
        # process the Status for Eligible Subjects
        self.Status_Eligible_Subjects()
        # process the Study Tx Listing
        self.Infusion_Listing()
        # process the Study Tx Statistics
        self.Infusion_Statistics()
        # process the Response Listing
        self.Response_Listing()
        # process the Response Statistics
        self.Response_Statistics()
        # process the PET Imaging
        self.PET_Imaging()
        # Generate Excel output
        self.output()

    def Enrollment_Listing(self):
        data = self.data
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
            "DSDLA": {
                "Dose Level Assignment (IG_NS_NA_DSDLA1.CL_NS_YH_DLADOSELV_cl_NS_DOSELV1)": "Dose Level Assignment"
            },
            "IE": {
                "Main Consent Date (IG_NS_NA_IE1.DT_NS_NH_MAINCDAT)": "Main Consent Date",
                "Subject Meets All Study Eligibility (IG_NS_NA_IE3.CL_NS_YH_ELIGYN_cl_YS_YN1)": "Screen Fail (Y/N)",
                "Other Screen Fail Reason (IG_NS_NA_IE4.TX_NS_YH_OTHRSFREAS)": "SF3",
                "Screen Failure Reason (IG_NS_NA_IE4.CL_NS_YH_IECAT_cl_NS_IEREASSF1)": "Reason for Screen Failure",
                "Select the Primary Inclusion Criterion Excluding this Subject (IG_NS_NA_IE4.CL_NS_NH_ITESTCD_cl_NS_IEINCL1)": "SF1",
                "Select the Primary Exclusion Criterion Excluding this Subject (IG_NS_NA_IE4.CL_NS_NH_ETESTCD_cl_NS_IEEXCL1)": "SF2",
            },
            "EXINF": {
                "Event Group Label": "Event Group Label",
                "Was infusion administered? (IG_NS_NA_EXINF1.CL_NS_NH_INFADMIN_cl_YS_YN1)": "Infused (Y/N)",
            },
            "DSEOS": {
                "End of Study Date (IG_NS_NA_DSEOS1.DT_NS_YH_EOSDAT)": "End of Study Date",
                "Reason for End of Study? (IG_NS_NA_DSEOS2.CL_NS_YH_EOSCOD1_cl_NS_EOSREAS1)": "End of Study Reason",
                "Provide Supportive Information (IG_NS_NA_DSEOS2.TX_NS_YH_EOSTERM)": "End of Study Supportive Info",
            },
        }

        # using guard rail to check if DM is in the data
        # Check if DM exists and is not empty
        if "DM" not in data or data["DM"].empty:
            return

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

        # invert Screen Fail
        if "Screen Fail (Y/N)" in enrollment_df:
            enrollment_df["Screen Fail (Y/N)"] = (
                enrollment_df["Screen Fail (Y/N)"]
                .map({"Yes": "No", "No": "Yes"})
                .fillna("")
            )

        # ensure string
        enrollment_df["Reason for Screen Failure"] = enrollment_df[
            "Reason for Screen Failure"
        ].astype(str)

        # unified replacements
        repl_cols = {
            "Other": "SF3",
            "Inclusion Criteria": "SF1",
            "Exclusion Criteria": "SF2",
        }
        for label, src in repl_cols.items():
            m = enrollment_df["Reason for Screen Failure"] == label
            if src == "Other":
                # replace exact Other→SF3
                enrollment_df.loc[m, "Reason for Screen Failure"] = enrollment_df.loc[
                    m, src
                ]
            else:
                # append code
                enrollment_df.loc[
                    m & enrollment_df[src].ne(""), "Reason for Screen Failure"
                ] = label + " " + enrollment_df.loc[m, src].astype(str)

        # Check DSEOS data for screen failures
        if "DSEOS" in data and not data["DSEOS"].empty:
            dseos_data = data["DSEOS"]
            # Look for subjects with "Screen failure" as the reason for end of study
            # Use the exact column name as it appears in the raw CSV data
            screen_fail_mask = (
                dseos_data[
                    "Reason for End of Study? (IG_NS_NA_DSEOS2.CL_NS_YH_EOSCOD1_cl_NS_EOSREAS1)"
                ]
                == "Screen failure"
            )
            screen_fail_subjects = dseos_data[screen_fail_mask]

            # Update enrollment_df for these subjects
            for _, row in screen_fail_subjects.iterrows():
                subject = row["Subject"]
                # Also use the exact column name for supportive info
                supportive_info = (
                    row[
                        "Provide Supportive Information (IG_NS_NA_DSEOS2.TX_NS_YH_EOSTERM)"
                    ]
                    if pd.notna(
                        row[
                            "Provide Supportive Information (IG_NS_NA_DSEOS2.TX_NS_YH_EOSTERM)"
                        ]
                    )
                    else ""
                )

                # Find the subject in enrollment_df and update
                subject_mask = enrollment_df["Subject"] == subject
                if any(subject_mask):
                    # Update Screen Fail to Yes
                    enrollment_df.loc[subject_mask, "Screen Fail (Y/N)"] = "Yes"
                    # Update Reason for Screen Failure if supportive info exists
                    if supportive_info:
                        enrollment_df.loc[subject_mask, "Reason for Screen Failure"] = (
                            supportive_info
                        )

        # drop all helper cols at once
        enrollment_df = enrollment_df.drop(
            columns=["SF1", "SF2", "SF3", "Event Group Label"]
        )

        # set Infused status
        inf = enrollment_df["Infused (Y/N)"].fillna("No")
        pending = (~inf.eq("Yes")) & enrollment_df["End of Study Date"].isna()
        ended = (~inf.eq("Yes")) & enrollment_df["End of Study Date"].notna()
        enrollment_df.loc[pending, "Infused (Y/N)"] = "Pending"
        enrollment_df.loc[ended, "Infused (Y/N)"] = "No"
        enrollment_df = enrollment_df.drop(
            columns=[
                "End of Study Date",
                "End of Study Reason",
                "End of Study Supportive Info",
            ]
        )

        # Sort
        enrollment_df = enrollment_df.sort_values(["Subject"])

        # date formatting
        out = enrollment_df.copy()
        for dcol in out.filter(like="Date").columns:
            out[dcol] = out[dcol].dt.strftime("%m/%d/%Y")

        # If Gender is "Other", replace the value with "Other Gender"
        out.loc[out["Gender Identity"] == "Other", "Gender Identity"] = out[
            "Other Gender"
        ]

        # If Race is "Other", replace the value with "Other Race"
        out.loc[out["Race"] == "Other", "Race"] = out["Other Race"]

        # final column reorder & assign
        self.enrollment_output_df = out[
            [
                "Subject",
                "Dose Level Assignment",
                "Legal Sex",
                "Sex Assigned at Birth",
                "Gender Identity",
                "Ethnicity",
                "Race",
                "Age at Consent",
                "Screen Fail (Y/N)",
                "Reason for Screen Failure",
                "Infused (Y/N)",
            ]
        ].reset_index(drop=True)
        self.enrollment_df = enrollment_df.reset_index(drop=True)

    def Demographics_Statistics(self):
        if "DM" not in self.data or self.data["DM"].empty:
            return

        enrollment_df = self.enrollment_df.copy()
        # Update this filter options to each cohort
        filter_options = [enrollment_df["Consent Date"].notna()]
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
            ## Screen Fail
            SF_df = filtered_df[filtered_df["Screen Fail (Y/N)"] == "Yes"].copy()
            SF = SF_df["Subject"].count()
            ## Eligible
            EL_df = filtered_df[filtered_df["Screen Fail (Y/N)"] == "No"].copy()
            EL = EL_df["Subject"].count()
            ## Infused
            INF_df = filtered_df[filtered_df["Infused (Y/N)"] == "Yes"].copy()
            INF = INF_df["Subject"].count()
            # Define a dictionary containing the status of each variable
            self.status_list.append(
                {
                    "Total Consented": TT,
                    "Screen Fail (Y/N)": SF,
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

    def Status_Eligible_Subjects(self):
        # centralize data column names for maintainability
        cols = {
            "ae_flag": "AE or SAE? (IG_NS_NA_AE2.CL_YS_YH_AESEV_cl_NS_AESAE1)",
            "eos_date": "End of Study Date (IG_NS_NA_DSEOS1.DT_NS_YH_EOSDAT)",
            "eos_reason": "Reason for End of Study? (IG_NS_NA_DSEOS2.CL_NS_YH_EOSCOD1_cl_NS_EOSREAS1)",
            "eos_last": "Last Study Visit Completed in Primary Treatment (IG_NS_NA_DSEOS1.CL_NS_YH_EOSLSVPR_cl_NS_EOSTP1)",
            "dssv_occ": "Did the protocol-specified study visit occur? (IG_NS_NA_DSSV1.CL_YS_NH_SVOCCUR_cl_YS_YN1)",
            "dssvltfu_occ": "Did the protocol-specified study visit occur? (IG_NS_NA_DSSVLTFU1.CL_YS_NH_SVOCCUR_cl_YS_YN1)",
        }

        if "DM" not in self.data or self.data["DM"].empty:
            return
        data = self.data

        # status_df subjects are the filtered enrollment_df with only subjects that are not screen failed
        status_df = self.enrollment_df[
            self.enrollment_df["Screen Fail (Y/N)"] == "No"
        ].copy()
        # get dataframe from status_df with only the subject and Dose Level Assignment columns
        status_df = status_df[["Subject", "Dose Level Assignment"]].copy()

        # Check for AEs and SAEs
        if "AE" in data:
            ae_data = data["AE"]
            subjects_with_ae = set(ae_data["Subject"].unique())
            subjects_with_sae = set(
                ae_data[ae_data[cols["ae_flag"]] == "SAE"]["Subject"].unique()
            )
            # Add columns for AEs and SAEs
            status_df["Adverse Events (Y/N)"] = status_df["Subject"].apply(
                lambda x: "Y" if x in subjects_with_ae else "N"
            )
            status_df["Serious Adverse Events (Y/N)"] = status_df["Subject"].apply(
                lambda x: "Y" if x in subjects_with_sae else "N"
            )
        else:
            # If no AE data, set both columns to "N"
            status_df["Adverse Events (Y/N)"] = "N"
            status_df["Serious Adverse Events (Y/N)"] = "N"

        # Determine off‐study subjects via DSEOS
        off_study_subjects = set()
        off_study_reason = {}
        last_study_visit = {}
        if "DSEOS" in data:
            dseos_data = data["DSEOS"]
            eos_info = dseos_data[dseos_data[cols["eos_date"]].notna()]
            off_study_subjects = set(eos_info["Subject"])
            for _, row in eos_info.iterrows():
                subject = row["Subject"]
                reason = row.get(cols["eos_reason"], "")
                if pd.notna(reason) and reason != "":
                    off_study_reason[subject] = reason
                else:
                    off_study_reason[subject] = "Not Reported"
                last_visit = row.get(cols["eos_last"], "")
                if pd.notna(last_visit) and last_visit != "":
                    last_study_visit[subject] = last_visit
                else:
                    last_study_visit[subject] = "Not Reported"

        # Initialize study status column with default "On Study"
        status_df["Study Status"] = "On Study"
        status_df["Off-Study Reason"] = "N/A"
        status_df["Last Study Visit Performed for Off-Study Subject"] = "N/A"

        # Create a dictionary to store the latest visit info for each subject
        latest_visits = {}

        # Combine visits from DSSV and DSSVLTFU
        all_visits = []
        if "DSSV" in data:
            dssv = data["DSSV"].copy()
            valid = dssv[dssv[cols["dssv_occ"]] == "Yes"]
            valid["Event Date"] = pd.to_datetime(valid["Event Date"], errors="coerce")
            all_visits.append(valid[["Subject", "Event Date", "Event Label"]])
        if "DSSVLTFU" in data:
            dssvltfu = data["DSSVLTFU"].copy()
            valid2 = dssvltfu[dssvltfu[cols["dssvltfu_occ"]] == "Yes"]
            valid2["Event Date"] = pd.to_datetime(valid2["Event Date"], errors="coerce")
            all_visits.append(valid2[["Subject", "Event Date", "Event Label"]])

        # Combine all visits
        if all_visits:
            combined_visits = pd.concat(all_visits, ignore_index=True)
            # For each subject, find the latest visit
            for subject, subject_data in combined_visits.groupby("Subject"):
                if not subject_data.empty:
                    # Get the row with the latest event date
                    latest_idx = subject_data["Event Date"].idxmax()
                    event_label = subject_data.loc[latest_idx, "Event Label"]
                    latest_visits[subject] = event_label

        # Now set the Study Status column and off-study information
        for idx, row in status_df.iterrows():
            subject = row["Subject"]
            if subject in off_study_subjects:
                status_df.loc[idx, "Study Status"] = "Off Study"
                status_df.loc[idx, "Off-Study Reason"] = off_study_reason.get(
                    subject, "Not Reported"
                )
                status_df.loc[
                    idx, "Last Study Visit Performed for Off-Study Subject"
                ] = last_study_visit.get(subject, "Not Reported")
            elif subject in latest_visits:
                status_df.loc[idx, "Study Status"] = (
                    f"On Study/{latest_visits[subject]}"
                )

        # sort by Subject ID
        status_df = status_df.sort_values("Subject").reset_index(drop=True)
        self.status_df = status_df.copy()

    def Infusion_Listing(self):
        if "EXINF" not in self.data or self.data["EXINF"].empty:
            return
        data = self.data

        # Filter EXINF data to include only "Primary Treatment" in Study Phase
        exinf_data = data["EXINF"]
        study_phase_col = (
            "Study Phase (IG_NS_NA_EXINF1.CL_YS_NH_STUDYPS_cl_YS_STUDYPS1)"
        )
        if study_phase_col in exinf_data.columns:
            exinf_data = exinf_data[exinf_data[study_phase_col] == "Primary Treatment"]
            data["EXINF"] = exinf_data

        # Update this dictionary to the new study
        TCD_dict = {
            "Dose Level -1 (DL-1)": 10000000,
            "Dose Level 1 (DL1)": 50000000,
            "Dose Level 2 (DL2)": 100000000,
            "Dose Level 3 (DL3)": 300000000,
            "Not Assigned": "Not Assigned",
        }

        # Get lymphodepleting chemotherapy dates from EXCHMO
        chemo_info = None
        if "EXCHMO" in data and not data["EXCHMO"].empty:
            exchmo_df = data["EXCHMO"].copy()

            # Filter EXCHMO data to include only "Primary Treatment" in Study Phase
            exchmo_phase_col = (
                "Study Phase (IG_NS_NA_EXCHMO1.CL_NS_NH_CHMOSTPS_cl_YS_STUDYPS1)"
            )
            if exchmo_phase_col in exchmo_df.columns:
                exchmo_df = exchmo_df[
                    exchmo_df[exchmo_phase_col] == "Primary Treatment"
                ]

            # Check if the required columns exist
            start_date_col = "Start Date (IG_NS_NA_EXCHMO2.DT_NS_NH_EXSTDAT)"
            end_date_col = "End Date (IG_NS_NA_EXCHMO2.DT_NS_NH_EXENDAT)"
            if (
                start_date_col in exchmo_df.columns
                and end_date_col in exchmo_df.columns
            ):
                # Convert date columns to datetime, coercing errors
                exchmo_df[start_date_col] = pd.to_datetime(
                    exchmo_df[start_date_col], errors="coerce"
                )
                exchmo_df[end_date_col] = pd.to_datetime(
                    exchmo_df[end_date_col], errors="coerce"
                )
                # Group by Subject to get start and end dates for chemotherapy
                chemo_dates = (
                    exchmo_df.groupby("Subject")
                    .agg({start_date_col: "min", end_date_col: "max"})
                    .reset_index()
                )
                # Format dates as MM/DD/YYYY only if they're not null
                chemo_dates = remove_leading_zeros_from_dates(chemo_dates)
                chemo_dates["Lymphodepleting Chemotherapy Dates"] = chemo_dates.apply(
                    lambda row: (
                        f"{row[start_date_col]} to {row[end_date_col]}"
                        if pd.notna(row[start_date_col]) and pd.notna(row[end_date_col])
                        else ""
                    ),
                    axis=1,
                )
                # Keep only Subject and combined dates
                chemo_info = chemo_dates[
                    ["Subject", "Lymphodepleting Chemotherapy Dates"]
                ]
        # Prepare the data for the Study Treatment Listing
        input_dict = {
            "EXINF": {
                "Event Group Label": "Event Group Label",
                "Infusion Date (IG_NS_NA_EXINF1.DT_NS_NH_INFDAT)": "Date of TmPSMA-02 CAR T Cell Infusion",
                "CAR T Cell Dose Administered (IG_NS_NA_EXINF1.NM_NS_NH_TDOS)": "Total TmPSMA-02 CAR T Cell Dose Administered",
                "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TDOSXP_cl_YS_EX10POW1)": "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TDOSXP_cl_YS_EX10POW1)",
                "Total Cell Dose Administered (IG_NS_NA_EXINF1.NM_NS_NH_TOTDOS)": "Total Cell Dose Administered",
                "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TOTDOSXP_cl_YS_EX10POW1)": "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TOTDOSXP_cl_YS_EX10POW1)",
                "Transduction Efficiency (%) (IG_NS_NA_EXINF1.NM_NS_NH_TRANSEFFP)": "%scFv Flow",
            },
            "DSDLA": {
                "Dose Level Assignment (IG_NS_NA_DSDLA1.CL_NS_YH_DLADOSELV_cl_NS_DOSELV1)": "Dose Level Assignment"
            },
        }
        raw_infusion_df = get_data_from_dict(data, input_dict, "EXINF")
        # format infusion date vectorized
        raw = raw_infusion_df.copy()
        raw["Date of TmPSMA-02 CAR T Cell Infusion"] = pd.to_datetime(
            raw["Date of TmPSMA-02 CAR T Cell Infusion"], errors="coerce"
        ).dt.strftime("%m/%d/%Y")
        raw = remove_leading_zeros_from_dates(raw)
        infusion_df = raw[raw["Event Group Label"] == "Day 0"].copy()
        # Add lymphodepleting chemotherapy dates to infusion_df if available
        if chemo_info is not None and not chemo_info.empty:
            infusion_df = pd.merge(infusion_df, chemo_info, on="Subject", how="left")
        else:
            # Add empty column if no chemotherapy data
            infusion_df["Lymphodepleting Chemotherapy Dates"] = ""
        # adding Target TmPSMA-02 CAR T Cell Dose using TCD_dict
        infusion_df["Target TmPSMA-02 CAR T Cell Dose"] = infusion_df[
            "Dose Level Assignment"
        ].map(TCD_dict)
        # in‐place dose multipliers
        infusion_df["Total TmPSMA-02 CAR T Cell Dose Administered"] *= (
            10
            ** infusion_df.pop(
                "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TDOSXP_cl_YS_EX10POW1)"
            )
        )
        infusion_df["Total Cell Dose Administered"] *= 10 ** infusion_df.pop(
            "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TOTDOSXP_cl_YS_EX10POW1)"
        )
        # met target binary count
        targ = infusion_df["Target TmPSMA-02 CAR T Cell Dose"]
        infusion_df["Met Target Dose"] = (
            (
                targ.eq(targ.astype(int))
                & infusion_df["Total TmPSMA-02 CAR T Cell Dose Administered"].ge(targ)
            )
            .map({True: "Y", False: "N"})
            .fillna("")
        )
        infusion_df["Met Target %scFv"] = (
            infusion_df["%scFv Flow"].ge(2).map({True: "Y", False: "N"}).fillna("")
        )
        # fill NaN with empty string and use infer_objects to avoid downcast warning
        infusion_df = infusion_df.fillna("").infer_objects()
        # Only keep the rows that have Event Group Label
        infusion_df = infusion_df[infusion_df["Event Group Label"] != ""]
        # Re-order the columns and remove the columns that are not needed
        infusion_df = infusion_df[
            [
                "Subject",
                "Dose Level Assignment",
                "Lymphodepleting Chemotherapy Dates",
                "Date of TmPSMA-02 CAR T Cell Infusion",
                "Target TmPSMA-02 CAR T Cell Dose",
                "Total TmPSMA-02 CAR T Cell Dose Administered",
                "Total Cell Dose Administered",
                "Met Target Dose",
                "%scFv Flow",
                "Met Target %scFv",
            ]
        ]
        # sort by Subject ID
        infusion_df = infusion_df.sort_values("Subject").reset_index(drop=True)
        # Store the sorted dataframe
        self.infusion_df = infusion_df.copy()

    def Infusion_Statistics(self):
        if "EXINF" not in self.data or self.data["EXINF"].empty:
            return
        # Use the infusion_df data - no cohort separation needed
        infusion_df = self.infusion_df.copy()
        # Don't process if dataframe is empty
        if infusion_df.empty:
            return
        # Create statistics for Total TmPSMA-02 CAR T Cell Dose Administered
        infusion_stat1 = get_stats_df(
            "Total TmPSMA-02 CAR T Cell Dose Administered", infusion_df
        )
        # Create statistics for Total Cell Dose Administered
        infusion_stat2 = get_stats_df("Total Cell Dose Administered", infusion_df)
        # Count the number of subjects that met the target dose
        total = infusion_df["Subject"].nunique()
        ycount = infusion_df["Met Target Dose"].eq("Y").sum()
        infusion_stat2["Met Target Dose"] = (
            f"{ycount} ({ycount / total * 100:.2f}%)" if total else "0 (0%)"
        )
        # Create statistics for %scFv Flow
        infusion_stat3 = get_stats_perc_df("%scFv Flow", infusion_df)
        # Count the number of subjects that met the target %scFv
        y2 = infusion_df["Met Target %scFv"].eq("Y").sum()
        infusion_stat3["Met Target %scFv"] = (
            f"{y2} ({y2 / total * 100:.2f}%)" if total else "0 (0%)"
        )
        # Combine the three statistics dataframes
        self.infusion_stat_df = pd.concat(
            [infusion_stat1, infusion_stat2, infusion_stat3], axis=1
        )
        # Rename the columns to the desired headers
        self.infusion_stat_df.columns = [
            "TmPSMA-02 CAR T Cells",
            "Total Cells",
            "Met Target Dose",
            "%scFv Flow",
            "Met Target %scFv",
        ]
        # Replace infinity values with empty strings and fill NaN values
        self.infusion_stat_df = self.infusion_stat_df.replace([np.inf, -np.inf], "")
        self.infusion_stat_df = self.infusion_stat_df.fillna("")
        # Now format the display dataframe with scientific notation AFTER statistics have been calculated
        display_df = self.infusion_df.copy()
        display_df["Target TmPSMA-02 CAR T Cell Dose"] = display_df[
            "Target TmPSMA-02 CAR T Cell Dose"
        ].apply(
            lambda x: (
                convert_float_2_sci_notation(x)
                if not isinstance(x, str) and pd.notna(x)
                else x
            )
        )
        display_df["Total TmPSMA-02 CAR T Cell Dose Administered"] = display_df[
            "Total TmPSMA-02 CAR T Cell Dose Administered"
        ].apply(lambda x: convert_float_2_sci_notation(x) if pd.notna(x) else x)
        display_df["Total Cell Dose Administered"] = display_df[
            "Total Cell Dose Administered"
        ].apply(lambda x: convert_float_2_sci_notation(x) if pd.notna(x) else x)
        # Add percentage sign to %scFv Flow values if they're not empty
        display_df["%scFv Flow"] = display_df["%scFv Flow"].apply(
            lambda x: f"{x}%" if pd.notna(x) and x != "" else x
        )
        # Save the formatted display version for output
        self.infusion_display_df = display_df

    def Response_Listing(self):
        """
        Process response data to create a response listing table
        with 3 rows per subject (RECIST 1.1, PCWG3, PSA Response)
        """
        if "RS" not in self.data or self.data["RS"].empty:
            return
        rs_data = self.data["RS"].copy()
        if rs_data.empty:
            return

        # Filter RS data to include only "Primary Treatment" in Study Phase
        study_phase_col = (
            "Study Phase (IG_YS_NA_STUDYPHASE.CL_NS_NH_STUDPS_cl_YS_STUDYPS1)"
        )
        if study_phase_col in rs_data.columns:
            rs_data = rs_data[rs_data[study_phase_col] == "Primary Treatment"]

        # centralize column names for maintainability
        cols = {
            "subject": "Subject",
            "primary_tp": "Primary Treatment Time Point (IG_YS_NA_STUDYPHASE.CL_YS_NH_PRMFLTP_cl_NS_PRMTXTP1)",
            "unsched_day": "For Unscheduled Primary Treatment Time Points, Specify Day # (IG_YS_NA_STUDYPHASE.TX_YS_YH_UNSDAYPMFUP)",
            "recist": "Overall Tumor Response (IG_NS_NA_RS2.CL_NS_NH_OTRS_cl_NS_OTRS1)",
            "pcwg": "Bone Scan Response (IG_NS_NA_RS3.CL_NS_NH_BSRS_cl_NS_BSRS1)",
            "psa": "PSA Response (IG_NS_NA_RS3.CL_NS_YH_PSARS_cl_NS_PSARS1)",
        }

        subjects = sorted(rs_data[cols["subject"]].unique())
        standard_time_points = [
            "Day 28",
            "Month 2",
            "Month 3",
            "Month 4",
            "Month 5",
            "Month 6",
            "Month 9",
            "Month 12",
        ]
        rows = []
        for subject in subjects:
            subject_data = rs_data[rs_data[cols["subject"]] == subject]
            # Create dictionaries for each response type
            recist_data = {"Subject": subject, "Response Type": "RECIST 1.1"}
            pcwg_data = {"Subject": subject, "Response Type": "PCWG3"}
            psa_data = {"Subject": subject, "Response Type": "PSA Response"}
            # Initialize additional_timepoints lists
            recist_data["additional_timepoints"] = []
            pcwg_data["additional_timepoints"] = []
            psa_data["additional_timepoints"] = []
            # Initialize columns for standard timepoints
            for tp in standard_time_points:
                recist_data[tp] = ""
                pcwg_data[tp] = ""
                psa_data[tp] = ""
            # Process each record for the subject
            for _, row in subject_data.iterrows():
                primary_tp = row.get(cols["primary_tp"], "")
                recist_response = row.get(cols["recist"], "")
                pcwg_response = row.get(cols["pcwg"], "")
                psa_response = row.get(cols["psa"], "")
                # Format the time point - check if standard or additional
                if primary_tp in standard_time_points:
                    # Standard timepoint
                    if recist_response and pd.notna(recist_response):
                        recist_data[primary_tp] = recist_response
                    if pcwg_response and pd.notna(pcwg_response):
                        pcwg_data[primary_tp] = pcwg_response
                    if psa_response and pd.notna(psa_response):
                        psa_data[primary_tp] = psa_response
                else:
                    # Non-standard timepoint - handle as additional
                    import re

                    # For unscheduled timepoints, use the day number
                    if primary_tp == "Unscheduled":
                        unscheduled_day = row.get(cols["unsched_day"], "")
                        if unscheduled_day and pd.notna(unscheduled_day):
                            # Skip timepoints with day number less than 28
                            try:
                                day_num = int(unscheduled_day)
                                if day_num < 28:
                                    continue  # Skip this timepoint
                                timepoint_label = f"Day {unscheduled_day}"
                            except ValueError, TypeError:
                                timepoint_label = "Unscheduled"
                        else:
                            timepoint_label = "Unscheduled"
                    else:
                        # For all other non-standard timepoints
                        # Check if we can extract a day number from the timepoint name
                        day_match = re.search(r"Day\s+(\d+)", primary_tp)
                        if day_match:
                            day_num = int(day_match.group(1))
                            # Skip timepoints with day number less than 28
                            if day_num < 28:
                                continue  # Skip this timepoint
                            timepoint_label = primary_tp
                        else:
                            # Keep original format for all other timepoints
                            timepoint_label = primary_tp
                    # Calculate a sort value for sorting within each subject's additional timepoints
                    sort_value = 9999  # Default high value
                    day_match = re.search(r"Day\s+(\d+)", timepoint_label)
                    if day_match:
                        sort_value = int(day_match.group(1))
                    else:
                        month_match = re.search(r"Month\s+(\d+)", timepoint_label)
                        if month_match:
                            # Convert months to approximate days for sorting
                            sort_value = int(month_match.group(1)) * 28
                    # Store timepoint info with sort value and response text
                    if recist_response and pd.notna(recist_response):
                        recist_data["additional_timepoints"].append(
                            {
                                "timepoint": timepoint_label,
                                "response": recist_response,
                                "sort_value": sort_value,
                            }
                        )
                    if pcwg_response and pd.notna(pcwg_response):
                        pcwg_data["additional_timepoints"].append(
                            {
                                "timepoint": timepoint_label,
                                "response": pcwg_response,
                                "sort_value": sort_value,
                            }
                        )
                    if psa_response and pd.notna(psa_response):
                        psa_data["additional_timepoints"].append(
                            {
                                "timepoint": timepoint_label,
                                "response": psa_response,
                                "sort_value": sort_value,
                            }
                        )
            # Sort and format additional timepoints for each subject
            for data_dict in [recist_data, pcwg_data, psa_data]:
                if (
                    "additional_timepoints" in data_dict
                    and data_dict["additional_timepoints"]
                ):
                    # Sort by the sort_value
                    data_dict["additional_timepoints"].sort(
                        key=lambda x: x["sort_value"]
                    )
                    # Format as a newline-separated list of "Timepoint (Response)"
                    formatted_timepoints = "\n".join(
                        [
                            f"{tp['timepoint']} ({tp['response']})"
                            for tp in data_dict["additional_timepoints"]
                        ]
                    )
                    data_dict["Additional/ Unscheduled Timepoints"] = (
                        formatted_timepoints
                    )
                    # Remove the temporary list
                    del data_dict["additional_timepoints"]
                else:
                    # If no additional timepoints, set as "Not Applicable"
                    data_dict["Additional/ Unscheduled Timepoints"] = "Not Applicable"
            # Add the three rows for this subject
            rows.append(recist_data)
            rows.append(pcwg_data)
            rows.append(psa_data)
        # Create the DataFrame from the rows
        if rows:
            response_df = pd.DataFrame(rows)
            # Generate final column order - standard timepoints plus the single additional timepoints column
            final_columns = (
                ["Subject", "Response Type"]
                + standard_time_points
                + ["Additional/ Unscheduled Timepoints"]
            )
            # Reindex dataframe with all columns, fill missing with empty string
            response_df = response_df.reindex(columns=final_columns).fillna("")
            # Store the complete list of time points including the additional column
            self.time_points = standard_time_points + [
                "Additional/ Unscheduled Timepoints"
            ]
        # Store the DataFrame as a class attribute
        self.response_df = response_df

    def Response_Statistics(self):
        """
        Calculate the best overall response for each subject regardless of timepoint
        and create statistics for each response type.
        """
        if not hasattr(self, "response_df") or self.response_df.empty:
            return
        # Define response rankings (best to worst)
        recist_ranking = {
            "Complete Response (CR)": 1,
            "Partial Response (PR)": 2,
            "Stable Disease (SD)": 3,
            "Progressive Disease (PD)": 4,
            "Not Evaluable per RECIST 1.1": 5,  # Added new status for subjects without measurable disease
            "Not Reported": 6,  # Changed rank from 5 to 6
        }
        bone_scan_ranking = {
            "No New Lesions/No Bone Progression": 1,
            "New Lesions- Preliminary Assessment/Progressive Disease Suspected": 2,
            "New Lesions- Progressive Osseous Disease Confirmed": 3,
            "Not Reported": 4,  # Lowest rank
        }
        psa_ranking = {
            "Confirmed PSA Response": 1,
            "Preliminary PSA Response": 2,
            "Stable": 3,
            "Preliminary PSA Progression": 4,
            "Confirmed PSA Progression": 5,
            "Not Reported": 6,  # Lowest rank
        }
        # Get all unique subjects
        subjects = self.response_df["Subject"].unique()
        # Initialize the response counts dictionaries
        recist_counts = {status: 0 for status in recist_ranking.keys()}
        bone_scan_counts = {status: 0 for status in bone_scan_ranking.keys()}
        psa_counts = {status: 0 for status in psa_ranking.keys()}
        # Get RS data to check for subjects without measurable disease
        rs_data = self.data.get("RS", pd.DataFrame())
        not_measurable_subjects = set()
        # Identify subjects who don't have measurable disease per RECIST 1.1 at baseline
        if (
            not rs_data.empty
            and "Subject had measurable disease per RECIST 1.1 at baseline? (IG_NS_NA_RS2.CL_NS_NH_MDRCTBL_cl_YS_YN1)"
            in rs_data.columns
        ):
            measurable_column = "Subject had measurable disease per RECIST 1.1 at baseline? (IG_NS_NA_RS2.CL_NS_NH_MDRCTBL_cl_YS_YN1)"
            # Group by Subject and check if any records show 'No' for measurable disease
            for subject, subject_data in rs_data.groupby("Subject"):
                # If any record shows 'No' for measurable disease, add to not_measurable_subjects
                if "No" in subject_data[measurable_column].values:
                    not_measurable_subjects.add(subject)

        # Improved function to extract response from formatted string
        def extract_response(response_text):
            if not response_text or not isinstance(response_text, str):
                return "Not Reported"
            # If response is standard format with no timepoint prefix, return as is
            if (
                response_text in recist_ranking
                or response_text in bone_scan_ranking
                or response_text in psa_ranking
            ):
                return response_text
            # Check if this is a formatted string like "Day X (Response)"
            if "(" in response_text and ")" in response_text:
                try:
                    # Find the first opening parenthesis which indicates start of the response
                    first_paren_idx = response_text.find("(")
                    if first_paren_idx > 0:
                        # Count all remaining parentheses to handle nested cases
                        open_count = 1
                        for i in range(first_paren_idx + 1, len(response_text)):
                            if response_text[i] == "(":
                                open_count += 1
                            elif response_text[i] == ")":
                                open_count -= 1
                                # When we find the matching closing parenthesis
                                if open_count == 0:
                                    # Return everything between the first "(" and the matching ")"
                                    return response_text[
                                        first_paren_idx + 1 : i
                                    ].strip()
                    # Fallback for simple formats with no nested parentheses
                    return response_text[
                        first_paren_idx + 1 : response_text.rfind(")")
                    ].strip()
                except ValueError, IndexError:
                    # If parsing fails, return original
                    return response_text.strip()
            # Return as is if it doesn't match our expected formats
            return response_text.strip()

        # Process each subject's best response
        for subject in subjects:
            subject_data = self.response_df[self.response_df["Subject"] == subject]
            # Initialize with appropriate default based on measurability
            if subject in not_measurable_subjects:
                best_recist = "Not Evaluable per RECIST 1.1"
                best_recist_rank = recist_ranking["Not Evaluable per RECIST 1.1"]
            else:
                best_recist = "Not Reported"
                best_recist_rank = recist_ranking["Not Reported"]
            best_bone_scan = "Not Reported"
            best_psa = "Not Reported"
            best_bone_scan_rank = bone_scan_ranking["Not Reported"]
            best_psa_rank = psa_ranking["Not Reported"]
            # Only look for RECIST responses if subject has measurable disease
            if subject not in not_measurable_subjects:
                # Find best RECIST response
                recist_row = subject_data[subject_data["Response Type"] == "RECIST 1.1"]
                if not recist_row.empty:
                    # Check all time point columns (excluding Subject and Response Type)
                    for col in recist_row.columns[2:]:
                        response_value = recist_row.iloc[0][col]
                        if (
                            response_value
                            and isinstance(response_value, str)
                            and response_value.strip() != ""
                        ):
                            extracted_response = extract_response(response_value)
                            # Check if this response has a better rank
                            if (
                                extracted_response in recist_ranking
                                and recist_ranking[extracted_response]
                                < best_recist_rank
                            ):
                                best_recist = extracted_response
                                best_recist_rank = recist_ranking[extracted_response]
            # Find best Bone Scan response
            bone_scan_row = subject_data[subject_data["Response Type"] == "PCWG3"]
            if not bone_scan_row.empty:
                for col in bone_scan_row.columns[2:]:
                    response_value = bone_scan_row.iloc[0][col]
                    if (
                        response_value
                        and isinstance(response_value, str)
                        and response_value.strip() != ""
                    ):
                        extracted_response = extract_response(response_value)
                        if (
                            extracted_response in bone_scan_ranking
                            and bone_scan_ranking[extracted_response]
                            < best_bone_scan_rank
                        ):
                            best_bone_scan = extracted_response
                            best_bone_scan_rank = bone_scan_ranking[extracted_response]
            # Find best PSA response
            psa_row = subject_data[subject_data["Response Type"] == "PSA Response"]
            if not psa_row.empty:
                for col in psa_row.columns[2:]:
                    response_value = psa_row.iloc[0][col]
                    if (
                        response_value
                        and isinstance(response_value, str)
                        and response_value.strip() != ""
                    ):
                        extracted_response = extract_response(response_value)
                        if (
                            extracted_response in psa_ranking
                            and psa_ranking[extracted_response] < best_psa_rank
                        ):
                            best_psa = extracted_response
                            best_psa_rank = psa_ranking[extracted_response]
            # Update counts
            recist_counts[best_recist] += 1
            bone_scan_counts[best_bone_scan] += 1
            psa_counts[best_psa] += 1
        # Calculate percentages
        total_subjects = len(subjects)
        # Create DataFrames for statistics
        recist_stats = pd.DataFrame(
            {
                "Count": [recist_counts[status] for status in recist_ranking.keys()],
                "Percentage": [
                    f"{recist_counts[status] / total_subjects * 100:.1f}%"
                    if total_subjects > 0
                    else "0.0%"
                    for status in recist_ranking.keys()
                ],
            },
            index=recist_ranking.keys(),
        )
        bone_scan_stats = pd.DataFrame(
            {
                "Count": [
                    bone_scan_counts[status] for status in bone_scan_ranking.keys()
                ],
                "Percentage": [
                    f"{bone_scan_counts[status] / total_subjects * 100:.1f}%"
                    if total_subjects > 0
                    else "0.0%"
                    for status in bone_scan_ranking.keys()
                ],
            },
            index=bone_scan_ranking.keys(),
        )
        psa_stats = pd.DataFrame(
            {
                "Count": [psa_counts[status] for status in psa_ranking.keys()],
                "Percentage": [
                    f"{psa_counts[status] / total_subjects * 100:.1f}%"
                    if total_subjects > 0
                    else "0.0%"
                    for status in psa_ranking.keys()
                ],
            },
            index=psa_ranking.keys(),
        )
        # Add totals
        recist_stats.loc["Total"] = [total_subjects, "100.0%"]
        bone_scan_stats.loc["Total"] = [total_subjects, "100.0%"]
        psa_stats.loc["Total"] = [total_subjects, "100.0%"]
        # Store statistics DataFrames as class attributes
        self.recist_stats = recist_stats
        self.bone_scan_stats = bone_scan_stats
        self.psa_stats = psa_stats
        self.total_response_subjects = total_subjects

    def PET_Imaging(self):
        """
        Process PSMA imaging data to create a PET Imaging tab with data organized by subject and timepoint
        """
        if "PSMAIMG" not in self.data or self.data["PSMAIMG"].empty:
            return

        # Get the PSMAIMG data
        psma_data = self.data["PSMAIMG"].copy()

        if psma_data.empty:
            return

        # Extract the subjects
        subjects = sorted(psma_data["Subject"].unique())

        # Define the Measurements we want to track (exactly 5)
        measurement_types = [
            "Total Tumor Uptake",
            "Average Tumor Uptake",
            "Qualitative Tumor Uptake",
            "Total Uptake Percent Change",
            "New PSMA+ Lesions",
        ]

        # Initialize dataframe to store the organized data
        pet_df_rows = []

        # Process each subject
        for subject in subjects:
            subject_data = psma_data[psma_data["Subject"] == subject]

            # For each Measurement, create exactly one row
            for measurement_type in measurement_types:
                row = {"Subject": subject, "Measurement": measurement_type}

                # Initialize all timepoint columns as empty
                row["Baseline (Pre-Tx Safety)"] = "N/A"  # Default for baseline is N/A
                row["Post-Treatment (Day 28)"] = ""
                row["Disease Progression"] = ""

                # Process each record for this subject
                for _, record in subject_data.iterrows():
                    timepoint = record.get(
                        "Primary Treatment Time Point (IG_YS_NA_STUDYPHASE.CL_YS_NH_PRMFLTP_cl_NS_PRMTXTP1)",
                        "",
                    )
                    event_date = record.get("Event Date", "")

                    if pd.isna(timepoint) or pd.isna(event_date):
                        continue

                    # Get the appropriate value based on Measurement
                    value = ""
                    if measurement_type == "Total Tumor Uptake":
                        value = record.get(
                            "Total Tumor Uptake (IG_NS_NA_PSMAIMG4.NM_NS_NH_TTU)", ""
                        )
                    elif measurement_type == "Average Tumor Uptake":
                        value = record.get(
                            "Average Tumor Uptake (IG_NS_NA_PSMAIMG4.NM_NS_NH_ATU)", ""
                        )
                    elif measurement_type == "Qualitative Tumor Uptake":
                        value = record.get(
                            "Qualitative Tumor Uptake (IG_NS_NA_PSMAIMG4.CL_NS_NH_QTU_cl_NS_PNMNR1)",
                            "",
                        )
                    elif measurement_type == "Total Uptake Percent Change":
                        value = record.get(
                            "Total Tumor Uptake Percent Change (%) (IG_NS_NA_PSMAIMG4.NM_NS_YH_TTUCP1)",
                            "",
                        )
                        if pd.notna(value):
                            value = f"{value}%"
                    elif measurement_type == "New PSMA+ Lesions":
                        new_lesions = record.get(
                            "Were new PSMA positive lesions identified? (IG_NS_NA_PSMAIMG5.CL_NS_YH_PSMANLESYN_cl_NS_LESYNNA1)",
                            "",
                        )
                        if new_lesions == "Yes":
                            num_lesions = record.get(
                                "Total Number of New PSMA Positive Lesions (IG_NS_NA_PSMAIMG5.CL_NS_NH_NPSMAPL_cl_NS_NPSMAPL1)",
                                "",
                            )
                            value = (
                                f"Yes, {num_lesions}"
                                if pd.notna(num_lesions)
                                else "Yes"
                            )
                        elif new_lesions == "Not Applicable- Baseline Imaging":
                            value = "N/A"
                        else:
                            value = new_lesions if pd.notna(new_lesions) else ""

                    # Assign to the correct column based on timepoint
                    if (
                        "Pre-Treatment Safety/Baseline" in timepoint
                        or "Baseline" in timepoint
                    ):
                        row["Baseline (Pre-Tx Safety)"] = (
                            value if pd.notna(value) else "N/A"
                        )
                    elif "Day 28" in timepoint:
                        row["Post-Treatment (Day 28)"] = (
                            value if pd.notna(value) else ""
                        )
                    else:
                        # For other timepoints, combine with any existing disease progression data
                        if pd.notna(value) and value != "":
                            existing = row["Disease Progression"]
                            if existing and existing != "":
                                row["Disease Progression"] = (
                                    f"{existing}\n{timepoint} ({value})"
                                )
                            else:
                                row["Disease Progression"] = f"{timepoint} ({value})"

                pet_df_rows.append(row)

        # Create the DataFrame
        if pet_df_rows:
            self.pet_imaging_df = pd.DataFrame(pet_df_rows)
        else:
            self.pet_imaging_df = pd.DataFrame(
                columns=[
                    "Subject",
                    "Measurement",
                    "Baseline (Pre-Tx Safety)",
                    "Post-Treatment (Day 28)",
                    "Disease Progression",
                ]
            )

    def output(self):
        with pd.ExcelWriter(
            self.output_dir + "/" + self.output_file_name + ".xlsx", engine="xlsxwriter"
        ) as writer:
            # Get formatting options from util.py
            formats = get_named_excel_formats(writer.book)

            # ==================== Demographics Statistics Tab (FIRST) ====================
            if (
                hasattr(self, "LegalSex_list")
                and hasattr(self, "Age_at_Consent_list")
                and hasattr(self, "Race_list")
                and hasattr(self, "Ethnicity_list")
            ):
                # Create Demographics Statistics worksheet as the first sheet
                worksheet = writer.book.add_worksheet("DSMB-Demographics Statistics")
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
                # Status row headers and data
                worksheet.merge_range(
                    "B1:E1", "Overall Study Enrollment", formats["bold_12_format"]
                )
                worksheet.write(1, 0, "Status", formats["bold_11_format"])
                for i in range(0, len(Sex_order)):
                    worksheet.write(
                        i + 3, 0, Sex_order[i], formats["bold_11_wrap_format"]
                    )
                for i in range(0, len(Age_order)):
                    worksheet.write(
                        i + 8, 0, Age_order[i], formats["bold_11_wrap_format"]
                    )
                for i in range(0, len(Race_order)):
                    worksheet.write(
                        i + 12, 0, Race_order[i], formats["bold_11_wrap_format"]
                    )
                for i in range(0, len(Ethnicity_order)):
                    worksheet.write(
                        i + 22, 0, Ethnicity_order[i], formats["bold_11_wrap_format"]
                    )
                # Write status headers with counts
                status_headers = [
                    "Total Consented\nN=" + str(self.status_list[0]["Total Consented"]),
                    "Screen Fail\nN=" + str(self.status_list[0]["Screen Fail (Y/N)"]),
                    "Eligible\nN=" + str(self.status_list[0]["Eligible"]),
                    "Infused\nN=" + str(self.status_list[0]["Infused"]),
                ]
                for i, header in enumerate(status_headers):
                    worksheet.write(1, i + 1, header, formats["bold_11_wrap_format"])
                # Legal Sex section
                worksheet.merge_range("A3:E3", "Legal Sex", formats["bold_11_format"])
                sex_order = ["Male", "Female", "X (Nonbinary)", "Not Reported"]
                # Write Legal Sex row labels
                for i, sex in enumerate(sex_order):
                    worksheet.write(i + 3, 0, sex, formats["bold_11_format"])
                # Write Legal Sex data
                for j in range(len(self.LegalSex_list[0])):
                    for k in range(len(self.LegalSex_list[0].columns)):
                        worksheet.write(
                            j + 3,
                            k + 1,
                            self.LegalSex_list[0].iloc[j, k],
                            formats["normal_data_format"],
                        )
                # Age at Consent section
                worksheet.merge_range(
                    "A8:E8", "Age at Consent", formats["bold_11_format"]
                )
                age_order = ["Mean SD", "Median", "Range"]
                # Write Age at Consent row labels
                for i, age in enumerate(age_order):
                    worksheet.write(i + 8, 0, age, formats["bold_11_format"])
                # Write Age at Consent data
                for j in range(len(self.Age_at_Consent_list[0])):
                    for k in range(len(self.Age_at_Consent_list[0].columns)):
                        worksheet.write(
                            j + 8,
                            k + 1,
                            self.Age_at_Consent_list[0].iloc[j, k],
                            formats["normal_data_format"],
                        )
                # Race section
                worksheet.merge_range("A12:E12", "Race", formats["bold_11_format"])
                # Write Race row data starting at row 12
                # Write Race data
                for j in range(len(self.Race_list[0])):
                    for k in range(len(self.Race_list[0].columns)):
                        worksheet.write(
                            j + 12,
                            k + 1,
                            self.Race_list[0].iloc[j, k],
                            formats["normal_data_format"],
                        )
                # Ethnicity section
                worksheet.merge_range("A22:E22", "Ethnicity", formats["bold_11_format"])
                # Write Ethnicity row labels and data starting at row 22
                for j in range(len(self.Ethnicity_list[0])):
                    for k in range(len(self.Ethnicity_list[0].columns)):
                        worksheet.write(
                            j + 22,
                            k + 1,
                            self.Ethnicity_list[0].iloc[j, k],
                            formats["normal_data_format"],
                        )
                # Set column widths
                worksheet.set_column(0, 0, 30)  # First column wider for labels
                worksheet.set_column(1, 4, 15)  # Data columns

            # ==================== Enrollment Listing Tab ====================
            if (
                hasattr(self, "enrollment_output_df")
                and not self.enrollment_output_df.empty
            ):
                # Write data
                self.enrollment_output_df.to_excel(
                    writer,
                    sheet_name="DSMB-Enrollment Listing",
                    index=False,
                    header=False,
                    startrow=1,
                )
                worksheet = writer.sheets["DSMB-Enrollment Listing"]
                # Format headers
                for col_num, value in enumerate(
                    self.enrollment_output_df.columns.values
                ):
                    worksheet.write(0, col_num, value, formats["bold_12_wrap_format"])
                # Format data cells
                for row in range(1, len(self.enrollment_output_df) + 1):
                    for col in range(len(self.enrollment_output_df.columns)):
                        worksheet.write(
                            row,
                            col,
                            self.enrollment_output_df.iloc[row - 1, col],
                            formats["normal_data_format"],
                        )
                # Set column widths
                for idx, col in enumerate(self.enrollment_output_df.columns):
                    max_len = (
                        max(
                            self.enrollment_output_df[col].astype(str).map(len).max(),
                            len(str(col)),
                        )
                        + 3
                    )
                    worksheet.set_column(idx, idx, max_len)
                # Freeze top row
                worksheet.freeze_panes(1, 0)

            # ==================== Status Eligible Subjects Tab ====================
            if hasattr(self, "status_df") and not self.status_df.empty:
                # Write data
                self.status_df.to_excel(
                    writer,
                    sheet_name="DSMB-Status Eligible Subjects",
                    index=False,
                    header=False,
                    startrow=1,
                )
                worksheet = writer.sheets["DSMB-Status Eligible Subjects"]
                # Format headers
                for col_num, value in enumerate(self.status_df.columns.values):
                    worksheet.write(0, col_num, value, formats["bold_12_wrap_format"])
                # Format data cells
                for row in range(1, len(self.status_df) + 1):
                    for col in range(len(self.status_df.columns)):
                        worksheet.write(
                            row,
                            col,
                            self.status_df.iloc[row - 1, col],
                            formats["normal_data_format"],
                        )
                # Set column widths
                for idx, col in enumerate(self.status_df.columns):
                    max_len = (
                        max(
                            self.status_df[col].astype(str).map(len).max(),
                            len(str(col)),
                        )
                        + 3
                    )
                    worksheet.set_column(idx, idx, max_len)
                # Freeze top row
                worksheet.freeze_panes(1, 0)

            # ==================== Infusion Statistics Tab (BEFORE Infusion Listing) ====================
            if hasattr(self, "infusion_stat_df") and not self.infusion_stat_df.empty:
                # Create worksheet
                worksheet = writer.book.add_worksheet("DSMB-Infusion Statistics")
                # Define row indices
                row_indices = ["Mean SD", "Median", "Range"]
                # Create section headers
                worksheet.merge_range(
                    "B1:D1", "Cells Infused", formats["bold_12_format"]
                )
                worksheet.merge_range(
                    "E1:F1", "Transduction Efficiency", formats["bold_12_format"]
                )
                # Write column headers
                col_headers = [
                    "TmPSMA-02 CAR T Cells",
                    "Total Cells",
                    "Met Target Dose",
                    "%scFv Flow",
                    "Met Target %scFv",
                ]
                for col, header in enumerate(col_headers):
                    worksheet.write(1, col + 1, header, formats["bold_12_wrap_format"])
                # Write row indices
                for row, idx in enumerate(row_indices):
                    worksheet.write(row + 2, 0, idx, formats["bold_11_format"])
                # Write data
                for row in range(len(self.infusion_stat_df)):
                    for col in range(len(self.infusion_stat_df.columns)):
                        if row < len(
                            row_indices
                        ):  # Only write data for defined row indices
                            worksheet.write(
                                row
                                + 2,  # Row offset of 2 (merged header + column titles)
                                col + 1,  # Column offset of 1 (for row indices)
                                self.infusion_stat_df.iloc[row, col],
                                formats["normal_data_format"],
                            )
                # Merge Met Target Dose and Met Target %scFv cells of data
                # For "Met Target Dose" column (index 2) - merge for all row indices
                for row in range(len(row_indices)):
                    if row == 0:  # Only need to write data in first row
                        cell_value = self.infusion_stat_df.iloc[
                            0, 2  # Only need to write data in first row
                        ]  # Value from first row of "Met Target Dose" column
                        worksheet.merge_range(
                            2, 3, 4, 3, cell_value, formats["normal_data_format"]
                        )
                # For "Met Target %scFv" column (index 4) - merge for all row indices
                for row in range(len(row_indices)):
                    if row == 0:  # Only need to write data in first row
                        cell_value = self.infusion_stat_df.iloc[
                            0, 4  # Only need to write data in first row
                        ]  # Value from first row of "Met Target %scFv" column
                        worksheet.merge_range(
                            2, 5, 4, 5, cell_value, formats["normal_data_format"]
                        )
                # Set column widths
                worksheet.set_column(0, 0, 15)  # Row labels column
                worksheet.set_column(1, 5, 20)  # Data columns

            # ==================== Infusion Listing Tab (AFTER Infusion Statistics) ====================
            if hasattr(self, "infusion_df") and not self.infusion_df.empty:
                # Write data starting at row 3, using the display version with formatted values
                display_df = (
                    self.infusion_display_df
                    if hasattr(self, "infusion_display_df")
                    else self.infusion_df
                )
                display_df.to_excel(
                    writer,
                    sheet_name="DSMB-Infusion Listing",
                    index=False,
                    header=False,
                    startrow=2,
                )
                worksheet = writer.sheets["DSMB-Infusion Listing"]
                # Create merged header cells
                worksheet.merge_range("A1:A2", "Subject ID", formats["bold_12_format"])
                worksheet.merge_range(
                    "B1:B2", "Dose Level Assignment", formats["bold_12_format"]
                )
                worksheet.merge_range(
                    "C1:C2",
                    "Lymphodepleting Chemotherapy Dates",
                    formats["bold_12_format"],
                )
                worksheet.merge_range(
                    "D1:H1", "Cells Infused", formats["bold_12_format"]
                )
                worksheet.merge_range(
                    "I1:J1", "Transduction Efficiency", formats["bold_12_format"]
                )
                # Write column headers in row 2
                column_headers = [
                    "",
                    "",
                    "",
                    "Date of TmPSMA-02 CAR T Cell Infusion",
                    "Target TmPSMA-02 CAR T Cell Dose",
                    "Total TmPSMA-02 CAR T Cell Dose Administered",
                    "Total Cell Dose Administered",
                    "Met Target Dose",
                    "%scFv Flow",
                    "Met Target %scFv",
                ]
                for col, header in enumerate(column_headers):
                    if col >= 3:  # Skip the first 3 columns
                        worksheet.write(1, col, header, formats["bold_12_wrap_format"])
                # Format data cells
                for row in range(len(display_df)):
                    for col in range(len(display_df.columns)):
                        worksheet.write(
                            row + 2,  # Start at row 2 (0-indexed, so row 3)
                            col,
                            display_df.iloc[row, col],
                            formats["normal_data_format"],
                        )
                # Set column widths
                for idx, col in enumerate(display_df.columns):
                    max_len = (
                        max(display_df[col].astype(str).map(len).max(), len(str(col)))
                        + 3
                    )
                    worksheet.set_column(idx, idx, max_len)
                # Freeze top two rows
                worksheet.freeze_panes(2, 0)

            # ==================== Response Statistics Tab ====================
            if (
                hasattr(self, "recist_stats")
                and hasattr(self, "bone_scan_stats")
                and hasattr(self, "psa_stats")
            ):
                # Create worksheet
                worksheet = writer.book.add_worksheet("DSMB-Response Statistics")
                # Filter out Total rows from all stats dataframes
                recist_stats_filtered = self.recist_stats[
                    self.recist_stats.index != "Total"
                ]
                bone_scan_stats_filtered = self.bone_scan_stats[
                    self.bone_scan_stats.index != "Total"
                ]
                psa_stats_filtered = self.psa_stats[self.psa_stats.index != "Total"]
                # Add merged title across all tables
                worksheet.merge_range(
                    "A1:F1", "Best Overall Response", formats["bold_12_format"]
                )
                # Define column positions for the three tables
                col_recist = 0
                col_bone = 2
                col_psa = 4
                # Add table headers with subject counts
                recist_count = self.total_response_subjects
                bone_count = self.total_response_subjects
                psa_count = self.total_response_subjects
                worksheet.write(
                    1,
                    col_recist,
                    f"RECIST 1.1 (N={recist_count})",
                    formats["bold_11_format"],
                )
                worksheet.write(
                    1, col_recist + 1, "Count (%)", formats["bold_11_format"]
                )
                worksheet.write(
                    1,
                    col_bone,
                    f"Bone Scan Response (PCWG3) (N={bone_count})",
                    formats["bold_11_format"],
                )
                worksheet.write(1, col_bone + 1, "Count (%)", formats["bold_11_format"])
                worksheet.write(
                    1,
                    col_psa,
                    f"PSA Response (N={psa_count})",
                    formats["bold_11_format"],
                )
                worksheet.write(1, col_psa + 1, "Count (%)", formats["bold_11_format"])
                # Write RECIST data
                for i, (index, row) in enumerate(recist_stats_filtered.iterrows()):
                    worksheet.write(
                        i + 2, col_recist, index, formats["normal_data_format"]
                    )
                    # Combine count and percentage
                    count_perc = (
                        f"{row['Count']} ({row['Percentage'].replace('%', '')}%)"
                    )
                    worksheet.write(
                        i + 2, col_recist + 1, count_perc, formats["normal_data_format"]
                    )
                # Write Bone Scan data
                for i, (index, row) in enumerate(bone_scan_stats_filtered.iterrows()):
                    worksheet.write(
                        i + 2, col_bone, index, formats["normal_data_format"]
                    )
                    # Combine count and percentage
                    count_perc = (
                        f"{row['Count']} ({row['Percentage'].replace('%', '')}%)"
                    )
                    worksheet.write(
                        i + 2, col_bone + 1, count_perc, formats["normal_data_format"]
                    )
                # Write PSA Response data
                for i, (index, row) in enumerate(psa_stats_filtered.iterrows()):
                    worksheet.write(
                        i + 2, col_psa, index, formats["normal_data_format"]
                    )
                    # Combine count and percentage
                    count_perc = (
                        f"{row['Count']} ({row['Percentage'].replace('%', '')}%)"
                    )
                    worksheet.write(
                        i + 2, col_psa + 1, count_perc, formats["normal_data_format"]
                    )
                # Set column widths for all tables
                worksheet.set_column(
                    col_recist, col_recist, 30
                )  # RECIST response descriptions
                worksheet.set_column(
                    col_recist + 1, col_recist + 1, 15
                )  # RECIST count/%
                worksheet.set_column(
                    col_bone, col_bone, 40
                )  # Bone scan response descriptions
                worksheet.set_column(
                    col_bone + 1, col_bone + 1, 15
                )  # Bone scan count/%
                worksheet.set_column(col_psa, col_psa, 30)  # PSA response descriptions
                worksheet.set_column(col_psa + 1, col_psa + 1, 15)  # PSA count/%

            # ==================== Response Listing Tab ====================
            if hasattr(self, "response_df") and not self.response_df.empty:
                # Write data with a row offset of 2 to leave space for the header row
                self.response_df.to_excel(
                    writer,
                    sheet_name="DSMB-Response Listing",
                    index=False,
                    header=False,
                    startrow=2,
                )
                worksheet = writer.sheets["DSMB-Response Listing"]
                # Add merged header for "Overall Disease Response"
                worksheet.merge_range(
                    "B1:H1", "Overall Disease Response", formats["bold_12_format"]
                )
                # Write column headers in row 2
                worksheet.write(1, 0, "Subject", formats["bold_12_wrap_format"])
                worksheet.write(1, 1, "Response Type", formats["bold_12_wrap_format"])
                # Write all time point headers including additional ones
                for col, header in enumerate(self.time_points):
                    worksheet.write(1, col + 2, header, formats["bold_12_wrap_format"])
                # Group and merge subject cells
                # First, identify where each subject starts and ends
                subject_ranges = {}
                current_subject = None
                start_row = None
                # Scan through the dataframe to identify subject ranges
                for row_idx, row_data in self.response_df.iterrows():
                    subject = row_data["Subject"]
                    if subject != current_subject:
                        if current_subject is not None:
                            subject_ranges[current_subject] = (start_row, row_idx - 1)
                        current_subject = subject
                        start_row = row_idx
                # Add the last subject's range
                if current_subject is not None:
                    subject_ranges[current_subject] = (
                        start_row,
                        len(self.response_df) - 1,
                    )
                # Now merge cells for each subject range
                for subject, (start_idx, end_idx) in subject_ranges.items():
                    # Calculate Excel rows (add 2 for header rows offset)
                    excel_start_row = start_idx + 2
                    excel_end_row = end_idx + 2
                    # Only merge if there are multiple rows for this subject
                    if excel_start_row < excel_end_row:
                        worksheet.merge_range(
                            excel_start_row,
                            0,
                            excel_end_row,
                            0,
                            subject,
                            formats["normal_data_format"],
                        )
                    else:
                        # Single row case, just write the value directly
                        worksheet.write(
                            excel_start_row, 0, subject, formats["normal_data_format"]
                        )
                # Write the remaining data (response types and values) with wrap_format
                for row in range(len(self.response_df)):
                    for col in range(1, len(self.response_df.columns)):
                        worksheet.write(
                            row + 2,  # +2 due to header rows
                            col,
                            self.response_df.iloc[row, col],
                            formats[
                                "normal_data_wrap_format"
                            ],  # Changed to wrap format
                        )
                # Set column widths
                worksheet.set_column(0, 0, 15)  # Subject column
                worksheet.set_column(1, 1, 15)  # Response Type column
                worksheet.set_column(
                    2, 1 + len(self.time_points), 40
                )  # All time point columns including additional ones
                # Freeze top two rows and first two columns
                worksheet.freeze_panes(2, 2)

            # ==================== PET Imaging Tab ====================
            if hasattr(self, "pet_imaging_df") and not self.pet_imaging_df.empty:
                # Write data with a row offset of 2 to leave space for the header row
                self.pet_imaging_df.to_excel(
                    writer,
                    sheet_name="DSMB-PET Imaging",
                    index=False,
                    header=False,
                    startrow=2,
                )
                worksheet = writer.sheets["DSMB-PET Imaging"]
                # Add merged header for "PET Imaging Data"
                worksheet.merge_range(
                    "B1:E1", "PET Imaging Data", formats["bold_12_format"]
                )
                # Write column headers in row 2
                worksheet.write(1, 0, "Subject", formats["bold_12_wrap_format"])
                worksheet.write(1, 1, "Measurement", formats["bold_12_wrap_format"])
                worksheet.write(
                    1, 2, "Baseline (Pre-Tx Safety)", formats["bold_12_wrap_format"]
                )
                worksheet.write(
                    1, 3, "Post-Treatment (Day 28)", formats["bold_12_wrap_format"]
                )
                worksheet.write(
                    1, 4, "Disease Progression", formats["bold_12_wrap_format"]
                )
                # Group and merge subject cells
                # First, identify where each subject starts and ends
                subject_ranges = {}
                current_subject = None
                start_row = None
                # Scan through the dataframe to identify subject ranges
                for row_idx, row_data in self.pet_imaging_df.iterrows():
                    subject = row_data["Subject"]
                    if subject != current_subject:
                        if current_subject is not None:
                            subject_ranges[current_subject] = (start_row, row_idx - 1)
                        current_subject = subject
                        start_row = row_idx
                # Add the last subject's range
                if current_subject is not None:
                    subject_ranges[current_subject] = (
                        start_row,
                        len(self.pet_imaging_df) - 1,
                    )
                # Now merge cells for each subject range
                for subject, (start_idx, end_idx) in subject_ranges.items():
                    # Calculate Excel rows (add 2 for header rows offset)
                    excel_start_row = start_idx + 2
                    excel_end_row = end_idx + 2
                    # Only merge if there are multiple rows for this subject
                    if excel_start_row < excel_end_row:
                        worksheet.merge_range(
                            excel_start_row,
                            0,
                            excel_end_row,
                            0,
                            subject,
                            formats["normal_data_format"],
                        )
                    else:
                        # Single row case, just write the value directly
                        worksheet.write(
                            excel_start_row, 0, subject, formats["normal_data_format"]
                        )
                # Write the remaining data (Measurements and values) with wrap_format
                for row in range(len(self.pet_imaging_df)):
                    for col in range(1, len(self.pet_imaging_df.columns)):
                        worksheet.write(
                            row + 2,  # +2 due to header rows
                            col,
                            self.pet_imaging_df.iloc[row, col],
                            formats[
                                "normal_data_wrap_format"
                            ],  # Changed to wrap format
                        )
                # Set column widths
                worksheet.set_column(0, 0, 15)  # Subject column
                worksheet.set_column(1, 1, 20)  # Measurement column
                worksheet.set_column(2, 4, 25)  # All value columns
                # Freeze top two rows and first two columns
                worksheet.freeze_panes(2, 2)
