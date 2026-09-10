"""
Occupancy Agent
---------------
Agent responsible for monitoring facility occupancy,
performing occupancy analytics, detecting capacity issues,
and generating operational insights.
"""

from .occupancy_analytics import OccupancyAnalytics


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