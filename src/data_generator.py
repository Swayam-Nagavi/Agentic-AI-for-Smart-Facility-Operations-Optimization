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

MAX_VACANT_ROOMS_PER_INTERVAL = 4

# The final dashboard snapshot intentionally contains every occupancy state
# used by the Occupancy Agent: Vacant, Low, Moderate, High, Near Capacity,
# and Over Capacity. Four rooms are vacant and five are occupied, so the
# facility rule is still respected.
LATEST_OCCUPANCY_PATTERN = {
    ("B001", "R001"): 0,   # Vacant
    ("B001", "R002"): 2,   # Low
    ("B001", "R003"): 1,   # Moderate
    ("B002", "R001"): 9,   # High
    ("B002", "R002"): 9,   # Near Capacity
    ("B002", "R003"): 4,   # Over Capacity
    ("B003", "R001"): 0,   # Vacant
    ("B003", "R002"): 0,   # Vacant
    ("B003", "R003"): 0,   # Vacant
}

# Additional scheduled scenarios ensure the historical data contains recurring
# low, moderate, high, near-capacity, over-capacity, and vacant examples.
OCCUPANCY_CASE_SCENARIOS = {
    24: {
        ("B001", "R001"): 2,
        ("B001", "R002"): 5,
        ("B001", "R003"): 1,
        ("B002", "R001"): 9,
        ("B002", "R002"): 9,
        ("B002", "R003"): 4,
        ("B003", "R001"): 0,
        ("B003", "R002"): 0,
        ("B003", "R003"): 0,
    },
    52: {
        ("B001", "R001"): 11,
        ("B001", "R002"): 0,
        ("B001", "R003"): 2,
        ("B002", "R001"): 5,
        ("B002", "R002"): 7,
        ("B002", "R003"): 1,
        ("B003", "R001"): 13,
        ("B003", "R002"): 0,
        ("B003", "R003"): 0,
    },
    95: LATEST_OCCUPANCY_PATTERN,
}


