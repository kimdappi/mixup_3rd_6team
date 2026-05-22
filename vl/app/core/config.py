from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"

    llm_provider: str = Field(default="openai")
    llm_model: str
    openai_api_key: SecretStr
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 2
    llm_temperature: float = 0.2

    molit_api_service_key: SecretStr
    ocr_provider: str = "local"
    ocr_api_key: SecretStr | None = None
    ocr_api_url: str | None = None

    @model_validator(mode="after")
    def validate_ocr_settings(self) -> "Settings":
        if self.ocr_provider != "local" and self.ocr_api_key is None:
            raise ValueError("OCR_PROVIDER가 local이 아니면 OCR_API_KEY가 필요합니다.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
