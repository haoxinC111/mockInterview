# LangGraph Migration Implementation Plan

> **Document Status:** Draft
> **Author:** GitHub Copilot (GPT-5.4)
> **Created:** 2026-03-09
> **Document Role:** Executable migration plan for LangGraph-first workflow refactor

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate InterviewSim from a monolithic custom interview state machine to a LangGraph-first workflow architecture, while preserving the current growth-oriented interview quality, fallback behavior, and API contracts.

**Architecture:** Keep FastAPI routes and core domain services, introduce LangGraph as the workflow runtime, and use LangChain only where component abstractions genuinely reduce complexity. Migrate in phases under feature flags and shadow execution so the new workflow must prove parity before it serves real traffic.

**Tech Stack:** FastAPI, Python, SQLModel, SQLite, LangGraph, selective LangChain components, pytest, existing Relay LLM client, existing OCR/STT stack.

---

I'm using the writing-plans skill to create the implementation plan.

## Preconditions

Before Task 1, establish these non-negotiables:
- The project mission in `app/core/config.py` remains injected into every LLM-facing prompt.
- The current HTTP API contract remains backward compatible.
- Every migrated workflow keeps a non-LLM fallback path where one already exists.
- New workflow execution is feature-flagged and can run in shadow mode.
- No task may remove `evidence`, `gaps`, `score_rationale`, `reference_answer`, or action-plan related report fields.

## Migration Strategy

Recommended path:
1. Introduce workflow abstractions without changing user-visible behavior.
2. Move report generation first, because it is easiest to validate offline.
3. Move resume ingestion second, because it has explicit fallback steps.
4. Move interview turn orchestration last, because it is the most user-sensitive path.
5. Only after parity is proven, enable new workflows gradually.

## Task 1: Freeze Current Behavior With Golden Tests

**Files:**
- Create: `backend/python-brain/tests/golden/test_interview_turn_golden.py`
- Create: `backend/python-brain/tests/golden/test_report_golden.py`
- Create: `backend/python-brain/tests/fixtures/golden_sessions.json`
- Modify: `backend/python-brain/tests/test_api_smoke.py`

**Step 1: Write the failing golden tests**

```python
from pathlib import Path
import json


def test_turn_golden_cases():
    cases = json.loads(Path("tests/fixtures/golden_sessions.json").read_text())
    assert cases, "golden cases missing"
```

**Step 2: Run test to verify it fails**

Run: `cd backend/python-brain && uv run pytest tests/golden/test_interview_turn_golden.py -q`
Expected: FAIL because fixtures and assertions are incomplete.

**Step 3: Expand tests to assert stable outputs**

Add assertions for:
- `next_action`
- `topic`
- `score` band, not exact brittle value
- required fields in `turn_eval`
- report payload required keys

**Step 4: Run tests to verify they pass on the current engine**

Run: `cd backend/python-brain && uv run pytest tests/golden/test_interview_turn_golden.py tests/golden/test_report_golden.py -q`
Expected: PASS on the current custom engine.

**Step 5: Commit**

```bash
git add backend/python-brain/tests/golden backend/python-brain/tests/fixtures backend/python-brain/tests/test_api_smoke.py
git commit -m "test: add golden coverage for workflow migration"
```

## Task 2: Define Strong Workflow State Schemas

**Files:**
- Create: `backend/python-brain/app/workflows/__init__.py`
- Create: `backend/python-brain/app/workflows/state_models.py`
- Modify: `backend/python-brain/app/workflow/state.py`
- Test: `backend/python-brain/tests/test_workflow_state_models.py`

**Step 1: Write the failing test**

```python
from app.workflows.state_models import InterviewWorkflowState


def test_interview_workflow_state_defaults():
    state = InterviewWorkflowState.initial()
    assert state.turn_count == 0
    assert state.finished is False
```

**Step 2: Run test to verify it fails**

Run: `cd backend/python-brain && uv run pytest tests/test_workflow_state_models.py -q`
Expected: FAIL because `state_models.py` does not exist yet.

**Step 3: Write minimal implementation**

Create typed state models for:
- `InterviewWorkflowState`
- `ResumeIngestionState`
- `ReportWorkflowState`

Use explicit fields for:
- current topic/module/depth
- evaluation artifacts
- feature flags
- shadow execution metadata
- workflow version

**Step 4: Run test to verify it passes**

