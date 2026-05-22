"""등기부등본 PDF → OCR 텍스트 추출 서비스.

Google Vision DOCUMENT_TEXT_DETECTION을 사용.
PyMuPDF로 PDF를 페이지별 PNG로 렌더한 뒤 Vision API에 전송.

모드:
    "vision" — 실 API 호출 (운영)
    "demo"   — 빈 문자열 반환 (개발/CI에서 Vision API 비용 회피)
"""
import base64
import logging

import fitz
import requests

from app.core.config import GOOGLE_VISION_API_KEY, REGISTRY_OCR_MODE

logger = logging.getLogger(__name__)

VISION_API_URL = "https://vision.googleapis.com/v1/images:annotate"
DEFAULT_DPI = 200
DEFAULT_TIMEOUT = 30
MAX_PAGES = 10  # 등기부등본은 보통 1~3페이지. 안전망으로 상한 설정.


def extract_text_from_pdf_bytes(pdf_bytes: bytes, dpi: int = DEFAULT_DPI) -> str:
    """PDF bytes → 모든 페이지의 OCR 텍스트를 합쳐 반환.

    Args:
        pdf_bytes: PDF 원본 바이트
        dpi: PDF 렌더 해상도 (높을수록 OCR 품질 ↑, 응답 시간/비용 ↑)

    Returns:
        페이지별 텍스트를 `\\n` 으로 합친 문자열. demo 모드면 빈 문자열.

    Raises:
        RuntimeError: vision 모드인데 API 키가 비어 있거나 호출이 실패한 경우.
        ValueError: PDF 파일이 깨졌거나 PyMuPDF가 못 여는 경우.
    """
    if REGISTRY_OCR_MODE == "demo":
        logger.info("registry_ocr: demo mode — returning empty text")
        return ""

    if not GOOGLE_VISION_API_KEY:
        raise RuntimeError("GOOGLE_VISION_API_KEY not set")

    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    pages_text: list[str] = []
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
            for page_index, page in enumerate(pdf):
                if page_index >= MAX_PAGES:
                    logger.warning(
                        "registry_ocr: MAX_PAGES=%d 초과, 이후 페이지 무시", MAX_PAGES
                    )
                    break
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                png_bytes = pixmap.tobytes("png")
                text = _call_vision(png_bytes)
                pages_text.append(text)
    except fitz.FileDataError as e:
        raise ValueError(f"PDF 파일을 열 수 없습니다: {e}") from e

    return "\n".join(pages_text).strip()


def _call_vision(image_bytes: bytes) -> str:
    """단일 이미지에 Vision DOCUMENT_TEXT_DETECTION 호출."""
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    payload = {
        "requests": [
            {
                "image": {"content": image_b64},
                "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
            }
        ]
    }

    try:
        resp = requests.post(
            f"{VISION_API_URL}?key={GOOGLE_VISION_API_KEY}",
            json=payload,
            timeout=DEFAULT_TIMEOUT,
        )
    except requests.RequestException as e:
        raise RuntimeError(f"Vision API 호출 실패 (네트워크): {e}") from e

    if resp.status_code != 200:
        # 키 오류·쿼터 초과 등은 body에 진단 정보가 있음. 단, 응답에 키 자체를 노출하지 말 것.
        snippet = (resp.text or "")[:200]
        raise RuntimeError(
            f"Vision API HTTP {resp.status_code}: {snippet}"
        )

    data = resp.json()
    error = (data.get("responses") or [{}])[0].get("error")
    if error:
        raise RuntimeError(f"Vision API error: {error}")

    annotation = (data.get("responses") or [{}])[0].get("fullTextAnnotation") or {}
    return (annotation.get("text") or "").strip()
