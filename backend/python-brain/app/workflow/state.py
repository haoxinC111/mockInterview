from typing import Any, TypedDict

from app.workflows.state_models import InterviewWorkflowState


class InterviewState(TypedDict):
    module_idx: int
    topic_idx: int
    depth: int
    max_depth: int
    turn_count: int
    max_turns: int
    evaluations: list[dict[str, Any]]
    outline: dict[str, Any]
    finished: bool


def from_workflow_state(state: InterviewWorkflowState) -> InterviewState:
    """Bridge typed workflow state back to legacy dict state shape."""
    return {
        "module_idx": state.module_idx,
        "topic_idx": state.topic_idx,
        "depth": state.depth,
        "max_depth": state.max_depth,
        "turn_count": state.turn_count,
        "max_turns": state.max_turns,
        "evaluations": state.evaluations,
        "outline": state.outline,
        "finished": state.finished,
    }
