import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

SUBJECT = "Subject"
EVENT_GROUP_LABEL = "Event Group Label"

# DM (Demographics)
DM_RACE = "Race (IG_NS_NA_DM1.CL_NS_YH_RACE_cl_NS_DMRACE1)"
DM_ETHNICITY = "Ethnicity (IG_NS_NA_DM1.CL_NS_NH_ETHNIC_cl_NS_DMETHNIC1)"
DM_SEX_AT_BIRTH = "Sex Assigned at Birth (IG_NS_NA_DM1.CL_NS_NH_BRTHSEX_cl_NS_DMSEX3)"
DM_LEGAL_SEX = "Legal Sex (IG_NS_NA_DM1.CL_NS_YH_SEX_cl_NS_DMSEX1)"
DM_DOB = "Date of Birth (IG_NS_NA_DM1.DT_NS_NH_BRTHDAT)"

# DSTA (Treatment Arm Assignment)
DSTA_TREATMENT_ARM = (
    "Treatment Arm Assignment (IG_NS_NA_DSTA1.CL_NS_NH_CACHASCOD_cl_NS_TXARM1)"
)

# DSDLA (Dose Level Assignment)
DSDLA_DOSE_LEVEL = (
    "Dose Level Assignment (IG_NS_NA_DSDLA1.CL_NS_YH_DLADOSELV_cl_NS_DOSELV1)"
)

# IE (Eligibility)
IE_CONSENT_DATE = "Consent Date (IG_NS_NA_IE1.DT_NS_NH_MAINCDAT)"
IE_ELIGIBILITY_PI_DATE = "Date of Eligibility Confirmation by Physician-Investigator (IG_NS_NA_IE5.DT_NS_YH_ELIGPIDAT)"
IE_ELIGIBILITY_MONITOR_DATE = "Date of Completion of Monitoring Visit for Eligibility (IG_NS_NA_IE5.DT_NS_YH_ELIGMONDAT)"

# PRAPH (Apheresis)
PRAPH_APHERESIS_TYPE = "Apheresis Type (IG_NS_NA_PRAPH1.CL_NS_YH_APHTP_cl_NS_APHTP1)"
PRAPH_APHERESIS_DATE = "Apheresis Date (IG_NS_NA_PRAPH1.DT_NS_NH_APHDAT)"

# EXINF (CAR T cell Infusion)
EXINF_INFUSION_DATE = "Infusion Date (IG_NS_NA_EXINF1.DT_NS_NH_INFDAT)"

# EXCHMO (Lymphodepleting Chemotherapy)
EXCHMO_START_DATE = "Start Date (IG_NS_NA_EXCHMO2.DT_NS_NH_EXSTDAT)"

# DSINITLF (Initiation of Long-Term Follow-Up)
DSINITLF_PHASE = "From which Phase is the Subject entering Long-Term Follow-Up? (IG_NS_NA_DSINITLF1.CL_NS_NH_PHASELTFU_cl_NS_PHASE1)"
DSINITLF_LAST_VISIT_PFU = "Last Study Visit Completed in Primary Follow-Up (IG_NS_NA_DSINITLF1.CL_NS_NH_LVCPFU_cl_YS_LVCPFU1)"
DSINITLF_PFU_END_DATE = (
    "End of Primary Follow-Up Date (IG_NS_NA_DSINITLF1.DT_NS_YH_INITLFPFUENDDAT)"
)
DSINITLF_LAST_VISIT_RETX = "Last Study Visit Completed in Retreatment (IG_NS_NA_DSINITLF1.CL_NS_NH_LVCRETX_cl_NS_LVCPFUR1)"
DSINITLF_RETX_END_DATE = (
    "End of Retreatment Date (IG_NS_NA_DSINITLF1.DT_NS_YH_RETXENDDAT)"
)

# DSINITRT (Initiation of Retreatment)
DSINITRT_LAST_VISIT_PFU = "Last Visit Completed in Primary Follow-Up (IG_NS_NA_DSINITRT1.CL_NS_NH_RELVCPFU_cl_YS_LVCPFU1)"
DSINITRT_PHASE = "From which Phase is the Subject entering Retreatment? (IG_NS_NA_DSINITRT1.CL_NS_NH_PHASER_cl_NS_PHASE2)"
DSINITRT_PFU_END_DATE = (
    "End of Primary Follow-Up Date (IG_NS_NA_DSINITRT1.DT_NS_YH_PFUENDDAT)"
)
DSINITRT_LTFU_END_DATE = (
    "End of Long-Term Follow-Up Date (IG_NS_NA_DSINITRT1.DT_NS_YH_LTFUENDDAT)"
)

