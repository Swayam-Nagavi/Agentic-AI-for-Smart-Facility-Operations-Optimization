from pathlib import Path
import sys

from flask import Flask, jsonify, send_from_directory

sys.path.append(str(Path(__file__).parent / "src"))

from analytics import (
    load_data,
    total_energy,
    energy_by_building,
    energy_by_room,
    hourly_energy,
    peak_usage,
    detect_anomalies,
)
from energy_agent import generate_recommendations


BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "facility_data.csv"
STATIC_DIR = BASE_DIR / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR))


def build_dashboard_data():
    df = load_data(DATA_FILE)
    anomalies = detect_anomalies(df)

    anomaly_rows = [
        {
            "building": row["building_id"],
            "room": row["room_id"],
            "room_type": row["room_type"],
            "timestamp": row["timestamp"].isoformat(),
            "energy": round(float(row["energy_consumption"]), 2),
            "baseline": round(float(row["baseline"]), 2),
            "above_baseline": round(float(row["baseline_difference_pct"]), 1),
        }
        for _, row in anomalies.iterrows()
    ]

    room_energy = energy_by_room(df)
    rooms = [
        {
            "label": f"{building} - {room} ({room_type})",
            "energy": float(energy),
        }
        for (building, room, room_type), energy in room_energy.items()
    ]

    hourly = hourly_energy(df)

    hourly_data = [
        {
            "time": timestamp.isoformat(),
            "energy": float(energy),
        }
        for timestamp, energy in hourly.items()
    ]

    return {
        "kpis": {
            "total_energy": total_energy(df),
            "average_interval_energy": round(
                float(df["energy_consumption"].mean()), 2
            ),
            "peak_usage": round(float(df["energy_consumption"].max()), 2),
            "anomalies": len(anomalies),
        },
        "building_energy": [
            {"building": building, "energy": float(energy)}
            for building, energy in energy_by_building(df).items()
        ],
        "room_energy": rooms,
        "hourly_energy": hourly_data,
        "peak": peak_usage(df),
        "anomalies": anomaly_rows,
        "recommendations": generate_recommendations(df),
    }


@app.get("/")
def dashboard():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/api/dashboard")
def dashboard_api():
    return jsonify(build_dashboard_data())


if __name__ == "__main__":
    app.run(debug=True)
