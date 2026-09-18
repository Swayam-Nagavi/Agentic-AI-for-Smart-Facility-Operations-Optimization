import csv
import math
import random
from datetime import datetime, timedelta


ROOMS = {
    "R001": {
        "room_type": "Office",
        "capacity": 12,
        "base_load_kw": 0.35,
        "lighting_kw": 0.12,
        "cooling_capacity_kw": 4.5,
        "thermal_factor": 0.85,
    },
    "R002": {
        "room_type": "Meeting Room",
        "capacity": 10,
        "base_load_kw": 0.25,
        "lighting_kw": 0.10,
        "cooling_capacity_kw": 4.0,
        "thermal_factor": 0.75,
    },
    "R003": {
        "room_type": "Server Room",
        "capacity": 3,
        "base_load_kw": 2.50,
        "lighting_kw": 0.03,
        "cooling_capacity_kw": 5.5,
        "thermal_factor": 1.00,
    },
}

BUILDINGS = {
    "B001": {"efficiency": 1.00, "outdoor_offset": 0.0},
    "B002": {"efficiency": 1.08, "outdoor_offset": 0.6},
    "B003": {"efficiency": 0.94, "outdoor_offset": -0.4},
}


def outdoor_conditions(hour):
    temperature = (
        24
        + 4 * math.sin((hour - 7) * math.pi / 12)
        + 1.2 * math.sin((hour - 14) * math.pi / 8)
    )
    temperature += random.gauss(0, 0.5)

    humidity = 72 - max(0, temperature - 24) * 2.2
    humidity += random.gauss(0, 2.0)
    humidity = max(35, min(85, humidity))

    return round(temperature, 2), round(humidity, 2)


def occupancy_for_room(room_type, timestamp):
    hour = timestamp.hour
    weekday = timestamp.weekday() < 5

    if room_type == "Server Room":
        if 8 <= hour < 20:
            return random.choices([0, 1, 2], weights=[0.55, 0.35, 0.10])[0]
        return random.choices([0, 1], weights=[0.85, 0.15])[0]

    # Night / off-peak hours (before 7am or after 8pm)
    if hour < 7 or hour >= 20:
        if room_type == "Meeting Room":
            return 0  # Meeting rooms vacant at night
        # Office: small likelihood of late shift / security / maintenance staff
        if random.random() < 0.25:
            return random.randint(1, 3)
        return 0

    if not weekday:
        probability = 0.15 if 9 <= hour < 17 else 0.03
    else:
        if 8 <= hour < 10:
            probability = 0.55
        elif 10 <= hour < 13:
            probability = 0.75
        elif 13 <= hour < 14:
            probability = 0.45
        elif 14 <= hour < 17:
            probability = 0.70
        elif 17 <= hour < 19:
            probability = 0.35
        else:
            probability = 0.15

    capacity = 12 if room_type == "Office" else 10

    if random.random() > probability:
        return 0

    occupancy = int(random.gauss(capacity * 0.55, capacity * 0.20))
    return max(1, min(capacity, occupancy))


