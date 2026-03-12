# LangGraph Shadow Mode Runbook

## Goal
Validate LangGraph migration paths without changing user-visible behavior.

## Runtime Model
- `legacy`: only legacy services are executed.
- `langgraph`: target workflow executes on LangGraph path.
- `shadow`: legacy response is returned; LangGraph runs in parallel and logs structured diffs.

## Required Flags
```bash
WORKFLOW_USE_LANGGRAPH=true
WORKFLOW_SHADOW_MODE=true
WORKFLOW_REPORT_USE_LANGGRAPH=true
WORKFLOW_RESUME_USE_LANGGRAPH=true
WORKFLOW_TURN_USE_LANGGRAPH=true
```

Keep LLM flags explicit for predictable tests:
```bash
INTERVIEW_ENGINE_USE_LLM=false
INTERVIEW_TURN_USE_LLM=false
RESUME_PARSER_USE_LLM=false
```

## Local Smoke Procedure
1. Start backend:
```bash
cd backend/python-brain
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
2. Upload resume (`POST /api/v1/resumes`).
3. Start interview (`POST /api/v1/interviews`).
4. Send one answer turn (`POST /api/v1/interviews/{id}/messages`).
5. Finish interview (`POST /api/v1/interviews/{id}/finish`).

Expected outcome:
- HTTP remains 2xx.
- Response contracts unchanged.
- Summary/full logs contain `workflow.turn.shadow.diff`, `workflow.report.shadow.diff`, and `workflow.resume.shadow.diff` when drift exists.

## Mission Guard Check
If turn/report payload misses actionable feedback, guards auto-fill minimum growth-oriented artifacts (`evidence`, `gaps`, `reference_answer`, action-plan fallback).

## Cutover Recommendation
1. Enable report graph first.
2. Keep resume and turn in shadow mode for at least one validation cycle.
3. Promote resume graph, then interview graph after golden parity and shadow diff acceptance.

## Testing Status
- Automated tests: passed in the LangGraph worktree.
- Manual browser smoke: not completed for this update; treat rollout notes as pre-release until manual validation is done.
