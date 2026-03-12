from __future__ import annotations

from typing import Any

from app.core.logging import log_event

DIMENSIONS = {
    "technical_depth": {"label": "技术深度", "weight": 0.35},
    "architecture_design": {"label": "架构设计", "weight": 0.35},
    "engineering_practice": {"label": "工程实践", "weight": 0.30},
}

DEFAULT_BENCHMARK = 6.0


class ReportService:
    @staticmethod
    def salary_fit(avg_score: float, expected_salary: str, risks: list[str]) -> dict[str, Any]:
        if avg_score <= 0:
            return {
                "level": "样本不足",
                "advice": f"当前还没有形成有效作答样本，暂不判断与期望薪资 {expected_salary} 的匹配度，建议先完成至少 2 轮有效训练。",
            }
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
        dim_scores: dict[str, list[float]] = {}
        for ev in evaluations:
            ds = ev.get("dimension_scores", {})
            for dim, score in ds.items():
                dim_scores.setdefault(dim, []).append(float(score))
        return {dim: round(sum(scores) / len(scores), 2) for dim, scores in dim_scores.items() if scores}

    @staticmethod
    def _build_radar_chart(dimension_scores: dict[str, float]) -> dict[str, Any]:
        labels = []
        values = []
        benchmarks = []
        for dim_id, meta in DIMENSIONS.items():
            labels.append(meta["label"])
            values.append(dimension_scores.get(dim_id, 0.0))
            benchmarks.append(DEFAULT_BENCHMARK)
        return {"labels": labels, "values": values, "benchmarks": benchmarks}

    @staticmethod
    def _build_action_plan(
        risks: list[str],
        evaluations: list[dict[str, Any]],
        dimension_scores: dict[str, float],
    ) -> dict[str, Any]:
        overall: list[str] = []
        by_dimension: dict[str, list[str]] = {}

        weak_dims = [dim_id for dim_id, score in dimension_scores.items() if score < DEFAULT_BENCHMARK]
        low_topics = [
            (item.get("topic", ""), item.get("primary_dimension", ""), item.get("gaps", []))
            for item in evaluations
            if item.get("score", 0) <= 4
        ]

        for topic, primary_dim, gaps in low_topics[:4]:
            overall.append(f"针对「{topic}」建立复盘卡片，梳理核心概念并进行模拟演练")
            if primary_dim:
                dim_plan = by_dimension.setdefault(primary_dim, [])
                if gaps:
                    dim_plan.append(f"补强「{topic}」: {gaps[0][:60]}")
                else:
                    dim_plan.append(f"深入学习「{topic}」相关知识点")

        for dim_id in weak_dims:
            if dim_id not in by_dimension:
                dim_label = DIMENSIONS.get(dim_id, {}).get("label", dim_id)
                by_dimension[dim_id] = [f"系统提升{dim_label}能力，建议结合项目实践做专项练习"]

        if not evaluations:
            overall.extend(
                [
                    "先完成至少 2 轮有效作答，确保系统获得足够样本再生成正式评估。",
                    "围绕目标岗位准备 3 个项目案例，按“背景-方案-取舍-结果”结构练习表达。",
                ]
            )
        else:
            overall.append("补齐每个模块的标准答题框架（定义-原理-权衡-落地）")
            if not low_topics:
                overall.append("进一步深化项目实战案例，练习讲清 tradeoff 和量化收益")

        return {"overall": overall[:4], "by_dimension": by_dimension}

    @staticmethod
    def _build_low_signal_risk(dimension_scores: dict[str, float], target_role: str) -> str:
        if dimension_scores:
            lowest_dim = min(dimension_scores.items(), key=lambda item: item[1])[0]
            dim_label = DIMENSIONS.get(lowest_dim, {}).get("label", lowest_dim)
            return f"{dim_label} 暂未形成稳定优势，建议补充可验证的项目证据、设计取舍与复盘细节。"
        return f"针对目标岗位「{target_role}」的有效作答样本不足，建议先补齐基础题框架和项目证据。"

    def build_report(self, evaluations: list[dict[str, Any]], expected_salary: str, target_role: str) -> dict[str, Any]:
        log_event(
            "report.build.start",
            target_role=target_role,
            expected_salary=expected_salary,
            evaluations_count=len(evaluations),
        )
        avg = 0.0 if not evaluations else sum(item.get("score", 0) for item in evaluations) / len(evaluations)

        strengths = [f"{item['topic']} 回答较完整" for item in evaluations if item.get("score", 0) >= 7]
        risks = [
            f"{item['topic']} 关键点缺失: {', '.join(item.get('gaps', [])[:3])}"
            for item in evaluations
            if item.get("score", 0) <= 4
        ]

        dimension_scores = self._aggregate_dimension_scores(evaluations)
        if dimension_scores:
            weighted_sum = 0.0
            weight_sum = 0.0
            for dim_id, meta in DIMENSIONS.items():
                if dim_id in dimension_scores:
                    weighted_sum += dimension_scores[dim_id] * meta["weight"]
                    weight_sum += meta["weight"]
            if weight_sum > 0:
                avg = round(weighted_sum / weight_sum, 2)

        if not evaluations:
            risks = ["尚未形成有效作答样本，当前报告仅提供训练建议，不进行岗位或薪资匹配判断。"]
        elif avg < DEFAULT_BENCHMARK and not risks:
            risks = [self._build_low_signal_risk(dimension_scores, target_role)]

        radar_chart = self._build_radar_chart(dimension_scores)
        action_plan = self._build_action_plan(risks, evaluations, dimension_scores)

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
            "report_mode": "training_guidance" if not evaluations else "standard_evaluation",
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
            report_mode=payload["report_mode"],
        )
        return payload
