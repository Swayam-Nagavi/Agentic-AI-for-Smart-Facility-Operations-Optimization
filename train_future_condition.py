from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from src.future_condition_model import (
    FEATURE_COLUMNS,
    build_features,
)


DATA_PATH = Path("facility_data.csv")
MODEL_PATH = Path(
    "models/future_condition_model.pkl"
)


def calculate_condition_risk(row):
    risk = 0.0

    temperature = float(
        row["temperature"]
    )

    humidity = float(
        row["humidity"]
    )

    occupancy = float(
        row["occupancy"]
    )

    energy = float(
        row["energy_consumption"]
    )

    hvac_energy = float(
        row["hvac_energy"]
    )

    hvac_status = str(
        row["hvac_status"]
    ).upper()

    setpoint = float(
        row["hvac_setpoint"]
    )

    equipment_status = str(
        row["equipment_status"]
    ).lower()


    temperature_deviation = abs(
        temperature - setpoint
    )


    if temperature_deviation > 3:
        risk += 35

    elif temperature_deviation > 2:
        risk += 20

    elif temperature_deviation > 1:
        risk += 10


    if humidity > 65 or humidity < 35:
        risk += 25

    elif humidity > 60 or humidity < 40:
        risk += 10


    if equipment_status == "fault":
        risk += 50

    elif equipment_status == "warning":
        risk += 30


    if (
        hvac_status == "ON"
        and occupancy > 0
        and hvac_energy <= 0
    ):
        risk += 25


    if energy > 1.30:
        risk += 20

    elif energy > 1.10:
        risk += 10


    return max(
        0.0,
        min(100.0, risk)
    )


def create_target(df):

    data = df.copy()

    data["timestamp"] = pd.to_datetime(
        data["timestamp"]
    )

    data = data.sort_values(
        [
            "building_id",
            "room_id",
            "timestamp",
        ]
    )


    data["current_risk"] = data.apply(
        calculate_condition_risk,
        axis=1
    )


    data["future_risk"] = (
        data.groupby(
            ["building_id", "room_id"]
        )["current_risk"]
        .shift(-1)
    )


    data["risk_change"] = (
        data["future_risk"]
        - data["current_risk"]
    )


    def classify(change):

        if change > 5:
            return "Deteriorating"

        if change < -5:
            return "Improving"

        return "Stable"


    data["future_condition"] = (
        data["risk_change"]
        .apply(classify)
    )


    return data.dropna(
        subset=["future_risk"]
    )


def main():

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )


    df = pd.read_csv(
        DATA_PATH
    )


    df = create_target(df)


    feature_data = build_features(
        df
    )


    for column in FEATURE_COLUMNS:
        feature_data[column] = pd.to_numeric(
            feature_data[column],
            errors="coerce"
        )


    feature_data["target"] = (
        df["future_condition"]
        .values
    )


    feature_data = feature_data.dropna(
        subset=FEATURE_COLUMNS + ["target"]
    )


    X = feature_data[
        FEATURE_COLUMNS
    ]

    y = feature_data[
        "target"
    ]


    print(
        "\nFuture condition classes:"
    )

    print(
        y.value_counts()
    )


    if y.nunique() < 2:
        raise ValueError(
            "The dataset contains only one "
            "future-condition class. The model "
            "needs at least two classes."
        )


    X_train, X_test, y_train, y_test = (
        train_test_split(
            X,
            y,
            test_size=0.20,
            random_state=42,
            stratify=y,
        )
    )


    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )


    model.fit(
        X_train,
        y_train
    )


    predictions = model.predict(
        X_test
    )


    accuracy = accuracy_score(
        y_test,
        predictions
    )


    print(
        f"\nTest accuracy: "
        f"{accuracy * 100:.2f}%"
    )


    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    joblib.dump(
        model,
        MODEL_PATH
    )


    print(
        f"\nModel saved to: "
        f"{MODEL_PATH}"
    )


if __name__ == "__main__":
    main()