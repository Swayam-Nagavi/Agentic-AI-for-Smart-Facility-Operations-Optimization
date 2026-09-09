import pandas as pd


def load_data(filepath="facility_data.csv"):
    df = pd.read_csv(filepath)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def total_energy(df):
    return round(df["energy_consumption"].sum(), 2)


def average_interval_energy(df):
    return round(df["energy_consumption"].mean(), 2)


def energy_by_building(df):
    return (
        df.groupby("building_id")["energy_consumption"]
        .sum()
        .round(2)
    )


def energy_by_room(df):
    return (
        df.groupby(
            ["building_id", "room_id", "room_type"]
        )["energy_consumption"]
        .sum()
        .round(2)
    )


def peak_usage(df):
    row = df.loc[df["energy_consumption"].idxmax()]

    return {
        "building_id": row["building_id"],
        "room_id": row["room_id"],
        "room_type": row["room_type"],
        "energy": round(float(row["energy_consumption"]), 3),
        "timestamp": str(row["timestamp"]),
    }


def add_baseline_comparison(df):
    df = df.copy()

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
    df = add_baseline_comparison(df)

    energy_anomalies = df[
        df["baseline_difference_pct"] > 50
    ].copy()

    equipment_anomalies = df[
        df["equipment_status"] == "Warning"
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
    return (
        df.set_index("timestamp")["energy_consumption"]
        .resample("1h")
        .sum()
        .round(2)
    )


def calculate_energy_distribution(df):
    totals = {
        "HVAC": float(df["hvac_energy"].sum()),
        "Lighting": float(df["lighting_energy"].sum()),
        "Equipment": float(df["equipment_energy"].sum()),
        "Other Systems": float(df["other_energy"].sum()),
    }

    total = sum(totals.values())

    return [
        {
            "category": category,
            "energy": round(value, 2),
            "percentage": round((value / total) * 100, 1) if total else 0,
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
