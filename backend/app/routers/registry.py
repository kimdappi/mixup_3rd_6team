"""등기부등본 분석 API.

흐름:
    PDF 업로드 → OCR(Vision) → 파싱(룰) → 위험도 판정(룰) → 자연어 풀이(Solar)

OCR 호출은 sync I/O(`requests`)이므로 async 핸들러에서 `to_thread`로 감싸 이벤트 루프 보호.
"""
import asyncio
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services import solar_pro
from app.services.registry_ocr import extract_text_from_pdf_bytes
from app.services.registry_parser import parse_registry
from app.services.registry_rules import assess_registry_risk

logger = logging.getLogger(__name__)

MAX_PDF_BYTES = 10 * 1024 * 1024  # 10MB

router = APIRouter(prefix="/api/registry", tags=["registry"])


@router.post("/analyze")
async def analyze_registry(
    file: UploadFile = File(...),
    user_deposit_won: int = Form(...),
):
    """등기부등본 PDF 1장 + 전세금(원) → 위험도 분석."""
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(400, "PDF 파일만 업로드 가능합니다.")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise HTTPException(400, f"파일이 너무 큽니다 (최대 {MAX_PDF_BYTES // (1024*1024)}MB).")
    if len(pdf_bytes) == 0:
        raise HTTPException(400, "빈 파일입니다.")
    if user_deposit_won < 0:
        raise HTTPException(400, "전세금은 0 이상이어야 합니다.")

    # 1. OCR — sync 라이브러리(requests)라 이벤트 루프 보호 위해 to_thread
    try:
        ocr_text = await asyncio.to_thread(extract_text_from_pdf_bytes, pdf_bytes)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("registry OCR failed")
        raise HTTPException(502, f"OCR 처리 실패: {e}")

    # 2. 파싱 (룰 엔진)
    info = parse_registry(ocr_text)

    # 3. 위험도 판정 (룰 엔진)
    risk_result = assess_registry_risk(info, user_deposit_won)

    # 4. 자연어 풀이 (Solar, 실패 시 stub)
    summary = solar_pro.interpret_registry({
        "info": info.to_dict(),
        "risk_result": risk_result.to_dict(),
        "user_deposit_won": user_deposit_won,
    })

    # 원본 OCR 텍스트는 응답에 싣지 않는다 (개인정보 보호).
    return {
        "info": info.to_dict(),
        "risk": risk_result.to_dict(),
        "summary": summary,
    }
