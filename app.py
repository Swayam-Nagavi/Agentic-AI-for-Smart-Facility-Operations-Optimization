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
from src.occupancy_agent import OccupancyAgent


app = Flask(__name__, static_folder="static")


# ============================================================
# CONFIGURATION
# ============================================================

FACILITY_DATA_PATH = "facility_data.csv"

ELECTRICITY_TARIFF_INR_PER_KWH = 8.0
GRID_EMISSION_FACTOR_KG_PER_KWH = 0.70


# ============================================================
# ENERGY DASHBOARD
# ============================================================

def build_dashboard_data():

    df = load_data(FACILITY_DATA_PATH)

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

    hourly_energy = []

    for timestamp in hourly_total.index:

        hourly_energy.append({
            "time": timestamp.isoformat(),

            "energy": round(
                float(hourly_total.loc[timestamp]),
                2,
            ),

            "B001": round(
                float(
                    hourly.get(
                        "B001",
                        pd.Series(
                            0,
                            index=hourly.index,
                        ),
                    ).loc[timestamp]
                ),
                2,
            ),

            "B002": round(
                float(
                    hourly.get(
                        "B002",
                        pd.Series(
                            0,
                            index=hourly.index,
                        ),
                    ).loc[timestamp]
                ),
                2,
            ),

            "B003": round(
                float(
                    hourly.get(
                        "B003",
                        pd.Series(
                            0,
                            index=hourly.index,
                        ),
                    ).loc[timestamp]
                ),
                2,
            ),
        })

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


# ============================================================
# OCCUPANCY AGENT
# ============================================================

