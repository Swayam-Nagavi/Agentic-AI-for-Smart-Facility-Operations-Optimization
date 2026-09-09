from pathlib import Path

import pandas as pd

from src.health_scoring import (
    calculate_health_score,
    health_category,
    maintenance_priority,
)

from src.future_condition_model import (
    build_features,
    load_future_condition_model,
    predict_future_condition,
)


FACILITY_DATA_PATH = Path(
    "facility_data.csv"
)


def _condition_risk(row):

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


    return round(
        max(
            0.0,
            min(100.0, risk)
        ),
        1
    )


def _maintenance_plan(score):

    if score < 30:
        return (
            "Immediate inspection",
            "Within 24 hours",
        )

    if score < 50:
        return (
            "Schedule inspection",
            "Within 7 days",
        )

    if score < 65:
        return (
            "Monitor condition",
            "Next maintenance cycle",
        )

    return (
        None,
        "No maintenance required",
    )


def _latest_room_data(df):

    data = df.copy()

    data["timestamp"] = pd.to_datetime(
        data["timestamp"],
        errors="coerce",
    )

    data = data.dropna(
        subset=[
            "building_id",
            "room_id",
            "timestamp",
        ]
    )

    return (
        data
        .sort_values("timestamp")
        .groupby(
            ["building_id", "room_id"],
            as_index=False,
        )
        .tail(1)
        .copy()
    )


def _prepare_prediction_data(df):

    data = df.copy()

    data["timestamp"] = pd.to_datetime(
        data["timestamp"],
        errors="coerce",
    )

    data = data.sort_values(
        [
            "building_id",
            "room_id",
            "timestamp",
        ]
    )

    return build_features(data)


def analyze_facility_assets(
    data_path=FACILITY_DATA_PATH
):

    path = Path(data_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Facility data not found: {path}"
        )


    df = pd.read_csv(path)


    if df.empty:
        return []


    latest_assets = _latest_room_data(
        df
    )


    prediction_data = (
        _prepare_prediction_data(df)
    )


    model = load_future_condition_model()


    results = []


    for _, row in latest_assets.iterrows():

        asset_id = (
            f"{row['building_id']} - "
            f"{row['room_id']}"
        )


        condition_risk = _condition_risk(
            row
        )


        health_score = (
            calculate_health_score(
                condition_risk
            )
        )


        category = health_category(
            health_score
        )


        priority = maintenance_priority(
            health_score
        )


        (
            maintenance_action,
            maintenance_window,
        ) = _maintenance_plan(
            health_score
        )


        maintenance_required = (
            category in
            ("Warning", "Critical")
        )


        if maintenance_required:

            if maintenance_action is None:
                maintenance_action = (
                    "Schedule inspection"
                )

            recommendation = (
                f"{maintenance_action}: "
                f"review the current room "
                f"equipment condition."
            )

        else:

            recommendation = (
                "Continue normal monitoring."
            )


        matching = prediction_data[
            (
                prediction_data["building_id"]
                == row["building_id"]
            )
            &
            (
                prediction_data["room_id"]
                == row["room_id"]
            )
            &
            (
                prediction_data["timestamp"]
                == row["timestamp"]
            )
        ]


        future_prediction = {
            "prediction": "Stable",
            "probabilities": {},
        }


        if not matching.empty:

            prediction_row = (
                matching.iloc[0]
            )

            future_prediction = (
                predict_future_condition(
                    model,
                    prediction_row
                )
            )


        predicted_condition = (
            future_prediction[
                "prediction"
            ]
        )


        probabilities = (
            future_prediction[
                "probabilities"
            ]
        )


        if predicted_condition == (
            "Deteriorating"
        ):

            prediction_recommendation = (
                "Condition is predicted to "
                "deteriorate in the next "
                "observation. Consider "
                "preventive inspection."
            )

        elif predicted_condition == (
            "Improving"
        ):

            prediction_recommendation = (
                "Condition is predicted to "
                "improve in the next "
                "observation."
            )

        else:

            prediction_recommendation = (
                "Condition is predicted to "
                "remain stable in the next "
                "observation."
            )


        results.append(
            {
                "asset_id": asset_id,

                "building_id": str(
                    row["building_id"]
                ),

                "room_id": str(
                    row["room_id"]
                ),

                "room_type": str(
                    row["room_type"]
                ),

                "equipment_type": "HVAC",

                "fault_detected":
                    maintenance_required,

                "fault_likelihood":
                    condition_risk,

                "maintenance_risk":
                    condition_risk,

                "health_score":
                    health_score,

                "health_category":
                    category,

                "priority":
                    priority,

                "maintenance_due":
                    (
                        maintenance_action
                        if maintenance_required
                        else None
                    ),

                "maintenance_window":
                    (
                        maintenance_window
                        if maintenance_required
                        else
                        "No maintenance required"
                    ),

                "recommendation":
                    recommendation,

                "temperature":
                    round(
                        float(
                            row["temperature"]
                        ),
                        2,
                    ),

                "humidity":
                    round(
                        float(
                            row["humidity"]
                        ),
                        2,
                    ),

                "occupancy":
                    int(
                        row["occupancy"]
                    ),

                "energy_consumption":
                    round(
                        float(
                            row[
                                "energy_consumption"
                            ]
                        ),
                        3,
                    ),

                "hvac_energy":
                    round(
                        float(
                            row["hvac_energy"]
                        ),
                        3,
                    ),

                "hvac_status":
                    str(
                        row["hvac_status"]
                    ),

                "hvac_setpoint":
                    round(
                        float(
                            row["hvac_setpoint"]
                        ),
                        2,
                    ),

                "equipment_status":
                    str(
                        row["equipment_status"]
                    ),

                "timestamp":
                    row[
                        "timestamp"
                    ].isoformat(),

                "future_condition":
                    predicted_condition,

                "future_condition_probabilities":
                    probabilities,

                "prediction_recommendation":
                    prediction_recommendation,

                "prediction_basis":
                    (
                        "Random Forest model trained "
                        "on the facility's historical "
                        "sensor readings to predict "
                        "the next condition state."
                    ),

                "health_basis":
                    (
                        "Health score is derived from "
                        "the current temperature, "
                        "humidity, HVAC condition, "
                        "equipment status, and energy "
                        "readings."
                    ),
            }
        )


    return sorted(
        results,
        key=lambda x: x["health_score"]
    )


