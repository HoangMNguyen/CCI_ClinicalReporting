from clinical_reporting.data import parse_study_name


def get_dose_level(dose, power, dose_level_mapping):
    """
    Helper function to compute dose level administered.

    Returns:
    str: The correct Dose Level (e.g., DL1, DL2, etc.) or 'Not Matching' if no match found.
    """
    # Calculate the actual dose administered
    actual_dose = dose * (10**power)

    # Determine the correct dose level based on the mapping provided
    for dose_level, (p_dose, p_power) in dose_level_mapping.items():
        if actual_dose == p_dose * (10**p_power):
            return dose_level

    # if no match found, return 'Not Matching'
    return "Not Matching"


def get_study_name(input_dir) -> str:
    """
    Extracts the five-digit study name from the Corelisting file path.

    Delegates the filename parsing to clinical_reporting.data.parse_study_name
    and keeps this tool's digit validation on top of it.

    Returns:
        str: The study name if it is a digit; otherwise, None.
    """
    study_name: str = parse_study_name(input_dir)[0:5]

    # Check if the extracted study name is a digit
    if not study_name.isdigit():
        return None
    else:
        return study_name
