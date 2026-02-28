# InterviewSim Project Guidelines

## Quick Reference

```bash
cd backend/python-brain
uv sync --extra dev --extra stt   # Install all deps
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000  # Dev server
uv run pytest -q                  # Run tests (4 tests, ~60-90s due to LLM mocks)
```

- Web UI: `http://127.0.0.1:8000/` (redirects to `/web/`)
- API docs: `http://127.0.0.1:8000/docs`
- Logs: `backend/python-brain/logs/interviewsim.log` (full) + `interviewsim.summary.log` (key events)

## Project Mission & Design Principles

> **The system's core goal is NOT to "stump candidates" but to "help candidates grow".**
> （本系统的核心目标不是「考倒候选人」，而是「帮助候选人成长」。）

- Every question should guide candidates to expose their real capability boundaries.
- Every evaluation should point out specific improvable directions.
- Every piece of feedback should leave candidates knowing more clearly what to study and how to practice.
- Always prioritize "improving candidate ability" above all else.

**Feature decision rule**: If a new feature doesn't help candidates more precisely know "what to improve and how", it's not worth building.

This mission is injected into all LLM system prompts via `PROJECT_MISSION` constant in `app/core/config.py`. Do not remove or weaken it.

### Design Implications
- **Evaluation features**: Prioritize actionable feedback (evidence, gaps, reference answers) over numerical scores alone.
- **Reports**: Always include specific per-dimension improvement suggestions. Generic "needs improvement" is unacceptable.
- **Question generation**: Questions should probe capability boundaries constructively — never trick or mislead.
- **UI**: Growth-oriented information (gaps, action plans, reference answers) must be highly visible, not buried.
- **Scoring model**: 4-dimension evaluation (technical_depth, architecture_design, engineering_practice, communication). See `PROJECT-PLAN.md` §8.1.

## Architecture

```
backend/python-brain/
  app/
    main.py          ← FastAPI app, CORS, request_id middleware, static mount
    api/routes.py    ← All REST endpoints (single router, prefix /api/v1)
    core/            ← config (pydantic-settings), database (SQLModel/SQLite), logging (JSON-line), request_context (ContextVar)
    models/
      db.py          ← SQLModel table classes (Resume, InterviewSession, InterviewMessage, etc.)
      schemas.py     ← Pure Pydantic models (CandidateProfile, InterviewOutline, TurnEvaluation, etc.)
    services/        ← Business logic: interview_engine, llm_client, resume_parser, report_service, stt_service
    workflow/state.py ← InterviewState TypedDict
    nodes/           ← Empty placeholder for future LangGraph nodes
frontend/web-chat/   ← Vanilla HTML/JS/CSS, served by FastAPI at /web/
```

- **Single backend service**: FastAPI handles API + static files. No separate frontend dev server.
- **Storage**: SQLite via SQLModel. JSON columns for complex nested data (`profile_json`, `state_json`).
- **LLM**: Relay service at configurable base URL (OpenAI-compatible). Models: `MiniMax-M2.5`, `glm-5`.
- **OCR**: Local Ollama (`deepseek-ocr`) for PDF resume parsing (optional feature flag).
- **STT**: Local `faster-whisper` model. Frontend records audio → converts to 16kHz WAV in browser → POST to `/api/v1/stt`.

## Code Style & Conventions

- **Python 3.12** (minimum 3.10). Use `uv` exclusively for dependency management.
- **Type hints**: Use `X | None` (PEP 604), not `Optional[X]`. Use `from __future__ import annotations` in service files.
- **Pydantic models** are the single source of truth for API contracts. DB models use SQLModel (Pydantic + SQLAlchemy hybrid).
- **Feature flags**: All LLM-dependent features guarded by `settings.*_use_llm` booleans. Always provide a rule-based fallback.
- **Logging**: Use `log_event(event_name, **fields)` for all log output. Always include `request_id`, `session_id`, or `report_id`. Use `log_summary()` for key business events.
- **State mutation**: Always `copy.deepcopy()` on `state_json` before/after modification — SQLModel needs this to detect changes on JSON columns.
- **LLM client**: Returns `(parsed_json, reasoning_content)` tuples. Always handle parsing failures gracefully.

## Key Patterns

- **3-tier fallback**: Resume parsing and outline generation both try LLM → heuristic → hardcoded default.
- **Scoring**: 10-point scale. Branching: score ≥ 7 deepens, ≤ 2 skips module, LLM decides at ≥ 5. Each evaluation includes `score_rationale`, `evidence`, `gaps`, `reference_answer`.
- **Config**: All via `.env` → `pydantic-settings`. Singleton `settings = Settings()` in `app/core/config.py`.
- **DI in routes**: `db: Session = Depends(get_session)` for database access.
- **Resume caching**: By `(filename, sha256_hash)`. Pass `force_reparse=true` to bypass.
- **Conversation window**: Last 10 messages sent as LLM context.

## Frontend

- Vanilla JS with IIFE modules. Helper: `byId(id)` wraps `document.getElementById`.
- CSS custom properties in `:root` / `[data-theme="dark"]`. Dark mode persisted to `localStorage`.
- "Stealth mode" replaces interview terminology with generic chat terms (面试→对话, 简历→资料).
- Voice input: MediaRecorder → WAV conversion (OfflineAudioContext 16kHz) → backend `/api/v1/stt`.
- Global state: `resumeId`, `sessionId`, `stealthOn`. Exposed: `window._micBtn`, `window._stopListening`.

## Testing

- Tests in `backend/python-brain/tests/`. Run with `uv run pytest -q`.
- `test_api_smoke.py`: Full end-to-end flow with `TestClient(app)` — upload → start → chat → finish → report.
- `test_interview_engine.py`: Unit tests for engine logic — outline building, turn progression, termination.
- Tests use `init_db()` at module scope. LLM flags default to off, so tests use rule-based paths.

## Environment Variables (`.env`)

| Variable | Purpose | Default |
|---|---|---|
| `LLM_BASE_URL` | Relay endpoint | — |
| `LLM_API_KEY` | Relay API key | — |
| `LLM_MODEL_DEFAULT` | Primary model | `MiniMax-M2.5` |
| `RESUME_PARSER_USE_LLM` | LLM for resume parsing | `false` |
| `INTERVIEW_ENGINE_USE_LLM` | LLM for outline gen | `false` |
| `INTERVIEW_TURN_USE_LLM` | LLM for per-turn eval | `false` |
| `RESUME_OCR_ENABLED` | Ollama OCR for PDFs | `false` |
| `STT_ENABLED` | Whisper speech-to-text | `true` |
| `STT_MODEL` | Whisper model size | `small` |
| `DATABASE_URL` | SQLite path | `sqlite:///./interview_sim.db` |

## Pitfalls

- **JSON columns**: SQLModel won't detect in-place mutations on `Column(JSON)`. Always reassign after `deepcopy()`.
- **Stale state**: `process_turn()` reads `state_json` from DB, mutates, writes back. Don't cache across requests.
- **ffmpeg**: Required by `faster-whisper` for non-WAV formats. The frontend converts to WAV to avoid this dependency, but install `brew install ffmpeg` for robustness.
- **Port 8000**: Dev server and frontend static files share the same process. No CORS issues in dev.
- **Test duration**: Tests take ~60-90s due to SQLite setup and engine logic. Use `-q --tb=short` for concise output.
