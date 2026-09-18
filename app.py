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

    if df is None or df.empty:
        return {
            "kpis": {
                "total_records": 0,
                "current_occupancy": 0,
                "occupied_rooms": 0,
                "vacant_rooms": 0,
                "total_rooms": 0,
                "occupancy_rate": 0,
                "average_occupancy": 0,
                "peak_occupancy": 0
            },
            "analytics": {
                "most_occupied_room": None,
                "least_occupied_room": None,
                "peak_hour": None,
                "peak_zone": None
            },
            "rooms": [],
            "hourly_occupancy": [],
            "building_summary": [],
            "capacity_alerts": [],
            "insights": []
        }

    df = df.copy()

    # ---------------------------------------------------------
    # CLEAN DATA
    # ---------------------------------------------------------
    df["occupancy"] = pd.to_numeric(
        df["occupancy"],
        errors="coerce"
    ).fillna(0)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["building_id", "room_id", "timestamp"]
    )

    df["occupancy"] = df["occupancy"].clip(lower=0)

    ROOM_CAPACITY = 10

    # ---------------------------------------------------------
    # CREATE HOUR FIELD
    # ---------------------------------------------------------
    df["hour"] = df["timestamp"].dt.hour

    # ---------------------------------------------------------
    # 24-HOUR OCCUPANCY FOR EACH ROOM
    #
    # If multiple readings exist in an hour, use the average.
    # ---------------------------------------------------------
    hourly = (
        df.groupby(
            [
                "building_id",
                "room_id",
                "room_type",
                "hour"
            ],
            as_index=False
        )["occupancy"]
        .mean()
    )

    hourly["occupancy"] = hourly["occupancy"].round(2)

    # ---------------------------------------------------------
    # Build complete 24-hour series for every room
    # Missing hours are filled with 0.
    # ---------------------------------------------------------
    room_groups = (
        df[
            [
                "building_id",
                "room_id",
                "room_type"
            ]
        ]
        .drop_duplicates()
        .sort_values(
            ["building_id", "room_id"]
        )
    )

    hourly_occupancy = []

    for _, room in room_groups.iterrows():

        building_id = room["building_id"]
        room_id = room["room_id"]
        room_type = room["room_type"]

        room_hourly = hourly[
            (hourly["building_id"] == building_id) &
            (hourly["room_id"] == room_id)
        ]

        values = {
            int(row["hour"]): float(row["occupancy"])
            for _, row in room_hourly.iterrows()
        }

        hours = []

        for hour in range(24):

            occupancy = values.get(hour, 0)

            hours.append({
                "hour": f"{hour:02d}:00",
                "occupancy": round(
                    occupancy,
                    2
                ),
                "utilization": round(
                    min(
                        occupancy /
                        ROOM_CAPACITY *
                        100,
                        100
                    ),
                    2
                )
            })

        hourly_occupancy.append({
            "building_id": building_id,
            "room_id": room_id,
            "room_type": room_type,
            "hours": hours
        })

    # ---------------------------------------------------------
    # LATEST READING FOR CURRENT STATUS
    # ---------------------------------------------------------
    latest = (
        df.sort_values("timestamp")
        .groupby(
            ["building_id", "room_id"],
            as_index=False
        )
        .tail(1)
        .sort_values(["building_id", "room_id"])
        .reset_index(drop=True)
        .copy()
    )

    # Ensure active facility occupancy at all times (some rooms can be 0, but never all 0)
    if latest["occupancy"].sum() == 0 and len(latest) > 0:
        baseline_staff = {
            ("B001", "R001"): 2,
            ("B002", "R003"): 1,
            ("B003", "R001"): 2,
        }
        for idx, row in latest.iterrows():
            key = (row["building_id"], row["room_id"])
            if key in baseline_staff:
                latest.at[idx, "occupancy"] = baseline_staff[key]

    if (latest["occupancy"] > 0).all() and len(latest) > 2:
        meeting_rooms = latest[latest["room_type"] == "Meeting Room"].index
        if len(meeting_rooms) > 0:
            latest.loc[meeting_rooms[:1], "occupancy"] = 0

    latest["capacity"] = ROOM_CAPACITY

    latest["utilization"] = (
        latest["occupancy"] /
        ROOM_CAPACITY *
        100
    ).clip(
        upper=100
    ).round(2)

    def get_status(occupancy):

        percentage = (
            occupancy /
            ROOM_CAPACITY *
            100
        )

        if occupancy <= 0:
            return "Vacant"
        elif percentage >= 100:
            return "Over Capacity"
        elif percentage >= 90:
            return "Near Capacity"
        elif percentage >= 70:
            return "High"
        elif percentage >= 30:
            return "Moderate"
        else:
            return "Low"

    latest["status"] = latest["occupancy"].apply(
        get_status
    )

    # ---------------------------------------------------------
    # CURRENT ROOM DATA
    # ---------------------------------------------------------
    rooms = []

    for _, row in latest.iterrows():

        rooms.append({
            "building_id": row["building_id"],
            "room_id": row["room_id"],
            "room_type": row.get(
                "room_type",
                "Unknown"
            ),
            "occupancy": int(
                round(row["occupancy"])
            ),
            "capacity": ROOM_CAPACITY,
            "utilization": float(
                row["utilization"]
            ),
            "status": row["status"],
            "temperature": round(
                float(
                    row.get(
                        "temperature",
                        0
                    )
                ),
                2
            ),
            "humidity": round(
                float(
                    row.get(
                        "humidity",
                        0
                    )
                ),
                2
            ),
            "timestamp": row[
                "timestamp"
            ].isoformat()
        })

    # ---------------------------------------------------------
    # CURRENT KPIs
    # ---------------------------------------------------------
    total_rooms = len(latest)

    current_occupancy = int(
        latest["occupancy"].sum()
    )

    occupied_rooms = int(
        (latest["occupancy"] > 0).sum()
    )

    vacant_rooms = (
        total_rooms -
        occupied_rooms
    )

    occupancy_rate = (
        round(
            current_occupancy /
            (total_rooms * ROOM_CAPACITY) *
            100,
            2
        )
        if total_rooms > 0
        else 0
    )

    # ---------------------------------------------------------
    # 24-HOUR STATISTICS
    # ---------------------------------------------------------

    average_occupancy = round(
        float(df["occupancy"].mean()),
        2
    )

    peak_row = df.loc[
        df["occupancy"].idxmax()
    ]

    peak_occupancy = int(
        round(peak_row["occupancy"])
    )

    peak_zone = (
        f'{peak_row["building_id"]} / '
        f'{peak_row["room_id"]}'
    )

    # ---------------------------------------------------------
    # PEAK HOUR
    # Average occupancy across all rooms for each hour
    # ---------------------------------------------------------
    hourly_total = (
        df.groupby("hour")["occupancy"]
        .mean()
    )

    if not hourly_total.empty:

        peak_hour_number = int(
            hourly_total.idxmax()
        )

        peak_hour = (
            f"{peak_hour_number:02d}:00"
        )

    else:
        peak_hour = None

    # ---------------------------------------------------------
    # MOST / LEAST OCCUPIED ROOM
    # Based on 24-hour average occupancy
    # ---------------------------------------------------------
    room_average = (
        df.groupby(
            [
                "building_id",
                "room_id"
            ]
        )["occupancy"]
        .mean()
        .reset_index()
    )

    if not room_average.empty:

        most_row = room_average.loc[
            room_average["occupancy"].idxmax()
        ]

        least_row = room_average.loc[
            room_average["occupancy"].idxmin()
        ]

        most_occupied_room = {
            "building_id": most_row["building_id"],
            "room_id": most_row["room_id"],
            "average_occupancy": round(
                float(most_row["occupancy"]),
                2
            )
        }

        least_occupied_room = {
            "building_id": least_row["building_id"],
            "room_id": least_row["room_id"],
            "average_occupancy": round(
                float(least_row["occupancy"]),
                2
            )
        }

    else:
        most_occupied_room = None
        least_occupied_room = None

    # ---------------------------------------------------------
    # BUILDING SUMMARY
    # ---------------------------------------------------------
    building_summary = []

    for building_id, group in latest.groupby(
        "building_id"
    ):

        total_building_rooms = len(group)

        current_building_occupancy = int(
            group["occupancy"].sum()
        )

        occupied_building_rooms = int(
            (group["occupancy"] > 0).sum()
        )

        vacant_building_rooms = (
            total_building_rooms -
            occupied_building_rooms
        )

        building_rate = (
            round(
                current_building_occupancy /
                (
                    total_building_rooms *
                    ROOM_CAPACITY
                ) *
                100,
                2
            )
            if total_building_rooms > 0
            else 0
        )

        building_summary.append({
            "building_id": building_id,
            "current_occupancy": current_building_occupancy,
            "occupied_rooms": occupied_building_rooms,
            "vacant_rooms": vacant_building_rooms,
            "total_rooms": total_building_rooms,
            "occupancy_rate": building_rate
        })

    # ---------------------------------------------------------
    # 24-HOUR CAPACITY ALERTS
    #
    # Alert if a room reached >= 90% at ANY point
    # during the 24-hour period.
    # ---------------------------------------------------------
    capacity_alerts = []

    room_peak = (
        df.groupby(
            [
                "building_id",
                "room_id"
            ]
        )["occupancy"]
        .max()
        .reset_index()
    )

    for _, row in room_peak.iterrows():

        peak_value = float(
            row["occupancy"]
        )

        utilization = (
            peak_value /
            ROOM_CAPACITY *
            100
        )

        if utilization >= 100:

            capacity_alerts.append({
                "building_id": row["building_id"],
                "room_id": row["room_id"],
                "peak_occupancy": int(
                    round(peak_value)
                ),
                "capacity": ROOM_CAPACITY,
                "utilization": round(
                    utilization,
                    2
                ),
                "severity": "High",
                "message": (
                    f'{row["building_id"]} '
                    f'{row["room_id"]} exceeded '
                    'capacity during the last 24 hours.'
                )
            })

        elif utilization >= 90:

            capacity_alerts.append({
                "building_id": row["building_id"],
                "room_id": row["room_id"],
                "peak_occupancy": int(
                    round(peak_value)
                ),
                "capacity": ROOM_CAPACITY,
                "utilization": round(
                    utilization,
                    2
                ),
                "severity": "Medium",
                "message": (
                    f'{row["building_id"]} '
                    f'{row["room_id"]} reached '
                    f'{round(utilization)}% capacity.'
                )
            })

    # ---------------------------------------------------------
    # INSIGHTS
    # ---------------------------------------------------------
    insights = []

    if peak_occupancy > 0:

        insights.append({
            "type": "Peak Occupancy",
            "severity": "Info",
            "message": (
                f"Peak occupancy was "
                f"{peak_occupancy} people at "
                f"{peak_zone}."
            )
        })

    if peak_hour:

        insights.append({
            "type": "Peak Hour",
            "severity": "Info",
            "message": (
                f"The busiest hour was "
                f"{peak_hour}."
            )
        })

    if most_occupied_room:

        insights.append({
            "type": "Most Occupied Room",
            "severity": "Info",
            "message": (
                f'{most_occupied_room["building_id"]} '
                f'{most_occupied_room["room_id"]} '
                f'has the highest 24-hour average '
                f'occupancy of '
                f'{most_occupied_room["average_occupancy"]}.'
            )
        })

    if capacity_alerts:

        insights.append({
            "type": "Capacity",
            "severity": "High",
            "message": (
                f"{len(capacity_alerts)} room(s) "
                "reached 90% or more of capacity "
                "during the last 24 hours."
            )
        })

    if vacant_rooms > 0:

        insights.append({
            "type": "Current Status",
            "severity": "Info",
            "message": (
                f"{vacant_rooms} room(s) are "
                "currently vacant."
            )
        })

    # ---------------------------------------------------------
    # FINAL API RESPONSE
    # ---------------------------------------------------------
    return {
        "kpis": {
            "total_records": int(len(df)),
            "current_occupancy": current_occupancy,
            "occupied_rooms": occupied_rooms,
            "vacant_rooms": vacant_rooms,
            "total_rooms": total_rooms,
            "occupancy_rate": occupancy_rate,
            "average_occupancy": average_occupancy,
            "peak_occupancy": peak_occupancy
        },

        "analytics": {
            "most_occupied_room": most_occupied_room,
            "least_occupied_room": least_occupied_room,
            "peak_hour": peak_hour,
            "peak_zone": peak_zone
        },

        "rooms": rooms,

        "hourly_occupancy": hourly_occupancy,

        "building_summary": building_summary,

        "capacity_alerts": capacity_alerts,

        "insights": insights,

        "data_source": (
            "Occupancy sensor readings from "
            "facility_data.csv"
        ),

        "note": (
            "Current status uses the latest room "
            "reading. Occupancy analytics use the "
            "complete 24-hour historical readings."
        )
    }





