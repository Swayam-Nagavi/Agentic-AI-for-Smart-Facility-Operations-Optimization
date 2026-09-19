"""
Energy Agent
------------
Builds the Energy Intelligence Dashboard from the rows that are present in
``facility data source``. The agent calculates KPIs, aggregations, anomalies, and
recommendations from sensor readings only; it does not inject sample
or fallback facility readings.
"""

from pathlib import Path

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
# HELPERS
# ============================================================

def _safe_round(value, digits=2, default=0.0):
    if pd.isna(value):
        return default

    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return default


def _infer_sampling_interval(df):
    if df.empty or "timestamp" not in df.columns:
        return None

    timestamps = (
        pd.Series(df["timestamp"].dropna().unique())
        .sort_values()
        .reset_index(drop=True)
    )

    if len(timestamps) < 2:
        return None

    deltas = timestamps.diff().dropna()

    if deltas.empty:
        return None

    minutes = deltas.median().total_seconds() / 60

    if minutes.is_integer():
        return f"{int(minutes)} minutes"

    return f"{minutes:.1f} minutes"


def _build_metadata(df, data_path):
    path = Path(data_path)
    display_source = "Simulated facility energy sensors (digital twin demo)"

    if df.empty:
        return {
            "data_source": display_source,
            "record_count": 0,
            "building_ids": [],
            "room_count": 0,
            "start_timestamp": None,
            "end_timestamp": None,
            "sampling_interval": None,
            "summary": "No usable data rows found",
        }

    timestamps = df["timestamp"].dropna()
    start_timestamp = timestamps.min().isoformat() if not timestamps.empty else None
    end_timestamp = timestamps.max().isoformat() if not timestamps.empty else None

    building_ids = sorted(str(value) for value in df["building_id"].dropna().unique())
    room_count = int(
        df[["building_id", "room_id"]]
        .drop_duplicates()
        .shape[0]
    )

    return {
        "data_source": display_source,
        "record_count": int(len(df)),
        "building_ids": building_ids,
        "room_count": room_count,
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "sampling_interval": _infer_sampling_interval(df),
        "summary": f"{len(df)} records • {room_count} rooms • {len(building_ids)} buildings",
    }


def _empty_dashboard(data_path):
    metadata = _build_metadata(pd.DataFrame(), data_path)

    return {
        "available": False,
        "kpis": {
            "total_energy": 0.0,
            "average_interval_energy": 0.0,
            "peak_usage": 0.0,
            "anomalies": 0,
            "anomalies_shown": 0,
            "estimated_cost": 0.0,
            "potential_cost_savings": 0.0,
            "efficiency_score": 0.0,
            "potential_carbon_reduction": 0.0,
        },
        "units": {
            "sampling_interval": "Auto-detected",
            "interval_energy": "kWh / reading",
            "hourly_energy": "kWh / hour",
            "total_energy": "kWh / monitoring period",
            "tariff": "₹8.00 / kWh",
            "carbon_factor": "0.70 kg CO2 / kWh",
        },
        "building_energy": [],
        "room_energy": [],
        "hourly_energy": [],
        "peak": peak_usage(pd.DataFrame()),
        "anomalies": [],
        "recommendations": [],
        "energy_distribution": [],
        "metadata": metadata,
        "data_source": metadata["data_source"],
        "note": "No facility sensor readings are available yet.",
    }


# ============================================================
# RECOMMENDATIONS (rule-based, data source-backed)
# ============================================================

