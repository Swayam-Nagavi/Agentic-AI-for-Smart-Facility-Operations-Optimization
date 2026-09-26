"""
Milestone 4 — Executive Cost Optimization Agent

Builds the executive financial view from the outputs of the
Energy, Maintenance, Occupancy, Security and Operations agents.

Important:
- Financial values are calculated from current agent outputs.
- Internal rates and planning factors are kept inside this file.
- These internal calculation assumptions are NOT returned to the dashboard.
"""

# ============================================================
# INTERNAL FINANCIAL PARAMETERS
# ============================================================
# These are calculation parameters only.
# They are intentionally NOT exposed through the API/dashboard.

ELECTRICITY_TARIFF_INR_PER_KWH = 8.0

MONTHLY_DAYS = 30.0

# Internal operating-cost factors
MAINTENANCE_COST_PER_ASSET_INR = 12000.0
MAINTENANCE_FAULT_COST_INR = 18000.0
MAINTENANCE_HIGH_RISK_COST_INR = 7000.0

SECURITY_COST_PER_EVENT_INR = 250.0
SECURITY_ALERT_COST_INR = 2500.0
SECURITY_CRITICAL_ALERT_COST_INR = 5000.0

# Administration is calculated from direct operating costs.
ADMINISTRATIVE_COST_RATIO = 0.17

# Savings factors
MAINTENANCE_SAVING_RATE = 0.20
OCCUPANCY_SAVING_RATE = 0.08
SECURITY_SAVING_RATE = 0.15

# Maximum savings limits prevent unrealistic results
MAX_TOTAL_SAVINGS_RATIO = 0.30

# Implementation cost is derived from the size of the facility
IMPLEMENTATION_BASE_COST_INR = 500000.0
IMPLEMENTATION_COST_PER_ASSET_INR = 25000.0


# ============================================================
# HELPERS
# ============================================================

def _number(value, default=0.0):
    try:
        if value is None:
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def _integer(value, default=0):
    try:
        return int(float(value or 0))

    except (TypeError, ValueError):
        return default


def _percentage(value, default=0.0):
    value = _number(value, default)

    return max(
        0.0,
        min(100.0, value),
    )


def _priority_rank(priority):
    return {
        "Critical": 4,
        "High": 3,
        "Medium": 2,
        "Low": 1,
        "Info": 0,
    }.get(
        str(priority),
        0,
    )


def _monitoring_days(energy):
    """
    Estimate the duration covered by the current energy dataset.

    Uses the Energy Agent metadata rather than assuming that the
    generated sensor dataset already represents a full month.
    """

    metadata = energy.get(
        "metadata",
        {},
    )

    start = metadata.get(
        "start_timestamp"
    )

    end = metadata.get(
        "end_timestamp"
    )

    if not start or not end:
        return 1.0

    try:
        from datetime import datetime

        start_dt = datetime.fromisoformat(
            str(start)
        )

        end_dt = datetime.fromisoformat(
            str(end)
        )

        seconds = (
            end_dt - start_dt
        ).total_seconds()

        days = seconds / 86400.0

        return max(
            1.0,
            days,
        )

    except (TypeError, ValueError):
        return 1.0


def _monthly_factor(energy):
    """
    Convert the current monitoring period into an approximate
    30-day operating baseline.
    """

    days = _monitoring_days(
        energy
    )

    return MONTHLY_DAYS / days


# ============================================================
# FINANCIAL CALCULATIONS
# ============================================================

def _calculate_energy_financials(energy):
    """
    Calculate monthly energy cost and energy savings from
    the actual Energy Agent output.
    """

    kpis = energy.get(
        "kpis",
        {},
    )

    monitoring_days = _monitoring_days(
        energy
    )

    monthly_factor = (
        MONTHLY_DAYS / monitoring_days
    )

    actual_energy_cost = _number(
        kpis.get(
            "estimated_cost"
        )
    )

    actual_energy_savings = _number(
        kpis.get(
            "potential_cost_savings"
        )
    )

    monthly_energy_cost = (
        actual_energy_cost
        * monthly_factor
    )

    monthly_energy_savings = (
        actual_energy_savings
        * monthly_factor
    )

    return {
        "monthly_cost": round(
            monthly_energy_cost,
            2,
        ),
        "monthly_savings": round(
            monthly_energy_savings,
            2,
        ),
    }