EQUIPMENT_CASE_SCENARIOS = {
    95: {
        ("B001", "R001"): "Normal",
        ("B001", "R002"): "Warning",
        ("B001", "R003"): "Normal",
        ("B002", "R001"): "Warning",
        ("B002", "R002"): "Normal",
        ("B002", "R003"): "Fault",
        ("B003", "R001"): "Normal",
        ("B003", "R002"): "Normal",
        ("B003", "R003"): "Normal",
    }
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


def minimum_operational_occupancy(room_type):
    if room_type == "Server Room":
        return random.choice([1, 1, 2])

    if room_type == "Meeting Room":
        return random.randint(1, 4)

    return random.randint(1, 6)


def occupied_count_for_room(room_type):
    capacity = 3 if room_type == "Server Room" else 12 if room_type == "Office" else 10
    roll = random.random()

    if room_type == "Server Room":
        if roll < 0.55:
            return 1
        if roll < 0.85:
            return 2
        if roll < 0.96:
            return 3
        return 4

    low_min = 1
    low_max = max(1, math.floor(capacity * 0.29))
    moderate_min = max(1, math.ceil(capacity * 0.30))
    moderate_max = max(moderate_min, math.floor(capacity * 0.69))
    high_min = max(1, math.ceil(capacity * 0.70))
    high_max = max(high_min, math.floor(capacity * 0.89))
    near_min = max(1, math.ceil(capacity * 0.90))
    near_max = max(near_min, capacity - 1)

    if roll < 0.18:
        return random.randint(low_min, low_max)
    if roll < 0.62:
        return random.randint(moderate_min, moderate_max)
    if roll < 0.84:
        return random.randint(high_min, high_max)
    if roll < 0.96:
        return random.randint(near_min, near_max)
    return random.randint(capacity + 1, capacity + 2)


def occupancy_for_room(room_type, timestamp):
    hour = timestamp.hour
    weekday = timestamp.weekday() < 5

    if room_type == "Server Room":
        vacant_probability = 0.45 if 8 <= hour < 20 else 0.65

        if random.random() < vacant_probability:
            return 0

        return occupied_count_for_room(room_type)

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

    return occupied_count_for_room(room_type)


def apply_occupancy_case_scenarios(interval, interval_occupancies):
    scenario = OCCUPANCY_CASE_SCENARIOS.get(interval)

    if scenario:
        interval_occupancies.update(scenario)


def enforce_vacancy_limit(interval_occupancies):
    vacant_keys = [
        key
        for key, occupancy in interval_occupancies.items()
        if occupancy <= 0
    ]

    if len(vacant_keys) <= MAX_VACANT_ROOMS_PER_INTERVAL:
        return

    random.shuffle(vacant_keys)
    rooms_to_activate = len(vacant_keys) - MAX_VACANT_ROOMS_PER_INTERVAL

    for key in vacant_keys[:rooms_to_activate]:
        _, room_id = key
        room_type = ROOMS[room_id]["room_type"]
        interval_occupancies[key] = minimum_operational_occupancy(room_type)


def apply_equipment_case_scenarios(interval, record):
    scenario = EQUIPMENT_CASE_SCENARIOS.get(interval, {})
    key = (record["building_id"], record["room_id"])

    if key in scenario:
        record["equipment_status"] = scenario[key]


def apply_latest_sensor_case_scenarios(interval, record):
    if interval != 95:
        return

    key = (record["building_id"], record["room_id"])

    sensor_cases = {
        ("B001", "R001"): {
            "temperature": 24.0,
            "humidity": 50.0,
            "hvac_status": "OFF",
            "hvac_energy": 0.0,
            "lighting_energy": 0.008,
            "equipment_energy": 0.090,
            "other_energy": 0.015,
        },
        ("B001", "R002"): {
            "temperature": 24.7,
            "humidity": 55.0,
            "hvac_status": "OFF",
            "hvac_energy": 0.0,
            "lighting_energy": 0.010,
            "equipment_energy": 0.080,
            "other_energy": 0.015,
        },
        ("B001", "R003"): {
            "temperature": 22.3,
            "humidity": 54.0,
            "hvac_status": "OFF",
            "hvac_energy": 0.0,
            "lighting_energy": 0.004,
            "equipment_energy": 0.630,
            "other_energy": 0.015,
        },
        ("B002", "R001"): {
            "temperature": 26.3,
            "humidity": 56.0,
            "hvac_status": "ON",
            "hvac_energy": 0.520,
            "lighting_energy": 0.025,
            "equipment_energy": 0.145,
            "other_energy": 0.018,
        },
        ("B002", "R002"): {
            "temperature": 25.3,
            "humidity": 62.0,
            "hvac_status": "ON",
            "hvac_energy": 0.470,
            "lighting_energy": 0.029,
            "equipment_energy": 0.120,
            "other_energy": 0.018,
        },
        ("B002", "R003"): {
            "temperature": 26.0,
            "humidity": 68.0,
            "hvac_status": "ON",
            "hvac_energy": 0.950,
            "lighting_energy": 0.012,
            "equipment_energy": 0.725,
            "other_energy": 0.020,
        },
    }

    updates = sensor_cases.get(key)

    if not updates:
        return

    record.update(updates)
    record["energy_consumption"] = round(
        record["hvac_energy"]
        + record["lighting_energy"]
        + record["equipment_energy"]
        + record["other_energy"],
        3,
    )


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

    equipment_roll = random.random()

    if equipment_roll < 0.003:
        equipment_status = "Fault"
    elif equipment_roll < 0.015:
        equipment_status = "Warning"
    else:
        equipment_status = "Normal"

    return {
        "building_id": building_id,
        "room_id": room_id,
        "room_type": room["room_type"],
        "capacity": room["capacity"],
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

        # Pre-compute occupancies for this interval and enforce the
        # facility-level rule: across the 9 monitored rooms, no more than
        # 4 rooms can be vacant at the same timestamp.
        interval_occupancies = {}
        for building_id in BUILDINGS:
            for room_id in ROOMS:
                key = (building_id, room_id)
                interval_occupancies[key] = occupancy_for_room(ROOMS[room_id]["room_type"], timestamp)

        apply_occupancy_case_scenarios(interval, interval_occupancies)
        enforce_vacancy_limit(interval_occupancies)

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

                apply_equipment_case_scenarios(interval, record)
                apply_latest_sensor_case_scenarios(interval, record)

                previous_temperatures[key] = record["temperature"]
                records.append(record)

    return records


def save_to_csv(records, filename="facility_data.csv"):
    if not records:
        return

    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=records[0].keys(),
            lineterminator="\n",
        )
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
