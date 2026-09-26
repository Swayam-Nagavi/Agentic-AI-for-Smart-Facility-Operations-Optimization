document.addEventListener(
    "DOMContentLoaded",
    () => {

        loadOperationsDashboard();

        const refreshButton =
            document.getElementById(
                "refreshButton"
            );

        if (refreshButton) {

            refreshButton.addEventListener(
                "click",
                loadOperationsDashboard
            );

        }

    }
);


async function loadOperationsDashboard() {

    hideError();

    try {

        const response =
            await fetch(
                "/api/orchestrator/dashboard"
            );

        if (!response.ok) {

            throw new Error(
                `API returned ${response.status}`
            );

        }

        const data =
            await response.json();

        const cost =
            data.cost_optimization || {};


        updateExecutiveKPIs(
            data,
            cost
        );

        renderCostDistribution(
            cost.cost_distribution || []
        );

        renderCostRecommendations(
            cost.cost_recommendations || []
        );

        renderAgentPerformance(
            data.agent_status || [],
            data.domain_scores || [],
            data
        );

        renderDomainScores(
            data.domain_scores || []
        );

        renderList(
            "crossAgentInsights",
            data.cross_agent_insights || [],
            renderInsight
        );

        renderList(
            "guardrails",
            data.guardrails || [],
            renderGuardrail
        );

        renderActions(
            data.actions || []
        );

        renderList(
            "decisionLog",
            data.decision_log || [],
            renderDecision
        );

        updateSource(
            data,
            cost
        );

    }

    catch (error) {

        console.error(
            "Operations dashboard error:",
            error
        );

        showError();

    }

}


/* ============================================================
   EXECUTIVE KPIs
   ============================================================ */

function updateExecutiveKPIs(
    data,
    cost
) {

    const costKpis =
        cost.kpis || {};

    const operationKpis =
        data.kpis || {};


    const health =
        toNumber(
            costKpis.facility_health ??
            operationKpis.facility_score
        );


    const status =
        operationKpis.facility_status ||
        "Loading";


    setText(
        "totalMonthlyCost",
        formatINR(
            costKpis.monthly_operating_cost ??
            costKpis.total_operating_cost
        )
    );


    setText(
        "totalOperatingCost",
        formatINR(
            costKpis.monthly_operating_cost ??
            costKpis.total_operating_cost
        )
    );


    setText(
        "costReduction",
        `${toNumber(
            costKpis.cost_reduction_percent
        ).toFixed(1)}%`
    );


    setText(
        "estimatedSavings",
        formatINR(
            costKpis.monthly_savings ??
            costKpis.estimated_savings_opportunity
        )
    );


    setText(
        "annualSavings",
        formatINR(
            costKpis.annual_savings
        )
    );


    setText(
        "facilityHealth",
        `${health.toFixed(0)}/100`
    );


    setText(
        "facilityStatus",
        status
    );


    setText(
        "optimizationCount",
        costKpis.optimizations ?? 0
    );


    const roi =
        cost.roi || {};


    if (roi.available) {

        const roiPercent =
            toNumber(
                roi.roi_percent ??
                roi.value
            );

        setText(
            "roiValue",
            `${roiPercent.toFixed(0)}%`
        );

        setText(
            "roiSummary",
            `${roiPercent.toFixed(0)}% return`
        );

        setText(
            "paybackPeriod",
            `${toNumber(
                roi.payback_months
            ).toFixed(1)} months`
        );

    }

    else {

        setText(
            "roiValue",
            "--"
        );

        setText(
            "roiSummary",
            "Not calculated"
        );

        setText(
            "paybackPeriod",
            "--"
        );

    }


    setText(
        "roiNote",
        roi.note ||
        "Facility financial model is available."
    );


    setText(
        "miniHealth",
        health.toFixed(0)
    );


    setText(
        "miniSavings",
        formatINRShort(
            costKpis.monthly_savings ??
            costKpis.estimated_savings_opportunity
        )
    );


    setText(
        "miniActions",
        costKpis.optimizations ?? 0
    );


    setText(
        "miniOperatingCost",
        formatINR(
            costKpis.monthly_operating_cost ??
            costKpis.total_operating_cost
        )
    );


    setText(
        "dataAsOf",
        data.data_as_of || "--"
    );

}


/* ============================================================
   COST DISTRIBUTION
   ============================================================ */

