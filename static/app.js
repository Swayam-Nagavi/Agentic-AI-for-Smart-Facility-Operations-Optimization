async function loadDashboard() {
    try {
        const response = await fetch("/api/dashboard");

        if (!response.ok) {
            throw new Error(`Dashboard API request failed: ${response.status}`);
        }

        const data = await response.json();
        const buildingIds = getBuildingIds(data);

        updateDataInfo(data, buildingIds);
        updateKPIs(data.kpis || {});
        renderDistribution(data.energy_distribution || []);
        renderBars("buildingChart", data.building_energy || [], "building");
        renderBars("roomChart", data.room_energy || [], "label");
        renderTrend(data.hourly_energy || [], buildingIds);
        renderPeak(data.peak || {});
        renderAnomalies(data.anomalies || []);
        renderRecommendations(data.recommendations || []);
    } catch (error) {
        console.error("Dashboard error:", error);
        showDashboardError();
    }
}


/* =========================================================
   DATA SOURCE / METADATA
   ========================================================= */

function updateDataInfo(data, buildingIds) {
    const metadata = data.metadata || {};
    const units = data.units || {};

    setText("samplingInterval", units.sampling_interval || metadata.sampling_interval || "Auto-detected");
    setText("energyUnit", units.interval_energy || "kWh / reading");

    const source = data.data_source || metadata.data_source || "live facility sensors";
    const recordCount = Number(metadata.record_count || 0);
    const roomCount = Number(metadata.room_count || 0);
    const buildingCount = buildingIds.length;

    const parts = [
        `${recordCount} record${recordCount === 1 ? "" : "s"}`,
    ];

    if (roomCount) {
        parts.push(`${roomCount} room${roomCount === 1 ? "" : "s"}`);
    }

    if (buildingCount) {
        parts.push(`${buildingCount} building${buildingCount === 1 ? "" : "s"}`);
    }

    setText("datasetSummary", parts.join(" • "));
    setText("dataSource", source);

    const start = metadata.start_timestamp ? formatDate(metadata.start_timestamp) : null;
    const end = metadata.end_timestamp ? formatDate(metadata.end_timestamp) : null;
    setText("monitoringPeriod", start && end ? `${start} → ${end}` : "No timestamp range available");
}


function updateKPIs(kpis) {
    setText("totalEnergy", `${toNumber(kpis.total_energy).toFixed(2)} kWh`);
    setText("estimatedCost", `₹${toNumber(kpis.estimated_cost).toFixed(2)}`);
    setText("efficiencyScore", `${toNumber(kpis.efficiency_score).toFixed(0)}%`);
    setText("potentialSavings", `₹${toNumber(kpis.potential_cost_savings).toFixed(2)}`);
    setText("averageEnergy", `${toNumber(kpis.average_interval_energy).toFixed(2)} kWh / reading`);
    setText("peakEnergy", `${toNumber(kpis.peak_usage).toFixed(2)} kWh / reading`);
    setText("carbonReduction", `${toNumber(kpis.potential_carbon_reduction).toFixed(2)} kg CO₂`);
    setText("anomalyCount", kpis.anomalies ?? 0);
}


/* =========================================================
   ENERGY DISTRIBUTION
   ========================================================= */

function renderDistribution(items) {
    const container = document.getElementById("energyDistribution");

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (!items.length) {
        container.innerHTML = '<p class="muted">No energy distribution data available.</p>';
        return;
    }

    items.forEach(item => {
        const row = document.createElement("div");
        row.className = "distribution-row";

        const top = document.createElement("div");
        top.className = "distribution-top";

        const label = document.createElement("span");
        label.textContent = item.category || "Unknown";

        const percentage = document.createElement("span");
        percentage.textContent = `${toNumber(item.percentage).toFixed(1)}%`;

        top.append(label, percentage);

        const track = document.createElement("div");
        track.className = "distribution-track";

        const bar = document.createElement("div");
        bar.className = "distribution-bar";
        bar.style.width = `${Math.max(0, Math.min(100, toNumber(item.percentage)))}%`;

        track.appendChild(bar);

        const value = document.createElement("div");
        value.className = "distribution-value";
        value.textContent = `${toNumber(item.energy).toFixed(2)} kWh / monitoring period`;

        row.append(top, track, value);
        container.appendChild(row);
    });
}


/* =========================================================
   BUILDING / ROOM BAR CHARTS
   ========================================================= */

function renderBars(elementId, items, labelKey) {
    const container = document.getElementById(elementId);

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (!items.length) {
        container.innerHTML = '<p class="muted">No data available.</p>';
        return;
    }

    const max = Math.max(...items.map(item => toNumber(item.energy)), 1);

    items.forEach(item => {
        const row = document.createElement("div");
        row.className = "bar-row";

        const label = document.createElement("span");
        label.textContent = item[labelKey] || "Unknown";

        const track = document.createElement("div");
        track.className = "bar-track";

        const bar = document.createElement("div");
        bar.className = "bar";
        bar.style.width = `${(toNumber(item.energy) / max) * 100}%`;

        const value = document.createElement("span");
        value.textContent = `${toNumber(item.energy).toFixed(2)} kWh`;

        track.appendChild(bar);
        row.append(label, track, value);
        container.appendChild(row);
    });
}


