async function loadOccupancy() {
    try {
        const response = await fetch("/api/occupancy");

        if (!response.ok) {
            throw new Error(`Failed to load occupancy data: ${response.status}`);
        }

        const data = await response.json();

        updateKPIs(data.kpis || {});
        updateOverview(data.analytics || {});
        renderRooms(data.rooms || []);
        renderHourlyOccupancy(data.hourly_occupancy || []);
        renderCapacityAlerts(data.capacity_alerts || []);
        renderInsights(data.insights || []);
        renderRecommendations(data.insights || []);
        updateSource(data);
    } catch (error) {
        console.error("Occupancy error:", error);
        showError();
    }
}


function updateKPIs(kpis) {
    setText("totalRecords", kpis.total_records ?? 0);
    setText("totalOccupancy", kpis.current_occupancy ?? 0);
    setText("averageOccupancy", formatNumber(kpis.average_occupancy, 2));
    setText("peakOccupancy", kpis.peak_occupancy ?? 0);
    setText("occupancyRate", kpis.occupancy_rate == null ? "Capacity unavailable" : `${formatNumber(kpis.occupancy_rate, 1)}%`);
}


function updateOverview(analytics) {
    const mostOccupied = analytics.most_occupied_room;
    const leastOccupied = analytics.least_occupied_room;

    setText("mostOccupied", mostOccupied ? `${mostOccupied.building_id} - ${mostOccupied.room_id}` : "-");
    setText("leastOccupied", leastOccupied ? `${leastOccupied.building_id} - ${leastOccupied.room_id}` : "-");
    setText("peakHour", analytics.peak_hour ?? "-");
    setText("peakZone", analytics.peak_zone ?? "-");
}


function renderRooms(rooms) {
    const zoneTable = document.getElementById("zoneTable");

    if (!zoneTable) {
        return;
    }

    if (!rooms.length) {
        zoneTable.innerHTML = `
            <tr>
                <td colspan="6">No occupancy data available.</td>
            </tr>
        `;
        return;
    }

    zoneTable.innerHTML = rooms.map(room => {
        const occupancy = Number(room.occupancy) || 0;
        const utilization = room.utilization == null ? "-" : `${formatNumber(room.utilization, 1)}%`;
        const capacity = room.capacity == null ? "-" : formatNumber(room.capacity, 0);
        const status = room.status || (occupancy > 0 ? "Occupied" : "Vacant");
        const statusClass = statusClassFor(status);

        return `
            <tr>
                <td>${escapeHtml(room.building_id)} - ${escapeHtml(room.room_id)}</td>
                <td>${escapeHtml(room.room_type || "")}</td>
                <td>${occupancy}</td>
                <td>${escapeHtml(capacity)}</td>
                <td>${escapeHtml(utilization)}</td>
                <td><span class="status ${statusClass}">${escapeHtml(status)}</span></td>
            </tr>
        `;
    }).join("");
}


function renderCapacityAlerts(alerts) {
    const alertsContainer = document.getElementById("capacityAlerts");

    if (!alertsContainer) {
        return;
    }

    if (!alerts.length) {
        alertsContainer.innerHTML = `
            <div class="alert">
                <strong>No Capacity Alerts</strong>
                <p>No monitored room reached 90% capacity.</p>
            </div>
        `;
        return;
    }

    alertsContainer.innerHTML = alerts.map(alert => `
        <div class="alert">
            <strong>${escapeHtml(alert.severity || "Alert")}</strong>
            <p>${escapeHtml(alert.message || "")}</p>
        </div>
    `).join("");
}


function renderInsights(insights) {
    const insightsContainer = document.getElementById("insights");

    if (!insightsContainer) {
        return;
    }

    if (!insights.length) {
        insightsContainer.innerHTML = `
            <div class="insight">No occupancy insights were generated from the readings.</div>
        `;
        return;
    }

    insightsContainer.innerHTML = insights.map(insight => `
        <div class="insight">
            <strong>${escapeHtml(insight.type || "Insight")}</strong>
            <p>${escapeHtml(insight.message || "")}</p>
        </div>
    `).join("");
}


