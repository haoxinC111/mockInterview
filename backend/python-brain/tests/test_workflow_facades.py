from app.services.interview_engine import InterviewEngine
from app.workflows.facades import (
    advance_state_step,
    aggregate_report_step,
    build_outline_step,
    evaluate_answer_step,
    generate_question_step,
)


def test_build_outline_step_returns_outline_payload() -> None:
    payload = build_outline_step(skills=["python"], target_role="Agent Engineer")
    assert "outline" in payload
    assert payload["outline"]["modules"]


def test_generate_and_evaluate_steps_return_expected_shape() -> None:
    engine = InterviewEngine()
    outline = engine.build_outline(["python"])
    state = engine.init_state(outline)

    question_payload = generate_question_step(state=state)
    assert "question" in question_payload

    eval_payload = evaluate_answer_step(
        state=state,
        user_message="I know attention and self-attention details.",
    )
    assert "question" in eval_payload
    assert "turn_eval" in eval_payload
    assert "next_action" in eval_payload
    assert "state" in eval_payload

    state_payload = advance_state_step(state=eval_payload["state"])
    assert "state" in state_payload


def test_aggregate_report_step_returns_report_payload() -> None:
    payload = aggregate_report_step(
        evaluations=[
            {
                "topic": "Transformer 原理",
                "score": 6,
                "evidence": ["covers basic mechanism"],
                "gaps": ["missing deeper tradeoff"],
                "primary_dimension": "technical_depth",
                "dimension_scores": {"technical_depth": 6},
            }
        ],
        expected_salary="20k-30k",
        target_role="Agent Engineer",
    )
    assert "report_payload" in payload
    assert "overall_score" in payload["report_payload"]
