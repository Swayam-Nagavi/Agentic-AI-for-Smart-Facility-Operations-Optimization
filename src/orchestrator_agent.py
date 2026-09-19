"""
Milestone 4 — Multi-Agent Operations Orchestrator
-------------------------------------------------

Coordinates the Energy, Maintenance, Occupancy, and Security agents into a
single operations command layer. The orchestrator does not create independent
sensor readings; it receives each agent's dashboard output and converts those
results into cross-agent scores, prioritized actions, guardrails, and a concise
operations timeline.
"""

AGENT_LABELS = {
    "energy": "Energy Agent",
    "maintenance": "Maintenance Agent",
    "occupancy": "Occupancy Agent",
    "security": "Security Agent",
}

PRIORITY_WEIGHT = {
    "Critical": 4,
    "High": 3,
    "Medium": 2,
    "Low": 1,
    "Info": 0,
}


def build_operations_dashboard(energy, maintenance, occupancy, security):
    """Return the unified Milestone 4 operations dashboard payload."""

    domain_scores = _build_domain_scores(
        energy,
        maintenance,
        occupancy,
        security,
    )

    facility_score = _weighted_facility_score(domain_scores)
    actions = _build_actions(energy, maintenance, occupancy, security)
    insights = _build_cross_agent_insights(energy, maintenance, occupancy, security)
    guardrails = _build_guardrails(energy, maintenance, occupancy, security)
    timeline = _build_timeline(energy, maintenance, occupancy, security)
    as_of = _latest_data_timestamp(energy, occupancy, security)
    decision_log = _build_decision_log(actions, domain_scores, as_of=as_of)

    critical_actions = [
        action for action in actions
        if action["priority"] == "Critical"
    ]

    high_priority_actions = [
        action for action in actions
        if action["priority"] in ("Critical", "High")
    ]

    active_alerts = (
        _number(energy.get("kpis", {}).get("anomalies"))
        + _number(maintenance.get("kpis", {}).get("faults_detected"))
        + len(occupancy.get("capacity_alerts", []))
        + _number(security.get("kpis", {}).get("active_alerts"))
    )

    automation_readiness = _automation_readiness_score(
        facility_score,
        actions,
        guardrails,
    )

    return {
        "available": True,
        "kpis": {
            "facility_score": facility_score,
            "facility_status": _facility_status(facility_score),
            "coordinated_agents": len(AGENT_LABELS),
            "active_alerts": int(active_alerts),
            "critical_actions": len(critical_actions),
            "high_priority_actions": len(high_priority_actions),
            "automation_readiness": automation_readiness,
        },
        "domain_scores": domain_scores,
        "agent_status": _build_agent_status(
            energy,
            maintenance,
            occupancy,
            security,
            domain_scores,
        ),
        "actions": actions,
        "cross_agent_insights": insights,
        "guardrails": guardrails,
        "decision_log": decision_log,
        "timeline": timeline,
        "data_as_of": as_of,
        "data_source": "Simulated facility intelligence layer (digital twin demo)",
        "note": (
            "Milestone 4 coordinates all facility agents into one prioritized "
            "operations view with safety, comfort, energy, maintenance, and "
            "security guardrails."
        ),
    }


# ============================================================
# SCORE MODEL
# ============================================================

def _build_domain_scores(energy, maintenance, occupancy, security):
    energy_score = _clamp(
        _number(energy.get("kpis", {}).get("efficiency_score")),
        0,
        100,
    )

    maintenance_score = _clamp(
        _number(maintenance.get("kpis", {}).get("average_health")),
        0,
        100,
    )

    occupancy_score = _occupancy_score(occupancy)
    security_score = _security_score(security)

    return [
        {
            "domain": "Energy",
            "score": round(energy_score, 1),
            "status": _facility_status(energy_score),
            "weight": 30,
            "summary": _energy_score_summary(energy),
        },
        {
            "domain": "Maintenance",
            "score": round(maintenance_score, 1),
            "status": _facility_status(maintenance_score),
            "weight": 30,
            "summary": _maintenance_score_summary(maintenance),
        },
        {
            "domain": "Occupancy",
            "score": round(occupancy_score, 1),
            "status": _facility_status(occupancy_score),
            "weight": 20,
            "summary": _occupancy_score_summary(occupancy),
        },
        {
            "domain": "Security",
            "score": round(security_score, 1),
            "status": _facility_status(security_score),
            "weight": 20,
            "summary": _security_score_summary(security),
        },
    ]


