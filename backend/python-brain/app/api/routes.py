from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse
from sqlmodel import Session, select

from app.core.config import PROJECT_MISSION, settings
from app.core.database import get_session
from app.core.logging import log_event, log_summary, log_workflow_diff
from app.core.request_context import get_request_id
from app.models.db import InterviewMessage, InterviewReport, InterviewSession, Resume, ResumeParseCache
from app.models.schemas import (
    CandidateProfile,
    FinishInterviewResponse,
    ReportResponse,
    ResumeInterviewResponse,
    ResumeUploadResponse,
    SendMessageRequest,
    SendMessageResponse,
    StartInterviewRequest,
    StartInterviewResponse,
    TurnEvaluation,
)
from app.services.interview_engine import InterviewEngine, LLMEvaluationError
from app.services.report_service import ReportService
from app.services.resume_parser import ResumeParser
from app.workflows.diffing import diff_resume_results
from app.workflows.executors import execute_interview_turn, execute_report_generation
from app.workflows.graphs.resume_graph import run_resume_graph
from app.workflows.graphs.report_graph import build_report_via_graph
from app.workflows.runtime import choose_workflow_runtime_from_settings

router = APIRouter(prefix="/api/v1", tags=["interview"])
engine = InterviewEngine()
report_service = ReportService()


@router.get("/mission")
def get_mission():
    """Return the project mission statement (立意)."""
    return {
        "mission": PROJECT_MISSION,
        "title": "InterviewSim 立意",
        "subtitle": "本系统的一切设计，服务于一个核心目标",
        "core": "帮助候选人成长",
        "principles": [
            "每一个提问引导候选人暴露真实能力边界",
            "每一次评估指出具体可改进的方向",
            "每一份反馈让候选人比面试前更清楚该学什么、怎么练",
        ],
    }


def _clip(text: str, max_len: int = 1200) -> str:
    return text[:max_len]


def _assess_resume_readiness(raw_text: str, profile: CandidateProfile, filename: str) -> dict[str, Any]:
    score = 0
    warnings: list[str] = []
    if len(raw_text.strip()) >= 20:
        score += 1
    else:
        warnings.append("resume_text_too_short")
    if len(profile.skills) >= 2:
        score += 1
    elif profile.skills:
        warnings.append("skills_signal_too_thin")
    else:
        warnings.append("missing_skills")
    if profile.projects or profile.years_exp:
        score += 1
    else:
        warnings.append("missing_project_or_experience_signal")
    readiness = "ready" if score >= 2 else "needs_more_input"
    guidance = []
    if readiness != "ready":
        guidance.append("请补充更完整的简历内容，至少包含技能栈、项目经历或工作年限，再开始正式面试。")
    return {
        "score": score,
        "readiness": readiness,
        "warnings": warnings + guidance,
    }


def _collect_llm_events(request_ids: set[str]) -> list[dict]:
    if not request_ids:
        return []
    log_dir = Path(settings.log_dir)
    if not log_dir.is_absolute():
        log_dir = Path(__file__).resolve().parents[2] / log_dir
    summary_path = log_dir / settings.summary_log_file
    if not summary_path.exists():
        return []

    events: list[dict] = []
    try:
        with summary_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue
                try:
                    payload = json.loads(line)
                except Exception:
                    continue
                rid = str(payload.get("request_id", ""))
                event_name = str(payload.get("event", ""))
                if rid in request_ids and event_name.startswith("llm."):
                    events.append(payload)
    except Exception as exc:
        log_event("session.workflow.llm_events.read_failed", error=str(exc))
    return events[-200:]


