import pandas as pd

from cci_automation.enrollment_log.EnrollmentLog30425 import (
    DSEOS_EOS_DATE,
    FPTMP_ADMIN_DATE_COL,
    FPTMP_PRIMARY_TP_COL,
    FPTMP_RETX_TP_COL,
    FPTMP_STUDY_PHASE_COL,
    PRIMARY_PET_COLUMNS,
    RETX_PET_COLUMNS,
    EnrollmentLog30425,
)


def _dm(subject):
    return pd.DataFrame(
        {
            "Subject": [subject],
            "Race (IG_NS_NA_DM1.CL_NS_YH_RACE_cl_NS_DMRACE1)": ["Asian"],
            "Ethnicity (IG_NS_NA_DM1.CL_NS_NH_ETHNIC_cl_NS_DMETHNIC1)": [
                "Non-Hispanic"
            ],
            "Sex Assigned at Birth (IG_NS_NA_DM1.CL_NS_NH_BRTHSEX_cl_NS_DMSEX3)": [
                "Male"
            ],
            "Legal Sex (IG_NS_NA_DM1.CL_NS_YH_SEX_cl_NS_DMSEX1)": ["Male"],
            "Date of Birth (IG_NS_NA_DM1.DT_NS_NH_BRTHDAT)": ["2000-01-01"],
        }
    )


def test_enrollment_log30425_sorts_fptmp_pet_columns_by_administration_date():
    subject = "30425-07"
    fptmp = pd.DataFrame(
        {
            "Subject": [subject] * 7,
            FPTMP_STUDY_PHASE_COL: [
                "Primary Treatment",
                "Primary Treatment",
                "Primary Treatment",
                "Primary Treatment",
                "Primary Treatment",  # excluded: Pre-Treatment Safety Visit
                "Retreatment",
                "Retreatment",
            ],
            FPTMP_PRIMARY_TP_COL: [
                "Day 14",
                "Day 7",
                "Day 21",
                "Day 10",
                "Pre-Treatment Safety Visit",
                None,
                None,
            ],
            FPTMP_RETX_TP_COL: [None, None, None, None, None, "Day 10-R", "Day 7-R"],
            FPTMP_ADMIN_DATE_COL: [
                "2026-06-05",
                "2026-06-03",
                "2026-06-06",
                "2026-06-04",
                "2026-06-02",
                "2026-05-29",
                "2026-05-28",
            ],
        }
    )

    output = EnrollmentLog30425({"DM": _dm(subject), "FPTMPADM": fptmp})

    # Primary admins sorted ascending fill PET0..PET3 (Pre-Treatment Safety Visit excluded)
    assert output.loc[0, "FP-TMP Admin/PET0"] == "06/03/2026"
    assert output.loc[0, "FP-TMP Admin/PET1"] == "06/04/2026"
    assert output.loc[0, "FP-TMP Admin/PET2"] == "06/05/2026"
    assert output.loc[0, "FP-TMP Admin/PET3"] == "06/06/2026"

    # Retreatment admins sorted ascending fill PET0R/PET1R; PET2R stays blank (static columns)
    assert output.loc[0, "FP-TMP Admin/PET0R"] == "05/28/2026"
    assert output.loc[0, "FP-TMP Admin/PET1R"] == "05/29/2026"
    assert pd.isna(output.loc[0, "FP-TMP Admin/PET2R"])


def test_enrollment_log30425_pet_columns_are_static():
    subject = "30425-07"
    # Five qualifying retreatment admins, but only three static PET#R columns exist.
    fptmp = pd.DataFrame(
        {
            "Subject": [subject] * 5,
            FPTMP_STUDY_PHASE_COL: ["Retreatment"] * 5,
            FPTMP_PRIMARY_TP_COL: [None] * 5,
            FPTMP_RETX_TP_COL: [
                "Day 7-R",
                "Day 10-R",
                "Day 14-R",
                "Day 21-R",
                "Day 28-R",
            ],
            FPTMP_ADMIN_DATE_COL: [
                "2026-05-28",
                "2026-05-29",
                "2026-06-01",
                "2026-06-02",
                "2026-06-09",
            ],
        }
    )

    output = EnrollmentLog30425({"DM": _dm(subject), "FPTMPADM": fptmp})

    # Exactly the static set of PET columns, no more
    assert [c for c in output.columns if str(c).startswith("FP-TMP Admin/PET")] == (
        PRIMARY_PET_COLUMNS + RETX_PET_COLUMNS
    )
    # Earliest three administrations are kept; the later two are dropped
    assert output.loc[0, "FP-TMP Admin/PET0R"] == "05/28/2026"
    assert output.loc[0, "FP-TMP Admin/PET1R"] == "05/29/2026"
    assert output.loc[0, "FP-TMP Admin/PET2R"] == "06/01/2026"


