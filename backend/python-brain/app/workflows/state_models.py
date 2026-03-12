from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class WorkflowFeatureFlags:
    use_langgraph: bool = False
    shadow_mode: bool = False
    report_use_langgraph: bool = False
    resume_use_langgraph: bool = False
    turn_use_langgraph: bool = False


@dataclass(slots=True)
class ShadowExecutionMeta:
    enabled: bool = False
    legacy_result: dict[str, Any] | None = None
    langgraph_result: dict[str, Any] | None = None
    diff: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class InterviewWorkflowState:
    module_idx: int = 0
    topic_idx: int = 0
    depth: int = 0
    max_depth: int = 2
    turn_count: int = 0
    max_turns: int = 12
    finished: bool = False
    outline: dict[str, Any] = field(default_factory=dict)
    evaluations: list[dict[str, Any]] = field(default_factory=list)
    decision_traces: list[dict[str, Any]] = field(default_factory=list)
    current_module: str | None = None
    current_topic: str | None = None
    workflow_version: str = "v1"
    feature_flags: WorkflowFeatureFlags = field(default_factory=WorkflowFeatureFlags)
    shadow: ShadowExecutionMeta = field(default_factory=ShadowExecutionMeta)

    @classmethod
    def initial(
        cls,
        *,
        outline: dict[str, Any] | None = None,
        max_depth: int = 2,
        max_turns: int = 12,
        feature_flags: WorkflowFeatureFlags | None = None,
        workflow_version: str = "v1",
    ) -> "InterviewWorkflowState":
        return cls(
            outline=outline or {},
            max_depth=max_depth,
            max_turns=max_turns,
            workflow_version=workflow_version,
            feature_flags=feature_flags or WorkflowFeatureFlags(),
            shadow=ShadowExecutionMeta(enabled=(feature_flags.shadow_mode if feature_flags else False)),
        )


@dataclass(slots=True)
class ResumeIngestionState:
    resume_id: int | None = None
    filename: str = ""
    resume_text: str = ""
    parsed_profile: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    used_ocr: bool = False
    fallback_path: str = ""
    workflow_version: str = "v1"
    feature_flags: WorkflowFeatureFlags = field(default_factory=WorkflowFeatureFlags)
    shadow: ShadowExecutionMeta = field(default_factory=ShadowExecutionMeta)


@dataclass(slots=True)
class ReportWorkflowState:
    session_id: int | None = None
    evaluations: list[dict[str, Any]] = field(default_factory=list)
    target_role: str = "Agent Engineer"
    expected_salary: str = ""
    dimension_scores: dict[str, float] = field(default_factory=dict)
    report_payload: dict[str, Any] = field(default_factory=dict)
    workflow_version: str = "v1"
    feature_flags: WorkflowFeatureFlags = field(default_factory=WorkflowFeatureFlags)
    shadow: ShadowExecutionMeta = field(default_factory=ShadowExecutionMeta)
