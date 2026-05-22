"""계약 단계별 체크리스트 생성 — 구조화 출력 + 단순 목록(프론트 호환)"""
from __future__ import annotations

from app.models.diagnoses_models import RiskSignal, StructuredChecklist

# ── 정적 기본 항목 ────────────────────────────────────────────────
_STAGE_URGENT: dict[str, list[str]] = {
    "before_visit": ["주변 실거래가를 조회하세요 (국토부 실거래가 공개시스템)."],
    "before_contract": [
        "최신 등기부등본(발급일 1개월 이내)을 확인하세요.",
        "계약서 주소와 등기부 주소가 정확히 일치하는지 확인하세요.",
        "임대인 신분증과 등기부 소유자 명의가 일치하는지 확인하세요.",
    ],
    "before_balance": [
        "잔금 당일 오전 다시 한번 등기부등본을 발급해 확인하세요.",
        "전입신고와 확정일자를 잔금일 당일 처리하세요.",
    ],
    "after_move_in": [
        "전입신고·확정일자 완료 여부를 확인하세요.",
        "HUG 전세보증금 반환보증 신청 여부를 확인하세요.",
    ],
}

_STAGE_BEFORE_CONTRACT: dict[str, list[str]] = {
    "before_visit": [
        "건축물대장을 발급받아 위반건축물 여부를 확인하세요.",
        "임대인 미납 국세·지방세 열람을 신청하세요.",
    ],
    "before_contract": [
        "건축물대장 용도가 주거용(아파트·다세대·연립)인지 확인하세요.",
        "임대인 미납 국세 열람 동의를 임대인에게 요청하세요.",
    ],
    "before_balance": [
        "잔금 전 HUG 전세보증보험 가입 접수를 완료하세요.",
    ],
    "after_move_in": [
        "보증보험 가입 완료 상태를 HUG 앱에서 확인하세요.",
    ],
}


def _risk_based_items(codes: set[str]) -> list[str]:
    items: list[str] = []
    if "JEONSE_RATIO_OVER_80" in codes or "JEONSE_RATIO_OVER_90" in codes:
        items.append("HUG 전세보증금 반환보증 가입 가능 여부를 계약 전 확인하세요.")
    if "MORTGAGE_FOUND" in codes:
        items.append("근저당 말소 조건(잔금일 전 말소)을 계약서 특약에 반드시 명시하세요.")
    if "TRUST_REGISTRATION_FOUND" in codes:
        items.append("신탁원부를 발급받아 임대인의 임대 권한을 확인하세요.")
    if "SEIZURE_FOUND" in codes or "AUCTION_START_FOUND" in codes:
        items.append("압류·경매 등 권리 제한이 있는 매물입니다. 법률 전문가 상담을 강력히 권합니다.")
    if "OWNER_LANDLORD_MISMATCH" in codes:
        items.append("임대인과 등기부 소유자가 다릅니다. 위임장 원본을 반드시 확인하세요.")
    if "ILLEGAL_BUILDING_FOUND" in codes:
        items.append("위반건축물 내용을 확인하고, HUG 보증 가입 가능 여부를 별도 문의하세요.")
    if "OLD_REGISTRY_DOCUMENT" in codes:
        items.append("제출된 등기부등본이 오래되었습니다. 최신 등기부를 다시 발급받으세요.")
    return items


def build_checklist(
    contract_stage: str,
    risk_signals: list[RiskSignal],
    missing_information: list[str],
) -> list[str]:
    """단순 list[str] — 프론트엔드 호환용"""
    structured = build_structured_checklist(contract_stage, risk_signals, missing_information)
    flat: list[str] = []
    flat.extend(structured.urgent)
    flat.extend(structured.before_contract)
    flat.extend(structured.risk_based)
    flat.extend(f"{doc} 정보를 추가로 확인하세요." for doc in structured.missing_documents)
    return flat


def build_structured_checklist(
    contract_stage: str,
    risk_signals: list[RiskSignal],
    missing_information: list[str],
) -> StructuredChecklist:
    """구조화 체크리스트 반환"""
    codes = {s.code for s in risk_signals}
    stage = contract_stage if contract_stage in _STAGE_URGENT else "before_contract"

    return StructuredChecklist(
        urgent=list(_STAGE_URGENT.get(stage, [])),
        before_contract=list(_STAGE_BEFORE_CONTRACT.get(stage, [])),
        missing_documents=list(missing_information),
        risk_based=_risk_based_items(codes),
    )
