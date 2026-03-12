from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.report_service import ReportService


def _load_cases() -> list[dict]:
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "golden_sessions.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    cases = payload.get("report_cases", [])
    assert cases, "golden report cases missing"
    return cases


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["name"])
def test_report_golden_cases(case: dict) -> None:
    service = ReportService()
    report = service.build_report(
        evaluations=case["evaluations"],
        expected_salary=case["expected_salary"],
        target_role=case["target_role"],
    )

    expected = case["expected"]
    assert expected["score_min"] <= report["overall_score"] <= expected["score_max"]

    required_keys = {
        "overall_score",
        "dimension_scores",
        "dimension_details",
        "radar_chart",
        "strengths",
        "risks",
        "salary_fit",
        "action_plan_30d",
        "disclaimer",
    }
    assert required_keys.issubset(report.keys())
    assert "labels" in report["radar_chart"]
    assert "values" in report["radar_chart"]
    assert "benchmarks" in report["radar_chart"]
    assert "overall" in report["action_plan_30d"]
    assert "by_dimension" in report["action_plan_30d"]
