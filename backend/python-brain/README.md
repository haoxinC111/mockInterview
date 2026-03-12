# python-brain

InterviewSim Chat-MVP backend service.

## Workflow Runtime

The backend supports dual-path orchestration:
- legacy runtime (default)
- LangGraph runtime via feature flags
- shadow mode for contract-drift observation before cutover

Key env flags:
- `WORKFLOW_USE_LANGGRAPH`
- `WORKFLOW_SHADOW_MODE`
- `WORKFLOW_REPORT_USE_LANGGRAPH`
- `WORKFLOW_RESUME_USE_LANGGRAPH`
- `WORKFLOW_TURN_USE_LANGGRAPH`

## Quick Start

```bash
uv sync --extra dev --extra stt
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

For shadow-mode local verification, see:
`docs/runbooks/langgraph-shadow-mode.md`

## Test

```bash
uv run pytest -q
```

## Latest Update

- Added resume quality gating (`quality_score`, `readiness`) before interview start.
- Added `training_guidance` mode for reports generated without valid turn samples.
- Manual QA status: **not manually tested** in browser yet; automated tests pass.