def _weighted_facility_score(domain_scores):
    total_weight = sum(_number(item.get("weight")) for item in domain_scores)

    if total_weight <= 0:
        return 0.0

    score = sum(
        _number(item.get("score")) * _number(item.get("weight"))
        for item in domain_scores
    ) / total_weight

    return round(_clamp(score, 0, 100), 1)


def _occupancy_score(occupancy):
    kpis = occupancy.get("kpis", {})
    occupancy_rate = kpis.get("occupancy_rate")

    if occupancy_rate is None:
        score = 78.0
    else:
        rate = _number(occupancy_rate)
        # Balanced utilization is considered healthy. Very low utilization wastes
        # space, while very high utilization can create comfort and safety issues.
        score = 100 - abs(rate - 55) * 0.35

        if rate > 90:
            score -= (rate - 90) * 1.2
        elif rate < 15:
            score -= (15 - rate) * 0.5

    # Penalize CURRENT crowding using the latest per-room status, not the
    # all-day peak-based capacity_alerts list (which flags nearly every room
    # at some point in 24h and previously drove this score to 0).
    penalty = 0.0

    for room in occupancy.get("rooms", []):
        status = room.get("status")

        if status == "Over Capacity":
            penalty += 15
        elif status == "Near Capacity":
            penalty += 5

    score -= min(penalty, 50)

    return _clamp(score, 0, 100)


def _security_score(security):
    kpis = security.get("kpis", {})

    unauthorized_rate = _number(kpis.get("unauthorized_rate"))
    high_risk = _number(kpis.get("high_risk_events"))
    critical = _number(kpis.get("critical_alerts"))

    score = 100
    score -= unauthorized_rate * 0.35
    score -= high_risk * 2.5
    score -= critical * 4.0

    return _clamp(score, 0, 100)


def _automation_readiness_score(facility_score, actions, guardrails):
    score = facility_score

    for action in actions:
        if action["priority"] == "Critical":
            score -= 5
        elif action["priority"] == "High":
            score -= 2

    blocking_guardrails = [
        guardrail for guardrail in guardrails
        if guardrail.get("level") in ("Critical", "High")
    ]

    score -= len(blocking_guardrails) * 2

    return round(_clamp(score, 0, 100), 1)


def _facility_status(score):
    score = _number(score)

    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Warning"
    return "Critical"


# ============================================================
# AGENT STATUS
# ============================================================

def _build_agent_status(energy, maintenance, occupancy, security, domain_scores):
    score_map = {
        item["domain"]: item
        for item in domain_scores
    }

    energy_kpis = energy.get("kpis", {})
    maintenance_kpis = maintenance.get("kpis", {})
    occupancy_kpis = occupancy.get("kpis", {})
    security_kpis = security.get("kpis", {})

    return [
        {
            "agent": AGENT_LABELS["energy"],
            "status": score_map["Energy"]["status"],
            "score": score_map["Energy"]["score"],
            "primary_metric": f"{_number(energy_kpis.get('total_energy')):.2f} kWh",
            "secondary_metric": f"{_number(energy_kpis.get('anomalies')):.0f} anomalies",
            "summary": score_map["Energy"]["summary"],
        },
        {
            "agent": AGENT_LABELS["maintenance"],
            "status": score_map["Maintenance"]["status"],
            "score": score_map["Maintenance"]["score"],
            "primary_metric": f"{_number(maintenance_kpis.get('average_health')):.1f} average health",
            "secondary_metric": f"{_number(maintenance_kpis.get('faults_detected')):.0f} current faults",
            "summary": score_map["Maintenance"]["summary"],
        },
        {
            "agent": AGENT_LABELS["occupancy"],
            "status": score_map["Occupancy"]["status"],
            "score": score_map["Occupancy"]["score"],
            "primary_metric": f"{_number(occupancy_kpis.get('current_occupancy')):.0f} occupants",
            "secondary_metric": f"{_number(occupancy_kpis.get('vacant_rooms')):.0f} vacant rooms",
            "summary": score_map["Occupancy"]["summary"],
        },
        {
            "agent": AGENT_LABELS["security"],
            "status": score_map["Security"]["status"],
            "score": score_map["Security"]["score"],
            "primary_metric": f"{_number(security_kpis.get('active_alerts')):.0f} active alerts",
            "secondary_metric": f"{_number(security_kpis.get('critical_alerts')):.0f} critical events",
            "summary": score_map["Security"]["summary"],
        },
    ]


