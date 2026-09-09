async function loadDashboard() {

    try {

        const response =
            await fetch("/api/dashboard");


        if (!response.ok) {

            throw new Error(
                "Dashboard API request failed"
            );

        }


        const data =
            await response.json();


        // =====================================================
        // KPI VALUES
        // =====================================================

        document.getElementById(
            "totalEnergy"
        ).textContent =
            `${data.kpis.total_energy.toFixed(2)} kWh`;


        document.getElementById(
            "estimatedCost"
        ).textContent =
            `₹${data.kpis.estimated_cost.toFixed(2)}`;


        document.getElementById(
            "efficiencyScore"
        ).textContent =
            `${data.kpis.efficiency_score.toFixed(0)}%`;


        document.getElementById(
            "potentialSavings"
        ).textContent =
            `₹${data.kpis.potential_cost_savings.toFixed(2)}`;


        document.getElementById(
            "averageEnergy"
        ).textContent =
            `${data.kpis.average_interval_energy.toFixed(2)} kWh / 15 min`;


        document.getElementById(
            "peakEnergy"
        ).textContent =
            `${data.kpis.peak_usage.toFixed(2)} kWh / 15 min`;


        document.getElementById(
            "carbonReduction"
        ).textContent =
            `${data.kpis.potential_carbon_reduction.toFixed(2)} kg CO₂`;


        document.getElementById(
            "anomalyCount"
        ).textContent =
            data.kpis.anomalies;


        // =====================================================
        // RENDER DASHBOARD COMPONENTS
        // =====================================================

        renderDistribution(
            data.energy_distribution
        );


        renderBars(
            "buildingChart",
            data.building_energy,
            "building"
        );


        renderBars(
            "roomChart",
            data.room_energy,
            "label"
        );


        renderTrend(
            data.hourly_energy
        );


        renderPeak(
            data.peak
        );


        renderAnomalies(
            data.anomalies
        );


        renderRecommendations(
            data.recommendations
        );


    } catch (error) {

        console.error(
            "Dashboard error:",
            error
        );

    }

}


/* =========================================================
   ENERGY DISTRIBUTION
   ========================================================= */

function renderDistribution(items) {

    const container =
        document.getElementById(
            "energyDistribution"
        );


    container.innerHTML = "";


    if (
        !items ||
        items.length === 0
    ) {

        container.innerHTML =
            '<p class="muted">No energy distribution data available.</p>';

        return;

    }


    items.forEach(item => {

        const row =
            document.createElement(
                "div"
            );

        row.className =
            "distribution-row";


        // -----------------------------
        // Category + percentage
        // -----------------------------

        const top =
            document.createElement(
                "div"
            );

        top.className =
            "distribution-top";


        const label =
            document.createElement(
                "span"
            );

        label.textContent =
            item.category;


        const percentage =
            document.createElement(
                "span"
            );

        percentage.textContent =
            `${item.percentage.toFixed(1)}%`;


        top.append(
            label,
            percentage
        );


        // -----------------------------
        // Progress bar
        // -----------------------------

        const track =
            document.createElement(
                "div"
            );

        track.className =
            "distribution-track";


        const bar =
            document.createElement(
                "div"
            );

        bar.className =
            "distribution-bar";


        bar.style.width =
            `${item.percentage}%`;


        track.appendChild(
            bar
        );


        // -----------------------------
        // Energy value
        // -----------------------------

        const value =
            document.createElement(
                "div"
            );

        value.className =
            "distribution-value";


        value.textContent =
            `${item.energy.toFixed(2)} kWh / 24 hours`;


        row.append(
            top,
            track,
            value
        );


        container.appendChild(
            row
        );

    });

}


/* =========================================================
   BUILDING / ROOM BAR CHARTS
   ========================================================= */

