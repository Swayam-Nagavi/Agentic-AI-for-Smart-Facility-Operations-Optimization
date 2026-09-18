import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

# Simulated security-event generator for the FacilityOps AI project.
# Output: security_events.csv in the project root.

random.seed(42)

output_file = Path("security_events.csv")

buildings = {
    "B001": ["R001", "R002", "R003"],
    "B002": ["R004", "R005", "R006"],
    "B003": ["R007", "R008", "R009"],
}

event_types_normal = [
    "Access Granted",
    "Door Opened",
    "Door Closed",
    "Badge Scan",
]

event_types_suspicious = [
    "Unauthorized Access",
    "Invalid Badge",
    "Door Forced",
    "Tailgating Detected",
    "Door Held Open",
]

rows = []
event_id = 1

# Generate normal activity across a 24-hour period.
base_time = datetime(2026, 8, 28, 0, 0)

for _ in range(52):
    building_id = random.choice(list(buildings))
    room_id = random.choice(buildings[building_id])

    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    timestamp = base_time + timedelta(hours=hour, minutes=minute)

    # More authorized activity during working hours.
    if 8 <= hour <= 18:
        authorized = True
        event_type = random.choice(event_types_normal)
        severity = "Low"
        access_type = "Authorized"
    else:
        # Mostly normal, but some suspicious night activity.
        if random.random() < 0.25:
            authorized = False
            event_type = random.choice(event_types_suspicious)
            access_type = "Unauthorized"
            severity = random.choice(["Medium", "High"])
        else:
            authorized = True
            event_type = random.choice(event_types_normal)
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

# Add deliberate repeated unauthorized attempts so the dashboard
# has meaningful high-risk/repeated-event patterns.
for building_id, room_id in [
    ("B001", "R002"),
    ("B002", "R005"),
    ("B003", "R008"),
]:
    start = base_time.replace(hour=2, minute=random.randint(0, 30))

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

# Add a few explicit critical events.
critical_events = [
    ("B001", "R003", 3, 45, "Door Forced"),
    ("B002", "R006", 22, 10, "Tailgating Detected"),
    ("B003", "R009", 1, 20, "Invalid Badge"),
]

for building_id, room_id, hour, minute, event_type in critical_events:
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

rows.sort(key=lambda x: x["timestamp"])

fieldnames = [
    "event_id",
    "building_id",
    "room_id",
    "timestamp",
    "event_type",
    "access_type",
    "authorized",
    "severity",
]

with output_file.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Generated {len(rows)} simulated security events.")
print(f"Created: {output_file.resolve()}")
print("Data is simulated and intended for the FacilityOps Security Agent dashboard.")