def build_maintenance_dashboard(
    data_path=FACILITY_DATA_PATH
):

    assets = analyze_facility_assets(
        data_path
    )


    distribution = {
        "Excellent": 0,
        "Good": 0,
        "Warning": 0,
        "Critical": 0,
    }


    for asset in assets:

        category = asset[
            "health_category"
        ]

        if category in distribution:
            distribution[
                category
            ] += 1


    alerts = [
        asset
        for asset in assets
        if asset["fault_detected"]
    ]


    maintenance_recommendations = [
        asset
        for asset in assets
        if asset["fault_detected"]
    ]


    deteriorating = [
        asset
        for asset in assets
        if asset[
            "future_condition"
        ] == "Deteriorating"
    ]


    improving = [
        asset
        for asset in assets
        if asset[
            "future_condition"
        ] == "Improving"
    ]


    stable = [
        asset
        for asset in assets
        if asset[
            "future_condition"
        ] == "Stable"
    ]


    average_health = (
        sum(
            asset["health_score"]
            for asset in assets
        ) / len(assets)
        if assets
        else 0
    )


    high_risk_assets = [
        asset
        for asset in assets
        if asset["maintenance_risk"] >= 40
    ]


    return {

        "kpis": {

            "assets_monitored":
                len(assets),

            "faults_detected":
                len(alerts),

            "maintenance_recommendations":
                len(
                    maintenance_recommendations
                ),

            "average_health":
                round(
                    average_health,
                    1
                ),

            "high_risk_assets":
                len(high_risk_assets),

            "deteriorating_assets":
                len(deteriorating),

            "improving_assets":
                len(improving),

            "stable_assets":
                len(stable),
        },


        "health_distribution": [

            {
                "category": category,

                "count": count,

                "percentage":
                    round(
                        count /
                        len(assets) *
                        100,
                        1,
                    )
                    if assets
                    else 0,
            }

            for category, count
            in distribution.items()
        ],


        "assets":
            assets,


        "alerts":
            alerts,


        "schedule":
            maintenance_recommendations,


        "prediction_summary": {

            "deteriorating":
                len(deteriorating),

            "improving":
                len(improving),

            "stable":
                len(stable),
        },


        "data_source":
            "Facility sensor data from facility_data.csv",


        "note":
            (
                "The future condition model predicts "
                "whether the next observed equipment "
                "condition is likely to improve, remain "
                "stable, or deteriorate. It does not "
                "predict equipment failure probability "
                "or a failure date."
            ),
    }