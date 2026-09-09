# Milestone 2 — Predictive Maintenance System

This adds the predictive-maintenance layer to the existing Energy Intelligence project.

## What was added

- Synthetic historical maintenance training dataset generator
- Random Forest failure-risk model
- Asset-level equipment health scoring (0–100)
- Excellent / Good / Warning / Critical health categories
- Hybrid Maintenance Agent (ML risk + transparent safety rules)
- Predictive maintenance alerts
- Maintenance schedule recommendations
- Work-order generation/tracking
- Predictive Maintenance Dashboard
- `/api/maintenance/dashboard` API

> The maintenance training data is synthetic and intended for a college/demo project. It must not be presented as real equipment-failure data.

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

## How the Maintenance Agent works

1. Reads the existing `facility_data.csv`.
2. Aggregates observations per HVAC asset.
3. Calculates condition features such as temperature deviation, HVAC runtime and equipment warnings.
4. Sends those features to the trained Random Forest model.
5. Adds a transparent rule-based safety layer for observable operating warnings.
6. Produces a failure-risk percentage and risk level.
7. Converts risk into a maintenance window.
8. Generates alerts and work orders for the dashboard.