def _calculate_maintenance_financials(
    maintenance
):
    """
    Calculate maintenance operating cost from the current
    maintenance-agent asset and fault information.
    """

    kpis = maintenance.get(
        "kpis",
        {},
    )

    assets = _integer(
        kpis.get(
            "assets_monitored"
        )
    )

    faults = _integer(
        kpis.get(
            "faults_detected"
        )
    )

    high_risk = _integer(
        kpis.get(
            "high_risk_assets"
        )
    )

    deteriorating = _integer(
        kpis.get(
            "deteriorating_assets"
        )
    )

    base_cost = (
        assets
        * MAINTENANCE_COST_PER_ASSET_INR
    )

    fault_cost = (
        faults
        * MAINTENANCE_FAULT_COST_INR
    )

    risk_cost = (
        high_risk
        * MAINTENANCE_HIGH_RISK_COST_INR
    )

    monthly_cost = (
        base_cost
        + fault_cost
        + risk_cost
    )

    # Preventive maintenance savings are based on
    # the active maintenance risk signals.
    risk_signals = (
        faults
        + high_risk
        + deteriorating
    )

    potential_savings = (
        monthly_cost
        * MAINTENANCE_SAVING_RATE
    )

    # No risk signals -> no additional optimization opportunity.
    if risk_signals <= 0:
        potential_savings = 0.0

    return {
        "monthly_cost": round(
            monthly_cost,
            2,
        ),
        "monthly_savings": round(
            potential_savings,
            2,
        ),
        "assets": assets,
        "faults": faults,
        "high_risk": high_risk,
        "deteriorating": deteriorating,
    }


def _calculate_occupancy_financials(
    occupancy,
    monthly_non_energy_cost
):
    """
    Calculate an occupancy-driven optimization opportunity.

    Occupancy itself is not treated as a monetary expense.
    Instead, room utilization signals are converted into a
    potential operational saving against non-energy operating cost.
    """

    kpis = occupancy.get(
        "kpis",
        {},
    )

    capacity_alerts = occupancy.get(
        "capacity_alerts",
        [],
    )

    occupancy_rate = _percentage(
        kpis.get(
            "occupancy_rate"
        )
    )

    occupied_rooms = _integer(
        kpis.get(
            "occupied_rooms"
        )
    )

    total_rooms = _integer(
        kpis.get(
            "total_rooms"
        )
    )

    alert_count = len(
        capacity_alerts
    )

    # Stronger optimization opportunity when there are
    # capacity/utilization signals.
    utilization_signal = (
        alert_count * 0.03
    )

    if total_rooms > 0:
        utilization_signal += (
            occupied_rooms
            / total_rooms
            * 0.03
        )

    utilization_signal = min(
        utilization_signal,
        OCCUPANCY_SAVING_RATE,
    )

    # If occupancy information is unavailable,
    # don't invent a financial saving.
    if (
        total_rooms <= 0
        or occupancy_rate <= 0
    ):
        utilization_signal = 0.0

    monthly_savings = (
        monthly_non_energy_cost
        * utilization_signal
    )

    return {
        "monthly_savings": round(
            monthly_savings,
            2,
        ),
        "occupancy_rate": round(
            occupancy_rate,
            2,
        ),
        "capacity_alerts": alert_count,
    }


def _calculate_security_financials(
    security
):
    """
    Calculate security operating cost from actual security
    event and alert counts.
    """

    kpis = security.get(
        "kpis",
        {},
    )

    total_events = _integer(
        kpis.get(
            "total_events"
        )
    )

    active_alerts = _integer(
        kpis.get(
            "active_alerts"
        )
    )

    critical_alerts = _integer(
        kpis.get(
            "critical_alerts"
        )
    )

    event_cost = (
        total_events
        * SECURITY_COST_PER_EVENT_INR
    )

    alert_cost = (
        active_alerts
        * SECURITY_ALERT_COST_INR
    )

    critical_cost = (
        critical_alerts
        * SECURITY_CRITICAL_ALERT_COST_INR
    )

    monthly_cost = (
        event_cost
        + alert_cost
        + critical_cost
    )

    monthly_savings = (
        monthly_cost
        * SECURITY_SAVING_RATE
        if active_alerts > 0
        or critical_alerts > 0
        else 0.0
    )

    return {
        "monthly_cost": round(
            monthly_cost,
            2,
        ),
        "monthly_savings": round(
            monthly_savings,
            2,
        ),
        "total_events": total_events,
        "active_alerts": active_alerts,
        "critical_alerts": critical_alerts,
    }


# ============================================================
# COST DISTRIBUTION
# ============================================================

