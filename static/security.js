async function fetchJSON(url) {
    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
    }

    return await response.json();
}

function getSummary(data) {
    return data.summary || data;
}

function renderAlerts(alerts) {
    const container = document.getElementById("alerts");

    if (!alerts || alerts.length === 0) {
        container.innerHTML = `
            <div class="insight">
                No security alerts detected.
            </div>
        `;
        return;
    }

    container.innerHTML = alerts.map(alert => `
        <div class="alert ${alert.severity}">
            <div class="alert-title">
                ${alert.alert_type} — ${alert.severity}
            </div>

            <div>${alert.message}</div>

            <small>
                Facility: ${alert.facility_id || "Unknown"}
                ${alert.timestamp ? " | " + alert.timestamp : ""}
            </small>
        </div>
    `).join("");
}

function renderHighRiskEvents(events) {
    const table = document.getElementById("highRiskTable");

    table.innerHTML = "";

    if (!events || events.length === 0) {
        table.innerHTML = `
            <tr>
                <td colspan="4">No high-risk events detected.</td>
            </tr>
        `;
        return;
    }

    events.forEach(event => {
        const facility =
            event.facility_id ||
            event.building_id ||
            "Unknown";

        const eventType =
            event.event_type ||
            event.type ||
            "Unknown";

        const severity =
            event.severity ||
            "High";

        table.innerHTML += `
            <tr>
                <td>${facility}</td>
                <td>${eventType}</td>
                <td>
                    <span class="badge badge-${severity.toLowerCase()}">
                        ${severity}
                    </span>
                </td>
                <td>${event.timestamp || "-"}</td>
            </tr>
        `;
    });
}

function renderInsights(insights) {
    const container = document.getElementById("insights");

    if (!insights || insights.length === 0) {
        container.innerHTML = `
            <div class="insight">
                No security insights available.
            </div>
        `;
        return;
    }

    container.innerHTML = insights.map(item => `
        <div class="insight">
            ${item}
        </div>
    `).join("");
}

async function loadSecurity() {
    try {
        const data = await fetchJSON("/api/security");

        const summary = getSummary(data);

        document.getElementById("totalEvents").textContent =
            summary.total_events ?? 0;

        document.getElementById("unauthorizedEvents").textContent =
            summary.unauthorized_access ?? 0;

        const highRisk =
            summary.high_risk_events || [];

        document.getElementById("highRiskEvents").textContent =
            highRisk.length;

        const access =
            summary.access_analysis || {};

        document.getElementById("unauthorizedRate").textContent =
            `${access.unauthorized_rate ?? 0}%`;

        const severity =
            summary.events_by_severity || {};

        document.getElementById("lowEvents").textContent =
            severity.Low ?? severity.low ?? 0;

        document.getElementById("mediumEvents").textContent =
            severity.Medium ?? severity.medium ?? 0;

        document.getElementById("highEvents").textContent =
            severity.High ?? severity.high ?? 0;

        document.getElementById("criticalEvents").textContent =
            severity.Critical ?? severity.critical ?? 0;

        renderAlerts(summary.alerts || []);

        renderHighRiskEvents(highRisk);

        renderInsights(summary.insights || []);

    } catch (error) {
        console.error("Security error:", error);

        document.getElementById("alerts").innerHTML = `
            <div class="alert">
                Security data is currently unavailable.
            </div>
        `;

        document.getElementById("insights").innerHTML = `
            <div class="insight">
                Unable to load security information.
            </div>
        `;
    }
}

loadSecurity();

setInterval(loadSecurity, 30000);