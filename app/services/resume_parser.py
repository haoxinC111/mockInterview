from __future__ import annotations

import re
from io import BytesIO

from pypdf import PdfReader

from app.core.config import settings
from app.models.schemas import CandidateProfile
from app.services.llm_client import RelayLLMClient

KNOWN_SKILLS = [
    "python",
    "java",
    "javascript",
    "typescript",
    "go",
    "rust",
    "c++",
    "sql",
    "linux",
    "git",
    "flask",
    "langchain",
    "langgraph",
    "rag",
    "llm",
    "prompt",
    "agent",
    "docker",
    "kubernetes",
    "redis",
    "postgresql",
    "mysql",
    "mongodb",
    "elasticsearch",
    "fastapi",
    "pytorch",
    "tensorflow",
]


class ResumeParser:
    _llm_client = RelayLLMClient()

    @staticmethod
    def extract_text(content: bytes) -> str:
        try:
            reader = PdfReader(BytesIO(content))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = ResumeParser._normalize_text("\n".join(pages))
            if text:
                return text
        except Exception:
            pass
        return ResumeParser._normalize_text(content.decode("utf-8", errors="ignore"))

    @staticmethod
    def parse_profile(text: str, model: str | None = None) -> CandidateProfile:
        if settings.resume_parser_use_llm and ResumeParser._llm_client.is_enabled():
            try:
                profile = ResumeParser._parse_profile_with_llm(text, model or settings.llm_model_default)
                if profile.skills or profile.projects:
                    return profile
            except Exception:
                pass
        return ResumeParser._parse_profile_with_rules(text)

    @staticmethod
    def _normalize_text(text: str) -> str:
        raw_lines = [re.sub(r"\s+", " ", line).strip() for line in text.replace("\r", "\n").split("\n")]
        lines = [line for line in raw_lines if line]
        if not lines:
            return ""

        def is_list_item(line: str) -> bool:
            return bool(re.match(r"^([\-*•]|(\d+[\.\)])|[一二三四五六七八九十]+[、\.])\s*", line))

        def ends_sentence(line: str) -> bool:
            return line.endswith(("。", "！", "？", ".", "!", "?", ";", "；", ":", "："))

        merged: list[str] = []
        for line in lines:
            if not merged:
                merged.append(line)
                continue

            prev = merged[-1]
            # Keep headings/list items separated.
            if is_list_item(line) or is_list_item(prev):
                merged.append(line)
                continue

            # Merge wrapped lines produced by PDF extraction.
            if not ends_sentence(prev):
                if re.search(r"[\u4e00-\u9fff]$", prev) and re.match(r"^[\u4e00-\u9fff]", line):
                    merged[-1] = prev + line
                elif re.search(r"[A-Za-z0-9]$", prev) and re.match(r"^[A-Za-z0-9]", line):
                    merged[-1] = prev + " " + line
                else:
                    merged[-1] = prev + " " + line
                continue

            merged.append(line)

        return "\n".join(merged).strip()

    @staticmethod
    def _parse_profile_with_rules(text: str) -> CandidateProfile:
        lowered = text.lower()
        skills = sorted({skill for skill in KNOWN_SKILLS if skill in lowered})

        years_exp = None
        years_match = re.search(r"(\d{1,2})\+?\s*(?:years?|yrs?|年)", lowered)
        if years_match:
            years_exp = int(years_match.group(1))

        age = None
        age_match = re.search(r"(?:age|年龄)\s*[:：]?\s*(\d{2})", lowered)
        if age_match:
            age = int(age_match.group(1))

        expected_salary = None
        salary_match = re.search(r"(?:薪资|期望薪资|expected salary)\s*[:：]?\s*([^\n,，;；]{3,40})", text, re.IGNORECASE)
        if salary_match:
            expected_salary = salary_match.group(1).strip()

        name = None
        name_match = re.search(r"(?:姓名|name)\s*[:：]?\s*([A-Za-z\u4e00-\u9fff·\s]{2,40})", text, re.IGNORECASE)
        if name_match:
            name = name_match.group(1).strip()

        for line in text.splitlines()[:120]:
            if re.search(r"(技能|skills?)\s*[:：]", line, re.IGNORECASE):
                raw = re.split(r"[:：]", line, maxsplit=1)[-1]
                candidates = [s.strip().lower() for s in re.split(r"[,，/|、;；]", raw) if s.strip()]
                for token in candidates:
                    if 1 < len(token) <= 32 and re.search(r"[a-zA-Z\u4e00-\u9fff]", token):
                        skills.append(token)

        project_lines: list[str] = []
        capture_project_section = False
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            low = line.lower()
            if re.search(r"(项目经历|project experience|projects?)", low):
                capture_project_section = True
                continue
            if capture_project_section and re.search(r"(教育|education|技能|skills?|工作经历|experience)", low):
                capture_project_section = False
            if capture_project_section and len(line) >= 8:
                project_lines.append(line)
            if len(line) > 16 and any(tag in low for tag in ["project", "项目", "负责", "设计", "落地", "experience", "经历"]):
                project_lines.append(line)

        return CandidateProfile(
            name=name,
            years_exp=years_exp,
            age=age,
            expected_salary=expected_salary,
            skills=sorted(set(skills))[:40],
            projects=list(dict.fromkeys(project_lines))[:20],
        )

    @staticmethod
    def _parse_profile_with_llm(text: str, model: str) -> CandidateProfile:
        system_prompt = (
            "你是简历信息提取器。"
            "严格输出 JSON，不要输出解释。"
            "字段: name, years_exp, age, expected_salary, skills(list), projects(list)。"
            "skills 和 projects 尽量完整，不要臆造。"
        )
        user_prompt = (
            "从以下简历文本中提取结构化信息。\n"
            "如果字段缺失，返回 null 或空数组。\n"
            f"简历文本:\n{text[:18000]}"
        )
        data = ResumeParser._llm_client.chat_json_sync(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            force_json_object=True,
            timeout_s=25.0,
        )
        return CandidateProfile.model_validate(data)
