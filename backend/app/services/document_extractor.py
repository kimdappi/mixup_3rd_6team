"""
문서 텍스트 추출 모듈.
PDF → pdfplumber 우선, 실패 시 raw bytes decode fallback.
이미지 PDF는 현재 local OCR 없이 빈 텍스트 반환 (OCR_PROVIDER 확장 예정).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExtractedDocument:
    document_type: str   # registry | building_ledger | contract | unknown
    text: str
    extraction_method: str = "text_decode"   # pdf | text_decode | ocr
    page_count: int = 0
    warnings: list[str] = field(default_factory=list)


def _classify_document_type(filename: str) -> str:
    lower = filename.lower()
    if any(k in lower for k in ("registry", "등기", "등기부")):
        return "registry"
    if any(k in lower for k in ("ledger", "건축물", "대장")):
        return "building_ledger"
    if any(k in lower for k in ("contract", "계약", "임대차")):
        return "contract"
    return "unknown"


def _extract_pdf(content: bytes) -> tuple[str, int, str]:
    """pdfplumber로 PDF 텍스트 추출. 반환: (text, page_count, method)"""
    try:
        import pdfplumber  # type: ignore
        import io

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
            text = "\n".join(pages).strip()
            return text, len(pdf.pages), "pdf"
    except ImportError:
        logger.warning("pdfplumber 미설치 — pip install pdfplumber 후 PDF 추출 가능")
        return "", 0, "pdf_unavailable"
    except Exception as exc:
        logger.warning("PDF 텍스트 추출 실패: %s", exc)
        return "", 0, "pdf_error"


def extract_text_from_upload(filename: str, content: bytes) -> ExtractedDocument:
    """
    업로드된 파일에서 텍스트를 추출한다.
    - .pdf: pdfplumber 시도 → fallback text decode
    - 나머지: UTF-8 decode (CP949 fallback)
    """
    doc_type = _classify_document_type(filename)
    warnings: list[str] = []

    if filename.lower().endswith(".pdf"):
        text, pages, method = _extract_pdf(content)
        if not text:
            # PDF 추출 실패 시 raw bytes를 텍스트로 시도 (텍스트 기반 PDF)
            text = content.decode("utf-8", errors="ignore")
            method = "text_decode_fallback"
            warnings.append("PDF 전용 추출 실패 — 텍스트 직접 디코딩으로 대체했습니다.")
        return ExtractedDocument(
            document_type=doc_type,
            text=text,
            extraction_method=method,
            page_count=pages,
            warnings=warnings,
        )

    # 일반 텍스트 파일 (txt, hwp 등)
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            text = content.decode(enc)
            return ExtractedDocument(
                document_type=doc_type,
                text=text,
                extraction_method="text_decode",
            )
        except UnicodeDecodeError:
            continue

    # 최후 fallback
    text = content.decode("utf-8", errors="replace")
    warnings.append("인코딩을 인식할 수 없어 일부 문자가 손실되었습니다.")
    return ExtractedDocument(
        document_type=doc_type,
        text=text,
        extraction_method="text_decode",
        warnings=warnings,
    )
