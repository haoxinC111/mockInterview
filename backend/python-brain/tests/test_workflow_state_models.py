from app.workflows.state_models import (
    InterviewWorkflowState,
    ReportWorkflowState,
    ResumeIngestionState,
    WorkflowFeatureFlags,
)


def test_interview_workflow_state_defaults() -> None:
    state = InterviewWorkflowState.initial()
    assert state.turn_count == 0
    assert state.finished is False
    assert state.workflow_version == "v1"
    assert state.feature_flags.use_langgraph is False
    assert state.shadow.enabled is False


def test_interview_workflow_state_initial_with_flags() -> None:
    flags = WorkflowFeatureFlags(use_langgraph=True, shadow_mode=True, turn_use_langgraph=True)
    state = InterviewWorkflowState.initial(feature_flags=flags)
    assert state.feature_flags.use_langgraph is True
    assert state.feature_flags.turn_use_langgraph is True
    assert state.shadow.enabled is True


def test_resume_and_report_state_models() -> None:
    resume_state = ResumeIngestionState(filename="resume.pdf")
    report_state = ReportWorkflowState(session_id=123)

    assert resume_state.filename == "resume.pdf"
    assert resume_state.workflow_version == "v1"
    assert report_state.session_id == 123
    assert report_state.report_payload == {}
