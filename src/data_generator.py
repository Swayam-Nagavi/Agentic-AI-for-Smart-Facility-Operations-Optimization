import random
import csv
from datetime import datetime, timedelta


ROOM_TYPES = ["Office", "Meeting Room", "Server Room"]


def generate_room(building_id, room_id, room_type, hour):

    # Occupancy
    if 8 <= hour < 18:
        occupancy = random.randint(5, 30)
    else:
        occupancy = random.randint(0, 5)

    # Temperature
    if 10 <= hour < 17:
        temperature = random.uniform(26, 32)
    elif 7 <= hour < 10 or 17 <= hour < 20:
        temperature = random.uniform(23, 28)
    else:
        temperature = random.uniform(20, 25)

    # HVAC setpoint
    if room_type == "Server Room":
        hvac_setpoint = 22
    else:
        hvac_setpoint = 24

    # HVAC status
    if temperature > hvac_setpoint or occupancy > 10:
        hvac_status = "ON"
    else:
        hvac_status = "OFF"

    # HVAC energy
    if hvac_status == "ON":
        if temperature > hvac_setpoint:
            hvac_energy = (temperature - hvac_setpoint) * 1.5
        else:
            hvac_energy = 1
    else:
        hvac_energy = 0

    # Occupancy energy
    occupancy_energy = occupancy * 0.1

    # Base energy
    base_energy = 3

    # Total energy
    energy_consumption = (
        base_energy +
        hvac_energy +
        occupancy_energy
    )

    # Small random variation
    energy_consumption += random.uniform(-1, 1)
    energy_consumption = max(
        0,
        round(energy_consumption, 2)
    )

    # Equipment status
    if energy_consumption > 15:
        equipment_status = "Warning"
    else:
        equipment_status = "Normal"

    # Humidity
    if temperature > 28:
        humidity = random.uniform(40, 55)
    else:
        humidity = random.uniform(50, 70)

    return {
        "building_id": building_id,
        "room_id": room_id,
        "room_type": room_type,
        "temperature": round(temperature, 1),
        "humidity": round(humidity, 1),
        "occupancy": occupancy,
        "energy_consumption": energy_consumption,
        "hvac_status": hvac_status,
        "hvac_setpoint": hvac_setpoint,
        "equipment_status": equipment_status,
        "timestamp": ""
    }


def generate_facility_data():

    facility_data = []

    start_time = datetime(
        2026, 8, 30, 0, 0
    )

    # 24 hours with 15-minute intervals
    for interval in range(96):

        current_time = (
            start_time +
            timedelta(minutes=15 * interval)
        )

        hour = current_time.hour

        for building_number in range(1, 4):

            building_id = (
                f"B{building_number:03}"
            )

            for room_number, room_type in enumerate(
                ROOM_TYPES,
                start=1
            ):

                room_id = (
                    f"R{room_number:03}"
                )

                room = generate_room(
                    building_id,
                    room_id,
                    room_type,
                    hour
                )

                room["timestamp"] = (
                    current_time.isoformat()
                )

                facility_data.append(room)

    return facility_data


# Generate the data
data = generate_facility_data()

# Save CSV
with open(
    "facility_data.csv",
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=data[0].keys()
    )

    writer.writeheader()
    writer.writerows(data)

print("Total records:", len(data))
print("Data saved to facility_data.csv")
