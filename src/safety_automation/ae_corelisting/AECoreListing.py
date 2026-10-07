"""The AE & DLT listing: Safety Automation's one workflow.

:func:`run` reads a Corelisting export and returns the workbook
(:class:`clinical_reporting.workflow.OutputFile`); :class:`AECoreListing`
works out the listing for one study. Nothing here touches Qt or a folder.
"""

import datetime  # Import datetime module
import io
import warnings
from typing import Optional

import numpy as np
import pandas as pd

from clinical_reporting.export import get_named_excel_formats
from clinical_reporting.workflow import (
    OutputFile,
    UnsupportedStudyError,
    missing_forms_error,
    named_output,
    read_corelisting,
    study_named_by,
)

# The listing's pandas steps warn about things that don't matter here. Only
# warnings raised from this module are ignored (a warnings.catch_warnings()
# around a run would change the filters of the whole process while it runs).
warnings.filterwarnings("ignore", module=r"safety_automation\.ae_corelisting")

#: What the messages call this workflow (in the middle of a sentence).
WORKFLOW = "the AE & DLT listing"
#: Studies the listing is set up for (each has its AE columns below).
SUPPORTED_STUDIES = ("03325", "10325", "11823", "12423", "15420", "16321")


def default_file_name(study: str) -> str:
    """The file name to suggest for *study*'s workbook (the run adds the time)."""
    return f"{study} AE DLT"


def _form_keys(key_map: dict) -> tuple[str, str, str, str]:
    """The names *key_map* gives the AE, DSDLA, DSCA and EXINF forms.

    A form without an entry keeps its own name.
    """
    return tuple(key_map.get(form, form) for form in ("AE", "DSDLA", "DSCA", "EXINF"))


def run(corelisting, *, file_name: str = "", study: Optional[str] = None) -> OutputFile:
    """Build the AE & DLT workbook from a Corelisting export.

    *corelisting* is the ZIP: its path, or a file-like object (an upload). The
    study comes from its file name unless *study* is given. The workbook is
    named *file_name* (or :func:`default_file_name`) plus the date and time.
    Raises :class:`~clinical_reporting.workflow.WorkflowInputError` when the
    file name names no study, the study isn't supported, or the export lacks a
    form the listing reads.
    """
    study = study or study_named_by(corelisting)
    if study not in SUPPORTED_STUDIES:
        raise UnsupportedStudyError(WORKFLOW, study, SUPPORTED_STUDIES)
    data = read_corelisting(corelisting)
    ae_key, _, _, exinf_key = _form_keys(AECoreListing.STUDY_KEY_MAP.get(study, {}))
    needed = {ae_key, exinf_key}
    if not needed <= set(data):
        raise missing_forms_error(WORKFLOW, needed - set(data))
    workbook = AECoreListing(data, study).to_excel_bytes()
    return named_output(
        workbook, file_name=file_name, default_name=default_file_name(study)
    )