Run: `cd backend/python-brain && uv run pytest tests/test_workflow_state_models.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/python-brain/app/workflows backend/python-brain/app/workflow/state.py backend/python-brain/tests/test_workflow_state_models.py
git commit -m "refactor: add typed workflow state models"
```

## Task 3: Add Workflow Feature Flags And Runtime Selection

**Files:**
- Modify: `backend/python-brain/app/core/config.py`
- Create: `backend/python-brain/app/workflows/runtime.py`
- Test: `backend/python-brain/tests/test_workflow_runtime.py`

**Step 1: Write the failing test**

```python
from app.workflows.runtime import choose_interview_runtime


def test_choose_runtime_defaults_to_legacy():
    assert choose_interview_runtime(False, False) == "legacy"
```

**Step 2: Run test to verify it fails**

Run: `cd backend/python-brain && uv run pytest tests/test_workflow_runtime.py -q`
Expected: FAIL because the runtime selector does not exist.

**Step 3: Write minimal implementation**

Add settings such as:
- `WORKFLOW_USE_LANGGRAPH=false`
- `WORKFLOW_SHADOW_MODE=false`
- `WORKFLOW_REPORT_USE_LANGGRAPH=false`
- `WORKFLOW_RESUME_USE_LANGGRAPH=false`
- `WORKFLOW_TURN_USE_LANGGRAPH=false`

Implement a selector that decides whether to execute:
- legacy only
- shadow mode
- langgraph primary

**Step 4: Run test to verify it passes**

Run: `cd backend/python-brain && uv run pytest tests/test_workflow_runtime.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/python-brain/app/core/config.py backend/python-brain/app/workflows/runtime.py backend/python-brain/tests/test_workflow_runtime.py
git commit -m "feat: add workflow runtime flags"
```

## Task 4: Introduce Workflow Facades Around Existing Domain Services

**Files:**
- Create: `backend/python-brain/app/workflows/facades.py`
- Modify: `backend/python-brain/app/services/interview_engine.py`
- Modify: `backend/python-brain/app/services/report_service.py`
- Modify: `backend/python-brain/app/services/resume_parser.py`
- Test: `backend/python-brain/tests/test_workflow_facades.py`

**Step 1: Write the failing test**

```python
from app.workflows.facades import build_question_step


def test_build_question_step_returns_question_payload():
    payload = build_question_step(state={}, profile={}, resume_text="")
    assert "question" in payload
```

**Step 2: Run test to verify it fails**

Run: `cd backend/python-brain && uv run pytest tests/test_workflow_facades.py -q`
Expected: FAIL because the facade layer does not exist.

**Step 3: Write minimal implementation**

Create stateless facade functions for:
- `build_outline_step`
- `generate_question_step`
- `evaluate_answer_step`
- `advance_state_step`
- `aggregate_report_step`
- `extract_resume_text_step`

These functions should wrap current service behavior without changing outputs.

**Step 4: Run test to verify it passes**

Run: `cd backend/python-brain && uv run pytest tests/test_workflow_facades.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/python-brain/app/workflows/facades.py backend/python-brain/app/services/interview_engine.py backend/python-brain/app/services/report_service.py backend/python-brain/app/services/resume_parser.py backend/python-brain/tests/test_workflow_facades.py
git commit -m "refactor: extract workflow facade layer"
```

## Task 5: Add LangGraph Dependency And Skeleton Workflows

**Files:**
- Modify: `backend/python-brain/pyproject.toml`
- Create: `backend/python-brain/app/workflows/graphs/__init__.py`
- Create: `backend/python-brain/app/workflows/graphs/interview_graph.py`
- Create: `backend/python-brain/app/workflows/graphs/report_graph.py`
- Create: `backend/python-brain/app/workflows/graphs/resume_graph.py`
- Test: `backend/python-brain/tests/test_graph_builds.py`

**Step 1: Write the failing test**

```python
from app.workflows.graphs.interview_graph import build_interview_graph


def test_interview_graph_builds():
    graph = build_interview_graph()
    assert graph is not None
```

**Step 2: Run test to verify it fails**

Run: `cd backend/python-brain && uv run pytest tests/test_graph_builds.py -q`
Expected: FAIL because LangGraph graph builders do not exist.

**Step 3: Write minimal implementation**

