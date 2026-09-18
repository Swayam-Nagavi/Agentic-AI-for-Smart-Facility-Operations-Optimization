# Milestone 4 — Multi-Agent Operations Orchestrator

Milestone 4 adds a unified Operations Command Center that coordinates the Energy,
Maintenance, Occupancy, and Security agents.

## What was added

- Multi-agent orchestration module: `src/orchestrator_agent.py`
- Unified operations API: `/api/orchestrator/dashboard`
- Prioritized actions API: `/api/orchestrator/actions`
- Operations Command Center dashboard: `/operations.html`
- Cross-agent domain scoring for energy, maintenance, occupancy, and security
- Facility-level operations score and status
- Prioritized optimization actions with automation mode
- Cross-agent insights for overlapping risks
- Automation guardrails for comfort, reliability, and security
- Decision log and operations timeline

## Occupancy scenario coverage

The facility data generator now produces all room-occupancy cases represented in
the dashboard:

- Vacant
- Low occupancy
- Moderate occupancy
- High occupancy
- Near capacity
- Over capacity

The generator also enforces the facility rule that no more than four of the nine
rooms are vacant at the same timestamp. This means at least five rooms remain
occupied in every generated interval.

## Data-generation coverage

The data generators include examples needed by the dashboards and agents:

- Normal and abnormal energy usage
- HVAC-on while room is vacant
- Equipment Normal, Warning, and Fault states
- Maintenance health categories: Excellent, Good, Warning, Critical
- Future condition classes: Improving, Stable, Deteriorating
- Security Low, Medium, High, and Critical events
- Authorized and unauthorized access events

## Run the application

```powershell
python app.py
```

Open:

- Energy dashboard: `http://127.0.0.1:5000/`
- Maintenance dashboard: `http://127.0.0.1:5000/maintenance.html`
- Occupancy dashboard: `http://127.0.0.1:5000/occupancy.html`
- Security dashboard: `http://127.0.0.1:5000/security.html`
- Operations Command Center: `http://127.0.0.1:5000/operations.html`
