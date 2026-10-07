import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta


def EnrollmentLog03325(final_data):
    if "DM" in final_data and not final_data["DM"].empty:
        # DM
        DM_df = final_data["DM"][
            [
                "Subject",
                "Race (IG_NS_NA_DM1.CL_NS_YH_RACE_cl_NS_DMRACE1)",
                "Ethnicity (IG_NS_NA_DM1.CL_NS_NH_ETHNIC_cl_NS_DMETHNIC1)",
                "Sex Assigned at Birth (IG_NS_NA_DM1.CL_NS_NH_BRTHSEX_cl_NS_DMSEX3)",
                "Legal Sex (IG_NS_NA_DM1.CL_NS_YH_SEX_cl_NS_DMSEX1)",
                "Date of Birth (IG_NS_NA_DM1.DT_NS_NH_BRTHDAT)",
                "Main Consent Date (IG_NS_NA_DM1.DT_NS_YH_RFICDAT)",
            ]
        ].copy()
        DM_new_col_name = {
            "Race (IG_NS_NA_DM1.CL_NS_YH_RACE_cl_NS_DMRACE1)": "Race",
            "Ethnicity (IG_NS_NA_DM1.CL_NS_NH_ETHNIC_cl_NS_DMETHNIC1)": "Ethnicity",
            "Sex Assigned at Birth (IG_NS_NA_DM1.CL_NS_NH_BRTHSEX_cl_NS_DMSEX3)": "Sex Assigned at Birth",
            "Legal Sex (IG_NS_NA_DM1.CL_NS_YH_SEX_cl_NS_DMSEX1)": "Legal Sex",
            "Date of Birth (IG_NS_NA_DM1.DT_NS_NH_BRTHDAT)": "Date of Birth",
            "Main Consent Date (IG_NS_NA_DM1.DT_NS_YH_RFICDAT)": "Main Consent Date",
        }
        DM_df = DM_df.rename(columns=DM_new_col_name)
        DM_df["Main Consent Date"] = pd.to_datetime(DM_df["Main Consent Date"])
        sorted_DM_df = DM_df.sort_values(["Subject"])
        merged_df = sorted_DM_df

    if "DSDLA" in final_data and not final_data["DSDLA"].empty:
        # DSDLA
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
        merged_df = pd.merge(sorted_DM_df, DSDLA_df, on="Subject", how="left")
        index_reference = merged_df.columns.get_loc("Race")
        merged_df.insert(
            index_reference, "Assigned Dose Level", merged_df.pop("Assigned Dose Level")
        )

    if "DSCA" in final_data and not final_data["DSCA"].empty:
        # DSCA
        DSCA_df = final_data["DSCA"][
            [
                "Subject",
                "Cohort Assignment (IG_NS_NA_DSCA1.CL_NS_YH_CACHASCOD_cl_NS_COHORT1)",
            ]
        ].copy()
        DSCA_new_col_name = {
            "Cohort Assignment (IG_NS_NA_DSCA1.CL_NS_YH_CACHASCOD_cl_NS_COHORT1)": "Assigned Cohort"
        }
        DSCA_df = DSCA_df.rename(columns=DSCA_new_col_name)
        merged_df = pd.merge(merged_df, DSCA_df, on="Subject", how="left")
        index_reference = merged_df.columns.get_loc("Assigned Dose Level")
        merged_df.insert(
            index_reference, "Assigned Cohort", merged_df.pop("Assigned Cohort")
        )

    if "IE" in final_data and not final_data["IE"].empty:
        # IE Date of Confirmation of Step #1 Eligibility by PI
        IE_df = final_data["IE"][
            [
                "Subject",
                "Event Group Label",
                "Date of Eligibility Confirmation by Physician-Investigator (IG_NS_NA_IE5.DT_NS_YH_ELIGPIDAT)",
            ]
        ].copy()
        IE_df = IE_df[IE_df["Event Group Label"] == "Step #1 Screening/Eligibility"]
        IE_new_col_name = {
            "Date of Eligibility Confirmation by Physician-Investigator (IG_NS_NA_IE5.DT_NS_YH_ELIGPIDAT)": "Date of Confirmation of Step #1 Eligibility by PI"
        }
        IE_df = IE_df.rename(columns=IE_new_col_name)
        IE_df = IE_df.drop("Event Group Label", axis=1)
        merged_df = pd.merge(merged_df, IE_df, on="Subject", how="left")
        merged_df["Date of Confirmation of Step #1 Eligibility by PI"] = pd.to_datetime(
            merged_df["Date of Confirmation of Step #1 Eligibility by PI"]
        ).dt.strftime("%m/%d/%Y")

        # convert date columns to datetime type
        merged_df["Date of Birth"] = pd.to_datetime(merged_df["Date of Birth"])

        # Calculate time difference in days and convert to years
        # create a mask for non-NaT values in the two columns
        mask = ~merged_df[["Main Consent Date", "Date of Birth"]].isnull().any(axis=1)

        # apply relativedelta only to rows with non-NaT values in both columns
        merged_df.loc[mask, "Age at Consent"] = merged_df[mask].apply(
            lambda x: relativedelta(x["Main Consent Date"], x["Date of Birth"]).years,
            axis=1,
        )
        merged_df["Main Consent Date"] = pd.to_datetime(
            merged_df["Main Consent Date"]
        ).dt.strftime("%m/%d/%Y")
        merged_df = merged_df.drop("Date of Birth", axis=1)
        # move the column
        index_reference = merged_df.columns.get_loc("Main Consent Date")
        merged_df.insert(
            index_reference, "Age at Consent", merged_df.pop("Age at Consent")
        )

        # IE Date of Confirmation of Step #2 Eligibility by PI
        IE_df = final_data["IE"][
            [
                "Subject",
                "Event Group Label",
                "Date of Eligibility Confirmation by Physician-Investigator (IG_NS_NA_IE5.DT_NS_YH_ELIGPIDAT)",
            ]
        ].copy()
        IE_df = IE_df[IE_df["Event Group Label"] == "Step #2 Screening/Eligibility"]
        IE_new_col_name = {
            "Date of Eligibility Confirmation by Physician-Investigator (IG_NS_NA_IE5.DT_NS_YH_ELIGPIDAT)": "Date of Confirmation of Step #2 Eligibility by PI"
        }
        IE_df = IE_df.rename(columns=IE_new_col_name)
        IE_df = IE_df.drop("Event Group Label", axis=1)
        merged_df = pd.merge(merged_df, IE_df, on="Subject", how="left")
        merged_df["Date of Confirmation of Step #2 Eligibility by PI"] = pd.to_datetime(
            merged_df["Date of Confirmation of Step #2 Eligibility by PI"]
        ).dt.strftime("%m/%d/%Y")

        # IE Date of Confirmation of Step #2 Eligibility by Monitoring
        IE_df = final_data["IE"][
            [
                "Subject",
                "Event Group Label",
                "Date of Completion of Monitoring Visit for Eligibility (IG_NS_NA_IE5.DT_NS_YH_ELIGMONDAT)",
            ]
        ].copy()
        IE_df = IE_df[IE_df["Event Group Label"] == "Step #2 Screening/Eligibility"]
        IE_new_col_name = {
            "Date of Completion of Monitoring Visit for Eligibility (IG_NS_NA_IE5.DT_NS_YH_ELIGMONDAT)": "Date of Confirmation of Step #2 Eligibility by Monitoring"
        }
        IE_df = IE_df.rename(columns=IE_new_col_name)
        IE_df = IE_df.drop("Event Group Label", axis=1)
        merged_df = pd.merge(merged_df, IE_df, on="Subject", how="left")
        merged_df["Date of Confirmation of Step #2 Eligibility by Monitoring"] = (
            pd.to_datetime(
                merged_df["Date of Confirmation of Step #2 Eligibility by Monitoring"]
            ).dt.strftime("%m/%d/%Y")
        )

    if "PRAPH" in final_data and not final_data["PRAPH"].empty:
        # PRAPH
        APH_df = final_data["PRAPH"][
            [
                "Subject",
                "Apheresis Type (IG_NS_NA_PRAPH1.CL_NS_YH_APHTP_cl_NS_APHTP1)",
                "Apheresis Date (IG_NS_NA_PRAPH1.DT_NS_NH_APHDAT)",
            ]
        ].copy()
        APH_new_col_name = {
            "Apheresis Type (IG_NS_NA_PRAPH1.CL_NS_YH_APHTP_cl_NS_APHTP1)": "Apheresis Type (Fresh or Historical)",
            "Apheresis Date (IG_NS_NA_PRAPH1.DT_NS_NH_APHDAT)": "Date of Apheresis Collection",
        }
        APH_df = APH_df.rename(columns=APH_new_col_name)
        merged_df = pd.merge(merged_df, APH_df, on="Subject", how="left")
        merged_df["Date of Apheresis Collection"] = pd.to_datetime(
            merged_df["Date of Apheresis Collection"]
        ).dt.strftime("%m/%d/%Y")

    if "EXCHEMO" in final_data and not final_data["EXCHEMO"].empty:
        EXCHEMO_df = final_data["EXCHEMO"][
            [
                "Subject",
                "Event Group Label",
                "Event Date",
                "Was rituximab administered? (IG_NS_NA_EXCHMO2.CL_NS_NH_RITUADM_CL_YS_YNNRPP)",
                "Rituximab Administration Date (IG_NS_NA_EXCHMO2.DT_NS_NH_RITUADMDT)",
                "Fludarabine Dose #1 Administration Date (IG_NS_NA_EXCHMO3.DT_NS_NH_FLUDD1DT)",
                "Fludarabine Dose #2 Administration Date (IG_NS_NA_EXCHMO3.DT_NS_NH_FLUDD2DT)",
                "Fludarabine Dose #3 Administration Date (IG_NS_NA_EXCHMO3.DT_NS_NH_FLUDD3DT)",
                "Cyclophosphamide Dose #1 Administration Date (IG_NS_NA_EXCHMO4.DT_NS_NH_CYCLD1DT)",
                "Cyclophosphamide Dose #2 Administration Date (IG_NS_NA_EXCHMO4.DT_NS_NH_CYCLD2DT)",
                "Cyclophosphamide Dose #3 Administration Date (IG_NS_NA_EXCHMO4.DT_NS_NH_CYCLD3DT)",
            ]
        ].copy()
        RIT_df = EXCHEMO_df[
            EXCHEMO_df[
                "Was rituximab administered? (IG_NS_NA_EXCHMO2.CL_NS_NH_RITUADM_CL_YS_YNNRPP)"
            ]
            == "Yes"
        ].copy()
        RIT_df["Date of Rituximab Administration (Cohort B)"] = pd.to_datetime(
            RIT_df[
                "Rituximab Administration Date (IG_NS_NA_EXCHMO2.DT_NS_NH_RITUADMDT)"
            ],
            errors="coerce",
        ).fillna(pd.to_datetime(RIT_df["Event Date"], errors="coerce"))
        RIT_df = RIT_df.dropna(subset=["Date of Rituximab Administration (Cohort B)"])
        RIT_df = RIT_df.sort_values(
            ["Subject", "Date of Rituximab Administration (Cohort B)"]
        )
        RIT_df = RIT_df.drop_duplicates(subset=["Subject"])[
            ["Subject", "Date of Rituximab Administration (Cohort B)"]
        ]
        RIT_df["Date of Rituximab Administration (Cohort B)"] = RIT_df[
            "Date of Rituximab Administration (Cohort B)"
        ].dt.strftime("%m/%d/%Y")
        merged_df = pd.merge(merged_df, RIT_df, on="Subject", how="left")

        INILDCHEMO_df = EXCHEMO_df[
            EXCHEMO_df["Event Group Label"] == "Cycle 1 Day 3-5"
        ][
            [
                "Subject",
                "Fludarabine Dose #1 Administration Date (IG_NS_NA_EXCHMO3.DT_NS_NH_FLUDD1DT)",
                "Fludarabine Dose #2 Administration Date (IG_NS_NA_EXCHMO3.DT_NS_NH_FLUDD2DT)",
                "Fludarabine Dose #3 Administration Date (IG_NS_NA_EXCHMO3.DT_NS_NH_FLUDD3DT)",
                "Cyclophosphamide Dose #1 Administration Date (IG_NS_NA_EXCHMO4.DT_NS_NH_CYCLD1DT)",
                "Cyclophosphamide Dose #2 Administration Date (IG_NS_NA_EXCHMO4.DT_NS_NH_CYCLD2DT)",
                "Cyclophosphamide Dose #3 Administration Date (IG_NS_NA_EXCHMO4.DT_NS_NH_CYCLD3DT)",
            ]
        ].copy()
        ld_chemo_dates = INILDCHEMO_df[
            [
                "Fludarabine Dose #1 Administration Date (IG_NS_NA_EXCHMO3.DT_NS_NH_FLUDD1DT)",
                "Fludarabine Dose #2 Administration Date (IG_NS_NA_EXCHMO3.DT_NS_NH_FLUDD2DT)",
                "Fludarabine Dose #3 Administration Date (IG_NS_NA_EXCHMO3.DT_NS_NH_FLUDD3DT)",
                "Cyclophosphamide Dose #1 Administration Date (IG_NS_NA_EXCHMO4.DT_NS_NH_CYCLD1DT)",
                "Cyclophosphamide Dose #2 Administration Date (IG_NS_NA_EXCHMO4.DT_NS_NH_CYCLD2DT)",
                "Cyclophosphamide Dose #3 Administration Date (IG_NS_NA_EXCHMO4.DT_NS_NH_CYCLD3DT)",
            ]
        ].apply(lambda col: pd.to_datetime(col, errors="coerce"))
        INILDCHEMO_df["Date of Initiation of LD Chemo (Cohort B)"] = ld_chemo_dates.min(
            axis=1
        )
        INILDCHEMO_df = INILDCHEMO_df.dropna(
            subset=["Date of Initiation of LD Chemo (Cohort B)"]
        )
        INILDCHEMO_df = INILDCHEMO_df.sort_values(
            ["Subject", "Date of Initiation of LD Chemo (Cohort B)"]
        ).drop_duplicates(subset=["Subject"])
        INILDCHEMO_df = INILDCHEMO_df[
            ["Subject", "Date of Initiation of LD Chemo (Cohort B)"]
        ]
        INILDCHEMO_df["Date of Initiation of LD Chemo (Cohort B)"] = INILDCHEMO_df[
            "Date of Initiation of LD Chemo (Cohort B)"
        ].dt.strftime("%m/%d/%Y")
        merged_df = pd.merge(merged_df, INILDCHEMO_df, on="Subject", how="left")

    if "EXINF" in final_data and not final_data["EXINF"].empty:
        # EXINF
        EXINF_df = final_data["EXINF"][
            [
                "Subject",
                "Event Group Label",
                "Study Treatment Date (IG_NS_NA_EXINF1.DT_NS_NH_INFDAT)",
            ]
        ].copy()
        EXINF_df = EXINF_df[EXINF_df["Event Group Label"] == "Study Treatment"]
        EXINF_new_col_name = {
            "Study Treatment Date (IG_NS_NA_EXINF1.DT_NS_NH_INFDAT)": "Initial CAR T cell Administration Date"
        }
        EXINF_df = EXINF_df.rename(columns=EXINF_new_col_name)
        EXINF_df = EXINF_df.drop("Event Group Label", axis=1)
        merged_df = pd.merge(merged_df, EXINF_df, on="Subject", how="left")
        merged_df["Initial CAR T cell Administration Date"] = pd.to_datetime(
            merged_df["Initial CAR T cell Administration Date"]
        ).dt.strftime("%m/%d/%Y")

        # EXINF Retx
        EXINF_df = final_data["EXINF"][
            [
                "Subject",
                "Event Group Label",
                "Study Treatment Date (IG_NS_NA_EXINF1.DT_NS_NH_INFDAT)",
            ]
        ].copy()
        EXINF_df = EXINF_df[EXINF_df["Event Group Label"] == "Study Retreatment"]
        EXINF_new_col_name = {
            "Study Treatment Date (IG_NS_NA_EXINF1.DT_NS_NH_INFDAT)": "CAR T Cell Retreatment Date (Day 0-R)"
        }
        EXINF_df = EXINF_df.rename(columns=EXINF_new_col_name)
        EXINF_df = EXINF_df.drop("Event Group Label", axis=1)
        merged_df = pd.merge(merged_df, EXINF_df, on="Subject", how="left")
        merged_df["CAR T Cell Retreatment Date (Day 0-R)"] = pd.to_datetime(
            merged_df["CAR T Cell Retreatment Date (Day 0-R)"]
        ).dt.strftime("%m/%d/%Y")

    if "EXINF2" in final_data and not final_data["EXINF2"].empty:
        cycle_col = "Cycle Number (IG_NS_NA_EXINF21.CL_YS_NH_CNUM_cl_NS_CNUM)"
        administered_col = "Were CART-EGFR-IL13Ra2 cells administered? (IG_NS_NA_EXINF21.CL_NS_NH_INFADMIN2_cl_YS_YN1)"
        administration_date_col = (
            "Cell Product Administration Date (IG_NS_NA_EXINF21.DT_NS_NH_INFDAT)"
        )
        EXINF2_df = final_data["EXINF2"][
            [
                "Subject",
                "Event Group Label",
                "Event Date",
                cycle_col,
                administered_col,
                administration_date_col,
            ]
        ].copy()
        EXINF2_df = EXINF2_df[
            EXINF2_df[administered_col].fillna("").astype(str).str.strip().str.lower()
            == "yes"
        ]
        cycle_from_column = (
            EXINF2_df[cycle_col].astype(str).str.extract(r"Cycle\s*(\d+)", expand=False)
        )
        cycle_from_label = (
            EXINF2_df["Event Group Label"]
            .astype(str)
            .str.extract(r"Cycle\s*(\d+)", expand=False)
        )
        EXINF2_df["Administration Cycle"] = pd.to_numeric(
            cycle_from_column.fillna(cycle_from_label), errors="coerce"
        )
        EXINF2_df["Administration Date"] = pd.to_datetime(
            EXINF2_df[administration_date_col], errors="coerce"
        ).fillna(pd.to_datetime(EXINF2_df["Event Date"], errors="coerce"))
        EXINF2_df = EXINF2_df.dropna(
            subset=["Administration Cycle", "Administration Date"]
        )
        EXINF2_df["Administration Cycle"] = EXINF2_df["Administration Cycle"].astype(
            int
        )
        EXINF2_df = EXINF2_df[EXINF2_df["Administration Cycle"].between(1, 6)]
        EXINF2_df = EXINF2_df.sort_values(
            ["Subject", "Administration Cycle", "Administration Date"]
        )
        EXINF2_df = EXINF2_df.drop_duplicates(
            subset=["Subject", "Administration Cycle"]
        )

        if not EXINF2_df.empty:
            EXINF2_df = EXINF2_df.pivot(
                index="Subject",
                columns="Administration Cycle",
                values="Administration Date",
            ).reset_index()
            EXINF2_df = EXINF2_df.rename(
                columns={
                    1: "Initial CAR T cell Administration Date (EXINF2)",
                    2: "2nd CAR T cell Administration Date",
                    3: "3rd CAR T cell Administration Date",
                    4: "4th CAR T cell Administration Date",
                    5: "5th CAR T cell Administration Date",
                    6: "6th CAR T cell Administration Date",
                }
            )
            for col in EXINF2_df.columns:
                if col != "Subject":
                    EXINF2_df[col] = pd.to_datetime(
                        EXINF2_df[col], errors="coerce"
                    ).dt.strftime("%m/%d/%Y")
            merged_df = pd.merge(merged_df, EXINF2_df, on="Subject", how="left")
            initial_exinf2_col = "Initial CAR T cell Administration Date (EXINF2)"
            if initial_exinf2_col in merged_df.columns:
                if "Initial CAR T cell Administration Date" not in merged_df.columns:
                    merged_df["Initial CAR T cell Administration Date"] = np.nan
                merged_df["Initial CAR T cell Administration Date"] = merged_df[
                    "Initial CAR T cell Administration Date"
                ].combine_first(merged_df[initial_exinf2_col])
                merged_df = merged_df.drop(initial_exinf2_col, axis=1)

    if "DSINITLF" in final_data and not final_data["DSINITLF"].empty:
        # DSINITLF
        INITLF_df = final_data["DSINITLF"][
            [
                "Subject",
                "From which Phase is the Subject entering Long-Term Follow-Up? (IG_NS_NA_DSINITLF1.CL_NS_NH_PHASELTFU_cl_NS_PHASE1)",
                "Last Study Visit Completed in Primary Follow-Up (IG_NS_NA_DSINITLF1.CL_NS_NH_LVCPFU_cl_YS_LVCPFU1)",
                "End of Primary Follow-Up Date (IG_NS_NA_DSINITLF1.DT_NS_YH_INITLFPFUENDDAT)",
            ]
        ].copy()
        INITLF_df = INITLF_df[
            INITLF_df[
                "From which Phase is the Subject entering Long-Term Follow-Up? (IG_NS_NA_DSINITLF1.CL_NS_NH_PHASELTFU_cl_NS_PHASE1)"
            ]
            != "Retreatment"
        ]
        INITLF_new_col_name = {
            "Last Study Visit Completed in Primary Follow-Up (IG_NS_NA_DSINITLF1.CL_NS_NH_LVCPFU_cl_YS_LVCPFU1)": "Last Study Visit Completed in Primary Follow-Up",
            "End of Primary Follow-Up Date (IG_NS_NA_DSINITLF1.DT_NS_YH_INITLFPFUENDDAT)": "Initiation of LTFU Date",
        }
        INITLF_df = INITLF_df.rename(columns=INITLF_new_col_name)
        INITLF_df = INITLF_df.drop(
            "From which Phase is the Subject entering Long-Term Follow-Up? (IG_NS_NA_DSINITLF1.CL_NS_NH_PHASELTFU_cl_NS_PHASE1)",
            axis=1,
        )
        merged_df = pd.merge(merged_df, INITLF_df, on="Subject", how="left")
        merged_df["Initiation of LTFU Date"] = pd.to_datetime(
            merged_df["Initiation of LTFU Date"]
        ).dt.strftime("%m/%d/%Y")

        # INITLF Retx
        INITLF_df = final_data["DSINITLF"][
            [
                "Subject",
                "From which Phase is the Subject entering Long-Term Follow-Up? (IG_NS_NA_DSINITLF1.CL_NS_NH_PHASELTFU_cl_NS_PHASE1)",
                "Last Study Visit Completed in Retreatment (IG_NS_NA_DSINITLF1.CL_NS_NH_LVCRETX_cl_NS_LVCPFUR1)",
                "End of Retreatment Date (IG_NS_NA_DSINITLF1.DT_NS_YH_RETXENDDAT)",
            ]
        ].copy()
        INITLF_df = INITLF_df[
            INITLF_df[
                "From which Phase is the Subject entering Long-Term Follow-Up? (IG_NS_NA_DSINITLF1.CL_NS_NH_PHASELTFU_cl_NS_PHASE1)"
            ]
            == "Retreatment"
        ]
        INITLF_new_col_name = {
            "Last Study Visit Completed in Retreatment (IG_NS_NA_DSINITLF1.CL_NS_NH_LVCRETX_cl_NS_LVCPFUR1)": "Last Study Visit Completed in Retreatment (X-R)",
            "End of Retreatment Date (IG_NS_NA_DSINITLF1.DT_NS_YH_RETXENDDAT)": "Initiation of Retreatment LTFU Date",
        }
        INITLF_df = INITLF_df.rename(columns=INITLF_new_col_name)
        INITLF_df = INITLF_df.drop(
            "From which Phase is the Subject entering Long-Term Follow-Up? (IG_NS_NA_DSINITLF1.CL_NS_NH_PHASELTFU_cl_NS_PHASE1)",
            axis=1,
        )
        merged_df = pd.merge(merged_df, INITLF_df, on="Subject", how="left")
        merged_df["Initiation of Retreatment LTFU Date"] = pd.to_datetime(
            merged_df["Initiation of Retreatment LTFU Date"]
        ).dt.strftime("%m/%d/%Y")

    if "DSINITRT" in final_data and not final_data["DSINITRT"].empty:
        # DSINITRT
        DSINITRT_df = final_data["DSINITRT"][
            [
                "Subject",
                "Last Visit Completed in Primary Follow-Up (IG_NS_NA_DSINITRT1.CL_NS_NH_RELVCPFU_cl_YS_LVCPFU1)",
                "Will the Subject receive Retreatment? (IG_NS_NA_DSINITRT1.CL_NS_NH_RTYN_cl_YS_YN1)",
                "From which Phase is the Subject entering Retreatment? (IG_NS_NA_DSINITRT1.CL_NS_NH_PHASER_cl_NS_PHASE2)",
                "End of Primary Follow-Up Date (IG_NS_NA_DSINITRT1.DT_NS_YH_PFUENDDAT)",
                "End of Long-Term Follow-Up Date (IG_NS_NA_DSINITRT1.DT_NS_YH_LTFUENDDAT)",
            ]
        ].copy()
        DSINITRT_new_col_name = {
            "Will the Subject receive Retreatment? (IG_NS_NA_DSINITRT1.CL_NS_NH_RTYN_cl_YS_YN1)": "Retreatment? (Cohort A)",
            "From which Phase is the Subject entering Retreatment? (IG_NS_NA_DSINITRT1.CL_NS_NH_PHASER_cl_NS_PHASE2)": "Phase",
            "End of Primary Follow-Up Date (IG_NS_NA_DSINITRT1.DT_NS_YH_PFUENDDAT)": "Initiation of Retx Date",
        }
        DSINITRT_df = DSINITRT_df.rename(columns=DSINITRT_new_col_name)
        DSINITRT_df["Initiation of Retx Date"] = DSINITRT_df[
            "Initiation of Retx Date"
        ].fillna(
            DSINITRT_df[
                "End of Long-Term Follow-Up Date (IG_NS_NA_DSINITRT1.DT_NS_YH_LTFUENDDAT)"
            ]
        )
        DSINITRT_df = DSINITRT_df.drop(
            "End of Long-Term Follow-Up Date (IG_NS_NA_DSINITRT1.DT_NS_YH_LTFUENDDAT)",
            axis=1,
        )
        merged_df = pd.merge(merged_df, DSINITRT_df, on="Subject", how="left")
        # if 'Phase' = Primary Follow-Up, convert Initiation of LTFU Date to N/A
        merged_df.loc[
            merged_df["Phase"] == "Primary Follow-Up", "Initiation of LTFU Date"
        ] = "N/A"
        merged_df["Last Study Visit Completed in Primary Follow-Up"] = merged_df[
            "Last Study Visit Completed in Primary Follow-Up"
        ].fillna(
            merged_df[
                "Last Visit Completed in Primary Follow-Up (IG_NS_NA_DSINITRT1.CL_NS_NH_RELVCPFU_cl_YS_LVCPFU1)"
            ]
        )
        merged_df = merged_df.drop(
            [
                "Last Visit Completed in Primary Follow-Up (IG_NS_NA_DSINITRT1.CL_NS_NH_RELVCPFU_cl_YS_LVCPFU1)",
                "Phase",
            ],
            axis=1,
        )
        merged_df["Initiation of Retx Date"] = pd.to_datetime(
            merged_df["Initiation of Retx Date"]
        ).dt.strftime("%m/%d/%Y")

    if "DSEOS" in final_data and not final_data["DSEOS"].empty:
        # EOS
        EOS_df = final_data["DSEOS"][
            ["Subject", "End of Study Date (IG_NS_NA_DSEOS1.DT_NS_YH_EOSDAT)"]
        ].copy()
        EOS_new_col_name = {
            "End of Study Date (IG_NS_NA_DSEOS1.DT_NS_YH_EOSDAT)": "End of Study Date"
        }
        EOS_df = EOS_df.rename(columns=EOS_new_col_name)
        merged_df = pd.merge(merged_df, EOS_df, on="Subject", how="left")
        merged_df["End of Study Date"] = pd.to_datetime(
            merged_df["End of Study Date"]
        ).dt.strftime("%m/%d/%Y")
        # Remove duplicate rows based on both columns
        merged_df.drop_duplicates(inplace=True)

    if "DM" not in final_data or final_data["DM"].empty:
        merged_df = pd.DataFrame()

    # Re-order and add missing columns
    column_list = [
        "Subject",
        "Assigned Cohort",
        "Assigned Dose Level",
        "Race",
        "Ethnicity",
        "Sex Assigned at Birth",
        "Legal Sex",
        "Age at Consent",
        "Main Consent Date",
        "Date of Confirmation of Step #1 Eligibility by PI",
        "Date of Confirmation of Step #2 Eligibility by PI",
        "Date of Confirmation of Step #2 Eligibility by Monitoring",
        "Apheresis Type (Fresh or Historical)",
        "Date of Apheresis Collection",
        "Date of Rituximab Administration (Cohort B)",  # new
        "Date of Initiation of LD Chemo (Cohort B)",  # new
        "Initial CAR T cell Administration Date",
        "2nd CAR T cell Administration Date",  # new
        "3rd CAR T cell Administration Date",  # new
        "4th CAR T cell Administration Date",  # new
        "5th CAR T cell Administration Date",  # new
        "6th CAR T cell Administration Date",  # new
        "Last Study Visit Completed in Primary Follow-Up",
        "Initiation of LTFU Date",
        "Retreatment? (Cohort A)",
        "Initiation of Retx Date",
        "CAR T Cell Retreatment Date (Day 0-R)",
        "Last Study Visit Completed in Retreatment (X-R)",
        "Initiation of Retreatment LTFU Date",
        "End of Study Date",
    ]
    for col in column_list:
        if col not in merged_df.columns:
            merged_df[col] = np.nan
    merged_df = merged_df[column_list]
    return merged_df
