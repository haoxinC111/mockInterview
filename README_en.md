# InterviewSim (Chat-MVP)

English | [中文](./README.md)

---

## Project Overview

An AI-powered mock interview system for interview training, built with LLM technology.

## Features

- 📄 **Resume Parsing** - Auto-parse PDF resumes
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
| `RESUME_OCR_ENABLED=true` | Local Ollama OCR for PDF parsing |

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

## Notes

- Frontend doesn't require a separate process (served by backend `app.main`).
- Voice input requires `faster-whisper` (install with `--extra stt`) and `ffmpeg` (`brew install ffmpeg`, WAV format exempt).
- For separate frontend/backend deployment, add a separate `frontend` dev server.

## Tech Stack

| Category | Technology |
|----------|------------|
| Backend | FastAPI + Python |
| Frontend | Static pages (backend hosted) |
| LLM | MiniMax, GLM, etc. |
| STT | Faster-Whisper |

## License

MIT License