@router.post("/resumes", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    force_reparse: bool = Query(default=False),
    db: Session = Depends(get_session),
):
    log_event("resume.upload.received", filename=file.filename or "unknown")
    content = await file.read()
    if not content:
        log_event("resume.upload.rejected", reason="empty_file")
        raise HTTPException(status_code=400, detail="empty file")

    filename = file.filename or "resume.pdf"
    file_hash = hashlib.sha256(content).hexdigest()
    cache = db.exec(
        select(ResumeParseCache).where(
            ResumeParseCache.filename == filename,
            ResumeParseCache.file_hash == file_hash,
        )
    ).first()

    if cache and not force_reparse:
        resume = db.get(Resume, cache.resume_id) if cache.resume_id else None
        if not resume:
            resume = Resume(filename=filename, raw_text=cache.raw_text, profile_json=cache.profile_json)
            db.add(resume)
            db.commit()
            db.refresh(resume)
            cache.resume_id = resume.id

        cache.hit_count += 1
        cache.last_used_at = datetime.utcnow()
        cache.updated_at = datetime.utcnow()
        db.add(cache)
        db.commit()

        profile = CandidateProfile.model_validate(cache.profile_json)
        quality = cache.profile_json.get("_quality") or _assess_resume_readiness(cache.raw_text, profile, filename)
        log_event(
            "resume.upload.cache_hit",
            filename=filename,
            file_hash=file_hash,
            resume_id=resume.id,
            cache_id=cache.id,
            cache_hit_count=cache.hit_count,
        )
        log_summary(
            "resume.cache.hit",
            filename=filename,
            file_hash=file_hash,
            resume_id=resume.id,
            cache_id=cache.id,
            cache_hit_count=cache.hit_count,
        )
        return ResumeUploadResponse(
            resume_id=resume.id,
            parsed_profile=profile,
            warnings=["cache_hit: reused previous parsed profile", *quality["warnings"]],
            cache_hit=True,
            cache_id=cache.id,
            quality_score=quality["score"],
            readiness=quality["readiness"],
        )

    runtime = choose_workflow_runtime_from_settings().resume
    if runtime == "langgraph":
        graph_payload = run_resume_graph(content=content, model=settings.llm_model_default)
        raw_text = graph_payload["resume_text"]
        profile = CandidateProfile.model_validate(graph_payload["parsed_profile"])
        log_event(
            "resume.upload.runtime",
            runtime=runtime,
            extraction_branch=graph_payload.get("extraction_branch"),
        )
    elif runtime == "shadow":
        graph_payload = run_resume_graph(content=content, model=settings.llm_model_default)
        raw_text = ResumeParser.extract_text(content)
        profile = ResumeParser.parse_profile(raw_text, model=settings.llm_model_default)
        log_workflow_diff(
            "resume",
            diff_resume_results(
                {"resume_text": raw_text, "parsed_profile": profile.model_dump()},
                {
                    "resume_text": graph_payload.get("resume_text", ""),
                    "parsed_profile": graph_payload.get("parsed_profile", {}),
                },
            ),
            runtime=runtime,
            extraction_branch=graph_payload.get("extraction_branch"),
        )
    else:
        raw_text = ResumeParser.extract_text(content)
        profile = ResumeParser.parse_profile(raw_text, model=settings.llm_model_default)
    quality = _assess_resume_readiness(raw_text, profile, filename)
    profile_payload = profile.model_dump()
    profile_payload["_quality"] = quality
    resume = Resume(filename=filename, raw_text=raw_text, profile_json=profile_payload)
    db.add(resume)
    db.commit()
    db.refresh(resume)

    if cache:
        cache.resume_id = resume.id
        cache.raw_text = raw_text
        cache.profile_json = profile_payload
        cache.updated_at = datetime.utcnow()
        cache.last_used_at = datetime.utcnow()
        db.add(cache)
        db.commit()
        db.refresh(cache)
        log_event("resume.upload.cache_overwrite", cache_id=cache.id, filename=filename, file_hash=file_hash)
    else:
        cache = ResumeParseCache(
            filename=filename,
            file_hash=file_hash,
            resume_id=resume.id,
            raw_text=raw_text,
            profile_json=profile_payload,
            hit_count=0,
        )
        db.add(cache)
        db.commit()
        db.refresh(cache)
    warnings = [] if raw_text else ["failed to parse text from file"]
    warnings.extend(quality["warnings"])
    log_event(
        "resume.upload.parsed",
        runtime=runtime,
        resume_id=resume.id,
        filename=resume.filename,
        file_hash=file_hash,
        cache_id=cache.id,
        text_len=len(raw_text),
        raw_text_preview=_clip(raw_text),
        parsed_profile=profile_payload,
        skills_count=len(profile.skills),
        projects_count=len(profile.projects),
        quality_score=quality["score"],
        readiness=quality["readiness"],
    )
    if force_reparse and warnings == []:
        warnings = ["force_reparse: parsed fresh result and refreshed cache"]
    return ResumeUploadResponse(
        resume_id=resume.id,
        parsed_profile=profile,
        warnings=warnings,
        cache_hit=False,
        cache_id=cache.id if cache else None,
        quality_score=quality["score"],
        readiness=quality["readiness"],
    )