Add `langgraph` to dependencies and create graph builders with placeholder nodes:
- interview graph nodes: `select_topic`, `generate_question`, `evaluate_answer`, `advance_state`
- report graph nodes: `aggregate_scores`, `build_action_plan`, `persist_report`
- resume graph nodes: `ocr_extract`, `pdf_extract`, `parse_profile`, `persist_cache`

Use the typed workflow states created earlier.

**Step 4: Run test to verify it passes**

Run: `cd backend/python-brain && uv run pytest tests/test_graph_builds.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/python-brain/pyproject.toml backend/python-brain/app/workflows/graphs backend/python-brain/tests/test_graph_builds.py
git commit -m "feat: add langgraph workflow skeletons"
```

## Task 6: Migrate Report Generation First

**Files:**
- Modify: `backend/python-brain/app/workflows/graphs/report_graph.py`
- Modify: `backend/python-brain/app/api/routes.py`
- Test: `backend/python-brain/tests/test_report_service.py`
- Test: `backend/python-brain/tests/golden/test_report_golden.py`

**Step 1: Write the failing test**

```python
def test_report_graph_matches_legacy_report_shape():
    payload = build_report_via_graph(sample_evaluations)
    assert "overall_score" in payload
    assert "action_plan_30d" in payload
```

**Step 2: Run test to verify it fails**

Run: `cd backend/python-brain && uv run pytest tests/test_report_service.py tests/golden/test_report_golden.py -q`
Expected: FAIL because the graph path is incomplete.

**Step 3: Write minimal implementation**

Implement report graph nodes by wrapping current report aggregation logic. Add routing logic so:
- legacy remains default
- shadow mode computes both reports and logs differences
- langgraph path can be enabled independently

**Step 4: Run test to verify it passes**

Run: `cd backend/python-brain && uv run pytest tests/test_report_service.py tests/golden/test_report_golden.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/python-brain/app/workflows/graphs/report_graph.py backend/python-brain/app/api/routes.py backend/python-brain/tests/test_report_service.py backend/python-brain/tests/golden/test_report_golden.py
git commit -m "feat: migrate report generation to langgraph"
```

## Task 7: Migrate Resume Ingestion Second

**Files:**
- Modify: `backend/python-brain/app/workflows/graphs/resume_graph.py`
- Modify: `backend/python-brain/app/api/routes.py`
- Test: `backend/python-brain/tests/test_api_smoke.py`
- Create: `backend/python-brain/tests/test_resume_graph.py`

**Step 1: Write the failing test**

```python
def test_resume_graph_preserves_ocr_then_pdf_fallback():
    result = run_resume_graph(sample_pdf_bytes)
    assert result.raw_text is not None
```

**Step 2: Run test to verify it fails**

Run: `cd backend/python-brain && uv run pytest tests/test_resume_graph.py tests/test_api_smoke.py -q`
Expected: FAIL because the graph path does not yet preserve extraction flow.

**Step 3: Write minimal implementation**

Implement explicit conditional routing in the resume graph:
- OCR enabled and sufficient text -> parse profile
- OCR failed or insufficient -> pypdf extraction
- pypdf failed -> raw decode fallback
- profile parse keeps existing LLM/rule behavior

Add logging fields that record which branch executed.

**Step 4: Run test to verify it passes**

Run: `cd backend/python-brain && uv run pytest tests/test_resume_graph.py tests/test_api_smoke.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/python-brain/app/workflows/graphs/resume_graph.py backend/python-brain/app/api/routes.py backend/python-brain/tests/test_resume_graph.py backend/python-brain/tests/test_api_smoke.py
git commit -m "feat: migrate resume ingestion to langgraph"
```

## Task 8: Introduce Structured Mission Guards For LLM Nodes

**Files:**
- Create: `backend/python-brain/app/workflows/mission_guards.py`
- Modify: `backend/python-brain/app/workflows/facades.py`
- Test: `backend/python-brain/tests/test_mission_guards.py`

**Step 1: Write the failing test**

```python
from app.workflows.mission_guards import validate_growth_feedback


def test_validate_growth_feedback_rejects_empty_actionable_feedback():
    assert validate_growth_feedback({"gaps": [], "reference_answer": ""}) is False
```

**Step 2: Run test to verify it fails**

Run: `cd backend/python-brain && uv run pytest tests/test_mission_guards.py -q`
Expected: FAIL because mission guards do not exist.

