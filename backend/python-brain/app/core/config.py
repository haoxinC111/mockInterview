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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
