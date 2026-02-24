from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.core.logging import log_event, log_summary
from app.models.schemas import InterviewOutline, OutlineModule, OutlineTopic, TurnEvaluation
from app.services.llm_client import RelayLLMClient

DEFAULT_OUTLINE = [
    (
        "LLM 基础",
        [
            ("Transformer 原理", ["attention", "self-attention", "position", "并行"]),
            ("Prompt 设计", ["system prompt", "few-shot", "约束", "输出格式"]),
        ],
    ),
    (
        "RAG 架构",
        [
            ("索引与召回", ["chunk", "embedding", "topk", "向量库"]),
            ("检索优化", ["rerank", "hybrid", "召回率", "精确率"]),
        ],
    ),
    (
        "Agent 编排",
        [
            ("状态机与工具调用", ["state", "tool", "planner", "executor"]),
            ("稳定性与回退", ["retry", "fallback", "timeout", "幂等"]),
        ],
    ),
]


@dataclass
class EngineResult:
    question: str
    turn_eval: TurnEvaluation
    next_action: str
    state: dict[str, Any]


class InterviewEngine:
    def __init__(self) -> None:
        self.llm_client = RelayLLMClient()

    def build_outline(
        self,
        skills: list[str],
        *,
        target_role: str | None = None,
        model: str | None = None,
        profile: dict[str, Any] | None = None,
        resume_text: str | None = None,
    ) -> InterviewOutline:
        log_event("engine.outline.build.start", skills=skills)
        use_llm = settings.interview_engine_use_llm and self.llm_client.is_enabled()
        if use_llm and (profile or resume_text):
            try:
                outline = self._build_outline_with_llm(
                    skills=skills,
                    target_role=target_role or "Agent Engineer",
                    model=model or settings.llm_model_default,
                    profile=profile or {},
                    resume_text=resume_text or "",
                )
                log_event(
                    "engine.outline.build.done",
                    source="llm",
                    module_count=len(outline.modules),
                    module_names=[m.module_name for m in outline.modules],
                )
                return outline
            except Exception as exc:
                log_event("engine.outline.build.llm_fallback", error=str(exc))
        if profile or resume_text:
            outline = self._build_outline_from_resume_signal(
                skills=skills,
                target_role=target_role or "Agent Engineer",
                profile=profile or {},
                resume_text=resume_text or "",
            )
            log_event(
                "engine.outline.build.done",
                source="resume_signal",
                module_count=len(outline.modules),
                module_names=[m.module_name for m in outline.modules],
            )
            return outline

        modules: list[OutlineModule] = []
        for module_name, topics in DEFAULT_OUTLINE:
            items = [OutlineTopic(name=t[0], rubric_keywords=t[1]) for t in topics]
            modules.append(OutlineModule(module_name=module_name, topics=items))
        if "langgraph" in skills or "langchain" in skills:
            modules.append(
                OutlineModule(
                    module_name="LLM 应用工程",
                    topics=[
                        OutlineTopic(name="LangGraph 设计", rubric_keywords=["state", "node", "edge", "checkpoint"])
                    ],
                )
            )
        outline = InterviewOutline(modules=modules)
        log_event(
            "engine.outline.build.done",
            module_count=len(outline.modules),
            module_names=[m.module_name for m in outline.modules],
        )
        return outline

    def _build_outline_from_resume_signal(
        self,
        *,
        skills: list[str],
        target_role: str,
        profile: dict[str, Any],
        resume_text: str,
    ) -> InterviewOutline:
        skills_lower = [str(s).lower() for s in skills]
        projects = [str(x) for x in (profile.get("projects") or []) if str(x).strip()]
        modules: list[OutlineModule] = []

        if projects:
            title_hint = projects[0][:16]
            modules.append(
                OutlineModule(
                    module_name="项目实战深挖",
                    topics=[
                        OutlineTopic(name=f"{title_hint} 架构设计", rubric_keywords=["架构", "链路", "瓶颈", "取舍"]),
                        OutlineTopic(name="稳定性与故障处理", rubric_keywords=["超时", "重试", "限流", "降级"]),
                    ],
                )
            )

        if "go" in skills_lower:
            modules.append(
                OutlineModule(
                    module_name="Go 工程能力",
                    topics=[
                        OutlineTopic(name="并发与性能优化", rubric_keywords=["goroutine", "channel", "锁", "性能"]),
                        OutlineTopic(name="服务治理", rubric_keywords=["超时", "重试", "熔断", "幂等"]),
                    ],
                )
            )

        if any(x in skills_lower for x in ["redis", "postgresql", "sql", "mysql", "mongodb"]):
            modules.append(
                OutlineModule(
                    module_name="数据与存储设计",
                    topics=[
                        OutlineTopic(name="缓存与数据库协同", rubric_keywords=["缓存", "一致性", "索引", "热点"]),
                        OutlineTopic(name="查询与容量治理", rubric_keywords=["慢查询", "分库分表", "扩容", "监控"]),
                    ],
                )
            )

        if any(x in skills_lower for x in ["rag", "langchain", "langgraph", "llm", "agent"]):
            modules.append(
                OutlineModule(
                    module_name="LLM / Agent 实践",
                    topics=[
                        OutlineTopic(name="RAG 检索链路", rubric_keywords=["chunk", "召回", "rerank", "延迟"]),
                        OutlineTopic(name="Agent 工具编排", rubric_keywords=["tool", "state", "planner", "fallback"]),
                    ],
                )
            )

        if not modules:
            modules.append(
                OutlineModule(
                    module_name=f"{target_role} 核心能力",
                    topics=[
                        OutlineTopic(name="系统设计与权衡", rubric_keywords=["性能", "稳定性", "成本", "可观测"]),
                        OutlineTopic(name="项目复盘与改进", rubric_keywords=["问题", "定位", "修复", "复盘"]),
                    ],
                )
            )
        return InterviewOutline(modules=modules[:5])

    def _build_outline_with_llm(
        self,
        *,
        skills: list[str],
        target_role: str,
        model: str,
        profile: dict[str, Any],
        resume_text: str,
    ) -> InterviewOutline:
        system_prompt = (
            "你是资深技术面试官。根据候选人简历与目标岗位生成结构化面试框架。"
            "严格输出 JSON: {\"modules\": [{\"module_name\": str, \"topics\": [{\"name\": str, \"rubric_keywords\": [str]}]}]}"
            "要求: 3-5 个模块，每模块 2-3 个主题，每主题 3-6 个关键词。"
            "必须与候选人背景和岗位相关，避免泛泛模板。"
        )
        user_prompt = (
            f"目标岗位: {target_role}\n"
            f"候选人技能: {skills}\n"
            f"候选人结构化信息: {profile}\n"
            f"候选人简历文本(节选): {(resume_text or '')[:6000]}"
        )
        data = self.llm_client.chat_json_sync(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            force_json_object=True,
            timeout_s=25.0,
        )
        outline = InterviewOutline.model_validate(data)
        if not outline.modules:
            raise ValueError("empty outline from llm")
        return outline

    def init_state(self, outline: InterviewOutline, model: str | None = None, target_role: str | None = None) -> dict[str, Any]:
        return {
            "module_idx": 0,
            "topic_idx": 0,
            "depth": 0,
            "max_depth": 2,
            "turn_count": 0,
            "max_turns": 12,
            "evaluations": [],
            "decision_traces": [],
            "outline": outline.model_dump(),
            "model": model or settings.llm_model_default,
            "target_role": target_role or "Agent Engineer",
            "finished": False,
        }

    def current_topic(self, state: dict[str, Any]) -> dict[str, Any] | None:
        modules = state["outline"]["modules"]
        mi = state["module_idx"]
        ti = state["topic_idx"]
        if mi >= len(modules):
            return None
        topics = modules[mi]["topics"]
        if ti >= len(topics):
            return None
        return {
            "module_name": modules[mi]["module_name"],
            "topic_name": topics[ti]["name"],
            "rubric_keywords": topics[ti]["rubric_keywords"],
        }

    def first_question(
        self,
        state: dict[str, Any],
        *,
        profile: dict[str, Any] | None = None,
        resume_text: str | None = None,
    ) -> str:
        topic = self.current_topic(state)
        if not topic:
            return "请先介绍你最有代表性的 Agent 项目。"
        use_llm = settings.interview_engine_use_llm and self.llm_client.is_enabled()
        if use_llm:
            try:
                model = str(state.get("model") or settings.llm_model_default)
                role = str(state.get("target_role") or "Agent Engineer")
                system_prompt = (
                    "你是技术面试官。输出 JSON: {\"question\": \"...\"}。"
                    "题目必须结合简历和岗位，具体且可追问。"
                    "只能输出一个问题，禁止编号、禁止分点、禁止同时提多个并列子问题。"
                )
                user_prompt = (
                    f"岗位: {role}\n"
                    f"当前模块: {topic['module_name']}\n"
                    f"当前主题: {topic['topic_name']}\n"
                    f"候选人信息: {profile or {}}\n"
                    f"简历文本节选: {(resume_text or '')[:3000]}"
                )
                data = self.llm_client.chat_json_sync(
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    force_json_object=True,
                    timeout_s=20.0,
                )
                question = str(data.get("question", "")).strip()
                if question:
                    return self._normalize_single_question(question)
            except Exception as exc:
                log_event("engine.first_question.llm_fallback", error=str(exc))
        project_hint = ""
        profile_projects = (profile or {}).get("projects") if isinstance(profile, dict) else None
        if isinstance(profile_projects, list) and profile_projects:
            project_hint = f"请结合你在“{str(profile_projects[0])[:18]}”里的实战细节回答。"
        return self._normalize_single_question(f"我们先看【{topic['module_name']}】中的 {topic['topic_name']}。{project_hint}".strip())

    def evaluate(self, user_message: str, keywords: list[str]) -> tuple[int, list[str], list[str]]:
        text = user_message.lower()
        hit = [kw for kw in keywords if kw.lower() in text]
        miss = [kw for kw in keywords if kw.lower() not in text]

        if len(hit) >= max(1, len(keywords) - 1):
            score = 5
        elif len(hit) >= max(1, len(keywords) // 2):
            score = 3
        elif hit:
            score = 2
        else:
            score = 1
        return score, hit, miss

    def evaluate_with_llm(
        self,
        model: str,
        topic_name: str,
        keywords: list[str],
        user_message: str,
        target_role: str,
        conversation_context: list[dict[str, str]] | None = None,
    ) -> tuple[int, list[str], list[str], str | None, str | None]:
        system_prompt = (
            "你是技术面试评分器。"
            "只输出 JSON，字段: score(1-5), evidence(list), gaps(list), recommend_action, reason。"
            "score 必须严格在 1-5 之间。"
        )
        user_prompt = (
            f"岗位: {target_role}\n"
            f"题目主题: {topic_name}\n"
            f"期望关键词: {keywords}\n"
            f"候选人回答: {user_message}\n"
            f"最近对话上下文: {conversation_context or []}\n"
            "请给出严格评分，evidence 和 gaps 均控制在 1-4 条。"
            "recommend_action 只能是 deepen/next_topic/end 之一。"
        )
        data = self.llm_client.chat_json_sync(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            force_json_object=True,
            timeout_s=10.0,
        )
        score = int(data.get("score", 1))
        score = max(1, min(5, score))
        evidence = [str(x) for x in (data.get("evidence") or [])][:4]
        gaps = [str(x) for x in (data.get("gaps") or [])][:4]
        recommend_action = str(data.get("recommend_action", "")).strip() or None
        reason = str(data.get("reason", "")).strip() or None
        return score, evidence, gaps, recommend_action, reason

    def generate_followup_with_llm(
        self,
        model: str,
        topic_name: str,
        module_name: str,
        decision: str,
        user_message: str,
        target_role: str,
        conversation_context: list[dict[str, str]] | None = None,
    ) -> str:
        system_prompt = "你是技术面试官。只返回一句中文追问或转场问题，不要解释。"
        user_prompt = (
            f"岗位: {target_role}\n"
            f"模块: {module_name}\n"
            f"主题: {topic_name}\n"
            f"决策: {decision}\n"
            f"候选人上一轮回答: {user_message}\n"
            f"最近对话上下文: {conversation_context or []}\n"
            "生成一句高质量提问。"
        )
        data = self.llm_client.chat_json_sync(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt
            + "\n要求：只能输出一个问题，不要分点，不要编号，不要给多问并列。"
            + "\n输出 JSON: {\"question\": \"...\"}",
            force_json_object=True,
            timeout_s=10.0,
        )
        question = str(data.get("question", "")).strip()
        if not question:
            raise ValueError("empty question from llm")
        return self._normalize_single_question(question)

    @staticmethod
    def _normalize_single_question(text: str) -> str:
        # Enforce one concise question for realistic interview turn-taking.
        t = re.sub(r"\s+", " ", text).strip()
        t = t.replace("```json", "").replace("```", "").strip()

        list_start = re.search(r"(?:^|[：:])\s*1[\.、]", t)
        if list_start:
            t = t[: list_start.start()].strip()

        t = re.sub(r"\b[1-9][\.、]\s*", "", t)
        t = t.strip(" -")

        qmark_idx = min([idx for idx in [t.find("？"), t.find("?")] if idx != -1], default=-1)
        if qmark_idx != -1:
            t = t[: qmark_idx + 1]

        if not t.endswith(("？", "?")):
            t = f"{t.rstrip('。') }？"

        if len(t) > 120:
            t = t[:120].rstrip("，,。；;:： ")
            if not t.endswith(("？", "?")):
                t += "？"
        return t

    @staticmethod
    def _build_feedback(score: int, gaps: list[str], llm_reason: str | None = None) -> str:
        if llm_reason:
            reason = llm_reason
        elif gaps:
            reason = f"关键点覆盖不足，缺少 {', '.join(gaps[:2])}"
        elif score <= 1:
            reason = "回答偏笼统，缺少可验证的技术细节"
        else:
            reason = "回答有基础，但深度和证据还不够"
        return f"反馈：{reason}。"

    def _advance(self, state: dict[str, Any]) -> None:
        modules = state["outline"]["modules"]
        mi = state["module_idx"]
        ti = state["topic_idx"] + 1

        if mi < len(modules) and ti < len(modules[mi]["topics"]):
            state["topic_idx"] = ti
            state["depth"] = 0
            return

        state["module_idx"] = mi + 1
        state["topic_idx"] = 0
        state["depth"] = 0

    def process_turn(
        self,
        state: dict[str, Any],
        user_message: str,
        conversation_context: list[dict[str, str]] | None = None,
    ) -> EngineResult:
        log_event(
            "engine.turn.process.start",
            module_idx=state.get("module_idx"),
            topic_idx=state.get("topic_idx"),
            depth=state.get("depth"),
            turn_count=state.get("turn_count"),
            user_message_len=len(user_message),
        )
        topic = self.current_topic(state)
        if topic is None:
            turn_eval = TurnEvaluation(
                topic="面试结束",
                score=0,
                evidence=[],
                gaps=[],
                depth_delta=0,
                decision="end",
            )
            state["finished"] = True
            log_event("engine.turn.process.end", decision="end", reason="no_current_topic")
            return EngineResult(
                question="本次面试结束。我将为你生成结构化报告。",
                turn_eval=turn_eval,
                next_action="end",
                state=state,
            )

        model = str(state.get("model") or settings.llm_model_default)
        target_role = str(state.get("target_role") or "Agent Engineer")
        use_llm = settings.interview_turn_use_llm and self.llm_client.is_enabled()
        llm_recommend_action: str | None = None
        llm_reason: str | None = None
        llm_evaluate_failed = False
        llm_followup_failed = False
        decision_source = "rule"
        if use_llm:
            try:
                score, evidence, gaps, llm_recommend_action, llm_reason = self.evaluate_with_llm(
                    model=model,
                    topic_name=topic["topic_name"],
                    keywords=topic["rubric_keywords"],
                    user_message=user_message,
                    target_role=target_role,
                    conversation_context=conversation_context,
                )
                decision_source = "llm"
            except Exception as exc:
                llm_evaluate_failed = True
                log_event("engine.turn.evaluate.llm_fallback", error=str(exc))
                score, evidence, gaps = self.evaluate(user_message, topic["rubric_keywords"])
        else:
            score, evidence, gaps = self.evaluate(user_message, topic["rubric_keywords"])
        state["turn_count"] += 1
        log_event(
            "engine.turn.evaluated",
            topic=topic["topic_name"],
            score=score,
            evidence=evidence,
            gaps=gaps,
        )

        decision_reason = ""
        feedback_text = ""
        if state["turn_count"] >= state["max_turns"]:
            decision = "end"
            next_action = "end"
            state["finished"] = True
            question = "达到本轮面试上限，我将结束并生成报告。"
            depth_delta = 0
            decision_reason = "达到最大轮次上限"
        elif llm_evaluate_failed and score >= 2 and state["depth"] < 1:
            # If LLM times out but candidate answer has some substance,
            # prefer one conservative follow-up over immediate topic switch.
            state["depth"] += 1
            decision = "deepen"
            next_action = "follow_up"
            anchors = "、".join((evidence or topic["rubric_keywords"])[:2])
            question = f"你刚提到了 {anchors}，请结合具体线上案例说明设计取舍和失败复盘。"
            depth_delta = 1
            decision_reason = "LLM 超时，采用保守追问策略避免过早切题"
        elif llm_recommend_action == "end":
            decision = "end"
            next_action = "end"
            state["finished"] = True
            question = "本轮先到这里，我将结束并生成结构化报告。"
            depth_delta = 0
            decision_reason = llm_reason or "LLM 建议结束"
        elif llm_recommend_action == "deepen" and score >= 3 and state["depth"] < state["max_depth"]:
            state["depth"] += 1
            decision = "deepen"
            next_action = "follow_up"
            question = f"我们继续深入 {topic['topic_name']}，请讲一个失败案例和你的修复路径。"
            depth_delta = 1
            decision_reason = llm_reason or "LLM 建议继续深挖"
        elif llm_recommend_action == "next_topic":
            self._advance(state)
            decision = "next_topic" if self.current_topic(state) else "end"
            next_action = "next_topic" if decision != "end" else "end"
            next_topic = self.current_topic(state)
            feedback_text = self._build_feedback(score, gaps, llm_reason)
            question = (
                f"{feedback_text}我们切到【{next_topic['module_name']} - {next_topic['topic_name']}】。请结合项目给出技术取舍。"
                if next_topic
                else "面试结束。我将为你生成结构化报告。"
            )
            depth_delta = -state["depth"]
            if decision == "end":
                state["finished"] = True
            decision_reason = llm_reason or "LLM 建议切换题目"
        elif score >= 4 and state["depth"] < state["max_depth"]:
            state["depth"] += 1
            decision = "deepen"
            next_action = "follow_up"
            question = f"你提到的点不错。请继续深入 {topic['topic_name']} 的边界情况和失败案例。"
            depth_delta = 1
            decision_reason = "规则: 得分高且未达深挖上限"
        elif score <= 1:
            self._advance(state)
            decision = "next_module" if self.current_topic(state) else "end"
            next_action = "next_topic" if decision != "end" else "end"
            next_topic = self.current_topic(state)
            feedback_text = self._build_feedback(score, gaps, llm_reason)
            question = (
                f"{feedback_text}我们切到【{next_topic['module_name']} - {next_topic['topic_name']}】。请结合你的项目经历说明你的设计取舍。"
                if next_topic
                else "面试结束。我将为你生成结构化报告。"
            )
            depth_delta = -state["depth"]
            if decision == "end":
                state["finished"] = True
            decision_reason = "规则: 得分过低，切换知识点"
        else:
            self._advance(state)
            decision = "next_topic" if self.current_topic(state) else "end"
            next_action = "next_topic" if decision != "end" else "end"
            next_topic = self.current_topic(state)
            feedback_text = self._build_feedback(score, gaps, llm_reason)
            question = (
                f"{feedback_text}我们进入【{next_topic['module_name']} - {next_topic['topic_name']}】。请优先讲你做过的真实方案和权衡。"
                if next_topic
                else "面试结束。我将为你生成结构化报告。"
            )
            depth_delta = -state["depth"]
            if decision == "end":
                state["finished"] = True
            decision_reason = "规则: 常规推进到下一题"

        turn_eval = TurnEvaluation(
            topic=topic["topic_name"],
            score=score,
            evidence=evidence,
            gaps=gaps,
            depth_delta=depth_delta,
            decision=decision,  # type: ignore[arg-type]
        )
        state["evaluations"].append(turn_eval.model_dump())

        if use_llm and next_action in {"follow_up", "next_topic"} and not state.get("finished"):
            try:
                question = self.generate_followup_with_llm(
                    model=model,
                    topic_name=topic["topic_name"],
                    module_name=topic["module_name"],
                    decision=turn_eval.decision,
                    user_message=user_message,
                    target_role=target_role,
                    conversation_context=conversation_context,
                )
                if next_action == "next_topic" and feedback_text:
                    question = f"{feedback_text}{question}"
            except Exception as exc:
                llm_followup_failed = True
                log_event("engine.turn.followup.llm_fallback", error=str(exc))
                if next_action == "follow_up":
                    anchors = "、".join((evidence or topic["rubric_keywords"])[:2])
                    question = f"继续围绕 {anchors}，请补充关键实现细节与线上指标变化。"
        log_event(
            "engine.turn.decision",
            decision=turn_eval.decision,
            decision_source=decision_source,
            decision_reason=decision_reason,
            llm_recommend_action=llm_recommend_action,
            llm_reason=llm_reason,
            topic=topic["topic_name"],
            score=score,
        )
        state["decision_traces"].append(
            {
                "turn": state.get("turn_count"),
                "topic": topic["topic_name"],
                "module": topic["module_name"],
                "score": score,
                "decision": turn_eval.decision,
                "decision_source": decision_source,
                "decision_reason": decision_reason,
                "llm_recommend_action": llm_recommend_action,
                "llm_evaluate_failed": llm_evaluate_failed,
                "llm_followup_failed": llm_followup_failed,
                "feedback": feedback_text,
                "next_question": question,
            }
        )
        log_summary(
            "engine.turn.decision",
            topic=topic["topic_name"],
            decision=turn_eval.decision,
            decision_source=decision_source,
            decision_reason=decision_reason,
            llm_recommend_action=llm_recommend_action,
        )
        log_event(
            "engine.turn.process.end",
            topic=turn_eval.topic,
            decision=turn_eval.decision,
            next_action=next_action,
            module_idx=state.get("module_idx"),
            topic_idx=state.get("topic_idx"),
            depth=state.get("depth"),
            turn_count=state.get("turn_count"),
            finished=state.get("finished"),
        )

        return EngineResult(question=question, turn_eval=turn_eval, next_action=next_action, state=state)
