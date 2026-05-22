"""registry_ocr 단위 테스트.

실 Vision API 호출은 통합 테스트 전용. 단위 테스트는 mock으로 처리.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.services import registry_ocr


# ============================================================
# Demo 모드
# ============================================================

class TestDemoMode:
    def test_demo_mode_returns_empty_string(self, monkeypatch):
        """REGISTRY_OCR_MODE='demo' → 빈 문자열."""
        monkeypatch.setattr("app.services.registry_ocr.REGISTRY_OCR_MODE", "demo")
        # PDF bytes도 무시한다
        result = registry_ocr.extract_text_from_pdf_bytes(b"fake-pdf-bytes")
        assert result == ""

    def test_demo_mode_skips_vision_call(self, monkeypatch):
        """demo 모드에서는 Vision API 호출 자체가 일어나지 않아야 함."""
        monkeypatch.setattr("app.services.registry_ocr.REGISTRY_OCR_MODE", "demo")
        called = []
        monkeypatch.setattr(
            "app.services.registry_ocr._call_vision",
            lambda *a, **kw: called.append(1) or "should not be called",
        )
        registry_ocr.extract_text_from_pdf_bytes(b"any")
        assert called == []


# ============================================================
# Vision 모드 - 키 검증
# ============================================================

class TestKeyValidation:
    def test_raises_when_key_missing(self, monkeypatch):
        """vision 모드인데 키가 비어 있으면 RuntimeError."""
        monkeypatch.setattr("app.services.registry_ocr.REGISTRY_OCR_MODE", "vision")
        monkeypatch.setattr("app.services.registry_ocr.GOOGLE_VISION_API_KEY", "")
        with pytest.raises(RuntimeError, match="GOOGLE_VISION_API_KEY"):
            registry_ocr.extract_text_from_pdf_bytes(b"any")


# ============================================================
# Vision 모드 - HTTP 호출 mock
# ============================================================

def _fake_response(status_code=200, json_data=None, text=""):
    class _Resp:
        def __init__(self):
            self.status_code = status_code
            self._json = json_data or {}
            self.text = text

        def json(self):
            return self._json

    return _Resp()


class TestVisionCall:
    def test_returns_text_on_success(self, monkeypatch):
        """정상 응답이면 추출된 텍스트 반환."""
        monkeypatch.setattr("app.services.registry_ocr.REGISTRY_OCR_MODE", "vision")
        monkeypatch.setattr("app.services.registry_ocr.GOOGLE_VISION_API_KEY", "test-key")

        # fitz.open이 1페이지짜리 PDF처럼 동작하도록 MagicMock 구성.
        mock_page = MagicMock()
        mock_page.get_pixmap.return_value.tobytes.return_value = b"fake-png"
        mock_pdf = MagicMock()
        mock_pdf.__enter__.return_value = iter([mock_page])
        mock_pdf.__exit__.return_value = False

        with patch(
            "app.services.registry_ocr._call_vision",
            return_value="추출된 텍스트",
        ), patch(
            "app.services.registry_ocr.fitz.open",
            return_value=mock_pdf,
        ):
            result = registry_ocr.extract_text_from_pdf_bytes(b"fake-pdf")
            assert result == "추출된 텍스트"

    def test_raises_on_http_error(self, monkeypatch):
        """Vision이 200 이외 응답 → RuntimeError."""
        monkeypatch.setattr("app.services.registry_ocr.REGISTRY_OCR_MODE", "vision")
        monkeypatch.setattr("app.services.registry_ocr.GOOGLE_VISION_API_KEY", "test-key")

        fake = _fake_response(status_code=403, text="Forbidden")
        with patch(
            "app.services.registry_ocr.requests.post",
            return_value=fake,
        ):
            with pytest.raises(RuntimeError, match="403"):
                registry_ocr._call_vision(b"fake-img")

    def test_raises_on_api_error_body(self, monkeypatch):
        """200이지만 응답 body에 error 필드 → RuntimeError."""
        monkeypatch.setattr("app.services.registry_ocr.REGISTRY_OCR_MODE", "vision")
        monkeypatch.setattr("app.services.registry_ocr.GOOGLE_VISION_API_KEY", "test-key")

        fake = _fake_response(
            status_code=200,
            json_data={"responses": [{"error": {"code": 7, "message": "PERMISSION_DENIED"}}]},
        )
        with patch(
            "app.services.registry_ocr.requests.post",
            return_value=fake,
        ):
            with pytest.raises(RuntimeError, match="Vision API error"):
                registry_ocr._call_vision(b"fake-img")