/* =========================================================
   HOURLY ENERGY TREND
   ========================================================= */

function renderTrend(items, buildingIds) {
    const svg = document.getElementById("trendChart");
    const tooltip = document.getElementById("energyTooltip");

    if (!svg) {
        return;
    }

    svg.innerHTML = "";

    if (!items.length) {
        const message = createSvgElement("text", {
            x: 30,
            y: 40,
            "font-size": 14,
            fill: "#64748b",
        });
        message.textContent = "No hourly Energy data available.";
        svg.appendChild(message);
        return;
    }

    const width = 760;
    const height = 380;
    const left = 65;
    const right = 25;
    const top = 25;
    const bottom = 75;
    const chartWidth = width - left - right;
    const chartHeight = height - top - bottom;

    const maxEnergy = Math.max(...items.map(item => toNumber(item.energy)));
    const max = Math.max(Math.ceil(maxEnergy / 5) * 5, 5);

    svg.appendChild(createSvgElement("line", {
        x1: left,
        y1: top,
        x2: left,
        y2: height - bottom,
        stroke: "#777",
    }));

    svg.appendChild(createSvgElement("line", {
        x1: left,
        y1: height - bottom,
        x2: width - right,
        y2: height - bottom,
        stroke: "#777",
    }));

    const yTitle = createSvgElement("text", {
        x: 5,
        y: 15,
        "font-size": 12,
    });
    yTitle.textContent = "Energy (kWh / hour)";
    svg.appendChild(yTitle);

    const xTitle = createSvgElement("text", {
        x: width - right,
        y: height - 15,
        "text-anchor": "end",
        "font-size": 12,
    });
    xTitle.textContent = "Time";
    svg.appendChild(xTitle);

    for (let i = 0; i <= 4; i += 1) {
        const value = (max / 4) * i;
        const y = height - bottom - (value / max) * chartHeight;

        svg.appendChild(createSvgElement("line", {
            x1: left,
            y1: y,
            x2: width - right,
            y2: y,
            stroke: "#e5e9f0",
        }));

        const label = createSvgElement("text", {
            x: left - 10,
            y: y + 4,
            "text-anchor": "end",
            "font-size": 11,
        });
        label.textContent = value.toFixed(1);
        svg.appendChild(label);
    }

    const points = items.map((item, index) => {
        const x = left + (index / Math.max(items.length - 1, 1)) * chartWidth;
        const y = height - bottom - (toNumber(item.energy) / max) * chartHeight;
        return { x, y, item };
    });

    points.forEach((point, index) => {
        if (index % 2 !== 0) {
            return;
        }

        const tick = createSvgElement("line", {
            x1: point.x,
            y1: height - bottom,
            x2: point.x,
            y2: height - bottom + 6,
            stroke: "#777",
        });
        svg.appendChild(tick);

        const label = createSvgElement("text", {
            x: point.x,
            y: height - bottom + 25,
            "text-anchor": "middle",
            "font-size": 11,
        });
        label.textContent = formatTime(point.item.time);
        svg.appendChild(label);
    });

    const line = createSvgElement("polyline", {
        points: points.map(point => `${point.x},${point.y}`).join(" "),
        fill: "none",
        stroke: "#3b82f6",
        "stroke-width": 3,
    });
    svg.appendChild(line);

    points.forEach(point => {
        const dot = createSvgElement("circle", {
            cx: point.x,
            cy: point.y,
            r: 4,
            fill: "#3b82f6",
        });
        dot.style.cursor = "pointer";

        dot.addEventListener("mouseenter", event => {
            if (!tooltip) {
                return;
            }

            const buildingRows = buildingIds
                .filter(buildingId => Object.prototype.hasOwnProperty.call(point.item, buildingId))
                .map(buildingId => (
                    `<br><strong>${escapeHtml(buildingId)}:</strong> ${toNumber(point.item[buildingId]).toFixed(2)} kWh / hour`
                ))
                .join("");

            tooltip.innerHTML = `
                <strong>Time:</strong> ${escapeHtml(formatTime(point.item.time))}
                <br><strong>Total:</strong> ${toNumber(point.item.energy).toFixed(2)} kWh / hour
                ${buildingRows}
            `;
            tooltip.style.display = "block";
            tooltip.style.left = `${event.clientX + 12}px`;
            tooltip.style.top = `${event.clientY + 12}px`;
        });

        dot.addEventListener("mousemove", event => {
            if (!tooltip) {
                return;
            }

            tooltip.style.left = `${event.clientX + 12}px`;
            tooltip.style.top = `${event.clientY + 12}px`;
        });

        dot.addEventListener("mouseleave", () => {
            if (tooltip) {
                tooltip.style.display = "none";
            }
        });

        svg.appendChild(dot);
    });
}