def build_occupancy_data():
    df = load_data(FACILITY_DATA_PATH)

    if df.empty:
        return {
            "kpis": {
                "occupancy_rate": 0,
                "occupied_rooms": 0,
                "total_occupancy": 0,
                "vacant_rooms": 0
            },
            "rooms": [],
            "building_summary": [],
            "peak_occupancy": None,
            "peak_hour": None,
            "most_occupied_zone": None,
            "least_occupied_zone": None,
            "insights": ["No occupancy data available."],
            "capacity_alerts": []
        }

    # -------------------------------------------------
    # CURRENT OCCUPANCY
    # Latest reading for every room
    # -------------------------------------------------

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    latest = (
        df.sort_values("timestamp")
        .groupby(["building_id", "room_id"], as_index=False)
        .tail(1)
        .copy()
    )

    latest["occupancy"] = pd.to_numeric(
        latest["occupancy"],
        errors="coerce"
    ).fillna(0)

    capacity_per_room = 10
    total_capacity = len(latest) * capacity_per_room

    total_occupancy = int(latest["occupancy"].sum())

    occupied_rooms = int(
        (latest["occupancy"] > 0).sum()
    )

    vacant_rooms = len(latest) - occupied_rooms

    occupancy_rate = round(
        (total_occupancy / total_capacity) * 100,
        2
    ) if total_capacity > 0 else 0

    # -------------------------------------------------
    # ROOM STATUS
    # -------------------------------------------------

    rooms = []

    for _, row in latest.iterrows():

        occupancy = int(row["occupancy"])

        if occupancy == 0:
            status = "Vacant"
        elif occupancy >= capacity_per_room:
            status = "Critical"
        elif occupancy >= capacity_per_room * 0.9:
            status = "Medium"
        else:
            status = "Occupied"

        rooms.append({
            "building_id": row["building_id"],
            "room_id": row["room_id"],
            "room_type": row["room_type"],
            "occupancy": occupancy,
            "capacity": capacity_per_room,
            "utilization": round(
                (occupancy / capacity_per_room) * 100,
                2
            ),
            "status": status,
            "temperature": round(
                float(row["temperature"]), 2
            ),
            "humidity": round(
                float(row["humidity"]), 2
            ),
            "timestamp": row["timestamp"].isoformat()
        })

    # -------------------------------------------------
    # BUILDING SUMMARY
    # -------------------------------------------------

    building_summary = []

    for building_id, group in latest.groupby("building_id"):

        building_occupancy = int(
            group["occupancy"].sum()
        )

        room_count = len(group)

        building_capacity = room_count * capacity_per_room

        building_summary.append({
            "building_id": building_id,
            "total_occupancy": building_occupancy,
            "total_rooms": room_count,
            "occupied_rooms": int(
                (group["occupancy"] > 0).sum()
            ),
            "occupancy_rate": round(
                (building_occupancy / building_capacity) * 100,
                2
            ) if building_capacity > 0 else 0
        })

    # -------------------------------------------------
    # HISTORICAL OCCUPANCY ANALYTICS
    # Use the Occupancy Agent for peak analysis
    # -------------------------------------------------

    records = df.to_dict("records")

    occupancy_agent = OccupancyAgent(
        records=records,
        capacity_per_zone=capacity_per_room
    )

    peak = occupancy_agent.get_peak_occupancy()
    peak_hour = occupancy_agent.get_peak_hour()

    # Historical highest room reading
    most_occupied_record = max(
        records,
        key=lambda r: float(r.get("occupancy", 0) or 0)
    ) if records else None

    peak_zone = None

    if most_occupied_record:
        peak_zone = (
            f"{most_occupied_record.get('building_id')} - "
            f"{most_occupied_record.get('room_id')}"
        )

    # -------------------------------------------------
    # CURRENT ROOM INSIGHTS
    # -------------------------------------------------

    current_sorted = latest.sort_values(
        "occupancy",
        ascending=False
    )

    most_occupied_room = (
        current_sorted.iloc[0]
        if not current_sorted.empty
        else None
    )

    least_occupied_room = (
        current_sorted.iloc[-1]
        if not current_sorted.empty
        else None
    )

    most_occupied_zone = (
        f"{most_occupied_room['building_id']} - "
        f"{most_occupied_room['room_id']}"
        if most_occupied_room is not None
        else None
    )

    least_occupied_zone = (
        f"{least_occupied_room['building_id']} - "
        f"{least_occupied_room['room_id']}"
        if least_occupied_room is not None
        else None
    )

    # -------------------------------------------------
    # CAPACITY ALERTS
    # -------------------------------------------------

    capacity_alerts = []

    for room in rooms:

        if room["utilization"] >= 100:

            capacity_alerts.append({
                "zone": (
                    f"{room['building_id']} - "
                    f"{room['room_id']}"
                ),
                "occupancy": room["occupancy"],
                "capacity": room["capacity"],
                "utilization": room["utilization"],
                "severity": "High",
                "message": (
                    f"{room['building_id']} - "
                    f"{room['room_id']} has exceeded "
                    f"its capacity."
                )
            })

        elif room["utilization"] >= 90:

            capacity_alerts.append({
                "zone": (
                    f"{room['building_id']} - "
                    f"{room['room_id']}"
                ),
                "occupancy": room["occupancy"],
                "capacity": room["capacity"],
                "utilization": room["utilization"],
                "severity": "Medium",
                "message": (
                    f"{room['building_id']} - "
                    f"{room['room_id']} is nearing capacity."
                )
            })

    # -------------------------------------------------
    # INSIGHTS
    # -------------------------------------------------

    insights = []

    if total_occupancy == 0:
        insights.append({
            "type": "Low Utilization",
            "severity": "Low",
            "message": (
                "All monitored rooms are currently vacant."
            )
        })

    elif occupancy_rate < 30:
        insights.append({
            "type": "Low Utilization",
            "severity": "Low",
            "message": (
                "Current facility occupancy is relatively low."
            )
        })

    else:
        insights.append({
            "type": "Occupancy Status",
            "severity": "Low",
            "message": (
                f"Current facility occupancy is "
                f"{occupancy_rate}%."
            )
        })

    if most_occupied_zone:
        insights.append({
            "type": "Current Occupancy",
            "severity": "Low",
            "message": (
                f"{most_occupied_zone} is currently "
                f"the most occupied room."
            )
        })

    if peak:
        insights.append({
            "type": "Historical Peak",
            "severity": "Low",
            "message": (
                f"Historical peak occupancy was "
                f"{int(peak['occupancy'])} in "
                f"{peak['zone']}."
            )
        })

    if peak_hour:
        insights.append({
            "type": "Peak Hour",
            "severity": "Low",
            "message": (
                f"The busiest observed hour was "
                f"{peak_hour}."
            )
        })

    # -------------------------------------------------
    # FINAL API RESPONSE
    # -------------------------------------------------

    return {
        "data_source": (
            "Occupancy sensor readings from facility_data.csv"
        ),

        "note": (
            "Current occupancy uses the latest available "
            "room-level sensor reading. Peak metrics use "
            "historical sensor records."
        ),

        "kpis": {
            "occupancy_rate": occupancy_rate,
            "occupied_rooms": occupied_rooms,
            "total_occupancy": total_occupancy,
            "vacant_rooms": vacant_rooms,
            "total_rooms": len(latest),
            "total_capacity": total_capacity
        },

        "peak_occupancy": peak,
        "peak_hour": peak_hour,

        "most_occupied_zone": most_occupied_zone,
        "least_occupied_zone": least_occupied_zone,

        "building_summary": building_summary,

        "rooms": rooms,

        "capacity_alerts": capacity_alerts,

        "insights": insights
    }


