# Code Review — Agentic AI for Smart Facility Operations Optimization

Reviewed: 2026-09-19 against commit `628ec15` ("Implement milestone 4 operations orchestrator").
Every claim below was verified by reading the code and/or running the app (`python app.py`) and querying the live API.

---

## Verdict in one paragraph

This is a milestone-dumped demo project wearing an "Agentic AI" costume. The five "agents" are plain pandas
aggregation functions with class/function wrappers; none of them has state, memory, goals, tool use, or any
reasoning loop. The "AI" is more troubling: a Random Forest trained on 869 MB of **real LBNL fault data is
trained and never used at runtime**, while the model that *is* used at runtime is trained on labels produced
by the same hand-written rule it predicts (circular ML). All "Live sensor readings" labels are scripted
synthetic data — the generator hard-codes the exact demo outcomes the dashboards then "discover". The
recommendations are, as suspected, largely tautologies, re-narrated counts, and pseudo-precise numbers with
invented arithmetic behind them. There is also a large amount of dead/duplicated code and an 869 MB data
folder committed to Git.

---

## 1. The "AI" is fake in two different ways

### 1.1 The real model is trained but never served (AI-washing)
- `train_maintenance_model.py` trains a RandomForestClassifier on the LBNL RTU fault dataset
  (`data/lbnl`, 25 files, ~35 MB each) and saves `models/maintenance_fault_model.joblib`.
- `src/maintenance_model.py` loads exactly that model (`MODEL_PATH = Path("models/maintenance_fault_model.joblib")`).
- **Nothing imports `src/maintenance_model.py`.** Verified by grep: zero imports anywhere in `app.py` or `src/`.
  The running maintenance dashboard never touches the trained fault model.
- What the dashboard actually uses is `src/health_scoring.calculate_condition_risk()` — a hand-written
  if/else point system (`temp deviation > 3 → +35`, `humidity out of band → +25`, `fault → +50`, …).
  So README_MILESTONE_2's "Random Forest failure-risk model" claim is stale/false for the shipped app.
- There is also an orphan artifact: `models/maintenance_model.joblib` — written by no current script
  (the trainer writes `maintenance_fault_model.joblib`), loaded by nothing.

### 1.2 The model that *is* served is circular (learns its own rule, lagged one step)
- `train_future_condition.py` creates labels as: run the same hand-written `calculate_condition_risk` rule
  on row *t* and row *t+1*, then label = Deteriorating if `risk[t+1] − risk[t] > 5`, Improving if `< −5`, else Stable.
- The RandomForest's features are the same sensor columns the rule consumes. So the model's job is to
  approximate "what my own if/else rule will say in 15 minutes" — it cannot discover anything the rule
  doesn't already encode.
- Live evidence of the nonsense this produces (`/api/maintenance/dashboard`):

  | Asset | Rule-based health | ML "future" prediction | ML confidence |
  |---|---|---|---|
  | B002 - R003 | **0.0 / Critical** (active Fault) | **"Improving"** | 57.5% |

  The worst-possible asset is simultaneously predicted to improve — because its rule-risk is already pinned
  at the 100 ceiling, so the only possible direction anywhere near it is down. The dashboard shows both
  verdicts side by side, contradicting itself, with a confidence number attached.
- Bonus: the same `calculate_condition_risk` function exists **three times** in the codebase
  (`src/health_scoring.py:19`, dead copy in `src/maintenance_agent.py:24` named `_condition_risk`, and
  `train_future_condition.py:21`). They will drift apart the first time someone edits one.

### 1.3 The fault-model training itself is methodologically weak
- `train_maintenance_model.py` labels *every* non-baseline simulation file as fault=1, collapsing
  condenser fouling, evaporator fouling, over/undercharge and pipe-pressure faults into one binary class,
  then splits each time-ordered file 80/20 and samples. Train and test rows come from the *same
  simulation runs* — adjacent timestamps with near-identical constant offsets. The RF trivially separates
  them; the reported balanced accuracy is not evidence the model detects faults, only that it can tell
  simulation files apart. And as noted, the result isn't served anyway, so this is all theatre.

