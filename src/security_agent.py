"""Security dashboard builder.

Facility access monitoring, security-event analysis, unauthorized-access
detection, incident classification, and security alerts, computed from the
security-events data source.
"""

from pathlib import Path

import pandas as pd


# ============================================================
# SECURITY DASHBOARD BUILDER
# ============================================================

def build_security_dashboard(data_path):
    """
    Build the complete security dashboard response.

    Parameters
    ----------
    data_path : str
        Path to the security events data source.

    Returns
    -------
    dict
        JSON-ready dictionary with KPIs, severity counts,
        alerts, events, high-risk events, and insights.
    """

    path = Path(data_path)

    try:
        df = pd.read_csv(path)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return _empty_response(
            data_source="Simulated security event stream (digital twin demo)",
            note="No security event readings are available yet."
        )

    if df.empty:
        return _empty_response(
            data_source="Simulated security event stream (digital twin demo)",
            note="No security event readings are available yet.",
        )

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

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        return _empty_response(
            data_source="Simulated security event stream (digital twin demo)",
            note=(
                "Security event data is missing required field(s): "
                + ", ".join(missing_columns)
                + "."
            ),
        )

    df = df.copy()

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    authorized_text = (
        df["authorized"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    df["authorized_known"] = authorized_text.isin(
        ["true", "1", "yes", "false", "0", "no"]
    )

    df["authorized"] = authorized_text.isin(["true", "1", "yes"])

    df["severity"] = (
        df["severity"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.title()
    )

    df["event_type"] = (
        df["event_type"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df["access_type"] = (
        df["access_type"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df["building_id"] = (
        df["building_id"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df["room_id"] = (
        df["room_id"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df = df.dropna(subset=["timestamp"])

    if df.empty:
        return _empty_response(
            data_source="Simulated security event stream (digital twin demo)",
            note="No valid timestamped security events are available after data cleanup.",
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
        df["authorized_known"]
        & (df["authorized"] == False)
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
        },

        "severity": severity_counts,

        "alerts": alerts,

        "events": events,

        "high_risk_events": (
            high_risk_events_data
        ),

        "insights": insights,

        "data_source": (
            "Simulated security event stream (digital twin demo)"
        ),

        "note": (
            "Security metrics are based on facility access-control events."
        ),

        "metadata": {
            "data_source": "Simulated security event stream (digital twin demo)",
            "total_records": int(total_events),
            "start_timestamp": df["timestamp"].min().isoformat(),
            "end_timestamp": df["timestamp"].max().isoformat(),
            "building_ids": sorted(
                str(value)
                for value in df["building_id"].dropna().unique()
                if str(value)
            ),
        },
    }


# ============================================================
# EMPTY RESPONSE HELPER
# ============================================================

def _empty_response(data_source="Simulated security event stream (digital twin demo)", note=""):
    """Return the empty response structure."""

    return {
        "available": False,
        "kpis": {
            "total_events": 0,
            "unauthorized_access": 0,
            "high_risk_events": 0,
            "unauthorized_rate": 0,
            "active_alerts": 0,
            "critical_alerts": 0,
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
        "data_source": data_source,
        "note": note,
        "metadata": {
            "data_source": data_source,
            "total_records": 0,
            "start_timestamp": None,
            "end_timestamp": None,
            "building_ids": [],
        },
    }