# DSEOS (End of Study)
DSEOS_EOS_DATE = "End of Study Date (IG_NS_NA_DSEOS1.DT_NS_YH_EOSDAT)"

# FPTMPADM (FP-TMP Administration)
FPTMP_STUDY_PHASE_COL = (
    "Study Phase (IG_YS_NA_FPTMPPHASETP.CL_YS_NH_STUDPSRS_cl_NS_STUDYPS2)"
)
FPTMP_PRIMARY_TP_COL = (
    "Primary Treatment Time Point (IG_YS_NA_FPTMPPHASETP.CL_YS_YH_IMGTPT_cl_NS_IMGTPT3)"
)
FPTMP_RETX_TP_COL = (
    "Retreatment Time Point (IG_YS_NA_FPTMPPHASETP.CL_YS_YH_IMGTPTR_cl_NS_IMGTPT4)"
)
FPTMP_ADMIN_DATE_COL = "Administration Date (IG_NS_NA_FPTMPADM1.DT_NS_NH_ADMDAT)"

# FP-TMP Admin/PET output columns (static). Administrations are sorted by Administration
# Date and placed into these columns in order; columns without data are left blank.
PRIMARY_PET_COLUMNS = [
    "FP-TMP Admin/PET0",
    "FP-TMP Admin/PET1",
    "FP-TMP Admin/PET2",
    "FP-TMP Admin/PET3",
]
RETX_PET_COLUMNS = [
    "FP-TMP Admin/PET0R",
    "FP-TMP Admin/PET1R",
    "FP-TMP Admin/PET2R",
]


def collect_fptmp_pet_columns(
    fptmp_df, study_phase, time_point_col, excluded_time_point, pet_columns
):
    """Map FP-TMP administrations into the given static PET columns for one study phase.

    Rows are filtered to the given Study Phase, excluding the specified safety-visit
    time point, then sorted by Administration Date. For each subject the administrations
    fill the PET columns in order; any administrations beyond the available columns are
    dropped and any unused columns are left blank.

    Args:
        fptmp_df (DataFrame): the FPTMPADM form data
        study_phase (str): the Study Phase value to keep ("Primary Treatment" or "Retreatment")
        time_point_col (str): the time point column to filter on
        excluded_time_point (str): the time point value to exclude (the safety visit)
        pet_columns (list): the ordered PET column names to populate

    Returns:
        DataFrame: a (Subject, *pet_columns) dataframe; empty when no administrations qualify
    """
    pet_df = fptmp_df[
        [SUBJECT, FPTMP_STUDY_PHASE_COL, time_point_col, FPTMP_ADMIN_DATE_COL]
    ].copy()
    pet_df = pet_df[
        pet_df[FPTMP_STUDY_PHASE_COL].fillna("").astype(str).str.strip() == study_phase
    ]
    pet_df = pet_df[
        pet_df[time_point_col].fillna("").astype(str).str.strip() != excluded_time_point
    ]
    pet_df["Administration Date"] = pd.to_datetime(
        pet_df[FPTMP_ADMIN_DATE_COL], errors="coerce"
    )
    pet_df = pet_df.dropna(subset=["Administration Date"])
    if pet_df.empty:
        return pd.DataFrame(columns=[SUBJECT] + pet_columns)
    pet_df = pet_df.sort_values([SUBJECT, "Administration Date"])
    pet_df["PET Sequence"] = pet_df.groupby(SUBJECT).cumcount()
    pet_df = pet_df[pet_df["PET Sequence"] < len(pet_columns)]
    pivot_df = pet_df.pivot(
        index=SUBJECT, columns="PET Sequence", values="Administration Date"
    ).reset_index()
    pivot_df = pivot_df.rename(
        columns={seq: pet_columns[seq] for seq in pivot_df.columns if seq != SUBJECT}
    )
    for col in pet_columns:
        if col not in pivot_df.columns:
            pivot_df[col] = pd.NaT
        pivot_df[col] = pd.to_datetime(pivot_df[col], errors="coerce").dt.strftime(
            "%m/%d/%Y"
        )
    return pivot_df[[SUBJECT] + pet_columns]