function renderCostDistribution(items) {

    const chart =
        document.getElementById(
            "costDistributionChart"
        );

    const list =
        document.getElementById(
            "costDistributionList"
        );


    if (!chart || !list) {
        return;
    }


    if (!items.length) {

        chart.innerHTML =
            `<div class="empty-state">
                No cost distribution available.
            </div>`;

        list.innerHTML =
            `<div class="empty-state">
                No cost distribution available.
            </div>`;

        return;
    }


    /* Simple visual distribution */

    chart.innerHTML = `
        <div class="distribution-visual">

            <div class="distribution-circle">

                <strong>
                    ${items.reduce(
                        (sum, item) =>
                            sum +
                            toNumber(item.percentage),
                        0
                    ).toFixed(0)}%
                </strong>

                <span>
                    Allocated
                </span>

            </div>

        </div>
    `;


    list.innerHTML =
        items.map(
            item => {

                const percentage =
                    Math.max(
                        0,
                        Math.min(
                            100,
                            toNumber(
                                item.percentage
                            )
                        )
                    );


                return `

                    <div class="cost-row">

                        <div class="cost-row-top">

                            <span>
                                ${escapeHtml(
                                    item.category
                                )}
                            </span>

                            <strong>
                                ${formatINR(
                                    item.cost
                                )}
                                ·
                                ${percentage.toFixed(1)}%
                            </strong>

                        </div>


                        <div class="cost-track">

                            <div
                                class="cost-bar"
                                style="width:${percentage}%">
                            </div>

                        </div>

                    </div>

                `;

            }
        ).join("");

}


/* ============================================================
   COST RECOMMENDATIONS
   ============================================================ */

function renderCostRecommendations(
    items
) {

    const container =
        document.getElementById(
            "costRecommendations"
        );


    if (!container) {
        return;
    }


    if (!items.length) {

        container.innerHTML =
            `<div class="empty-state">
                No current cost-saving opportunities.
            </div>`;

        return;
    }


    container.innerHTML =
        items.map(
            item => `

                <article
                    class="recommendation-card">

                    <div
                        class="recommendation-top">

                        <span
                            class="badge ${safeClass(
                                item.priority
                            )}">

                            ${escapeHtml(
                                item.priority
                            )}

                        </span>


                        <span
                            class="domain-label">

                            ${escapeHtml(
                                item.domain
                            )}

                        </span>

                    </div>


                    <h3>
                        ${escapeHtml(
                            item.title
                        )}
                    </h3>


                    <p>
                        ${escapeHtml(
                            item.reason
                        )}
                    </p>


                    <strong
                        class="saving-value">

                        ${formatINR(
                            item.estimated_savings
                        )}

                    </strong>


                    <small>
                        Estimated savings opportunity
                    </small>

                </article>

            `
        ).join("");

}


/* ============================================================
   AGENT PERFORMANCE
============================================================ */

function renderAgentPerformance(
    agentStatus,
    domainScores,
    data
) {

    const agents = {};

    agentStatus.forEach(
        agent => {

            const key =
                String(
                    agent.agent || ""
                )
                .toLowerCase()
                .replace(
                    " agent",
                    ""
                );

            agents[key] = agent;

        }
    );


    fillAgentCard(
        "energy",
        agents.energy
    );

    fillAgentCard(
        "maintenance",
        agents.maintenance
    );

    fillAgentCard(
        "occupancy",
        agents.occupancy
    );

    fillAgentCard(
        "security",
        agents.security
    );

}


/* ============================================================
   AGENT CARD DATA
============================================================ */

function fillAgentCard(
    type,
    agent
) {

    if (!agent) {
        return;
    }


    /* Score */

    setText(
        `${type}Score`,
        Math.round(
            toNumber(
                agent.score
            )
        )
    );


    /* Status */

    setText(
        `${type}Status`,
        agent.status || "--"
    );


    /* Primary metric */

    if (type === "energy") {

        setText(
            "energyConsumption",
            agent.primary_metric || "--"
        );

        setText(
            "energyAnomalies",
            agent.secondary_metric || "--"
        );

    }


    if (type === "maintenance") {

        setText(
            "maintenanceHealth",
            agent.primary_metric || "--"
        );

        setText(
            "maintenanceFaults",
            agent.secondary_metric || "--"
        );

    }


    if (type === "occupancy") {

        setText(
            "occupancyLevel",
            agent.primary_metric || "--"
        );

        setText(
            "occupancyAlerts",
            agent.secondary_metric || "--"
        );

    }


    if (type === "security") {

        setText(
            "securityAlerts",
            agent.primary_metric || "--"
        );

        setText(
            "securityLevel",
            agent.secondary_metric || "--"
        );

    }

}


/* ============================================================
   INDIVIDUAL AGENT
   ============================================================ */

