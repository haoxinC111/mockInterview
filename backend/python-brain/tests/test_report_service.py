"""Tests for ReportService — report generation, dimension aggregation, radar chart."""

from app.services.report_service import ReportService
from app.workflows.graphs.report_graph import build_report_via_graph


def _make_eval(topic: str, score: int, primary_dim: str = "technical_depth",
               evidence: list | None = None, gaps: list | None = None,
               dim_scores: dict | None = None):
    """Helper to build a mock evaluation dict."""
    return {
        "topic": topic,
        "score": score,
        "evidence": evidence or [],
        "gaps": gaps or [],
        "primary_dimension": primary_dim,
        "dimension_scores": dim_scores or {primary_dim: score},
    }


svc = ReportService()


def test_build_report_empty_evaluations():
    report = svc.build_report([], "20k-30k", "Agent Engineer")
    assert report["overall_score"] == 0.0
    assert report["strengths"] == []
    assert report["risks"]
    assert report["report_mode"] == "training_guidance"
    assert report["salary_fit"]["level"] == "样本不足"
    assert "disclaimer" in report
    assert "radar_chart" in report
    assert "action_plan_30d" in report


def test_build_report_single_evaluation():
    evals = [_make_eval("Transformer 原理", 6,
                        primary_dim="technical_depth",
                        evidence=["答到了 attention 机制"],
                        gaps=["缺少 position encoding 细节"],
                        dim_scores={"technical_depth": 6, "architecture_design": 5})]
    report = svc.build_report(evals, "20k-30k", "Agent Engineer")
    assert report["overall_score"] > 0
    assert report["target_role"] == "Agent Engineer"
    assert isinstance(report["dimension_scores"], dict)


def test_build_report_multiple_evaluations():
    evals = [
        _make_eval("Transformer 原理", 8, "technical_depth",
                   evidence=["深入理解 attention"], dim_scores={"technical_depth": 8}),
        _make_eval("RAG 架构", 3, "architecture_design",
                   gaps=["不了解向量检索原理"], dim_scores={"architecture_design": 3}),
        _make_eval("Docker 部署", 7, "engineering_practice",
                   evidence=["有实际 K8s 经验"], dim_scores={"engineering_practice": 7}),
    ]
    report = svc.build_report(evals, "30k-40k", "Agent Engineer")

    assert len(report["strengths"]) >= 1
    assert len(report["risks"]) >= 1
    assert report["radar_chart"]["labels"]
    assert len(report["radar_chart"]["values"]) == len(report["radar_chart"]["labels"])
    assert len(report["radar_chart"]["benchmarks"]) == len(report["radar_chart"]["labels"])


def test_radar_chart_structure():
    evals = [_make_eval("Transformer 原理", 7, dim_scores={"technical_depth": 7})]
    report = svc.build_report(evals, "20k", "SRE")
    radar = report["radar_chart"]
    assert "labels" in radar
    assert "values" in radar
    assert "benchmarks" in radar
    # All benchmarks should be the default benchmark value
    assert all(b == 6.0 for b in radar["benchmarks"])


def test_action_plan_structure():
    evals = [
        _make_eval("RAG 架构", 3, "architecture_design",
                   gaps=["不了解检索策略"]),
        _make_eval("Prompt 工程", 8, "technical_depth",
                   evidence=["掌握 few-shot 技巧"]),
    ]
    report = svc.build_report(evals, "25k", "Agent Engineer")
    plan = report["action_plan_30d"]
    assert "overall" in plan
    assert "by_dimension" in plan
    assert isinstance(plan["overall"], list)
    assert isinstance(plan["by_dimension"], dict)


def test_salary_fit_levels():
    # High score → 较匹配
    assert svc.salary_fit(8.0, "20k", [])["level"] == "较匹配"
    # Mid score → 部分匹配
    assert svc.salary_fit(5.0, "20k", [])["level"] == "部分匹配"
    # Low score → 不匹配
    assert svc.salary_fit(2.0, "20k", [])["level"] == "不匹配"


def test_dimension_details_populated():
    evals = [
        _make_eval("Agent 编排", 4, "architecture_design",
                   gaps=["缺少多 Agent 协作经验"],
                   dim_scores={"architecture_design": 4}),
        _make_eval("Docker 部署", 8, "engineering_practice",
                   evidence=["熟练使用 K8s"],
                   dim_scores={"engineering_practice": 8}),
    ]
    report = svc.build_report(evals, "25k", "Agent Engineer")
    details = report["dimension_details"]
    assert "architecture_design" in details or "engineering_practice" in details
    for dim_id, dim in details.items():
        assert "label" in dim
        assert "score" in dim


def test_report_graph_matches_legacy_report_shape():
    evals = [
        _make_eval("Transformer 原理", 7, "technical_depth", dim_scores={"technical_depth": 7}),
        _make_eval("RAG 架构", 4, "architecture_design", dim_scores={"architecture_design": 4}),
    ]
    payload = build_report_via_graph(
        evaluations=evals,
        expected_salary="20k-30k",
        target_role="Agent Engineer",
    )
    assert "overall_score" in payload
    assert "action_plan_30d" in payload
    assert "disclaimer" in payload


def test_build_report_empty_evaluations_uses_training_guidance_mode():
    report = svc.build_report([], "20k-30k", "Agent Engineer")
    assert report["report_mode"] == "training_guidance"
    assert report["salary_fit"]["level"] == "样本不足"
    assert report["risks"]
    assert report["action_plan_30d"]["overall"]


def test_build_report_low_signal_adds_risk_when_missing():
    evals = [
        _make_eval(
            "Transformer 原理",
            5,
            "technical_depth",
            evidence=["知道基本概念"],
            gaps=[],
            dim_scores={"technical_depth": 5},
        )
    ]
    report = svc.build_report(evals, "20k-30k", "Agent Engineer")
    assert report["overall_score"] < 6
    assert report["risks"]
