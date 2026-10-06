#!/usr/bin/env python3
import pandas as pd
from dateutil.relativedelta import relativedelta


def EnrollmentLog03821(final_data):
    # DM
    # Check DM is blank
    if "DM" in final_data:
        DM_df = final_data["DM"][
            [
                "Subject",
                "Race (ig_DM1.RACE)",
                "Ethnicity (ig_DM1.ETHNIC)",
                "Sex Assigned at Birth (ig_DM1.BRTHSEX)",
                "Legal Sex (ig_DM1.SEX)",
                "Date of Birth (ig_DM1.BRTHDAT)",
                "Apheresis Consent Date (ig_DM1.RFICDAT)",
            ]
        ].copy()
        DM_new_col_name = {
            "Race (ig_DM1.RACE)": "Race",
            "Ethnicity (ig_DM1.ETHNIC)": "Ethnicity",
            "Sex Assigned at Birth (ig_DM1.BRTHSEX)": "Sex Assigned at Birth",
            "Legal Sex (ig_DM1.SEX)": "Legal Sex",
            "Date of Birth (ig_DM1.BRTHDAT)": "Date of Birth",
            "Apheresis Consent Date (ig_DM1.RFICDAT)": "Apheresis Consent Date",
        }
        DM_df = DM_df.rename(columns=DM_new_col_name)
        sorted_DM_df = DM_df.sort_values(["Subject"])

        # DSCA

        DSCA_df = final_data["DSCA"][
            [
                "Subject",
                "Study Phase (ig_DSCA1.CL_NS_NH_STDPHS_cl_NS_STDPHS1)",
                "Cohort/Treatment Arm Assignment (ig_DSCA1.CACHASCOD)",
            ]
        ].copy()
        DSCA_new_col_name = {
            "Study Phase (ig_DSCA1.CL_NS_NH_STDPHS_cl_NS_STDPHS1)": "Study Phase",
            "Cohort/Treatment Arm Assignment (ig_DSCA1.CACHASCOD)": "Study Assignment",
        }
        DSCA_df = DSCA_df.rename(columns=DSCA_new_col_name)
        merged_df = pd.merge(sorted_DM_df, DSCA_df, on="Subject", how="left")
        index_reference = merged_df.columns.get_loc("Race")
        merged_df.insert(
            index_reference,
            "Study Phase",
            merged_df.pop("Study Phase"),
        )
        merged_df.insert(
            index_reference + 1,
            "Study Assignment",
            merged_df.pop("Study Assignment"),
        )
        # print(merged_df)

        # MHDIAG
        MHDIAG_df = final_data["MHDIAG"][
            ["Subject", "Disease Type (ig_MHDIAG1.RSCAT)"]
        ].copy()
        MHDIAG_new_col_name = {"Disease Type (ig_MHDIAG1.RSCAT)": "Disease Type"}
        MHDIAG_df = MHDIAG_df.rename(columns=MHDIAG_new_col_name)
        merged_df = pd.merge(merged_df, MHDIAG_df, on="Subject", how="left")
        index_reference = merged_df.columns.get_loc("Study Phase")
        merged_df.insert(index_reference, "Disease Type", merged_df.pop("Disease Type"))

        # IE
        IE_df = final_data["IE"][
            [
                "Subject",
                "Main Consent Date (ig_IE1.MAINCDAT)",
                "Date of eligibility confirmation by physician-investigator (ig_IE5.ELIGPIDAT)",
                "Date of completion of monitoring visit for eligibility (ig_IE5.ELIGMONDAT)",
            ]
        ].copy()
        IE_new_col_name = {
            "Main Consent Date (ig_IE1.MAINCDAT)": "Main Consent Date",
            "Date of eligibility confirmation by physician-investigator (ig_IE5.ELIGPIDAT)": "Date Physician-Investigator Confirmed Eligibility",
            "Date of completion of monitoring visit for eligibility (ig_IE5.ELIGMONDAT)": "Date of Monitoring Visit for Eligibility",
        }
        IE_df = IE_df.rename(columns=IE_new_col_name)
        merged_df = pd.merge(merged_df, IE_df, on="Subject", how="left")
        # convert date columsn to datetime type
        merged_df["Apheresis Consent Date"] = pd.to_datetime(
            merged_df["Apheresis Consent Date"]
        )
        merged_df["Main Consent Date"] = pd.to_datetime(merged_df["Main Consent Date"])
        merged_df["Date of Birth"] = pd.to_datetime(merged_df["Date of Birth"])
        # Calculate time difference in days and convert to years
        # create a mask for non-NaT values in the two columns
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
        merged_df["Apheresis Consent Date"] = pd.to_datetime(
            merged_df["Apheresis Consent Date"]
        ).dt.strftime("%m/%d/%Y")
        merged_df["Main Consent Date"] = pd.to_datetime(
            merged_df["Main Consent Date"]
        ).dt.strftime("%m/%d/%Y")
        merged_df["Date Physician-Investigator Confirmed Eligibility"] = pd.to_datetime(
            merged_df["Date Physician-Investigator Confirmed Eligibility"]
        ).dt.strftime("%m/%d/%Y")
        merged_df["Date of Monitoring Visit for Eligibility"] = pd.to_datetime(
            merged_df["Date of Monitoring Visit for Eligibility"]
        ).dt.strftime("%m/%d/%Y")
        # print(merged_df)
        merged_df = merged_df.drop("Date of Birth", axis=1)

        # move the column
        index_reference = merged_df.columns.get_loc("Apheresis Consent Date")
        merged_df.insert(
            index_reference, "Age at Consent", merged_df.pop("Age at Consent")
        )

        # PRAPH
        APH_df = final_data["PRAPH"][
            [
                "Subject",
                "Apheresis Type (ig_PRAPH1.APHCAT)",
                "Apheresis Date (ig_PRAPH1.APHDAT)",
            ]
        ].copy()
        APH_new_col_name = {
            "Apheresis Type (ig_PRAPH1.APHCAT)": "Apheresis Type (Fresh or Historical)",
            "Apheresis Date (ig_PRAPH1.APHDAT)": "Date of Apheresis Collection",
        }
        APH_df = APH_df.rename(columns=APH_new_col_name)
        merged_df = pd.merge(merged_df, APH_df, on="Subject", how="left")
        merged_df["Date of Apheresis Collection"] = pd.to_datetime(
            merged_df["Date of Apheresis Collection"]
        ).dt.strftime("%m/%d/%Y")

        # EXVCNINF
        EXVCNINF_df = final_data["EXVCNINF"][
            ["Subject", "Infusion Date (ig_EXVCNINF1.INFDAT)"]
        ].copy()
        EXVCNINF_new_col_name = {
            "Infusion Date (ig_EXVCNINF1.INFDAT)": "Date of VCN-01 Infusion"
        }
        EXVCNINF_df = EXVCNINF_df.rename(columns=EXVCNINF_new_col_name)
        merged_df = pd.merge(merged_df, EXVCNINF_df, on="Subject", how="left")
        merged_df["Date of VCN-01 Infusion"] = pd.to_datetime(
            merged_df["Date of VCN-01 Infusion"]
        ).dt.strftime("%m/%d/%Y")
        # print(merged_df)

        # EXMESOINF
        INF_df = final_data["EXMESOINF"][
            ["Subject", "Event Group Label", "Infusion Date (ig_EXMESOINF1.INFDAT)"]
        ].copy()
        INF_df = INF_df[INF_df["Event Group Label"] != "Day 0-R"]
        INF_new_col_name = {
            "Infusion Date (ig_EXMESOINF1.INFDAT)": "Date of huCART-meso Infusion"
        }
        INF_df = INF_df.rename(columns=INF_new_col_name)
        INF_df = INF_df.drop("Event Group Label", axis=1)
        merged_df = pd.merge(merged_df, INF_df, on="Subject", how="left")
        merged_df["Date of huCART-meso Infusion"] = pd.to_datetime(
            merged_df["Date of huCART-meso Infusion"]
        ).dt.strftime("%m/%d/%Y")

        # DSINITLF
        INITLF_df = final_data["DSINITLF"][
            [
                "Subject",
                "From which Phase is the Subject entering Long-Term Follow-Up? (ig_DSINITLF1.DSPHASE)",
                "Last Study Visit Completed in Primary Follow-Up (ig_DSINITLF1.DSLVCPFU)",
                "End of Primary Follow-Up Date (ig_DSINITLF1.DSENPFUDAT)",
            ]
        ].copy()
        INITLF_df = INITLF_df[
            INITLF_df[
                "From which Phase is the Subject entering Long-Term Follow-Up? (ig_DSINITLF1.DSPHASE)"
            ]
            != "Retreatment"
        ]
        INITLF_new_col_name = {
            "Last Study Visit Completed in Primary Follow-Up (ig_DSINITLF1.DSLVCPFU)": "Last Study Visit Completed in Primary Follow-Up",
            "End of Primary Follow-Up Date (ig_DSINITLF1.DSENPFUDAT)": "Initiation of LTFU Date",
        }
        INITLF_df = INITLF_df.rename(columns=INITLF_new_col_name)
        INITLF_df = INITLF_df.drop(
            "From which Phase is the Subject entering Long-Term Follow-Up? (ig_DSINITLF1.DSPHASE)",
            axis=1,
        )
        merged_df = pd.merge(merged_df, INITLF_df, on="Subject", how="left")
        merged_df["Initiation of LTFU Date"] = pd.to_datetime(
            merged_df["Initiation of LTFU Date"]
        ).dt.strftime("%m/%d/%Y")

        # DSINITRT
        DSINITRT_df = final_data["DSINITRT"][
            [
                "Subject",
                "Last Visit Completed in Primary Follow-Up (ig_DSINITRT1.DSLVCPFUR)",
                "Will the Subject receive Retreatment? (ig_DSINITRT1.DSRTYN)",
                "From which Phase is the Subject entering Retreatment? (ig_DSINITRT1.DSPHASER)",
                "End of Primary Follow-Up Date (ig_DSINITRT1.DSRENPFUDAT)",
                "End of Long-Term Follow-Up Date (ig_DSINITRT1.DSRENLTFUDAT)",
            ]
        ].copy()
        DSINITRT_new_col_name = {
            "Will the Subject receive Retreatment? (ig_DSINITRT1.DSRTYN)": "Retreatment?",
            "From which Phase is the Subject entering Retreatment? (ig_DSINITRT1.DSPHASER)": "Phase",
            "End of Primary Follow-Up Date (ig_DSINITRT1.DSRENPFUDAT)": "Initiation of Retx Date",
            "End of Long-Term Follow-Up Date (ig_DSINITRT1.DSRENLTFUDAT)": "End of Long-Term Follow-Up Date",
        }
        DSINITRT_df = DSINITRT_df.rename(columns=DSINITRT_new_col_name)
        merged_df = pd.merge(merged_df, DSINITRT_df, on="Subject", how="left")
        # if 'Phase' = Primary Follow-Up, convert Initiation of LTFU Date to N/A
        merged_df.loc[
            merged_df["Phase"] == "Primary Follow-Up", "Initiation of LTFU Date"
        ] = "N/A"
        merged_df["Last Study Visit Completed in Primary Follow-Up"] = merged_df[
            "Last Study Visit Completed in Primary Follow-Up"
        ].fillna(
            merged_df[
                "Last Visit Completed in Primary Follow-Up (ig_DSINITRT1.DSLVCPFUR)"
            ]
        )
        merged_df["Initiation of Retx Date"] = merged_df[
            "Initiation of Retx Date"
        ].fillna(merged_df["End of Long-Term Follow-Up Date"])
        merged_df = merged_df.drop(
            "Last Visit Completed in Primary Follow-Up (ig_DSINITRT1.DSLVCPFUR)", axis=1
        )
        # Drop End of Long-Term Follow-Up Date and Phase column
        merged_df = merged_df.drop(["End of Long-Term Follow-Up Date", "Phase"], axis=1)
        merged_df["Initiation of Retx Date"] = pd.to_datetime(
            merged_df["Initiation of Retx Date"]
        ).dt.strftime("%m/%d/%Y")

        # EXCHMO
        EXCHMO_df = final_data["EXCHMO"][
            ["Subject", "Start Date (IG_NS_NA_EXCHMO2.DT_NS_NH_EXSTDAT)"]
        ].copy()
        EXCHMO_df = EXCHMO_df[
            EXCHMO_df["Start Date (IG_NS_NA_EXCHMO2.DT_NS_NH_EXSTDAT)"] != "NaN"
        ]
        EXCHMO_new_col_name = {
            "Start Date (IG_NS_NA_EXCHMO2.DT_NS_NH_EXSTDAT)": "Date of Initiation of Retx LD Chemo"
        }
        EXCHMO_df = EXCHMO_df.rename(columns=EXCHMO_new_col_name)
        EXCHMO_df["Date of Initiation of Retx LD Chemo"] = pd.to_datetime(
            EXCHMO_df["Date of Initiation of Retx LD Chemo"]
        )
        EXCHMO_df = EXCHMO_df.sort_values(
            by=["Subject", "Date of Initiation of Retx LD Chemo"]
        )
        EXCHMO_df = EXCHMO_df.drop_duplicates(subset=["Subject"], keep="first")

        merged_df = pd.merge(merged_df, EXCHMO_df, on="Subject", how="left")
        merged_df["Date of Initiation of Retx LD Chemo"] = merged_df[
            "Date of Initiation of Retx LD Chemo"
        ].dt.strftime("%m/%d/%Y")
        # if 'Study Phase' = Dose Finding Phase, convert Date of Initiation of Retx LD Chemo to N/A
        merged_df.loc[
            merged_df["Study Phase"] == "Dose Finding Phase",
            "Date of Initiation of Retx LD Chemo",
        ] = "N/A"

        # INF Retx
        INF_df = final_data["EXMESOINF"][
            ["Subject", "Event Group Label", "Infusion Date (ig_EXMESOINF1.INFDAT)"]
        ].copy()
        INF_df = INF_df[INF_df["Event Group Label"] == "Day 0-R"]
        INF_new_col_name = {
            "Infusion Date (ig_EXMESOINF1.INFDAT)": "CAR T cell Retreatment Date [Day 0-R]"
        }
        INF_df = INF_df.rename(columns=INF_new_col_name)
        INF_df = INF_df.drop("Event Group Label", axis=1)
        merged_df = pd.merge(merged_df, INF_df, on="Subject", how="left")
        merged_df["CAR T cell Retreatment Date [Day 0-R]"] = pd.to_datetime(
            merged_df["CAR T cell Retreatment Date [Day 0-R]"]
        ).dt.strftime("%m/%d/%Y")

        # INITLF Retx
        INITLF_df = final_data["DSINITLF"][
            [
                "Subject",
                "From which Phase is the Subject entering Long-Term Follow-Up? (ig_DSINITLF1.DSPHASE)",
                "Last Study Visit Completed in Retreatment (ig_DSINITLF1.DSLVCRETX)",
                "End of Retreatment Date (ig_DSINITLF1.DSENRETXDAT)",
            ]
        ].copy()
        INITLF_df = INITLF_df[
            INITLF_df[
                "From which Phase is the Subject entering Long-Term Follow-Up? (ig_DSINITLF1.DSPHASE)"
            ]
            == "Retreatment"
        ]
        INITLF_new_col_name = {
            "Last Study Visit Completed in Retreatment (ig_DSINITLF1.DSLVCRETX)": "Last Study Visit Completed in Retreatment F/up",
            "End of Retreatment Date (ig_DSINITLF1.DSENRETXDAT)": "Initiation of Retreatment LTFU Date",
        }
        INITLF_df = INITLF_df.rename(columns=INITLF_new_col_name)
        INITLF_df = INITLF_df.drop(
            "From which Phase is the Subject entering Long-Term Follow-Up? (ig_DSINITLF1.DSPHASE)",
            axis=1,
        )
        merged_df = pd.merge(merged_df, INITLF_df, on="Subject", how="left")
        merged_df["Initiation of Retreatment LTFU Date"] = pd.to_datetime(
            merged_df["Initiation of Retreatment LTFU Date"]
        ).dt.strftime("%m/%d/%Y")

        # EOS
        EOS_df = final_data["DSEOS"][
            ["Subject", "End of Study Date (ig_DSEOS1.EOSDAT)"]
        ].copy()
        EOS_new_col_name = {"End of Study Date (ig_DSEOS1.EOSDAT)": "End of Study Date"}
        EOS_df = EOS_df.rename(columns=EOS_new_col_name)
        merged_df = pd.merge(merged_df, EOS_df, on="Subject", how="left")
        merged_df["End of Study Date"] = pd.to_datetime(
            merged_df["End of Study Date"]
        ).dt.strftime("%m/%d/%Y")
        # update headers and fill N/A
        merged_df = merged_df.rename(columns={"Subject": "Subject ID#"})
        # merged_df.loc[
        #     merged_df["End of Study Date"].notna(), merged_df.columns.tolist()
        # ] = merged_df.loc[
        #     merged_df["End of Study Date"].notna(), merged_df.columns.tolist()
        # ].fillna("N/A")
        return merged_df
