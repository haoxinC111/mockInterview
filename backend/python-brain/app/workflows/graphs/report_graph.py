from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.workflows.facades import aggregate_report_step


class ReportGraphState(TypedDict, total=False):
    evaluations: list[dict[str, Any]]
    expected_salary: str
    target_role: str
    report_payload: dict[str, Any]


def _aggregate_scores(state: ReportGraphState) -> ReportGraphState:
    payload = aggregate_report_step(
        evaluations=state.get("evaluations", []),
        expected_salary=state.get("expected_salary", ""),
        target_role=state.get("target_role", "Agent Engineer"),
    )
    return {"report_payload": payload["report_payload"]}


def _build_action_plan(state: ReportGraphState) -> ReportGraphState:
    return {"report_payload": state.get("report_payload", {})}


def _persist_report(state: ReportGraphState) -> ReportGraphState:
    return {"report_payload": state.get("report_payload", {})}


def build_report_graph():
    builder = StateGraph(ReportGraphState)
    builder.add_node("aggregate_scores", _aggregate_scores)
    builder.add_node("build_action_plan", _build_action_plan)
    builder.add_node("persist_report", _persist_report)

    builder.add_edge(START, "aggregate_scores")
    builder.add_edge("aggregate_scores", "build_action_plan")
    builder.add_edge("build_action_plan", "persist_report")
    builder.add_edge("persist_report", END)
    return builder.compile()


def build_report_via_graph(
    *,
    evaluations: list[dict[str, Any]],
    expected_salary: str,
    target_role: str,
) -> dict[str, Any]:
    graph = build_report_graph()
    result = graph.invoke(
        {
            "evaluations": evaluations,
            "expected_salary": expected_salary,
            "target_role": target_role,
        }
    )
    return result["report_payload"]