function fillAgent(
    type,
    scoreData,
    agent,
    data
) {

    const score =
        scoreData?.score ??
        agent?.score ??
        0;

    const status =
        scoreData?.status ??
        agent?.status ??
        "--";


    setText(
        `${type}Score`,
        Math.round(
            toNumber(score)
        )
    );


    setText(
        `${type}Status`,
        status
    );


    if (type === "energy") {

        setText(
            "energyConsumption",
            firstValue(
                agent,
                [
                    "consumption",
                    "energy_consumption",
                    "energy"
                ],
                "--"
            )
        );

        setText(
            "energyAnomalies",
            firstValue(
                agent,
                [
                    "anomalies",
                    "active_alerts"
                ],
                "--"
            )
        );

    }


    if (type === "maintenance") {

        setText(
            "maintenanceFaults",
            firstValue(
                agent,
                [
                    "faults_detected",
                    "faults"
                ],
                "--"
            )
        );

        setText(
            "maintenanceHealth",
            firstValue(
                agent,
                [
                    "average_health",
                    "health"
                ],
                "--"
            )
        );

    }


    if (type === "occupancy") {

        setText(
            "occupancyLevel",
            firstValue(
                agent,
                [
                    "occupancy_rate",
                    "occupancy"
                ],
                "--"
            )
        );

        setText(
            "occupancyAlerts",
            firstValue(
                agent,
                [
                    "capacity_alerts",
                    "alerts"
                ],
                "--"
            )
        );

    }


    if (type === "security") {

        setText(
            "securityAlerts",
            firstValue(
                agent,
                [
                    "active_alerts",
                    "alerts"
                ],
                "--"
            )
        );

        setText(
            "securityLevel",
            firstValue(
                agent,
                [
                    "security_level",
                    "level"
                ],
                status
            )
        );

    }

}


/* ============================================================
   DOMAIN HEALTH
   ============================================================ */

function renderDomainScores(items) {

    const container =
        document.getElementById(
            "domainScores"
        );


    if (!container) {
        return;
    }


    if (!items.length) {

        container.innerHTML =
            `<div class="empty-state">
                No domain scores available.
            </div>`;

        return;
    }


    container.innerHTML =
        items.map(
            item => {

                const score =
                    Math.max(
                        0,
                        Math.min(
                            100,
                            toNumber(
                                item.score
                            )
                        )
                    );


                return `

                    <div
                        class="domain-score">

                        <div
                            class="domain-score-header">

                            <span>
                                ${escapeHtml(
                                    item.domain
                                )}
                            </span>

                            <strong>
                                ${score.toFixed(0)}
                            </strong>

                        </div>


                        <div
                            class="progress-bar">

                            <div
                                class="progress-fill"
                                style="width:${score}%">
                            </div>

                        </div>


                        <span
                            class="badge ${safeClass(
                                item.status
                            )}">

                            ${escapeHtml(
                                item.status
                            )}

                        </span>


                        <p class="score-summary">

                            ${escapeHtml(
                                item.summary || ""
                            )}

                        </p>

                    </div>

                `;

            }
        ).join("");

}


/* ============================================================
   ACTIONS
   ============================================================ */

function renderActions(
    actions
) {

    const container =
        document.getElementById(
            "recommendedActions"
        );


    if (!container) {
        return;
    }


    if (!actions.length) {

        container.innerHTML =
            `<div class="empty-state">
                No optimization actions currently required.
            </div>`;

        return;
    }


    container.innerHTML =
        actions.map(
            action => `

                <div
                    class="action-card">

                    <div
                        class="action-card-top">

                        <span
                            class="badge ${safeClass(
                                action.priority
                            )}">

                            ${escapeHtml(
                                action.priority
                            )}

                        </span>


                        <span
                            class="action-id">

                            ${escapeHtml(
                                action.action_id
                            )}

                        </span>

                    </div>


                    <h3>
                        ${escapeHtml(
                            action.title
                        )}
                    </h3>


                    <p>
                        ${escapeHtml(
                            action.recommended_action
                        )}
                    </p>


                    <div
                        class="action-meta">

                        <span>
                            Domain:
                            <strong>
                                ${escapeHtml(
                                    action.domain
                                )}
                            </strong>
                        </span>

                        <span>
                            ${escapeHtml(
                                action.automation_mode
                            )}
                        </span>

                    </div>

                </div>

            `
        ).join("");

}


/* ============================================================
   GENERIC LIST
   ============================================================ */