---

## 2. "Live" data is scripted theater

- `src/data_generator.py` hard-codes the demo outcome: `OCCUPANCY_CASE_SCENARIOS` and
  `EQUIPMENT_CASE_SCENARIOS` force specific states at specific intervals (24, 52, **95 = the "latest"
  interval**, i.e. what the dashboards show as *current*): one scripted equipment Fault, two scripted
  Warnings, and one scripted over-capacity room (B002-R003: 4 people, capacity 3).
- `src/security_data_generator.py` likewise plants exactly three 2 a.m. repeated "Unauthorized Access"
  attempts per building and three Critical events ("Door Forced", "Tailgating Detected", "Invalid Badge")
  — so the security agent "detects" exactly what was planted for it.
- Every dashboard then labels this **"Live facility sensor readings" / "Live security event stream"
  / "Live occupancy sensor readings"** (`energy_agent.py:70`, `maintenance_agent.py:777`,
  `occupancy_agent.py:655`, `security_agent.py:732`, `orchestrator_agent.py:95` →
  `"Live facility intelligence layer"`). The data all dates from 2026-08-28 — three weeks old at review
  time — and `GET` requests silently *generate* this data on disk if the CSV is missing
  (`app.py` → `ensure_facility_csv`/`ensure_security_csv` on every read endpoint).
- README_MILESTONE_2 honestly says the training data "must not be presented as real equipment-failure
  data" — and then the app presents synthetic data as "live" anyway.

---

## 3. Why the recommendations specifically are bad (with live API evidence)

### Energy agent (`/api/dashboard`)
Real output verbatim:
- `Medium | High Consumption | "B002 R003 (Server Room) has the highest monitoring period consumption at
  103.02 kWh."` — a tautology. *Something* is always the highest consumer; this is a sorted fact, not a
  recommendation, and it fires on every dataset, always.
- `"HVAC operated during 126 unoccupied reading(s), using approximately 72.26 kWh."` — always "Medium"
  priority regardless of magnitude; counts *readings*, not time; gives no schedule action.
- `"B002 R001 (Office) exceeded its HVAC setpoint in 1 reading(s)."` — **one reading = 15 minutes**.
  Firing a High-priority "recommendation" over a single 15-minute sample is noise, and the generator's
  temperature model guarantees a handful of these will always exist.
- The "Critical" equipment alerts are literally the three statuses scripted at interval 95.
- KPI math: `potential savings = 0.8 × empty-HVAC energy + 0.3 × anomaly excess`, then **arbitrarily
  capped at 20% of total** (`min(computed, total * 0.20)`), then multiplied by ₹8/kWh and presented as
  `₹610.92` with two-decimal precision, plus "53.46 kg CO₂". Three invented constants and a cap, dressed
  as money.
- `efficiency_score` = 100 minus weighted ratios (30/30/10/20 weights, invented). Live result: efficiency
  **90.8 = "Excellent"** in the same snapshot where a **Critical equipment fault** exists. The KPIs
  contradict each other within one payload.
- `anomalies` KPI counts the **capped** list (`detect_anomalies` returns `.head(20)`), so the KPI can
  never exceed 20 no matter how anomalous the data is. It also conflates energy spikes with any
  equipment Warning/Fault row — two different things counted as one.
- `hourly_energy` is zero-filled for missing timestamps (`fillna(0)`), directly contradicting the
  occupancy module's loudly documented "we never fill fake zeroes" philosophy. Inconsistent data policy.

### Maintenance agent (`/api/maintenance/dashboard`)
- Recommendations are one generic sentence template: `"Immediate inspection: review the current room
  equipment condition."` — same text for every asset, no fault type, no what's-wrong, no parts/checks,
  despite the payload carrying temperature/humidity/energy/severity fields it could say something specific about.
