"""Security-event CSV generator.

The dashboards can auto-create ``security_events.csv`` when it is missing or
empty. The dashboard still reads only CSV rows; this module is responsible only
for writing those rows to disk first.
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


SECURITY_FIELDNAMES = [
    "event_id",
    "building_id",
    "room_id",
    "timestamp",
    "event_type",
    "access_type",
    "authorized",
    "severity",
]

DEFAULT_BUILDING_ROOMS = {
    "B001": ["R001", "R002", "R003"],
    "B002": ["R001", "R002", "R003"],
    "B003": ["R001", "R002", "R003"],
}

NORMAL_EVENT_TYPES = [
    "Access Granted",
    "Door Opened",
    "Door Closed",
    "Badge Scan",
]

SUSPICIOUS_EVENT_TYPES = [
    "Unauthorized Access",
    "Invalid Badge",
    "Door Forced",
    "Tailgating Detected",
    "Door Held Open",
]


def _normalise_building_rooms(building_rooms=None):
    rooms = building_rooms or DEFAULT_BUILDING_ROOMS

    normalised = {
        str(building_id): [str(room_id) for room_id in room_ids]
        for building_id, room_ids in rooms.items()
        if room_ids
    }

    return normalised or DEFAULT_BUILDING_ROOMS


def generate_security_events(
    building_rooms=None,
    start_time=None,
    event_count=52,
    seed=42,
):
    """Generate security-event rows ready to be written to CSV."""

    rng = random.Random(seed)
    buildings = _normalise_building_rooms(building_rooms)
    base_time = start_time or datetime(2026, 8, 28, 0, 0)

    rows = []
    event_id = 1
    building_ids = list(buildings)

    # Generate normal and suspicious activity across a 24-hour period.
    for _ in range(event_count):
        building_id = rng.choice(building_ids)
        room_id = rng.choice(buildings[building_id])

        hour = rng.randint(0, 23)
        minute = rng.randint(0, 59)
        timestamp = base_time + timedelta(hours=hour, minutes=minute)

        if 8 <= hour <= 18:
            authorized = True
            event_type = rng.choice(NORMAL_EVENT_TYPES)
            severity = "Low"
            access_type = "Authorized"
        elif rng.random() < 0.25:
            authorized = False
            event_type = rng.choice(SUSPICIOUS_EVENT_TYPES)
            access_type = "Unauthorized"
            severity = rng.choice(["Medium", "High"])
        else:
            authorized = True
            event_type = rng.choice(NORMAL_EVENT_TYPES)
            access_type = "Authorized"
            severity = "Low"

        rows.append({
            "event_id": f"SEC{event_id:04d}",
            "building_id": building_id,
            "room_id": room_id,
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": event_type,
            "access_type": access_type,
            "authorized": authorized,
            "severity": severity,
        })
        event_id += 1

    # Add repeated unauthorized attempts against real building-room combinations.
    target_pairs = []
    for building_id in building_ids[:3]:
        room_ids = buildings[building_id]
        room_id = room_ids[1] if len(room_ids) > 1 else room_ids[0]
        target_pairs.append((building_id, room_id))

    for building_id, room_id in target_pairs:
        start = base_time.replace(hour=2, minute=rng.randint(0, 30))

        for attempt in range(3):
            timestamp = start + timedelta(minutes=attempt * 3)

            rows.append({
                "event_id": f"SEC{event_id:04d}",
                "building_id": building_id,
                "room_id": room_id,
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "event_type": "Unauthorized Access",
                "access_type": "Unauthorized",
                "authorized": False,
                "severity": "High" if attempt < 2 else "Critical",
            })
            event_id += 1

    # Add explicit critical events to the first three available locations.
    critical_templates = [
        (3, 45, "Door Forced"),
        (22, 10, "Tailgating Detected"),
        (1, 20, "Invalid Badge"),
    ]

    location_pairs = [
        (building_id, room_id)
        for building_id in building_ids
        for room_id in buildings[building_id]
    ]

    for index, (hour, minute, event_type) in enumerate(critical_templates):
        building_id, room_id = location_pairs[index % len(location_pairs)]
        timestamp = base_time.replace(hour=hour, minute=minute)

        rows.append({
            "event_id": f"SEC{event_id:04d}",
            "building_id": building_id,
            "room_id": room_id,
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": event_type,
            "access_type": "Unauthorized",
            "authorized": False,
            "severity": "Critical",
        })
        event_id += 1

    rows.sort(key=lambda row: row["timestamp"])

    return rows


def save_security_events(rows, filename="security_events.csv"):
    """Write generated security-event rows to ``filename``."""

    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=SECURITY_FIELDNAMES,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    return path
