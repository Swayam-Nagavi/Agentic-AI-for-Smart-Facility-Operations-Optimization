document.addEventListener("DOMContentLoaded", () => {
    loadOperationsDashboard();

    const refreshButton = document.getElementById("refreshButton");

    if (refreshButton) {
        refreshButton.addEventListener("click", loadOperationsDashboard);
    }
});


async function loadOperationsDashboard() {
    try {
        const response = await fetch("/api/orchestrator/dashboard");

        if (!response.ok) {
            throw new Error(`Operations API returned ${response.status}`);
        }

        const data = await response.json();

        updateKPIs(data.kpis || {});
        renderDomainScores(data.domain_scores || []);
        renderAgentStatus(data.agent_status || []);
        renderActions(data.actions || []);
        renderList("crossAgentInsights", data.cross_agent_insights || [], renderInsight);
        renderList("guardrails", data.guardrails || [], renderGuardrail);
        renderList("decisionLog", data.decision_log || [], renderDecision);
        renderTimeline(data.timeline || []);
        updateSource(data);
    } catch (error) {
        console.error("Operations dashboard error:", error);
        showError();
    }
}


function updateKPIs(kpis) {
    const score = toNumber(kpis.facility_score);
    const status = kpis.facility_status || "Loading";

    setText("facilityScore", `${score.toFixed(0)}%`);
    setText("facilityStatus", status);
    setText("coordinatedAgents", kpis.coordinated_agents ?? 0);
    setText("activeAlerts", kpis.active_alerts ?? 0);
    setText("criticalActions", kpis.critical_actions ?? 0);
    setText("automationReadiness", `${toNumber(kpis.automation_readiness).toFixed(0)}%`);

    const ring = document.getElementById("facilityScoreRing");

    if (ring) {
        ring.className = `score-ring ${safeClass(status)}`;
    }
}


function renderDomainScores(items) {
    const container = document.getElementById("domainScores");

    if (!container) {
        return;
    }

    if (!items.length) {
        container.innerHTML = '<div class="empty-state">No domain scores available.</div>';
        return;
    }

    container.innerHTML = items.map(item => {
        const score = toNumber(item.score);
        const statusClass = safeClass(item.status);

        return `
            <div class="score-card">
                <div class="score-top">
                    <div>
                        <strong>${escapeHtml(item.domain)}</strong>
                        <div class="meta-text">Weight ${toNumber(item.weight).toFixed(0)}%</div>
                    </div>
                    <span class="score-value">${score.toFixed(0)}</span>
                </div>
                <div class="progress-track">
                    <div class="progress-bar ${statusClass}" style="width:${Math.max(0, Math.min(100, score))}%"></div>
                </div>
                <span class="badge ${statusClass}">${escapeHtml(item.status)}</span>
                <p class="score-summary">${escapeHtml(item.summary || "")}</p>
            </div>
        `;
    }).join("");
}


function renderAgentStatus(items) {
    const container = document.getElementById("agentStatus");

    if (!container) {
        return;
    }

    if (!items.length) {
        container.innerHTML = '<div class="empty-state">No agent status available.</div>';
        return;
    }

    container.innerHTML = items.map(agent => {
        const statusClass = safeClass(agent.status);

        return `
            <div class="agent-card">
                <div class="agent-top">
                    <strong>${escapeHtml(agent.agent)}</strong>
                    <span class="badge ${statusClass}">${escapeHtml(agent.status)}</span>
                </div>
                <h3>${toNumber(agent.score).toFixed(0)}%</h3>
                <p class="meta-text">${escapeHtml(agent.primary_metric)} • ${escapeHtml(agent.secondary_metric)}</p>
                <p class="agent-summary">${escapeHtml(agent.summary || "")}</p>
            </div>
        `;
    }).join("");
}


function renderActions(actions) {
    const tbody = document.getElementById("actionsTableBody");

    if (!tbody) {
        return;
    }

    if (!actions.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="empty-state">No optimization actions currently required.</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = actions.map(action => {
        const priorityClass = safeClass(action.priority);

        return `
            <tr>
                <td>${escapeHtml(action.action_id)}</td>
                <td><span class="badge ${priorityClass}">${escapeHtml(action.priority)}</span></td>
                <td>${escapeHtml(action.domain)}</td>
                <td>
                    <strong>${escapeHtml(action.title)}</strong>
                    <p class="meta-text">${escapeHtml(action.recommended_action)}</p>
                    <p class="meta-text">Impact: ${escapeHtml(action.expected_impact)}</p>
                </td>
                <td>${escapeHtml(action.reason)}</td>
                <td>${escapeHtml(action.automation_mode)}</td>
            </tr>
        `;
    }).join("");
}


function renderList(elementId, items, renderer) {
    const container = document.getElementById(elementId);

    if (!container) {
        return;
    }

    if (!items.length) {
        container.innerHTML = '<div class="empty-state">No items available.</div>';
        return;
    }

    container.innerHTML = items.map(renderer).join("");
}


function renderInsight(item) {
    const severityClass = safeClass(item.severity || "Info");

    return `
        <div class="list-card">
            <div class="list-top">
                <strong>${escapeHtml(item.title || "Insight")}</strong>
                <span class="badge ${severityClass}">${escapeHtml(item.severity || "Info")}</span>
            </div>
            <p>${escapeHtml(item.message || "")}</p>
        </div>
    `;
}


function renderGuardrail(item) {
    const levelClass = safeClass(item.level || "Info");

    return `
        <div class="list-card">
            <div class="list-top">
                <strong>${escapeHtml(item.name || "Guardrail")}</strong>
                <span class="badge ${levelClass}">${escapeHtml(item.level || "Info")}</span>
            </div>
            <p>${escapeHtml(item.rule || "")}</p>
        </div>
    `;
}


function renderDecision(item) {
    return `
        <div class="list-card">
            <strong>${escapeHtml(item.decision || "Decision")}</strong>
            <p>${escapeHtml(item.rationale || "")}</p>
            <p class="meta-text">${escapeHtml(formatDate(item.timestamp))} • Confidence: ${escapeHtml(item.confidence || "Medium")}</p>
        </div>
    `;
}


function renderTimeline(items) {
    const container = document.getElementById("timeline");

    if (!container) {
        return;
    }

    if (!items.length) {
        container.innerHTML = '<div class="empty-state">No operations events available.</div>';
        return;
    }

    container.innerHTML = items.map(item => `
        <div class="timeline-item">
            <strong>${escapeHtml(item.title || item.type || "Event")}</strong>
            <p>${escapeHtml(item.message || "")}</p>
            <p class="meta-text">${escapeHtml(item.type || "Operations")} • ${escapeHtml(formatDate(item.timestamp))}</p>
        </div>
    `).join("");
}


function updateSource(data) {
    setText("dataSource", data.data_source || "Live facility intelligence layer");
    setText("dataNote", data.note || "Facility agents are coordinated into a unified operations layer.");
}


function showError() {
    setText("facilityScore", "--");
    setText("facilityStatus", "Unavailable");
    setText("coordinatedAgents", "-");
    setText("activeAlerts", "-");
    setText("criticalActions", "-");
    setText("automationReadiness", "-");

    const actions = document.getElementById("actionsTableBody");

    if (actions) {
        actions.innerHTML = `
            <tr>
                <td colspan="6" class="empty-state">Unable to load operations data.</td>
            </tr>
        `;
    }
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


function safeClass(value) {
    return String(value ?? "")
        .toLowerCase()
        .replace(/[^a-z0-9_-]/g, "");
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


function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
