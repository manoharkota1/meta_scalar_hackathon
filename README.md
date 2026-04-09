---
title: Meta Scalar Hackathon OpenEnv
emoji: "🚦"
colorFrom: cyan
colorTo: green
sdk: docker
app_port: 8000
---

# Autonomous Traffic Control OpenEnv

Multi-agent environment where AI systems manage a 4-way intersection with emergency vehicle prioritization.

## Problem Description
Urban intersections rely on AI-assisted control systems to coordinate signals, prevent gridlock, and prioritize ambulances, fire trucks, and police vehicles. Agents in this benchmark must inspect control evidence, classify true hazards versus false positives, prioritize high-impact incidents by deadline, and submit concise operational handoffs.

This environment models that workflow with deterministic task data and deterministic grading.

## Real-World Motivation
- Traffic control alerts can be noisy, but missing a real hazard is costly.
- Control rooms operate with limited intervention budget and strict timing constraints.
- Reliable incident response requires evidence gathering, prioritization, and concise shift handoffs.

## Environment Interface
Core environment implementation is in `env/environment.py` and exposes:
- `reset(task_id: Optional[str]) -> ReviewObservation`
- `step(action: ReviewAction) -> (ReviewObservation, reward, done, info)`
- `state() -> ReviewState`

Server runtime is provided by `server/app.py` with OpenEnv-compatible HTTP and WebSocket endpoints:
- `POST /reset`
- `POST /step`
- `GET /state`
- `GET /health`
- `GET /metadata`
- `GET /schema`
- `POST /mcp`
- `WS /ws`

## Action Space
`ReviewAction` (Pydantic model in `env/models.py`):
- `action_type`: one of `inspect_alert`, `inspect_file`, `inspect_tests`, `triage_alert`, `add_note`, `submit_review`
- `alert_id`: traffic-alert target for alert-scoped actions
- `decision`: classifier decision (`bug`, `false_positive`, `needs_info`)
- `severity`: required when decision is `bug` (`low`, `medium`, `high`, `critical`)
- `note`: per-alert operator note
- `summary`: final intersection-control summary

## Observation Space
`ReviewObservation` includes:
- task metadata (`task_id`, `difficulty`, `objective`)
- progress counters (`step_count`, `max_steps`, `budget_used`, `budget_limit`)
- `progress_score` in `[0, 1]`
- alert queue with per-alert workflow status
- `focused_context` containing latest inspected evidence
- `last_action_error` for deterministic error reporting

## State Space
`ReviewState` tracks:
- step count and episode id
- per-alert inspection and triage status
- invalid action count, loop count, budget usage
- action history and notes
- final deterministic score at episode completion

## Task Suite
Task definitions are in `env/tasks.py`.

### Easy: `easy-four-way-rush-hour`
- 2 alerts
- short horizon (max 8 steps)
- objective: stabilize rush-hour timing and protect an inbound ambulance corridor

### Medium: `medium-downtown-commuter-wave`
- 3 alerts
- multi-step reasoning across controller/test evidence
- objective: preserve throughput while maintaining emergency preemption reliability

### Hard: `hard-citywide-evacuation-incident`
- 5 alerts
- long horizon planning with deadline and budget pressure
- objective: run incident-mode signal control with safety, latency, and resilience trade-offs

## Deterministic Graders
Grading logic is in `env/graders.py`.

Each episode receives a normalized score in `[0.0, 1.0]` based on:
- decision accuracy
- severity accuracy
- triage coverage
- evidence coverage before triage
- SLA compliance for deadline-bound alerts
- summary quality
- efficiency (steps, budget, invalid actions, loops)

No randomness is used in grading.

## Reward Logic (Dense)
Dense step reward implementation is in `env/reward.py`.

Signals include:
- progress delta toward completion and correctness
- positive novelty reward for meaningful non-repeated actions
- triage correctness shaping
- completion bonus linked to final deterministic score

Penalties include:
- invalid action penalties
- loop penalties
- no-op penalties
- step tax and late-episode tempo pressure

## Project Layout

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

### Local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start server:

```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

Or with uv project runner:

```bash
uv run server
```

### Docker

```bash
docker build -t autonomous-traffic-control-env .
docker run --rm -p 8000:8000 autonomous-traffic-control-env
```

## Inference Runner
`inference.py`:
- uses OpenAI client
- reads `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN`, `LOCAL_IMAGE_NAME`
- emits only structured logs:
  - `[START]`
  - `[STEP]`
  - `[END]`
- runs all three tasks sequentially
- reports deterministic per-task score in `[0, 1]`

Run:

```bash
python inference.py
```

## Tests
Run deterministic environment and API tests:

```bash
pytest -q
```

Recommended environment variables:

```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="<your_token>"
```

## Baseline Scores
Measured with deterministic policy in `inference.py`:
- easy-four-way-rush-hour: 0.99
- medium-downtown-commuter-wave: 0.94
- hard-citywide-evacuation-incident: 0.93

## openenv.yaml fields
Manifest includes:
- `name`
- `description`
- `version`
- `entrypoint`
- `tags` including `openenv`
- OpenEnv runtime fields (`spec_version`, `runtime`, `app`, `port`)

## Hugging Face Space Compatibility
- Containerized startup via root `Dockerfile`
- FastAPI app boots at `server.app:app`
- `POST /reset` is available immediately
- API is deterministic and stateless per reset
