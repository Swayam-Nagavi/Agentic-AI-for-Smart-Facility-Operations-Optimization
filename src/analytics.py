from pathlib import Path

import pandas as pd


FACILITY_REQUIRED_COLUMNS = [
    "building_id",
    "room_id",
    "room_type",
    "temperature",
    "humidity",
    "occupancy",
    "energy_consumption",
    "hvac_energy",
    "lighting_energy",
    "equipment_energy",
    "other_energy",
    "hvac_status",
    "hvac_setpoint",
    "equipment_status",
    "timestamp",
]

NUMERIC_COLUMNS = [
    "temperature",
    "humidity",
    "occupancy",
    "energy_consumption",
    "hvac_energy",
    "lighting_energy",
    "equipment_energy",
    "other_energy",
    "hvac_setpoint",
    "capacity",
    "outdoor_temperature",
    "outdoor_humidity",
]


def _empty_facility_frame():
    return pd.DataFrame(columns=FACILITY_REQUIRED_COLUMNS)


def load_data(filepath="facility_data.csv"):
    """
    Load facility readings from CSV without generating replacement data.

    If the file is missing, empty, malformed, or does not contain the
    facility-data columns required by the dashboards, an empty DataFrame is
    returned. This keeps the dashboards honest: they show only CSV-backed rows.
    """

    path = Path(filepath)

    if not path.exists():
        return _empty_facility_frame()

    try:
        df = pd.read_csv(path)
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return _empty_facility_frame()

    if df.empty:
        return _empty_facility_frame()

    missing_required = [
        column
        for column in FACILITY_REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_required:
        return _empty_facility_frame()

    df = df.copy()

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
    )

    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    text_columns = [
        "building_id",
        "room_id",
        "room_type",
        "hvac_status",
        "equipment_status",
    ]

    for column in text_columns:
        df[column] = df[column].astype("string")

    df = df.dropna(
        subset=[
            "building_id",
            "room_id",
            "timestamp",
            "energy_consumption",
        ]
    )

    df = df.sort_values("timestamp").reset_index(drop=True)

    return df


def total_energy(df):
    if df.empty:
        return 0.0

    return round(float(df["energy_consumption"].sum()), 2)


def average_interval_energy(df):
    if df.empty:
        return 0.0

    return round(float(df["energy_consumption"].mean()), 2)


def energy_by_building(df):
    if df.empty:
        return pd.Series(dtype="float64")

    return (
        df.groupby("building_id")["energy_consumption"]
        .sum()
        .round(2)
    )


def energy_by_room(df):
    if df.empty:
        return pd.Series(dtype="float64")

    return (
        df.groupby(
            ["building_id", "room_id", "room_type"]
        )["energy_consumption"]
        .sum()
        .round(2)
    )


def peak_usage(df):
    if df.empty:
        return {
            "building_id": None,
            "room_id": None,
            "room_type": None,
            "energy": 0.0,
            "timestamp": None,
        }

    row = df.loc[df["energy_consumption"].idxmax()]

    return {
        "building_id": row["building_id"],
        "room_id": row["room_id"],
        "room_type": row["room_type"],
        "energy": round(float(row["energy_consumption"]), 3),
        "timestamp": row["timestamp"].isoformat(),
    }


def add_baseline_comparison(df):
    df = df.copy()

    if df.empty:
        df["baseline"] = []
        df["baseline_difference_pct"] = []
        return df

    baseline = (
        df.groupby(["building_id", "room_id"])["energy_consumption"]
        .transform("mean")
    )

    df["baseline"] = baseline.round(3)

    df["baseline_difference_pct"] = (
        (
            df["energy_consumption"] - df["baseline"]
        )
        / df["baseline"].replace(0, pd.NA)
        * 100
    ).round(2)

    return df


def detect_anomalies(df):
    if df.empty:
        return add_baseline_comparison(df)

    df = add_baseline_comparison(df)

    energy_anomalies = df[
        df["baseline_difference_pct"] > 50
    ].copy()

    equipment_anomalies = df[
        df["equipment_status"].astype(str).str.lower() == "warning"
    ].copy()

    anomalies = pd.concat(
        [energy_anomalies, equipment_anomalies],
        ignore_index=True,
    ).drop_duplicates()

    if not anomalies.empty:
        anomalies = anomalies.sort_values(
            "baseline_difference_pct",
            ascending=False,
        )

    return anomalies.head(20)


def hourly_energy(df):
    if df.empty:
        return pd.Series(dtype="float64")

    return (
        df.set_index("timestamp")["energy_consumption"]
        .resample("1h")
        .sum()
        .round(2)
    )


def calculate_energy_distribution(df):
    if df.empty:
        return []

    component_columns = {
        "HVAC": "hvac_energy",
        "Lighting": "lighting_energy",
        "Equipment": "equipment_energy",
        "Other Systems": "other_energy",
    }

    totals = {
        category: float(df[column].sum())
        for category, column in component_columns.items()
        if column in df.columns
    }

    total = sum(totals.values())

    if total <= 0:
        return []

    return [
        {
            "category": category,
            "energy": round(value, 2),
            "percentage": round((value / total) * 100, 1),
        }
        for category, value in totals.items()
    ]


def calculate_summary(df):
    return {
        "total_energy": total_energy(df),
        "average_interval_energy": average_interval_energy(df),
        "peak_usage": peak_usage(df),
        "building_energy": energy_by_building(df),
        "room_energy": energy_by_room(df),
        "anomalies": detect_anomalies(df),
    }
