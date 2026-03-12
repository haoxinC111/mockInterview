# InterviewSim (Chat-MVP)

English | [中文](./README.md)

---

## Project Overview

An AI-powered mock interview system for interview training, built with LLM technology.

The current interview workflow is not powered by `langchain` or `langgraph`. It is implemented with the project's own `InterviewEngine`, structured state objects, and a hybrid rule-plus-LLM decision flow. The repository keeps `app/nodes/` only as a placeholder for possible future LangGraph expansion, but the current runtime does not depend on or execute either framework.

At this stage, `main` should be treated as the stable custom-state-machine baseline: it preserves the currently working version, supports regression comparison, and acts as the reference point for any workflow migration. LangGraph-oriented refactoring is best developed in a separate branch and a separate worktree so experimental workflow changes do not get mixed directly into the baseline.
The latest LangGraph migration work currently lives in the `feat/langgraph-migration` worktree at `/Users/chenhaoxin/ccProjects/mockInterview/.worktrees/langgraph-migration`.

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

## Current Status And Roadmap

### Current Baseline

- `main` still uses the custom `InterviewEngine` state machine as the production path
- The interview flow remains intentionally explicit and growth-oriented, with rule-based fallbacks and constrained LLM outputs
- The current branch is best suited for stability fixes, docs updates, regression tests, and baseline quality validation

### Future Direction

- The recommended next-step architecture is not a free-form autonomous agent flow, but `LangGraph` as the workflow orchestration layer
- `LangChain` should be used selectively as a component layer for structured outputs, prompts, retrieval, or tool wrappers, not as the primary business-process controller
- The migration goal is to preserve the current growth-oriented behavior, fallback safety, and API contracts while improving extensibility, recoverability, and workflow-level observability

### Recommended Development Flow

- Keep the current directory on `main` for the custom-state-machine baseline
- Create a dedicated branch such as `feat/langgraph-migration`
- Develop the LangGraph version in a separate git worktree for side-by-side comparison with `main`
- See `docs/designs/2026-03-09-agent-orchestration-migration-strategy.md` for the design rationale
- See `docs/plans/2026-03-09-langgraph-migration-plan.md` for the phased implementation plan

## Notes

- Frontend doesn't require a separate process (served by backend `app.main`).
- The current PDF extraction chain is: `Ollama deepseek-ocr` -> `pypdf` text-layer extraction -> raw UTF-8 decode fallback.
- For scanned, image-based, multi-column, or layout-heavy PDFs, `deepseek-ocr` should be considered the preferred path. If parsing falls back to `pypdf` or raw decode, quality can degrade noticeably, with common issues such as broken line merges, missing text, wrong reading order, and lost structure.
- The project does not currently use `langchain` or `langgraph` as its agent orchestration framework; the implementation is a custom state-machine-style interview engine with constrained JSON LLM outputs.
- Voice input requires `faster-whisper` (install with `--extra stt`) and `ffmpeg` (`brew install ffmpeg`, WAV format exempt).
- For separate frontend/backend deployment, add a separate `frontend` dev server.

## Tech Stack

| Category | Technology |
|----------|------------|
| Backend API | FastAPI + Python |
| Orchestration | Custom `InterviewEngine` state machine with rule-plus-LLM branching |
| Storage | SQLModel + SQLite |
| Frontend | Vanilla JS / HTML / CSS (hosted by FastAPI) |
| LLM Access | OpenAI-compatible relay, currently defaulting to `MiniMax-M2.5` with `glm-5` as a candidate model |
| PDF Parsing | Ollama `deepseek-ocr` (preferred) + `pypdf` (fallback) + `pymupdf` (PDF-to-image for OCR) |
| STT | `faster-whisper` |

## License

MIT License