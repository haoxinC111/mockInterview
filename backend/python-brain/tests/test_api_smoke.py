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

    finish = client.post(f"/api/v1/interviews/{session_id}/finish")
    assert finish.status_code == 200
    report_id = finish.json()["report_id"]

    report = client.get(f"/api/v1/reports/{report_id}")
    assert report.status_code == 200
    assert report.json()["report_payload"]["overall_score"] >= 0
