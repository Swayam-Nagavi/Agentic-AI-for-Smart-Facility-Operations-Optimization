let healthScoreChart = null;
let futureConditionChart = null;


document.addEventListener(
    "DOMContentLoaded",
    () => {

        loadMaintenanceDashboard();


        const refreshButton =
            document.getElementById(
                "refreshButton"
            );


        if (refreshButton) {

            refreshButton.addEventListener(
                "click",
                loadMaintenanceDashboard
            );
        }

    }
);


/* =========================================================
   LOAD DASHBOARD
========================================================= */

async function loadMaintenanceDashboard() {

    try {

        const response =
            await fetch(
                "/api/maintenance/dashboard"
            );


        if (!response.ok) {

            throw new Error(
                `Server returned ${response.status}`
            );
        }


        const data =
            await response.json();


        console.log(
            "Maintenance data:",
            data
        );


        updateKPIs(
            data.kpis || {}
        );


        updateHealthDistribution(
            data.health_distribution || []
        );


        updateHealthScoreChart(
            data.assets || []
        );


        updateFutureConditionChart(
            data.assets || []
        );


        updateAlerts(
            data.alerts || []
        );


        updateSchedule(
            data.schedule || []
        );


        updateAssets(
            data.assets || []
        );


        updateWorkOrders(
            data.schedule || []
        );


        updateSource(
            data.data_source,
            data.note
        );

    }

    catch (error) {

        console.error(
            "Maintenance dashboard error:",
            error
        );

        showError();
    }
}


/* =========================================================
   KPIs
========================================================= */

function updateKPIs(kpis) {

    setText(
        "assetsMonitored",
        kpis.assets_monitored ?? 0
    );


    setText(
        "faultsDetected",
        kpis.faults_detected ?? 0
    );


    setText(
        "maintenanceRecommendations",
        kpis.maintenance_recommendations ?? 0
    );


    setText(
        "averageHealth",
        Number(
            kpis.average_health ?? 0
        ).toFixed(1)
    );


    setText(
        "highRiskAssets",
        kpis.high_risk_assets ?? 0
    );


    setText(
        "deterioratingAssets",
        kpis.deteriorating_assets ?? 0
    );
}


/* =========================================================
   HEALTH DISTRIBUTION
========================================================= */

function updateHealthDistribution(
    distribution
) {

    const container =
        document.getElementById(
            "healthDistribution"
        );


    if (!container) {
        return;
    }


    container.innerHTML =
        distribution.map(item => {

            const category =
                safeClass(
                    item.category
                );


            return `
                <div
                    class="health-card ${category}"
                >

                    <div class="category">
                        ${escapeHtml(
                            item.category
                        )}
                    </div>

                    <div class="count">
                        ${Number(
                            item.count || 0
                        )}
                    </div>

                    <div class="percentage">
                        ${Number(
                            item.percentage || 0
                        ).toFixed(1)}%
                    </div>

                </div>
            `;

        }).join("");
}


/* =========================================================
   HEALTH SCORE CHART
========================================================= */

function updateHealthScoreChart(
    assets
) {

    const canvas =
        document.getElementById(
            "healthScoreChart"
        );


    if (
        !canvas ||
        !assets.length ||
        typeof Chart === "undefined"
    ) {
        return;
    }


    if (healthScoreChart) {
        healthScoreChart.destroy();
    }


    healthScoreChart =
        new Chart(
            canvas,
            {

                type: "bar",

                data: {

                    labels:
                        assets.map(
                            asset =>
                                asset.asset_id
                        ),

                    datasets: [

                        {
                            label:
                                "Health Score",

                            data:
                                assets.map(
                                    asset =>
                                        Number(
                                            asset.health_score || 0
                                        )
                                ),

                            borderWidth: 1
                        }

                    ]
                },


                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    scales: {

                        y: {

                            beginAtZero: true,

                            max: 100,

                            title: {

                                display: true,

                                text:
                                    "Health Score"
                            }
                        }
                    },

                    plugins: {

                        legend: {
                            display: false
                        }
                    }
                }
            }
        );
}


/* =========================================================
   FUTURE CONDITION CHART
========================================================= */

function updateFutureConditionChart(
    assets
) {

    const canvas =
        document.getElementById(
            "futureConditionChart"
        );


    if (
        !canvas ||
        !assets.length ||
        typeof Chart === "undefined"
    ) {
        return;
    }


    const counts = {

        Improving: 0,

        Stable: 0,

        Deteriorating: 0,

        Unavailable: 0
    };


    assets.forEach(
        asset => {

            const condition =
                asset.future_condition;


            if (
                counts.hasOwnProperty(
                    condition
                )
            ) {

                counts[
                    condition
                ]++;

            }

        }
    );


    if (futureConditionChart) {
        futureConditionChart.destroy();
    }


    futureConditionChart =
        new Chart(
            canvas,
            {

                type: "bar",

                data: {

                    labels: [
                        "Improving",
                        "Stable",
                        "Deteriorating",
                        "Unavailable"
                    ],

                    datasets: [

                        {
                            label:
                                "Assets",

                            data: [
                                counts.Improving,
                                counts.Stable,
                                counts.Deteriorating,
                                counts.Unavailable
                            ],

                            borderWidth: 1
                        }

                    ]
                },


                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    scales: {

                        y: {

                            beginAtZero: true,

                            ticks: {
                                precision: 0
                            },

                            title: {

                                display: true,

                                text:
                                    "Number of Assets"
                            }
                        }
                    }
                }
            }
        );
}


/* =========================================================
   ALERTS
========================================================= */

