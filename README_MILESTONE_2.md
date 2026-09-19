# Milestone 2 — Predictive Maintenance System

This adds the predictive-maintenance layer to the existing Energy Intelligence project.

## What was added

- Asset-level equipment health scoring (0–100) via transparent, rules-based
  condition-risk scoring (`src/health_scoring.py`)
- Excellent / Good / Warning / Critical health categories
- Alerts (current-condition events) distinct from the maintenance schedule
  (forward-looking work plan, including assets predicted to deteriorate)
- A Random Forest "future condition" model that predicts whether the rule
  risk of the *next* reading improves / stays stable / deteriorates
- Work-order generation/tracking
- Predictive Maintenance Dashboard
- `/api/maintenance/dashboard` API

> **Status note (Phase A cleanup):** An earlier draft of this README claimed a
> "Random Forest failure-risk model" powered the dashboard. A fault classifier
> was trained on the public LBNL RTU dataset (`train_maintenance_model.py`),
> but it was **never wired into the running app**; the unused loader module
> and stale model artifacts were removed in Phase A. The trainer remains as a
> documented offline experiment. The dashboard's health scoring is rule-based.

> The maintenance data is synthetic and intended for a college/demo project. It must not be presented as real equipment-failure data.

## First-time setup in PowerShell

```powershell
cd "C:\path\to\new agentic"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks script execution for the current terminal, use:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Generate training data and train the model

```powershell
python train_maintenance_model.py
```

This creates:

- `maintenance_training_data.csv`
- `models/maintenance_model.joblib`

## Run the application

```powershell
python app.py
```

Open:

- Energy dashboard: `http://127.0.0.1:5000/`
- Predictive maintenance dashboard: `http://127.0.0.1:5000/static/maintenance.html`

## Dashboard data-source policy

The dashboards read from the CSV files in the project root. The Energy,
Occupancy, and Maintenance dashboards use `facility_data.csv`; the Security
dashboard uses `security_events.csv`. If either CSV file is missing, empty, or
has no usable rows, the application first writes generated rows into that CSV
file and then renders the dashboard from the CSV contents. Existing usable CSV
data is not overwritten.

## How the Maintenance Agent works

1. Reads the existing `facility_data.csv`.
2. Aggregates observations per HVAC asset.
3. Calculates condition features such as temperature deviation, HVAC runtime and equipment warnings.
4. Scores current health with the transparent rule set in `src/health_scoring.py`.
5. Predicts the next reading's condition direction (Improving / Stable /
   Deteriorating) with the future-condition Random Forest trained by
   `train_future_condition.py`.
6. Produces a failure-risk percentage and risk level.
7. Converts risk into a maintenance window.
8. Generates alerts (current condition) and scheduled work (including
   predicted deterioration) for the dashboard.
