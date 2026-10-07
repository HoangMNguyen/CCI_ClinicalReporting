import numpy as np
import pandas as pd

from cci_automation.util import age_calculation, get_data_from_dict


def EnrollmentLog15122(raw_data):
    # * Filter conditions before calling
    # filter conditions for the raw data
    raw_data["PRTUBX"] = raw_data["PRTUBX"][
        raw_data["PRTUBX"]["Event Label"] == "Surgical Excision/Biopsy (Day 7)"
    ]

    # Re-consented subjects
    filtered_data1 = raw_data.copy()
    filtered_data1["DM"] = filtered_data1["DM"][
        filtered_data1["DM"]["Event Group Label"] == "Repeat Pre-Screening"
    ]
    filtered_data1["DSEOS"] = filtered_data1["DSEOS"][
        filtered_data1["DSEOS"]["Event Group Label"] == "Repeat End of Study"
    ]
    # Subjects not re-consented
    filtered_data2 = raw_data.copy()
    filtered_data2["DM"] = filtered_data2["DM"][
        ~filtered_data2["DM"]["Subject"].isin(filtered_data1["DM"]["Subject"])
    ]
    filtered_data2["DSEOS"] = filtered_data2["DSEOS"][
        filtered_data2["DSEOS"]["Event Group Label"] == "Common Forms"
    ]
    # re-consented subjects capturing the initial consent
    filtered_data3 = raw_data.copy()
    filtered_data3["DM"] = filtered_data3["DM"][
        filtered_data3["DM"]["Subject"].isin(filtered_data1["DM"]["Subject"])
        & (filtered_data3["DM"]["Event Group Label"] == "Pre-Screening")
    ]
    filtered_data3["DSEOS"] = filtered_data3["DSEOS"][
        filtered_data3["DSEOS"]["Event Group Label"] == "Common Forms"
    ]
    # remove all data other than 'DM', 'DSEOS'
    filtered_data3 = {
        key: filtered_data3[key] for key in ["DM", "DSEOS", "DSCA", "DSDLA"]
    }
    data_list = [filtered_data1, filtered_data2, filtered_data3]
    # create an empty dataframe
    output_df = pd.DataFrame()
    for data in data_list:
        # *
        input_dict = {
            "DM": {
                "Race (IG_NS_NA_DM1.CL_NS_YH_RACE_cl_NS_DMRACE1)": "Race",
                "Ethnicity (IG_NS_NA_DM1.CL_NS_NH_ETHNIC_cl_NS_DMETHNIC1)": "Ethnicity",
                "Sex Assigned at Birth (IG_NS_NA_DM1.CL_NS_NH_BRTHSEX_cl_NS_DMSEX3)": "Sex Assigned at Birth",
                "Legal Sex (IG_NS_NA_DM1.CL_NS_YH_SEX_cl_NS_DMSEX1)": "Legal Sex",
                "Date of Birth (IG_NS_NA_DM1.DT_NS_NH_BRTHDAT)": "Date of Birth",
                "Pre-Screening Consent Date (IG_NS_NA_DM1.DT_NS_YH_RFICDAT)": "Pre-Screening Consent Date",
            },
            "DSCA": {
                "Cohort Assignment (IG_NS_NA_DSCA1.CL_NS_YH_CACHASCOD_cl_NS_COHORT1)": "Cohort"
            },
            "DSDLA": {
                "Dose Level Assignment (IG_NS_NA_DSDLA1.CL_NS_YH_DLADOSELV_cl_NS_DOSELV1)": "Assigned Dose Level"
            },
            "IE": {
                "Main Consent Date (IG_NS_NA_IE1.DT_NS_NH_MAINCDAT)": "Main Consent Date",
                "Subject Meets All Study Eligibility (IG_NS_NA_IE3.CL_NS_YH_ELIGYN_cl_YS_YN1)": "Subject Meets All Study Eligibility",
                "Date of Eligibility Confirmation by Physician-Investigator (IG_NS_NA_IE5.DT_NS_YH_ELIGPIDAT)": "Date Physician-Investigator Confirmed Eligibility",
                "Date of Completion of Monitoring Visit for Eligibility (IG_NS_NA_IE5.DT_NS_YH_ELIGMONDAT)": "Date of Monitoring Visit for Eligibility",
            },
            "PRAPH": {
                "Apheresis Type (IG_NS_NA_PRAPH1.CL_NS_YH_APHTP_cl_NS_APHTP1)": "Apheresis Type (Fresh or Historical)",
                "Apheresis Date (IG_NS_NA_PRAPH1.DT_NS_NH_APHDAT)": "Date of Apheresis Collection",
            },
            "EXINF": {
                "Date Study Treatment Administered (IG_NS_NA_EXINF1.DT_NS_NH_INFDAT)": "Date of huCART-meso Injection (Day 0)"
            },
            "PRTUBX": {
                "Date of Tumor Sample Collection (IG_NS_NA_PRTUBX2.DT_NS_NH_TUDAT)": "Date of Surgical Excision or Tumor Biopsy (Day 7 +2d)",
                "Date of Surgery (IG_NS_NA_PRTUBX3.DT_NS_NH_SGDAT)": "Date of Surgery",
            },
            "DSINITLF": {
                "Last Study Visit Completed in Primary Follow-Up (IG_NS_NA_DSINITLF1.CL_NS_NH_LVCPFU_cl_YS_LVCPFU1)": "Last Study Visit Completed in Primary Follow-Up",
                "End of Primary Follow-Up Date (IG_NS_NA_DSINITLF1.DT_NS_YH_INITLFPFUENDDAT)": "Initiation of LTFU Date",
            },
            "DSEOS": {
                "End of Study Date (IG_NS_NA_DSEOS1.DT_NS_YH_EOSDAT)": "End of Study Date"
            },
        }

        merged_df = get_data_from_dict(data, input_dict)
        # * Additional processing after merging dataframes
        merged_df = age_calculation(
            merged_df,
            "Age at Consent",
            "Date of Birth",
            "Pre-Screening Consent Date",
            "Main Consent Date",
        )

        if "PRTUBX" in data:
            # combine 'Date of Surgery' and 'Date of Surgical Excision or Tumor Biopsy (Day 7 +2d)' columns
            merged_df["Date of Surgical Excision or Tumor Biopsy (Day 7 +2d)"] = (
                merged_df[
                    "Date of Surgical Excision or Tumor Biopsy (Day 7 +2d)"
                ].fillna(merged_df["Date of Surgery"])
            )

        # * Formatting

        merged_df = merged_df.rename(columns={"Subject": "Subject ID#"})

        # select and reorder columns
        column_list = [
            "Subject ID#",
            "Cohort",
            "Assigned Dose Level",
            "Race",
            "Ethnicity",
            "Sex Assigned at Birth",
            "Legal Sex",
            "Age at Consent",
            "Pre-Screening Consent Date",
            "Main Consent Date",
            "Date Physician-Investigator Confirmed Eligibility",
            "Date of Monitoring Visit for Eligibility",
            "Apheresis Type (Fresh or Historical)",
            "Date of Apheresis Collection",
            "Date of huCART-meso Injection (Day 0)",
            "Date of Surgical Excision or Tumor Biopsy (Day 7 +2d)",
            "Last Study Visit Completed in Primary Follow-Up",
            "Initiation of LTFU Date",
            "End of Study Date",
        ]
        # if merged_df does not have all the columns in column_list, add the missing columns
        for col in column_list:
            if col not in merged_df.columns:
                merged_df[col] = np.nan
        merged_df = merged_df[column_list]
        # merge the dataframes with the output dataframe
        output_df = pd.concat([output_df, merged_df], ignore_index=True)
    # sort based on 'Subject ID#' and 'Pre-Screening Consent Date'
    output_df = output_df.sort_values(
        ["Subject ID#", "Pre-Screening Consent Date"]
    ).reset_index(drop=True)
    # convert the date columns to string format
    for col in output_df.columns:
        if "Date" in col:
            output_df[col] = pd.to_datetime(output_df[col])
            output_df[col] = output_df[col].dt.strftime("%m/%d/%Y")

    return output_df