function updateAlerts(
    alerts
) {

    const tbody =
        document.getElementById(
            "alertsTableBody"
        );


    if (!tbody) {
        return;
    }


    if (!alerts.length) {

        tbody.innerHTML = `
            <tr>
                <td
                    colspan="6"
                    class="empty-state"
                >
                    No maintenance alerts.
                </td>
            </tr>
        `;

        return;
    }


    tbody.innerHTML =
        alerts.map(asset => {

            return `
                <tr>

                    <td>
                        ${escapeHtml(
                            asset.asset_id
                        )}
                    </td>

                    <td>
                        ${Number(
                            asset.health_score || 0
                        ).toFixed(1)}
                    </td>

                    <td>
                        ${Number(
                            asset.maintenance_risk || 0
                        ).toFixed(1)}
                    </td>

                    <td>
                        ${escapeHtml(
                            asset.future_condition ||
                            "Stable"
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            asset.priority ||
                            "Low"
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            asset.recommendation ||
                            asset.prediction_recommendation ||
                            "Continue monitoring."
                        )}
                    </td>

                </tr>
            `;

        }).join("");
}


/* =========================================================
   SCHEDULE
========================================================= */

function updateSchedule(
    schedule
) {

    const tbody =
        document.getElementById(
            "scheduleTableBody"
        );


    if (!tbody) {
        return;
    }


    if (!schedule.length) {

        tbody.innerHTML = `
            <tr>
                <td
                    colspan="5"
                    class="empty-state"
                >
                    No maintenance actions currently
                    required.
                </td>
            </tr>
        `;

        return;
    }


    tbody.innerHTML =
        schedule.map(asset => {

            const status = asset.work_order_status || "Action required";

            return `
                <tr>

                    <td>
                        ${escapeHtml(
                            asset.asset_id
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            asset.priority
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            asset.maintenance_due ||
                            "Inspection"
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            asset.maintenance_window ||
                            "-"
                        )}
                    </td>

                    <td>
                        ${escapeHtml(status)}
                    </td>

                </tr>
            `;

        }).join("");
}


/* =========================================================
   ASSETS
========================================================= */

function updateAssets(
    assets
) {

    const tbody =
        document.getElementById(
            "assetsTableBody"
        );


    if (!tbody) {
        return;
    }


    tbody.innerHTML =
        assets.map(asset => {

            return `
                <tr>

                    <td>
                        ${escapeHtml(
                            asset.asset_id
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            asset.equipment_type ||
                            "HVAC"
                        )}
                    </td>

                    <td>
                        ${Number(
                            asset.health_score || 0
                        ).toFixed(1)}
                    </td>

                    <td>
                        ${Number(
                            asset.maintenance_risk || 0
                        ).toFixed(1)}
                    </td>

                    <td>
                        ${escapeHtml(
                            asset.health_category
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            asset.future_condition ||
                            "Stable"
                        )}
                    </td>

                    <td>
                        ${Number(
                            asset.observations || 0
                        )}
                    </td>

                    <td>
                        ${formatDate(
                            asset.timestamp
                        )}
                    </td>

                </tr>
            `;

        }).join("");
}


/* =========================================================
   WORK ORDERS
========================================================= */

function updateWorkOrders(
    schedule
) {

    const tbody =
        document.getElementById(
            "workOrdersTableBody"
        );


    if (!tbody) {
        return;
    }


    if (!schedule.length) {

        tbody.innerHTML = `
            <tr>
                <td
                    colspan="4"
                    class="empty-state"
                >
                    No work orders required.
                </td>
            </tr>
        `;

        return;
    }


    tbody.innerHTML =
        schedule.map(asset => {

            const status = asset.work_order_status || "Action required";

            return `
                <tr>

                    <td>
                        ${escapeHtml(
                            asset.asset_id
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            asset.priority
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            asset.recommendation ||
                            "Inspection required."
                        )}
                    </td>

                    <td>
                        ${escapeHtml(status)}
                    </td>

                </tr>
            `;

        }).join("");
}


/* =========================================================
   SOURCE
========================================================= */

function updateSource(
    source,
    note
) {

    setText(
        "dataSource",

        source ||
        "Simulated facility sensor readings (digital twin demo)"
    );


    setText(
        "dataNote",

        note ||
        "Only live facility readings are used for maintenance health, alerts, and actions."
    );
}


/* =========================================================
   ERROR
========================================================= */

function showError() {

    setText(
        "assetsMonitored",
        0
    );

    setText(
        "faultsDetected",
        0
    );

    setText(
        "maintenanceRecommendations",
        0
    );

    setText(
        "averageHealth",
        0
    );

    setText(
        "highRiskAssets",
        0
    );

    setText(
        "deterioratingAssets",
        0
    );


    const distribution =
        document.getElementById(
            "healthDistribution"
        );


    if (distribution) {

        distribution.innerHTML = `
            <div class="loading">
                Unable to load health data.
            </div>
        `;
    }


    const alerts =
        document.getElementById(
            "alertsTableBody"
        );


    if (alerts) {

        alerts.innerHTML = `
            <tr>
                <td
                    colspan="6"
                    class="loading"
                >
                    Unable to load maintenance data.
                </td>
            </tr>
        `;
    }
}


/* =========================================================
   HELPERS
========================================================= */

function setText(
    id,
    value
) {

    const element =
        document.getElementById(id);


    if (element) {
        element.textContent = value;
    }
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


function formatDate(
    value
) {

    if (!value) {
        return "-";
    }


    const date =
        new Date(value);


    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return String(value);
    }


    return date.toLocaleString();
}