def generate_room(building_id, room_id, timestamp, previous_temperature=None, forced_occupancy=None):
    room = ROOMS[room_id]
    building = BUILDINGS[building_id]

    outdoor_temperature, outdoor_humidity = outdoor_conditions(timestamp.hour)
    outdoor_temperature += building["outdoor_offset"]

    if forced_occupancy is not None:
        occupancy = forced_occupancy
    else:
        occupancy = occupancy_for_room(room["room_type"], timestamp)
    setpoint = 22 if room["room_type"] == "Server Room" else 24

    heat_gain = max(0, outdoor_temperature - setpoint) * 0.035
    occupancy_heat = occupancy * 0.025

    target_temperature = (
        outdoor_temperature * 0.18
        + setpoint * 0.82
        + heat_gain
        + occupancy_heat * room["thermal_factor"]
    )

    if previous_temperature is None:
        previous_temperature = target_temperature

    temperature = (
        previous_temperature * 0.82
        + target_temperature * 0.18
        + random.gauss(0, 0.12)
    )

    hvac_threshold = setpoint + (0.25 if room["room_type"] == "Server Room" else 0.5)
    hvac_status = "ON" if temperature > hvac_threshold else "OFF"

    if hvac_status == "ON":
        temperature_error = max(0, temperature - setpoint)
        cooling_fraction = min(1.0, 0.30 + temperature_error / 5.0)
        hvac_demand_kw = (
            room["cooling_capacity_kw"]
            * cooling_fraction
            * building["efficiency"]
        )
    else:
        hvac_demand_kw = 0.0

    lighting_demand_kw = room["lighting_kw"] * (
        0.25 + 0.75 * occupancy / max(room["capacity"], 1)
    )

    equipment_demand_kw = room["base_load_kw"] + occupancy * 0.025

    # Small auxiliary/other load: networking, controls, pumps, sensors, etc.
    other_demand_kw = random.uniform(0.04, 0.08)

    total_demand_kw = (
        hvac_demand_kw
        + lighting_demand_kw
        + equipment_demand_kw
        + other_demand_kw
    )

    total_demand_kw *= random.uniform(0.97, 1.03)
    total_demand_kw = max(0.05, total_demand_kw)

    # 15 minutes = 0.25 hour, so kWh = kW × 0.25 h.
    interval_hours = 0.25

    hvac_energy = hvac_demand_kw * interval_hours
    lighting_energy = lighting_demand_kw * interval_hours
    equipment_energy = equipment_demand_kw * interval_hours
    other_energy = other_demand_kw * interval_hours

    total_energy = (
        hvac_energy
        + lighting_energy
        + equipment_energy
        + other_energy
    )

    # Keep total and components internally consistent after noise.
    scale = total_demand_kw / (
        hvac_demand_kw
        + lighting_demand_kw
        + equipment_demand_kw
        + other_demand_kw
    )
    hvac_energy *= scale
    lighting_energy *= scale
    equipment_energy *= scale
    other_energy *= scale
    total_energy = (
        hvac_energy
        + lighting_energy
        + equipment_energy
        + other_energy
    )

    indoor_humidity = (
        outdoor_humidity * 0.65
        + 35 * 0.35
        - occupancy * 0.15
        + random.gauss(0, 1.2)
    )
    indoor_humidity = max(35, min(75, indoor_humidity))

    equipment_status = "Warning" if random.random() < 0.008 else "Normal"

    return {
        "building_id": building_id,
        "room_id": room_id,
        "room_type": room["room_type"],
        "temperature": round(temperature, 2),
        "humidity": round(indoor_humidity, 2),
        "occupancy": occupancy,

        # All energy fields are kWh consumed in THIS 15-minute interval.
        "energy_consumption": round(total_energy, 3),
        "hvac_energy": round(hvac_energy, 3),
        "lighting_energy": round(lighting_energy, 3),
        "equipment_energy": round(equipment_energy, 3),
        "other_energy": round(other_energy, 3),

        "hvac_status": hvac_status,
        "hvac_setpoint": setpoint,
        "equipment_status": equipment_status,

        "outdoor_temperature": outdoor_temperature,
        "outdoor_humidity": outdoor_humidity,
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
    }


def generate_facility_data():
    # 24 hours × 4 readings/hour × 3 buildings × 3 rooms = 864 records.
    start_time = datetime(2026, 8, 28, 0, 0, 0)

    records = []
    previous_temperatures = {}

    for interval in range(96):
        timestamp = start_time + timedelta(minutes=15 * interval)

        # Pre-compute occupancies for this interval to guarantee facility occupancy rules:
        # 1. Total facility occupancy is never 0 (some occupancy at all times).
        # 2. Some rooms can be 0 (vacant), but not all rooms.
        interval_occupancies = {}
        for building_id in BUILDINGS:
            for room_id in ROOMS:
                key = (building_id, room_id)
                interval_occupancies[key] = occupancy_for_room(ROOMS[room_id]["room_type"], timestamp)

        # Ensure rule: Total occupancy is never 0 at any time, and at least 2-3 rooms are active
        if sum(interval_occupancies.values()) < 3:
            # Round-the-clock facility monitoring/security/operations in select rooms:
            # B001 - R001 (Operations Desk): 2-3 occupants
            # B002 - R003 (Server Room monitoring): 1 occupant
            # B003 - R001 (Facility Maintenance): 2 occupants
            # The remaining 6 rooms stay at 0 (vacant)
            interval_occupancies[("B001", "R001")] = max(interval_occupancies.get(("B001", "R001"), 0), 2)
            interval_occupancies[("B002", "R003")] = max(interval_occupancies.get(("B002", "R003"), 0), 1)
            interval_occupancies[("B003", "R001")] = max(interval_occupancies.get(("B003", "R001"), 0), 2)

        # Ensure rule: Some rooms can be 0 (never all 9 rooms occupied simultaneously)
        if all(occ > 0 for occ in interval_occupancies.values()):
            interval_occupancies[("B001", "R002")] = 0
            interval_occupancies[("B002", "R002")] = 0

        for building_id in BUILDINGS:
            for room_id in ROOMS:
                key = (building_id, room_id)

                record = generate_room(
                    building_id,
                    room_id,
                    timestamp,
                    previous_temperatures.get(key),
                    forced_occupancy=interval_occupancies[key],
                )

                previous_temperatures[key] = record["temperature"]
                records.append(record)

    return records


def save_to_csv(records, filename="facility_data.csv"):
    if not records:
        return

    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)


if __name__ == "__main__":
    random.seed(42)

    data = generate_facility_data()
    save_to_csv(data)

    print(f"Generated {len(data)} records.")
    print("Sampling interval: 15 minutes")
    print("Energy unit: kWh per 15-minute interval")
    print("Saved to facility_data.csv")
