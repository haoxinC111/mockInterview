from app.services.interview_engine import InterviewEngine


def test_interview_engine_progression() -> None:
    engine = InterviewEngine()
    outline = engine.build_outline(["python", "langgraph"])
    state = engine.init_state(outline)

    assert state["module_idx"] == 0
    assert state["topic_idx"] == 0

    result = engine.process_turn(state, "I use self-attention with position encoding and parallel compute")
    assert result.turn_eval.score >= 2
    assert result.next_action in {"follow_up", "next_topic", "end"}


def test_interview_engine_end_by_max_turn() -> None:
    engine = InterviewEngine()
    outline = engine.build_outline([])
    state = engine.init_state(outline)
    state["max_turns"] = 1

    result = engine.process_turn(state, "I don't know")
    assert result.next_action == "end"
    assert result.state["finished"] is True
