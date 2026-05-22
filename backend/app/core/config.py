from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"
    log_level: str = "INFO"

    # ── 프론트엔드 CORS ──────────────────────────────────────────
    frontend_origin: str = "http://localhost:5173"

    # ── 사주 Agent (Kakao Map + Solar Pro) ───────────────────────
    kakao_rest_api_key: str = ""
    solar_pro_api_key: str = ""

    # ── 전세 진단 LLM ─────────────────────────────────────────────
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 2
    llm_temperature: float = 0.2

    # ── 전세 진단 국토부 API ───────────────────────────────────────
    molit_api_service_key: str = ""

    # ── OCR (확장 예정) ───────────────────────────────────────────
    ocr_provider: str = "local"
    ocr_api_key: str = ""
    ocr_api_url: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


# ── 기존 backend 코드와 호환성 유지 (os.getenv 방식 대신 Settings 사용) ──
def _s() -> Settings:
    return get_settings()


# 기존 코드에서 `from app.core.config import KAKAO_REST_API_KEY` 형태로 쓰던 것 유지
KAKAO_REST_API_KEY: str = get_settings().kakao_rest_api_key
SOLAR_PRO_API_KEY: str = get_settings().solar_pro_api_key
FRONTEND_ORIGIN: str = get_settings().frontend_origin
