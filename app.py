from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from src.csv_data_manager import ensure_facility_csv, ensure_security_csv
from src.energy_agent import build_energy_dashboard
from src.maintenance_agent import build_maintenance_dashboard
from src.occupancy_agent import build_occupancy_dashboard
from src.security_agent import build_security_dashboard


BASE_DIR = Path(__file__).resolve().parent
FACILITY_DATA_PATH = BASE_DIR / "facility_data.csv"
SECURITY_DATA_PATH = BASE_DIR / "security_events.csv"

app = Flask(__name__, static_folder="static")


# ============================================================
# DASHBOARD DATA BUILDERS
# ============================================================

def build_dashboard_data():
    """Build the energy dashboard from facility_data.csv.

    If the CSV has no usable rows, create the CSV data first and then read it.
    """

    ensure_facility_csv(FACILITY_DATA_PATH)
    return build_energy_dashboard(FACILITY_DATA_PATH)


def build_occupancy_data():
    """Build the occupancy dashboard from facility_data.csv.

    If the CSV has no usable rows, create the CSV data first and then read it.
    """

    ensure_facility_csv(FACILITY_DATA_PATH)
    return build_occupancy_dashboard(FACILITY_DATA_PATH)


def build_maintenance_data():
    """Build the maintenance dashboard from facility_data.csv.

    If the CSV has no usable rows, create the CSV data first and then read it.
    """

    ensure_facility_csv(FACILITY_DATA_PATH)
    return build_maintenance_dashboard(FACILITY_DATA_PATH)


def build_security_data():
    """Build the security dashboard from security_events.csv.

    If the CSV has no usable rows, create the CSV data first and then read it.
    """

    ensure_security_csv(SECURITY_DATA_PATH, FACILITY_DATA_PATH)
    return build_security_dashboard(SECURITY_DATA_PATH)


# ============================================================
# API ROUTES
# ============================================================

@app.route("/api/dashboard")
def dashboard_api():
    return jsonify(build_dashboard_data())


@app.route("/api/maintenance/dashboard")
def maintenance_dashboard_api():
    return jsonify(build_maintenance_data())


@app.route("/api/occupancy")
def occupancy_api():
    return jsonify(build_occupancy_data())


@app.route("/api/occupancy/insights")
def occupancy_insights_api():
    data = build_occupancy_data()

    return jsonify({
        "insights": data.get("insights", []),
        "kpis": data.get("kpis", {}),
        "data_source": data.get("data_source"),
        "note": data.get("note"),
    })


@app.route("/api/occupancy/rooms")
def occupancy_rooms_api():
    data = build_occupancy_data()

    return jsonify({
        "rooms": data.get("rooms", []),
        "data_source": data.get("data_source"),
    })


@app.route("/api/security")
def security_api():
    return jsonify(build_security_data())


@app.route("/api/security/alerts")
def security_alerts_api():
    data = build_security_data()
    kpis = data.get("kpis", {})

    return jsonify({
        "alerts": data.get("alerts", []),
        "active_alerts": kpis.get("active_alerts", 0),
        "critical_alerts": kpis.get("critical_alerts", 0),
        "data_source": data.get("data_source"),
    })


@app.route("/api/health")
def health_check():
    return jsonify({
        "status": "ok",
        "agents": {
            "energy": True,
            "maintenance": True,
            "occupancy": True,
            "security": True,
        },
        "data_sources": {
            "facility": str(FACILITY_DATA_PATH.name),
            "security": str(SECURITY_DATA_PATH.name),
        },
    })


# ============================================================
# PAGE ROUTES
# ============================================================

@app.route("/")
def home():
    return send_from_directory("static", "index.html")


@app.route("/maintenance.html")
def maintenance_page():
    return send_from_directory("static", "maintenance.html")


@app.route("/occupancy.html")
def occupancy_page():
    return send_from_directory("static", "occupancy.html")


@app.route("/security.html")
def security_page():
    return send_from_directory("static", "security.html")


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
    )
