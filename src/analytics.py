import pandas as pd


def load_data(path="facility_data.csv"):
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def total_energy(df):
    return round(df["energy_consumption"].sum(), 2)


def energy_by_building(df):
    return (
        df.groupby("building_id")["energy_consumption"]
        .sum()
        .round(2)
        .sort_values(ascending=False)
    )


def energy_by_room(df):
    return (
        df.groupby(["building_id", "room_id", "room_type"])["energy_consumption"]
        .sum()
        .round(2)
        .sort_values(ascending=False)
    )


def peak_usage(df):
    peak = df.loc[df["energy_consumption"].idxmax()]
    return {
        "timestamp": peak["timestamp"].isoformat(),
        "building_id": peak["building_id"],
        "room_id": peak["room_id"],
        "room_type": peak["room_type"],
        "energy": round(float(peak["energy_consumption"]), 2),
    }


def add_baseline_comparison(df):
    result = df.copy()
    result["baseline"] = (
        result.groupby(["building_id", "room_id"])["energy_consumption"]
        .transform("mean")
        .round(2)
    )
    result["baseline_difference"] = (
        result["energy_consumption"] - result["baseline"]
    ).round(2)
    result["baseline_difference_pct"] = (
        result["baseline_difference"] / result["baseline"] * 100
    ).round(1)
    return result


def detect_anomalies(df):
    result = add_baseline_comparison(df)

    room_mean = result.groupby(
        ["building_id", "room_id"]
    )["energy_consumption"].transform("mean")

    room_std = result.groupby(
        ["building_id", "room_id"]
    )["energy_consumption"].transform("std").fillna(0)

    result["anomaly"] = (
        result["energy_consumption"] > room_mean + (2 * room_std)
    )

    return result[result["anomaly"]].sort_values(
        "energy_consumption", ascending=False
    )


def hourly_energy(df):
    return (
        df.set_index("timestamp")["energy_consumption"]
        .resample("1h")
        .sum()
        .round(2)
    )
