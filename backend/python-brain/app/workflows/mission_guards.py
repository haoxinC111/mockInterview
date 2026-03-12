from __future__ import annotations

from typing import Any

_GENERIC_PHRASES = (
    "继续加油",
    "总体不错",
    "good job",
    "well done",
)


def _has_actionable_items(items: list[str]) -> bool:
    for item in items:
        text = (item or "").strip()
        if len(text) >= 8 and not any(p in text.lower() for p in _GENERIC_PHRASES):
            return True
    return False


def validate_growth_feedback(payload: dict[str, Any]) -> bool:
    evidence = [str(x) for x in (payload.get("evidence") or [])]
    gaps = [str(x) for x in (payload.get("gaps") or [])]
    reference_answer = str(payload.get("reference_answer") or "").strip()
    return _has_actionable_items(evidence) and _has_actionable_items(gaps) and bool(reference_answer)


def enforce_turn_growth_feedback(payload: dict[str, Any]) -> dict[str, Any]:
    fixed = dict(payload)
    evidence = [str(x) for x in (fixed.get("evidence") or [])]
    gaps = [str(x) for x in (fixed.get("gaps") or [])]

    if not _has_actionable_items(evidence):
        fixed["evidence"] = ["回答体现了部分基础理解，但需要结合项目细节证明能力。"]
    if not _has_actionable_items(gaps):
        fixed["gaps"] = ["缺少可落地的实现细节，建议补充方案取舍与线上指标变化。"]
    if not str(fixed.get("reference_answer") or "").strip():
        topic = str(fixed.get("topic") or "当前问题")
        fixed["reference_answer"] = f"围绕{topic}补充：定义、核心原理、工程取舍、线上实践与复盘。"
    return fixed


def validate_report_growth_artifacts(report_payload: dict[str, Any]) -> bool:
    risks = [str(x) for x in (report_payload.get("risks") or [])]
    action_plan = report_payload.get("action_plan_30d") or {}
    overall_plan = [str(x) for x in (action_plan.get("overall") or [])]
    return _has_actionable_items(risks) and _has_actionable_items(overall_plan)