/* =========================================================
   PEAK USAGE
   ========================================================= */

function renderPeak(peak) {
    const container = document.getElementById("peakDetails");

    if (!container) {
        return;
    }

    if (!peak || !peak.timestamp) {
        container.innerHTML = '<p class="muted">No peak usage row available in the sensor stream.</p>';
        return;
    }

    container.innerHTML = `
        <div><b>Building:</b> ${escapeHtml(peak.building_id)}</div>
        <div><b>Room:</b> ${escapeHtml(peak.room_id)} (${escapeHtml(peak.room_type)})</div>
        <div><b>Time:</b> ${escapeHtml(formatDate(peak.timestamp))}</div>
        <div><b>Peak Energy:</b> ${toNumber(peak.energy).toFixed(2)} kWh / reading</div>
    `;
}


/* =========================================================
   ANOMALIES
   ========================================================= */

function renderAnomalies(anomalies) {
    const container = document.getElementById("anomalies");

    if (!container) {
        return;
    }

    if (!anomalies.length) {
        container.innerHTML = '<p class="muted">No significant energy anomalies detected in the readings.</p>';
        return;
    }

    const rows = anomalies.map(item => `
        <tr>
            <td>${escapeHtml(item.building)}</td>
            <td>${escapeHtml(item.room)}</td>
            <td>${escapeHtml(item.room_type)}</td>
            <td>${escapeHtml(formatDate(item.timestamp))}</td>
            <td>${toNumber(item.energy).toFixed(2)} kWh / reading</td>
            <td>${toNumber(item.baseline).toFixed(2)} kWh / reading</td>
            <td>${toNumber(item.above_baseline).toFixed(1)}%</td>
        </tr>
    `).join("");

    container.innerHTML = `
        <table>
            <thead>
                <tr>
                    <th>Building</th>
                    <th>Room</th>
                    <th>Room Type</th>
                    <th>Timestamp</th>
                    <th>Energy<br>(kWh / reading)</th>
                    <th>Baseline<br>(kWh / reading)</th>
                    <th>Above Baseline</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}


/* =========================================================
   ENERGY AGENT RECOMMENDATIONS
   ========================================================= */

function renderRecommendations(recommendations) {
    const container = document.getElementById("recommendations");

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (!recommendations.length) {
        container.innerHTML = '<p class="muted">No recommendations available.</p>';
        return;
    }

    recommendations.forEach(item => {
        const alert = document.createElement("div");
        alert.className = `alert ${safeClass(item.priority || "low")}`;
        alert.innerHTML = `
            <div class="alert-title">
                ${escapeHtml(item.priority || "Info")} • ${escapeHtml(item.type || "Recommendation")}
            </div>
            <div>${escapeHtml(item.message || "")}</div>
            <div class="muted">Reason: ${escapeHtml(item.reason || "Derived from readings.")}</div>
        `;
        container.appendChild(alert);
    });
}


/* =========================================================
   HELPERS
   ========================================================= */

function getBuildingIds(data) {
    const fromMetadata = data.metadata?.building_ids;

    if (Array.isArray(fromMetadata) && fromMetadata.length) {
        return fromMetadata.map(String);
    }

    const fromBuildings = data.building_energy || [];

    if (fromBuildings.length) {
        return fromBuildings.map(item => String(item.building));
    }

    const fromTrend = data.hourly_energy || [];
    const keys = new Set();

    fromTrend.forEach(row => {
        Object.keys(row).forEach(key => {
            if (key !== "time" && key !== "energy") {
                keys.add(key);
            }
        });
    });

    return Array.from(keys).sort();
}


function createSvgElement(name, attributes) {
    const element = document.createElementNS("http://www.w3.org/2000/svg", name);

    Object.entries(attributes || {}).forEach(([key, value]) => {
        element.setAttribute(key, value);
    });

    return element;
}


function setText(id, value) {
    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}


function toNumber(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
}


function formatDate(value) {
    if (!value) {
        return "-";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return String(value);
    }

    return date.toLocaleString();
}


function formatTime(value) {
    if (!value) {
        return "-";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return String(value);
    }

    return date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
    });
}


function safeClass(value) {
    return String(value ?? "")
        .toLowerCase()
        .replace(/[^a-z0-9_-]/g, "");
}


function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


function showDashboardError() {
    [
        "totalEnergy",
        "estimatedCost",
        "efficiencyScore",
        "potentialSavings",
        "averageEnergy",
        "peakEnergy",
        "carbonReduction",
        "anomalyCount",
    ].forEach(id => setText(id, "-"));

    setText("datasetSummary", "Unable to load dashboard data");
}


loadDashboard();
setInterval(loadDashboard, 30000);
