"""
Energy Agent
------------
Agent responsible for energy monitoring, analytics,
anomaly detection, cost estimation, and generating
actionable energy-optimisation recommendations.

This module is self-contained.  Its only internal
dependency is ``src.analytics`` (energy-specific helpers).
"""

import pandas as pd

from src.analytics import (
    load_data,
    total_energy,
    average_interval_energy,
    energy_by_building,
    energy_by_room,
    peak_usage,
    detect_anomalies,
    calculate_energy_distribution,
)


# ============================================================
# CONFIGURATION
# ============================================================

ELECTRICITY_TARIFF_INR_PER_KWH = 8.0
GRID_EMISSION_FACTOR_KG_PER_KWH = 0.70


# ============================================================
# RECOMMENDATIONS (rule-based)
# ============================================================

def generate_recommendations(df):
    """Generate energy-optimisation recommendations."""

    recommendations = []

    # 1. HVAC running in empty rooms.
    empty_hvac = df[
        (df["occupancy"] == 0)
        & (df["hvac_status"] == "ON")
    ]

    if not empty_hvac.empty:
        wasted_hvac = empty_hvac["hvac_energy"].sum()

        recommendations.append({
            "type": "HVAC Scheduling",
            "priority": "Medium",
            "message": (
                f"HVAC operated during {len(empty_hvac)} "
                f"unoccupied 15-minute interval(s), using "
                f"approximately {wasted_hvac:.2f} kWh."
            ),
            "reason": (
                "Cooling an unoccupied room can create "
                "avoidable energy consumption."
            ),
        })

    # 2. High-temperature rooms.
    hot_rooms = df[
        (df["temperature"] > df["hvac_setpoint"] + 1.5)
        & (df["occupancy"] > 0)
    ]

    if not hot_rooms.empty:
        grouped = (
            hot_rooms.groupby(
                ["building_id", "room_id", "room_type"]
            )
            .size()
            .reset_index(name="count")
        )

        for _, row in grouped.head(3).iterrows():
            recommendations.append({
                "type": "Setpoint / HVAC Check",
                "priority": "High",
                "message": (
                    f"{row['building_id']} {row['room_id']} "
                    f"({row['room_type']}) repeatedly exceeded "
                    f"its HVAC setpoint."
                ),
                "reason": (
                    "Temperature above the intended setpoint "
                    "while occupied may indicate cooling demand "
                    "or HVAC performance issues."
                ),
            })

    # 3. Equipment warnings.
    equipment_warnings = df[
        df["equipment_status"] == "Warning"
    ]

    if not equipment_warnings.empty:
        for _, row in equipment_warnings.head(3).iterrows():
            recommendations.append({
                "type": "Equipment Investigation",
                "priority": "High",
                "message": (
                    f"{row['building_id']} {row['room_id']} "
                    f"({row['room_type']}) reported an equipment warning."
                ),
                "reason": (
                    "An equipment warning can indicate abnormal "
                    "operation or an unexpected energy load."
                ),
            })

    # 4. Highest-consuming room.
    room_energy = (
        df.groupby(
            ["building_id", "room_id", "room_type"]
        )["energy_consumption"]
        .sum()
        .sort_values(ascending=False)
    )

    if not room_energy.empty:
        (building, room, room_type), energy = (
            room_energy.index[0],
            room_energy.iloc[0],
        )

        recommendations.append({
            "type": "High Consumption",
            "priority": "Medium",
            "message": (
                f"{building} {room} ({room_type}) has the "
                f"highest 24-hour consumption at {energy:.2f} kWh."
            ),
            "reason": (
                "The room is the largest energy consumer in "
                "the monitored facility and should be investigated "
                "for HVAC, equipment and operating-schedule optimization."
            ),
        })

    if not recommendations:
        recommendations.append({
            "type": "No Action Required",
            "priority": "Low",
            "message": (
                "No significant optimization opportunity "
                "was detected in the current monitoring period."
            ),
            "reason": (
                "Energy, occupancy, HVAC and equipment patterns "
                "are within the configured monitoring thresholds."
            ),
        })

    return recommendations


# ============================================================
# ENERGY DASHBOARD BUILDER
# ============================================================

