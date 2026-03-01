from __future__ import annotations

from typing import Any

from app.core.logging import log_event

# Dimension metadata per §8.1
DIMENSIONS = {
    "technical_depth": {"label": "技术深度", "weight": 0.35},
    "architecture_design": {"label": "架构设计", "weight": 0.35},
    "engineering_practice": {"label": "工程实践", "weight": 0.30},
    # communication enabled in v0.9+ when voice mode is ready
}

DEFAULT_BENCHMARK = 6.0


class ReportService:
    @staticmethod
    def salary_fit(avg_score: float, expected_salary: str, risks: list[str]) -> dict[str, Any]:
        gap_hint = f"，建议补齐 {risks[0].split('关键点缺失')[0].strip()}" if risks else ""
        if avg_score >= 7:
            level = "较匹配"
            advice = f"当前能力与期望薪资 {expected_salary} 基本匹配，可冲击更高难度面试。"
        elif avg_score >= 4:
            level = "部分匹配"
            advice = f"对标期望薪资 {expected_salary} 仍有缺口{gap_hint}。"
        else:
            level = "不匹配"
            advice = f"与期望薪资 {expected_salary} 存在明显差距，建议先强化基础能力再求职。"
        return {"level": level, "advice": advice}

    @staticmethod
    def _aggregate_dimension_scores(evaluations: list[dict[str, Any]]) -> dict[str, float]:
        """Aggregate per-dimension scores across all turns.

        For each dimension, collect all scores where that dimension appears
        and compute a weighted average (primary scores weight 1.0,
        secondary scores weight 0.5 — but since we store raw scores,
        we simply average all occurrences)."""
        dim_scores: dict[str, list[float]] = {}
        for ev in evaluations:
            ds = ev.get("dimension_scores", {})
            for dim, score in ds.items():
                dim_scores.setdefault(dim, []).append(float(score))
        return {
            dim: round(sum(scores) / len(scores), 2)
            for dim, scores in dim_scores.items()
            if scores
        }

    @staticmethod
    def _build_radar_chart(dimension_scores: dict[str, float]) -> dict[str, Any]:
        """Build radar chart data structure for frontend rendering."""
        labels = []
        values = []
        benchmarks = []
        for dim_id, meta in DIMENSIONS.items():
            labels.append(meta["label"])
            values.append(dimension_scores.get(dim_id, 0.0))
            benchmarks.append(DEFAULT_BENCHMARK)
        return {
            "labels": labels,
            "values": values,
            "benchmarks": benchmarks,
        }

    @staticmethod
    def _build_action_plan(
        risks: list[str],
        evaluations: list[dict[str, Any]],
        dimension_scores: dict[str, float],
    ) -> dict[str, Any]:
        """Generate action plan items per dimension based on actual weak areas."""
        overall: list[str] = []
        by_dimension: dict[str, list[str]] = {}

        # Identify weak dimensions (below benchmark)
        weak_dims = [
            dim_id for dim_id, score in dimension_scores.items()
            if score < DEFAULT_BENCHMARK
        ]

        # Specific items for low-scoring topics
        low_topics = [
            (item.get("topic", ""), item.get("primary_dimension", ""),
             item.get("gaps", []))
            for item in evaluations if item.get("score", 0) <= 4
        ]

        for topic, primary_dim, gaps in low_topics[:4]:
            dim_label = DIMENSIONS.get(primary_dim, {}).get("label", primary_dim)
            overall.append(f"针对「{topic}」建立复盘卡片，梳理核心概念并进行模拟演练")
            if primary_dim:
                dim_plan = by_dimension.setdefault(primary_dim, [])
                if gaps:
                    dim_plan.append(f"补强「{topic}」: {gaps[0][:60]}")
                else:
                    dim_plan.append(f"深入学习「{topic}」相关知识点")

        # Add general advice for weak dimensions without specific topics
        for dim_id in weak_dims:
            dim_label = DIMENSIONS.get(dim_id, {}).get("label", dim_id)
            if dim_id not in by_dimension:
                by_dimension[dim_id] = [f"系统提升{dim_label}能力，建议结合项目实践做专项练习"]

        overall.append("补齐每个模块的标准答题框架（定义-原理-权衡-落地）")
        if not low_topics:
            overall.append("进一步深化项目实战案例，练习讲清 tradeoff 和量化收益")

        return {
            "overall": overall[:4],
            "by_dimension": by_dimension,
        }

    def build_report(self, evaluations: list[dict[str, Any]], expected_salary: str, target_role: str) -> dict[str, Any]:
        log_event(
            "report.build.start",
            target_role=target_role,
            expected_salary=expected_salary,
            evaluations_count=len(evaluations),
        )
        if not evaluations:
            avg = 0.0
        else:
            avg = sum(item.get("score", 0) for item in evaluations) / len(evaluations)

        strengths = [
            f"{item['topic']} 回答较完整"
            for item in evaluations
            if item.get("score", 0) >= 7
        ]
        risks = [
            f"{item['topic']} 关键点缺失: {', '.join(item.get('gaps', [])[:3])}"
            for item in evaluations
            if item.get("score", 0) <= 4
        ]

        # Aggregate per-dimension scores
        dimension_scores = self._aggregate_dimension_scores(evaluations)

        # Compute weighted overall score if dimension data available
        if dimension_scores:
            weighted_sum = 0.0
            weight_sum = 0.0
            for dim_id, meta in DIMENSIONS.items():
                if dim_id in dimension_scores:
                    weighted_sum += dimension_scores[dim_id] * meta["weight"]
                    weight_sum += meta["weight"]
            if weight_sum > 0:
                avg = round(weighted_sum / weight_sum, 2)

        radar_chart = self._build_radar_chart(dimension_scores)
        action_plan = self._build_action_plan(risks, evaluations, dimension_scores)

        # Per-dimension strengths and gaps
        dimension_details: dict[str, dict[str, Any]] = {}
        for dim_id, meta in DIMENSIONS.items():
            if dim_id not in dimension_scores:
                continue
            dim_strengths = []
            dim_gaps = []
            for ev in evaluations:
                if ev.get("primary_dimension") == dim_id:
                    if ev.get("score", 0) >= 7:
                        dim_strengths.extend(ev.get("evidence", [])[:2])
                    if ev.get("score", 0) <= 5:
                        dim_gaps.extend(ev.get("gaps", [])[:2])
            dimension_details[dim_id] = {
                "label": meta["label"],
                "score": dimension_scores[dim_id],
                "strengths": dim_strengths[:4],
                "gaps": dim_gaps[:4],
            }

        payload = {
            "target_role": target_role,
            "overall_score": round(avg, 2),
            "dimension_scores": dimension_scores,
            "dimension_details": dimension_details,
            "radar_chart": radar_chart,
            "strengths": strengths[:5],
            "risks": risks[:5],
            "salary_fit": self.salary_fit(avg, expected_salary, risks),
            "action_plan_30d": action_plan,
            "disclaimer": "该报告仅用于训练与自我评估，不作为真实招聘决策唯一依据。",
        }
        log_event(
            "report.build.done",
            overall_score=payload["overall_score"],
            dimension_scores=dimension_scores,
            strengths_count=len(payload["strengths"]),
            risks_count=len(payload["risks"]),
            salary_fit=payload["salary_fit"]["level"],
        )
        return payload
