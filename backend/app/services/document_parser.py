"""
업로드된 문서 텍스트에서 구조화된 필드를 추출한다.
정규식 기반 룰엔진 방식. OCR 원문 전체를 LLM에 넘기지 않는다.
"""
from __future__ import annotations

import re

from app.models.diagnoses_models import ParsedContract, ParsedLedger, ParsedRegistry


# ── 공통 유틸 ─────────────────────────────────────────────────────

def _find(pattern: str, text: str, flags: int = 0) -> str | None:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def _money_to_won(raw: str) -> int | None:
    """'150,000,000' 또는 '1억5천만' 같은 표현을 원으로 변환"""
    cleaned = raw.replace(",", "").replace(" ", "")
    # 순수 숫자
    if cleaned.isdigit():
        v = int(cleaned)
        # 만원 단위로 입력된 경우 (5자리 이하 & 값이 너무 작으면 만원 단위로 간주)
        return v if v >= 10_000_000 else v * 10_000
    return None


# ── 등기부등본 파싱 ───────────────────────────────────────────────

_MORTGAGE_PAT = re.compile(
    r"채권최고액\s*금?\s*([\d,]+)\s*원",
    re.IGNORECASE,
)
_ISSUE_DATE_PAT = re.compile(
    r"발급일시?\s*[:：]\s*(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})",
)
_OWNER_PAT = re.compile(
    r"(?:소유자|성\s*명)\s+([가-힣]{2,5})\b",
)
_ADDRESS_PAT = re.compile(
    r"(?:부동산의\s*표시|소재지번|도로명주소)\s*[:：]?\s*([^\n\r]+)",
)


def parse_registry(text: str) -> ParsedRegistry:
    mortgage_total = 0
    mortgage_details: list[str] = []
    for m in _MORTGAGE_PAT.finditer(text):
        raw = m.group(1)
        won = _money_to_won(raw)
        if won:
            mortgage_total += won
            mortgage_details.append(f"채권최고액 {raw}원")

    return ParsedRegistry(
        owner=_find(r"(?:소유자|성\s*명)\s+([가-힣]{2,5})\b", text),
        address=_find(r"(?:부동산의\s*표시|소재지번|도로명주소)\s*[:：]?\s*([^\n\r]+)", text),
        issue_date=_find(r"발급일시?\s*[:：]\s*(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})", text),
        mortgage_total=mortgage_total,
        mortgage_details=mortgage_details,
        has_trust="신탁" in text,
        has_seizure="압류" in text,
        has_provisional_seizure="가압류" in text,
        has_provisional_disposition="가처분" in text,
        has_auction="경매개시결정" in text,
        has_lease_right=bool(re.search(r"전세권|임차권\s*등기", text)),
        raw_text=text,
    )


# ── 건축물대장 파싱 ───────────────────────────────────────────────

def parse_ledger(text: str) -> ParsedLedger:
    area_raw = _find(r"전용면적\s*([\d.]+)\s*㎡?", text)
    return ParsedLedger(
        address=_find(r"(?:대지위치|소재지)\s*[:：]?\s*([^\n\r]+)", text),
        exclusive_area=float(area_raw) if area_raw else None,
        main_purpose=_find(r"주용도\s*[:：]?\s*([가-힣·\s]+)", text),
        approval_date=_find(r"사용승인일\s*[:：]?\s*(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})", text),
        has_illegal_building="위반건축물" in text,
        ledger_type=_find(r"(일반건축물대장|집합건축물대장|총괄표제부)", text),
        raw_text=text,
    )


# ── 임대차계약서 파싱 ─────────────────────────────────────────────

def _parse_deposit(text: str) -> int | None:
    raw = _find(r"보증금\s*금?\s*([\d,]+)\s*원", text)
    if raw:
        return _money_to_won(raw)
    # '금 2억5천만원' 형태
    m = re.search(r"금\s*([\d억천만]+)\s*원", text)
    if m:
        return _korean_money_to_won(m.group(1))
    return None


def _korean_money_to_won(s: str) -> int | None:
    """'2억5천만' → 250000000"""
    try:
        total = 0
        s = s.replace(" ", "")
        if "억" in s:
            parts = s.split("억")
            total += int(parts[0]) * 100_000_000
            s = parts[1]
        if "천만" in s:
            parts = s.split("천만")
            total += int(parts[0] or "1") * 10_000_000
            s = parts[1]
        if "만" in s:
            parts = s.split("만")
            total += int(parts[0] or "1") * 10_000
            s = parts[1]
        if s.isdigit():
            total += int(s)
        return total if total > 0 else None
    except Exception:
        return None


def parse_contract(text: str) -> ParsedContract:
    return ParsedContract(
        address=_find(r"(?:임대차\s*목적물|소재지|주\s*소)\s*[:：]?\s*([^\n\r]+)", text),
        landlord=_find(r"임대인\s*[:：]?\s*([가-힣]{2,5})\b", text),
        tenant=_find(r"임차인\s*[:：]?\s*([가-힣]{2,5})\b", text),
        deposit=_parse_deposit(text),
        contract_start=_find(
            r"(?:계약기간|임대기간).*?(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})", text
        ),
        contract_end=_find(
            r"(?:계약기간|임대기간).*?\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}.*?~.*?(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})",
            text,
        ),
        balance_date=_find(
            r"잔금\s*[:：]?\s*(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})", text
        ),
        has_special_terms=bool(re.search(r"특약|특수\s*조건", text)),
        has_bank_account=bool(re.search(r"계좌|통장|은행|이체", text)),
        raw_text=text,
    )
