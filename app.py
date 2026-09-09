from flask import Flask, jsonify, send_from_directory
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
from src.energy_agent import generate_recommendations
from src.maintenance_agent import build_maintenance_dashboard


app = Flask(__name__, static_folder="static")


# Assumptions used only for estimated metrics.
ELECTRICITY_TARIFF_INR_PER_KWH = 8.0
GRID_EMISSION_FACTOR_KG_PER_KWH = 0.70


def build_dashboard_data():
    df = load_data("facility_data.csv")

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
    # Savings are NOT actual measured savings.
    # They are an estimate based on avoidable HVAC usage
    # and excess anomaly consumption.
    empty_hvac_energy = df.loc[
        (df["occupancy"] == 0)
        & (df["hvac_status"] == "ON"),
        "hvac_energy",
    ].sum()

    baseline_df = df.copy()

    baseline_df["room_baseline"] = (
        baseline_df.groupby(
            ["building_id", "room_id"]
        )["energy_consumption"]
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
    # Potential carbon reduction
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

    hourly_energy = []

    for timestamp in hourly_total.index:
        hourly_energy.append({
            "time": timestamp.isoformat(),
            "energy": round(
                float(hourly_total.loc[timestamp]),
                2,
            ),
            "B001": round(
                float(hourly.get("B001", pd.Series(0, index=hourly.index)).loc[timestamp]),
                2,
            ),
            "B002": round(
                float(hourly.get("B002", pd.Series(0, index=hourly.index)).loc[timestamp]),
                2,
            ),
            "B003": round(
                float(hourly.get("B003", pd.Series(0, index=hourly.index)).loc[timestamp]),
                2,
            ),
        })

    # ---------------------------------------------------------
    # API-friendly building data
    # ---------------------------------------------------------
    building_energy = [
        {
            "building": building,
            "energy": round(float(energy), 2),
        }
        for building, energy in buildings.items()
    ]

    # ---------------------------------------------------------
    # API-friendly room data
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
    # API-friendly anomalies
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
    }


@app.route("/api/maintenance/dashboard")
def maintenance_dashboard_api():
    return jsonify(build_maintenance_dashboard("facility_data.csv"))

@app.route("/")
def home():
    return send_from_directory(
        "static",
        "index.html",
    )


@app.route("/api/dashboard")
def dashboard_api():
    return jsonify(
        build_dashboard_data()
    )


if __name__ == "__main__":
    app.run(
        debug=True
    )
