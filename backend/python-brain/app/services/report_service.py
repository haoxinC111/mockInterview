from __future__ import annotations

from typing import Any

from app.core.logging import log_event


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
    def _build_action_plan(risks: list[str], evaluations: list[dict[str, Any]]) -> list[str]:
        """Generate action plan items based on actual weak areas."""
        plan: list[str] = []
        # Specific items for low-scoring topics
        low_topics = [item.get("topic", "") for item in evaluations if item.get("score", 0) <= 4]
        for topic in low_topics[:2]:
            plan.append(f"针对「{topic}」建立复盘卡片，梳理核心概念并进行模拟演练")
        # General improvements
        plan.append("补齐每个模块的标准答题框架（定义-原理-权衡-落地）")
        if not low_topics:
            plan.append("进一步深化项目实战案例，练习讲清 tradeoff 和量化收益")
        return plan[:3]

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

        payload = {
            "target_role": target_role,
            "overall_score": round(avg, 2),
            "dimension_scores": {
                "technical_depth": round(avg, 2),
            },
            "strengths": strengths[:5],
            "risks": risks[:5],
            "salary_fit": self.salary_fit(avg, expected_salary, risks),
            "action_plan_30d": self._build_action_plan(risks, evaluations),
            "disclaimer": "该报告仅用于训练与自我评估，不作为真实招聘决策唯一依据。",
        }
        log_event(
            "report.build.done",
            overall_score=payload["overall_score"],
            strengths_count=len(payload["strengths"]),
            risks_count=len(payload["risks"]),
            salary_fit=payload["salary_fit"]["level"],
        )
        return payload