# ============================================================
# ACTIONS AND INSIGHTS
# ============================================================

def _build_actions(energy, maintenance, occupancy, security):
    actions = []

    for asset in maintenance.get("alerts", [])[:6]:
        priority = _priority_from_health(asset.get("health_category"), asset.get("priority"))
        actions.append(_action(
            priority=priority,
            domain="Maintenance",
            source_agents=["Maintenance", "Energy"],
            title=f"Inspect {asset.get('asset_id', 'facility asset')}",
            recommended_action=asset.get("recommendation") or "Schedule maintenance inspection.",
            reason=(
                f"Health score {float(_number(asset.get('health_score'))):.1f}; "
                f"risk {float(_number(asset.get('maintenance_risk'))):.1f}."
            ),
            expected_impact="Protect equipment reliability and avoid efficiency loss.",
            automation_mode="Human approval required" if priority == "Critical" else "Ready for scheduling",
        ))

    for alert in occupancy.get("capacity_alerts", [])[:5]:
        priority = "High" if alert.get("severity") == "High" else "Medium"
        actions.append(_action(
            priority=priority,
            domain="Occupancy",
            source_agents=["Occupancy", "Energy", "Security"],
            title=f"Rebalance occupancy at {alert.get('building_id')} {alert.get('room_id')}",
            recommended_action="Redirect occupants or schedule an alternate room to keep comfort and safety levels stable.",
            reason=alert.get("message") or "Room utilization is near or above capacity.",
            expected_impact="Improves comfort, safety, and HVAC load balance.",
            automation_mode="Ready for scheduling",
        ))

    security_kpis = security.get("kpis", {})
    critical_alerts = int(_number(security_kpis.get("critical_alerts")))

    if critical_alerts > 0:
        actions.append(_action(
            priority="Critical",
            domain="Security",
            source_agents=["Security", "Occupancy"],
            title="Review critical access-control events",
            recommended_action="Escalate critical events to the security team and verify access permissions for affected areas.",
            reason=f"{critical_alerts} critical security event(s) require attention.",
            expected_impact="Reduces unauthorized-access risk and protects occupied spaces.",
            automation_mode="Human approval required",
        ))

    for recommendation in energy.get("recommendations", [])[:5]:
        recommendation_type = recommendation.get("type", "Energy Optimization")
        priority = _normalise_priority(recommendation.get("priority"))
        target = recommendation.get("target")
        title = (
            f"{recommendation_type} — {target}"
            if target
            else recommendation_type
        )

        actions.append(_action(
            priority=priority,
            domain="Energy",
            source_agents=["Energy", "Occupancy", "Maintenance"],
            title=title,
            recommended_action=recommendation.get("message") or "Review energy optimization opportunity.",
            reason=recommendation.get("reason") or "Energy agent identified an optimization opportunity.",
            expected_impact="Reduces avoidable consumption while preserving comfort guardrails.",
            automation_mode="Ready for automation" if priority in ("Low", "Medium") else "Human approval required",
        ))

    actions = _dedupe_actions(actions)
    actions.sort(
        key=lambda item: (
            PRIORITY_WEIGHT.get(item["priority"], 0),
            item["domain"],
            item["title"],
        ),
        reverse=True,
    )

    if not actions:
        actions.append(_action(
            priority="Low",
            domain="Operations",
            source_agents=list(AGENT_LABELS.values()),
            title="Continue coordinated monitoring",
            recommended_action="Maintain current operating plan and keep all agents active.",
            reason="No high-risk condition is currently detected.",
            expected_impact="Sustains normal facility performance.",
            automation_mode="Autonomous monitoring",
        ))

    for index, action in enumerate(actions, start=1):
        action["action_id"] = f"ACT-{index:03d}"

    return actions[:14]


