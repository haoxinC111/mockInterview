# InterviewSim Project Guidelines

## Code Style
- **Python**: Use `uv` for dependency management. Target Python 3.11 (minimum 3.10).
- **Data Validation**: Use Pydantic models as the single source of truth for all API contracts and internal data structures.

## Architecture
- **Backend**: Python FastAPI + LangGraph for the interview flow state machine.
- **Frontend**: Lightweight Web Chat static pages (`frontend/web-chat/`) hosted directly by the FastAPI backend. No separate frontend dev server.
- **Storage**: SQLite local persistence for sessions, messages, reports, and resume parsing results.
- **LLM Integration**: Uses a relay service. Models configured via `.env` (e.g., `MiniMax-M2.5`, `glm-5`).

## Build and Test
- **Install Dependencies**:
  ```bash
  cd backend/python-brain
  uv sync --extra dev
  ```
- **Run Development Server**:
  ```bash
  cd backend/python-brain
  uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  ```
- **Run Tests**:
  ```bash
  cd backend/python-brain
  uv run pytest -q
  ```

## Conventions
- **Logging**: Use JSON line logs for full traceability. Always include `request_id` (HTTP level), `session_id` (interview level), or `report_id` (report level) in log events.
- **API Design**: Follow the Chat-MVP API contracts defined in `PROJECT-PLAN.md` (e.g., `/api/v1/resumes`, `/api/v1/interviews`).