- `"faults_detected": 2` counts categories Warning+Critical — "fault" includes "warning". Naming bug.
- **Three dashboard sections are the same list**: `alerts`, `schedule`, and KPI
  `maintenance_recommendations` are all `[asset for asset in assets if asset["fault_detected"]]`
  (verified live: `alerts == schedule == maintenance_recommendations → True`). The dashboard shows
  "alerts" and "schedule" as if they were different artifacts; they are byte-identical.
- The cross-check between the rule score and the ML prediction (health 0.0 vs "Improving" 57.5%) is
  shipped as if both were meaningful.

### Occupancy agent (`/api/occupancy/insights`, and its use inside the orchestrator)
- `"9 room(s) reached 90% or more of the configured room capacity"` — **all nine rooms**, because
  capacity alerts are computed from the daily *peak* per room and the generator deliberately breeds
  near-/over-capacity readings (plus a scripted over-capacity room). An alert that fires for every room
  is decoration, not signal.
- Orchestrator occupancy score confirmed broken: base score from utilization ≈ 92.4 (33.3% utilization,
  100 − |rate−55|×0.35), then **−12 for each of the 9 "High" capacity alerts** → clamps to **0 /
  "Critical"**. So the orchestrator screams that occupancy is in a Critical state while the occupancy
  dashboard itself says everything is normal. This single bug alone drags the composite
  `facility_score` to 56.0 "Warning".
- The `OccupancyAgent` class and the entire `src/occupancy_analytics.py` (368 lines) it wraps are only
  reachable via each other — nothing in the app uses them. Dead code propped up by other dead code.
- `_utilization()` clamps at 100%: an over-capacity room (4 people in a capacity-3 server room, 133%)
  displays as exactly 100.0% — the one place showing how far over you are is the place that caps it.

### Security agent (`/api/security`)
- "Insights" are count re-narration: "18 unauthorized access event(s) were detected", "6 critical
  security event(s) require attention", "15 high-risk event(s)" — 15 = High+Critical, so the same
  events are insight-ed twice.
- The plant-and-detect problem from §2: the 2 a.m. repeated attacks and the Critical events are scripted
  into the CSV; the agent then "detects" them as if from sensors. `unauthorized_rate: 28.12%` would be a
  five-alarm fire in any real building; here it's a generator knob (`rng.random() < 0.25` at night).
- `resolved_events: 0` — hardcoded fake KPI pretending there's an incident-resolution workflow. There isn't.
- The entire `SecurityAgent` class (~300 lines, with `run()`, keyword-scan `is_unauthorized`, etc.) is
  dead code; the dashboard path uses separate module-level functions that re-implement the logic.

### Orchestrator (`/api/orchestrator/dashboard`) — the shit cherry on top
Live output, annotated:

```
facility_score: 56.0 "Warning"        ← weighted avg (30/30/20/20, invented) of the broken sub-scores
automation_readiness: 19.0            ← 56 − 3×5 − 8×2 − 3×2. Pure arithmetic theater: a pseudo-precise
                                        float scoring readiness for automation that does not exist.
active_alerts: 49                     ← 20 capped energy anomalies + 2 faults + 9 capacity + 18 security.
                                        Apples + oranges + capped lists, summed into one number.
```
- `decision_log` timestamps are **`datetime.now()` (2026-09-19)** while all underlying data is from
  2026-08-28 — the log claims decisions were made today about three-week-old events. "Confidence" is a
  string looked up from the priority label (`Critical → "High"`): confidence derived from a
  non-probability, i.e. invented twice over.
- Actions like `ACT-001`, `status: "Recommended"`, `automation_mode: "Human approval required"` mimic an
  operational workflow system — but nothing consumes action IDs, nothing can be approved, scheduled, or
  executed. It's cosplay of an incident system.
- Dedupe bug: 3 near-identical **"Setpoint / HVAC Check"** actions appear in the same action list because
  `_dedupe_actions` keys on (domain, title, recommended_action) while the variation lives in the room
  name inside `reason`/`recommended_action`. Should key on target asset.
- Incoherent quota system: maintenance alerts `[:6]`, capacity alerts `[:5]`, energy recs `[:5]`, then
  the merged list `[:14]` — whichever domain floods first silently starves the others.
