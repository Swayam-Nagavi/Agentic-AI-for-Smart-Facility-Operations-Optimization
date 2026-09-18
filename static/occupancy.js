async function loadOccupancy() {
    try {
        const response = await fetch("/api/occupancy");

        if (!response.ok) {
            throw new Error("Failed to load occupancy data");
        }

        const data = await response.json();

        // -----------------------------
        // KPI VALUES
        // -----------------------------

        document.getElementById("totalRecords").textContent =
            data.kpis?.total_records ?? 0;

        document.getElementById("totalOccupancy").textContent =
            data.kpis?.current_occupancy ?? 0;

        document.getElementById("averageOccupancy").textContent =
            data.kpis?.average_occupancy ?? 0;

        document.getElementById("peakOccupancy").textContent =
            data.kpis?.peak_occupancy ?? 0;


        // -----------------------------
        // OVERVIEW
        // -----------------------------

        const analytics = data.analytics || {};

        const mostOccupied =
            analytics.most_occupied_room;

        const leastOccupied =
            analytics.least_occupied_room;

        document.getElementById("mostOccupied").textContent =
            mostOccupied
                ? `${mostOccupied.building_id} - ${mostOccupied.room_id}`
                : "-";

        document.getElementById("leastOccupied").textContent =
            leastOccupied
                ? `${leastOccupied.building_id} - ${leastOccupied.room_id}`
                : "-";

        document.getElementById("peakHour").textContent =
            analytics.peak_hour ?? "-";

        document.getElementById("peakZone").textContent =
            analytics.peak_zone ?? "-";


        // -----------------------------
        // ROOM TABLE
        // -----------------------------

        const zoneTable =
            document.getElementById("zoneTable");

        if (zoneTable) {

            zoneTable.innerHTML = "";

            if (!data.rooms || data.rooms.length === 0) {

                zoneTable.innerHTML = `
                    <tr>
                        <td colspan="4">
                            No occupancy data available.
                        </td>
                    </tr>
                `;

            } else {

                data.rooms.forEach(room => {

                    const occupancy =
                        Number(room.occupancy) || 0;

                    const utilization =
                        Number(room.utilization) || 0;

                    const status =
                        room.status || "Vacant";

                    let statusClass = "normal";

                    if (status === "Vacant") {
                        statusClass = "vacant";
                    } else if (
                        status === "Moderate" ||
                        status === "Near Capacity"
                    ) {
                        statusClass = "medium";
                    } else if (
                        status === "High" ||
                        status === "Over Capacity"
                    ) {
                        statusClass = "critical";
                    }

                    zoneTable.innerHTML += `
                        <tr>
                            <td>
                                ${room.building_id} -
                                ${room.room_id}
                            </td>

                            <td>
                                ${occupancy}
                            </td>

                            <td>
                                ${utilization.toFixed(1)}%
                            </td>

                            <td>
                                <span class="status ${statusClass}">
                                    ${status}
                                </span>
                            </td>
                        </tr>
                    `;
                });
            }
        }


        // -----------------------------
        // 24-HOUR ROOM OCCUPANCY
        // -----------------------------

        renderHourlyOccupancy(
            data.hourly_occupancy || []
        );


        // -----------------------------
        // CAPACITY ALERTS
        // -----------------------------

        const alertsContainer =
            document.getElementById("capacityAlerts");

        if (alertsContainer) {

            alertsContainer.innerHTML = "";

            const alerts =
                data.capacity_alerts || [];

            if (alerts.length === 0) {

                alertsContainer.innerHTML = `
                    <div class="alert">
                        <strong>No Capacity Alerts</strong>
                        <p>
                            No room reached 90% capacity
                            during the last 24 hours.
                        </p>
                    </div>
                `;

            } else {

                alerts.forEach(alert => {

                    alertsContainer.innerHTML += `
                        <div class="alert">
                            <strong>
                                ${alert.severity}
                            </strong>

                            <p>
                                ${alert.message}
                            </p>
                        </div>
                    `;
                });
            }
        }


        // -----------------------------
        // INSIGHTS
        // -----------------------------

        const insightsContainer =
            document.getElementById("insights");

        if (insightsContainer) {

            insightsContainer.innerHTML = "";

            const insights =
                data.insights || [];

            if (insights.length === 0) {

                insightsContainer.innerHTML = `
                    <div class="insight">
                        No occupancy insights available.
                    </div>
                `;

            } else {

                insights.forEach(insight => {

                    insightsContainer.innerHTML += `
                        <div class="insight">
                            <strong>
                                ${insight.type || "Insight"}
                            </strong>

                            <p>
                                ${insight.message}
                            </p>
                        </div>
                    `;
                });
            }
        }


        // -----------------------------
        // RECOMMENDATIONS
        // -----------------------------

        const recommendations =
            document.getElementById("recommendations");

        if (recommendations) {

            recommendations.innerHTML = "";

            const insights =
                data.insights || [];

            if (insights.length > 0) {

                insights.forEach(insight => {

                    recommendations.innerHTML += `
                        <div class="recommendation">
                            ${insight.message}
                        </div>
                    `;

                });

            } else {

                recommendations.innerHTML = `
                    <div class="recommendation">
                        Occupancy levels are within
                        normal limits.
                    </div>
                `;
            }
        }

    } catch (error) {

        console.error(
            "Occupancy error:",
            error
        );

        document.getElementById(
            "totalRecords"
        ).textContent = "-";

        document.getElementById(
            "totalOccupancy"
        ).textContent = "-";

        document.getElementById(
            "averageOccupancy"
        ).textContent = "-";

        document.getElementById(
            "peakOccupancy"
        ).textContent = "-";

        const insights =
            document.getElementById("insights");

        if (insights) {

            insights.innerHTML = `
                <div class="insight">
                    Failed to load occupancy data.
                </div>
            `;
        }
    }
}