def _build_cross_agent_insights(energy, maintenance, occupancy, security):
    insights = []

    energy_kpis = energy.get("kpis", {})
    maintenance_kpis = maintenance.get("kpis", {})
    occupancy_kpis = occupancy.get("kpis", {})
    security_kpis = security.get("kpis", {})

    if _number(energy_kpis.get("anomalies")) > 0 and _number(maintenance_kpis.get("faults_detected")) > 0:
        insights.append({
            "title": "Energy and maintenance signals overlap",
            "severity": "High",
            "message": (
                "Energy anomalies are present while maintenance alerts are active. "
                "Prioritize equipment inspections before applying aggressive energy reductions."
            ),
        })

    status_counts = _occupancy_status_counts(occupancy)

    if status_counts.get("Over Capacity", 0) > 0:
        insights.append({
            "title": "Over-capacity area detected",
            "severity": "High",
            "message": (
                f"{status_counts['Over Capacity']} room(s) are over capacity. "
                "Coordinate space reassignment with HVAC and security coverage."
            ),
        })

    if status_counts.get("Vacant", 0) > 0 and _has_energy_recommendation(energy, "HVAC Scheduling"):
        insights.append({
            "title": "Vacant rooms and HVAC scheduling",
            "severity": "Medium",
            "message": (
                "Vacant rooms are present and HVAC optimization is available. "
                "Apply savings only where comfort and equipment guardrails allow it."
            ),
        })

    if _number(security_kpis.get("critical_alerts")) > 0 and _number(occupancy_kpis.get("current_occupancy")) > 0:
        insights.append({
            "title": "Security escalation affects occupied areas",
            "severity": "Critical",
            "message": (
                "Critical security events are active while the facility is occupied. "
                "Route response teams using occupancy visibility."
            ),
        })

    if not insights:
        insights.append({
            "title": "Facility operations stable",
            "severity": "Info",
            "message": "No cross-agent conflict requires escalation at this time.",
        })

    return insights


def _build_guardrails(energy, maintenance, occupancy, security):
    guardrails = []
    status_counts = _occupancy_status_counts(occupancy)

    if status_counts.get("High", 0) or status_counts.get("Near Capacity", 0) or status_counts.get("Over Capacity", 0):
        guardrails.append({
            "level": "High",
            "name": "Comfort protection",
            "rule": "Do not reduce cooling in highly occupied, near-capacity, or over-capacity rooms.",
        })

    if _number(maintenance.get("kpis", {}).get("faults_detected")) > 0:
        guardrails.append({
            "level": "High",
            "name": "Reliability protection",
            "rule": "Maintenance-critical equipment takes priority over non-urgent energy optimization.",
        })

    if _number(security.get("kpis", {}).get("critical_alerts")) > 0:
        guardrails.append({
            "level": "Critical",
            "name": "Security approval",
            "rule": "Critical security actions require human approval before automation changes access states.",
        })

    if _has_energy_recommendation(energy, "HVAC Scheduling"):
        guardrails.append({
            "level": "Medium",
            "name": "Energy automation limit",
            "rule": "HVAC schedule optimization is allowed only for unoccupied or low-impact spaces.",
        })

    if not guardrails:
        guardrails.append({
            "level": "Info",
            "name": "Normal automation",
            "rule": "All domains are within normal operating guardrails.",
        })

    return guardrails


def _build_decision_log(actions, domain_scores, as_of=None):
    # Timestamp decisions with the end of the data window they were derived
    # from — never with wall-clock "now", which would claim decisions were
    # made today about potentially stale sensor readings.
    now = as_of or "unknown"
    log = []

    if actions:
        top_action = actions[0]
        log.append({
            "timestamp": now,
            "decision": f"Prioritize {top_action['domain'].lower()} action {top_action['action_id']}",
            "rationale": top_action["reason"],
            "confidence": _confidence_from_priority(top_action["priority"]),
        })

    lowest_domain = min(domain_scores, key=lambda item: item["score"])
    log.append({
        "timestamp": now,
        "decision": f"Watch {lowest_domain['domain'].lower()} domain closely",
        "rationale": lowest_domain["summary"],
        "confidence": "Medium",
    })

    log.append({
        "timestamp": now,
        "decision": "Apply guardrail-first orchestration",
        "rationale": "Safety, comfort, equipment reliability, and security override savings-only decisions.",
        "confidence": "High",
    })

    return log


