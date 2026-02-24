from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CandidateProfile(BaseModel):
    name: str | None = None
    years_exp: int | None = None
    age: int | None = None
    expected_salary: str | None = None
    skills: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)


class OutlineTopic(BaseModel):
    name: str
    rubric_keywords: list[str]


class OutlineModule(BaseModel):
    module_name: str
    topics: list[OutlineTopic]


class InterviewOutline(BaseModel):
    modules: list[OutlineModule]


class TurnEvaluation(BaseModel):
    topic: str
    score: int
    evidence: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    depth_delta: int = 0
    decision: Literal["deepen", "next_topic", "next_module", "end"]


class ResumeUploadResponse(BaseModel):
    resume_id: int
    parsed_profile: CandidateProfile
    warnings: list[str] = Field(default_factory=list)
    cache_hit: bool = False
    cache_id: int | None = None


class StartInterviewRequest(BaseModel):
    resume_id: int
    target_role: str = "Agent Engineer"
    expected_salary: str
    model: str | None = None


class StartInterviewResponse(BaseModel):
    session_id: int
    first_question: str
    outline_summary: list[str]


class SendMessageRequest(BaseModel):
    user_message: str
    client_turn_id: str | None = None


class SendMessageResponse(BaseModel):
    assistant_message: str
    turn_eval: TurnEvaluation
    next_action: Literal["follow_up", "next_topic", "end"]


class FinishInterviewResponse(BaseModel):
    report_id: int
    report_payload: dict[str, Any]


class ReportResponse(BaseModel):
    report_id: int
    session_id: int
    created_at: datetime
    report_payload: dict[str, Any]
