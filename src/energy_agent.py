def generate_recommendations(df):
    recommendations = []

    # 1. HVAC running in empty rooms.
    empty_hvac = df[
        (df["occupancy"] == 0)
        & (df["hvac_status"] == "ON")
    ]

    if not empty_hvac.empty:
        wasted_hvac = empty_hvac["hvac_energy"].sum()

        recommendations.append({
            "type": "HVAC Scheduling",
            "priority": "Medium",
            "message": (
                f"HVAC operated during {len(empty_hvac)} "
                f"unoccupied 15-minute interval(s), using "
                f"approximately {wasted_hvac:.2f} kWh."
            ),
            "reason": (
                "Cooling an unoccupied room can create "
                "avoidable energy consumption."
            ),
        })

    # 2. High-temperature rooms.
    hot_rooms = df[
        (df["temperature"] > df["hvac_setpoint"] + 1.5)
        & (df["occupancy"] > 0)
    ]

    if not hot_rooms.empty:
        grouped = (
            hot_rooms.groupby(
                ["building_id", "room_id", "room_type"]
            )
            .size()
            .reset_index(name="count")
        )

        for _, row in grouped.head(3).iterrows():
            recommendations.append({
                "type": "Setpoint / HVAC Check",
                "priority": "High",
                "message": (
                    f"{row['building_id']} {row['room_id']} "
                    f"({row['room_type']}) repeatedly exceeded "
                    f"its HVAC setpoint."
                ),
                "reason": (
                    "Temperature above the intended setpoint "
                    "while occupied may indicate cooling demand "
                    "or HVAC performance issues."
                ),
            })

    # 3. Equipment warnings.
    equipment_warnings = df[
        df["equipment_status"] == "Warning"
    ]

    if not equipment_warnings.empty:
        for _, row in equipment_warnings.head(3).iterrows():
            recommendations.append({
                "type": "Equipment Investigation",
                "priority": "High",
                "message": (
                    f"{row['building_id']} {row['room_id']} "
                    f"({row['room_type']}) reported an equipment warning."
                ),
                "reason": (
                    "An equipment warning can indicate abnormal "
                    "operation or an unexpected energy load."
                ),
            })

    # 4. Highest-consuming room.
    room_energy = (
        df.groupby(
            ["building_id", "room_id", "room_type"]
        )["energy_consumption"]
        .sum()
        .sort_values(ascending=False)
    )

    if not room_energy.empty:
        (building, room, room_type), energy = room_energy.index[0], room_energy.iloc[0]

        recommendations.append({
            "type": "High Consumption",
            "priority": "Medium",
            "message": (
                f"{building} {room} ({room_type}) has the "
                f"highest 24-hour consumption at {energy:.2f} kWh."
            ),
            "reason": (
                "The room is the largest energy consumer in "
                "the monitored facility and should be investigated "
                "for HVAC, equipment and operating-schedule optimization."
            ),
        })

    if not recommendations:
        recommendations.append({
            "type": "No Action Required",
            "priority": "Low",
            "message": (
                "No significant optimization opportunity "
                "was detected in the current monitoring period."
            ),
            "reason": (
                "Energy, occupancy, HVAC and equipment patterns "
                "are within the configured monitoring thresholds."
            ),
        })

    return recommendations
