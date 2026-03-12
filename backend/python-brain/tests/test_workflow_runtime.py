from app.core.config import settings
from app.services.interview_engine import InterviewEngine
from app.workflows.executors import execute_interview_turn
from app.workflows.runtime import choose_interview_runtime, choose_workflow_runtime


def test_choose_runtime_defaults_to_legacy() -> None:
    assert choose_interview_runtime(False, False) == "legacy"


def test_choose_runtime_shadow() -> None:
    assert choose_interview_runtime(True, True) == "shadow"


def test_choose_runtime_langgraph_primary() -> None:
    assert choose_interview_runtime(True, False) == "langgraph"


def test_choose_workflow_runtime_by_feature_flags() -> None:
    runtimes = choose_workflow_runtime(
        workflow_use_langgraph=True,
        workflow_shadow_mode=True,
        workflow_report_use_langgraph=True,
        workflow_resume_use_langgraph=False,
        workflow_turn_use_langgraph=True,
    )

    assert runtimes.interview == "shadow"
    assert runtimes.report == "shadow"
    assert runtimes.resume == "legacy"


def test_shadow_turn_execution_does_not_double_advance_state(monkeypatch) -> None:
    monkeypatch.setattr(settings, "workflow_use_langgraph", True)
    monkeypatch.setattr(settings, "workflow_shadow_mode", True)
    monkeypatch.setattr(settings, "workflow_turn_use_langgraph", True)
    monkeypatch.setattr(settings, "interview_turn_use_llm", False)
    monkeypatch.setattr(settings, "interview_engine_use_llm", False)

    engine = InterviewEngine()
    outline = engine.build_outline(["python"])
    state = engine.init_state(outline)

    payload = execute_interview_turn(
        engine=engine,
        state=state,
        user_message="I know attention and prompt constraints",
        conversation_context=[],
    )
    # One user turn should only advance one step in persisted legacy state.
    assert payload["state"]["turn_count"] == 1
