async function loadDashboard() {
    const response = await fetch("/api/dashboard");
    const data = await response.json();

    document.getElementById("totalEnergy").textContent =
        `${data.kpis.total_energy.toFixed(2)} kWh`;

    document.getElementById("averageEnergy").textContent =
        `${data.kpis.average_interval_energy.toFixed(2)} kWh`;

    document.getElementById("peakEnergy").textContent =
        `${data.kpis.peak_usage.toFixed(2)} kWh`;

    document.getElementById("anomalyCount").textContent =
        data.kpis.anomalies;

    renderBars("buildingChart", data.building_energy, "building");
    renderBars("roomChart", data.room_energy, "label");
    renderTrend(data.hourly_energy);
    renderPeak(data.peak);
    renderAnomalies(data.anomalies);
    renderRecommendations(data.recommendations);
}


function renderBars(elementId, items, labelKey) {
    const container = document.getElementById(elementId);
    container.innerHTML = "";

    const max = Math.max(...items.map(item => item.energy), 1);

    items.forEach(item => {
        const row = document.createElement("div");
        row.className = "bar-row";

        const label = document.createElement("span");
        label.textContent = item[labelKey];

        const track = document.createElement("div");
        track.className = "bar-track";

        const bar = document.createElement("div");
        bar.className = "bar";
        bar.style.width = `${(item.energy / max) * 100}%`;

        const value = document.createElement("span");
        value.textContent = `${item.energy.toFixed(2)} kWh`;

        track.appendChild(bar);
        row.append(label, track, value);
        container.appendChild(row);
    });
}


function renderTrend(items) {
    const svg = document.getElementById("trendChart");
    const tooltip = document.getElementById("energyTooltip");

    svg.innerHTML = "";

    if (!items.length) return;

    const width = 760;
    const height = 380;

    const left = 65;
    const right = 25;
    const top = 25;
    const bottom = 75;

    const chartWidth = width - left - right;
    const chartHeight = height - top - bottom;

    const maxEnergy = Math.max(...items.map(item => item.energy));
    const max = Math.ceil(maxEnergy / 50) * 50;

    // Y-axis
    const yAxis = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "line"
    );

    yAxis.setAttribute("x1", left);
    yAxis.setAttribute("y1", top);
    yAxis.setAttribute("x2", left);
    yAxis.setAttribute("y2", height - bottom);
    yAxis.setAttribute("stroke", "#777");

    svg.appendChild(yAxis);

    // X-axis
    const xAxis = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "line"
    );

    xAxis.setAttribute("x1", left);
    xAxis.setAttribute("y1", height - bottom);
    xAxis.setAttribute("x2", width - right);
    xAxis.setAttribute("y2", height - bottom);
    xAxis.setAttribute("stroke", "#777");

    svg.appendChild(xAxis);

    // Y-axis title
    const yTitle = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "text"
    );

    yTitle.setAttribute("x", 5);
    yTitle.setAttribute("y", 15);
    yTitle.textContent = "Energy (kWh)";
    yTitle.setAttribute("font-size", "12");

    svg.appendChild(yTitle);

    // X-axis title
    const xTitle = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "text"
    );

    xTitle.setAttribute("x", width - right);
    xTitle.setAttribute("y", height - 15);
    xTitle.setAttribute("text-anchor", "end");
    xTitle.textContent = "Time";
    xTitle.setAttribute("font-size", "12");

    svg.appendChild(xTitle);

    // Y-axis ticks and grid lines
    for (let i = 0; i <= 4; i++) {
        const value = (max / 4) * i;

        const y =
            height -
            bottom -
            (value / max) * chartHeight;

        const grid = document.createElementNS(
            "http://www.w3.org/2000/svg",
            "line"
        );

        grid.setAttribute("x1", left);
        grid.setAttribute("y1", y);
        grid.setAttribute("x2", width - right);
        grid.setAttribute("y2", y);
        grid.setAttribute("stroke", "#e5e9f0");

        svg.appendChild(grid);

        const label = document.createElementNS(
            "http://www.w3.org/2000/svg",
            "text"
        );

        label.setAttribute("x", left - 10);
        label.setAttribute("y", y + 4);
        label.setAttribute("text-anchor", "end");
        label.textContent = value.toFixed(0);
        label.setAttribute("font-size", "11");

        svg.appendChild(label);
    }

    // Calculate graph points
    const points = items.map((item, index) => {
        const x =
            left +
            (index / Math.max(items.length - 1, 1)) *
            chartWidth;

        const y =
            height -
            bottom -
            (item.energy / max) *
            chartHeight;

        return {
            x,
            y,
            item
        };
    });

    // X-axis time labels
    points.forEach((point, index) => {
        if (index % 2 !== 0) return;

        const date = new Date(point.item.time);

        const time = date.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
            hour12: false
        });

        const tick = document.createElementNS(
            "http://www.w3.org/2000/svg",
            "line"
        );

        tick.setAttribute("x1", point.x);
        tick.setAttribute("y1", height - bottom);
        tick.setAttribute("x2", point.x);
        tick.setAttribute("y2", height - bottom + 6);
        tick.setAttribute("stroke", "#777");

        svg.appendChild(tick);

        const label = document.createElementNS(
            "http://www.w3.org/2000/svg",
            "text"
        );

        label.setAttribute("x", point.x);
        label.setAttribute("y", height - bottom + 25);
        label.setAttribute("text-anchor", "middle");
        label.textContent = time;
        label.setAttribute("font-size", "11");

        svg.appendChild(label);
    });

    // Energy line
    const line = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "polyline"
    );

    line.setAttribute(
        "points",
        points.map(point => `${point.x},${point.y}`).join(" ")
    );

    line.setAttribute("fill", "none");
    line.setAttribute("stroke", "#3b82f6");
    line.setAttribute("stroke-width", "3");

    svg.appendChild(line);

    // Dots + hover
    points.forEach(point => {
        const dot = document.createElementNS(
            "http://www.w3.org/2000/svg",
            "circle"
        );

        dot.setAttribute("cx", point.x);
        dot.setAttribute("cy", point.y);
        dot.setAttribute("r", "4");
        dot.setAttribute("fill", "#3b82f6");

        dot.style.cursor = "pointer";

        dot.addEventListener("mouseenter", event => {
            const date = new Date(point.item.time);

            const time = date.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
                hour12: false
            });

            tooltip.innerHTML = `
                <strong>Time:</strong> ${time}<br>
                <strong>Energy:</strong> ${point.item.energy.toFixed(2)} kWh
            `;

            tooltip.style.display = "block";
            tooltip.style.left = `${event.clientX + 12}px`;
            tooltip.style.top = `${event.clientY + 12}px`;
        });

        dot.addEventListener("mousemove", event => {
            tooltip.style.left = `${event.clientX + 12}px`;
            tooltip.style.top = `${event.clientY + 12}px`;
        });

        dot.addEventListener("mouseleave", () => {
            tooltip.style.display = "none";
        });

        svg.appendChild(dot);
    });
}