- `cross_agent_insights` are 4 hard-coded AND-combinations of KPI booleans (e.g. "anomalies>0 AND
  faults>0 → overlap insight"). This is the entire "cross-agent coordination": an if-statement.
- `_build_timeline` iterates **all** occupancy rooms (no cap) before slicing to 12 — works today with 9
  rooms, pointless work and wrong-by-design at scale.

---

## 4. Dead / duplicated code inventory (delete-candidates, all verified)

| What | Where | Why dead |
|---|---|---|
| `_condition_risk` (3rd copy of the rule) | `src/maintenance_agent.py:24-104` | Module imports and uses `calculate_condition_risk` from `health_scoring` instead |
| `SecurityAgent` class | `src/security_agent.py:22-323` | Dashboard uses standalone `build_security_dashboard` |
| `OccupancyAgent` class | `src/occupancy_agent.py:23-177` | Dashboard uses standalone `build_occupancy_dashboard` |
| `OccupancyAnalytics` + module | `src/occupancy_analytics.py` (368 lines) | Only referenced by the dead class above |
| `src/maintenance_model.py` (237 lines) + `models/maintenance_model.joblib` | repo | Zero imports; artifact written by no script |
| `models/maintenance_fault_model.joblib` | repo | Only loadable by the dead `maintenance_model.py` |
| `hourly_energy()` helper | `src/analytics.py:233` | Superseded by inline resample inside `energy_agent.py` |
| `style_additions.css.txt` | repo root | Stray paste-buffer CSS dump |
| `generate_security_data.py` duplicated wrapper | repo root vs `src/security_data_generator.py` | Thin wrapper, now obsoleted by `ensure_security_csv` |

Rough total: **~1,200–1,500 lines of the ~4,700-line backend are dead weight** (25–30%).

---

## 5. Repo & app hygiene

1. **869 MB of CSVs committed to Git** (`data/lbnl/`, 25 files × ~35 MB; verified via git blob audit).
   No `.gitignore` entry for `data/`; no Git LFS. This balloons every clone forever — move to LFS,
   a release artifact, or a download script (and keep a small sampled CSV for the demo).
2. **Generated artifacts committed**: `facility_data.csv`, `security_events.csv`, and all `models/*`
   binaries are tracked. These are outputs; commit the generators, not the outputs (or commit one tiny
   frozen sample with a comment saying it's a fixture).
3. **No `README.md`** — only `README_MILESTONE_2.md` and `README_MILESTONE_4.md` (milestones 1 and 3
   undocumented). The repo front page explains nothing about what this is, how to run it, or its
   synthetic-data disclaimer.
4. **Zero tests.** No `tests/`, no CI. The occupancy-score-0 bug above is exactly what one assertion
   would have caught.
5. `app.py`:
   - **Side-effecting GETs**: every dashboard endpoint may *generate and write CSVs* on read.
     Write-on-read belongs behind an explicit `POST /api/data/regenerate` or a startup step.
   - **No caching**: `/api/orchestrator/dashboard` re-reads both CSVs and rebuilds all four dashboards
     on *every* request (~0.5 s measured). At minimum cache by file mtime.
   - `debug=True` + `host="0.0.0.0"` in the committed entrypoint — debug reloader + Werkzeug debugger on
     all interfaces is a classic footgun (arbitrary code execution via the debugger if exposed).
   - `/api/health` hardcodes every agent `True` and both data sources `"ready"` without checking anything.
   - Unbounded payloads: security `events` returns the whole CSV per request; fine at 64 rows, wrong by design.
6. Silent-failure defaults: `analyze_facility_assets` returns `[]` if *any* of 12 columns is missing —
   dashboard just shows "nothing" instead of failing loudly; several `except Exception` / `_number(value,
   default=0.0)` paths convert real errors into plausible-looking zeros. For a monitoring product, zero
   is the most dangerous failure mode there is.

---

## 6. Fair credit — what's actually decent

- Consistent, documented JSON response shapes (including `available`, `data_source`, `note`,
  `metadata`) on every endpoint; the frontend consumes one schema.
- The occupancy builder has a genuinely good empty-data policy ("no fake zeroes", explicit `None`
  propagation) — even if the energy module contradicts it.
- Clear empty-state handling instead of crashes for missing/empty/malformed CSVs.
- `pandas`/`joblib` version pins are sane and install cleanly (verified: flask 3.1.3, pandas 3.0.6,
  sklearn 1.9.0 on Python 3.11).
- The LBNL pipeline idea (train on a real public fault dataset, sample per file, use balanced metrics)
  is the right *instinct* — it just isn't wired into the app, and the split methodology leaks.
- README_MILESTONE_2's synthetic-data disclaimer is honest; the problem is the UI contradicts it.

---

## 7. What to fix, in order

**P0 — honesty & coherence (a day):**
1. Pick one: either wire the LBNL-trained fault model into the maintenance dashboard for real (with a
   feature-mapping layer and a model card), or delete `train_maintenance_model.py`,
   `src/maintenance_model.py`, both joblib artifacts, and the README claims. Dead ML is worse than no ML.
2. Fix or drop the future-condition model: label it from *observed outcomes* (e.g. setpoint deviation
   persisting/worsening beyond noise over the next N readings — an actual event), not from "my own rule,
   shifted by one row". Single-source `calculate_condition_risk` (train script imports it from
   `src.health_scoring`).
3. Change every `data_source: "Live ..."` string to `"Simulated facility data (synthetic)"`, and say so
   on the dashboards.
4. Delete the dead code in §4 (~1.5k lines). Delete `models/maintenance_model.joblib`.

**P1 — make recommendations earn their name:**
5. Every recommendation should carry: *what* (specific fault/condition from the fields you already have),
   *magnitude* (kWh/people/₹ range with the assumption shown), *action* (concrete verb: "shedule fan
   belt inspection", "defer server-room setpoint to X", not "review the condition"), and *why now*.
   Kill tautologies ("highest consumption room") or relabel them as stats, not recommendations.
6. Fix the occupancy scoring (cap the per-alert penalty, use current-state signal not daily-peak count),
   the anomaly KPI cap (report true count + capped list), the `resolved_events` fake KPI, the action
   dedupe key, and the decision-log fake timestamps (use data timestamps).
7. Replace `min(savings, 20% of total)` and the 0.8/0.3 constants with sourced assumptions shown in the UI,
   or present a range. Precision without provenance is how you get "₹610.92".
8. Give each asset *one* verdict: reconcile rule-health vs ML-future (e.g. ML only refines Warning-band
   assets; Critical rule state overrides the model) instead of displaying a contradiction.

**P2 — engineering:**
9. Get `data/lbnl` out of Git history (LFS / external storage / sampled fixture). Untrack generated CSVs
   and model binaries.
10. Add a real `README.md` (what it is, synthetic-data disclaimer up front, quickstart) and a `tests/`
    dir: smoke-test each dashboard builder against a fixture CSV; unit-test `health_scoring`,
    `_occupancy_score`, `detect_anomalies` — the occupancy-0 and alerts==schedule bugs both fall out of
    this immediately.
11. `app.py`: no writes in GET handlers, cache dashboards keyed on CSV mtime, `debug` from env var
    defaulting off, real checks in `/api/health`, pagination/caps on event payloads.
12. If "agentic" must stay in the name, make it true at least once: a small tool-using loop (even a
    rules + LLM hybrid) that can *do* something — create a work order, propose a schedule diff, simulate
    a setpoint change against the generator — with guardrails enforced in code, not in label strings
    like `"Human approval required"`.

---

*Method note: claims were verified by static reading of all 15 Python modules + training scripts and by
running the app and querying `/api/dashboard`, `/api/maintenance/dashboard`, `/api/occupancy/insights`,
`/api/security`, `/api/orchestrator/dashboard`, and `/api/orchestrator/actions` on 2026-09-19.*