def _build_cost_distribution(
    energy_cost,
    maintenance_cost,
    security_cost,
):
    """
    Build cost distribution from calculated domain costs.

    Administration is derived from the direct operating costs.
    """

    direct_cost = (
        energy_cost
        + maintenance_cost
        + security_cost
    )

    administration_cost = (
        direct_cost
        * ADMINISTRATIVE_COST_RATIO
    )

    total_cost = (
        direct_cost
        + administration_cost
    )

    if total_cost <= 0:
        return []

    categories = [
        (
            "Energy",
            energy_cost,
        ),
        (
            "Maintenance",
            maintenance_cost,
        ),
        (
            "Security",
            security_cost,
        ),
        (
            "Administration",
            administration_cost,
        ),
    ]

    distribution = []

    for category, cost in categories:

        percentage = (
            cost
            / total_cost
            * 100
        )

        distribution.append(
            {
                "category": category,
                "percentage": round(
                    percentage,
                    2,
                ),
                "cost": round(
                    cost,
                    2,
                ),
            }
        )

    return distribution


# ============================================================
# COST RECOMMENDATIONS
# ============================================================

def _build_cost_recommendations(
    energy,
    maintenance,
    occupancy,
    security,
    financials,
):
    recommendations = []

    energy_kpis = energy.get(
        "kpis",
        {},
    )

    energy_anomalies = _integer(
        energy_kpis.get(
            "anomalies"
        )
    )

    energy_savings = financials[
        "energy"
    ]["monthly_savings"]

    if energy_anomalies > 0:

        recommendations.append(
            {
                "priority": "High",
                "domain": "Energy",
                "title": "Optimize abnormal energy consumption",
                "reason": (
                    f"{energy_anomalies} energy "
                    "anomaly signal(s) were detected. "
                    "Coordinate HVAC and equipment "
                    "loads with facility operations."
                ),
                "estimated_savings": round(
                    energy_savings,
                    2,
                ),
            }
        )

    elif energy_savings > 0:

        recommendations.append(
            {
                "priority": "Medium",
                "domain": "Energy",
                "title": "Optimize HVAC operating schedules",
                "reason": (
                    "The Energy Agent identified "
                    "avoidable energy consumption "
                    "within the monitored facility data."
                ),
                "estimated_savings": round(
                    energy_savings,
                    2,
                ),
            }
        )

    # --------------------------------------------------------
    # OCCUPANCY
    # --------------------------------------------------------

    occupancy_financials = financials[
        "occupancy"
    ]

    capacity_alerts = occupancy_financials[
        "capacity_alerts"
    ]

    occupancy_savings = occupancy_financials[
        "monthly_savings"
    ]

    if capacity_alerts > 0:

        recommendations.append(
            {
                "priority": "High",
                "domain": "Occupancy",
                "title": "Rebalance high-utilization rooms",
                "reason": (
                    f"{capacity_alerts} room(s) generated "
                    "capacity alerts. Coordinate room "
                    "allocation and facility operation schedules."
                ),
                "estimated_savings": round(
                    occupancy_savings,
                    2,
                ),
            }
        )

    elif occupancy_savings > 0:

        recommendations.append(
            {
                "priority": "Medium",
                "domain": "Occupancy",
                "title": "Use occupancy-aware scheduling",
                "reason": (
                    "Current occupancy patterns provide "
                    "an opportunity to coordinate room "
                    "utilization with facility operations."
                ),
                "estimated_savings": round(
                    occupancy_savings,
                    2,
                ),
            }
        )

    # --------------------------------------------------------
    # MAINTENANCE
    # --------------------------------------------------------

    maintenance_financials = financials[
        "maintenance"
    ]

    faults = maintenance_financials[
        "faults"
    ]

    maintenance_savings = maintenance_financials[
        "monthly_savings"
    ]

    if faults > 0:

        recommendations.append(
            {
                "priority": "Critical",
                "domain": "Maintenance",
                "title": "Prioritize equipment fault resolution",
                "reason": (
                    f"{faults} equipment fault "
                    "signal(s) were detected. "
                    "Resolve these before applying "
                    "aggressive optimization."
                ),
                "estimated_savings": round(
                    maintenance_savings,
                    2,
                ),
            }
        )

    elif maintenance_savings > 0:

        recommendations.append(
            {
                "priority": "Medium",
                "domain": "Maintenance",
                "title": "Increase preventive maintenance",
                "reason": (
                    "Current equipment health signals "
                    "indicate an opportunity to reduce "
                    "future corrective-maintenance costs."
                ),
                "estimated_savings": round(
                    maintenance_savings,
                    2,
                ),
            }
        )

    # --------------------------------------------------------
    # SECURITY
    # --------------------------------------------------------

    security_financials = financials[
        "security"
    ]

    active_alerts = security_financials[
        "active_alerts"
    ]

    critical_alerts = security_financials[
        "critical_alerts"
    ]

    security_savings = security_financials[
        "monthly_savings"
    ]

    if critical_alerts > 0:

        priority = "Critical"

    elif active_alerts > 0:

        priority = "High"

    else:

        priority = "Low"

    if (
        active_alerts > 0
        or critical_alerts > 0
    ):

        recommendations.append(
            {
                "priority": priority,
                "domain": "Security",
                "title": "Coordinate security response coverage",
                "reason": (
                    f"{active_alerts} active security "
                    f"alert(s) and {critical_alerts} "
                    "critical alert(s) were detected."
                ),
                "estimated_savings": round(
                    security_savings,
                    2,
                ),
            }
        )

    recommendations.sort(
        key=lambda item: (
            _priority_rank(
                item["priority"]
            ),
            item["estimated_savings"],
        ),
        reverse=True,
    )

    return recommendations[:8]