function renderBars(
    elementId,
    items,
    labelKey
) {

    const container =
        document.getElementById(
            elementId
        );


    container.innerHTML = "";


    if (
        !items ||
        items.length === 0
    ) {

        container.innerHTML =
            '<p class="muted">No data available.</p>';

        return;

    }


    const max =
        Math.max(
            ...items.map(
                item => item.energy
            ),
            1
        );


    items.forEach(item => {

        const row =
            document.createElement(
                "div"
            );

        row.className =
            "bar-row";


        // -----------------------------
        // Label
        // -----------------------------

        const label =
            document.createElement(
                "span"
            );


        if (
            labelKey === "label"
        ) {

            const parts =
                item[labelKey].split(
                    " ("
                );


            if (
                parts.length > 1
            ) {

                label.innerHTML = `
                    ${parts[0]}<br>
                    (${parts[1]}
                `;

            } else {

                label.textContent =
                    item[labelKey];

            }

        } else {

            label.textContent =
                item[labelKey];

        }


        // -----------------------------
        // Bar
        // -----------------------------

        const track =
            document.createElement(
                "div"
            );

        track.className =
            "bar-track";


        const bar =
            document.createElement(
                "div"
            );

        bar.className =
            "bar";


        bar.style.width =
            `${(item.energy / max) * 100}%`;


        // -----------------------------
        // Value
        // -----------------------------

        const value =
            document.createElement(
                "span"
            );

        value.textContent =
            `${item.energy.toFixed(2)} kWh`;


        track.appendChild(
            bar
        );


        row.append(
            label,
            track,
            value
        );


        container.appendChild(
            row
        );

    });

}


/* =========================================================
   HOURLY ENERGY TREND
   ========================================================= */

