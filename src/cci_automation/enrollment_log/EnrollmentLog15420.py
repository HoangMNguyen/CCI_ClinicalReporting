import pandas as pd
from dateutil.relativedelta import relativedelta


def EnrollmentLog15420(final_data):
    # DM
    # Check missing
    if "DM" in final_data:
        DM_df = final_data["DM"][
            [
                "Subject",
                "Race (ig_DM1.RACE)",
                "Ethnicity (ig_DM1.ETHNIC)",
                "Sex Assigned at Birth (ig_DM1.BRTHSEX)",
                "Legal Sex (ig_DM1.SEX)",
                "Date of Birth (ig_DM1.BRTHDAT)",
            ]
        ].copy()
        DM_new_col_name = {
            "Race (ig_DM1.RACE)": "Race",
            "Ethnicity (ig_DM1.ETHNIC)": "Ethnicity",
            "Sex Assigned at Birth (ig_DM1.BRTHSEX)": "Sex Assigned at Birth",
            "Legal Sex (ig_DM1.SEX)": "Legal Sex",
            "Date of Birth (ig_DM1.BRTHDAT)": "Date of Birth",
        }
        DM_df = DM_df.rename(columns=DM_new_col_name)
        sorted_DM_df = DM_df.sort_values(["Subject"])

    # DSCA
    if "DSCA" in final_data:
        DSCA_df = final_data["DSCA"][
            [
                "Subject",
                "Cohort Assignment (IG_NS_NA_DSCA1.CL_NS_NH_CACHASCOD_cl_NS_COHORT1)",
            ]
        ].copy()
        DSCA_new_col_name = {
            "Cohort Assignment (IG_NS_NA_DSCA1.CL_NS_NH_CACHASCOD_cl_NS_COHORT1)": "Cohort"
        }
        DSCA_df = DSCA_df.rename(columns=DSCA_new_col_name)
        merged_df = pd.merge(sorted_DM_df, DSCA_df, on="Subject", how="left")
        index_reference = merged_df.columns.get_loc("Race")
        merged_df.insert(index_reference, "Cohort", merged_df.pop("Cohort"))
    elif "PRDIAG" in final_data:
        PRDIAG_df = final_data["PRDIAG"][
            ["Subject", "Disease Type (ig_PRDIAG1.RSCAT)"]
        ].copy()
        PRDIAG_new_col_name = {"Disease Type (ig_PRDIAG1.RSCAT)": "Cohort"}
        PRDIAG_df = PRDIAG_df.rename(columns=PRDIAG_new_col_name)
        merged_df = pd.merge(sorted_DM_df, PRDIAG_df, on="Subject", how="left")
        index_reference = merged_df.columns.get_loc("Race")
        merged_df.insert(index_reference, "Cohort", merged_df.pop("Cohort"))
    else:
        merged_df = sorted_DM_df

    # DLA

    DLA_df = final_data["DLA"][
        ["Subject", "Dose Level Assignment (ig_DLA1.DLADOSELVL)"]
    ].copy()
    DLA_new_col_name = {
        "Dose Level Assignment (ig_DLA1.DLADOSELVL)": "Assigned Dose Level"
    }
    DLA_df = DLA_df.rename(columns=DLA_new_col_name)
    merged_df = pd.merge(merged_df, DLA_df, on="Subject", how="left")
    index_reference = merged_df.columns.get_loc("Race")
    merged_df.insert(
        index_reference, "Assigned Dose Level", merged_df.pop("Assigned Dose Level")
    )

    # IE
    IE_df = final_data["IE"][
        [
            "Subject",
            "Did subject sign the consent form? (ig_IE1.SIGNMAINC)",
            "Consent Date (ig_IE1.MAINCDAT)",
            "Date of eligibility confirmation by physician-investigator (ig_IE5.ELIGPIDAT)",
            "Date of completion of monitoring visit for eligibility (ig_IE5.ELIGMONDAT)",
        ]
    ].copy()
    IE_df = IE_df[
        IE_df["Did subject sign the consent form? (ig_IE1.SIGNMAINC)"] == "Yes"
    ]
    IE_df = IE_df.drop("Did subject sign the consent form? (ig_IE1.SIGNMAINC)", axis=1)
    IE_new_col_name = {
        "Consent Date (ig_IE1.MAINCDAT)": "Consent Date",
        "Date of eligibility confirmation by physician-investigator (ig_IE5.ELIGPIDAT)": "Date Physician-Investigator Confirmed Eligibility",
        "Date of completion of monitoring visit for eligibility (ig_IE5.ELIGMONDAT)": "Date of Monitoring Visit for Eligibility",
    }
    IE_df = IE_df.rename(columns=IE_new_col_name)
    IE_df["Date Physician-Investigator Confirmed Eligibility"] = pd.to_datetime(
        IE_df["Date Physician-Investigator Confirmed Eligibility"]
    ).dt.strftime("%m/%d/%Y")
    IE_df["Date of Monitoring Visit for Eligibility"] = pd.to_datetime(
        IE_df["Date of Monitoring Visit for Eligibility"]
    ).dt.strftime("%m/%d/%Y")
    merged_df = pd.merge(merged_df, IE_df, on="Subject", how="left")
    # convert date columsn to datetime type
    merged_df["Consent Date"] = pd.to_datetime(merged_df["Consent Date"])
    merged_df["Date of Birth"] = pd.to_datetime(merged_df["Date of Birth"])
    # create a mask for non-NaT values in the two columns
    mask = ~merged_df[["Consent Date", "Date of Birth"]].isnull().any(axis=1)

    # apply relativedelta only to rows with non-NaT values in both columns
    merged_df.loc[mask, "Age at Consent"] = merged_df[mask].apply(
        lambda x: relativedelta(x["Consent Date"], x["Date of Birth"]).years, axis=1
    )

    merged_df["Consent Date"] = pd.to_datetime(merged_df["Consent Date"]).dt.strftime(
        "%m/%d/%Y"
    )
    merged_df = merged_df.drop("Date of Birth", axis=1)

    # move the column
    index_reference = merged_df.columns.get_loc("Consent Date")
    merged_df.insert(index_reference, "Age at Consent", merged_df.pop("Age at Consent"))

    # APH
    APH_df = final_data["APH"][
        [
            "Subject",
            "Event Group Label",
            "Apheresis Type (ig_APH1.APHCAT)",
            "Apheresis Date (ig_APH1.APHDAT)",
        ]
    ].copy()
    APH_new_col_name = {
        "Apheresis Type (ig_APH1.APHCAT)": "Apheresis Type (Fresh or Historical)",
        "Apheresis Date (ig_APH1.APHDAT)": "Date of Apheresis Collection",
    }
    APH_df = APH_df[APH_df["Event Group Label"] == "Apheresis"]
    APH_df = APH_df.drop("Event Group Label", axis=1)
    APH_df = APH_df.rename(columns=APH_new_col_name)
    merged_df = pd.merge(merged_df, APH_df, on="Subject", how="left")
    merged_df["Date of Apheresis Collection"] = pd.to_datetime(
        merged_df["Date of Apheresis Collection"]
    ).dt.strftime("%m/%d/%Y")

    # EXCHMO
    EXCHMO_df = final_data["EXCHMO"][
        ["Subject", "Event Group Label", "Start Date (ig_EXCHMO2.EXSTDAT)"]
    ].copy()
    EXCHMO_df = EXCHMO_df[EXCHMO_df["Start Date (ig_EXCHMO2.EXSTDAT)"] != "NaN"]
    EXCHMO_df = EXCHMO_df[
        (EXCHMO_df["Event Group Label"] != "Retreatment Lymphodepleting Chemotherapy")
        & (
            EXCHMO_df["Event Group Label"]
            != "Retreatment Lymphodepleting Chemotherapy - ALL"
        )
    ]
    EXCHMO_df = EXCHMO_df.drop_duplicates(subset=["Subject"])
    EXCHMO_new_col_name = {
        "Start Date (ig_EXCHMO2.EXSTDAT)": "Date of Initiation of LD Chemo"
    }
    EXCHMO_df = EXCHMO_df.rename(columns=EXCHMO_new_col_name)
    EXCHMO_df = EXCHMO_df.sort_values(["Subject"])
    EXCHMO_df = EXCHMO_df.drop("Event Group Label", axis=1)
    merged_df = pd.merge(merged_df, EXCHMO_df, on="Subject", how="left")
    merged_df["Date of Initiation of LD Chemo"] = pd.to_datetime(
        merged_df["Date of Initiation of LD Chemo"]
    ).dt.strftime("%m/%d/%Y")

    # INF
    INF_df = final_data["INF"][
        ["Subject", "Event Group Label", "Infusion Date (ig_INF1.INFDAT)"]
    ].copy()
    INF_df = INF_df[
        (INF_df["Event Group Label"] != "Day 0-R")
        & (INF_df["Event Group Label"] != " Day 0-R")
    ]
    INF_new_col_name = {
        "Infusion Date (ig_INF1.INFDAT)": "CAR T cell Infusion Date [Day 0]"
    }
    INF_df = INF_df.rename(columns=INF_new_col_name)
    INF_df = INF_df.drop("Event Group Label", axis=1)
    merged_df = pd.merge(merged_df, INF_df, on="Subject", how="left")
    merged_df["CAR T cell Infusion Date [Day 0]"] = pd.to_datetime(
        merged_df["CAR T cell Infusion Date [Day 0]"]
    ).dt.strftime("%m/%d/%Y")

    # INITLF
    INITLF_df = final_data["INITLF"][
        [
            "Subject",
            "From which Phase is the Subject entering Long-Term Follow-Up? (ig_INITLF1.DSPHASE)",
            "Last Study Visit Completed in Primary Follow-Up (ig_INITLF1.DSLVCPFU)",
            "End of Primary Follow-Up Date (ig_INITLF1.DSENPFUDAT)",
        ]
    ].copy()
    INITLF_df = INITLF_df[
        INITLF_df[
            "From which Phase is the Subject entering Long-Term Follow-Up? (ig_INITLF1.DSPHASE)"
        ]
        != "Retreatment"
    ]
    INITLF_new_col_name = {
        "Last Study Visit Completed in Primary Follow-Up (ig_INITLF1.DSLVCPFU)": "Last Study Visit Completed in Primary Follow-Up",
        "End of Primary Follow-Up Date (ig_INITLF1.DSENPFUDAT)": "Initiation of LTFU Date",
    }
    INITLF_df = INITLF_df.rename(columns=INITLF_new_col_name)
    INITLF_df = INITLF_df.drop(
        "From which Phase is the Subject entering Long-Term Follow-Up? (ig_INITLF1.DSPHASE)",
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
            "From which Phase is the Subject entering Retreatment? (ig_DSINITRT1.DSPHASER)",
            "Will the Subject receive Retreatment? (ig_DSINITRT1.DSRTYN)",
            "End of Primary Follow-Up Date (ig_DSINITRT1.DSRENPFUDAT)",
            "End of Long-Term Follow-Up Date (ig_DSINITRT1.DSRENLTFUDAT)",
        ]
    ].copy()
    DSINITRT_new_col_name = {
        "Will the Subject receive Retreatment? (ig_DSINITRT1.DSRTYN)": "Retreatment?",
        "From which Phase is the Subject entering Retreatment? (ig_DSINITRT1.DSPHASER)": "Phase",
        "End of Primary Follow-Up Date (ig_DSINITRT1.DSRENPFUDAT)": "Initiation of Retx Date",
    }
    DSINITRT_df = DSINITRT_df.rename(columns=DSINITRT_new_col_name)
    DSINITRT_df["Initiation of Retx Date"] = DSINITRT_df[
        "Initiation of Retx Date"
    ].fillna(DSINITRT_df["End of Long-Term Follow-Up Date (ig_DSINITRT1.DSRENLTFUDAT)"])
    DSINITRT_df = DSINITRT_df.drop(
        "End of Long-Term Follow-Up Date (ig_DSINITRT1.DSRENLTFUDAT)", axis=1
    )
    merged_df = pd.merge(merged_df, DSINITRT_df, on="Subject", how="left")
    # if 'Phase' = Primary Follow-Up, convert Initiation of LTFU Date to N/A
    merged_df.loc[
        merged_df["Phase"] == "Primary Follow-Up", "Initiation of LTFU Date"
    ] = "N/A"
    merged_df["Last Study Visit Completed in Primary Follow-Up"] = merged_df[
        "Last Study Visit Completed in Primary Follow-Up"
    ].fillna(
        merged_df["Last Visit Completed in Primary Follow-Up (ig_DSINITRT1.DSLVCPFUR)"]
    )
    merged_df = merged_df.drop(
        ["Last Visit Completed in Primary Follow-Up (ig_DSINITRT1.DSLVCPFUR)", "Phase"],
        axis=1,
    )
    merged_df["Initiation of Retx Date"] = pd.to_datetime(
        merged_df["Initiation of Retx Date"]
    ).dt.strftime("%m/%d/%Y")

    # EXCHMO Retreatment
    EXCHMO_df = final_data["EXCHMO"][
        ["Subject", "Event Group Label", "Start Date (ig_EXCHMO2.EXSTDAT)"]
    ].copy()
    EXCHMO_df = EXCHMO_df[EXCHMO_df["Start Date (ig_EXCHMO2.EXSTDAT)"] != "NaN"]
    EXCHMO_df = EXCHMO_df[
        (EXCHMO_df["Event Group Label"] != "Lymphodepleting Chemotherapy")
        & (EXCHMO_df["Event Group Label"] != "Lymphodepleting Chemotherapy - ALL")
    ]
    EXCHMO_df = EXCHMO_df.drop_duplicates(subset=["Subject"])
    EXCHMO_new_col_name = {
        "Start Date (ig_EXCHMO2.EXSTDAT)": "Date of Initiation of Retx LD Chemo"
    }
    EXCHMO_df = EXCHMO_df.rename(columns=EXCHMO_new_col_name)
    EXCHMO_df = EXCHMO_df.sort_values(["Subject"])
    EXCHMO_df = EXCHMO_df.drop("Event Group Label", axis=1)
    merged_df = pd.merge(merged_df, EXCHMO_df, on="Subject", how="left")
    merged_df["Date of Initiation of Retx LD Chemo"] = pd.to_datetime(
        merged_df["Date of Initiation of Retx LD Chemo"]
    ).dt.strftime("%m/%d/%Y")

    # INF Retx
    INF_df = final_data["INF"][
        ["Subject", "Event Group Label", "Infusion Date (ig_INF1.INFDAT)"]
    ].copy()
    INF_df = INF_df[
        (INF_df["Event Group Label"] == "Day 0-R")
        | (INF_df["Event Group Label"] == " Day 0-R")
    ]
    INF_new_col_name = {
        "Infusion Date (ig_INF1.INFDAT)": "CAR T cell Retreatment Date [Day 0-R]"
    }
    INF_df = INF_df.rename(columns=INF_new_col_name)
    INF_df = INF_df.drop("Event Group Label", axis=1)
    merged_df = pd.merge(merged_df, INF_df, on="Subject", how="left")
    merged_df["CAR T cell Retreatment Date [Day 0-R]"] = pd.to_datetime(
        merged_df["CAR T cell Retreatment Date [Day 0-R]"]
    ).dt.strftime("%m/%d/%Y")

    # INITLF Retx
    INITLF_df = final_data["INITLF"][
        [
            "Subject",
            "From which Phase is the Subject entering Long-Term Follow-Up? (ig_INITLF1.DSPHASE)",
            "Last Study Visit Completed in Retreatment (ig_INITLF1.DSLVCRETX)",
            "End of Retreatment Date (ig_INITLF1.DSENRETXDAT)",
        ]
    ].copy()
    INITLF_df = INITLF_df[
        INITLF_df[
            "From which Phase is the Subject entering Long-Term Follow-Up? (ig_INITLF1.DSPHASE)"
        ]
        == "Retreatment"
    ]
    INITLF_new_col_name = {
        "Last Study Visit Completed in Retreatment (ig_INITLF1.DSLVCRETX)": "Last Study Visit Completed in Retreatment F/up",
        "End of Retreatment Date (ig_INITLF1.DSENRETXDAT)": "Initiation of Retreatment LTFU Date",
    }
    INITLF_df = INITLF_df.rename(columns=INITLF_new_col_name)
    INITLF_df = INITLF_df.drop(
        "From which Phase is the Subject entering Long-Term Follow-Up? (ig_INITLF1.DSPHASE)",
        axis=1,
    )
    merged_df = pd.merge(merged_df, INITLF_df, on="Subject", how="left")
    merged_df["Initiation of Retreatment LTFU Date"] = pd.to_datetime(
        merged_df["Initiation of Retreatment LTFU Date"]
    ).dt.strftime("%m/%d/%Y")

    # EOS
    EOS_df = final_data["EOS"][["Subject", "End of Study Date (ig_EOS1.EOSDAT)"]].copy()
    EOS_new_col_name = {"End of Study Date (ig_EOS1.EOSDAT)": "End of Study Date"}
    EOS_df = EOS_df.rename(columns=EOS_new_col_name)
    merged_df = pd.merge(merged_df, EOS_df, on="Subject", how="left")
    merged_df["End of Study Date"] = pd.to_datetime(
        merged_df["End of Study Date"]
    ).dt.strftime("%m/%d/%Y")

    # update headers and fill N/A
    merged_df = merged_df.rename(columns={"Subject": "Subject ID#"})
    return merged_df
