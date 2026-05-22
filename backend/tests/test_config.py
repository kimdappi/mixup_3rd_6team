import pytest

from app.core.config import Settings


def test_settings_reads_llm_molit_and_ocr_values():
    settings = Settings(
        llm_provider="openai",
        llm_model="gpt-4.1-mini",
        openai_api_key="sk-test",
        molit_api_service_key="molit-test",
        ocr_provider="external",
        ocr_api_key="ocr-test",
        ocr_api_url="https://ocr.example.test",
        llm_timeout_seconds=30,
        llm_max_retries=2,
        llm_temperature=0.2,
    )

    assert settings.llm_provider == "openai"
    assert settings.llm_model == "gpt-4.1-mini"
    assert settings.openai_api_key.get_secret_value() == "sk-test"
    assert settings.molit_api_service_key.get_secret_value() == "molit-test"
    assert settings.ocr_api_key is not None
    assert settings.ocr_api_key.get_secret_value() == "ocr-test"
    assert settings.ocr_api_url == "https://ocr.example.test"
    assert settings.llm_temperature == 0.2


def test_settings_rejects_missing_required_keys():
    with pytest.raises(Exception):
        Settings(llm_provider="openai", llm_model="gpt-4.1-mini")


def test_settings_rejects_external_ocr_without_key():
    with pytest.raises(Exception):
        Settings(
            llm_provider="openai",
            llm_model="gpt-4.1-mini",
            openai_api_key="sk-test",
            molit_api_service_key="molit-test",
            ocr_provider="external",
        )