# ============================================================
# SECURITY AGENT
# ============================================================

def build_security_data():

    # Security events are intentionally not generated from
    # facility sensor data. The current facility dataset does
    # not contain access-control, CCTV, intrusion, badge,
    # door, or security-event fields.

    return {

        "available": False,

        "kpis": {
            "total_events": 0,
            "active_alerts": 0,
            "critical_alerts": 0,
            "resolved_events": 0,
        },

        "alerts": [],

        "events": [],

        "insights": [],

        "data_source": None,

        "note": (
            "Security monitoring requires a dedicated security "
            "event dataset. The current facility_data.csv contains "
            "facility and occupancy sensor data but no security "
            "events."
        ),
    }


# ============================================================
# MAINTENANCE API
# ============================================================

@app.route("/api/maintenance/dashboard")
def maintenance_dashboard_api():

    return jsonify(
        build_maintenance_dashboard(
            FACILITY_DATA_PATH
        )
    )


# ============================================================
# OCCUPANCY API
# ============================================================

@app.route("/api/occupancy")
def occupancy_api():

    return jsonify(
        build_occupancy_data()
    )


@app.route("/api/occupancy/insights")
def occupancy_insights_api():

    data = build_occupancy_data()

    return jsonify({
        "insights": data["insights"],
        "kpis": data["kpis"],
    })


@app.route("/api/occupancy/rooms")
def occupancy_rooms_api():

    data = build_occupancy_data()

    return jsonify({
        "rooms": data["rooms"],
    })


# ============================================================
# SECURITY APIs
# ============================================================

@app.route("/api/security")
def security_api():

    return jsonify(
        build_security_data()
    )


@app.route("/api/security/alerts")
def security_alerts_api():

    data = build_security_data()

    return jsonify({
        "alerts": data["alerts"],
        "active_alerts": data["kpis"]["active_alerts"],
        "critical_alerts": data["kpis"]["critical_alerts"],
    })


# ============================================================
# MAIN DASHBOARD
# ============================================================

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


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/api/health")
def health_check():

    return jsonify({
        "status": "ok",
        "agents": {
            "energy": True,
            "maintenance": True,
            "occupancy": True,
            "security": False,
        },
    })

@app.route("/maintenance.html")
def maintenance_page():
    return send_from_directory("static", "maintenance.html")


@app.route("/occupancy.html")
def occupancy_page():
    return send_from_directory("static", "occupancy.html")


@app.route("/security.html")
def security_page():
    return send_from_directory("static", "security.html")
# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )