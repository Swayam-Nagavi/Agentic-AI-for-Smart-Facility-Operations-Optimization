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
            data.rooms ? data.rooms.length : 0;

        document.getElementById("totalOccupancy").textContent =
            data.kpis?.total_occupancy ?? 0;

        document.getElementById("averageOccupancy").textContent =
            data.kpis?.occupancy_rate ?? 0;

        // Find peak occupancy from room data
        let peakOccupancy = 0;
        let peakRoom = "-";

        if (data.rooms && data.rooms.length > 0) {
            data.rooms.forEach(room => {
                const occupancy = Number(room.occupancy) || 0;

                if (occupancy > peakOccupancy) {
                    peakOccupancy = occupancy;
                    peakRoom = `${room.building_id} - ${room.room_id}`;
                }
            });
        }

        document.getElementById("peakOccupancy").textContent =
            peakOccupancy;

        // -----------------------------
        // OVERVIEW
        // -----------------------------

        const buildingSummary = data.building_summary || [];

        let mostOccupied = "-";
        let leastOccupied = "-";

        if (buildingSummary.length > 0) {

            const sorted = [...buildingSummary].sort(
                (a, b) => b.total_occupancy - a.total_occupancy
            );

            mostOccupied = sorted[0].building_id;
            leastOccupied = sorted[sorted.length - 1].building_id;
        }

        document.getElementById("mostOccupied").textContent =
            mostOccupied;

        document.getElementById("leastOccupied").textContent =
            leastOccupied;

        document.getElementById("peakHour").textContent =
            "-";

        document.getElementById("peakZone").textContent =
            peakRoom;

        // -----------------------------
        // ROOM TABLE
        // -----------------------------

        const zoneTable = document.getElementById("zoneTable");

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

                    let utilization = 0;

                    // Capacity used by the backend agent
                    const capacity = 10;

                    utilization =
                        (occupancy / capacity) * 100;

                    let status = room.status || "Vacant";

                    let statusClass = "normal";

                    if (status === "Medium") {
                        statusClass = "medium";
                    }

                    if (status === "Critical") {
                        statusClass = "critical";
                    }

                    zoneTable.innerHTML += `
                        <tr>
                            <td>
                                ${room.building_id} - ${room.room_id}
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
        // CAPACITY / INSIGHTS
        // -----------------------------

        const alertsContainer =
            document.getElementById("capacityAlerts");

        if (alertsContainer) {

            alertsContainer.innerHTML = "";

            if (!data.insights || data.insights.length === 0) {

                alertsContainer.innerHTML = `
                    <div class="insight">
                        No capacity alerts.
                    </div>
                `;

            } else {

                data.insights.forEach(insight => {

                    alertsContainer.innerHTML += `
                        <div class="alert">
                            <strong>${insight.type || "Occupancy Insight"}</strong>
                            <p>${insight.message}</p>
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

            if (!data.insights || data.insights.length === 0) {

                insightsContainer.innerHTML = `
                    <div class="insight">
                        No occupancy insights available.
                    </div>
                `;

            } else {

                data.insights.forEach(insight => {

                    insightsContainer.innerHTML += `
                        <div class="insight">
                            <strong>${insight.type || "Insight"}</strong>
                            <p>${insight.message}</p>
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

            if (data.insights && data.insights.length > 0) {

                data.insights.forEach(insight => {

                    recommendations.innerHTML += `
                        <div class="recommendation">
                            ${insight.message}
                        </div>
                    `;
                });

            } else {

                recommendations.innerHTML = `
                    <div class="recommendation">
                        Occupancy levels are within normal limits.
                    </div>
                `;
            }
        }

    } catch (error) {

        console.error("Occupancy error:", error);

        document.getElementById("totalRecords").textContent = "-";
        document.getElementById("totalOccupancy").textContent = "-";
        document.getElementById("averageOccupancy").textContent = "-";
        document.getElementById("peakOccupancy").textContent = "-";

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


// Load immediately
loadOccupancy();


// Refresh every 30 seconds
setInterval(loadOccupancy, 30000);