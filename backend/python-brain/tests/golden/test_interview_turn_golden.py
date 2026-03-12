from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.config import settings
from app.services.interview_engine import InterviewEngine
from app.workflows.graphs.interview_graph import run_interview_turn_graph


@pytest.fixture(autouse=True)
def _disable_llm(monkeypatch):
    monkeypatch.setattr(settings, "interview_turn_use_llm", False)
    monkeypatch.setattr(settings, "interview_engine_use_llm", False)


def _load_cases() -> list[dict]:
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "golden_sessions.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    cases = payload.get("turn_cases", [])
    assert cases, "golden turn cases missing"
    return cases


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["name"])
def test_turn_golden_cases(case: dict) -> None:
    engine = InterviewEngine()
    outline = engine.build_outline(case["skills"])
    state = engine.init_state(outline)

    result = engine.process_turn(state, case["answer"])
    expected = case["expected"]

    assert result.turn_eval.topic == expected["topic"]
    assert result.next_action == expected["next_action"]
    assert result.turn_eval.decision == expected["decision"]
    assert expected["score_min"] <= result.turn_eval.score <= expected["score_max"]

    assert isinstance(result.turn_eval.evidence, list)
    assert isinstance(result.turn_eval.gaps, list)
    assert isinstance(result.turn_eval.dimension_scores, dict)
    assert result.turn_eval.primary_dimension
    assert result.turn_eval.reference_answer
    assert result.turn_eval.score_rationale


def test_graph_turn_golden_contract() -> None:
    engine = InterviewEngine()
    outline = engine.build_outline(["python", "langgraph"])
    state = engine.init_state(outline)
    result = run_interview_turn_graph(
        state=state,
        user_message="I can explain attention and position encoding details.",
    )
    assert result["turn_eval"]["topic"]
    assert result["next_action"] in {"follow_up", "next_topic", "end"}
