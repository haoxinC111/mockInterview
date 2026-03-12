from __future__ import annotations

from typing import Any


_KEY_FIELDS_TURN = ("next_action", "question")
_KEY_FIELDS_REPORT = ("overall_score", "target_role")
_KEY_FIELDS_RESUME = ("resume_text", "parsed_profile")


def _trim_text(text: str, *, max_len: int = 80) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def diff_turn_results(legacy: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    diff: dict[str, Any] = {}
    for key in _KEY_FIELDS_TURN:
        if legacy.get(key) != candidate.get(key):
            diff[key] = {"legacy": legacy.get(key), "candidate": candidate.get(key)}

    legacy_eval = legacy.get("turn_eval") or {}
    candidate_eval = candidate.get("turn_eval") or {}
    for key in ("topic", "score", "decision", "primary_dimension"):
        if legacy_eval.get(key) != candidate_eval.get(key):
            diff[f"turn_eval.{key}"] = {
                "legacy": legacy_eval.get(key),
                "candidate": candidate_eval.get(key),
            }
    return diff


def diff_report_results(legacy: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    diff: dict[str, Any] = {}
    for key in _KEY_FIELDS_REPORT:
        if legacy.get(key) != candidate.get(key):
            diff[key] = {"legacy": legacy.get(key), "candidate": candidate.get(key)}

    legacy_dims = legacy.get("dimension_scores") or {}
    candidate_dims = candidate.get("dimension_scores") or {}
    if legacy_dims != candidate_dims:
        diff["dimension_scores"] = {"legacy": legacy_dims, "candidate": candidate_dims}
    return diff


def diff_resume_results(legacy: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    diff: dict[str, Any] = {}

    legacy_text = str(legacy.get("resume_text") or "")
    candidate_text = str(candidate.get("resume_text") or "")
    if legacy_text != candidate_text:
        diff["resume_text"] = {
            "legacy_len": len(legacy_text),
            "candidate_len": len(candidate_text),
            "legacy_preview": _trim_text(legacy_text),
            "candidate_preview": _trim_text(candidate_text),
        }

    legacy_profile = legacy.get("parsed_profile") or {}
    candidate_profile = candidate.get("parsed_profile") or {}
    if legacy_profile != candidate_profile:
        diff["parsed_profile"] = {
            "legacy_keys": sorted(legacy_profile.keys()),
            "candidate_keys": sorted(candidate_profile.keys()),
        }
    return diff
