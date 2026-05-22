"""HUG 전세보증금 반환보증 가입 사전진단 (HF·SGI 제외)"""
from __future__ import annotations

from app.models.diagnoses_models import InsuranceAnalysis

# HUG 보증한도: 수도권 4.5억, 그 외 2.5억 (2024년 기준 MVP 근사치)
_HUG_LIMIT_METROPOLITAN = 450_000_000
_HUG_LIMIT_OTHER = 250_000_000
_HUG_JEONSE_RATIO_LIMIT = 0.90   # 주택가격의 90% 초과 시 가입 불가 기준


def run_hug_precheck(
    *,
    user_deposit: int,
    estimated_sale_price: int | None,
    senior_debt_amount: int | None,
    has_illegal_building: bool | None,
    has_right_restriction: bool | None,  # 압류·가처분·신탁 등
    has_move_in_report: bool | None,
    has_fixed_date: bool | None,
    contract_start_date: str | None,
    contract_end_date: str | None,
    balance_date: str | None,
    is_metropolitan: bool = True,
) -> InsuranceAnalysis:
    """
    is_metropolitan: 수도권(서울/경기/인천) 여부. 보증한도 산정에 사용.
    """
    missing: list[str] = []
    blocking_reasons: list[str] = []

    # ── 필수 정보 누락 체크 ───────────────────────────────────────
    if senior_debt_amount is None:
        missing.append("선순위채권 금액")
    if has_illegal_building is None:
        missing.append("위반건축물 여부")
    if has_right_restriction is None:
        missing.append("권리침해 여부 (압류·가처분·신탁)")
    if has_move_in_report is None:
        missing.append("전입신고 여부")
    if has_fixed_date is None:
        missing.append("확정일자 여부")
    if contract_start_date is None:
        missing.append("계약 시작일")
    if contract_end_date is None:
        missing.append("계약 종료일")
    if balance_date is None:
        missing.append("잔금일")
    if estimated_sale_price is None:
        missing.append("추정 주택가격")

    # ── 보증한도 추정 ────────────────────────────────────────────
    guarantee_limit = _HUG_LIMIT_METROPOLITAN if is_metropolitan else _HUG_LIMIT_OTHER
    limit_confidence: str = "low"

    # ── 즉시 차단 사유 확인 ───────────────────────────────────────
    if has_illegal_building:
        blocking_reasons.append("위반건축물: HUG 보증 대상에서 제외됩니다.")
    if has_right_restriction:
        blocking_reasons.append("압류·가처분·신탁등기: 권리 제한이 있으면 보증 가입이 어렵습니다.")

    # 전세가율 초과 체크 (estimated_sale_price 있을 때만)
    if estimated_sale_price and estimated_sale_price > 0:
        ratio = user_deposit / estimated_sale_price
        if ratio > _HUG_JEONSE_RATIO_LIMIT:
            blocking_reasons.append(
                f"전세가율 {ratio:.1%}: 주택가격 대비 전세보증금이 너무 높습니다 (기준 {_HUG_JEONSE_RATIO_LIMIT:.0%})."
            )
        # 보증한도 vs 보증금 비교
        if user_deposit > guarantee_limit:
            blocking_reasons.append(
                f"보증금 {user_deposit:,}원이 HUG 보증한도 "
                f"{guarantee_limit:,}원을 초과합니다."
            )
        limit_confidence = "medium"

    # 선순위채권 + 보증금 > 주택가격 90%
    if senior_debt_amount is not None and estimated_sale_price and estimated_sale_price > 0:
        total = senior_debt_amount + user_deposit
        if total / estimated_sale_price > _HUG_JEONSE_RATIO_LIMIT:
            blocking_reasons.append(
                f"선순위채권({senior_debt_amount:,}원) + 보증금 합계가 주택가격의 "
                f"{total/estimated_sale_price:.1%}입니다. 보증 가입 기준을 초과합니다."
            )
        limit_confidence = "high"

    # ── 결과 반환 ────────────────────────────────────────────────
    if blocking_reasons:
        return InsuranceAnalysis(
            eligible=False,
            grade="danger",
            conversational="문서 분석 결과 HUG 보증 가입을 어렵게 만드는 위험 신호가 있습니다.",
            details=blocking_reasons,
            blocking_reasons=blocking_reasons,
            estimated_guarantee_limit=guarantee_limit,
            guarantee_limit_confidence=limit_confidence,
        )

    if missing:
        return InsuranceAnalysis(
            eligible=None,
            grade="warning",
            conversational="HUG 가입 가능성 판단에 필요한 정보가 부족합니다. 아래 항목을 추가로 확인하세요.",
            details=missing,
            blocking_reasons=[],
            estimated_guarantee_limit=guarantee_limit,
            guarantee_limit_confidence=limit_confidence,
        )

    return InsuranceAnalysis(
        eligible=True,
        grade="safe",
        conversational=(
            f"입력 정보 기준 HUG 가입 가능성을 검토해볼 수 있습니다. "
            f"(수도권 보증한도 {guarantee_limit:,}원 기준)"
        ),
        details=["실제 가입 가능 여부는 HUG 공식 심사 결과에 따라 달라집니다."],
        blocking_reasons=[],
        estimated_guarantee_limit=guarantee_limit,
        guarantee_limit_confidence=limit_confidence,
    )
