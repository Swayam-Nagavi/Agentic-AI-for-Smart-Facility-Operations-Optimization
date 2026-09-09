from pathlib import Path

import joblib
import pandas as pd


MODEL_PATH = Path("models/maintenance_fault_model.joblib")

_model = None


def _load_model():
    global _model

    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Maintenance model not found: {MODEL_PATH}"
            )

        _model = joblib.load(MODEL_PATH)

    return _model


def _prepare_input(sensor_data):
    model = _load_model()

    if isinstance(sensor_data, pd.Series):
        sensor_data = sensor_data.to_dict()

    if not isinstance(sensor_data, dict):
        raise TypeError(
            "sensor_data must be a dictionary or pandas Series."
        )

    feature_names = getattr(
        model,
        "feature_names_in_",
        None,
    )

    if feature_names is None:
        raise ValueError(
            "The trained maintenance model does not contain "
            "feature names."
        )

    row = {}

    for feature in feature_names:
        value = sensor_data.get(feature)

        if value is None:
            raise ValueError(
                f"Missing required sensor feature: {feature}"
            )

        try:
            row[feature] = float(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"Invalid numeric value for sensor feature: {feature}"
            )

    return pd.DataFrame(
        [row],
        columns=feature_names,
    )


def _prepare_batch(sensor_data):
    """
    Prepare multiple HVAC observations for one batch prediction.
    """

    model = _load_model()

    feature_names = getattr(
        model,
        "feature_names_in_",
        None,
    )

    if feature_names is None:
        raise ValueError(
            "The trained maintenance model does not contain "
            "feature names."
        )

    if isinstance(sensor_data, pd.DataFrame):

        data = sensor_data.copy()

    elif isinstance(sensor_data, list):

        data = pd.DataFrame(sensor_data)

    else:
        raise TypeError(
            "sensor_data must be a pandas DataFrame or list of dictionaries."
        )

    if data.empty:
        return pd.DataFrame(
            columns=feature_names
        )

    prepared = pd.DataFrame(index=data.index)

    for feature in feature_names:

        if feature not in data.columns:
            raise ValueError(
                f"Missing required sensor feature: {feature}"
            )

        prepared[feature] = pd.to_numeric(
            data[feature],
            errors="coerce",
        )

    if prepared.isna().any().any():
        invalid_columns = prepared.columns[
            prepared.isna().any()
        ].tolist()

        raise ValueError(
            "Invalid or missing numeric values in sensor features: "
            + ", ".join(invalid_columns)
        )

    return prepared


def predict_fault_likelihood(sensor_data):
    """
    Detect the likelihood that the current HVAC observation
    belongs to a faulted operating condition.

    This is current fault detection, not future failure prediction.
    """

    model = _load_model()

    features = _prepare_input(sensor_data)

    probabilities = model.predict_proba(
        features
    )

    classes = list(model.classes_)

    if 1 not in classes:
        return 0.0

    fault_index = classes.index(1)

    return round(
        float(
            probabilities[0][fault_index]
        ) * 100.0,
        1,
    )


def predict_fault_likelihood_batch(sensor_data):
    """
    Calculate current HVAC fault likelihood for multiple
    observations in a single model call.

    Returns a list of percentages in the same order
    as the supplied observations.

    This is current fault detection, not future failure prediction.
    """

    model = _load_model()

    features = _prepare_batch(sensor_data)

    if features.empty:
        return []

    probabilities = model.predict_proba(
        features
    )

    classes = list(model.classes_)

    if 1 not in classes:
        return [0.0] * len(features)

    fault_index = classes.index(1)

    return [
        round(
            float(probabilities[i][fault_index]) * 100.0,
            1,
        )
        for i in range(len(features))
    ]


def predict_fault(sensor_data):
    """
    Return the model's current fault classification.
    """

    model = _load_model()

    features = _prepare_input(sensor_data)

    prediction = model.predict(features)[0]

    return bool(prediction)


def model_features():
    """
    Return the sensor features expected by the trained model.
    """

    model = _load_model()

    feature_names = getattr(
        model,
        "feature_names_in_",
        None,
    )

    if feature_names is None:
        raise ValueError(
            "The trained maintenance model does not contain "
            "feature names."
        )

    return list(feature_names)