def test_enrollment_log30425_excludes_pre_retreatment_safety_visit():
    subject = "30425-03"
    fptmp = pd.DataFrame(
        {
            "Subject": [subject, subject],
            FPTMP_STUDY_PHASE_COL: ["Retreatment", "Retreatment"],
            FPTMP_PRIMARY_TP_COL: [None, None],
            FPTMP_RETX_TP_COL: ["Pre-Retreatment Safety Visit", "Day 7-R"],
            FPTMP_ADMIN_DATE_COL: ["2026-05-20", "2026-05-28"],
        }
    )

    output = EnrollmentLog30425({"DM": _dm(subject), "FPTMPADM": fptmp})

    # Only the non-safety-visit retreatment admin maps to a PET column
    assert output.loc[0, "FP-TMP Admin/PET0R"] == "05/28/2026"
    assert pd.isna(output.loc[0, "FP-TMP Admin/PET1R"])
    # No qualifying primary admins -> primary PET columns are blank
    assert pd.isna(output.loc[0, "FP-TMP Admin/PET0"])


def test_enrollment_log30425_age_at_consent_from_consent_date_and_dob():
    subject = "30425-05"
    dm = _dm(subject)
    ie = pd.DataFrame(
        {
            "Subject": [subject],
            "Consent Date (IG_NS_NA_IE1.DT_NS_NH_MAINCDAT)": ["2026-03-17"],
            "Date of Eligibility Confirmation by Physician-Investigator (IG_NS_NA_IE5.DT_NS_YH_ELIGPIDAT)": [
                "2026-03-17"
            ],
            "Date of Completion of Monitoring Visit for Eligibility (IG_NS_NA_IE5.DT_NS_YH_ELIGMONDAT)": [
                "2026-03-17"
            ],
        }
    )

    output = EnrollmentLog30425({"DM": dm, "IE": ie})

    assert output.loc[0, "Age at Consent"] == 26
    assert output.loc[0, "Consent Date"] == "03/17/2026"


def test_enrollment_log30425_returns_expected_static_columns_when_no_dm():
    output = EnrollmentLog30425({})

    assert output.empty
    assert output.columns[0] == "Subject ID#"
    assert output.columns[-1] == "End of Study Date"
    # The static PET columns are always present, even with no data
    assert [c for c in output.columns if str(c).startswith("FP-TMP Admin/PET")] == (
        PRIMARY_PET_COLUMNS + RETX_PET_COLUMNS
    )


def test_enrollment_log30425_keeps_latest_eos_date_when_multiple_rows():
    subject = "30425-07"
    dseos = pd.DataFrame(
        {
            "Subject": [subject, subject, subject],
            DSEOS_EOS_DATE: ["2026-05-01", "2026-06-09", "2026-03-15"],
        }
    )

    output = EnrollmentLog30425({"DM": _dm(subject), "DSEOS": dseos})

    assert len(output) == 1
    assert output.loc[0, "End of Study Date"] == "06/09/2026"


def test_enrollment_log30425_eos_latest_ignores_blank_date_rows():
    subject = "30425-07"
    dseos = pd.DataFrame(
        {
            "Subject": [subject, subject],
            DSEOS_EOS_DATE: ["2026-06-09", None],
        }
    )

    output = EnrollmentLog30425({"DM": _dm(subject), "DSEOS": dseos})

    assert len(output) == 1
    assert output.loc[0, "End of Study Date"] == "06/09/2026"