@router.delete("/resumes/cache")
def delete_resume_cache(filename: str = Query(...), db: Session = Depends(get_session)):
    records = db.exec(select(ResumeParseCache).where(ResumeParseCache.filename == filename)).all()
    if not records:
        return {"deleted": 0, "filename": filename}

    count = 0
    for rec in records:
        db.delete(rec)
        count += 1
    db.commit()
    log_event("resume.cache.deleted", filename=filename, deleted=count)
    log_summary("resume.cache.deleted", filename=filename, deleted=count)
    return {"deleted": count, "filename": filename}


@router.post("/interviews", response_model=StartInterviewResponse)
def start_interview(req: StartInterviewRequest, db: Session = Depends(get_session)):
    log_event(
        "interview.start.requested",
        resume_id=req.resume_id,
        target_role=req.target_role,
        expected_salary=req.expected_salary,
        requested_model=req.model,
        runtime_model_default=settings.llm_model_default,
        use_llm_resume_parser=settings.resume_parser_use_llm,
        use_llm_outline=settings.interview_engine_use_llm,
        use_llm_turn=settings.interview_turn_use_llm,
    )
    log_summary(
        "interview.start.requested",
        resume_id=req.resume_id,
        target_role=req.target_role,
        expected_salary=req.expected_salary,
        selected_model=req.model or settings.llm_model_default,
    )
    resume = db.get(Resume, req.resume_id)
    if not resume:
        log_event("interview.start.failed", reason="resume_not_found", resume_id=req.resume_id)
        raise HTTPException(status_code=404, detail="resume not found")

    selected_model = req.model or settings.llm_model_default
    profile = CandidateProfile.model_validate(resume.profile_json)
    quality = resume.profile_json.get("_quality") or _assess_resume_readiness(resume.raw_text, profile, resume.filename)
    if quality.get("readiness") != "ready":
        log_event("interview.start.failed", reason="resume_not_ready", resume_id=req.resume_id, quality_score=quality.get("score"))
        raise HTTPException(status_code=400, detail="resume content is too thin for a growth-oriented interview; please add skills, project details, or experience first")
    profile_skills = resume.profile_json.get("skills", [])
    outline = engine.build_outline(
        profile_skills,
        target_role=req.target_role,
        model=selected_model,
        profile=resume.profile_json,
        resume_text=resume.raw_text,
    )
    state = engine.init_state(outline, model=selected_model, target_role=req.target_role, expected_salary=req.expected_salary, city=req.city, answer_style=req.answer_style)
    state["workflow_request_ids"] = [get_request_id()]
    first_question = engine.first_question(
        state,
        profile=resume.profile_json,
        resume_text=resume.raw_text,
    )
    session = InterviewSession(
        resume_id=req.resume_id,
        target_role=req.target_role,
        expected_salary=req.expected_salary,
        city=req.city,
        model=selected_model,
        answer_style=req.answer_style,
        state_json=state,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    db.add(
        InterviewMessage(
            session_id=session.id,
            role="assistant",
            content=first_question,
            metadata_json={"kind": "question", "request_id": get_request_id()},
        )
    )
    db.commit()

    summary = [m.module_name for m in outline.modules]
    log_event(
        "interview.start.created",
        session_id=session.id,
        resume_id=req.resume_id,
        selected_model=selected_model,
        outline_modules=summary,
        first_question=first_question,
    )
    log_summary(
        "interview.start.created",
        session_id=session.id,
        selected_model=selected_model,
        outline_modules=summary,
        first_question=first_question,
    )
    return StartInterviewResponse(session_id=session.id, first_question=first_question, outline_summary=summary)


@router.post("/interviews/{session_id}/resume", response_model=ResumeInterviewResponse)
def resume_interview(session_id: int, db: Session = Depends(get_session)):
    """Resume an active interview session (断点续作).

    Loads the persisted state and message history so the frontend can
    reconstruct the chat UI and continue where the candidate left off.
    Only sessions with status == 'active' can be resumed.
    """
    log_event("interview.resume.requested", session_id=session_id)
    session = db.get(InterviewSession, session_id)
    if not session:
        log_event("interview.resume.failed", session_id=session_id, reason="session_not_found")
        raise HTTPException(status_code=404, detail="session not found")
    if session.status != "active":
        log_event("interview.resume.failed", session_id=session_id, reason="session_not_active", status=session.status)
        raise HTTPException(status_code=400, detail=f"session is {session.status}, only active sessions can be resumed")

    messages = db.exec(
        select(InterviewMessage).where(InterviewMessage.session_id == session_id).order_by(InterviewMessage.id)
    ).all()

    state = session.state_json or {}
    outline_raw = state.get("outline", {})
    outline_summary = [m.get("module_name", "") for m in outline_raw.get("modules", [])]

    log_event(
        "interview.resume.completed",
        session_id=session_id,
        message_count=len(messages),
        turn_count=state.get("turn_count", 0),
    )
    log_summary("interview.resume", session_id=session_id, message_count=len(messages))

    return ResumeInterviewResponse(
        session_id=session.id,
        status=session.status,
        target_role=session.target_role,
        expected_salary=session.expected_salary,
        city=session.city,
        model=session.model,
        answer_style=session.answer_style,
        outline_summary=outline_summary,
        messages=[
            {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at}
            for m in messages
        ],
        turn_count=state.get("turn_count", 0),
    )


@router.post("/interviews/{session_id}/messages", response_model=SendMessageResponse)
def send_message(session_id: int, req: SendMessageRequest, db: Session = Depends(get_session)):
    log_event(
        "interview.turn.received",
        session_id=session_id,
        user_message_len=len(req.user_message),
        user_message=req.user_message,
        has_client_turn_id=bool(req.client_turn_id),
    )
    log_summary("human.input", session_id=session_id, user_message=req.user_message)
    session = db.get(InterviewSession, session_id)
    if not session:
        log_event("interview.turn.failed", session_id=session_id, reason="session_not_found")
        raise HTTPException(status_code=404, detail="session not found")
    if session.status != "active":
        log_event("interview.turn.failed", session_id=session_id, reason="session_not_active", status=session.status)
        raise HTTPException(status_code=400, detail="session is not active")

    req_id = get_request_id()
    db.add(
        InterviewMessage(
            session_id=session.id,
            role="user",
            content=req.user_message,
            metadata_json={"client_turn_id": req.client_turn_id, "request_id": req_id},
        )
    )

    state_input = copy.deepcopy(session.state_json)
    context_messages = db.exec(
        select(InterviewMessage).where(InterviewMessage.session_id == session_id).order_by(InterviewMessage.id)
    ).all()
    conversation_context = [
        {"role": m.role, "content": m.content}
        for m in context_messages[-10:]
    ]
    try:
        result = execute_interview_turn(
            engine=engine,
            state=state_input,
            user_message=req.user_message,
            conversation_context=conversation_context,
        )
    except LLMEvaluationError as exc:
        # P0: Surface LLM failure as 503 — frontend shows retry UI.
        # The user message is already persisted, so the context is preserved.
        db.commit()
        log_event("interview.turn.llm_unavailable", session_id=session_id, error=str(exc))
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )
    # Re-assign a deep copy to ensure JSON field mutation is detected and persisted.
    session.state_json = copy.deepcopy(result["state"])
    workflow_request_ids = session.state_json.get("workflow_request_ids", [])
    if req_id not in workflow_request_ids:
        workflow_request_ids.append(req_id)
    session.state_json["workflow_request_ids"] = workflow_request_ids[-200:]
    session.updated_at = datetime.utcnow()
    if result["next_action"] == "end":
        session.status = "finished"

    db.add(
        InterviewMessage(
            session_id=session.id,
            role="assistant",
            content=result["question"],
            metadata_json={"next_action": result["next_action"], "request_id": req_id},
        )
    )
    db.add(session)
    db.commit()
    log_event(
        "interview.turn.completed",
        session_id=session.id,
        runtime=result.get("runtime"),
        assistant_message=result["question"],
        turn_eval=result["turn_eval"],
        score=result["turn_eval"]["score"],
        topic=result["turn_eval"]["topic"],
        decision=result["turn_eval"]["decision"],
        next_action=result["next_action"],
        turn_count=session.state_json.get("turn_count"),
        module_idx=session.state_json.get("module_idx"),
        topic_idx=session.state_json.get("topic_idx"),
        finished=session.state_json.get("finished"),
    )
    log_summary(
        "assistant.output",
        session_id=session.id,
        assistant_message=result["question"],
        decision=result["turn_eval"]["decision"],
        score=result["turn_eval"]["score"],
    )

    # reasoning, reference_answer, score_rationale are now set directly
    # in TurnEvaluation during process_turn() — no extra attachment needed.

    return SendMessageResponse(
        assistant_message=result["question"],
        turn_eval=TurnEvaluation.model_validate(result["turn_eval"]),
        next_action=result["next_action"],  # type: ignore[arg-type]
        expected_salary=session.expected_salary,
    )