**Step 3: Write minimal implementation**

Implement reusable checks so LLM nodes must produce growth-oriented artifacts:
- actionable gaps
- grounded evidence
- reference answer when required
- no purely generic encouragement

Use these guards in report and interview graph nodes.

**Step 4: Run test to verify it passes**

Run: `cd backend/python-brain && uv run pytest tests/test_mission_guards.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/python-brain/app/workflows/mission_guards.py backend/python-brain/app/workflows/facades.py backend/python-brain/tests/test_mission_guards.py
git commit -m "feat: add mission guards for workflow nodes"
```

## Task 9: Migrate Interview Turn Workflow Last

**Files:**
- Modify: `backend/python-brain/app/workflows/graphs/interview_graph.py`
- Create: `backend/python-brain/app/workflows/executors.py`
- Modify: `backend/python-brain/app/api/routes.py`
- Test: `backend/python-brain/tests/test_interview_engine.py`
- Test: `backend/python-brain/tests/golden/test_interview_turn_golden.py`

**Step 1: Write the failing test**

```python
def test_interview_graph_matches_legacy_turn_contract():
    result = run_interview_turn_graph(sample_state, "sample answer")
    assert result.turn_eval.topic
    assert result.next_action in {"follow_up", "next_topic", "end"}
```

**Step 2: Run test to verify it fails**

Run: `cd backend/python-brain && uv run pytest tests/test_interview_engine.py tests/golden/test_interview_turn_golden.py -q`
Expected: FAIL because the interview graph is not fully wired.

**Step 3: Write minimal implementation**

Implement interview graph nodes for:
- load session context
- select current topic
- generate question
- evaluate answer
- decide next action
- advance state
- persist turn artifacts

Route logic must preserve:
- rule fallback when LLM evaluation fails
- `LLMEvaluationError` behavior where still required
- current `SendMessageResponse` contract
- current `evidence`, `gaps`, `dimension_scores`, `primary_dimension`

**Step 4: Run test to verify it passes**

Run: `cd backend/python-brain && uv run pytest tests/test_interview_engine.py tests/golden/test_interview_turn_golden.py tests/test_api_smoke.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/python-brain/app/workflows/graphs/interview_graph.py backend/python-brain/app/workflows/executors.py backend/python-brain/app/api/routes.py backend/python-brain/tests/test_interview_engine.py backend/python-brain/tests/golden/test_interview_turn_golden.py backend/python-brain/tests/test_api_smoke.py
git commit -m "feat: migrate interview turn workflow to langgraph"
```

## Task 10: Add Shadow Execution Diff Logging

**Files:**
- Create: `backend/python-brain/app/workflows/diffing.py`
- Modify: `backend/python-brain/app/workflows/executors.py`
- Modify: `backend/python-brain/app/core/logging.py`
- Test: `backend/python-brain/tests/test_workflow_diffing.py`

**Step 1: Write the failing test**

```python
from app.workflows.diffing import diff_turn_results


def test_diff_turn_results_highlights_contract_drift():
    diff = diff_turn_results({"next_action": "end"}, {"next_action": "next_topic"})
    assert "next_action" in diff
```

**Step 2: Run test to verify it fails**

Run: `cd backend/python-brain && uv run pytest tests/test_workflow_diffing.py -q`
Expected: FAIL because diffing utilities do not exist.

**Step 3: Write minimal implementation**

Create diff helpers for:
- turn result comparison
- report comparison
- resume parse comparison

Log only concise structured differences to avoid noisy production logs.

**Step 4: Run test to verify it passes**

Run: `cd backend/python-brain && uv run pytest tests/test_workflow_diffing.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/python-brain/app/workflows/diffing.py backend/python-brain/app/workflows/executors.py backend/python-brain/app/core/logging.py backend/python-brain/tests/test_workflow_diffing.py
git commit -m "feat: add workflow shadow diff logging"
```

## Task 11: Add LangChain Selectively For Structured Components

**Files:**
- Modify: `backend/python-brain/pyproject.toml`
- Create: `backend/python-brain/app/llm/prompts.py`
- Create: `backend/python-brain/app/llm/structured.py`
- Test: `backend/python-brain/tests/test_structured_llm_components.py`

**Step 1: Write the failing test**

```python
from app.llm.structured import parse_question_output


def test_parse_question_output_accepts_valid_schema():
    data = parse_question_output({"question": "Explain retry strategy."})
    assert data.question
```