function renderRecommendations(insights) {
    const recommendations = document.getElementById("recommendations");

    if (!recommendations) {
        return;
    }

    if (!insights.length) {
        recommendations.innerHTML = `
            <div class="recommendation">No occupancy recommendations available.</div>
        `;
        return;
    }

    recommendations.innerHTML = insights.map(insight => `
        <div class="recommendation">${escapeHtml(insight.message || "")}</div>
    `).join("");
}


// =====================================================
// HOURLY OCCUPANCY RENDERING
// =====================================================

function renderHourlyOccupancy(roomData) {
    const container = document.getElementById("hourlyOccupancyContainer");

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (!roomData.length) {
        container.innerHTML = `
            <div class="insight">No hourly occupancy rows are available in the sensor stream.</div>
        `;
        return;
    }

    roomData.forEach(room => {
        const card = document.createElement("div");
        card.className = "hourly-room-card";

        const title = document.createElement("div");
        title.className = "hourly-room-title";
        title.innerHTML = `
            <strong>${escapeHtml(room.building_id)} - ${escapeHtml(room.room_id)}</strong>
            <span>${escapeHtml(room.room_type || "Room")}</span>
        `;

        const grid = document.createElement("div");
        grid.className = "hourly-grid";

        (room.hours || []).forEach(hourData => {
            const cell = document.createElement("div");
            cell.className = "hour-cell";

            const occupancy = Number(hourData.occupancy) || 0;
            const utilization = hourData.utilization == null ? null : Number(hourData.utilization);
            let level = "low";

            if (utilization !== null && utilization >= 70) {
                level = "high";
            } else if (utilization !== null && utilization >= 30) {
                level = "medium";
            } else if (occupancy > 0) {
                level = "medium";
            }

            const tooltip = [
                `${room.building_id} - ${room.room_id}`,
                hourData.hour,
                `Occupancy: ${occupancy}`,
                hourData.capacity == null ? null : `Capacity: ${formatNumber(hourData.capacity, 0)}`,
                utilization === null ? null : `Utilization: ${formatNumber(utilization, 1)}%`,
            ].filter(Boolean).join(" | ");

            cell.innerHTML = `
                <div class="hour-label">${escapeHtml(hourData.hour)}</div>
                <div class="hour-value ${level}" title="${escapeHtml(tooltip)}">${occupancy}</div>
            `;

            grid.appendChild(cell);
        });

        card.appendChild(title);
        card.appendChild(grid);
        container.appendChild(card);
    });
}


function updateSource(data) {
    const metadata = data.metadata || {};
    setText("dataSource", data.data_source || "Simulated occupancy sensor readings (digital twin demo)");

    const start = metadata.start_timestamp ? formatDate(metadata.start_timestamp) : null;
    const end = metadata.end_timestamp ? formatDate(metadata.end_timestamp) : null;
    setText("dataPeriod", start && end ? `${start} → ${end}` : "No timestamp range available");
    setText("dataNote", data.note || "Only live occupancy readings are shown.");
}


function showError() {
    setText("totalRecords", "-");
    setText("totalOccupancy", "-");
    setText("averageOccupancy", "-");
    setText("peakOccupancy", "-");
    setText("occupancyRate", "-");

    const insights = document.getElementById("insights");

    if (insights) {
        insights.innerHTML = `<div class="insight">Failed to load occupancy data.</div>`;
    }
}


function statusClassFor(status) {
    if (status === "Vacant") {
        return "vacant";
    }

    if (status === "Moderate" || status === "Near Capacity" || status === "Occupied") {
        return "medium";
    }

    if (status === "High" || status === "Over Capacity") {
        return "critical";
    }

    return "normal";
}


function setText(id, value) {
    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}


function formatNumber(value, digits = 1) {
    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "-";
    }

    return number.toFixed(digits);
}


function formatDate(value) {
    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return String(value || "-");
    }

    return date.toLocaleString();
}


function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


loadOccupancy();
setInterval(loadOccupancy, 30000);
