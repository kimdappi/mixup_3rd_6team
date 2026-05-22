"""
문서 교차검증 모듈.
사용자 입력 ↔ 등기부 ↔ 건축물대장 ↔ 계약서 간 불일치를 탐지한다.
"""
from __future__ import annotations

import re
from datetime import date

from app.models.diagnoses_models import (
    ParsedContract,
    ParsedLedger,
    ParsedRegistry,
    RiskSignal,
)


def _address_overlap(a: str | None, b: str | None, min_chars: int = 6) -> bool:
    """두 주소가 충분히 겹치는지 확인 (완전 일치 불필요)"""
    if not a or not b:
        return True  # 정보 없으면 경고 생략
    a_clean = re.sub(r"\s+", "", a)
    b_clean = re.sub(r"\s+", "", b)
    overlap = sum(c in b_clean for c in a_clean)
    return overlap >= min_chars


def _days_since(date_str: str) -> int | None:
    """'YYYY.MM.DD' 형태 문자열을 오늘 기준 경과일로 변환"""
    for fmt in ("%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            d = date.fromisoformat(date_str.replace(".", "-").replace("/", "-"))
            return (date.today() - d).days
        except ValueError:
            pass
    return None


def crosscheck_documents(
    *,
    user_address: str,
    user_deposit: int,
    user_area_sqm: float,
    user_housing_type: str,
    registry: ParsedRegistry | None,
    ledger: ParsedLedger | None,
    contract: ParsedContract | None,
) -> list[RiskSignal]:
    signals: list[RiskSignal] = []

    # ── 1. 주소 교차검증 ─────────────────────────────────────────
    if registry and registry.address:
        if not _address_overlap(user_address, registry.address):
            signals.append(RiskSignal(
                code="ADDRESS_MISMATCH",
                title="주소 불일치 (입력 vs 등기부)",
                severity="high",
                confidence="medium",
                evidence=f"입력: {user_address[:30]} / 등기부: {registry.address[:30]}",
                source="document_crosscheck",
                recommended_action="계약서와 등기부의 부동산 표시 주소를 직접 비교하세요.",
            ))

    if contract and contract.address and registry and registry.address:
        if not _address_overlap(contract.address, registry.address):
            signals.append(RiskSignal(
                code="ADDRESS_MISMATCH",
                title="주소 불일치 (계약서 vs 등기부)",
                severity="high",
                confidence="medium",
                evidence=f"계약서: {contract.address[:30]} / 등기부: {registry.address[:30]}",
                source="document_crosscheck",
                recommended_action="계약 체결 전 두 주소가 동일한지 확인하세요.",
            ))

    # ── 2. 임대인 ↔ 소유자 불일치 ───────────────────────────────
    if registry and registry.owner and contract and contract.landlord:
        if registry.owner.strip() != contract.landlord.strip():
            signals.append(RiskSignal(
                code="OWNER_LANDLORD_MISMATCH",
                title="임대인·소유자 불일치",
                severity="high",
                confidence="medium",
                evidence=f"계약서 임대인: {contract.landlord} / 등기부 소유자: {registry.owner}",
                source="document_crosscheck",
                recommended_action="대리인 계약 여부와 위임장을 반드시 확인하세요.",
            ))

    # ── 3. 보증금 불일치 ─────────────────────────────────────────
    if contract and contract.deposit is not None:
        diff_ratio = abs(contract.deposit - user_deposit) / max(user_deposit, 1)
        if diff_ratio > 0.05:  # 5% 이상 차이
            signals.append(RiskSignal(
                code="DEPOSIT_MISMATCH",
                title="보증금 불일치 (입력 vs 계약서)",
                severity="medium",
                confidence="medium",
                evidence=(
                    f"입력 보증금: {user_deposit:,}원 / "
                    f"계약서 보증금: {contract.deposit:,}원"
                ),
                source="document_crosscheck",
                recommended_action="계약서의 보증금 금액을 다시 확인하세요.",
            ))

    # ── 4. 면적 불일치 ───────────────────────────────────────────
    if ledger and ledger.exclusive_area is not None:
        diff_ratio = abs(ledger.exclusive_area - user_area_sqm) / max(user_area_sqm, 1)
        if diff_ratio > 0.10:  # 10% 이상 차이
            signals.append(RiskSignal(
                code="AREA_MISMATCH",
                title="전용면적 불일치",
                severity="low",
                confidence="medium",
                evidence=(
                    f"입력 면적: {user_area_sqm}㎡ / "
                    f"건축물대장: {ledger.exclusive_area}㎡"
                ),
                source="document_crosscheck",
                recommended_action="실제 전용면적을 건축물대장 기준으로 재확인하세요.",
            ))

    # ── 5. 주택 유형 불일치 ──────────────────────────────────────
    if ledger and ledger.main_purpose:
        purpose = ledger.main_purpose
        is_residential = any(k in purpose for k in ("아파트", "공동주택", "단독주택", "다세대", "연립", "오피스텔"))
        if user_housing_type == "apartment" and "아파트" not in purpose and "공동주택" not in purpose:
            signals.append(RiskSignal(
                code="NON_RESIDENTIAL_USAGE_FOUND",
                title="주택 용도 불일치",
                severity="medium",
                confidence="medium",
                evidence=f"건축물대장 주용도: {purpose}",
                source="document_crosscheck",
                recommended_action="실제 용도가 주거용인지 건축물대장을 통해 확인하세요.",
            ))

    # ── 6. 위반건축물 ─────────────────────────────────────────────
    if ledger and ledger.has_illegal_building:
        signals.append(RiskSignal(
            code="ILLEGAL_BUILDING_FOUND",
            title="위반건축물 확인",
            severity="high",
            confidence="high",
            evidence="건축물대장에 위반건축물 표시가 있습니다.",
            source="document_crosscheck",
            recommended_action="위반 내용을 확인하고 HUG 보증 가입 가능 여부를 별도로 확인하세요.",
        ))

    # ── 7. 등기부 발급일 오래됨 ──────────────────────────────────
    if registry and registry.issue_date:
        days = _days_since(registry.issue_date)
        if days is not None and days > 30:
            signals.append(RiskSignal(
                code="OLD_REGISTRY_DOCUMENT",
                title="등기부 발급일 오래됨",
                severity="low",
                confidence="high",
                evidence=f"발급일: {registry.issue_date} ({days}일 경과)",
                source="document_crosscheck",
                recommended_action="계약 당일 또는 잔금일에 최신 등기부를 다시 발급받아 확인하세요.",
            ))

    # ── 8. 경매개시결정 ──────────────────────────────────────────
    if registry and registry.has_auction:
        signals.append(RiskSignal(
            code="AUCTION_START_FOUND",
            title="경매개시결정 등기 발견",
            severity="critical",
            confidence="high",
            evidence="등기부에 경매개시결정 키워드가 있습니다.",
            source="document_crosscheck",
            recommended_action="계약을 즉시 보류하고 법률 전문가와 상담하세요.",
        ))

    return signals