@router.post("/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    context: str = Form(default=""),
):
    """Transcribe audio to text using local Whisper model.

    The optional `context` field (e.g. the current interview question)
    is used as Whisper initial_prompt for better Chinese-English recognition
    and optionally for LLM-based post-processing.
    """
    if not settings.stt_enabled:
        raise HTTPException(status_code=503, detail="STT 未启用，请在 .env 中设置 STT_ENABLED=true")
    try:
        from app.services.stt_service import transcribe_audio_async
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="空音频文件")

    try:
        text = await transcribe_audio_async(
            audio_bytes,
            filename=audio.filename or "audio.webm",
            context=context or None,
        )
    except Exception as exc:
        log_event("stt.error", error=str(exc))
        raise HTTPException(status_code=500, detail=f"语音识别失败: {exc}")

    return {"text": text}


@router.post("/interviews/{session_id}/finish", response_model=FinishInterviewResponse)
def finish_interview(session_id: int, db: Session = Depends(get_session)):
    log_event("interview.finish.requested", session_id=session_id)
    session = db.get(InterviewSession, session_id)
    if not session:
        log_event("interview.finish.failed", session_id=session_id, reason="session_not_found")
        raise HTTPException(status_code=404, detail="session not found")

    evaluations = session.state_json.get("evaluations", [])
    report_payload, runtime = execute_report_generation(
        evaluations=evaluations,
        expected_salary=session.expected_salary,
        target_role=session.target_role,
        legacy_builder=report_service.build_report,
        graph_builder=build_report_via_graph,
    )
    report = InterviewReport(session_id=session.id, report_json=report_payload)
    session.status = "finished"
    session.updated_at = datetime.utcnow()

    db.add(report)
    db.add(session)
    db.commit()
    db.refresh(report)
    log_event(
        "interview.finish.completed",
        session_id=session.id,
        report_id=report.id,
        report_runtime=runtime,
        evaluations_count=len(evaluations),
        overall_score=report_payload.get("overall_score"),
        report_payload=report_payload,
    )

    return FinishInterviewResponse(report_id=report.id, report_payload=report_payload)


