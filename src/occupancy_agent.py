"""Occupancy dashboard builder.

Monitors facility occupancy from the facility data source, performs
occupancy analytics, detects capacity issues, and generates operational
insights.
"""

from pathlib import Path

import pandas as pd


# ============================================================
# OCCUPANCY DASHBOARD BUILDER
# ============================================================

def _value_or_none(value):
    if pd.isna(value):
        return None

    return value


def _float_or_none(value, digits=2):
    if pd.isna(value):
        return None

    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def _capacity_for_room(df, building_id, room_id):
    if "capacity" not in df.columns:
        return None

    values = df.loc[
        (df["building_id"] == building_id)
        & (df["room_id"] == room_id),
        "capacity",
    ].dropna()

    if values.empty:
        return None

    return float(values.iloc[-1])


def _utilization(occupancy, capacity):
    if capacity is None or pd.isna(capacity) or capacity <= 0:
        return None

    return round(min(float(occupancy) / float(capacity) * 100, 100), 2)


def _status_from_reading_values(occupancy, capacity):
    if occupancy <= 0:
        return "Vacant"

    utilization = _utilization(occupancy, capacity)

    if utilization is None:
        return "Occupied"

    if utilization >= 100:
        return "Over Capacity"
    if utilization >= 90:
        return "Near Capacity"
    if utilization >= 70:
        return "High"
    if utilization >= 30:
        return "Moderate"
    return "Low"


def _build_metadata(df, data_path, has_capacity=False):
    source_name = "Simulated occupancy sensor readings (digital twin demo)"
    source_file = Path(data_path).name if data_path else None

    if df.empty:
        return {
            "data_source": source_name,
            "total_records": 0,
            "building_ids": [],
            "room_count": 0,
            "start_timestamp": None,
            "end_timestamp": None,
            "capacity_from_data": bool(has_capacity),
        }

    timestamps = df["timestamp"].dropna()
    building_ids = sorted(str(value) for value in df["building_id"].dropna().unique())
    room_count = int(
        df[["building_id", "room_id"]]
        .drop_duplicates()
        .shape[0]
    )

    return {
        "data_source": source_name,
        "total_records": int(len(df)),
        "building_ids": building_ids,
        "room_count": room_count,
        "start_timestamp": timestamps.min().isoformat() if not timestamps.empty else None,
        "end_timestamp": timestamps.max().isoformat() if not timestamps.empty else None,
        "capacity_from_data": bool(has_capacity),
    }


