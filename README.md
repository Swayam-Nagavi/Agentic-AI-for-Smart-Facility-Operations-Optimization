# Agentic AI for Smart Facility Operations Optimization

A Flask-based multi-domain facility operations demo: five dashboards (Energy,
Maintenance, Occupancy, Security, and a unified Operations Command Center) that
analyze building sensor data, score facility health, and produce prioritized
recommendations.

> **Honest status: this is a simulated digital twin, built as a college/demo
> project.** All facility and security data is **synthetically generated**, not
> real sensor output. There is no building attached to this system. The
> "agents" are deterministic analytics modules (rules + two small Random
> Forest models), not autonomous AI agents. Do not present dashboard output as
> real facility telemetry or real equipment-failure data.

## What it actually does

| Dashboard | Data | Method |
|---|---|---|
| Energy | `facility_data.csv` (simulated) | Aggregations, baseline/σ-style anomaly rules, rule-based recommendations |
| Maintenance | `facility_data.csv` (simulated) | Hand-tuned rule health score (`src/health_scoring.py`) + a Random Forest that predicts the next reading's rule-score direction (improving/stable/deteriorating) |
| Occupancy | `facility_data.csv` (simulated) | Aggregations, capacity thresholds, utilization statuses |
| Security | `security_events.csv` (simulated) | Event classification, unauthorized-access counting |
| Operations | outputs of the four above | Weighted composite scores, cross-domain rules, prioritized action list |

Known limitations are tracked honestly in `CODE_REVIEW.md` (full audit,
including which recommendation metrics are rule-of-thumb constants).

## Quickstart

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # or: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open:

- Energy dashboard: `http://127.0.0.1:5000/`
- Maintenance: `http://127.0.0.1:5000/maintenance.html`
- Occupancy: `http://127.0.0.1:5000/occupancy.html`
- Security: `http://127.0.0.1:5000/security.html`
- Operations Command Center: `http://127.0.0.1:5000/operations.html`

If `facility_data.csv` / `security_events.csv` are missing or empty, the app
generates **simulated** rows and writes them to those files before rendering.

## API

| Endpoint | Returns |
|---|---|
| `/api/dashboard` | Energy dashboard payload |
| `/api/maintenance/dashboard` | Maintenance dashboard payload |
| `/api/occupancy`, `/api/occupancy/insights`, `/api/occupancy/rooms` | Occupancy |
| `/api/security`, `/api/security/alerts` | Security |
| `/api/orchestrator/dashboard`, `/api/orchestrator/actions` | Unified operations |
| `/api/health` | Liveness |

## Project layout

```
app.py                          Flask app + API routes
src/
  analytics.py                  CSV loading, energy aggregations, anomaly rules
  csv_data_manager.py           Ensures CSVs exist (generates simulated data)
  data_generator.py             Simulated facility digital-twin data generator
  security_data_generator.py    Simulated security-event generator
  energy_agent.py               Energy dashboard builder + recommendations
  maintenance_agent.py          Maintenance dashboard builder + alerts/schedule
  health_scoring.py             Rule-based condition-risk & health scoring
                                (single source of truth for the risk formula)
  occupancy_agent.py            Occupancy dashboard builder
  security_agent.py             Security dashboard builder
  orchestrator_agent.py         Cross-domain scores, actions, guardrails
  future_condition_model.py     Feature builder + inference for the
                                next-condition Random Forest
train_future_condition.py       Trains models/future_condition_model.pkl
                                from facility_data.csv
train_maintenance_model.py      OFFLINE EXPERIMENT ONLY: trains a binary
                                fault classifier on the LBNL RTU dataset
                                (data/lbnl). Not used by the running app.
static/                         Dashboard frontends (vanilla JS, no build step)
```

## Data provenance

- `facility_data.csv`, `security_events.csv` — **synthetic**, produced by the
  generators above for a fixed demo day.
- `data/lbnl/` — public LBNL simulated RTU (rooftop unit) fault cases
  (baseline + fouling/charge/pipe-pressure faults). Large; used only by the
  offline experiment script.

## Milestone docs

- `README_MILESTONE_2.md` — predictive-maintenance milestone notes
- `README_MILESTONE_4.md` — orchestrator milestone notes
- `CODE_REVIEW.md` — full independent audit of the codebase with a
  prioritized fix plan (Phase A cleanup applied; Phases B–D pending)