def generate_recommendations(df):
    """Generate energy-optimisation recommendations from sensor readings."""

    if df.empty:
        return []

    recommendations = []

    # 1. HVAC running in empty rooms.
    empty_hvac = df[
        (df["occupancy"] == 0)
        & (df["hvac_status"].astype(str).str.upper() == "ON")
    ]

    if not empty_hvac.empty:
        wasted_hvac = empty_hvac["hvac_energy"].sum()

        recommendations.append({
            "type": "HVAC Scheduling",
            "priority": "Medium",
            "target": "Facility-wide",
            "message": (
                f"HVAC operated during {len(empty_hvac)} "
                f"unoccupied reading(s), using "
                f"approximately {wasted_hvac:.2f} kWh."
            ),
            "reason": (
                "The recommendation is calculated from occupancy, HVAC status, "
                "and HVAC energy sensor readings."
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
            .sort_values("count", ascending=False)
        )

        for _, row in grouped.head(3).iterrows():
            recommendations.append({
                "type": "Setpoint / HVAC Check",
                "priority": "High",
                "target": f"{row['building_id']} {row['room_id']}",
                "message": (
                    f"{row['building_id']} {row['room_id']} "
                    f"({row['room_type']}) exceeded its HVAC setpoint "
                    f"in {int(row['count'])} reading(s)."
                ),
                "reason": (
                    "The recommendation is calculated from temperature, "
                    "occupancy, and HVAC setpoint readings."
                ),
            })

    # 3. Equipment warnings.
    equipment_warnings = df[
        df["equipment_status"]
        .astype(str)
        .str.lower()
        .isin(["warning", "fault"])
    ]

    if not equipment_warnings.empty:
        equipment_warnings = equipment_warnings.copy()
        equipment_warnings["_status_rank"] = (
            equipment_warnings["equipment_status"]
            .astype(str)
            .str.lower()
            .map({"fault": 2, "warning": 1})
            .fillna(0)
        )
        equipment_warnings = equipment_warnings.sort_values(
            ["_status_rank", "timestamp"],
            ascending=[False, False],
        )

        for _, row in equipment_warnings.head(3).iterrows():
            status = str(row["equipment_status"]).lower()

            recommendations.append({
                "type": "Equipment Investigation",
                "priority": "Critical" if status == "fault" else "High",
                "target": f"{row['building_id']} {row['room_id']}",
                "message": (
                    f"{row['building_id']} {row['room_id']} "
                    f"({row['room_type']}) reported an equipment {status} "
                    f"at {row['timestamp']}."
                ),
                "reason": (
                    "The recommendation is generated when equipment status "
                    "reports a warning or fault."
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
            "target": f"{building} {room}",
            "message": (
                f"{building} {room} ({room_type}) has the highest monitoring period "
                f"consumption at {energy:.2f} kWh."
            ),
            "reason": (
                "This is the largest room-level sum of the energy_consumption "
                "column in the monitored readings."
            ),
        })

    return recommendations


# ============================================================
# ENERGY DASHBOARD BUILDER
# ============================================================

def build_energy_dashboard(data_path):
    """
    Build the complete energy dashboard response from facility data rows.
    """

    df = load_data(data_path)

    if df.empty:
        return _empty_dashboard(data_path)

    metadata = _build_metadata(df, data_path)

    total = total_energy(df)
    average = average_interval_energy(df)

    buildings = energy_by_building(df)
    rooms = energy_by_room(df)
    peak = peak_usage(df)
    anomalies_all = detect_anomalies(df, limit=None)
    anomaly_total_count = int(len(anomalies_all))
    anomalies = anomalies_all.head(20)
    recommendations = generate_recommendations(df)

    distribution = calculate_energy_distribution(df)

    estimated_cost = total * ELECTRICITY_TARIFF_INR_PER_KWH

    empty_hvac_energy = df.loc[
        (df["occupancy"] == 0)
        & (df["hvac_status"].astype(str).str.upper() == "ON"),
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

    potential_cost_savings = potential_savings_kwh * ELECTRICITY_TARIFF_INR_PER_KWH

    empty_hvac_ratio = empty_hvac_energy / total if total > 0 else 0
    anomaly_ratio = anomaly_excess / total if total > 0 else 0

    equipment_status_lower = df["equipment_status"].astype(str).str.lower()

    warning_ratio = (
        len(df[equipment_status_lower == "warning"]) / len(df)
        if len(df) > 0
        else 0
    )
    fault_reading_count = int((equipment_status_lower == "fault").sum())
    fault_ratio = fault_reading_count / len(df) if len(df) > 0 else 0
    hot_ratio = (
        len(df[df["temperature"] > df["hvac_setpoint"] + 1.5]) / len(df)
        if len(df) > 0
        else 0
    )

    efficiency_score = 100 - (
        empty_hvac_ratio * 30
        + anomaly_ratio * 30
        + warning_ratio * 10
        + fault_ratio * 20
        + hot_ratio * 20
    )

    # A facility with an active equipment fault must not be rated "Excellent",
    # otherwise the KPI contradicts the fault alerts shown next to it.
    if fault_reading_count > 0:
        efficiency_score = min(efficiency_score, 84)

    efficiency_score = max(0, min(100, efficiency_score))

    potential_carbon_reduction = potential_savings_kwh * GRID_EMISSION_FACTOR_KG_PER_KWH

    hourly = (
        df.set_index("timestamp")
        .groupby("building_id")["energy_consumption"]
        .resample("1h")
        .sum()
        .unstack(level=0)
        .fillna(0)
    )

    hourly_total = hourly.sum(axis=1)
    building_ids = metadata["building_ids"]

    hourly_energy = []

    for timestamp in hourly_total.index:
        entry = {
            "time": timestamp.isoformat(),
            "energy": round(float(hourly_total.loc[timestamp]), 2),
        }

        for building_id in building_ids:
            entry[building_id] = round(
                float(
                    hourly.get(
                        building_id,
                        pd.Series(0, index=hourly.index),
                    ).loc[timestamp]
                ),
                2,
            )

        hourly_energy.append(entry)

    building_energy = [
        {
            "building": str(building),
            "energy": round(float(energy), 2),
        }
        for building, energy in buildings.items()
    ]

    room_energy = [
        {
            "label": f"{building} - {room} ({room_type})",
            "building": str(building),
            "room": str(room),
            "room_type": str(room_type),
            "energy": round(float(energy), 2),
        }
        for (building, room, room_type), energy
        in rooms.items()
    ]

    anomaly_data = [
        {
            "building": str(row["building_id"]),
            "room": str(row["room_id"]),
            "room_type": str(row["room_type"]),
            "timestamp": row["timestamp"].isoformat(),
            "energy": _safe_round(row["energy_consumption"], 3),
            "baseline": _safe_round(row["baseline"], 3),
            "above_baseline": _safe_round(row["baseline_difference_pct"], 1),
        }
        for _, row in anomalies.iterrows()
    ]

    return {
        "available": True,
        "kpis": {
            "total_energy": total,
            "average_interval_energy": average,
            "peak_usage": peak["energy"],
            "anomalies": anomaly_total_count,
            "anomalies_shown": len(anomaly_data),
            "estimated_cost": round(estimated_cost, 2),
            "potential_cost_savings": round(potential_cost_savings, 2),
            "efficiency_score": round(efficiency_score, 1),
            "potential_carbon_reduction": round(potential_carbon_reduction, 2),
        },
        "units": {
            "sampling_interval": metadata["sampling_interval"] or "Auto-detected",
            "interval_energy": "kWh / reading",
            "hourly_energy": "kWh / hour",
            "total_energy": "kWh / monitoring period",
            "tariff": "₹8.00 / kWh",
            "carbon_factor": "0.70 kg CO2 / kWh",
        },
        "building_energy": building_energy,
        "room_energy": room_energy,
        "hourly_energy": hourly_energy,
        "peak": peak,
        "anomalies": anomaly_data,
        "recommendations": recommendations,
        "energy_distribution": distribution,
        "metadata": metadata,
        "data_source": metadata["data_source"],
        "note": (
            "Dashboard values reflect the current facility monitoring data."
        ),
    }
