from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate


def interview_question_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是成长导向技术面试官。只输出一个聚焦问题，避免多问并列。",
            ),
            (
                "human",
                "岗位: {target_role}\n主题: {topic}\n候选人回答: {answer}\n请输出下一个追问。",
            ),
        ]
    )


def render_interview_question_prompt(*, target_role: str, topic: str, answer: str) -> str:
    prompt = interview_question_prompt()
    messages = prompt.format_messages(target_role=target_role, topic=topic, answer=answer)
    return "\n".join(m.content for m in messages)
