import os

# Force LLM off before any app imports
os.environ["INTERVIEW_ENGINE_USE_LLM"] = "false"
os.environ["INTERVIEW_TURN_USE_LLM"] = "false"
os.environ["RESUME_PARSER_USE_LLM"] = "false"
os.environ["STT_ENABLED"] = "false"

from fastapi.testclient import TestClient

from app.core.database import init_db
from app.main import app

init_db()
client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_end_to_end_chat_flow() -> None:
    fake_resume = b"Agent engineer with 5 years. Skills: Python, LangGraph, RAG. Project: built planner executor."
    upload = client.post(
        "/api/v1/resumes",
        files={"file": ("resume.pdf", fake_resume, "application/pdf")},
    )
    assert upload.status_code == 200
    resume_id = upload.json()["resume_id"]

    start = client.post(
        "/api/v1/interviews",
        json={
            "resume_id": resume_id,
            "target_role": "Agent Engineer",
            "expected_salary": "20k-30k",
            "model": "glm-5",
        },
    )
    assert start.status_code == 200
    session_id = start.json()["session_id"]

    send = client.post(
        f"/api/v1/interviews/{session_id}/messages",
        json={"user_message": "I know attention, prompt constraints, and tool executor retry fallback."},
    )
    assert send.status_code == 200
    assert "assistant_message" in send.json()
    turn_eval = send.json()["turn_eval"]
    assert turn_eval["score_rationale"]
    assert turn_eval["reference_answer"]
    assert "evidence" in turn_eval
    assert "gaps" in turn_eval

    finish = client.post(f"/api/v1/interviews/{session_id}/finish")
    assert finish.status_code == 200
    report_id = finish.json()["report_id"]
    report_payload = finish.json()["report_payload"]

    report = client.get(f"/api/v1/reports/{report_id}")
    assert report.status_code == 200
    rp = report.json()["report_payload"]
    assert rp["overall_score"] >= 0
    # v0.6: report should include dimension_scores, radar_chart, action_plan_30d
    assert "dimension_scores" in rp
    assert "radar_chart" in rp
    assert "labels" in rp["radar_chart"]
    assert "values" in rp["radar_chart"]
    assert "action_plan_30d" in rp
    assert "overall" in rp["action_plan_30d"]
    assert "disclaimer" in rp

    # Verify trace endpoint works after a session has turns
    trace = client.get(f"/api/v1/sessions/{session_id}/trace")
    assert trace.status_code == 200
    trace_data = trace.json()
    assert trace_data["session_id"] == session_id
    assert len(trace_data["turns"]) >= 1
    assert "user_input" in trace_data["turns"][0]
    assert "assistant_output" in trace_data["turns"][0]

    # Verify workflow endpoint
    workflow = client.get(f"/api/v1/sessions/{session_id}/workflow")
    assert workflow.status_code == 200
    wf = workflow.json()
    assert wf["session_id"] == session_id
    assert len(wf["evaluations"]) >= 1

    # Verify sessions list
    sessions_resp = client.get("/api/v1/sessions")
    assert sessions_resp.status_code == 200
    assert len(sessions_resp.json()["sessions"]) >= 1


def test_start_with_answer_style() -> None:
    """Starting an interview with answer_style should persist."""
    fake_resume = b"Engineer: Python, Docker, K8s."
    upload = client.post(
        "/api/v1/resumes",
        files={"file": ("resume.pdf", fake_resume, "application/pdf")},
    )
    resume_id = upload.json()["resume_id"]

    start = client.post(
        "/api/v1/interviews",
        json={
            "resume_id": resume_id,
            "target_role": "SRE",
            "expected_salary": "15k-25k",
            "model": "glm-5",
            "answer_style": "thorough",
        },
    )
    assert start.status_code == 200
    assert start.json()["session_id"]


def test_404_on_missing_session() -> None:
    resp = client.post("/api/v1/interviews/99999/messages",
                       json={"user_message": "hello"})
    assert resp.status_code == 404


def test_404_on_missing_report() -> None:
    resp = client.get("/api/v1/reports/99999")
    assert resp.status_code == 404


