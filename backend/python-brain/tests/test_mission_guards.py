from app.workflows.mission_guards import (
    enforce_turn_growth_feedback,
    validate_growth_feedback,
    validate_report_growth_artifacts,
)


def test_validate_growth_feedback_rejects_empty_actionable_feedback() -> None:
    assert validate_growth_feedback({"gaps": [], "reference_answer": ""}) is False


def test_enforce_turn_growth_feedback_fills_required_fields() -> None:
    payload = enforce_turn_growth_feedback({"topic": "Transformer 原理", "evidence": [], "gaps": []})
    assert payload["evidence"]
    assert payload["gaps"]
    assert payload["reference_answer"]


def test_validate_report_growth_artifacts() -> None:
    ok = validate_report_growth_artifacts(
        {
            "risks": ["RAG 检索关键点缺失: rerank tradeoff"],
            "action_plan_30d": {"overall": ["每周做一次检索链路复盘并量化召回率变化"]},
        }
    )
    assert ok is True