def EnrollmentLog30425(final_data):
    if "DM" in final_data and not final_data["DM"].empty:
        # DM (Demographics)
        DM_df = final_data["DM"][
            [SUBJECT, DM_RACE, DM_ETHNICITY, DM_SEX_AT_BIRTH, DM_LEGAL_SEX, DM_DOB]
        ].copy()
        DM_df = DM_df.rename(
            columns={
                DM_RACE: "Race",
                DM_ETHNICITY: "Ethnicity",
                DM_SEX_AT_BIRTH: "Sex Assigned at Birth",
                DM_LEGAL_SEX: "Legal Sex",
                DM_DOB: "Date of Birth",
            }
        )
        merged_df = DM_df.sort_values([SUBJECT])

        # DSTA (Treatment Arm Assignment)
        if "DSTA" in final_data and not final_data["DSTA"].empty:
            DSTA_df = final_data["DSTA"][[SUBJECT, DSTA_TREATMENT_ARM]].copy()
            DSTA_df = DSTA_df.rename(columns={DSTA_TREATMENT_ARM: "Treatment Arm"})
            merged_df = pd.merge(merged_df, DSTA_df, on=SUBJECT, how="left")
            index_reference = merged_df.columns.get_loc("Race")
            merged_df.insert(
                index_reference, "Treatment Arm", merged_df.pop("Treatment Arm")
            )

        # DSDLA (Dose Level Assignment)
        if "DSDLA" in final_data and not final_data["DSDLA"].empty:
            DSDLA_df = final_data["DSDLA"][[SUBJECT, DSDLA_DOSE_LEVEL]].copy()
            DSDLA_df = DSDLA_df.rename(
                columns={DSDLA_DOSE_LEVEL: "Assigned Dose Level"}
            )
            merged_df = pd.merge(merged_df, DSDLA_df, on=SUBJECT, how="left")
            index_reference = merged_df.columns.get_loc("Race")
            merged_df.insert(
                index_reference,
                "Assigned Dose Level",
                merged_df.pop("Assigned Dose Level"),
            )

        # IE (Consent Date and eligibility confirmation dates)
        if "IE" in final_data and not final_data["IE"].empty:
            IE_df = final_data["IE"][
                [
                    SUBJECT,
                    IE_CONSENT_DATE,
                    IE_ELIGIBILITY_PI_DATE,
                    IE_ELIGIBILITY_MONITOR_DATE,
                ]
            ].copy()
            IE_df = IE_df.rename(
                columns={
                    IE_CONSENT_DATE: "Consent Date",
                    IE_ELIGIBILITY_PI_DATE: "Date Physician-Investigator Confirmed Eligibility",
                    IE_ELIGIBILITY_MONITOR_DATE: "Date of Monitoring Visit for Eligibility",
                }
            )
            IE_df = IE_df.drop_duplicates(subset=[SUBJECT])
            merged_df = pd.merge(merged_df, IE_df, on=SUBJECT, how="left")

            # Age at Consent = years between Consent Date and Date of Birth
            merged_df["Consent Date"] = pd.to_datetime(merged_df["Consent Date"])
            merged_df["Date of Birth"] = pd.to_datetime(merged_df["Date of Birth"])
            mask = ~merged_df[["Consent Date", "Date of Birth"]].isnull().any(axis=1)
            merged_df.loc[mask, "Age at Consent"] = merged_df[mask].apply(
                lambda x: relativedelta(x["Consent Date"], x["Date of Birth"]).years,
                axis=1,
            )
            merged_df["Consent Date"] = pd.to_datetime(
                merged_df["Consent Date"]
            ).dt.strftime("%m/%d/%Y")
            merged_df["Date Physician-Investigator Confirmed Eligibility"] = (
                pd.to_datetime(
                    merged_df["Date Physician-Investigator Confirmed Eligibility"]
                ).dt.strftime("%m/%d/%Y")
            )
            merged_df["Date of Monitoring Visit for Eligibility"] = pd.to_datetime(
                merged_df["Date of Monitoring Visit for Eligibility"]
            ).dt.strftime("%m/%d/%Y")
            # move "Age at Consent" right before "Consent Date"
            index_reference = merged_df.columns.get_loc("Consent Date")
            merged_df.insert(
                index_reference, "Age at Consent", merged_df.pop("Age at Consent")
            )

        if "Date of Birth" in merged_df.columns:
            merged_df = merged_df.drop("Date of Birth", axis=1)

        # PRAPH (Apheresis)
        if "PRAPH" in final_data and not final_data["PRAPH"].empty:
            APH_df = final_data["PRAPH"][
                [SUBJECT, PRAPH_APHERESIS_TYPE, PRAPH_APHERESIS_DATE]
            ].copy()
            APH_df = APH_df.rename(
                columns={
                    PRAPH_APHERESIS_TYPE: "Apheresis Type (Fresh or Historical)",
                    PRAPH_APHERESIS_DATE: "Date of Apheresis Collection",
                }
            )
            merged_df = pd.merge(merged_df, APH_df, on=SUBJECT, how="left")
            merged_df["Date of Apheresis Collection"] = pd.to_datetime(
                merged_df["Date of Apheresis Collection"]
            ).dt.strftime("%m/%d/%Y")

        # EXINF (CAR T cell infusion - Primary Treatment)
        if "EXINF" in final_data and not final_data["EXINF"].empty:
            EXINF_df = final_data["EXINF"][
                [SUBJECT, EVENT_GROUP_LABEL, EXINF_INFUSION_DATE]
            ].copy()
            EXINF_df = EXINF_df[EXINF_df[EVENT_GROUP_LABEL] == "Study Treatment"]
            EXINF_df = EXINF_df.rename(
                columns={EXINF_INFUSION_DATE: "CAR T cell Infusion Date [Day 0]"}
            )
            EXINF_df = EXINF_df.drop(EVENT_GROUP_LABEL, axis=1)
            merged_df = pd.merge(merged_df, EXINF_df, on=SUBJECT, how="left")
            merged_df["CAR T cell Infusion Date [Day 0]"] = pd.to_datetime(
                merged_df["CAR T cell Infusion Date [Day 0]"]
            ).dt.strftime("%m/%d/%Y")

        # FP-TMP Administration - Primary Treatment
        if "FPTMPADM" in final_data and not final_data["FPTMPADM"].empty:
            primary_pet_df = collect_fptmp_pet_columns(
                final_data["FPTMPADM"],
                study_phase="Primary Treatment",
                time_point_col=FPTMP_PRIMARY_TP_COL,
                excluded_time_point="Pre-Treatment Safety Visit",
                pet_columns=PRIMARY_PET_COLUMNS,
            )
            if not primary_pet_df.empty:
                merged_df = pd.merge(merged_df, primary_pet_df, on=SUBJECT, how="left")

        # DSINITLF (Initiation of Long-Term Follow-Up - from Primary Follow-Up)
        if "DSINITLF" in final_data and not final_data["DSINITLF"].empty:
            INITLF_df = final_data["DSINITLF"][
                [
                    SUBJECT,
                    DSINITLF_PHASE,
                    DSINITLF_LAST_VISIT_PFU,
                    DSINITLF_PFU_END_DATE,
                ]
            ].copy()
            INITLF_df = INITLF_df[INITLF_df[DSINITLF_PHASE] != "Retreatment"]
            INITLF_df = INITLF_df.rename(
                columns={
                    DSINITLF_LAST_VISIT_PFU: "Last Study Visit Completed in Primary Follow-Up",
                    DSINITLF_PFU_END_DATE: "Initiation of LTFU Date",
                }
            )
            INITLF_df = INITLF_df.drop(DSINITLF_PHASE, axis=1)
            merged_df = pd.merge(merged_df, INITLF_df, on=SUBJECT, how="left")
            merged_df["Initiation of LTFU Date"] = pd.to_datetime(
                merged_df["Initiation of LTFU Date"]
            ).dt.strftime("%m/%d/%Y")

        # DSINITRT (Initiation of Retreatment)
        if "DSINITRT" in final_data and not final_data["DSINITRT"].empty:
            DSINITRT_df = final_data["DSINITRT"][
                [
                    SUBJECT,
                    DSINITRT_LAST_VISIT_PFU,
                    DSINITRT_PHASE,
                    DSINITRT_PFU_END_DATE,
                    DSINITRT_LTFU_END_DATE,
                ]
            ].copy()
            DSINITRT_df = DSINITRT_df.rename(
                columns={
                    DSINITRT_PHASE: "Phase",
                    DSINITRT_PFU_END_DATE: "Initiation of Retx Date",
                }
            )
            DSINITRT_df["Initiation of Retx Date"] = DSINITRT_df[
                "Initiation of Retx Date"
            ].fillna(DSINITRT_df[DSINITRT_LTFU_END_DATE])
            DSINITRT_df = DSINITRT_df.drop(DSINITRT_LTFU_END_DATE, axis=1)
            DSINITRT_df = DSINITRT_df.drop_duplicates(subset=[SUBJECT])
            merged_df = pd.merge(merged_df, DSINITRT_df, on=SUBJECT, how="left")
            # if entering Retreatment directly from Primary Follow-Up, there is no LTFU
            if "Initiation of LTFU Date" in merged_df.columns:
                merged_df.loc[
                    merged_df["Phase"] == "Primary Follow-Up", "Initiation of LTFU Date"
                ] = "N/A"
            if "Last Study Visit Completed in Primary Follow-Up" in merged_df.columns:
                merged_df["Last Study Visit Completed in Primary Follow-Up"] = (
                    merged_df["Last Study Visit Completed in Primary Follow-Up"].fillna(
                        merged_df[DSINITRT_LAST_VISIT_PFU]
                    )
                )
            else:
                merged_df = merged_df.rename(
                    columns={
                        DSINITRT_LAST_VISIT_PFU: "Last Study Visit Completed in Primary Follow-Up"
                    }
                )
            merged_df = merged_df.drop(
                columns=[
                    col
                    for col in [DSINITRT_LAST_VISIT_PFU, "Phase"]
                    if col in merged_df.columns
                ]
            )
            merged_df["Initiation of Retx Date"] = pd.to_datetime(
                merged_df["Initiation of Retx Date"]
            ).dt.strftime("%m/%d/%Y")

        # EXCHMO (Retreatment Lymphodepleting Chemotherapy)
        if "EXCHMO" in final_data and not final_data["EXCHMO"].empty:
            EXCHMO_df = final_data["EXCHMO"][
                [SUBJECT, EVENT_GROUP_LABEL, EXCHMO_START_DATE]
            ].copy()
            EXCHMO_df = EXCHMO_df[
                EXCHMO_df[EVENT_GROUP_LABEL]
                == "Retreatment Lymphodepleting Chemotherapy"
            ]
            EXCHMO_df = EXCHMO_df.drop_duplicates(subset=[SUBJECT])
            EXCHMO_df = EXCHMO_df.rename(
                columns={EXCHMO_START_DATE: "Date of Initiation of Retx LD Chemo"}
            )
            EXCHMO_df = EXCHMO_df.drop(EVENT_GROUP_LABEL, axis=1)
            merged_df = pd.merge(merged_df, EXCHMO_df, on=SUBJECT, how="left")
            merged_df["Date of Initiation of Retx LD Chemo"] = pd.to_datetime(
                merged_df["Date of Initiation of Retx LD Chemo"]
            ).dt.strftime("%m/%d/%Y")

        # EXINF (CAR T cell infusion - Retreatment)
        if "EXINF" in final_data and not final_data["EXINF"].empty:
            INF_df = final_data["EXINF"][
                [SUBJECT, EVENT_GROUP_LABEL, EXINF_INFUSION_DATE]
            ].copy()
            INF_df = INF_df[INF_df[EVENT_GROUP_LABEL] == "Study Retreatment"]
            INF_df = INF_df.rename(
                columns={EXINF_INFUSION_DATE: "CAR T cell Infusion Date [Day 0-R]"}
            )
            INF_df = INF_df.drop(EVENT_GROUP_LABEL, axis=1)
            merged_df = pd.merge(merged_df, INF_df, on=SUBJECT, how="left")
            merged_df["CAR T cell Infusion Date [Day 0-R]"] = pd.to_datetime(
                merged_df["CAR T cell Infusion Date [Day 0-R]"]
            ).dt.strftime("%m/%d/%Y")

        # FP-TMP Administration - Retreatment
        if "FPTMPADM" in final_data and not final_data["FPTMPADM"].empty:
            retx_pet_df = collect_fptmp_pet_columns(
                final_data["FPTMPADM"],
                study_phase="Retreatment",
                time_point_col=FPTMP_RETX_TP_COL,
                excluded_time_point="Pre-Retreatment Safety Visit",
                pet_columns=RETX_PET_COLUMNS,
            )
            if not retx_pet_df.empty:
                merged_df = pd.merge(merged_df, retx_pet_df, on=SUBJECT, how="left")

        # DSINITLF (Initiation of Long-Term Follow-Up - from Retreatment)
        if "DSINITLF" in final_data and not final_data["DSINITLF"].empty:
            INITLF_df = final_data["DSINITLF"][
                [
                    SUBJECT,
                    DSINITLF_PHASE,
                    DSINITLF_LAST_VISIT_RETX,
                    DSINITLF_RETX_END_DATE,
                ]
            ].copy()
            INITLF_df = INITLF_df[INITLF_df[DSINITLF_PHASE] == "Retreatment"]
            INITLF_df = INITLF_df.rename(
                columns={
                    DSINITLF_LAST_VISIT_RETX: "Last Study Visit Completed in Retreatment",
                    DSINITLF_RETX_END_DATE: "Initiation of Retreatment LTFU Date",
                }
            )
            INITLF_df = INITLF_df.drop(DSINITLF_PHASE, axis=1)
            merged_df = pd.merge(merged_df, INITLF_df, on=SUBJECT, how="left")
            merged_df["Initiation of Retreatment LTFU Date"] = pd.to_datetime(
                merged_df["Initiation of Retreatment LTFU Date"]
            ).dt.strftime("%m/%d/%Y")

        # DSEOS (End of Study)
        if "DSEOS" in final_data and not final_data["DSEOS"].empty:
            EOS_df = final_data["DSEOS"][[SUBJECT, DSEOS_EOS_DATE]].copy()
            EOS_df = EOS_df.rename(columns={DSEOS_EOS_DATE: "End of Study Date"})
            EOS_df["End of Study Date"] = pd.to_datetime(
                EOS_df["End of Study Date"], errors="coerce"
            )
            # a subject can have multiple EOS rows -> keep the one with the latest End of Study Date
            EOS_df = EOS_df.sort_values(
                [SUBJECT, "End of Study Date"], na_position="first"
            ).drop_duplicates(subset=[SUBJECT], keep="last")
            merged_df = pd.merge(merged_df, EOS_df, on=SUBJECT, how="left")
            merged_df["End of Study Date"] = pd.to_datetime(
                merged_df["End of Study Date"]
            ).dt.strftime("%m/%d/%Y")
            merged_df.drop_duplicates(inplace=True)

        merged_df = merged_df.rename(columns={SUBJECT: "Subject ID#"})
    else:
        merged_df = pd.DataFrame()

    # Re-order and add missing columns.
    column_list = (
        [
            "Subject ID#",
            "Treatment Arm",
            "Assigned Dose Level",
            "Race",
            "Ethnicity",
            "Sex Assigned at Birth",
            "Legal Sex",
            "Age at Consent",
            "Consent Date",
            "Date Physician-Investigator Confirmed Eligibility",
            "Date of Monitoring Visit for Eligibility",
            "Apheresis Type (Fresh or Historical)",
            "Date of Apheresis Collection",
            "CAR T cell Infusion Date [Day 0]",
        ]
        + PRIMARY_PET_COLUMNS
        + [
            "Last Study Visit Completed in Primary Follow-Up",
            "Initiation of LTFU Date",
            "Initiation of Retx Date",
            "Date of Initiation of Retx LD Chemo",
            "CAR T cell Infusion Date [Day 0-R]",
        ]
        + RETX_PET_COLUMNS
        + [
            "Last Study Visit Completed in Retreatment",
            "Initiation of Retreatment LTFU Date",
            "End of Study Date",
        ]
    )
    for col in column_list:
        if col not in merged_df.columns:
            merged_df[col] = np.nan
    merged_df = merged_df[column_list]
    return merged_df