def test_resume_active_session() -> None:
    """Resume an active session returns messages and state."""
    fake_resume = b"Agent engineer. Skills: Python, FastAPI."
    upload = client.post(
        "/api/v1/resumes",
        files={"file": ("resume.pdf", fake_resume, "application/pdf")},
    )
    resume_id = upload.json()["resume_id"]

    start = client.post(
        "/api/v1/interviews",
        json={
            "resume_id": resume_id,
            "target_role": "Backend Dev",
            "expected_salary": "15k-25k",
            "model": "glm-5",
        },
    )
    session_id = start.json()["session_id"]

    # Send one message to create some history
    client.post(
        f"/api/v1/interviews/{session_id}/messages",
        json={"user_message": "I have experience with REST APIs and async programming."},
    )

    # Resume should return session data + messages
    resume = client.post(f"/api/v1/interviews/{session_id}/resume")
    assert resume.status_code == 200
    data = resume.json()
    assert data["session_id"] == session_id
    assert data["status"] == "active"
    assert data["target_role"] == "Backend Dev"
    assert len(data["messages"]) >= 2  # at least first_question + user + assistant
    assert data["outline_summary"]
    assert data["turn_count"] >= 1


def test_resume_finished_session_fails() -> None:
    """Cannot resume a finished session."""
    fake_resume = b"Engineer: Python, Docker."
    upload = client.post(
        "/api/v1/resumes",
        files={"file": ("resume.pdf", fake_resume, "application/pdf")},
    )
    resume_id = upload.json()["resume_id"]

    start = client.post(
        "/api/v1/interviews",
        json={
            "resume_id": resume_id,
            "target_role": "SRE",
            "expected_salary": "20k",
            "model": "glm-5",
        },
    )
    session_id = start.json()["session_id"]

    # Finish the session
    client.post(f"/api/v1/interviews/{session_id}/finish")

    # Resume should fail
    resume = client.post(f"/api/v1/interviews/{session_id}/resume")
    assert resume.status_code == 400
    assert "finished" in resume.json()["detail"]


def test_resume_nonexistent_session() -> None:
    resp = client.post("/api/v1/interviews/99999/resume")
    assert resp.status_code == 404


def test_sessions_list_includes_turn_count() -> None:
    """Sessions list should include turn_count field."""
    resp = client.get("/api/v1/sessions")
    assert resp.status_code == 200
    sessions = resp.json()["sessions"]
    assert len(sessions) >= 1
    assert "turn_count" in sessions[0]


def test_short_resume_blocks_interview_start() -> None:
    upload = client.post(
        "/api/v1/resumes",
        files={"file": ("resume.pdf", b"x", "application/pdf")},
    )
    assert upload.status_code == 200
    assert upload.json()["readiness"] == "needs_more_input"
    assert upload.json()["quality_score"] == 0
    assert upload.json()["warnings"]

    start = client.post(
        "/api/v1/interviews",
        json={
            "resume_id": upload.json()["resume_id"],
            "target_role": "Agent Engineer",
            "expected_salary": "20k-30k",
        },
    )
    assert start.status_code == 400
    assert "growth-oriented interview" in start.json()["detail"]


def test_finish_without_turns_returns_training_guidance_report() -> None:
    upload = client.post(
        "/api/v1/resumes?force_reparse=true",
        files={"file": ("resume-training.txt", b"Skills: Python, FastAPI\nProject: built APIs for payment retries", "text/plain")},
    )
    assert upload.status_code == 200

    start = client.post(
        "/api/v1/interviews",
        json={
            "resume_id": upload.json()["resume_id"],
            "target_role": "Backend Dev",
            "expected_salary": "15k-25k",
        },
    )
    assert start.status_code == 200
    session_id = start.json()["session_id"]

    finish = client.post(f"/api/v1/interviews/{session_id}/finish")
    assert finish.status_code == 200
    report_payload = finish.json()["report_payload"]
    assert report_payload["report_mode"] == "training_guidance"
    assert report_payload["salary_fit"]["level"] == "样本不足"
