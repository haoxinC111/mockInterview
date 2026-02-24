from typing import Any, TypedDict


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
