from __future__ import annotations

from typing import Any

from app.services.interview_engine import InterviewEngine
from app.services.report_service import ReportService
from app.services.resume_parser import ResumeParser
from app.workflows.mission_guards import enforce_turn_growth_feedback, validate_report_growth_artifacts

_engine = InterviewEngine()
_report_service = ReportService()


def build_outline_step(
    *,
    skills: list[str],
    target_role: str,
    model: str | None = None,
    profile: dict[str, Any] | None = None,
    resume_text: str | None = None,
) -> dict[str, Any]:
    outline = _engine.build_outline(
        skills=skills,
        target_role=target_role,
        model=model,
        profile=profile,
        resume_text=resume_text,
    )
    return {"outline": outline.model_dump()}


def generate_question_step(
    *,
    state: dict[str, Any],
    profile: dict[str, Any] | None = None,
    resume_text: str | None = None,
) -> dict[str, Any]:
    question = _engine.first_question(state, profile=profile, resume_text=resume_text)
    return {"question": question}


def evaluate_answer_step(
    *,
    state: dict[str, Any],
    user_message: str,
    conversation_context: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    result = _engine.process_turn(state, user_message, conversation_context=conversation_context)
    guarded_eval = enforce_turn_growth_feedback(result.turn_eval.model_dump())
    return {
        "question": result.question,
        "turn_eval": guarded_eval,
        "next_action": result.next_action,
        "state": result.state,
        "reasoning": result.reasoning,
        "reference_answer": result.reference_answer,
        "score_rationale": result.score_rationale,
    }


def advance_state_step(*, state: dict[str, Any]) -> dict[str, Any]:
    return {"state": state}


def aggregate_report_step(
    *,
    evaluations: list[dict[str, Any]],
    expected_salary: str,
    target_role: str,
) -> dict[str, Any]:
    report_payload = _report_service.build_report(
        evaluations=evaluations,
        expected_salary=expected_salary,
        target_role=target_role,
    )
    if not validate_report_growth_artifacts(report_payload):
        plan = report_payload.setdefault("action_plan_30d", {})
        plan.setdefault("overall", [])
        if not plan["overall"]:
            plan["overall"] = ["围绕低分维度制定 30 天训练计划，并每周复盘一次改进结果。"]
        report_payload.setdefault("risks", [])
        if not report_payload["risks"]:
            report_payload["risks"] = ["缺少可验证的成长风险条目，建议补充关键能力缺口。"]
    return {"report_payload": report_payload}


def extract_resume_text_step(*, content: bytes, model: str | None = None) -> dict[str, Any]:
    resume_text = ResumeParser.extract_text(content)
    profile = ResumeParser.parse_profile(resume_text, model=model)
    return {
        "resume_text": resume_text,
        "parsed_profile": profile.model_dump(),
    }