@router.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(report_id: int, db: Session = Depends(get_session)):
    log_event("report.get.requested", report_id=report_id)
    report = db.get(InterviewReport, report_id)
    if not report:
        log_event("report.get.failed", report_id=report_id, reason="report_not_found")
        raise HTTPException(status_code=404, detail="report not found")
    log_event("report.get.completed", report_id=report.id, session_id=report.session_id)

    return ReportResponse(
        report_id=report.id,
        session_id=report.session_id,
        created_at=report.created_at,
        report_payload=report.report_json,
    )


@router.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: int, db: Session = Depends(get_session)):
    log_event("session.messages.requested", session_id=session_id)
    session = db.get(InterviewSession, session_id)
    if not session:
        log_event("session.messages.failed", session_id=session_id, reason="session_not_found")
        raise HTTPException(status_code=404, detail="session not found")

    messages = db.exec(
        select(InterviewMessage).where(InterviewMessage.session_id == session_id).order_by(InterviewMessage.id)
    ).all()
    log_event("session.messages.completed", session_id=session_id, count=len(messages), status=session.status)
    return {
        "session_id": session_id,
        "status": session.status,
        "messages": [
            {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in messages
        ],
    }


@router.get("/sessions/{session_id}/trace")
def get_session_trace(session_id: int, db: Session = Depends(get_session)):
    log_event("session.trace.requested", session_id=session_id)
    session = db.get(InterviewSession, session_id)
    if not session:
        log_event("session.trace.failed", session_id=session_id, reason="session_not_found")
        raise HTTPException(status_code=404, detail="session not found")

    messages = db.exec(
        select(InterviewMessage).where(InterviewMessage.session_id == session_id).order_by(InterviewMessage.id)
    ).all()
    decision_traces = session.state_json.get("decision_traces", [])
    evaluations = session.state_json.get("evaluations", [])

    turns = []
    turn_no = 0
    pending_user = None
    for msg in messages:
        if msg.role == "user":
            pending_user = msg.content
            continue
        if msg.role == "assistant" and pending_user is not None:
            turn_no += 1
            trace = decision_traces[turn_no - 1] if len(decision_traces) >= turn_no else {}
            eval_item = evaluations[turn_no - 1] if len(evaluations) >= turn_no else {}
            turns.append(
                {
                    "turn": turn_no,
                    "user_input": pending_user,
                    "assistant_output": msg.content,
                    "topic": trace.get("topic") or eval_item.get("topic"),
                    "score": trace.get("score", eval_item.get("score")),
                    "decision": trace.get("decision", eval_item.get("decision")),
                    "decision_source": trace.get("decision_source"),
                    "decision_reason": trace.get("decision_reason"),
                    "feedback": trace.get("feedback"),
                    "llm_recommend_action": trace.get("llm_recommend_action"),
                    "llm_evaluate_failed": trace.get("llm_evaluate_failed", False),
                    "llm_followup_failed": trace.get("llm_followup_failed", False),
                }
            )
            pending_user = None

    log_event(
        "session.trace.completed",
        session_id=session_id,
        turns=len(turns),
        decisions=len(decision_traces),
        status=session.status,
    )
    return {
        "session_id": session_id,
        "status": session.status,
        "model": session.model,
        "target_role": session.target_role,
        "turns": turns,
    }


@router.get("/sessions")
def list_sessions(limit: int = 20, db: Session = Depends(get_session)):
    max_limit = max(1, min(limit, 100))
    sessions = db.exec(select(InterviewSession).order_by(InterviewSession.id.desc()).limit(max_limit)).all()
    return {
        "sessions": [
            {
                "session_id": s.id,
                "status": s.status,
                "target_role": s.target_role,
                "model": s.model,
                "answer_style": s.answer_style,
                "city": s.city,
                "turn_count": (s.state_json or {}).get("turn_count", 0),
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in sessions
        ]
    }


@router.get("/sessions/{session_id}/workflow")
def get_session_workflow(session_id: int, db: Session = Depends(get_session)):
    log_event("session.workflow.requested", session_id=session_id)
    session = db.get(InterviewSession, session_id)
    if not session:
        log_event("session.workflow.failed", session_id=session_id, reason="session_not_found")
        raise HTTPException(status_code=404, detail="session not found")

    messages = db.exec(
        select(InterviewMessage).where(InterviewMessage.session_id == session_id).order_by(InterviewMessage.id)
    ).all()

    state = session.state_json or {}
    workflow = {
        "session_id": session.id,
        "status": session.status,
        "target_role": session.target_role,
        "model": session.model,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "outline": state.get("outline", {}),
        "turn_count": state.get("turn_count"),
        "max_turns": state.get("max_turns"),
        "module_idx": state.get("module_idx"),
        "topic_idx": state.get("topic_idx"),
        "depth": state.get("depth"),
        "decision_traces": state.get("decision_traces", []),
        "evaluations": state.get("evaluations", []),
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "metadata": m.metadata_json,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }
    req_ids = {str(x) for x in state.get("workflow_request_ids", []) if x}
    for m in workflow["messages"]:
        rid = str((m.get("metadata") or {}).get("request_id") or "")
        if rid:
            req_ids.add(rid)
    workflow["llm_events"] = _collect_llm_events(req_ids)
    latest_report = db.exec(
        select(InterviewReport).where(InterviewReport.session_id == session_id).order_by(InterviewReport.id.desc())
    ).first()
    workflow["latest_report"] = (
        {
            "report_id": latest_report.id,
            "created_at": latest_report.created_at.isoformat(),
            "report_payload": latest_report.report_json,
        }
        if latest_report
        else None
    )
    log_event(
        "session.workflow.completed",
        session_id=session_id,
        message_count=len(workflow["messages"]),
        decisions=len(workflow["decision_traces"]),
        evaluations=len(workflow["evaluations"]),
        llm_events=len(workflow["llm_events"]),
    )
    return workflow


@router.get("/sessions/{session_id}/latest-report")
def get_session_latest_report(session_id: int, db: Session = Depends(get_session)):
    log_event("session.latest_report.requested", session_id=session_id)
    session = db.get(InterviewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    report = db.exec(
        select(InterviewReport).where(InterviewReport.session_id == session_id).order_by(InterviewReport.id.desc())
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="report not found")
    return {
        "session_id": session_id,
        "report_id": report.id,
        "created_at": report.created_at.isoformat(),
        "report_payload": report.report_json,
    }


@router.get("/sessions/{session_id}/trace/markdown", response_class=PlainTextResponse)
def get_session_trace_markdown(session_id: int, db: Session = Depends(get_session)):
    session = db.get(InterviewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")

    messages = db.exec(
        select(InterviewMessage).where(InterviewMessage.session_id == session_id).order_by(InterviewMessage.id)
    ).all()
    state = session.state_json or {}
    decision_traces = state.get("decision_traces", [])
    evaluations = state.get("evaluations", [])

    lines = []
    lines.append(f"# Session {session.id} Workflow Trace")
    lines.append("")
    lines.append(f"- Status: {session.status}")
    lines.append(f"- Role: {session.target_role}")
    lines.append(f"- Model: {session.model}")
    lines.append(f"- Created: {session.created_at.isoformat()}")
    lines.append(f"- Updated: {session.updated_at.isoformat()}")
    lines.append("")
    lines.append("## Outline")
    lines.append("```json")
    lines.append(str(state.get("outline", {})))
    lines.append("```")
    lines.append("")
    lines.append("## Turn Timeline")

    turn_no = 0
    pending_user = None
    for msg in messages:
        if msg.role == "user":
            pending_user = msg
            continue
        if msg.role == "assistant" and pending_user is not None:
            turn_no += 1
            trace = decision_traces[turn_no - 1] if len(decision_traces) >= turn_no else {}
            evaluation = evaluations[turn_no - 1] if len(evaluations) >= turn_no else {}
            lines.append(f"### Turn {turn_no}")
            lines.append(f"- Human: {pending_user.content}")
            lines.append(f"- Assistant: {msg.content}")
            lines.append(f"- Topic: {trace.get('topic') or evaluation.get('topic')}")
            lines.append(f"- Score: {trace.get('score', evaluation.get('score'))}")
            lines.append(f"- Decision: {trace.get('decision', evaluation.get('decision'))}")
            lines.append(f"- Decision Source: {trace.get('decision_source')}")
            lines.append(f"- Decision Reason: {trace.get('decision_reason')}")
            lines.append(f"- Feedback: {trace.get('feedback')}")
            lines.append(f"- LLM Recommend Action: {trace.get('llm_recommend_action')}")
            lines.append(f"- LLM Evaluate Failed: {trace.get('llm_evaluate_failed')}")
            lines.append(f"- LLM Followup Failed: {trace.get('llm_followup_failed')}")
            lines.append("")
            pending_user = None

    return "\n".join(lines)
