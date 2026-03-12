from __future__ import annotations

from io import BytesIO
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pypdf import PdfReader

from app.core.config import settings
from app.core.logging import log_event
from app.services.resume_parser import ResumeParser


class ResumeGraphState(TypedDict, total=False):
    content: bytes
    model: str
    ocr_text: str
    pdf_text: str
    resume_text: str
    parsed_profile: dict[str, Any]
    extraction_branch: str
    ocr_error: str


def _ocr_extract(state: ResumeGraphState) -> ResumeGraphState:
    content = state.get("content", b"")
    if not settings.resume_ocr_enabled:
        return {"ocr_text": "", "extraction_branch": "ocr_disabled"}
    try:
        text = ResumeParser._extract_text_with_ocr(content)
    except Exception as exc:
        return {"ocr_text": "", "ocr_error": str(exc), "extraction_branch": "ocr_failed"}
    if text and len(text.strip()) > 50:
        return {"ocr_text": text, "extraction_branch": "ocr"}
    return {"ocr_text": "", "extraction_branch": "ocr_insufficient"}


def _pdf_extract(state: ResumeGraphState) -> ResumeGraphState:
    if state.get("ocr_text", "").strip():
        return {"pdf_text": "", "extraction_branch": "ocr"}
    content = state.get("content", b"")
    try:
        reader = PdfReader(BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = ResumeParser._normalize_text("\n".join(pages))
    except Exception:
        text = ""
    if text and len(text.strip()) > 50:
        return {"pdf_text": text, "extraction_branch": "pdf"}
    return {"pdf_text": "", "extraction_branch": "raw_decode"}


def _branch_after_ocr(state: ResumeGraphState) -> str:
    return "parse_profile" if state.get("ocr_text", "").strip() else "pdf_extract"


def _branch_after_pdf(state: ResumeGraphState) -> str:
    return "parse_profile" if state.get("pdf_text", "").strip() else "raw_decode"


def _raw_decode(state: ResumeGraphState) -> ResumeGraphState:
    content = state.get("content", b"")
    text = ResumeParser._normalize_text(content.decode("utf-8", errors="ignore"))
    return {"resume_text": text, "extraction_branch": "raw_decode"}


def _parse_profile(state: ResumeGraphState) -> ResumeGraphState:
    resume_text = state.get("ocr_text") or state.get("pdf_text") or state.get("resume_text", "")
    profile = ResumeParser.parse_profile(resume_text, model=state.get("model"))
    return {
        "resume_text": resume_text,
        "parsed_profile": profile.model_dump(),
    }


def _persist_cache(state: ResumeGraphState) -> ResumeGraphState:
    log_event(
        "resume.graph.branch",
        extraction_branch=state.get("extraction_branch", "unknown"),
        ocr_error=state.get("ocr_error"),
        text_len=len(state.get("resume_text", "")),
    )
    return {
        "resume_text": state.get("resume_text", ""),
        "parsed_profile": state.get("parsed_profile", {}),
        "extraction_branch": state.get("extraction_branch", "unknown"),
    }


def build_resume_graph():
    builder = StateGraph(ResumeGraphState)
    builder.add_node("ocr_extract", _ocr_extract)
    builder.add_node("pdf_extract", _pdf_extract)
    builder.add_node("raw_decode", _raw_decode)
    builder.add_node("parse_profile", _parse_profile)
    builder.add_node("persist_cache", _persist_cache)

    builder.add_edge(START, "ocr_extract")
    builder.add_conditional_edges("ocr_extract", _branch_after_ocr)
    builder.add_conditional_edges("pdf_extract", _branch_after_pdf)
    builder.add_edge("raw_decode", "parse_profile")
    builder.add_edge("parse_profile", "persist_cache")
    builder.add_edge("persist_cache", END)
    return builder.compile()


def run_resume_graph(*, content: bytes, model: str | None = None) -> dict[str, Any]:
    graph = build_resume_graph()
    result = graph.invoke({"content": content, "model": model or settings.llm_model_default})
    return {
        "resume_text": result.get("resume_text", ""),
        "parsed_profile": result.get("parsed_profile", {}),
        "extraction_branch": result.get("extraction_branch", "unknown"),
    }