def _build_timeline(energy, maintenance, occupancy, security):
    timeline = []

    peak = energy.get("peak", {})
    if peak.get("timestamp"):
        timeline.append({
            "timestamp": peak.get("timestamp"),
            "type": "Energy",
            "title": "Peak energy event",
            "message": (
                f"{peak.get('building_id')} {peak.get('room_id')} reached "
                f"{float(_number(peak.get('energy'))):.2f} kWh."
            ),
            "severity": "Medium",
        })

    for asset in maintenance.get("alerts", [])[:3]:
        timeline.append({
            "timestamp": asset.get("timestamp"),
            "type": "Maintenance",
            "title": f"{asset.get('health_category', 'Health')} equipment condition",
            "message": f"{asset.get('asset_id')} requires {asset.get('maintenance_due', 'inspection')}.",
            "severity": _priority_from_health(asset.get("health_category"), asset.get("priority")),
        })

    for room in occupancy.get("rooms", [])[:25]:
        if room.get("status") in ("High", "Near Capacity", "Over Capacity"):
            timeline.append({
                "timestamp": room.get("timestamp"),
                "type": "Occupancy",
                "title": f"{room.get('status')} occupancy",
                "message": (
                    f"{room.get('building_id')} {room.get('room_id')} has "
                    f"{room.get('occupancy')} occupant(s)."
                ),
                "severity": "High" if room.get("status") == "Over Capacity" else "Medium",
            })

    for event in security.get("high_risk_events", [])[:4]:
        timeline.append({
            "timestamp": event.get("timestamp"),
            "type": "Security",
            "title": event.get("event_type", "Security event"),
            "message": f"{event.get('building_id')} {event.get('room_id')} reported {event.get('severity')} severity.",
            "severity": event.get("severity", "High"),
        })

    timeline.sort(
        key=lambda item: str(item.get("timestamp") or ""),
        reverse=True,
    )

    return timeline[:12]


# ============================================================
# SUMMARIES
# ============================================================

def _energy_score_summary(energy):
    kpis = energy.get("kpis", {})
    return (
        f"Efficiency {_number(kpis.get('efficiency_score')):.1f}% with "
        f"{int(_number(kpis.get('anomalies')))} anomaly signal(s)."
    )


def _maintenance_score_summary(maintenance):
    kpis = maintenance.get("kpis", {})
    return (
        f"Average health {_number(kpis.get('average_health')):.1f} with "
        f"{int(_number(kpis.get('faults_detected')))} active fault signal(s)."
    )


def _occupancy_score_summary(occupancy):
    kpis = occupancy.get("kpis", {})
    rate = kpis.get("occupancy_rate")
    rate_text = "capacity unavailable" if rate is None else f"{float(_number(rate)):.1f}% utilization"
    return (
        f"{int(_number(kpis.get('occupied_rooms')))} occupied room(s), "
        f"{int(_number(kpis.get('vacant_rooms')))} vacant room(s), {rate_text}."
    )


def _security_score_summary(security):
    kpis = security.get("kpis", {})
    return (
        f"{int(_number(kpis.get('active_alerts')))} active alert(s), "
        f"{int(_number(kpis.get('critical_alerts')))} critical event(s)."
    )


# ============================================================
# GENERAL HELPERS
# ============================================================

def _action(
    priority,
    domain,
    source_agents,
    title,
    recommended_action,
    reason,
    expected_impact,
    automation_mode,
):
    return {
        "action_id": "",
        "priority": _normalise_priority(priority),
        "domain": domain,
        "source_agents": source_agents,
        "title": title,
        "recommended_action": recommended_action,
        "reason": reason,
        "expected_impact": expected_impact,
        "automation_mode": automation_mode,
        "status": "Recommended",
    }


def _dedupe_actions(actions):
    seen = set()
    result = []

    for action in actions:
        key = (
            action.get("domain"),
            action.get("title"),
            action.get("recommended_action"),
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(action)

    return result


def _occupancy_status_counts(occupancy):
    counts = {}

    for room in occupancy.get("rooms", []):
        status = room.get("status") or "Unknown"
        counts[status] = counts.get(status, 0) + 1

    return counts


def _has_energy_recommendation(energy, recommendation_type):
    return any(
        recommendation.get("type") == recommendation_type
        for recommendation in energy.get("recommendations", [])
    )


def _priority_from_health(category, default_priority="Medium"):
    if category == "Critical":
        return "Critical"
    if category == "Warning":
        return "High"
    return _normalise_priority(default_priority)


def _normalise_priority(priority):
    value = str(priority or "Medium").title()
    return value if value in PRIORITY_WEIGHT else "Medium"


def _confidence_from_priority(priority):
    if priority == "Critical":
        return "High"
    if priority == "High":
        return "Medium-High"
    if priority == "Medium":
        return "Medium"
    return "Low"


def _number(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _latest_data_timestamp(energy, occupancy, security):
    """Latest timestamp present in the underlying data, across domains."""
    candidates = []

    for payload in (energy, occupancy, security):
        if not isinstance(payload, dict):
            continue

        end = payload.get("metadata", {}).get("end_timestamp")

        if end:
            candidates.append(str(end))

    return max(candidates) if candidates else None


def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))