# ============================================================
# EXECUTIVE FEATURES
# ============================================================

def _build_executive_features(
    energy,
    maintenance,
    occupancy,
    security,
    operations,
):

    features = [
        "Multi-agent facility monitoring",
        "Cross-agent operational decision making",
        "Energy consumption optimization",
        "Predictive maintenance coordination",
        "Occupancy-aware HVAC optimization",
        "Security-aware operational planning",
        "Automated action prioritization",
        "Facility-level cost optimization",
    ]

    energy_kpis = energy.get(
        "kpis",
        {}
    )

    maintenance_kpis = maintenance.get(
        "kpis",
        {}
    )

    occupancy_kpis = occupancy.get(
        "kpis",
        {}
    )

    security_kpis = security.get(
        "kpis",
        {}
    )

    if _number(
        energy_kpis.get(
            "anomalies"
        )
    ) > 0:

        features.append(
            "Energy anomaly detection is active"
        )

    if _number(
        maintenance_kpis.get(
            "faults_detected"
        )
    ) > 0:

        features.append(
            "Maintenance fault monitoring is active"
        )

    if _number(
        occupancy_kpis.get(
            "current_occupancy"
        )
    ) > 0:

        features.append(
            "Occupancy-aware facility control is active"
        )

    if _number(
        security_kpis.get(
            "active_alerts"
        )
    ) > 0:

        features.append(
            "Security event coordination is active"
        )

    return features[:12]


# ============================================================
# ROI CALCULATION
# ============================================================

def _build_roi(
    implementation_cost,
    annual_savings,
):
    """
    Calculate ROI and payback from the calculated
    annual savings and derived implementation cost.
    """

    if implementation_cost <= 0:

        roi_percent = 0.0
        payback_months = 0.0

    else:

        roi_percent = (
            (
                annual_savings
                - implementation_cost
            )
            / implementation_cost
            * 100
        )

        monthly_savings = (
            annual_savings / 12.0
        )

        payback_months = (
            implementation_cost
            / monthly_savings
            if monthly_savings > 0
            else 0.0
        )

    return {
        "available": True,

        "value": round(
            roi_percent,
            2,
        ),

        "roi_percent": round(
            roi_percent,
            2,
        ),

        "investment_cost": round(
            implementation_cost,
            2,
        ),

        "annual_savings": round(
            annual_savings,
            2,
        ),

        "payback_months": round(
            payback_months,
            2,
        ),

        "note": (
            "ROI and payback are calculated from "
            "the current multi-agent financial outputs."
        ),
    }


# ============================================================
# MAIN DASHBOARD BUILDER
# ============================================================

