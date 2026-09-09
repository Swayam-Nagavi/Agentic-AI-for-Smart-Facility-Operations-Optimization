def calculate_health_score(condition_risk):
    """
    Convert current equipment-condition risk into
    a 0-100 health score.

    Higher risk means lower health.
    """

    return round(
        max(
            0.0,
            min(
                100.0,
                100.0 - float(condition_risk),
            ),
        ),
        1,
    )


def health_category(score):
    """
    Categorize the current equipment health.
    """

    score = float(score)

    if score >= 75:
        return "Excellent"

    if score >= 60:
        return "Good"

    if score >= 40:
        return "Warning"

    return "Critical"


def maintenance_priority(score):
    """
    Determine maintenance priority from the
    current equipment health score.
    """

    score = float(score)

    if score < 40:
        return "Critical"

    if score < 60:
        return "High"

    if score < 75:
        return "Medium"

    return "Low"


def health_basis():
    """
    Explain how the health score is calculated.
    """

    return (
        "Health score is derived from the current "
        "temperature, humidity, HVAC operating condition, "
        "equipment status, and energy readings in the "
        "facility data."
    )