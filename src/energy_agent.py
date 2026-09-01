from analytics import energy_by_building, detect_anomalies


def generate_recommendations(df):
    recommendations = []
    anomalies = detect_anomalies(df)

    if not anomalies.empty:
        for _, row in anomalies.head(3).iterrows():
            recommendations.append({
                "priority": "High",
                "type": "High Consumption",
                "message": (
                    f"Investigate {row['building_id']} {row['room_id']} "
                    f"because energy reached {row['energy_consumption']:.2f} kWh, "
                    f"above its baseline of {row['baseline']:.2f} kWh."
                ),
                "reason": "Energy usage is significantly above the room baseline.",
            })

    hvac_when_empty = df[
        (df["hvac_status"] == "ON") & (df["occupancy"] == 0)
    ]

    if not hvac_when_empty.empty:
        recommendations.append({
            "priority": "Medium",
            "type": "HVAC Scheduling",
            "message": (
                f"Review HVAC scheduling for {len(hvac_when_empty)} "
                "intervals where HVAC ran with zero occupancy."
            ),
            "reason": "HVAC operation during empty periods can create avoidable consumption.",
        })

    occupied_hot = df[
        (df["occupancy"] > 10)
        & (df["temperature"] > df["hvac_setpoint"] + 2)
    ]

    if not occupied_hot.empty:
        recommendations.append({
            "priority": "Medium",
            "type": "Setpoint Adjustment",
            "message": (
                "Review HVAC setpoints in occupied rooms where temperature "
                "is more than 2°C above the target."
            ),
            "reason": "A large temperature gap indicates inefficient HVAC operation.",
        })

    building_energy = energy_by_building(df)

    if (
        len(building_energy) > 1
        and building_energy.iloc[0] > building_energy.iloc[-1] * 1.25
    ):
        recommendations.append({
            "priority": "Medium",
            "type": "Building Comparison",
            "message": (
                f"Investigate {building_energy.index[0]}, which consumes "
                f"substantially more energy than {building_energy.index[-1]}."
            ),
            "reason": "The building-level energy difference is larger than expected.",
        })

    if not recommendations:
        recommendations.append({
            "priority": "Low",
            "type": "No Action Required",
            "message": "Energy usage is within the detected normal operating range.",
            "reason": "No significant anomaly or inefficient operating pattern was detected.",
        })

    return recommendations