class AECoreListing:
    """The AE & DLT listing of one study, worked out from its Corelisting forms."""

    # Add this mapping as a class variable or set in __init__
    STUDY_KEY_MAP = {
        "03325": {
            "AE": "AE",
            "DSDLA": "DSDLA",
            "EXINF": "EXINF",
        },
        "10325": {
            "AE": "AE",
            "DSDLA": "DSDLA",
            "EXINF": "EXINF",
        },
        "15420": {
            "AE": "AE",
            "DSDLA": "DLA",
            "DSCA": "DSCA",
            "EXINF": "INF",
        },
        "12423": {
            "AE": "AE",
            "DSDLA": "DSDLA",
            "DSCA": "DSCA",
            "EXINF": "EXINF",
        },
        "16321": {
            "AE": "AE",
            "DSCA": "DSCA",
            "EXINF": "EXINF",
        },
        # Add more studies as needed
    }

    def __init__(self, data, study_name):
        """Work out the listing from *data* (form name to its DataFrame)."""
        self.study_name = study_name
        self.key_map = self.STUDY_KEY_MAP.get(self.study_name, {})
        self.data = data
        self.output_df = self.calculate_output_df(self.data)

    def to_excel_bytes(self) -> bytes:
        """The listing workbook: the reformatted report and its source forms."""
        buffer = io.BytesIO()
        self.output(self.output_df, buffer)
        return buffer.getvalue()

    def get_cohort_value_dict(self, study_name):
        # initialize cohort_value_dict
        cohort_value_dict = {}
        if study_name == "03325":
            cohort_value_dict = {
                "Cohort A": "A",
                "Cohort B": "B",
                "Not Assigned": "Not Assigned",
            }
        elif study_name == "16321":
            cohort_value_dict = {
                "Cohort -1": -1,
                "Cohort 1": 1,
                "Cohort 2": 2,
                "Cohort 3": 3,
                "Cohort 4": 4,
                "Not Assigned": "Not Assigned",
            }
        elif study_name == "12423":
            cohort_value_dict = {
                "Cohort A: Non-Hodgkin Lymphoma": "A",
                "Not Assigned": "Not Assigned",
            }
        elif study_name == "15420":
            cohort_value_dict = {
                "Cohort A: Non-Hodgkin Lymphoma (NHL)": "A",
                "Cohort B: Chronic Lymphocytic Leukemia (CLL)": " B",
                "Cohort C: Acute Lymphoblastic Leukemia (ALL)": "C",
                "Cohort D": "D",
            }
        return cohort_value_dict

    def get_dose_level_assignment_value_dict(self, study_name):
        # initialize dose_level_assignment_value_dict
        dose_level_assignment_value_dict = {}
        if study_name == "03325":
            dose_level_assignment_value_dict = {
                "Dose Level -1 (DL-1)": "DL-1",
                "Dose Level 1 (DL1)": "DL1",
                "Not Assigned": "Not Assigned",
            }
        elif study_name == "10325":
            dose_level_assignment_value_dict = {
                "Dose Level -1 (DL-1)": "DL-1",
                "Dose Level 1 (DL1)": "DL1",
                "Not Applicable": "Not Applicable",
                "Not Assigned": "Not Assigned",
            }
        elif study_name == "11823":
            dose_level_assignment_value_dict = {
                "Dose Level -1 (DL-1)": "DL-1",
                "Dose Level 1 (DL1)": "DL1",
                "Dose Level 2 (DL2)": "DL2",
                "Dose Level 3 (DL3)": "DL3",
                "Not Assigned": "Not Assigned",
            }
        elif study_name == "12423":
            dose_level_assignment_value_dict = {
                "Dose Level -1 (DL-1)": "DL-1",
                "Dose Level 1 (DL1)": "DL1",
                "Dose Level 2 (DL2)": "DL2",
                "Dose Level 3 (DL3)": "DL3",
                "Not Assigned": "Not Assigned",
            }
        elif study_name == "15420":
            dose_level_assignment_value_dict = {
                "Dose Level -1 (DL-1)": "DL-1",
                "Dose Level 1a (DL1a)": "DL1a",
                "Dose Level 1b (DL1b)": "DL1b",
                "Dose Level 2 (DL2)": "DL2",
                "Dose Level 3 (DL3)": "DL3",
                "Dose Level 4 (DL4)": "DL4",
                "Dose Level 5 (DL5)": "DL5",
                "Not Assigned": "Not Assigned",
            }
        return dose_level_assignment_value_dict

    def get_dose_level_mapping(self, study_name):
        if study_name in ("03325", "10325"):
            dose_level_mapping = {
                "DL-1": (1, 7),
                "DL1": (2.5, 7),
            }
        elif study_name == "11823":
            dose_level_mapping = {
                "DL-1": (1, 7),
                "DL1": (5, 7),
                "DL2": (1, 8),
                "DL3": (3, 8),
            }
        elif study_name == "12423":
            dose_level_mapping = {
                "DL-1": (2, 6),
                "DL1": (7, 6),
                "DL2": (2, 7),
                "DL3": (6, 7),
            }
        elif study_name == "15420":
            dose_level_mapping = {
                "DL-1": (7, 5),
                "DL1b": (3, 6),
                "DL2": (7, 6),
                "DL3": (3, 7),
                "DL4": (7, 7),
                "DL5": (3, 8),
            }

        return dose_level_mapping

    @staticmethod
    def get_dose_level(dose, power, dose_level_mapping):
        """The dose level administered (DL1, DL2, …), or 'Not Matching'."""
        actual_dose = dose * (10**power)
        for dose_level, (p_dose, p_power) in dose_level_mapping.items():
            if actual_dose == p_dose * (10**p_power):
                return dose_level
        return "Not Matching"

    def get_AE_header_list(self, study_name):
        if study_name in ("03325", "10325"):
            header = [
                "Subject",
                "AE or SAE (IG_NS_NA_AE2.CL_NS_YH_AESEV_cl_NS_AESAE1)",
                "T-cell Attribution (IG_NS_NA_AE1.CL_YS_NH_AEREL_cl_NS_TCELLATRIB1)",
                "T-cell Expectedness (IG_NS_NA_AE1.CL_NS_YH_AETRTINTP_cl_YS_YN1)",
                "Specify Other Attribution (IG_NS_NA_AE1.TX_YS_NH_AERELSPOTH)",
                "Other Attribution (IG_NS_NA_AE1.CL_YS_NH_RELOTH_cl_NS_OTHATRIB1)",
                "CTCAE Category (IG_NS_NA_AE1.CL_YS_NH_AECAT_cl_NS_CTCAECAT2)",
                "Derived Toxicity (IG_NS_NA_AE1.DV_YS_YH_AETOXDV)",
                "Toxicity (IG_NS_NA_AE1.TX_YS_NH_AETOX)",
                "Grade (IG_NS_NA_AE1.CL_YS_YH_AETOXGR_cl_YS_AEGRADE1)",
                "Start Date (IG_NS_NA_AE1.DT_YS_NH_AESTDAT)",
                "Stop Date (IG_NS_NA_AE1.DT_YS_YH_AEENDAT)",
                "Event Onset (IG_NS_NA_AE1.CL_NS_YH_AEONSET_cl_NS_AEONSET1)",
                "Additional Toxicity Details (IG_NS_NA_AE1.TX_YS_YH_AETOXTERM)",
                "Event Ongoing (IG_NS_NA_AE1.CL_YS_YH_AEONGO_cl_NS_AEONGO1)",
            ]
        elif study_name == "11823":
            header = [
                "Subject",
                "AE or SAE? (IG_NS_NA_AE2.CL_YS_YH_AESEV_cl_NS_AESAE1)",
                "T-cell Attribution (IG_NS_NA_AE1.CL_YS_NH_AEREL_cl_NS_TCELLATRIB1)",
                "Sponsor T-cell Expectedness (IG_NS_NA_AE1.CL_NS_YH_AETRTINTP_cl_YS_YN1)",
                "Specify Other Attribution (IG_NS_NA_AE1.TX_YS_NH_AERELSPOTH)",
                "Other Attribution (IG_NS_NA_AE1.CL_YS_NH_RELOTH_cl_NS_OTHATRIB1)",
                "CTCAE Category (IG_NS_NA_AE1.CL_YS_NH_AECAT_cl_NS_CTCAECAT2)",
                "Derived Toxicity (IG_NS_NA_AE1.DV_YS_YH_AETOXDV)",
                "Toxicity (IG_NS_NA_AE1.TX_YS_NH_AETOX)",
                "Grade (IG_NS_NA_AE1.CL_YS_YH_AETOXGR_cl_YS_AEGRADE1)",
                "Start Date (IG_NS_NA_AE1.DT_YS_NH_AESTDAT)",
                "Stop Date (IG_NS_NA_AE1.DT_YS_YH_AEENDAT)",
                "Event Onset (IG_NS_NA_AE1.CL_NS_YH_AEONSET_cl_NS_AEONSET1)",
                "Additional Toxicity Details (IG_NS_NA_AE1.TX_YS_YH_AETOXTERM)",
                "Event Ongoing (IG_NS_NA_AE1.CL_YS_YH_AEONGO_cl_NS_AEONGO1)",
            ]
        elif study_name == "16321":
            header = [
                "Subject",
                "AE or SAE? (ig_AE2.AESEV)",
                "T-cell Attribution (ig_AE1.AEREL)",
                "T-cell Expectedness (ig_AE1.AETRTINTP)",
                "Specify Other Attribution (ig_AE1.AERELSPOTH)",
                "Other Attribution (ig_AE1.AERELOTH)",
                "Other Expectedness (ig_AE1.AETRTINTPOTH)",
                "CTCAE Category (ig_AE1.AECAT)",
                "Derived Toxicity (ig_AE1.AETOXDV)",
                "Toxicity (ig_AE1.AETOX)",
                "Grade (ig_AE1.AETOXGR)",
                "Start Date (ig_AE1.AESTDAT)",
                "Stop Date (ig_AE1.AEENDAT)",
                "Event Onset (ig_AE1.AEONSET)",
                "Additional Toxicity Details (ig_AE1.AETOXTERM)",
                "Event Ongoing (ig_AE1.AEONGO)",
            ]
        elif study_name == "12423":
            header = [
                "Subject",
                "AE or SAE? (IG_NS_NA_AE2.CL_YS_YH_AESEV_cl_NS_AESAE1)",
                "T-cell Attribution (IG_NS_NA_AE1.CL_YS_NH_AEREL_cl_NS_TCELLATRIB1)",
                "T-cell Expectedness (IG_NS_NA_AE1.CL_YS_YH_AETRTINTP_cl_YS_YN1)",
                "Specify Other Attribution (IG_NS_NA_AE1.TX_YS_NH_AERELSPOTH)",
                "Other Attribution (IG_NS_NA_AE1.CL_YS_NH_RELOTH_cl_NS_OTHATRIB1)",
                "CTCAE Category (IG_NS_NA_AE1.CL_YS_NH_AECAT_cl_NS_CTCAECAT2)",
                "Derived Toxicity (IG_NS_NA_AE1.DV_YS_YH_AETOXDV)",
                "Toxicity (IG_NS_NA_AE1.TX_YS_NH_AETOX)",
                "Grade (IG_NS_NA_AE1.CL_YS_YH_AETOXGR_cl_YS_AEGRADE1)",
                "Start Date (IG_NS_NA_AE1.DT_YS_NH_AESTDAT)",
                "Stop Date (IG_NS_NA_AE1.DT_YS_YH_AEENDAT)",
                "Event Onset (IG_NS_NA_AE1.CL_NS_YH_AEONSET_cl_NS_AEONSET1)",
                "Additional Toxicity Details (IG_NS_NA_AE1.TX_YS_YH_AETOXTERM)",
                "Event Ongoing (IG_NS_NA_AE1.CL_YS_YH_AEONGO_cl_NS_AEONGO1)",
            ]
        elif study_name == "15420":
            header = [
                "Subject",
                "AE or SAE? (ig_AE2.AESEV)",
                "T-cell Attribution (ig_AE1.AEREL)",
                "T-cell Expectedness (ig_AE1.AETRTINTP)",
                "Specify Other Attribution (ig_AE1.AERELSPOTH)",
                "Other Attribution (ig_AE1.AERELOTH)",
                "CTCAE Category (ig_AE1.AECAT)",
                # "Derived Toxicity (IG_NS_NA_AE1.DV_YS_YH_AETOXDV)", # there is no AETOXDV in 15420
                "Toxicity (ig_AE1.AETOX)",
                "Grade (ig_AE1.AETOXGR)",
                "Start Date (ig_AE1.AESTDAT)",
                "Stop Date (ig_AE1.AEENDAT)",
                "Event Onset (ig_AE1.AEONSET)",
                "Additional Toxicity Details (ig_AE1.AETOXTERM)",
                "Event Ongoing (ig_AE1.AEONGO)",
            ]

        return header

    def get_DSCA_header_list(self, study_name):
        header = None  # The study has no cohort assignment.
        if study_name == "03325":
            header = [
                "Subject",
                "Cohort Assignment (IG_NS_NA_DSCA1.CL_NS_YH_CACHASCOD_cl_NS_COHORT1)",
            ]
        elif study_name == "16321":
            header = [
                "Subject",
                "Cohort Assignment (ig_DSCA1.CACHASCOD)",
            ]
        elif study_name == "12423":
            header = [
                "Subject",
                "Cohort Assignment (IG_NS_NA_DSCA1.CL_NS_YH_CACHASCOD_cl_NS_COHORT1)",
            ]
        elif study_name == "15420":
            header = [
                "Subject",
                "Cohort Assignment (IG_NS_NA_DSCA1.CL_NS_NH_CACHASCOD_cl_NS_COHORT1)",
            ]
        return header

    def get_DSDLA_header_list(self, study_name):
        header = None  # The study has no dose-level assignment.
        if study_name in ("03325", "10325"):
            header = [
                "Subject",
                "Dose Level Assignment (IG_NS_NA_DSDLA1.CL_NS_YH_DLADOSELV_cl_NS_DOSELV1)",
            ]
        elif study_name == "11823":
            header = [
                "Subject",
                "Dose Level Assignment (IG_NS_NA_DSDLA1.CL_NS_YH_DLADOSELV_cl_NS_DOSELV1)",
            ]
        elif study_name == "12423":
            header = [
                "Subject",
                "Dose Level Assignment (IG_NS_NA_DSDLA1.CL_NS_YH_DLADOSELV_cl_NS_DOSELV1)",
            ]
        elif study_name == "15420":
            header = [
                "Subject",
                "Dose Level Assignment (ig_DLA1.DLADOSELVL)",
            ]
        return header

    def get_EXINF_DLA_header_list(self, study_name):
        if study_name in ("03325", "10325"):
            header = [
                "Subject",
                "Event Label",
                "CAR T Cell Dose Administered (IG_NS_NA_EXINF1.NM_NS_YH_TDOS)",
                "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TDOSXP_cl_YS_EX10POW1)",
            ]
        elif study_name == "11823":
            header = [
                "Subject",
                "Event Group Label",
                "CAR T Cell Dose Administered (IG_NS_NA_EXINF1.NM_NS_NH_TDOS)",
                "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TDOSXP_cl_YS_EX10POW1)",
            ]
        elif study_name == "12423":
            header = [
                "Subject",
                "Event Group Label",
                "CAR T Cell Dose Administered (IG_NS_NA_EXINF1.NM_NS_NH_TDOS)",
                "x 10 to the power of (IG_NS_NA_EXINF1.CL_NS_NH_TDOSXP_cl_YS_EX10POW1)",
            ]
        elif study_name == "15420":
            header = [
                "Subject",
                "Event Group Label",
                "CAR T Cell Dose Administered (ig_INF1.INFDOS)",
                "x 10 to the power of (ig_INF1.INFDOSXP)",
            ]
        return header

    def get_EXINF_header_list(self, study_name):
        if study_name in ("03325", "10325"):
            header = [
                "Subject",
                "Study Treatment Date (IG_NS_NA_EXINF1.DT_NS_NH_INFDAT)",
                "Study Day (IG_NS_NA_EXINF1.CL_NS_NH_STUDYDAY_cl_NS_STUYDAY1)",
            ]
        elif study_name == "11823":
            header = [
                "Subject",
                "Infusion Date (IG_NS_NA_EXINF1.DT_NS_NH_INFDAT)",
                "Study Day (IG_NS_NA_EXINF1.CL_NS_NH_STUDYDAY_cl_NS_STUDYD1)",
            ]
        elif study_name == "16321":
            header = [
                "Subject",
                "Study Treatment Date (ig_EXINF1.INFDAT)",
                "Study Day (ig_EXINF1.CL_NS_NH_STUDYDAY_cl_NS_STUYDAY1)",
            ]

        elif study_name == "12423":
            header = [
                "Subject",
                "Infusion Date (IG_NS_NA_EXINF1.DT_NS_NH_INFDAT)",
                "Study Day (IG_NS_NA_EXINF1.CL_NS_NH_STUDYDAY_cl_NS_STUDYD1)",
            ]
        elif study_name == "15420":
            header = [
                "Subject",
                "Infusion Date (ig_INF1.INFDAT)",
                "Study Day (ig_INF1.CLSTUDYDAY)",
            ]
        return header

    def get_infusion_details(self, study_name):
        if study_name == "03325":
            return ["Day 0", "Day 0-R"]
        elif study_name == "10325":
            return [
                "Day 0",
                "Day 13",
                "Day 14",
                "Day 15",
                "Day 16",
                "Day 17",
                "Day 18",
                "Day 19",
                "Day 20",
                "Day 21",
                "Day 0-R",
                "Day 13-R",
                "Day 14-R",
                "Day 15-R",
                "Day 16-R",
                "Day 17-R",
                "Day 18-R",
                "Day 19-R",
                "Day 20-R",
                "Day 21-R",
            ]
        elif study_name == "11823":
            return ["Day 0", "Day 0-R"]
        elif study_name == "16321":
            return ["Day 0", "Day 0-R1", "Day 0-R2"]
        elif study_name == "12423":
            return ["Day 0", "Day 0-R"]
        elif study_name == "15420":
            return ["Day 0", "Day 0-R"]

    # Define a function to compute DLT Duration based on the rules
    def compute_dlt_duration(self, row):
        start_date = row["Start Date"]
        stop_date = row["Stop Date"]
        infusion_date = row["Infusion Date #1"]
        d_plus_28 = row["D+28"]

        # Rule 1: If start date before infusion = N/A
        if pd.isna(start_date) or pd.isna(infusion_date) or start_date < infusion_date:
            return "N/A"

        # Rule 2: If start date after D+28 = N/A
        if start_date > d_plus_28:
            return "N/A"

        # Rule 3: If no stop date, duration is [D+28 - Start Date] + 1
        if pd.isna(stop_date):
            return (d_plus_28 - start_date).days + 1

        # Rule 4: If stop date exists
        if stop_date < d_plus_28:
            return (stop_date - start_date).days + 1
        else:
            return (d_plus_28 - start_date).days + 1

    def derive_toxicity_15420(self, toxicity_value):
        """
        Implements the Derived Toxicity logic for study 15420.
        Uses the exact column name string, not regex.
        """
        if pd.isna(toxicity_value):
            return toxicity_value
        derived = toxicity_value
        if "Other" in str(toxicity_value):
            # Extract text within parentheses (exact string logic)
            left_paren = toxicity_value.find("(")
            right_paren = toxicity_value.find(")", left_paren)
            if left_paren != -1 and right_paren != -1:
                inner = toxicity_value[left_paren + 1 : right_paren]
                inner_upper = inner.upper()
                if inner_upper.startswith("CAR "):
                    new_inner = "CAR " + inner[4:].lower()
                    derived = toxicity_value.replace(inner, new_inner)
                elif inner_upper.startswith("COVID"):
                    derived = toxicity_value
                else:
                    new_inner = inner[0].upper() + inner[1:].lower() if inner else inner
                    derived = toxicity_value.replace(inner, new_inner)
                # Replace "hlh" with "HLH" (case-insensitive)
                derived = derived.replace("hlh", "HLH").replace("HLH", "HLH")
        return derived

    def calculate_output_df(self, data):
        # get the keys based on the study name
        AE_key, DSDLA_key, DSCA_key, EXINF_key = _form_keys(self.key_map)

        # The cohort and dose-level forms count only for studies set up for them.
        uses_dsca = (
            DSCA_key in data.keys()
            and self.get_DSCA_header_list(self.study_name) is not None
        )
        uses_dsdla = (
            DSDLA_key in data.keys()
            and self.get_DSDLA_header_list(self.study_name) is not None
        )

        # Things to do:
        output_df = pd.DataFrame()
        # for each element in the header list, check if it is in the data[AE_key] columns. If it is, then copy over the data to the output_df but without the part with parentheses
        AE_header_list = self.get_AE_header_list(self.study_name)
        for header in AE_header_list:
            if header in data[AE_key].columns:
                # copy over the column
                output_df[header] = data[AE_key][header]
        # remove rows that second column of AE_header_list is blank (for when every field is ILB instead of form)
        output_df = output_df[output_df[AE_header_list[1]].notna()]
        # rename the columns to remove the part with parentheses
        output_df.columns = output_df.columns.str.replace(
            r"\s*\([^)]*\)\s*$", "", regex=True
        )

        if self.study_name == "15420":
            toxicity_col = "Toxicity"
            CTCAE_col = "CTCAE Category"
            CTCAE_idx = output_df.columns.get_loc(CTCAE_col)
            output_df.insert(
                CTCAE_idx + 1,
                "Derived Toxicity",
                output_df[toxicity_col].apply(self.derive_toxicity_15420),
            )
        # for the rest of the column within the data[AE_key] columns, copy over to the output_df
        for column in data[AE_key].columns:
            if column not in AE_header_list:
                output_df[column] = data[AE_key][column].copy()

        # Calculating the "Duration" column based on "Start Date" and "Stop Date"
        # Convert the "Start Date" and "Stop Date" columns to datetime
        output_df["Start Date"] = pd.to_datetime(
            output_df["Start Date"], errors="coerce"
        )
        output_df["Stop Date"] = pd.to_datetime(output_df["Stop Date"], errors="coerce")
        # Calculate the "Duration" column
        output_df["Duration"] = (
            output_df["Stop Date"] - output_df["Start Date"]
        ) + pd.Timedelta(days=1)
        # Replace NaN values with an empty string
        output_df["Duration"] = output_df["Duration"].dt.days
        output_df["Duration"] = output_df["Duration"].replace(np.nan, "")

        # Insert the "Duration" column after the "Stop Date" column
        stop_date_index = output_df.columns.get_loc(
            "Stop Date"
        )  # Get the index of the "Stop Date" column
        output_df.insert(stop_date_index + 1, "Duration", output_df.pop("Duration"))

        CTCAEabbrev = [
            "COVID",
            "GGT ",
            "INR ",
            "CD4 ",
            "CPK ",
            " I ",
            " II ",
            " T ",
            " QT ",
            " NOS",
            "CAR ",
            "HLH",
        ]
        # if CTCAEabbrev is in the "Derived Toxicity" column (case insensitive), then replace it with the uppercase version
        for abbrev in CTCAEabbrev:
            output_df["Derived Toxicity"] = output_df["Derived Toxicity"].str.replace(
                abbrev, abbrev.upper(), case=False
            )

        if uses_dsca:
            # get data from DSCA
            DSCA_header_list = self.get_DSCA_header_list(self.study_name)
            DSCA_df = data[DSCA_key][DSCA_header_list]
            # rename the second column of DSCA to "Cohort"
            DSCA_df = DSCA_df.rename(columns={DSCA_df.columns[1]: "Cohort"})
            # map the cohort values to the cohort names
            cohort_value_dict = self.get_cohort_value_dict(self.study_name)
            DSCA_df["Cohort"] = DSCA_df["Cohort"].map(cohort_value_dict)
            # fill blank values with "pending"
            DSCA_df["Cohort"] = DSCA_df["Cohort"].fillna("Pending")
            output_df = output_df.merge(DSCA_df, on="Subject", how="left")

            # inset the "Cohort" column after the "Subject" column
            subject_index = output_df.columns.get_loc("Subject")
            output_df.insert(subject_index + 1, "Cohort", output_df.pop("Cohort"))

        if uses_dsdla:
            # get data from Dose Level Assignment
            DSDLA_header_list = self.get_DSDLA_header_list(self.study_name)
            DSDLA_df = data[DSDLA_key][DSDLA_header_list]
            # rename the second column of DSDLA to "Dose Level Assignment"
            DSDLA_df = DSDLA_df.rename(
                columns={DSDLA_df.columns[1]: "Dose Level Assignment"}
            )
            # map the dose level assignment values to the dose level assignment names
            dose_level_assignment_value_dict = (
                self.get_dose_level_assignment_value_dict(self.study_name)
            )
            DSDLA_df["Dose Level Assignment"] = DSDLA_df["Dose Level Assignment"].map(
                dose_level_assignment_value_dict
            )
            # fill blank values with "pending"
            DSDLA_df["Dose Level Assignment"] = DSDLA_df[
                "Dose Level Assignment"
            ].fillna("Pending")
            output_df = output_df.merge(DSDLA_df, on="Subject", how="left")
            if uses_dsca:
                # inset the "Dose Level Assignment" column after the "Cohort" column
                cohort_index = output_df.columns.get_loc("Cohort")
                output_df.insert(
                    cohort_index + 1,
                    "Dose Level Assignment",
                    output_df.pop("Dose Level Assignment"),
                )
            else:
                # inset the "Dose Level Assignment" column after the "Subject" column
                subject_index = output_df.columns.get_loc("Subject")
                output_df.insert(
                    subject_index + 1,
                    "Dose Level Assignment",
                    output_df.pop("Dose Level Assignment"),
                )
            # get data from EXINF
            EXINF_DLA_header_list = self.get_EXINF_DLA_header_list(self.study_name)
            EXINF_DLA_df = data[EXINF_key][EXINF_DLA_header_list]
            # Filter the EXINF_DLA_df to only include rows where the second column is "Day 0"
            EXINF_DLA_df = EXINF_DLA_df[
                EXINF_DLA_df[EXINF_DLA_header_list[1]] == "Day 0"
            ]
            # Remove the second column (Event Group Label) from EXINF_DLA_df
            EXINF_DLA_df = EXINF_DLA_df.drop(columns=[EXINF_DLA_header_list[1]])
            # get the dose level mapping
            dose_level_mapping = self.get_dose_level_mapping(self.study_name)
            # The dose level as treated, from the dose and its power of ten.
            EXINF_DLA_df["Dose Level As Treated"] = EXINF_DLA_df.apply(
                lambda row: self.get_dose_level(
                    row[EXINF_DLA_header_list[2]],
                    row[EXINF_DLA_header_list[3]],
                    dose_level_mapping,
                ),
                axis=1,
            )
            # remove the second and third columns
            EXINF_DLA_df = EXINF_DLA_df.drop(
                columns=[EXINF_DLA_header_list[2], EXINF_DLA_header_list[3]]
            )
            # merge
            output_df = output_df.merge(EXINF_DLA_df, on="Subject", how="left")
            # insert the "Dose Level As Treated" column after the "Dose Level Assignment" column
            dla_index = output_df.columns.get_loc(
                "Dose Level Assignment"
            )  # Get the index of the "Dose Level Assignment" column
            output_df.insert(
                dla_index + 1,
                "Dose Level As Treated",
                output_df.pop("Dose Level As Treated"),
            )

        # Initialize an empty list to hold the dataframes
        infusion_dfs = []
        # Define the infusion details in a list
        infusion_details = self.get_infusion_details(self.study_name)

        # Loop through each infusion detail
        for infusion_num, study_day in enumerate(infusion_details):
            # Get the data from EXINF for columns listed in the header list
            EXINF_header_list = self.get_EXINF_header_list(self.study_name)
            infusion_df = data[EXINF_key][EXINF_header_list]
            # Rename the second column of EXINF to "Infusion Date"
            infusion_df = infusion_df.rename(
                columns={infusion_df.columns[1]: f"Infusion Date #{infusion_num + 1}"}
            )
            # Rename the third column of EXINF to "Study Day"
            infusion_df = infusion_df.rename(
                columns={infusion_df.columns[2]: "Study Day"}
            )
            # Filter to the specific infusion
            infusion_df = infusion_df[infusion_df["Study Day"] == study_day]
            # Remove the "Study Day" column
            infusion_df = infusion_df.drop(columns=["Study Day"])
            # Append the prepared dataframe to the list
            infusion_dfs.append(infusion_df)

        # Merge the 3 infusion dataframes together based on the "Subject" column
        EXINF_df = infusion_dfs[0]
        for df in infusion_dfs[1:]:
            EXINF_df = EXINF_df.merge(df, on="Subject", how="left")

        output_df = output_df.merge(EXINF_df, on="Subject", how="left")
        # new empty column for in "Infusion Date"
        output_df["Infusion Date"] = pd.NaT
        output_df["Infusion Date"] = pd.to_datetime(
            output_df["Infusion Date"], errors="coerce"
        )
        # select the Infusion Date that is the last infusion prior to the Start Date
        for i in range(1, len(infusion_details) + 1):
            # convert 3 infusion dates to datetime
            output_df[f"Infusion Date #{i}"] = pd.to_datetime(
                output_df[f"Infusion Date #{i}"], errors="coerce"
            )
            output_df["Infusion Date"] = output_df["Infusion Date"].mask(
                (output_df["Start Date"] >= output_df[f"Infusion Date #{i}"])
                & (output_df[f"Infusion Date #{i}"] != pd.NaT),
                output_df[f"Infusion Date #{i}"],
            )
        # Insert the "Infusion Date" column after the "Duration" column
        duration_index = output_df.columns.get_loc(
            "Duration"
        )  # Get the index of the "Stop Date" column
        output_df.insert(
            duration_index + 1, "Infusion Date", output_df.pop("Infusion Date")
        )
        # column "Onset Post Infusion" is the difference between "Start Date" and "Infusion Date"
        output_df["Onset Post Infusion"] = (
            output_df["Start Date"] - output_df["Infusion Date"]
        ).dt.days.fillna("N/A")
        # inset the "Onset Post Infusion" column after the "Infusion Date" column
        output_df.insert(
            duration_index + 2,
            "Onset Post Infusion",
            output_df.pop("Onset Post Infusion"),
        )
        # calculate D+28 based on the first infusion date
        output_df["D+28"] = output_df["Infusion Date #1"] + pd.Timedelta(days=28)
        # insert the "D+28" column after the "Infusion Date" column
        output_df.insert(duration_index + 3, "D+28", output_df.pop("D+28"))
        # "DLT Duration" (see compute_dlt_duration) follows these rules:
        # -if start date before infusion = N/A
        # -if start date after D+28 = N/A
        # -if no stop date, then duration of [D+28 - start date] + 1
        # -if stop date, then:
        #     -if stop date <D+28, then [stop date - start date] + 1
        #     -else [D+28 - start date] + 1
        # Apply the function to each row
        output_df["DLT Duration"] = output_df.apply(self.compute_dlt_duration, axis=1)
        # insert the "DLT Duration" column after the "D+28" column
        d28_index = output_df.columns.get_loc(
            "D+28"
        )  # Get the index of the "D+28" column
        output_df.insert(d28_index + 1, "DLT Duration", output_df.pop("DLT Duration"))

        # convert the "Infusion Date" rows that have data not "N/A"
        output_df["Infusion Date"] = output_df["Infusion Date"].fillna("N/A")
        output_df["Stop Date"] = output_df["Stop Date"].fillna("Pending")
        # output_df["Start Date"] = output_df["Start Date"].dt.date
        output_df["D+28"] = output_df["D+28"].fillna("N/A")
        # drop the "Infusion Date" columns
        output_df = output_df.drop(
            columns=[f"Infusion Date #{i}" for i in range(1, len(infusion_details) + 1)]
        )
        # sort the columns based on Subject, Start Date
        output_df = output_df.sort_values(by=["Subject", "Start Date"])

        # fill Duration with "pending" where Stop Date is blank
        output_df["Duration"] = output_df["Duration"].mask(
            output_df["Stop Date"] == "Pending", "Pending"
        )
        # fill DLT Duration with "pending" if it is blank
        output_df["DLT Duration"] = output_df["DLT Duration"].fillna("Pending")
        if uses_dsca:
            # fill Cohort with "pending" if it is blank
            output_df["Cohort"] = output_df["Cohort"].fillna("Pending")
        if uses_dsdla:
            # fill Dose Level Assignment with "pending" if it is blank
            output_df["Dose Level Assignment"] = output_df[
                "Dose Level Assignment"
            ].fillna("Pending")
            # fill Dose Level As Treated with "pending" if it is blank
            output_df["Dose Level As Treated"] = output_df[
                "Dose Level As Treated"
            ].fillna("Pending")
        # Remove all columns with column name ends with "_RAW"
        output_df = output_df.loc[:, ~output_df.columns.str.endswith("_RAW")]
        # Remove duplicate rows
        output_df = output_df.drop_duplicates()
        return output_df

    def output(self, output_df, target):
        """Write the workbook to *target* (a path or a binary file)."""
        # get the keys based on the study name
        AE_key, DSDLA_key, DSCA_key, EXINF_key = _form_keys(self.key_map)

        # Create an Excel writer object using xlsxwriter engine
        with pd.ExcelWriter(target, engine="xlsxwriter") as writer:
            date_format = writer.book.add_format(
                {
                    "num_format": "mm/dd/yyyy",
                    "align": "center",
                    "valign": "vcenter",
                    "border": 1,
                    "font_name": "Calibri",
                    "font_size": 11,
                }
            )
            blue_date_format = writer.book.add_format(
                {
                    "num_format": "mm/dd/yyyy",
                    "align": "center",
                    "valign": "vcenter",
                    "border": 1,
                    "font_name": "Calibri",
                    "font_size": 11,
                    "font_color": "blue",
                }
            )
            formats = get_named_excel_formats(writer.book)
            normal_data_format = formats["normal_data_format"]
            bold_12_format = formats["bold_12_format"]
            blue_normal_data_format = writer.book.add_format(
                {
                    "bg_color": "#FFFFFF",
                    "text_wrap": False,
                    "valign": "vcenter",
                    "align": "center",
                    "bold": False,
                    "font_name": "Calibri",
                    "font_size": 11,
                    "border": 1,
                    "font_color": "blue",
                }
            )
            blue_bold_12_format = writer.book.add_format(
                {
                    "bg_color": "#FFFFFF",
                    "text_wrap": True,
                    "valign": "vcenter",
                    "align": "center",
                    "bold": True,
                    "font_name": "Calibri",
                    "font_size": 12,
                    "border": 1,
                    "font_color": "blue",
                }
            )

            writer.book.add_worksheet("Reformated AE Report")
            writer.book.add_worksheet(AE_key + " Corelisting")
            if DSDLA_key in self.data.keys():
                writer.book.add_worksheet(DSDLA_key + " Corelisting")
            if DSCA_key in self.data.keys():
                writer.book.add_worksheet(DSCA_key + " Corelisting")
            writer.book.add_worksheet(EXINF_key + " Corelisting")

            # Apply the format to each worksheet
            for worksheet_name in writer.sheets:
                ws = writer.sheets[worksheet_name]

                # Determine the number of columns and rows for the current worksheet
                if worksheet_name.startswith("Reformated AE Report"):
                    df = self.output_df
                elif worksheet_name == AE_key + " Corelisting":
                    df = self.data[AE_key]
                elif worksheet_name == DSCA_key + " Corelisting":
                    df = self.data[DSCA_key]
                elif worksheet_name == EXINF_key + " Corelisting":
                    df = self.data[EXINF_key]
                elif worksheet_name == DSDLA_key + " Corelisting":
                    df = self.data[DSDLA_key]

                # Replace NaN and Inf values with an empty string
                df = df.replace([np.nan, pd.NaT, float("inf"), float("-inf")], "")

                num_cols = len(df.columns)
                num_rows = len(df)

                # Autofit column widths
                for col_num, col in enumerate(df.columns):
                    max_len = (
                        max(
                            df[col].astype(str).map(len).max(),
                            len(str(col)),
                        )
                        + 2
                    )  # Add some extra space for padding
                    ws.set_column(col_num, col_num, max_len)  # Set the column width

                # update column names of Infusion Date, Onset Post Infusion, D+28, DLT duration
                updated_columns = {
                    "Infusion Date": "Infusion Date \n(last infusion prior to the event start date)",
                    "Onset Post Infusion": "Onset Post Infusion \n(related to last infusion)",
                    "D+28": "D+28 \n(based on FIRST infusion)",
                    "DLT Duration": "DLT Duration\n(if DLT, using FIRST infusion)",
                }
                df = df.rename(columns=updated_columns)

                blue_columns = [
                    "Cohort",
                    "Duration",
                    "Infusion Date \n(last infusion prior to the event start date)",
                    "D+28 \n(based on FIRST infusion)",
                    "DLT Duration\n(if DLT, using FIRST infusion)",
                    "Onset Post Infusion \n(related to last infusion)",
                    "Derived Toxicity",
                ]
                if DSDLA_key in self.data.keys():
                    # add Dose Level Assignment to blue_columns
                    blue_columns.append("Dose Level Assignment")
                    blue_columns.append("Dose Level As Treated")

                # Define date columns
                date_columns = [
                    "Start Date",
                    "Stop Date",
                    "Infusion Date \n(last infusion prior to the event start date)",
                    "D+28 \n(based on FIRST infusion)",
                ]  # Add other date columns if needed

                # Apply format to each cell in the DataFrame range
                for row in range(1, num_rows + 1):  # Start from row 1 to skip header
                    for col in range(num_cols):
                        cell_value = df.iloc[row - 1, col]
                        col_name = df.columns[col]

                        # Choose the appropriate cell format
                        if col_name in blue_columns:
                            cell_format = blue_normal_data_format
                        else:
                            cell_format = normal_data_format

                        # Apply date format if the column is a date column
                        if col_name in date_columns:
                            if col_name in blue_columns:
                                # add blue to the date format
                                cell_format = blue_date_format
                            else:
                                cell_format = date_format

                            if isinstance(cell_value, pd.Timestamp) and not pd.isnull(
                                cell_value
                            ):
                                ws.write_datetime(
                                    row, col, cell_value.to_pydatetime(), cell_format
                                )
                            elif isinstance(
                                cell_value, datetime.datetime
                            ) and not pd.isnull(cell_value):
                                ws.write_datetime(row, col, cell_value, cell_format)
                            elif isinstance(cell_value, str):
                                ws.write(row, col, cell_value, cell_format)
                            else:
                                ws.write_blank(row, col, None, cell_format)
                        else:
                            ws.write(row, col, cell_value, cell_format)

                for col_num, value in enumerate(df.columns.values):
                    if df.columns[col_num] in blue_columns:
                        ws.write(0, col_num, value, blue_bold_12_format)
                    else:
                        ws.write(
                            0, col_num, value, bold_12_format
                        )  # Apply format to the header row

                ws.autofit()
