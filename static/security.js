document.addEventListener("DOMContentLoaded", () => {
    loadSecurityDashboard();
});


async function loadSecurityDashboard() {

    try {
        const response = await fetch("/api/security");

        if (!response.ok) {
            throw new Error("Failed to load security data");
        }

        const data = await response.json();

        updateKPIs(data);
        updateSeverity(data);
        renderAlerts(data.alerts || []);
        renderHighRiskEvents(data.high_risk_events || []);
        renderInsights(data.insights || []);
        updateSource(data);

    } catch (error) {

        console.error(
            "Security dashboard error:",
            error
        );

        document.getElementById("alerts").innerHTML =
            "<p>Unable to load security data.</p>";
    }
}


// ============================================================
// KPI CARDS
// ============================================================

function updateKPIs(data) {

    const kpis = data.kpis || {};

    document.getElementById("totalEvents").textContent =
        kpis.total_events ?? 0;

    document.getElementById("unauthorizedEvents").textContent =
        kpis.unauthorized_access ?? 0;

    document.getElementById("highRiskEvents").textContent =
        kpis.high_risk_events ?? 0;

    document.getElementById("unauthorizedRate").textContent =
        `${kpis.unauthorized_rate ?? 0}%`;
}


// ============================================================
// SEVERITY
// ============================================================

function updateSeverity(data) {

    const severity = data.severity || {};

    document.getElementById("lowEvents").textContent =
        severity.Low ?? 0;

    document.getElementById("mediumEvents").textContent =
        severity.Medium ?? 0;

    document.getElementById("highEvents").textContent =
        severity.High ?? 0;

    document.getElementById("criticalEvents").textContent =
        severity.Critical ?? 0;
}


// ============================================================
// SECURITY ALERTS
// ============================================================

function renderAlerts(alerts) {

    const container =
        document.getElementById("alerts");

    if (!alerts.length) {

        container.innerHTML = `
            <p>No security alerts detected.</p>
        `;

        return;
    }

    container.innerHTML = alerts.map(alert => {

        const eventType =
            alert.event_type ||
            alert.type ||
            "Security Event";

        const building =
            alert.building_id ||
            alert.facility_id ||
            "Unknown";

        const room =
            alert.room_id ||
            "Unknown";

        const severity =
            alert.severity ||
            "Medium";

        const timestamp =
            formatTimestamp(alert.timestamp);

        return `
            <div class="security-alert ${severity.toLowerCase()}">

                <div class="alert-title">
                    ${escapeHtml(eventType)}
                    - ${escapeHtml(severity)}
                </div>

                <div class="alert-message">
                    Unauthorized access detected at
                    ${escapeHtml(building)} -
                    ${escapeHtml(room)}.
                </div>

                <div class="alert-meta">
                    ${escapeHtml(timestamp)}
                </div>

            </div>
        `;

    }).join("");
}


// ============================================================
// HIGH-RISK EVENTS
// ============================================================

function renderHighRiskEvents(events) {

    const table =
        document.getElementById("highRiskTable");

    if (!events.length) {

        table.innerHTML = `
            <tr>
                <td colspan="4">
                    No high-risk events detected.
                </td>
            </tr>
        `;

        return;
    }

    table.innerHTML = events.map(event => {

        const facility =
            event.building_id ||
            event.facility_id ||
            event.facility ||
            "Unknown";

        const room =
            event.room_id || "";

        const eventType =
            event.event_type ||
            event.type ||
            "Security Event";

        const severity =
            event.severity ||
            "High";

        const timestamp =
            formatTimestamp(event.timestamp);

        return `
            <tr>

                <td>
                    ${escapeHtml(facility)}
                    ${room
                        ? ` - ${escapeHtml(room)}`
                        : ""}
                </td>

                <td>
                    ${escapeHtml(eventType)}
                </td>

                <td>
                    <span class="severity-badge ${severity.toLowerCase()}">
                        ${escapeHtml(severity)}
                    </span>
                </td>

                <td>
                    ${escapeHtml(timestamp)}
                </td>

            </tr>
        `;

    }).join("");
}


// ============================================================
// SECURITY INSIGHTS
// ============================================================

function renderInsights(insights) {

    const container =
        document.getElementById("insights");

    if (!insights.length) {

        container.innerHTML = `
            <p>No security insights available.</p>
        `;

        return;
    }

    container.innerHTML = insights.map(insight => {

        if (typeof insight === "string") {

            return `
                <div class="insight">
                    ${escapeHtml(insight)}
                </div>
            `;
        }

        return `
            <div class="insight">

                <strong>
                    ${escapeHtml(
                        insight.type ||
                        "Security Insight"
                    )}
                </strong>

                <p>
                    ${escapeHtml(
                        insight.message || ""
                    )}
                </p>

            </div>
        `;

    }).join("");
}


// ============================================================
// DATA SOURCE
// ============================================================

function updateSource(data) {

    const metadata = data.metadata || {};

    setText(
        "dataSource",
        data.data_source || "Security events loaded from security_events.csv"
    );

    const start = metadata.start_timestamp
        ? formatTimestamp(metadata.start_timestamp)
        : null;

    const end = metadata.end_timestamp
        ? formatTimestamp(metadata.end_timestamp)
        : null;

    setText(
        "dataPeriod",
        start && end
            ? `${start} → ${end}`
            : "No CSV timestamp range available"
    );

    setText(
        "dataNote",
        data.note || "Only CSV-backed security events are shown."
    );
}


function setText(id, value) {

    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}


// ============================================================
// TIMESTAMP
// ============================================================

function formatTimestamp(timestamp) {

    if (!timestamp) {
        return "Unknown time";
    }

    const date = new Date(timestamp);

    if (Number.isNaN(date.getTime())) {
        return timestamp;
    }

    return date.toLocaleString();
}


// ============================================================
// HTML SAFETY
// ============================================================

function escapeHtml(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}