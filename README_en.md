# InterviewSim (Chat-MVP)

English | [中文](./README.md)

---

## Project Overview

An AI-powered mock interview system for interview training, built with LLM technology.

The repository is now in an incremental migration to `LangGraph` orchestration. Current status is dual-path runtime:
- legacy remains default (`InterviewEngine` + rule/LLM hybrid decisions)
- `LangGraph` can be enabled per workflow (report, resume, turn) or run in shadow mode
- `LangChain` is used selectively for structured components (prompt/schema), not as the orchestration owner

At this stage, `main` should be treated as the stable custom-state-machine baseline: it preserves the currently working version, supports regression comparison, and acts as the reference point for any workflow migration. LangGraph-oriented refactoring is best developed in a separate branch and a separate worktree so experimental workflow changes do not get mixed directly into the baseline.

## Features

- 📄 **Resume Parsing** - Auto-parse PDF resumes with plaintext fallback
- 🤖 **AI Interviewer** - Smart follow-up questions and in-depth discussion
- 📊 **Multi-dimensional Evaluation** - Technical depth, architecture design, engineering practice, communication
- 🎙️ **Voice Input** - Speech-to-text interview support
- 📝 **Detailed Reports** - Radar charts, improvement suggestions
- 🎯 **Role-based Framework** - Support for Agent Engineer and other job roles

## Directory Structure

```
backend/python-brain  - Backend service
frontend/web-chat     - Frontend assets
```

## Configuration

### Backend Config File

`backend/python-brain/.env`

### Pre-configured Models

| Variable | Value |
|----------|-------|
| LLM_BASE_URL | `https://v1.cdks.work` |
| LLM_MODEL_DEFAULT | `MiniMax-M2.5` |
| LLM_MODEL_CANDIDATES | `MiniMax-M2.5,glm-5` |

### Optional Flags

Disabled by default, enables actual LLM calls when enabled:

| Variable | Description |
|----------|-------------|
| `RESUME_PARSER_USE_LLM=true` | Resume parsing with LLM |
| `INTERVIEW_ENGINE_USE_LLM=true` | Interview engine with LLM |
| `INTERVIEW_TURN_USE_LLM=true` | Per-turn scoring/follow-up (higher latency) |
| `RESUME_OCR_ENABLED=true` | Prefer local Ollama `deepseek-ocr` for PDF parsing |
| `WORKFLOW_USE_LANGGRAPH=true` | Global switch for LangGraph runtime |
| `WORKFLOW_SHADOW_MODE=true` | Shadow mode (user-visible output stays legacy) |
| `WORKFLOW_REPORT_USE_LANGGRAPH=true` | Run report workflow via LangGraph |
| `WORKFLOW_RESUME_USE_LANGGRAPH=true` | Run resume ingestion via LangGraph |
| `WORKFLOW_TURN_USE_LANGGRAPH=true` | Run interview turn workflow via LangGraph |

### Voice Input

Enabled by default, using local Whisper inference:

| Variable | Description |
|----------|-------------|
| `STT_ENABLED=true` | Enable voice input |
| `STT_MODEL=small` | Whisper model size (options: tiny/base/small/medium/large) |

### Logging Config

| Variable | Description |
|----------|-------------|
| `LOG_DIR=logs` | Log directory |
| `LOG_FILE=interviewsim.log` | Log file |
| `SUMMARY_LOG_FILE=interviewsim.summary.log` | Summary log file |

Default log path: `backend/python-brain/logs/`

## Quick Start

### 1) Install Backend Dependencies

```bash
cd backend/python-brain
uv sync --extra dev --extra stt
```

### 2) Start Backend

Backend hosts frontend pages:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3) Access

| Service | URL |
|---------|-----|
| Web Chat | http://127.0.0.1:8000/ |
| API Docs | http://127.0.0.1:8000/docs |

## Quick Test

```bash
cd backend/python-brain
uv run pytest -q
```

## This Update (2026-03-12)

- Added `resume readiness` gating before interview start, returning `quality_score` and `readiness` for thin resumes.
- Changed zero-turn report semantics to `training_guidance` instead of immediate salary mismatch judgment.
- Added low-signal report fallback so weak sessions still produce actionable growth-oriented risks.
- Reduced noisy PDF parsing attempts for plain-text uploads.
- Automated verification is complete: the worktree test suite passes.
- Manual QA status: **not manually tested** in a real browser flow yet.

## Current Status And Roadmap

### Current Baseline

- Legacy path is still the default user-facing path for stability
- `LangGraph` graph skeletons and runtime selector are now integrated for phased rollout
- Shadow diff logging is available to track turn/report/resume drift before cutover

### Future Direction

- The target architecture remains `LangGraph` as workflow runtime with explicit fallback behavior
- `LangChain` remains selective (prompt templates and structured parsers), not the process controller
- The migration goal is to preserve the current growth-oriented behavior, fallback safety, and API contracts while improving extensibility, recoverability, and workflow-level observability

### Recommended Development Flow

- Keep the current directory on `main` for the custom-state-machine baseline
- Create a dedicated branch such as `feat/langgraph-migration`
- Develop the LangGraph version in a separate git worktree for side-by-side comparison with `main`
- See `docs/designs/2026-03-09-agent-orchestration-migration-strategy.md` for the design rationale
- See `docs/plans/2026-03-09-langgraph-migration-plan.md` for the phased implementation plan
- See `docs/runbooks/langgraph-shadow-mode.md` for shadow-mode operations

## Notes

- Frontend doesn't require a separate process (served by backend `app.main`).
- The current PDF extraction chain is: `Ollama deepseek-ocr` -> `pypdf` text-layer extraction -> raw UTF-8 decode fallback.
- For scanned, image-based, multi-column, or layout-heavy PDFs, `deepseek-ocr` should be considered the preferred path. If parsing falls back to `pypdf` or raw decode, quality can degrade noticeably, with common issues such as broken line merges, missing text, wrong reading order, and lost structure.
- Runtime is now migration-ready: legacy default + LangGraph feature flags + shadow mode diffing.
- Voice input requires `faster-whisper` (install with `--extra stt`) and `ffmpeg` (`brew install ffmpeg`, WAV format exempt).
- For separate frontend/backend deployment, add a separate `frontend` dev server.

## Tech Stack

| Category | Technology |
|----------|------------|
| Backend API | FastAPI + Python |
| Orchestration | Dual-path runtime: legacy default + LangGraph workflows behind feature flags |
| Storage | SQLModel + SQLite |
| Frontend | Vanilla JS / HTML / CSS (hosted by FastAPI) |
| LLM Access | OpenAI-compatible relay, currently defaulting to `MiniMax-M2.5` with `glm-5` as a candidate model |
| PDF Parsing | Ollama `deepseek-ocr` (preferred) + `pypdf` (fallback) + `pymupdf` (PDF-to-image for OCR) |
| STT | `faster-whisper` |

## License

MIT License
