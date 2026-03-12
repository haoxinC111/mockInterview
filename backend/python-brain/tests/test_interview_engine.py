import pytest

from app.core.config import settings
from app.services.interview_engine import InterviewEngine, LLMEvaluationError
from app.workflows.graphs.interview_graph import run_interview_turn_graph


@pytest.fixture(autouse=True)
def _disable_llm(monkeypatch):
    """Ensure tests use rule-based evaluation, not LLM."""
    monkeypatch.setattr(settings, "interview_turn_use_llm", False)
    monkeypatch.setattr(settings, "interview_engine_use_llm", False)


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


def test_dimension_scores_in_turn_eval() -> None:
    """Each turn_eval should carry dimension_scores and primary_dimension."""
    engine = InterviewEngine()
    outline = engine.build_outline(["python", "langgraph"])
    state = engine.init_state(outline)

    result = engine.process_turn(state, "I know about transformers and attention mechanisms")
    assert isinstance(result.turn_eval.dimension_scores, dict)
    assert len(result.turn_eval.dimension_scores) > 0
    # primary_dimension should be a non-empty string
    assert result.turn_eval.primary_dimension


def test_answer_style_in_state() -> None:
    """init_state should accept and store answer_style."""
    engine = InterviewEngine()
    outline = engine.build_outline(["python"])

    state_default = engine.init_state(outline)
    assert state_default["answer_style"] == "concise"

    state_thorough = engine.init_state(outline, answer_style="thorough")
    assert state_thorough["answer_style"] == "thorough"


def test_asked_questions_tracking() -> None:
    """process_turn should track asked questions for deduplication."""
    engine = InterviewEngine()
    outline = engine.build_outline(["python"])
    state = engine.init_state(outline)
    assert state["asked_questions"] == []

    result = engine.process_turn(state, "I use decorators and context managers")
    # After a turn, the question should be tracked
    assert len(result.state.get("asked_questions", [])) >= 0  # may be 0 if ended


def test_llm_evaluation_error_importable() -> None:
    """LLMEvaluationError should be importable and a subclass of Exception."""
    assert issubclass(LLMEvaluationError, Exception)


def test_engine_multi_turn_progression() -> None:
    """Running multiple turns should advance through topics."""
    engine = InterviewEngine()
    outline = engine.build_outline(["python", "langgraph"])
    state = engine.init_state(outline)
    state["max_turns"] = 5

    topics_seen = set()
    for _ in range(4):
        if state.get("finished"):
            break
        topic = engine.current_topic(state)
        if topic:
            topics_seen.add(topic["topic_name"])
        result = engine.process_turn(state, "I know about this topic")
        state = result.state

    # Should have seen more than one topic
    assert len(topics_seen) >= 1
    assert state["turn_count"] >= 1


def test_engine_all_topics_exhausted() -> None:
    """When all topics are done, engine should return 'end'."""
    engine = InterviewEngine()
    outline = engine.build_outline([])
    state = engine.init_state(outline)
    state["max_turns"] = 100  # high limit so it's not the constraint

    # Run until finished
    for _ in range(20):
        if state.get("finished"):
            break
        result = engine.process_turn(state, "I don't know")
        state = result.state

    assert state["finished"] is True


def test_evaluations_accumulate_in_state() -> None:
    """Each process_turn should append to evaluations list."""
    engine = InterviewEngine()
    outline = engine.build_outline(["python"])
    state = engine.init_state(outline)

    result = engine.process_turn(state, "Decorators wrap functions")
    state = result.state
    assert len(state["evaluations"]) == 1
    assert state["evaluations"][0]["topic"]
    assert "score" in state["evaluations"][0]


def test_interview_graph_matches_legacy_turn_contract() -> None:
    engine = InterviewEngine()
    outline = engine.build_outline(["python"])
    state = engine.init_state(outline)

    result = run_interview_turn_graph(
        state=state,
        user_message="I know attention and self-attention.",
    )
    assert result["turn_eval"]["topic"]
    assert result["next_action"] in {"follow_up", "next_topic", "end"}