def build_cost_optimization_dashboard(
    energy,
    maintenance,
    occupancy,
    security,
    operations,
):

    # --------------------------------------------------------
    # 1. Calculate domain financials
    # --------------------------------------------------------

    energy_financials = (
        _calculate_energy_financials(
            energy
        )
    )

    maintenance_financials = (
        _calculate_maintenance_financials(
            maintenance
        )
    )

    security_financials = (
        _calculate_security_financials(
            security
        )
    )

    # Direct non-energy operating cost
    non_energy_cost = (
        maintenance_financials[
            "monthly_cost"
        ]
        + security_financials[
            "monthly_cost"
        ]
    )

    occupancy_financials = (
        _calculate_occupancy_financials(
            occupancy,
            non_energy_cost,
        )
    )

    financials = {
        "energy": energy_financials,
        "maintenance": maintenance_financials,
        "occupancy": occupancy_financials,
        "security": security_financials,
    }

    # --------------------------------------------------------
    # 2. Administration cost
    # --------------------------------------------------------

    direct_operating_cost = (
        energy_financials[
            "monthly_cost"
        ]
        + maintenance_financials[
            "monthly_cost"
        ]
        + security_financials[
            "monthly_cost"
        ]
    )

    administration_cost = (
        direct_operating_cost
        * ADMINISTRATIVE_COST_RATIO
    )

    monthly_operating_cost = (
        direct_operating_cost
        + administration_cost
    )

    # --------------------------------------------------------
    # 3. Calculate savings
    # --------------------------------------------------------

    calculated_monthly_savings = (
        energy_financials[
            "monthly_savings"
        ]
        + maintenance_financials[
            "monthly_savings"
        ]
        + occupancy_financials[
            "monthly_savings"
        ]
        + security_financials[
            "monthly_savings"
        ]
    )

    # Prevent the optimization model from producing an
    # unrealistic saving larger than the operating cost.
    maximum_allowed_savings = (
        monthly_operating_cost
        * MAX_TOTAL_SAVINGS_RATIO
    )

    monthly_savings = min(
        calculated_monthly_savings,
        maximum_allowed_savings,
    )

    annual_savings = (
        monthly_savings
        * 12
    )

    cost_reduction_percent = (
        monthly_savings
        / monthly_operating_cost
        * 100
        if monthly_operating_cost > 0
        else 0.0
    )

    # --------------------------------------------------------
    # 4. Derive implementation cost
    # --------------------------------------------------------

    assets = maintenance_financials[
        "assets"
    ]

    implementation_cost = (
        IMPLEMENTATION_BASE_COST_INR
        + assets
        * IMPLEMENTATION_COST_PER_ASSET_INR
    )

    # --------------------------------------------------------
    # 5. ROI
    # --------------------------------------------------------

    roi = _build_roi(
        implementation_cost,
        annual_savings,
    )

    # --------------------------------------------------------
    # 6. Cost distribution
    # --------------------------------------------------------

    cost_distribution = (
        _build_cost_distribution(
            energy_financials[
                "monthly_cost"
            ],
            maintenance_financials[
                "monthly_cost"
            ],
            security_financials[
                "monthly_cost"
            ],
        )
    )

    # --------------------------------------------------------
    # 7. Recommendations
    # --------------------------------------------------------

    cost_recommendations = (
        _build_cost_recommendations(
            energy,
            maintenance,
            occupancy,
            security,
            financials,
        )
    )

    # --------------------------------------------------------
    # 8. Facility health
    # --------------------------------------------------------

    facility_health = _number(
        operations.get(
            "kpis",
            {}
        ).get(
            "facility_score"
        ),
        0.0,
    )

    # --------------------------------------------------------
    # 9. Optimization count
    # --------------------------------------------------------

    optimization_count = (
        len(
            cost_recommendations
        )
        + len(
            operations.get(
                "cross_agent_insights",
                [],
            )
        )
    )

    # --------------------------------------------------------
    # 10. Executive response
    # --------------------------------------------------------

    return {

        "available": True,

        "kpis": {

            "total_operating_cost":
                round(
                    monthly_operating_cost,
                    2,
                ),

            "monthly_operating_cost":
                round(
                    monthly_operating_cost,
                    2,
                ),

            "cost_reduction_percent":
                round(
                    cost_reduction_percent,
                    2,
                ),

            "estimated_savings_opportunity":
                round(
                    monthly_savings,
                    2,
                ),

            "monthly_savings":
                round(
                    monthly_savings,
                    2,
                ),

            "annual_savings":
                round(
                    annual_savings,
                    2,
                ),

            "facility_health":
                round(
                    facility_health,
                    1,
                ),

            "optimizations":
                optimization_count,
        },

        "roi":
            roi,

        "cost_distribution":
            cost_distribution,

        "cost_recommendations":
            cost_recommendations,

        "executive_features":
            _build_executive_features(
                energy,
                maintenance,
                occupancy,
                security,
                operations,
            ),

        "data_source":
            (
                "Multi-agent facility intelligence "
                "with dynamically calculated financial outputs"
            ),

        "note":
            (
                "Financial values are calculated from "
                "the current Energy, Maintenance, Occupancy "
                "and Security agent outputs."
            ),
    }