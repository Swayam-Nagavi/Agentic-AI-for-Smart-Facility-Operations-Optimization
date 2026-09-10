"""
Security Agent
--------------
Agent responsible for facility access monitoring,
security-event analysis, unauthorized-access detection,
incident classification, and security alerts.
"""

from collections import Counter, defaultdict
from datetime import datetime


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