function renderPeak(peak) {
    document.getElementById("peakDetails").innerHTML = `
        <div><b>Building:</b> ${peak.building_id}</div>
        <div><b>Room:</b> ${peak.room_id} (${peak.room_type})</div>
        <div><b>Time:</b> ${formatDate(peak.timestamp)}</div>
        <div><b>Energy:</b> ${peak.energy.toFixed(2)} kWh</div>
    `;
}


function renderAnomalies(anomalies) {
    const container = document.getElementById("anomalies");

    if (!anomalies.length) {
        container.innerHTML =
            '<p class="muted">No significant energy anomalies detected.</p>';
        return;
    }

    const rows = anomalies.map(item => `
        <tr>
            <td>${item.building}</td>
            <td>${item.room}</td>
            <td>${item.room_type}</td>
            <td>${formatDate(item.timestamp)}</td>
            <td>${item.energy.toFixed(2)}</td>
            <td>${item.baseline.toFixed(2)}</td>
            <td>${item.above_baseline.toFixed(1)}%</td>
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
                    <th>Energy</th>
                    <th>Baseline</th>
                    <th>Above Baseline</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}


function renderRecommendations(recommendations) {
    const container = document.getElementById("recommendations");
    container.innerHTML = "";

    recommendations.forEach(item => {
        const alert = document.createElement("div");
        alert.className = `alert ${item.priority.toLowerCase()}`;

        alert.innerHTML = `
            <div class="alert-title">
                ${item.priority} • ${item.type}
            </div>
            <div>${item.message}</div>
            <div class="muted">Reason: ${item.reason}</div>
        `;

        container.appendChild(alert);
    });
}


function formatDate(value) {
    return new Date(value).toLocaleString();
}


loadDashboard();
setInterval(loadDashboard, 30000);
