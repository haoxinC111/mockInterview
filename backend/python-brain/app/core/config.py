from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_provider: str = "relay"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model_default: str = "MiniMax-M2.5"
    llm_model_candidates: str = "MiniMax-M2.5,glm-5"
    llm_kimi_api_key: str | None = None
    resume_parser_use_llm: bool = False
    resume_ocr_enabled: bool = False
    resume_ocr_ollama_url: str = "http://localhost:11434"
    resume_ocr_model: str = "deepseek-ocr"
    resume_ocr_dpi: int = 216
    interview_engine_use_llm: bool = False
    interview_turn_use_llm: bool = False
    log_dir: str = "logs"
    log_file: str = "interviewsim.log"
    summary_log_file: str = "interviewsim.summary.log"
    database_url: str = "sqlite:///./interview_sim.db"
    stt_enabled: bool = True
    stt_model: str = "small"
    stt_device: str = "cpu"
    stt_compute_type: str = "int8"
    stt_llm_cleanup: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()

# ── Project Mission (立意) ──────────────────────────────────────────────
# This statement is injected into every LLM system prompt so the AI interviewer
# consistently serves the goal of *growing the candidate's capability*.
PROJECT_MISSION = (
    "【系统立意】本系统的核心目标不是「考倒候选人」，而是「帮助候选人成长」。"
    "你是一位严格但有建设性的技术面试教练——"
    "每一个提问都应该引导候选人暴露真实的能力边界，"
    "每一次评估都应该指出具体可改进的方向，"
    "每一份反馈都应该让候选人比面试前更清楚自己该学什么、怎么练。"
    "请始终以「提升候选人能力」为第一优先级开展工作。"
)