def build_occupancy_dashboard(data_path):
    """
    Build the complete occupancy dashboard response from facility readings.

    No display values are invented for missing readings. In particular, missing
    hourly readings are omitted instead of being filled with zero, and latest
    room occupancy is never overwritten by hardcoded baseline staff counts.
    """

    path = Path(data_path)

    try:
        df = pd.read_csv(path)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return _empty_response(
            data_source=path.name,
            note="No usable occupancy data is available yet.",
        )

    if df.empty:
        return _empty_response(
            data_source=path.name,
            note="No occupancy readings are available yet.",
        )

    required_columns = [
        "building_id",
        "room_id",
        "timestamp",
        "occupancy",
    ]

    missing_columns = [column for column in required_columns if column not in df.columns]

    if missing_columns:
        return _empty_response(
            data_source=path.name,
            note=(
                "Occupancy data is missing required field(s): "
                + ", ".join(missing_columns)
                + "."
            ),
        )

    df = df.copy()

    if "room_type" not in df.columns:
        df["room_type"] = "Unknown"

    has_capacity = "capacity" in df.columns

    df["occupancy"] = pd.to_numeric(df["occupancy"], errors="coerce")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    if has_capacity:
        df["capacity"] = pd.to_numeric(df["capacity"], errors="coerce")

    df = df.dropna(
        subset=[
            "building_id",
            "room_id",
            "timestamp",
            "occupancy",
        ]
    )

    if df.empty:
        return _empty_response(
            data_source=path.name,
            note="No valid occupancy readings are available after data cleanup.",
        )

    df["occupancy"] = df["occupancy"].clip(lower=0)
    df = df.sort_values(["building_id", "room_id", "timestamp"]).reset_index(drop=True)
    df["hour"] = df["timestamp"].dt.hour

    metadata = _build_metadata(df, path, has_capacity=has_capacity)

    # ---------------------------------------------------------
    # Hourly occupancy for each room. Only hours present in the
    # data are returned; no missing hour is filled with fake zeroes.
    # ---------------------------------------------------------
    hourly = (
        df.groupby(
            ["building_id", "room_id", "room_type", "hour"],
            as_index=False,
        )["occupancy"]
        .mean()
    )
    hourly["occupancy"] = hourly["occupancy"].round(2)

    room_groups = (
        df[["building_id", "room_id", "room_type"]]
        .drop_duplicates()
        .sort_values(["building_id", "room_id"])
    )

    hourly_occupancy = []

    for _, room in room_groups.iterrows():
        building_id = room["building_id"]
        room_id = room["room_id"]
        room_type = room["room_type"]
        capacity = _capacity_for_room(df, building_id, room_id)

        room_hourly = hourly[
            (hourly["building_id"] == building_id)
            & (hourly["room_id"] == room_id)
        ].sort_values("hour")

        hours = []

        for _, hour_row in room_hourly.iterrows():
            occupancy = float(hour_row["occupancy"])

            hours.append({
                "hour": f"{int(hour_row['hour']):02d}:00",
                "occupancy": round(occupancy, 2),
                "capacity": _float_or_none(capacity, 2),
                "utilization": _utilization(occupancy, capacity),
            })

        hourly_occupancy.append({
            "building_id": str(building_id),
            "room_id": str(room_id),
            "room_type": str(room_type),
            "capacity": _float_or_none(capacity, 2),
            "hours": hours,
        })

    # ---------------------------------------------------------
    # Latest reading for current status. Values remain exactly
    # based on the latest sensor reading for each room.
    # ---------------------------------------------------------
    latest = (
        df.sort_values("timestamp")
        .groupby(["building_id", "room_id"], as_index=False)
        .tail(1)
        .sort_values(["building_id", "room_id"])
        .reset_index(drop=True)
        .copy()
    )

    if has_capacity:
        latest["capacity"] = latest["capacity"].where(latest["capacity"].notna(), None)
    else:
        latest["capacity"] = None

    latest["utilization"] = latest.apply(
        lambda row: _utilization(row["occupancy"], row["capacity"]),
        axis=1,
    )

    latest["status"] = latest.apply(
        lambda row: _status_from_reading_values(row["occupancy"], row["capacity"]),
        axis=1,
    )

    rooms = []

    for _, row in latest.iterrows():
        rooms.append({
            "building_id": str(row["building_id"]),
            "room_id": str(row["room_id"]),
            "room_type": str(row.get("room_type", "Unknown")),
            "occupancy": int(round(float(row["occupancy"]))),
            "capacity": _float_or_none(row["capacity"], 2),
            "utilization": _float_or_none(row["utilization"], 2),
            "status": str(row["status"]),
            "temperature": _float_or_none(row.get("temperature"), 2),
            "humidity": _float_or_none(row.get("humidity"), 2),
            "timestamp": row["timestamp"].isoformat(),
        })

    # ---------------------------------------------------------
    # Current KPIs
    # ---------------------------------------------------------
    total_rooms = len(latest)
    current_occupancy = int(round(float(latest["occupancy"].sum())))
    occupied_rooms = int((latest["occupancy"] > 0).sum())
    vacant_rooms = total_rooms - occupied_rooms

    total_capacity = None
    occupancy_rate = None

    if has_capacity:
        capacity_values = pd.to_numeric(latest["capacity"], errors="coerce").dropna()
        if not capacity_values.empty and capacity_values.sum() > 0:
            total_capacity = float(capacity_values.sum())
            occupancy_rate = round(current_occupancy / total_capacity * 100, 2)

    average_occupancy = round(float(df["occupancy"].mean()), 2)
    peak_row = df.loc[df["occupancy"].idxmax()]
    peak_occupancy = int(round(float(peak_row["occupancy"])))
    peak_zone = f'{peak_row["building_id"]} / {peak_row["room_id"]}'

    hourly_total = df.groupby("hour")["occupancy"].mean()
    peak_hour = f"{int(hourly_total.idxmax()):02d}:00" if not hourly_total.empty else None

    room_average = (
        df.groupby(["building_id", "room_id"])["occupancy"]
        .mean()
        .reset_index()
    )

    if not room_average.empty:
        most_row = room_average.loc[room_average["occupancy"].idxmax()]
        least_row = room_average.loc[room_average["occupancy"].idxmin()]

        most_occupied_room = {
            "building_id": str(most_row["building_id"]),
            "room_id": str(most_row["room_id"]),
            "average_occupancy": round(float(most_row["occupancy"]), 2),
        }

        least_occupied_room = {
            "building_id": str(least_row["building_id"]),
            "room_id": str(least_row["room_id"]),
            "average_occupancy": round(float(least_row["occupancy"]), 2),
        }
    else:
        most_occupied_room = None
        least_occupied_room = None

    # ---------------------------------------------------------
    # Building summary
    # ---------------------------------------------------------
    building_summary = []

    for building_id, group in latest.groupby("building_id"):
        building_capacity = None
        building_rate = None

        if has_capacity:
            capacity_values = pd.to_numeric(group["capacity"], errors="coerce").dropna()
            if not capacity_values.empty and capacity_values.sum() > 0:
                building_capacity = float(capacity_values.sum())
                building_rate = round(float(group["occupancy"].sum()) / building_capacity * 100, 2)

        occupied_building_rooms = int((group["occupancy"] > 0).sum())
        total_building_rooms = int(len(group))

        building_summary.append({
            "building_id": str(building_id),
            "current_occupancy": int(round(float(group["occupancy"].sum()))),
            "occupied_rooms": occupied_building_rooms,
            "vacant_rooms": total_building_rooms - occupied_building_rooms,
            "total_rooms": total_building_rooms,
            "total_capacity": _float_or_none(building_capacity, 2),
            "occupancy_rate": _float_or_none(building_rate, 2),
        })

    # ---------------------------------------------------------
    # Capacity alerts. These are emitted only when a capacity
    # column exists in the data source.
    # ---------------------------------------------------------
    capacity_alerts = []

    if has_capacity:
        room_peak = (
            df.groupby(["building_id", "room_id"], as_index=False)
            .agg(
                peak_occupancy=("occupancy", "max"),
                capacity=("capacity", "max"),
            )
            .dropna(subset=["capacity"])
        )

        for _, row in room_peak.iterrows():
            peak_value = float(row["peak_occupancy"])
            capacity = float(row["capacity"])

            if capacity <= 0:
                continue

            utilization = peak_value / capacity * 100

            if utilization >= 100:
                severity = "High"
                message = (
                    f'{row["building_id"]} {row["room_id"]} exceeded '
                    "the configured room capacity."
                )
            elif utilization >= 90:
                severity = "Medium"
                message = (
                    f'{row["building_id"]} {row["room_id"]} reached '
                    f"{round(utilization)}% of the configured room capacity."
                )
            else:
                continue

            capacity_alerts.append({
                "building_id": str(row["building_id"]),
                "room_id": str(row["room_id"]),
                "peak_occupancy": int(round(peak_value)),
                "capacity": round(capacity, 2),
                "utilization": round(utilization, 2),
                "severity": severity,
                "message": message,
            })

    # ---------------------------------------------------------
    # Insights
    # ---------------------------------------------------------
    insights = []

    if peak_occupancy > 0:
        insights.append({
            "type": "Peak Occupancy",
            "severity": "Info",
            "message": f"Peak occupancy was {peak_occupancy} people at {peak_zone}.",
        })

    if peak_hour:
        insights.append({
            "type": "Peak Hour",
            "severity": "Info",
            "message": f"The busiest observed hour was {peak_hour}.",
        })

    if most_occupied_room:
        insights.append({
            "type": "Most Occupied Room",
            "severity": "Info",
            "message": (
                f'{most_occupied_room["building_id"]} '
                f'{most_occupied_room["room_id"]} has the highest average '
                f'occupancy of {most_occupied_room["average_occupancy"]}.'
            ),
        })

    if capacity_alerts:
        insights.append({
            "type": "Capacity",
            "severity": "High",
            "message": (
                f"{len(capacity_alerts)} room(s) reached 90% or more of "
                "the configured room capacity."
            ),
        })

    if vacant_rooms > 0:
        insights.append({
            "type": "Current Status",
            "severity": "Info",
            "message": f"{vacant_rooms} room(s) are vacant in the latest sensor readings.",
        })

    if not has_capacity:
        insights.append({
            "type": "Capacity Data",
            "severity": "Info",
            "message": "Room capacity is unavailable, so utilization and capacity alerts are not calculated.",
        })

    return {
        "available": True,
        "kpis": {
            "total_records": int(len(df)),
            "current_occupancy": current_occupancy,
            "occupied_rooms": occupied_rooms,
            "vacant_rooms": vacant_rooms,
            "total_rooms": total_rooms,
            "total_capacity": _float_or_none(total_capacity, 2),
            "occupancy_rate": _float_or_none(occupancy_rate, 2),
            "average_occupancy": average_occupancy,
            "peak_occupancy": peak_occupancy,
        },
        "analytics": {
            "most_occupied_room": most_occupied_room,
            "least_occupied_room": least_occupied_room,
            "peak_hour": peak_hour,
            "peak_zone": peak_zone,
        },
        "rooms": rooms,
        "hourly_occupancy": hourly_occupancy,
        "building_summary": building_summary,
        "capacity_alerts": capacity_alerts,
        "insights": insights,
        "metadata": metadata,
        "data_source": "Simulated occupancy sensor readings (digital twin demo)",
        "note": (
            "Current status uses the latest room reading, and occupancy "
            "analytics use observed readings only."
        ),
    }


# ============================================================
# EMPTY RESPONSE HELPER
# ============================================================

def _empty_response(data_source="Simulated occupancy sensor readings (digital twin demo)", note=""):
    """Return the empty response structure without fake occupancy rows."""

    return {
        "available": False,
        "kpis": {
            "total_records": 0,
            "current_occupancy": 0,
            "occupied_rooms": 0,
            "vacant_rooms": 0,
            "total_rooms": 0,
            "total_capacity": None,
            "occupancy_rate": None,
            "average_occupancy": 0,
            "peak_occupancy": 0,
        },
        "analytics": {
            "most_occupied_room": None,
            "least_occupied_room": None,
            "peak_hour": None,
            "peak_zone": None,
        },
        "rooms": [],
        "hourly_occupancy": [],
        "building_summary": [],
        "capacity_alerts": [],
        "insights": [],
        "metadata": {
            "data_source": "Simulated occupancy sensor readings (digital twin demo)",
            "total_records": 0,
            "building_ids": [],
            "room_count": 0,
            "start_timestamp": None,
            "end_timestamp": None,
            "capacity_from_data": False,
        },
        "data_source": "Simulated occupancy sensor readings (digital twin demo)",
        "note": note or "No occupancy readings are available yet.",
    }