function renderList(
    elementId,
    items,
    renderer
) {

    const container =
        document.getElementById(
            elementId
        );


    if (!container) {
        return;
    }


    if (!items.length) {

        container.innerHTML =
            `<div class="empty-state">
                No items available.
            </div>`;

        return;
    }


    container.innerHTML =
        items.map(renderer).join("");

}


/* ============================================================
   INSIGHT
   ============================================================ */

function renderInsight(
    item
) {

    return `

        <div class="list-card">

            <div class="list-top">

                <strong>
                    ${escapeHtml(
                        item.title ||
                        item.type ||
                        "Insight"
                    )}
                </strong>


                <span
                    class="badge ${safeClass(
                        item.severity ||
                        "Info"
                    )}">

                    ${escapeHtml(
                        item.severity ||
                        "Info"
                    )}

                </span>

            </div>


            <p>
                ${escapeHtml(
                    item.message || ""
                )}
            </p>

        </div>

    `;

}


/* ============================================================
   GUARDRAIL
   ============================================================ */

function renderGuardrail(
    item
) {

    return `

        <div class="list-card">

            <div class="list-top">

                <strong>
                    ${escapeHtml(
                        item.name ||
                        "Guardrail"
                    )}
                </strong>


                <span
                    class="badge ${safeClass(
                        item.level ||
                        "Info"
                    )}">

                    ${escapeHtml(
                        item.level ||
                        "Info"
                    )}

                </span>

            </div>


            <p>
                ${escapeHtml(
                    item.rule || ""
                )}
            </p>

        </div>

    `;

}


/* ============================================================
   DECISION LOG
   ============================================================ */

function renderDecision(
    item
) {

    return `

        <div class="list-card">

            <strong>
                ${escapeHtml(
                    item.decision ||
                    "Decision"
                )}
            </strong>


            <p>
                ${escapeHtml(
                    item.rationale ||
                    ""
                )}
            </p>


            <p class="meta-text">

                ${escapeHtml(
                    formatDate(
                        item.timestamp
                    )
                )}

                · Confidence:

                ${escapeHtml(
                    item.confidence ||
                    "Medium"
                )}

            </p>

        </div>

    `;

}


/* ============================================================
   SOURCE
   ============================================================ */

function updateSource(
    data,
    cost
) {

    setText(
        "dataSource",
        cost.data_source ||
        data.data_source ||
        "Multi-agent facility intelligence"
    );


    setText(
        "dataAsOf",
        data.data_as_of ||
        "--"
    );

}


/* ============================================================
   ERROR
   ============================================================ */

function showError() {

    const container =
        document.getElementById(
            "errorContainer"
        );

    if (container) {

        container.style.display =
            "block";

    }

}


function hideError() {

    const container =
        document.getElementById(
            "errorContainer"
        );

    if (container) {

        container.style.display =
            "none";

    }

}


/* ============================================================
   HELPERS
   ============================================================ */

function setText(
    id,
    value
) {

    const element =
        document.getElementById(id);

    if (element) {

        element.textContent =
            value;

    }

}


function toNumber(
    value
) {

    const number =
        Number(value);

    return Number.isFinite(number)
        ? number
        : 0;

}


function firstValue(
    object,
    keys,
    fallback
) {

    if (!object) {
        return fallback;
    }


    for (
        const key of keys
    ) {

        if (
            object[key] !== undefined &&
            object[key] !== null
        ) {

            return object[key];

        }

    }


    return fallback;

}


function formatINR(
    value
) {

    const number =
        toNumber(value);

    return new Intl.NumberFormat(
        "en-IN",
        {
            style: "currency",
            currency: "INR",
            maximumFractionDigits: 0
        }
    ).format(number);

}


function formatINRShort(
    value
) {

    const number =
        toNumber(value);


    if (number >= 10000000) {

        return `₹${(
            number / 10000000
        ).toFixed(1)}Cr`;

    }


    if (number >= 100000) {

        return `₹${(
            number / 100000
        ).toFixed(1)}L`;

    }


    if (number >= 1000) {

        return `₹${(
            number / 1000
        ).toFixed(1)}K`;

    }


    return `₹${number.toFixed(0)}`;

}


function safeClass(
    value
) {

    return String(
        value ?? ""
    )
        .toLowerCase()
        .replace(
            /[^a-z0-9_-]/g,
            ""
        );

}


function formatDate(
    value
) {

    if (!value) {
        return "-";
    }


    const date =
        new Date(value);


    return Number.isNaN(
        date.getTime()
    )
        ? String(value)
        : date.toLocaleString();

}


function escapeHtml(
    value
) {

    return String(
        value ?? ""
    )
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );

}