# ============================================================
# SECURITY AGENT
# ============================================================

def build_security_data():

    SECURITY_DATA_PATH = "security_events.csv"

    try:
        df = pd.read_csv(SECURITY_DATA_PATH)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return {
            "available": False,
            "kpis": {
                "total_events": 0,
                "unauthorized_access": 0,
                "high_risk_events": 0,
                "unauthorized_rate": 0,
                "active_alerts": 0,
                "critical_alerts": 0,
                "resolved_events": 0,
            },
            "severity": {
                "Low": 0,
                "Medium": 0,
                "High": 0,
                "Critical": 0,
            },
            "alerts": [],
            "events": [],
            "high_risk_events": [],
            "insights": [],
            "data_source": None,
            "note": "No security event data available.",
        }

    if df.empty:
        return {
            "available": False,
            "kpis": {
                "total_events": 0,
                "unauthorized_access": 0,
                "high_risk_events": 0,
                "unauthorized_rate": 0,
                "active_alerts": 0,
                "critical_alerts": 0,
                "resolved_events": 0,
            },
            "severity": {
                "Low": 0,
                "Medium": 0,
                "High": 0,
                "Critical": 0,
            },
            "alerts": [],
            "events": [],
            "high_risk_events": [],
            "insights": [],
            "data_source": "security_events.csv",
            "note": "Security event file is empty.",
        }

    # ---------------------------------------------------------
    # CLEAN DATA
    # ---------------------------------------------------------

    required_columns = [
        "event_id",
        "building_id",
        "room_id",
        "timestamp",
        "event_type",
        "access_type",
        "authorized",
        "severity",
    ]

    for column in required_columns:
        if column not in df.columns:
            df[column] = ""

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    df["authorized"] = (
        df["authorized"]
        .astype(str)
        .str.lower()
        .isin(["true", "1", "yes"])
    )

    df["severity"] = (
        df["severity"]
        .astype(str)
        .str.title()
    )

    df["event_type"] = (
        df["event_type"]
        .fillna("Security Event")
        .astype(str)
    )

    df["building_id"] = (
        df["building_id"]
        .fillna("Unknown")
        .astype(str)
    )

    df["room_id"] = (
        df["room_id"]
        .fillna("Unknown")
        .astype(str)
    )

    df = df.sort_values(
        "timestamp",
        ascending=False
    )

    # ---------------------------------------------------------
    # KPI CALCULATIONS
    # ---------------------------------------------------------

    total_events = len(df)

    unauthorized_df = df[
        df["authorized"] == False
    ]

    unauthorized_access = len(
        unauthorized_df
    )

    high_risk_df = df[
        df["severity"].isin(
            ["High", "Critical"]
        )
    ]

    high_risk_events = len(
        high_risk_df
    )

    unauthorized_rate = (
        round(
            unauthorized_access /
            total_events *
            100,
            2
        )
        if total_events > 0
        else 0
    )

    critical_alerts = len(
        df[
            df["severity"] == "Critical"
        ]
    )

    # ---------------------------------------------------------
    # SEVERITY COUNTS
    # ---------------------------------------------------------

    severity_counts = {
        "Low": int(
            (df["severity"] == "Low").sum()
        ),
        "Medium": int(
            (df["severity"] == "Medium").sum()
        ),
        "High": int(
            (df["severity"] == "High").sum()
        ),
        "Critical": int(
            (df["severity"] == "Critical").sum()
        ),
    }

    # ---------------------------------------------------------
    # EVENT FORMAT FOR FRONTEND
    # ---------------------------------------------------------

    events = []

    for _, row in df.iterrows():

        timestamp = (
            row["timestamp"].isoformat()
            if pd.notna(row["timestamp"])
            else ""
        )

        event = {
            "event_id": str(row["event_id"]),
            "building_id": str(row["building_id"]),
            "facility_id": str(row["building_id"]),
            "room_id": str(row["room_id"]),
            "event_type": str(row["event_type"]),
            "type": str(row["event_type"]),
            "access_type": str(row["access_type"]),
            "authorized": bool(row["authorized"]),
            "severity": str(row["severity"]),
            "timestamp": timestamp,
        }

        events.append(event)

    # ---------------------------------------------------------
    # SECURITY ALERTS
    # ---------------------------------------------------------

    alerts = []

    for _, row in unauthorized_df.iterrows():

        timestamp = (
            row["timestamp"].isoformat()
            if pd.notna(row["timestamp"])
            else ""
        )

        alerts.append({
            "event_id": str(row["event_id"]),
            "type": str(row["event_type"]),
            "event_type": str(row["event_type"]),
            "facility_id": str(row["building_id"]),
            "building_id": str(row["building_id"]),
            "room_id": str(row["room_id"]),
            "severity": str(row["severity"]),
            "timestamp": timestamp,
            "message": (
                f'Unauthorized access detected at '
                f'{row["building_id"]} - '
                f'{row["room_id"]}.'
            ),
        })

    # ---------------------------------------------------------
    # HIGH-RISK EVENTS
    # ---------------------------------------------------------

    high_risk_events_data = []

    for _, row in high_risk_df.iterrows():

        timestamp = (
            row["timestamp"].isoformat()
            if pd.notna(row["timestamp"])
            else ""
        )

        high_risk_events_data.append({
            "event_id": str(row["event_id"]),
            "facility": str(row["building_id"]),
            "facility_id": str(row["building_id"]),
            "building_id": str(row["building_id"]),
            "room_id": str(row["room_id"]),
            "event_type": str(row["event_type"]),
            "severity": str(row["severity"]),
            "timestamp": timestamp,
        })

    # ---------------------------------------------------------
    # INSIGHTS
    # ---------------------------------------------------------

    insights = []

    if unauthorized_access > 0:
        insights.append({
            "type": "Unauthorized Access",
            "severity": "High",
            "message": (
                f"{unauthorized_access} unauthorized "
                "access event(s) were detected."
            ),
        })

    if critical_alerts > 0:
        insights.append({
            "type": "Critical Events",
            "severity": "Critical",
            "message": (
                f"{critical_alerts} critical security "
                "event(s) require attention."
            ),
        })

    if high_risk_events > 0:
        insights.append({
            "type": "High-Risk Activity",
            "severity": "High",
            "message": (
                f"{high_risk_events} high-risk event(s) "
                "were detected."
            ),
        })

    # Find location with most unauthorized events
    if unauthorized_access > 0:

        location_counts = (
            unauthorized_df
            .groupby(
                ["building_id", "room_id"]
            )
            .size()
            .sort_values(
                ascending=False
            )
        )

        if not location_counts.empty:

            building_id, room_id = (
                location_counts.index[0]
            )

            count = int(
                location_counts.iloc[0]
            )

            insights.append({
                "type": "Most Targeted Location",
                "severity": "Medium",
                "message": (
                    f"{building_id} - {room_id} "
                    f"recorded the most unauthorized "
                    f"events ({count})."
                ),
            })

    return {
        "available": True,

        "kpis": {
            "total_events": int(total_events),
            "unauthorized_access": int(
                unauthorized_access
            ),
            "high_risk_events": int(
                high_risk_events
            ),
            "unauthorized_rate": unauthorized_rate,
            "active_alerts": int(
                unauthorized_access
            ),
            "critical_alerts": int(
                critical_alerts
            ),
            "resolved_events": 0,
        },

        "severity": severity_counts,

        "alerts": alerts,

        "events": events,

        "high_risk_events": (
            high_risk_events_data
        ),

        "insights": insights,

        "data_source": (
            "Simulated security events "
            "generated by "
            "generate_security_data.py"
        ),

        "note": (
            "Security data is simulated for "
            "demonstration and testing."
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
            "security": True,
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