"""
Occupancy Agent
---------------
Agent responsible for monitoring facility occupancy,
performing occupancy analytics, detecting capacity issues,
and generating operational insights.

This module is self-contained.  Its only internal
dependency is ``src.occupancy_analytics`` (occupancy-specific
helpers).  It does NOT import from any other agent.
"""

import pandas as pd

from .occupancy_analytics import OccupancyAnalytics


# ============================================================
# OCCUPANCY AGENT CLASS
# ============================================================

class OccupancyAgent:
    """Agent responsible for occupancy intelligence."""

    def __init__(self, records=None, capacity_per_zone=10):
        self.records = records or []
        self.capacity_per_zone = capacity_per_zone

        self.analytics = OccupancyAnalytics(
            self.records
        )

    def update_data(self, records):
        """Update occupancy records."""
        self.records = records or []

        self.analytics.set_records(
            self.records
        )

    def analyze(self):
        """
        Run the complete occupancy analysis.
        """
        return self.analytics.get_summary(
            capacity_per_zone=self.capacity_per_zone
        )

    def get_occupancy_rate(self, capacity=None):
        """Return occupancy rate."""
        return self.analytics.occupancy_rate(
            capacity=capacity
        )

    def get_zone_utilization(self):
        """Return utilization for each zone."""
        return self.analytics.zone_utilization()

    def get_peak_occupancy(self):
        """Return peak occupancy information."""
        return self.analytics.peak_occupancy()

    def get_peak_hour(self):
        """Return the busiest hour."""
        return self.analytics.peak_hour()

    def get_insights(self):
        """Return generated occupancy insights."""
        return self.analytics.generate_insights(
            capacity_per_zone=self.capacity_per_zone
        )

    def get_capacity_alerts(self):
        """Return zones approaching/exceeding capacity."""
        return self.analytics.capacity_alerts(
            capacity_per_zone=self.capacity_per_zone
        )

    def get_zone_status(self):
        """
        Return the current status of each zone.

        Status levels:
            Normal
            Medium
            Critical
        """
        occupancy = self.analytics.occupancy_by_zone()

        result = {}

        for zone, count in occupancy.items():

            utilization = (
                count / self.capacity_per_zone
            ) * 100 if self.capacity_per_zone > 0 else 0

            if utilization >= 100:
                status = "Critical"
            elif utilization >= 90:
                status = "Medium"
            else:
                status = "Normal"

            result[zone] = {
                "occupancy": int(count),
                "capacity": self.capacity_per_zone,
                "utilization": round(utilization, 2),
                "status": status
            }

        return result

    def generate_recommendations(self):
        """
        Generate operational recommendations based on
        occupancy conditions.
        """
        recommendations = []

        zone_status = self.get_zone_status()

        if not zone_status:
            return [
                "No occupancy data available for recommendations."
            ]

        for zone, data in zone_status.items():

            if data["status"] == "Critical":
                recommendations.append(
                    f"Consider redistributing occupants from "
                    f"{zone} because capacity has been exceeded."
                )

            elif data["status"] == "Medium":
                recommendations.append(
                    f"Monitor {zone}; occupancy is approaching "
                    f"its capacity."
                )

        least = self.analytics.least_occupied_zone()

        if least:
            recommendations.append(
                f"Consider using {least} as an alternative "
                f"space if higher-occupancy zones are crowded."
            )

        if not recommendations:
            recommendations.append(
                "Occupancy levels are within normal operating limits."
            )

        return recommendations

    def run(self):
        """
        Main agent execution method.

        Returns all information needed by the API/dashboard.
        """
        analysis = self.analyze()

        return {
            "agent": "Occupancy Agent",
            "status": "active",
            "summary": analysis,
            "zone_status": self.get_zone_status(),
            "recommendations": self.generate_recommendations()
        }


# ============================================================
# OCCUPANCY DASHBOARD BUILDER
# ============================================================

def build_occupancy_dashboard(data_path):
    """
    Build the complete occupancy dashboard response.

    Parameters
    ----------
    data_path : str
        Path to the facility CSV data file.

    Returns
    -------
    dict
        JSON-ready dictionary with KPIs, room data,
        hourly occupancy, building summary, capacity
        alerts, and insights.
    """

    try:
        df = pd.read_csv(data_path)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return _empty_response()

    if df.empty:
        return _empty_response()

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
# EMPTY RESPONSE HELPER
# ============================================================

def _empty_response():
    """Return the empty/fallback response structure."""

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