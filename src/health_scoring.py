"""
Health Scoring
--------------
Equipment health score calculation, categorisation,
maintenance priority, and condition-risk assessment.

This module is the single source of truth for the
condition-risk formula used by both the Maintenance Agent
and the future-condition training pipeline.
"""


# ============================================================
# CONDITION RISK
# ============================================================

def calculate_condition_risk(row):
    """
    Calculate a 0-100 condition-risk score for a single
    sensor observation.

    Higher risk indicates worse operating conditions.

    Parameters
    ----------
    row : dict-like
        A single observation containing at minimum:
        temperature, humidity, occupancy, energy_consumption,
        hvac_energy, hvac_status, hvac_setpoint, equipment_status.

    Returns
    -------
    float
        Risk score between 0.0 and 100.0.
    """

    risk = 0.0

    temperature = float(row["temperature"])
    humidity = float(row["humidity"])
    occupancy = float(row["occupancy"])
    energy = float(row["energy_consumption"])
    hvac_energy = float(row["hvac_energy"])
    hvac_status = str(row["hvac_status"]).upper()
    setpoint = float(row["hvac_setpoint"])
    equipment_status = str(row["equipment_status"]).lower()

    # Temperature deviation from setpoint.
    temperature_deviation = abs(temperature - setpoint)

    if temperature_deviation > 3:
        risk += 35
    elif temperature_deviation > 2:
        risk += 20
    elif temperature_deviation > 1:
        risk += 10

    # Humidity outside comfort band.
    if humidity > 65 or humidity < 35:
        risk += 25
    elif humidity > 60 or humidity < 40:
        risk += 10

    # Equipment fault / warning.
    if equipment_status == "fault":
        risk += 50
    elif equipment_status == "warning":
        risk += 30

    # HVAC running with occupancy but zero energy (sensor error).
    if (
        hvac_status == "ON"
        and occupancy > 0
        and hvac_energy <= 0
    ):
        risk += 25

    # High total energy consumption.
    if energy > 1.30:
        risk += 20
    elif energy > 1.10:
        risk += 10

    return round(
        max(0.0, min(100.0, risk)),
        1,
    )


# ============================================================
# HEALTH SCORE
# ============================================================

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


# ============================================================
# HEALTH CATEGORY
# ============================================================

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


# ============================================================
# MAINTENANCE PRIORITY
# ============================================================

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


# ============================================================
# HEALTH BASIS
# ============================================================

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