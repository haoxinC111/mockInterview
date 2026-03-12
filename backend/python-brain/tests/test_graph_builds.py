from app.workflows.graphs.interview_graph import build_interview_graph
from app.workflows.graphs.report_graph import build_report_graph
from app.workflows.graphs.resume_graph import build_resume_graph


def test_interview_graph_builds() -> None:
    graph = build_interview_graph()
    assert graph is not None


def test_report_graph_builds() -> None:
    graph = build_report_graph()
    assert graph is not None


def test_resume_graph_builds() -> None:
    graph = build_resume_graph()
    assert graph is not None
