from __future__ import annotations

import base64
import re
from io import BytesIO

import httpx
from pypdf import PdfReader

from app.core.config import settings
from app.core.logging import log_event
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
    def _looks_like_pdf(content: bytes) -> bool:
        return content.lstrip().startswith(b"%PDF-")

    @staticmethod
    def extract_text(content: bytes) -> str:
        # Priority 1: OCR via Ollama deepseek-ocr (best quality for complex PDFs)
        is_pdf = ResumeParser._looks_like_pdf(content)
        if settings.resume_ocr_enabled and is_pdf:
            try:
                ocr_text = ResumeParser._extract_text_with_ocr(content)
                if ocr_text and len(ocr_text.strip()) > 50:
                    log_event("resume.extract.ocr_success", text_len=len(ocr_text))
                    return ocr_text
                log_event("resume.extract.ocr_insufficient", text_len=len(ocr_text.strip()) if ocr_text else 0)
            except Exception as exc:
                log_event("resume.extract.ocr_failed", error=str(exc))

        # Priority 2: pypdf text layer extraction
        if is_pdf:
            try:
                reader = PdfReader(BytesIO(content))
                pages = [page.extract_text() or "" for page in reader.pages]
                text = ResumeParser._normalize_text("\n".join(pages))
                if text and len(text.strip()) > 50:
                    return text
            except Exception:
                pass

        # Priority 3: raw UTF-8 decode (for .txt files)
        return ResumeParser._normalize_text(content.decode("utf-8", errors="ignore"))

    @staticmethod
    def _extract_text_with_ocr(content: bytes) -> str:
        """Convert PDF pages to images, send to Ollama deepseek-ocr, concatenate results."""
        import fitz  # pymupdf

        doc = fitz.open(stream=content, filetype="pdf")
        all_text: list[str] = []
        dpi = settings.resume_ocr_dpi
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)

        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            img_b64 = base64.b64encode(img_bytes).decode("ascii")

            page_text = ResumeParser._ocr_single_image(img_b64, page_num + 1)
            if page_text:
                all_text.append(page_text)

        doc.close()
        return ResumeParser._normalize_text("\n".join(all_text))

    @staticmethod
    def _ocr_single_image(img_b64: str, page_num: int) -> str:
        """Call Ollama deepseek-ocr to extract text from a single page image."""
        url = f"{settings.resume_ocr_ollama_url.rstrip('/')}/api/chat"
        payload = {
            "model": settings.resume_ocr_model,
            "messages": [
                {
                    "role": "user",
                    "content": "OCR this document image. Output ONLY the recognized text, preserving the original structure and formatting. Do not add any explanation.",
                    "images": [img_b64],
                }
            ],
            "stream": False,
        }

        log_event("resume.ocr.request", page=page_num, model=settings.resume_ocr_model)
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()

        data = resp.json()
        text = data.get("message", {}).get("content", "")
        log_event("resume.ocr.response", page=page_num, text_len=len(text))
        return text.strip()

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
        # Match "X年经验" / "X+ years" but NOT calendar years like "2021年"
        years_match = re.search(r"(?<!\d)(\d{1,2})\+?\s*(?:years?|yrs?|年)\s*(?:经验|工作|开发|experience)?", lowered)
        if years_match:
            val = int(years_match.group(1))
            # Reject implausible values (calendar year fragments like 21 from "2021年")
            if val <= 40:
                # Check context: reject if preceded by 19xx/20xx pattern
                start = years_match.start()
                prefix = lowered[max(0, start - 2):start]
                if not re.match(r"(?:19|20)$", prefix):
                    years_exp = val

        age = None
        age_match = re.search(r"(?:age|年龄)\s*[:：]?\s*(\d{2})", lowered)
        if age_match:
            age = int(age_match.group(1))

        expected_salary = None
        salary_match = re.search(r"(?:薪资|期望薪资|expected salary)\s*[:：]?\s*([^\n,，;；]{3,40})", text, re.IGNORECASE)
        if salary_match:
            expected_salary = salary_match.group(1).strip()

        name = None
        # Try labeled name first
        name_match = re.search(r"(?:姓名|name)\s*[:：]?\s*([A-Za-z\u4e00-\u9fff·\s]{2,40})", text, re.IGNORECASE)
        if name_match:
            name = name_match.group(1).strip()
        # Fallback: detect Chinese name (2-4 chars) in the first few lines of the resume
        if not name:
            for line in text.splitlines()[:5]:
                line = line.strip()
                cn_name_match = re.match(r"^([\u4e00-\u9fff]{2,4})(?:\s|$|\d|[|｜,，])", line)
                if cn_name_match:
                    candidate_name = cn_name_match.group(1)
                    # Exclude common section headers
                    if candidate_name not in ("个人", "简历", "基本", "联系", "求职", "教育", "工作", "项目", "技能", "自我"):
                        name = candidate_name
                        break

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
            if re.search(r"(项目经历|project experience|projects?)\s*$", low):
                capture_project_section = True
                continue
            if capture_project_section and re.search(r"(教育|education|技能|skills?|工作经历|experience)", low):
                capture_project_section = False
            if capture_project_section and len(line) >= 8 and not ResumeParser._looks_like_personal_info(line):
                project_lines.append(line)
            if len(line) > 16 and not ResumeParser._looks_like_personal_info(line) and any(
                tag in low for tag in ["项目", "负责", "设计", "落地"]
            ):
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
    def _looks_like_personal_info(line: str) -> bool:
        """Detect lines that are personal info (phone, email, address) rather than project descriptions."""
        # Contains phone number pattern
        if re.search(r"\d{11}", line):
            return True
        # Contains email
        if re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", line):
            return True
        # Very short line starting with a Chinese name pattern (2-4 chars) followed by contact info
        if re.match(r"^[\u4e00-\u9fff]{2,4}\s*[\d|｜]", line):
            return True
        return False

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
        data, _reasoning = ResumeParser._llm_client.chat_json_sync(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            force_json_object=True,
            timeout_s=25.0,
        )
        return CandidateProfile.model_validate(data)