def build_energy_dashboard(data_path):
    """
    Build the complete energy dashboard response.

    Parameters
    ----------
    data_path : str
        Path to the facility CSV data file.

    Returns
    -------
    dict
        JSON-ready dictionary with KPIs, charts, anomalies,
        and recommendations.
    """

    df = load_data(data_path)

    total = total_energy(df)
    average = average_interval_energy(df)

    buildings = energy_by_building(df)
    rooms = energy_by_room(df)
    peak = peak_usage(df)
    anomalies = detect_anomalies(df)
    recommendations = generate_recommendations(df)

    # ---------------------------------------------------------
    # Energy distribution
    # ---------------------------------------------------------

    distribution = calculate_energy_distribution(df)

    # ---------------------------------------------------------
    # Estimated cost
    # ---------------------------------------------------------

    estimated_cost = total * ELECTRICITY_TARIFF_INR_PER_KWH

    # ---------------------------------------------------------
    # Potential savings
    # ---------------------------------------------------------

    empty_hvac_energy = df.loc[
        (df["occupancy"] == 0)
        & (df["hvac_status"] == "ON"),
        "hvac_energy",
    ].sum()

    baseline_df = df.copy()

    baseline_df["room_baseline"] = (
        baseline_df
        .groupby(["building_id", "room_id"])["energy_consumption"]
        .transform("mean")
    )

    baseline_df["excess_energy"] = (
        baseline_df["energy_consumption"]
        - baseline_df["room_baseline"]
    ).clip(lower=0)

    anomaly_excess = baseline_df.loc[
        baseline_df["energy_consumption"]
        > baseline_df["room_baseline"] * 1.5,
        "excess_energy",
    ].sum()

    potential_savings_kwh = (
        empty_hvac_energy * 0.80
        + anomaly_excess * 0.30
    )

    potential_savings_kwh = min(
        potential_savings_kwh,
        total * 0.20,
    )

    potential_cost_savings = (
        potential_savings_kwh
        * ELECTRICITY_TARIFF_INR_PER_KWH
    )

    # ---------------------------------------------------------
    # Efficiency score
    # ---------------------------------------------------------

    empty_hvac_ratio = (
        empty_hvac_energy / total
        if total > 0
        else 0
    )

    anomaly_ratio = (
        anomaly_excess / total
        if total > 0
        else 0
    )

    warning_ratio = (
        len(df[df["equipment_status"] == "Warning"])
        / len(df)
        if len(df) > 0
        else 0
    )

    hot_ratio = (
        len(
            df[
                df["temperature"]
                > df["hvac_setpoint"] + 1.5
            ]
        )
        / len(df)
        if len(df) > 0
        else 0
    )

    efficiency_score = 100 - (
        empty_hvac_ratio * 30
        + anomaly_ratio * 30
        + warning_ratio * 10
        + hot_ratio * 20
    )

    efficiency_score = max(
        0,
        min(100, efficiency_score),
    )

    # ---------------------------------------------------------
    # Carbon reduction
    # ---------------------------------------------------------

    potential_carbon_reduction = (
        potential_savings_kwh
        * GRID_EMISSION_FACTOR_KG_PER_KWH
    )

    # ---------------------------------------------------------
    # Hourly trend
    # ---------------------------------------------------------

    hourly = (
        df.set_index("timestamp")
        .groupby("building_id")["energy_consumption"]
        .resample("1h")
        .sum()
        .unstack(level=0)
        .fillna(0)
    )

    hourly_total = hourly.sum(axis=1)

    # Dynamically pick up whatever building IDs exist.
    building_ids = sorted(buildings.keys())

    hourly_energy = []

    for timestamp in hourly_total.index:

        entry = {
            "time": timestamp.isoformat(),
            "energy": round(
                float(hourly_total.loc[timestamp]),
                2,
            ),
        }

        for bid in building_ids:
            entry[bid] = round(
                float(
                    hourly.get(
                        bid,
                        pd.Series(0, index=hourly.index),
                    ).loc[timestamp]
                ),
                2,
            )

        hourly_energy.append(entry)

    # ---------------------------------------------------------
    # Building data
    # ---------------------------------------------------------

    building_energy = [
        {
            "building": building,
            "energy": round(float(energy), 2),
        }
        for building, energy in buildings.items()
    ]

    # ---------------------------------------------------------
    # Room data
    # ---------------------------------------------------------

    room_energy = [
        {
            "label": f"{building} - {room} ({room_type})",
            "building": building,
            "room": room,
            "room_type": room_type,
            "energy": round(float(energy), 2),
        }
        for (building, room, room_type), energy
        in rooms.items()
    ]

    # ---------------------------------------------------------
    # Anomaly data
    # ---------------------------------------------------------

    anomaly_data = [
        {
            "building": row["building_id"],
            "room": row["room_id"],
            "room_type": row["room_type"],
            "timestamp": str(row["timestamp"]),
            "energy": round(
                float(row["energy_consumption"]),
                3,
            ),
            "baseline": round(
                float(row["baseline"]),
                3,
            ),
            "above_baseline": round(
                float(row["baseline_difference_pct"]),
                1,
            ),
        }
        for _, row in anomalies.iterrows()
    ]

    return {

        "kpis": {
            "total_energy": total,
            "average_interval_energy": average,
            "peak_usage": peak["energy"],
            "anomalies": len(anomaly_data),

            "estimated_cost": round(
                estimated_cost,
                2,
            ),

            "potential_cost_savings": round(
                potential_cost_savings,
                2,
            ),

            "efficiency_score": round(
                efficiency_score,
                1,
            ),

            "potential_carbon_reduction": round(
                potential_carbon_reduction,
                2,
            ),
        },

        "units": {
            "sampling_interval": "15 minutes",
            "interval_energy": "kWh / 15 min",
            "hourly_energy": "kWh / hour",
            "total_energy": "kWh / 24 hours",
            "tariff": "\u20b98.00 / kWh",
            "carbon_factor": "0.70 kg CO2 / kWh",
        },

        "building_energy": building_energy,

        "room_energy": room_energy,

        "hourly_energy": hourly_energy,

        "peak": peak,

        "anomalies": anomaly_data,

        "recommendations": recommendations,

        "energy_distribution": distribution,
    }
