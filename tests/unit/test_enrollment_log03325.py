import pandas as pd

from cci_automation.enrollment_log.EnrollmentLog03325 import EnrollmentLog03325


def test_enrollment_log03325_maps_cohort_b_dates_from_exchemo_and_exinf2():
    subject = "100-03325-01"
    dm = pd.DataFrame(
        {
            "Subject": [subject],
            "Race (IG_NS_NA_DM1.CL_NS_YH_RACE_cl_NS_DMRACE1)": ["Race"],
            "Ethnicity (IG_NS_NA_DM1.CL_NS_NH_ETHNIC_cl_NS_DMETHNIC1)": ["Ethnicity"],
            "Sex Assigned at Birth (IG_NS_NA_DM1.CL_NS_NH_BRTHSEX_cl_NS_DMSEX3)": [
                "Sex"
            ],
            "Legal Sex (IG_NS_NA_DM1.CL_NS_YH_SEX_cl_NS_DMSEX1)": ["Legal"],
            "Date of Birth (IG_NS_NA_DM1.DT_NS_NH_BRTHDAT)": ["2000-01-01"],
            "Main Consent Date (IG_NS_NA_DM1.DT_NS_YH_RFICDAT)": ["2025-01-01"],
        }
    )
    exchemo = pd.DataFrame(
        {
            "Subject": [subject, subject],
            "Event Group Label": ["Cycle 1 Day 1", "Cycle 1 Day 3-5"],
            "Event Date": ["2026-04-20", "2026-04-22"],
            "Was rituximab administered? (IG_NS_NA_EXCHMO2.CL_NS_NH_RITUADM_CL_YS_YNNRPP)": [
                "Yes",
                "",
            ],
            "Rituximab Administration Date (IG_NS_NA_EXCHMO2.DT_NS_NH_RITUADMDT)": [
                "2026-04-19",
                "",
            ],
            "Fludarabine Dose #1 Administration Date (IG_NS_NA_EXCHMO3.DT_NS_NH_FLUDD1DT)": [
                "",
                "2026-04-21",
            ],
            "Fludarabine Dose #2 Administration Date (IG_NS_NA_EXCHMO3.DT_NS_NH_FLUDD2DT)": [
                "",
                "",
            ],
            "Fludarabine Dose #3 Administration Date (IG_NS_NA_EXCHMO3.DT_NS_NH_FLUDD3DT)": [
                "",
                "",
            ],
            "Cyclophosphamide Dose #1 Administration Date (IG_NS_NA_EXCHMO4.DT_NS_NH_CYCLD1DT)": [
                "",
                "2026-04-23",
            ],
            "Cyclophosphamide Dose #2 Administration Date (IG_NS_NA_EXCHMO4.DT_NS_NH_CYCLD2DT)": [
                "",
                "",
            ],
            "Cyclophosphamide Dose #3 Administration Date (IG_NS_NA_EXCHMO4.DT_NS_NH_CYCLD3DT)": [
                "",
                "",
            ],
        }
    )
    exinf2 = pd.DataFrame(
        {
            "Subject": [subject, subject],
            "Event Group Label": ["Cycle 1 Day 8", "Cycle 2 Day 6"],
            "Event Date": ["2026-04-30", "2026-05-05"],
            "Cycle Number (IG_NS_NA_EXINF21.CL_YS_NH_CNUM_cl_NS_CNUM)": [
                "Cycle 1",
                "Cycle 2",
            ],
            "Were CART-EGFR-IL13Ra2 cells administered? (IG_NS_NA_EXINF21.CL_NS_NH_INFADMIN2_cl_YS_YN1)": [
                "Yes",
                "Yes",
            ],
            "Cell Product Administration Date (IG_NS_NA_EXINF21.DT_NS_NH_INFDAT)": [
                "2026-04-29",
                "",
            ],
        }
    )

    output = EnrollmentLog03325({"DM": dm, "EXCHEMO": exchemo, "EXINF2": exinf2})

    assert output.shape[1] == 30
    assert output.loc[0, "Date of Rituximab Administration (Cohort B)"] == "04/19/2026"
    assert output.loc[0, "Date of Initiation of LD Chemo (Cohort B)"] == "04/21/2026"
    assert output.loc[0, "Initial CAR T cell Administration Date"] == "04/29/2026"
    assert output.loc[0, "2nd CAR T cell Administration Date"] == "05/05/2026"


def test_enrollment_log03325_keeps_exinf_initial_date_before_exinf2_fallback():
    subject = "100-03325-01"
    dm = pd.DataFrame(
        {
            "Subject": [subject],
            "Race (IG_NS_NA_DM1.CL_NS_YH_RACE_cl_NS_DMRACE1)": ["Race"],
            "Ethnicity (IG_NS_NA_DM1.CL_NS_NH_ETHNIC_cl_NS_DMETHNIC1)": ["Ethnicity"],
            "Sex Assigned at Birth (IG_NS_NA_DM1.CL_NS_NH_BRTHSEX_cl_NS_DMSEX3)": [
                "Sex"
            ],
            "Legal Sex (IG_NS_NA_DM1.CL_NS_YH_SEX_cl_NS_DMSEX1)": ["Legal"],
            "Date of Birth (IG_NS_NA_DM1.DT_NS_NH_BRTHDAT)": ["2000-01-01"],
            "Main Consent Date (IG_NS_NA_DM1.DT_NS_YH_RFICDAT)": ["2025-01-01"],
        }
    )
    exinf = pd.DataFrame(
        {
            "Subject": [subject],
            "Event Group Label": ["Study Treatment"],
            "Study Treatment Date (IG_NS_NA_EXINF1.DT_NS_NH_INFDAT)": ["2026-04-28"],
        }
    )
    exinf2 = pd.DataFrame(
        {
            "Subject": [subject],
            "Event Group Label": ["Cycle 1 Day 8"],
            "Event Date": ["2026-04-30"],
            "Cycle Number (IG_NS_NA_EXINF21.CL_YS_NH_CNUM_cl_NS_CNUM)": ["Cycle 1"],
            "Were CART-EGFR-IL13Ra2 cells administered? (IG_NS_NA_EXINF21.CL_NS_NH_INFADMIN2_cl_YS_YN1)": [
                "Yes"
            ],
            "Cell Product Administration Date (IG_NS_NA_EXINF21.DT_NS_NH_INFDAT)": [
                "2026-04-29"
            ],
        }
    )

    output = EnrollmentLog03325({"DM": dm, "EXINF": exinf, "EXINF2": exinf2})

    assert output.loc[0, "Initial CAR T cell Administration Date"] == "04/28/2026"