function renderTrend(items) {

    const svg =
        document.getElementById(
            "trendChart"
        );


    const tooltip =
        document.getElementById(
            "energyTooltip"
        );


    svg.innerHTML = "";


    if (
        !items ||
        !items.length
    ) {

        return;

    }


    const width = 760;
    const height = 380;


    const left = 65;
    const right = 25;
    const top = 25;
    const bottom = 75;


    const chartWidth =
        width - left - right;


    const chartHeight =
        height - top - bottom;


    const maxEnergy =
        Math.max(
            ...items.map(
                item => item.energy
            )
        );


    const max =
        Math.max(
            Math.ceil(
                maxEnergy / 5
            ) * 5,
            5
        );


    // =====================================================
    // Y AXIS
    // =====================================================

    const yAxis =
        document.createElementNS(
            "http://www.w3.org/2000/svg",
            "line"
        );


    yAxis.setAttribute(
        "x1",
        left
    );


    yAxis.setAttribute(
        "y1",
        top
    );


    yAxis.setAttribute(
        "x2",
        left
    );


    yAxis.setAttribute(
        "y2",
        height - bottom
    );


    yAxis.setAttribute(
        "stroke",
        "#777"
    );


    svg.appendChild(
        yAxis
    );


    // =====================================================
    // X AXIS
    // =====================================================

    const xAxis =
        document.createElementNS(
            "http://www.w3.org/2000/svg",
            "line"
        );


    xAxis.setAttribute(
        "x1",
        left
    );


    xAxis.setAttribute(
        "y1",
        height - bottom
    );


    xAxis.setAttribute(
        "x2",
        width - right
    );


    xAxis.setAttribute(
        "y2",
        height - bottom
    );


    xAxis.setAttribute(
        "stroke",
        "#777"
    );


    svg.appendChild(
        xAxis
    );


    // =====================================================
    // Y AXIS TITLE
    // =====================================================

    const yTitle =
        document.createElementNS(
            "http://www.w3.org/2000/svg",
            "text"
        );


    yTitle.setAttribute(
        "x",
        5
    );


    yTitle.setAttribute(
        "y",
        15
    );


    yTitle.textContent =
        "Energy (kWh / hour)";


    yTitle.setAttribute(
        "font-size",
        "12"
    );


    svg.appendChild(
        yTitle
    );


    // =====================================================
    // X AXIS TITLE
    // =====================================================

    const xTitle =
        document.createElementNS(
            "http://www.w3.org/2000/svg",
            "text"
        );


    xTitle.setAttribute(
        "x",
        width - right
    );


    xTitle.setAttribute(
        "y",
        height - 15
    );


    xTitle.setAttribute(
        "text-anchor",
        "end"
    );


    xTitle.textContent =
        "Time";


    xTitle.setAttribute(
        "font-size",
        "12"
    );


    svg.appendChild(
        xTitle
    );


    // =====================================================
    // Y AXIS GRID
    // =====================================================

    for (
        let i = 0;
        i <= 4;
        i++
    ) {

        const value =
            (max / 4) * i;


        const y =
            height -
            bottom -
            (
                value /
                max
            ) *
            chartHeight;


        const grid =
            document.createElementNS(
                "http://www.w3.org/2000/svg",
                "line"
            );


        grid.setAttribute(
            "x1",
            left
        );


        grid.setAttribute(
            "y1",
            y
        );


        grid.setAttribute(
            "x2",
            width - right
        );


        grid.setAttribute(
            "y2",
            y
        );


        grid.setAttribute(
            "stroke",
            "#e5e9f0"
        );


        svg.appendChild(
            grid
        );


        const label =
            document.createElementNS(
                "http://www.w3.org/2000/svg",
                "text"
            );


        label.setAttribute(
            "x",
            left - 10
        );


        label.setAttribute(
            "y",
            y + 4
        );


        label.setAttribute(
            "text-anchor",
            "end"
        );


        label.textContent =
            value.toFixed(1);


        label.setAttribute(
            "font-size",
            "11"
        );


        svg.appendChild(
            label
        );

    }


    // =====================================================
    // GRAPH POINTS
    // =====================================================

    const points =
        items.map(
            (item, index) => {

                const x =
                    left +
                    (
                        index /
                        Math.max(
                            items.length - 1,
                            1
                        )
                    ) *
                    chartWidth;


                const y =
                    height -
                    bottom -
                    (
                        item.energy /
                        max
                    ) *
                    chartHeight;


                return {
                    x,
                    y,
                    item
                };

            }
        );


    // =====================================================
    // TIME LABELS
    // =====================================================

    points.forEach(
        (point, index) => {

            if (
                index % 2 !== 0
            ) {

                return;

            }


            const date =
                new Date(
                    point.item.time
                );


            const time =
                date.toLocaleTimeString(
                    [],
                    {
                        hour: "2-digit",
                        minute: "2-digit",
                        hour12: false
                    }
                );


            const tick =
                document.createElementNS(
                    "http://www.w3.org/2000/svg",
                    "line"
                );


            tick.setAttribute(
                "x1",
                point.x
            );


            tick.setAttribute(
                "y1",
                height - bottom
            );


            tick.setAttribute(
                "x2",
                point.x
            );


            tick.setAttribute(
                "y2",
                height - bottom + 6
            );


            tick.setAttribute(
                "stroke",
                "#777"
            );


            svg.appendChild(
                tick
            );


            const label =
                document.createElementNS(
                    "http://www.w3.org/2000/svg",
                    "text"
                );


            label.setAttribute(
                "x",
                point.x
            );


            label.setAttribute(
                "y",
                height - bottom + 25
            );


            label.setAttribute(
                "text-anchor",
                "middle"
            );


            label.textContent =
                time;


            label.setAttribute(
                "font-size",
                "11"
            );


            svg.appendChild(
                label
            );

        }
    );


    // =====================================================
    // ENERGY LINE
    // =====================================================

    const line =
        document.createElementNS(
            "http://www.w3.org/2000/svg",
            "polyline"
        );


    line.setAttribute(
        "points",
        points
            .map(
                point =>
                    `${point.x},${point.y}`
            )
            .join(" ")
    );


    line.setAttribute(
        "fill",
        "none"
    );


    line.setAttribute(
        "stroke",
        "#3b82f6"
    );


    line.setAttribute(
        "stroke-width",
        "3"
    );


    svg.appendChild(
        line
    );


    // =====================================================
    // POINTS + TOOLTIP
    // =====================================================

    points.forEach(
        point => {

            const dot =
                document.createElementNS(
                    "http://www.w3.org/2000/svg",
                    "circle"
                );


            dot.setAttribute(
                "cx",
                point.x
            );


            dot.setAttribute(
                "cy",
                point.y
            );


            dot.setAttribute(
                "r",
                "4"
            );


            dot.setAttribute(
                "fill",
                "#3b82f6"
            );


            dot.style.cursor =
                "pointer";


            dot.addEventListener(
                "mouseenter",
                event => {

                    const date =
                        new Date(
                            point.item.time
                        );


                    const time =
                        date.toLocaleTimeString(
                            [],
                            {
                                hour: "2-digit",
                                minute: "2-digit",
                                hour12: false
                            }
                        );


                    tooltip.innerHTML = `

                        <strong>
                            Time:
                        </strong>
                        ${time}

                        <br>

                        <strong>
                            Total:
                        </strong>
                        ${point.item.energy.toFixed(2)}
                        kWh / hour

                        <br>

                        <strong>
                            B001:
                        </strong>
                        ${point.item.B001.toFixed(2)}
                        kWh / hour

                        <br>

                        <strong>
                            B002:
                        </strong>
                        ${point.item.B002.toFixed(2)}
                        kWh / hour

                        <br>

                        <strong>
                            B003:
                        </strong>
                        ${point.item.B003.toFixed(2)}
                        kWh / hour

                    `;


                    tooltip.style.display =
                        "block";


                    tooltip.style.left =
                        `${event.clientX + 12}px`;


                    tooltip.style.top =
                        `${event.clientY + 12}px`;

                }
            );


            dot.addEventListener(
                "mousemove",
                event => {

                    tooltip.style.left =
                        `${event.clientX + 12}px`;


                    tooltip.style.top =
                        `${event.clientY + 12}px`;

                }
            );


            dot.addEventListener(
                "mouseleave",
                () => {

                    tooltip.style.display =
                        "none";

                }
            );


            svg.appendChild(
                dot
            );

        }
    );

}


