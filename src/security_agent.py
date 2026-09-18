"""
Security Agent
--------------
Agent responsible for facility access monitoring,
security-event analysis, unauthorized-access detection,
incident classification, and security alerts.

This module is fully self-contained.  It has no
internal dependencies on any other agent or module.
"""

from pathlib import Path

import pandas as pd
from collections import Counter, defaultdict
from datetime import datetime


# ============================================================
# SECURITY AGENT CLASS
# ============================================================

class SecurityAgent:
    """Agent responsible for security intelligence."""

    def __init__(self, events=None):
        self.events = events or []

    def update_events(self, events):
        """Replace the current security events."""
        self.events = events or []

    def _event_type(self, event):
        """Return normalized event type."""
        value = (
            event.get("event_type")
            or event.get("type")
            or event.get("access_type")
            or "Unknown"
        )

        return str(value).strip()

    def _severity(self, event):
        """Return normalized severity."""
        value = event.get("severity", "Low")

        value = str(value).strip().lower()

        severity_map = {
            "low": "Low",
            "medium": "Medium",
            "moderate": "Medium",
            "high": "High",
            "critical": "Critical"
        }

        return severity_map.get(
            value,
            "Low"
        )

    def _timestamp(self, event):
        """Return event timestamp."""
        return event.get("timestamp")

    def _facility(self, event):
        """Return facility identifier."""
        return (
            event.get("facility_id")
            or event.get("building_id")
            or "Unknown"
        )

    def is_unauthorized(self, event):
        """
        Determine whether an event represents
        unauthorized access.
        """
        event_type = self._event_type(event).lower()

        unauthorized_keywords = [
            "unauthorized",
            "unauthorised",
            "access denied",
            "denied",
            "invalid access",
            "failed access",
            "forced entry",
            "intrusion"
        ]

        return any(
            keyword in event_type
            for keyword in unauthorized_keywords
        )

    def detect_unauthorized_access(self):
        """Return all unauthorized access events."""
        return [
            event
            for event in self.events
            if self.is_unauthorized(event)
        ]

    def count_security_events(self):
        """Return total number of security events."""
        return len(self.events)

    def count_unauthorized_access(self):
        """Return number of unauthorized access events."""
        return len(
            self.detect_unauthorized_access()
        )

    def events_by_severity(self):
        """Count security events by severity."""
        counter = Counter()

        for event in self.events:
            counter[
                self._severity(event)
            ] += 1

        return dict(counter)

    def events_by_type(self):
        """Count security events by event type."""
        counter = Counter()

        for event in self.events:
            counter[
                self._event_type(event)
            ] += 1

        return dict(counter)

    def events_by_facility(self):
        """Group events by facility."""
        result = defaultdict(list)

        for event in self.events:
            result[
                self._facility(event)
            ].append(event)

        return dict(result)

    def detect_high_risk_events(self):
        """
        Detect High and Critical security events.
        """
        return [
            event
            for event in self.events
            if self._severity(event) in {
                "High",
                "Critical"
            }
        ]

    def generate_alerts(self):
        """
        Convert suspicious/high-risk events into
        dashboard-ready security alerts.
        """
        alerts = []

        for event in self.events:

            unauthorized = self.is_unauthorized(event)
            severity = self._severity(event)

            if unauthorized or severity in {
                "High",
                "Critical"
            }:

                if unauthorized:
                    alert_type = "Unauthorized Access"
                    message = (
                        "Unauthorized access detected."
                    )
                else:
                    alert_type = "Security Incident"
                    message = (
                        f"{severity}-severity security "
                        f"event detected."
                    )

                alerts.append({
                    "facility_id": self._facility(event),
                    "alert_type": alert_type,
                    "severity": severity,
                    "event_type": self._event_type(event),
                    "timestamp": self._timestamp(event),
                    "message": message
                })

        return alerts

    def detect_repeated_events(self, threshold=3):
        """
        Detect repeated events of the same type.

        Example:
            3 failed access attempts
            -> suspicious repeated activity
        """
        counts = Counter(
            self._event_type(event).lower()
            for event in self.events
        )

        repeated = []

        for event_type, count in counts.items():

            if count >= threshold:
                repeated.append({
                    "event_type": event_type,
                    "count": count,
                    "severity": "Medium",
                    "message": (
                        f"Repeated security activity detected: "
                        f"{event_type} occurred {count} times."
                    )
                })

        return repeated

    def analyze_access_activity(self):
        """
        Analyze overall access activity.
        """
        total = self.count_security_events()
        unauthorized = self.count_unauthorized_access()

        if total == 0:
            unauthorized_rate = 0
        else:
            unauthorized_rate = (
                unauthorized / total
            ) * 100

        return {
            "total_events": total,
            "authorized_or_normal_events": (
                total - unauthorized
            ),
            "unauthorized_events": unauthorized,
            "unauthorized_rate": round(
                unauthorized_rate,
                2
            )
        }

    def generate_insights(self):
        """Generate human-readable security insights."""
        insights = []

        if not self.events:
            return [
                "No security events available."
            ]

        total = self.count_security_events()
        unauthorized = self.count_unauthorized_access()
        high_risk = len(
            self.detect_high_risk_events()
        )

        insights.append(
            f"{total} security events were analyzed."
        )

        if unauthorized > 0:
            insights.append(
                f"{unauthorized} unauthorized access "
                f"event(s) were detected."
            )
        else:
            insights.append(
                "No unauthorized access events were detected."
            )

        if high_risk > 0:
            insights.append(
                f"{high_risk} high-risk security "
                f"event(s) require attention."
            )

        repeated = self.detect_repeated_events()

        for item in repeated:
            insights.append(
                item["message"]
            )

        return insights

    def get_summary(self):
        """Return complete security analysis."""
        return {
            "total_events": self.count_security_events(),
            "unauthorized_access": (
                self.count_unauthorized_access()
            ),
            "events_by_severity": (
                self.events_by_severity()
            ),
            "events_by_type": (
                self.events_by_type()
            ),
            "high_risk_events": (
                self.detect_high_risk_events()
            ),
            "repeated_events": (
                self.detect_repeated_events()
            ),
            "access_analysis": (
                self.analyze_access_activity()
            ),
            "alerts": self.generate_alerts(),
            "insights": self.generate_insights()
        }

    def run(self):
        """
        Main Security Agent execution method.
        """
        return {
            "agent": "Security Agent",
            "status": "active",
            "summary": self.get_summary()
        }


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
            data_source="Live security event stream",
            note="No security event readings are available yet."
        )

    if df.empty:
        return _empty_response(
            data_source="Live security event stream",
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
            data_source="Live security event stream",
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
            data_source="Live security event stream",
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
            "Live security event stream"
        ),

        "note": (
            "Security metrics are based on facility access-control events."
        ),

        "metadata": {
            "data_source": "Live security event stream",
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

def _empty_response(data_source="Live security event stream", note=""):
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
