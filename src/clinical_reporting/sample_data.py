"""Made-up study data (DEMO01) for previews, screenshots and tests.

Nothing here comes from a real study: subjects, visits, and values are
generated from a fixed seed, so previews look the same every time and can be
shared without exposing trial data.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Dict, List

import pandas as pd

from clinical_reporting.models import JoinHow
from clinical_reporting.report import CLReport

STUDY = "DEMO01"
_VISITS = ["Screening", "C1D1", "C1D8", "C2D1", "C3D1", "End of treatment"]
_SITES = ["01", "02", "03"]


def _subjects(count: int) -> List[str]:
    return [f"{_SITES[i % len(_SITES)]}-{100 + i:03d}" for i in range(count)]


def sample_forms(subjects: int = 24, seed: int = 7) -> Dict[str, pd.DataFrame]:
    """DEMO01's forms as ``{form: DataFrame}``, like a read Corelisting ZIP."""
    rng = random.Random(seed)
    ids = _subjects(subjects)
    start = date(2026, 1, 5)

    def site(subject: str) -> str:
        return subject.split("-")[0]

    dm = pd.DataFrame(
        {
            "Subject": ids,
            "Site": [site(s) for s in ids],
            "Visit": "Screening",
            "Age": [rng.randint(24, 81) for _ in ids],
            "Sex": [rng.choice(["F", "M"]) for _ in ids],
            "Race": [rng.choice(["White", "Black", "Asian", "Other"]) for _ in ids],
            "Consent Date": [start + timedelta(days=rng.randint(0, 60)) for _ in ids],
        }
    )
    visit_rows = [(s, v) for s in ids for v in _VISITS[:4]]
    vs = pd.DataFrame(
        {
            "Subject": [s for s, _ in visit_rows],
            "Site": [site(s) for s, _ in visit_rows],
            "Visit": [v for _, v in visit_rows],
            "Systolic BP": [rng.randint(100, 160) for _ in visit_rows],
            "Diastolic BP": [rng.randint(60, 100) for _ in visit_rows],
            "Pulse": [rng.randint(55, 105) for _ in visit_rows],
            "Weight": [round(rng.uniform(48, 110), 1) for _ in visit_rows],
        }
    )
    terms = ["Nausea", "Fatigue", "Headache", "Rash", "Anemia", "Diarrhea"]
    ae_rows = [
        (s, rng.choice(_VISITS[1:4])) for s in ids for _ in range(rng.randint(0, 3))
    ]
    ae_starts = [start + timedelta(days=rng.randint(20, 120)) for _ in ae_rows]
    ae = pd.DataFrame(
        {
            "Subject": [s for s, _ in ae_rows],
            "Site": [site(s) for s, _ in ae_rows],
            "Visit": [v for _, v in ae_rows],
            "AE Term": [rng.choice(terms) for _ in ae_rows],
            "Grade": [rng.randint(1, 4) for _ in ae_rows],
            "Serious": [rng.choice(["No", "No", "No", "Yes"]) for _ in ae_rows],
            "Start Date": ae_starts,
            "End Date": [d + timedelta(days=rng.randint(1, 30)) for d in ae_starts],
        }
    )
    lb = pd.DataFrame(
        {
            "Subject": [s for s, _ in visit_rows],
            "Site": [site(s) for s, _ in visit_rows],
            "Visit": [v for _, v in visit_rows],
            "Lab Test": [
                rng.choice(["Hemoglobin", "ALT", "Creatinine"]) for _ in visit_rows
            ],
            "Result": [round(rng.uniform(0.5, 15), 1) for _ in visit_rows],
            "Unit": [rng.choice(["g/dL", "U/L", "mg/dL"]) for _ in visit_rows],
        }
    )
    simple = {
        "CM": ("Medication", ["Ondansetron", "Ibuprofen", "Omeprazole"]),
        "EX": ("Dose", ["100 mg", "200 mg"]),
        "EOT": ("Reason", ["Completed", "Progression", "Withdrew consent"]),
        "DS": ("Status", ["Ongoing", "Completed", "Discontinued"]),
    }
    forms = {"DM": dm, "VS": vs, "AE": ae, "LB": lb}
    for form, (column, values) in simple.items():
        forms[form] = pd.DataFrame(
            {
                "Subject": ids,
                "Site": [site(s) for s in ids],
                "Visit": rng.choice(_VISITS),
                column: [rng.choice(values) for _ in ids],
            }
        )
    return forms


def configure_sample_report(report: CLReport) -> None:
    """Pick forms, items, joins, a filter, and a comparison, as a user would.

    *report* must already hold :func:`sample_forms`.
    """
    for form in ("DM", "AE", "VS"):
        report.add_selected_form(form)
    report.set_common_item_state("Subject", selected=True)
    report.set_common_item_state("Site", selected=True)
    for form, items in {
        "DM": ["Age", "Sex"],
        "AE": ["AE Term", "Grade", "Start Date", "End Date"],
        "VS": ["Pulse", "Weight"],
    }.items():
        for item in items:
            report.selected_forms[form].set_form_item_state(item, selected=True)
    report.update_join_items("DM", [], 1, JoinHow.LEFT)
    report.update_join_items("AE", ["Subject", "Site"], 2, JoinHow.LEFT)
    report.update_join_items("VS", ["Subject", "Site"], 3, JoinHow.LEFT)
    report.add_static_filter_item("DM.Age", ">=", "18")
    report.add_dynamic_filter_item("AE.End Date", ">=", "AE.Start Date")
    report.set_rename_item("DM.Age", "Age (years)")


__all__ = ["STUDY", "configure_sample_report", "sample_forms"]
