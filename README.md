---
title: Meta Scalar Hackathon OpenEnv
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
---

# Autonomous Traffic Control OpenEnv

Production-grade OpenEnv benchmark where an agent acts as an autonomous traffic-control reviewer.
The agent inspects safety and reliability alerts, triages each finding, and submits an operational handoff under budget and deadline pressure.

## Problem Description
Urban intersections rely on adaptive control software to keep traffic flowing while prioritizing emergency vehicles.
Operational teams receive noisy alerts from static analysis, telemetry checks, and failing tests.
The agent in this environment must separate true defects from false positives, assign severity, and produce a final go or no-go summary.

## Real-World Motivation
- A missed critical defect can cause unsafe phase conflicts or emergency response delays.
- Over-triaging false positives wastes operator time and review budget.
- Control centers need concise, actionable handoffs during shift changes and incident response.

## Environment Interface
Core implementation: `env/environment.py`

- `reset(task_id: Optional[str]) -> ReviewObservation`
- `step(action: ReviewAction) -> (ReviewObservation, reward, done, info)`
- `state() -> ReviewState`

Serving layer: `server/app.py`

- `POST /reset`
- `POST /step`
- `GET /state`
- `GET /health`
- `GET /metadata`
- `GET /schema`
- `POST /mcp`
- `WS /ws`

## Action Space
Pydantic model: `ReviewAction` in `env/models.py`

Fields:
- `action_type`: `inspect_alert`, `inspect_file`, `inspect_tests`, `triage_alert`, `add_note`, `submit_review`
- `alert_id`: alert identifier for scoped actions
- `decision`: `bug`, `false_positive`, `needs_info`
- `severity`: required when `decision=bug` (`low`, `medium`, `high`, `critical`)
- `note`: operator note text
- `summary`: final submission summary

## Observation Space
Pydantic model: `ReviewObservation` in `env/models.py`

Key fields:
- task metadata (`task_id`, `difficulty`, `objective`)
- progress counters (`step_count`, `max_steps`, `budget_used`, `budget_limit`)
- `progress_score` in `[0, 1]`
- queue snapshot with per-alert inspection and triage status
- `focused_context` with current evidence details
- `last_action_error` for deterministic validation failures

## State Space
Pydantic model: `ReviewState` in `env/models.py`

Tracks:
- episode metadata and counters
- per-alert runtime status
- budget usage
- invalid action count and loop count
- action history and inspection log
- deterministic final score in `[0, 1]`

## Task Suite
Task definitions: `env/tasks.py`

### Easy: `easy-four-way-rush-hour`
- Objective: stabilize a suburban 4-way junction while preserving westbound ambulance priority
- Alerts: 2
- Horizon: 8 steps
- Profile: short horizon, basic triage discipline

### Medium: `medium-downtown-commuter-wave`
- Objective: handle commuter surge while protecting emergency corridor responsiveness
- Alerts: 3
- Horizon: 14 steps
- Profile: multi-step reasoning across file and test evidence

### Hard: `hard-citywide-evacuation-incident`
- Objective: manage evacuation-mode incident pressure with strict deadlines
- Alerts: 5
- Horizon: 20 steps
- Profile: long-horizon planning, deadline-aware triage, stronger trade-offs

## Grading Logic
Deterministic grader implementation: `env/graders.py`

Normalized score in `[0.0, 1.0]` is computed from:
- decision accuracy
- severity accuracy for true defects
- decision coverage across alerts
- evidence coverage before triage
- SLA deadline compliance for time-critical alerts
- summary quality
- efficiency under step and budget pressure

Penalty terms reduce score for invalid actions and loops.
No randomness is used in grading.

## Reward Logic
Dense reward implementation: `env/reward.py`

Positive reward signals:
- progress delta between current and previous state
- novelty for meaningful non-repeated actions
- triage correctness shaping
- completion bonus tied to final deterministic grade

Penalty signals:
- invalid actions
- looped behavior
- no-op behavior
- step tax and late-episode tempo pressure

## Determinism Guarantees
- Task content is static and deterministic.
- Grading has no stochastic components.
- Reward computation is deterministic for a given transition.
- The only varying value is `episode_id`, which does not affect score.

## Project Structure

```text
.
├── openenv.yaml
├── env/
│   ├── __init__.py
│   ├── environment.py
│   ├── models.py
│   ├── tasks.py
│   ├── graders.py
│   └── reward.py
├── server/
│   ├── __init__.py
│   └── app.py
├── inference.py
├── Dockerfile
├── requirements.txt
├── pyproject.toml
├── uv.lock
└── README.md
```

## Setup

### Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run Server Locally

```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

Or with the project script:

```bash
uv run server
```

### Quick API Smoke Test

```bash
curl -X POST http://127.0.0.1:8000/reset -H "Content-Type: application/json" -d '{}'
```

## Docker Usage

```bash
docker build -t autonomous-traffic-control-env .
docker run --rm -p 8000:8000 autonomous-traffic-control-env
```

## Inference Runner
Script: `inference.py`

Behavior:
- Uses OpenAI client.
- Reads `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN`, `LOCAL_IMAGE_NAME`.
- Runs all three tasks sequentially.
- Emits structured logs only: `[START]`, `[STEP]`, `[END]`.

Run:

```bash
python inference.py
```

Recommended environment variables:

```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="<your_token>"
export LOCAL_IMAGE_NAME="autonomous-traffic-control-env"
```

## Validation

```bash
openenv validate
pytest -q
```

## Baseline Scores
Deterministic policy results from `inference.py`:

- easy-four-way-rush-hour: `0.99`
- medium-downtown-commuter-wave: `0.94`
- hard-citywide-evacuation-incident: `0.93`

## Manifest Requirements
`openenv.yaml` includes:

- `name`
- `description`
- `version`
- `entrypoint`
- `tags` (including `openenv`)
- runtime fields: `spec_version`, `type`, `runtime`, `app`, `port`

## Hugging Face Space Compatibility
- Root-level Dockerfile with FastAPI app startup
- Health endpoints available at launch
- `POST /reset` and `POST /step` interface for benchmark execution
- Stateless reset behavior with deterministic transitions

## Repository Hygiene
- `.env` is ignored and not committed
- `.env.example` is ignored and not committed
- Docker build context excludes both files