// =====================================================
// 24-HOUR OCCUPANCY RENDERING
// =====================================================

function renderHourlyOccupancy(roomData) {

    const container =
        document.getElementById(
            "hourlyOccupancyContainer"
        );

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (
        !roomData ||
        roomData.length === 0
    ) {

        container.innerHTML = `
            <div class="insight">
                No 24-hour occupancy data available.
            </div>
        `;

        return;
    }


    roomData.forEach(room => {

        const card =
            document.createElement("div");

        card.className =
            "hourly-room-card";


        // Room heading

        const title =
            document.createElement("div");

        title.className =
            "hourly-room-title";

        title.innerHTML = `
            <strong>
                ${room.building_id} -
                ${room.room_id}
            </strong>

            <span>
                ${room.room_type || "Room"}
            </span>
        `;


        // Hourly grid

        const grid =
            document.createElement("div");

        grid.className =
            "hourly-grid";


        room.hours.forEach(hourData => {

            const cell =
                document.createElement("div");

            cell.className =
                "hour-cell";


            const occupancy =
                Number(
                    hourData.occupancy
                ) || 0;

            const utilization =
                Number(
                    hourData.utilization
                ) || 0;


            let level = "low";

            if (utilization >= 70) {
                level = "high";
            }
            else if (utilization >= 30) {
                level = "medium";
            }


            cell.innerHTML = `
                <div class="hour-label">
                    ${hourData.hour}
                </div>

                <div
                    class="hour-value ${level}"
                    title="
                        ${room.building_id} -
                        ${room.room_id}
                        | ${hourData.hour}
                        | Occupancy: ${occupancy}
                        | Utilization: ${utilization}%
                    "
                >
                    ${occupancy}
                </div>
            `;

            grid.appendChild(cell);
        });


        card.appendChild(title);
        card.appendChild(grid);

        container.appendChild(card);
    });
}


// =====================================================
// INITIAL LOAD
// =====================================================

loadOccupancy();


// =====================================================
// AUTO REFRESH
// =====================================================

setInterval(
    loadOccupancy,
    30000
);