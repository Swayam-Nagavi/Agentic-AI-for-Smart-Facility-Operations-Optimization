"""
Occupancy Analytics
-------------------
Provides calculations and analysis for facility occupancy data.

This module does not require ML training. It uses statistical analysis,
thresholds, aggregation, and historical patterns.
"""

from collections import defaultdict
from datetime import datetime
from statistics import mean


class OccupancyAnalytics:
    """Analytics engine for occupancy data."""

    def __init__(self, records=None):
        self.records = records or []

    def set_records(self, records):
        """Replace the current occupancy records."""
        self.records = records or []

    def _get_occupancy(self, record):
        """
        Extract occupancy from a record.

        Supports the existing facility-data format:
        {
            "occupancy": 4
        }

        Also supports:
        {
            "occupancy_count": 4
        }
        """
        value = record.get("occupancy")

        if value is None:
            value = record.get("occupancy_count")

        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _get_zone(self, record):
        """Return the best available zone identifier."""
        return (
            record.get("zone")
            or record.get("room_id")
            or record.get("room_type")
            or record.get("building_id")
            or "Unknown"
        )

    def _get_timestamp(self, record):
        """Extract timestamp from a record."""
        return record.get("timestamp")

    def total_occupancy(self):
        """Return the total current/recorded occupancy."""
        if not self.records:
            return 0

        return sum(self._get_occupancy(record) for record in self.records)

    def average_occupancy(self):
        """Return the average occupancy across records."""
        if not self.records:
            return 0

        values = [
            self._get_occupancy(record)
            for record in self.records
        ]

        return round(mean(values), 2)

    def occupancy_by_zone(self):
        """
        Calculate occupancy grouped by zone/room.

        Returns:
        {
            "R001": 12,
            "R002": 8
        }
        """
        zone_data = defaultdict(float)

        for record in self.records:
            zone = self._get_zone(record)
            zone_data[zone] += self._get_occupancy(record)

        return {
            zone: round(value, 2)
            for zone, value in zone_data.items()
        }

    def zone_utilization(self):
        """
        Calculate relative utilization of each zone.

        The zone with the highest recorded occupancy is treated
        as 100% utilization for relative comparison.
        """
        occupancy = self.occupancy_by_zone()

        if not occupancy:
            return {}

        maximum = max(occupancy.values())

        if maximum == 0:
            return {
                zone: 0
                for zone in occupancy
            }

        return {
            zone: round((value / maximum) * 100, 2)
            for zone, value in occupancy.items()
        }

    def most_occupied_zone(self):
        """Return the zone with the highest occupancy."""
        occupancy = self.occupancy_by_zone()

        if not occupancy:
            return None

        return max(
            occupancy,
            key=occupancy.get
        )

    def least_occupied_zone(self):
        """Return the zone with the lowest occupancy."""
        occupancy = self.occupancy_by_zone()

        if not occupancy:
            return None

        return min(
            occupancy,
            key=occupancy.get
        )

    def peak_occupancy(self):
        """
        Find the record with the highest occupancy.

        Returns a dictionary containing the record and occupancy.
        """
        if not self.records:
            return None

        peak_record = max(
            self.records,
            key=self._get_occupancy
        )

        return {
            "occupancy": self._get_occupancy(peak_record),
            "zone": self._get_zone(peak_record),
            "timestamp": self._get_timestamp(peak_record)
        }

    def occupancy_rate(self, capacity=None):
        """
        Calculate occupancy rate.

        If capacity is supplied:
            rate = occupancy / capacity * 100

        If capacity is not supplied, the maximum recorded occupancy
        is used as the reference capacity.
        """
        current = self.total_occupancy()

        if capacity is None:
            capacity = max(
                [self._get_occupancy(r) for r in self.records],
                default=0
            )

        try:
            capacity = float(capacity)
        except (TypeError, ValueError):
            return 0

        if capacity <= 0:
            return 0

        return round(
            min((current / capacity) * 100, 100),
            2
        )

    def hourly_occupancy(self):
        """
        Aggregate occupancy by hour.

        Returns:
        {
            "08:00": 12,
            "09:00": 27,
            ...
        }
        """
        hourly = defaultdict(list)

        for record in self.records:
            timestamp = self._get_timestamp(record)

            if not timestamp:
                continue

            try:
                dt = datetime.fromisoformat(
                    str(timestamp).replace("Z", "+00:00")
                )

                hour = dt.strftime("%H:00")
                hourly[hour].append(
                    self._get_occupancy(record)
                )

            except (ValueError, TypeError):
                continue

        return {
            hour: round(mean(values), 2)
            for hour, values in sorted(hourly.items())
        }

    def peak_hour(self):
        """Return the hour with the highest average occupancy."""
        hourly = self.hourly_occupancy()

        if not hourly:
            return None

        return max(
            hourly,
            key=hourly.get
        )

    def capacity_alerts(self, capacity_per_zone=10, threshold=0.9):
        """
        Detect zones that are close to or above capacity.

        Example:
            capacity = 10
            threshold = 0.9

        An occupancy of 9 or more generates an alert.
        """
        occupancy = self.occupancy_by_zone()
        alerts = []

        for zone, count in occupancy.items():
            percentage = count / capacity_per_zone

            if percentage >= 1:
                severity = "High"
                message = (
                    f"{zone} has exceeded its capacity "
                    f"with occupancy of {int(count)}."
                )

                alerts.append({
                    "zone": zone,
                    "occupancy": int(count),
                    "capacity": capacity_per_zone,
                    "utilization": round(percentage * 100, 2),
                    "severity": severity,
                    "message": message
                })

            elif percentage >= threshold:
                severity = "Medium"
                message = (
                    f"{zone} is nearing capacity "
                    f"with occupancy of {int(count)}."
                )

                alerts.append({
                    "zone": zone,
                    "occupancy": int(count),
                    "capacity": capacity_per_zone,
                    "utilization": round(percentage * 100, 2),
                    "severity": severity,
                    "message": message
                })

        return alerts

    def generate_insights(self, capacity_per_zone=10):
        """
        Generate human-readable occupancy insights.
        """
        insights = []

        if not self.records:
            return ["No occupancy data available."]

        average = self.average_occupancy()
        most = self.most_occupied_zone()
        least = self.least_occupied_zone()
        peak = self.peak_occupancy()
        peak_hour = self.peak_hour()

        insights.append(
            f"Average recorded occupancy is {average:.1f}."
        )

        if most:
            insights.append(
                f"{most} is currently the most occupied zone."
            )

        if least:
            insights.append(
                f"{least} has the lowest recorded occupancy."
            )

        if peak:
            insights.append(
                f"Peak occupancy was {int(peak['occupancy'])} "
                f"in {peak['zone']}."
            )

        if peak_hour:
            insights.append(
                f"The busiest observed hour is {peak_hour}."
            )

        alerts = self.capacity_alerts(
            capacity_per_zone=capacity_per_zone
        )

        for alert in alerts:
            insights.append(alert["message"])

        return insights

    def get_summary(self, capacity_per_zone=10):
        """Return a complete occupancy analytics summary."""
        return {
            "total_records": len(self.records),
            "total_occupancy": self.total_occupancy(),
            "average_occupancy": self.average_occupancy(),
            "occupancy_by_zone": self.occupancy_by_zone(),
            "zone_utilization": self.zone_utilization(),
            "most_occupied_zone": self.most_occupied_zone(),
            "least_occupied_zone": self.least_occupied_zone(),
            "peak_occupancy": self.peak_occupancy(),
            "peak_hour": self.peak_hour(),
            "capacity_alerts": self.capacity_alerts(
                capacity_per_zone=capacity_per_zone
            ),
            "insights": self.generate_insights(
                capacity_per_zone=capacity_per_zone
            )
        }