**Step 2: Run test to verify it fails**

Run: `cd backend/python-brain && uv run pytest tests/test_structured_llm_components.py -q`
Expected: FAIL because selective structured components do not exist.

**Step 3: Write minimal implementation**

Use LangChain only for:
- reusable prompt templates
- structured output schemas/parsers
- future retriever integration boundaries

Do not change graph ownership of orchestration.

**Step 4: Run test to verify it passes**

Run: `cd backend/python-brain && uv run pytest tests/test_structured_llm_components.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/python-brain/pyproject.toml backend/python-brain/app/llm backend/python-brain/tests/test_structured_llm_components.py
git commit -m "feat: add selective langchain structured components"
```

## Task 12: Update Documentation And Operating Guide

**Files:**
- Modify: `README.md`
- Modify: `README_en.md`
- Modify: `PROJECT-PLAN.md`
- Modify: `backend/python-brain/README.md`
- Create: `docs/runbooks/langgraph-shadow-mode.md`

**Step 1: Write the failing documentation checklist**

Create a checklist in the PR description or temporary note with required updates:
- architecture description
- runtime flags
- migration status
- shadow mode instructions
- mission guard explanation

**Step 2: Run a grep check to verify missing docs**

Run: `rg -n "LangGraph|workflow|shadow mode|mission guard" README.md README_en.md PROJECT-PLAN.md backend/python-brain/README.md`
Expected: Gaps identified before editing.

**Step 3: Write documentation updates**

Document:
- why LangGraph was chosen over pure LangChain or continued custom state machine growth
- how shadow mode works
- how fallback behavior is preserved
- which parts are already migrated versus still legacy

**Step 4: Run a grep check to verify docs were updated**

Run: `rg -n "LangGraph|shadow mode|mission guard|feature flag" README.md README_en.md PROJECT-PLAN.md backend/python-brain/README.md docs/runbooks/langgraph-shadow-mode.md`
Expected: matching lines found in all required docs.

**Step 5: Commit**

```bash
git add README.md README_en.md PROJECT-PLAN.md backend/python-brain/README.md docs/runbooks/langgraph-shadow-mode.md
git commit -m "docs: add langgraph migration and operations guide"
```

## Task 13: Final Verification Before Primary Cutover

**Files:**
- No code changes required unless verification fails

**Step 1: Run focused tests**

Run:

```bash
cd backend/python-brain && uv run pytest \
  tests/golden/test_interview_turn_golden.py \
  tests/golden/test_report_golden.py \
  tests/test_api_smoke.py \
  tests/test_interview_engine.py \
  tests/test_report_service.py -q
```

Expected: PASS.

**Step 2: Run full test suite**

Run: `cd backend/python-brain && uv run pytest -q`
Expected: PASS.

**Step 3: Run one manual shadow-mode smoke test**

Run the server with shadow flags enabled and exercise:
- resume upload
- interview start
- one answer turn
- finish interview

Expected:
- user-visible behavior unchanged
- structured diff logs generated
- no 5xx errors

**Step 4: Decide cutover scope**

Document whether the first production cutover enables:
- report graph only
- report + resume graph
- full interview graph

**Step 5: Commit operational decision**

```bash
git add .
git commit -m "chore: finalize langgraph migration verification"
```

## Recommended First Shipping Slice

Do not ship everything at once. Best first production slice:
1. Report graph enabled
2. Resume graph in shadow mode
3. Interview graph shadow only

This sequence gives the team real workflow telemetry without risking the live interview experience.

## Risks To Watch Closely

- Prompt drift causing less actionable feedback
- Graph state mismatch with persisted SQLModel `state_json`
- Over-reliance on LangChain abstractions in places where plain Python is clearer
- Log volume explosion from shadow diffs
- Hidden contract drift in `SendMessageResponse` and report payload shape

## Definition Of Done

The migration is only complete when all statements are true:
- LangGraph runs the targeted workflow in production behind feature flags
- Golden tests show parity with legacy behavior for key paths
- Growth-oriented output fields remain present and useful
- Fallback logic remains intact when LLM calls fail
- README and runbooks describe the new architecture accurately
- The team can explain why LangGraph is the orchestration layer and LangChain is only a selective component layer

Plan complete and saved to `docs/plans/2026-03-09-langgraph-migration-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
