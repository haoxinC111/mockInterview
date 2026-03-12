from __future__ import annotations

import copy
from typing import Any

from app.core.logging import log_workflow_diff
from app.services.interview_engine import InterviewEngine
from app.workflows.diffing import diff_report_results, diff_turn_results
from app.workflows.graphs.interview_graph import run_interview_turn_graph
from app.workflows.runtime import choose_workflow_runtime_from_settings


def execute_interview_turn(
    *,
    engine: InterviewEngine,
    state: dict[str, Any],
    user_message: str,
    conversation_context: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    runtime = choose_workflow_runtime_from_settings().interview
    if runtime == "langgraph":
        payload = run_interview_turn_graph(
            state=copy.deepcopy(state),
            user_message=user_message,
            conversation_context=conversation_context,
        )
        payload["runtime"] = runtime
        return payload

    if runtime == "shadow":
        legacy_state = copy.deepcopy(state)
        graph_state = copy.deepcopy(state)
        legacy = engine.process_turn(legacy_state, user_message, conversation_context=conversation_context)
        graph = run_interview_turn_graph(
            state=graph_state,
            user_message=user_message,
            conversation_context=conversation_context,
        )
        legacy_payload = {
            "question": legacy.question,
            "next_action": legacy.next_action,
            "turn_eval": legacy.turn_eval.model_dump(),
        }
        graph_payload = {
            "question": graph.get("question"),
            "next_action": graph.get("next_action"),
            "turn_eval": graph.get("turn_eval"),
        }
        log_workflow_diff("turn", diff_turn_results(legacy_payload, graph_payload))
        return {
            "question": legacy.question,
            "turn_eval": legacy.turn_eval.model_dump(),
            "next_action": legacy.next_action,
            "state": legacy.state,
            "reasoning": legacy.reasoning,
            "reference_answer": legacy.reference_answer,
            "score_rationale": legacy.score_rationale,
            "runtime": runtime,
        }

    legacy = engine.process_turn(state, user_message, conversation_context=conversation_context)
    return {
        "question": legacy.question,
        "turn_eval": legacy.turn_eval.model_dump(),
        "next_action": legacy.next_action,
        "state": legacy.state,
        "reasoning": legacy.reasoning,
        "reference_answer": legacy.reference_answer,
        "score_rationale": legacy.score_rationale,
        "runtime": runtime,
    }


def execute_report_generation(
    *,
    evaluations: list[dict[str, Any]],
    expected_salary: str,
    target_role: str,
    legacy_builder,
    graph_builder,
) -> tuple[dict[str, Any], str]:
    runtime = choose_workflow_runtime_from_settings().report
    if runtime == "langgraph":
        return graph_builder(evaluations=evaluations, expected_salary=expected_salary, target_role=target_role), runtime
    if runtime == "shadow":
        legacy = legacy_builder(evaluations, expected_salary, target_role)
        graph = graph_builder(evaluations=evaluations, expected_salary=expected_salary, target_role=target_role)
        log_workflow_diff("report", diff_report_results(legacy, graph))
        return legacy, runtime
    return legacy_builder(evaluations, expected_salary, target_role), runtime
