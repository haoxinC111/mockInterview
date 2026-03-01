from datetime import datetime
from typing import Any

from sqlalchemy import UniqueConstraint
from sqlmodel import JSON, Column, Field, SQLModel


class Resume(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    filename: str
    raw_text: str
    profile_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ResumeParseCache(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("filename", "file_hash", name="uq_resume_parse_cache_filename_hash"),)

    id: int | None = Field(default=None, primary_key=True)
    filename: str
    file_hash: str
    resume_id: int | None = None
    raw_text: str
    profile_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    hit_count: int = 0
    last_used_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InterviewSession(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    resume_id: int
    target_role: str
    expected_salary: str
    city: str = "北京"
    model: str
    answer_style: str = "concise"
    status: str = "active"
    state_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InterviewMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: int
    role: str
    content: str
    metadata_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class InterviewReport(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: int
    report_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
