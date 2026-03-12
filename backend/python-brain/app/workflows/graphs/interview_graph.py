from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.workflows.facades import advance_state_step, evaluate_answer_step, generate_question_step


class InterviewGraphState(TypedDict, total=False):
    state: dict[str, Any]
    user_message: str
    conversation_context: list[dict[str, str]]
    profile: dict[str, Any]
    resume_text: str
    question: str
    turn_eval: dict[str, Any]
    next_action: str
    reasoning: str | None
    reference_answer: str | None
    score_rationale: str | None


def _select_topic(state: InterviewGraphState) -> InterviewGraphState:
    return state


def _generate_question(state: InterviewGraphState) -> InterviewGraphState:
    payload = generate_question_step(
        state=state.get("state", {}),
        profile=state.get("profile"),
        resume_text=state.get("resume_text"),
    )
    return {"question": payload["question"]}


def _evaluate_answer(state: InterviewGraphState) -> InterviewGraphState:
    payload = evaluate_answer_step(
        state=state.get("state", {}),
        user_message=state.get("user_message", ""),
        conversation_context=state.get("conversation_context"),
    )
    return {
        "state": payload["state"],
        "turn_eval": payload["turn_eval"],
        "next_action": payload["next_action"],
        "question": payload["question"],
        "reasoning": payload.get("reasoning"),
        "reference_answer": payload.get("reference_answer"),
        "score_rationale": payload.get("score_rationale"),
    }


def _advance_state(state: InterviewGraphState) -> InterviewGraphState:
    payload = advance_state_step(state=state.get("state", {}))
    return {"state": payload["state"]}


def build_interview_graph():
    builder = StateGraph(InterviewGraphState)
    builder.add_node("select_topic", _select_topic)
    builder.add_node("generate_question", _generate_question)
    builder.add_node("evaluate_answer", _evaluate_answer)
    builder.add_node("advance_state", _advance_state)

    builder.add_edge(START, "select_topic")
    builder.add_edge("select_topic", "generate_question")
    builder.add_edge("generate_question", "evaluate_answer")
    builder.add_edge("evaluate_answer", "advance_state")
    builder.add_edge("advance_state", END)
    return builder.compile()


def run_interview_turn_graph(
    *,
    state: dict[str, Any],
    user_message: str,
    conversation_context: list[dict[str, str]] | None = None,
    profile: dict[str, Any] | None = None,
    resume_text: str | None = None,
) -> dict[str, Any]:
    graph = build_interview_graph()
    result = graph.invoke(
        {
            "state": state,
            "user_message": user_message,
            "conversation_context": conversation_context or [],
            "profile": profile or {},
            "resume_text": resume_text or "",
        }
    )
    return {
        "question": result["question"],
        "turn_eval": result["turn_eval"],
        "next_action": result["next_action"],
        "state": result["state"],
        "reasoning": result.get("reasoning"),
        "reference_answer": result.get("reference_answer"),
        "score_rationale": result.get("score_rationale"),
    }