/* =========================================================
   PEAK USAGE
   ========================================================= */

function renderPeak(peak) {

    document.getElementById(
        "peakDetails"
    ).innerHTML = `

        <div>
            <b>Building:</b>
            ${peak.building_id}
        </div>

        <div>
            <b>Room:</b>
            ${peak.room_id}
            (${peak.room_type})
        </div>

        <div>
            <b>Time:</b>
            ${formatDate(
                peak.timestamp
            )}
        </div>

        <div>
            <b>Peak Energy:</b>
            ${peak.energy.toFixed(2)}
            kWh / 15 min
        </div>

    `;

}


/* =========================================================
   ANOMALIES
   ========================================================= */

function renderAnomalies(
    anomalies
) {

    const container =
        document.getElementById(
            "anomalies"
        );


    if (
        !anomalies ||
        !anomalies.length
    ) {

        container.innerHTML =
            '<p class="muted">' +
            'No significant energy anomalies detected.' +
            '</p>';

        return;

    }


    const rows =
        anomalies
            .map(
                item => `

                    <tr>

                        <td>
                            ${item.building}
                        </td>

                        <td>
                            ${item.room}
                        </td>

                        <td>
                            ${item.room_type}
                        </td>

                        <td>
                            ${formatDate(
                                item.timestamp
                            )}
                        </td>

                        <td>
                            ${item.energy.toFixed(2)}
                            kWh / 15 min
                        </td>

                        <td>
                            ${item.baseline.toFixed(2)}
                            kWh / 15 min
                        </td>

                        <td>
                            ${item.above_baseline.toFixed(1)}%
                        </td>

                    </tr>

                `
            )
            .join("");


    container.innerHTML = `

        <table>

            <thead>

                <tr>

                    <th>
                        Building
                    </th>

                    <th>
                        Room
                    </th>

                    <th>
                        Room Type
                    </th>

                    <th>
                        Timestamp
                    </th>

                    <th>
                        Energy
                        <br>
                        (kWh / 15 min)
                    </th>

                    <th>
                        Baseline
                        <br>
                        (kWh / 15 min)
                    </th>

                    <th>
                        Above Baseline
                    </th>

                </tr>

            </thead>


            <tbody>
                ${rows}
            </tbody>

        </table>

    `;

}


/* =========================================================
   ENERGY AGENT RECOMMENDATIONS
   ========================================================= */

function renderRecommendations(
    recommendations
) {

    const container =
        document.getElementById(
            "recommendations"
        );


    container.innerHTML = "";


    if (
        !recommendations ||
        !recommendations.length
    ) {

        container.innerHTML =
            '<p class="muted">' +
            'No recommendations available.' +
            '</p>';

        return;

    }


    recommendations.forEach(
        item => {

            const alert =
                document.createElement(
                    "div"
                );


            alert.className =
                `alert ${item.priority.toLowerCase()}`;


            alert.innerHTML = `

                <div class="alert-title">

                    ${item.priority}
                    •
                    ${item.type}

                </div>


                <div>
                    ${item.message}
                </div>


                <div class="muted">

                    Reason:
                    ${item.reason}

                </div>

            `;


            container.appendChild(
                alert
            );

        }
    );

}


/* =========================================================
   DATE FORMAT
   ========================================================= */

function formatDate(
    value
) {

    return new Date(
        value
    ).toLocaleString();

}


/* =========================================================
   INITIAL LOAD
   ========================================================= */

loadDashboard();


/*
 * Refresh dashboard every 30 seconds.
 */

setInterval(
    loadDashboard,
    30000
);