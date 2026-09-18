from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


MODEL_PATH = Path("models/future_condition_model.pkl")


FEATURE_COLUMNS = [
    "temperature",
    "humidity",
    "occupancy",
    "energy_consumption",
    "hvac_energy",
    "hvac_setpoint",
    "temperature_deviation",
    "energy_change",
    "temperature_change",
    "humidity_change",
]


@lru_cache(maxsize=1)
def load_future_condition_model(
    model_path=MODEL_PATH
):
    path = Path(model_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Future condition model not found: {path}. "
            "Run train_future_condition.py first."
        )

    return joblib.load(path)


def build_features(df):
    data = df.copy()

    data["temperature"] = data["temperature"].astype(float)
    data["humidity"] = data["humidity"].astype(float)
    data["occupancy"] = data["occupancy"].astype(float)
    data["energy_consumption"] = (
        data["energy_consumption"].astype(float)
    )
    data["hvac_energy"] = data["hvac_energy"].astype(float)
    data["hvac_setpoint"] = data["hvac_setpoint"].astype(float)

    data["temperature_deviation"] = (
        data["temperature"]
        - data["hvac_setpoint"]
    ).abs()

    data["energy_change"] = (
        data.groupby(
            ["building_id", "room_id"]
        )["energy_consumption"]
        .diff()
        .fillna(0)
    )

    data["temperature_change"] = (
        data.groupby(
            ["building_id", "room_id"]
        )["temperature"]
        .diff()
        .fillna(0)
    )

    data["humidity_change"] = (
        data.groupby(
            ["building_id", "room_id"]
        )["humidity"]
        .diff()
        .fillna(0)
    )

    return data


def predict_future_condition(
    model,
    row
):
    values = [
        float(row[column])
        for column in FEATURE_COLUMNS
    ]

    features = pd.DataFrame(
        [values],
        columns=FEATURE_COLUMNS,
    )
    probabilities = {}

    if hasattr(model, "predict_proba"):
        probability_values = model.predict_proba(features)[0]
        prediction = model.classes_[np.argmax(probability_values)]

        for label, probability in zip(
            model.classes_,
            probability_values
        ):
            probabilities[str(label)] = round(
                float(probability) * 100,
                1
            )
    else:
        prediction = model.predict(features)[0]

    return {
        "prediction": str(prediction),
        "probabilities": probabilities,
    }