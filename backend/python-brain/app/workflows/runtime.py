from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.core.config import settings

RuntimeMode = Literal["legacy", "shadow", "langgraph"]


@dataclass(frozen=True)
class WorkflowRuntimeSelection:
    interview: RuntimeMode
    report: RuntimeMode
    resume: RuntimeMode


def choose_interview_runtime(use_langgraph: bool, shadow_mode: bool) -> RuntimeMode:
    if not use_langgraph:
        return "legacy"
    if shadow_mode:
        return "shadow"
    return "langgraph"


def _choose_feature_runtime(
    *,
    global_use_langgraph: bool,
    feature_use_langgraph: bool,
    shadow_mode: bool,
) -> RuntimeMode:
    return choose_interview_runtime(global_use_langgraph and feature_use_langgraph, shadow_mode)


def choose_workflow_runtime(
    *,
    workflow_use_langgraph: bool,
    workflow_shadow_mode: bool,
    workflow_report_use_langgraph: bool,
    workflow_resume_use_langgraph: bool,
    workflow_turn_use_langgraph: bool,
) -> WorkflowRuntimeSelection:
    return WorkflowRuntimeSelection(
        interview=_choose_feature_runtime(
            global_use_langgraph=workflow_use_langgraph,
            feature_use_langgraph=workflow_turn_use_langgraph,
            shadow_mode=workflow_shadow_mode,
        ),
        report=_choose_feature_runtime(
            global_use_langgraph=workflow_use_langgraph,
            feature_use_langgraph=workflow_report_use_langgraph,
            shadow_mode=workflow_shadow_mode,
        ),
        resume=_choose_feature_runtime(
            global_use_langgraph=workflow_use_langgraph,
            feature_use_langgraph=workflow_resume_use_langgraph,
            shadow_mode=workflow_shadow_mode,
        ),
    )


def choose_workflow_runtime_from_settings() -> WorkflowRuntimeSelection:
    return choose_workflow_runtime(
        workflow_use_langgraph=settings.workflow_use_langgraph,
        workflow_shadow_mode=settings.workflow_shadow_mode,
        workflow_report_use_langgraph=settings.workflow_report_use_langgraph,
        workflow_resume_use_langgraph=settings.workflow_resume_use_langgraph,
        workflow_turn_use_langgraph=settings.workflow_turn_use_langgraph,
    )
