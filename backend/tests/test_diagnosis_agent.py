"""diagnosis_agent 통합 테스트.

실제 국토부 API는 호출하지 않고 MolitApiClient를 mock으로 주입한다.
"""
import pytest

from app.agents import diagnosis_agent
from app.models.diagnosis_models import QuickDiagnosisResponse


class FakeMolitClient:
    """국토부 응답 mock. fetch_recent_months만 호출되니 그것만 구현."""

    def __init__(self, rent_items=None, trade_items=None):
        self._rent = rent_items or []
        self._trade = trade_items or []

    async def fetch_recent_months(self, lawd_cd, months=6, kind="rent"):
        return self._rent if kind == "rent" else self._trade


def _rent(name, dong, area, deposit_man, monthly=0):
    return {
        "아파트": name, "법정동": dong, "전용면적": str(area),
        "보증금액": f"{deposit_man:,}", "월세금액": str(monthly),
    }


def _trade(name, dong, area, price_man, cancelled=""):
    return {
        "아파트": name, "법정동": dong, "전용면적": str(area),
        "거래금액": f"{price_man:,}", "해제여부": cancelled,
    }


@pytest.mark.asyncio
async def test_quick_diagnosis_full_response_schema():
    """전세·매매 풀이 충분한 경우 응답이 QuickDiagnosisResponse 스키마를 만족."""
    rent = [_rent("가양강변아파트", "가양동", 60, 30000) for _ in range(10)]
    trade = [_trade("가양강변아파트", "가양동", 60, 80000) for _ in range(5)]
    client = FakeMolitClient(rent_items=rent, trade_items=trade)

    raw = await diagnosis_agent.run_quick_diagnosis(
        address="서울특별시 강서구 가양동 1234 가양강변아파트",
        user_deposit=30000 * 10000,
        area_sqm=60,
        housing_type="apt",
        contract_stage="pre_contract",
        client=client,  # type: ignore[arg-type]
    )

    # pydantic 검증
    response = QuickDiagnosisResponse(**raw)
    assert response.address.startswith("서울특별시 강서구")
    assert response.market_analysis.scope == "complex"
    assert response.market_analysis.confidence == "high"
    assert response.market_analysis.deposit_status == "fair"
    assert response.disclaimer
    assert response.summary
    # 체크리스트는 베이스 4개를 반드시 포함 (안전한 매물도 풍성한 체크리스트)
    from app.services.checklist_rules import BASE_CHECKLIST
    for base_item in BASE_CHECKLIST:
        assert base_item in response.checklist, f"베이스 항목 누락: {base_item}"
    assert len(response.checklist) >= len(BASE_CHECKLIST)


@pytest.mark.asyncio
async def test_quick_diagnosis_missing_trade_data():
    """매매 데이터 없는 경우 — 전세가율 None, missing_information에 표시."""
    rent = [_rent("가양강변아파트", "가양동", 60, 30000) for _ in range(5)]
    client = FakeMolitClient(rent_items=rent, trade_items=[])

    raw = await diagnosis_agent.run_quick_diagnosis(
        address="서울특별시 강서구 가양동 가양강변아파트",
        user_deposit=30000 * 10000,
        area_sqm=60,
        housing_type="apt",
        contract_stage=None,
        client=client,  # type: ignore[arg-type]
    )

    response = QuickDiagnosisResponse(**raw)
    assert response.jeonse_ratio_analysis.user_jeonse_rate is None
    assert response.jeonse_ratio_analysis.risk_level is None
    assert any(
        "매매" in m for m in response.missing_information
    )
    assert any(
        s.code == "NO_SALE_TRANSACTION_DATA" for s in response.risk_signals
    )


@pytest.mark.asyncio
async def test_quick_diagnosis_gu_fallback_marked_in_missing_info():
    """단지·동 매칭 실패 시 missing_information에 표시."""
    # 동·아파트 모두 다른 데이터만 제공 → gu 또는 gu_all로 떨어짐
    rent = [_rent("X아파트", "다른동", 60, 30000) for _ in range(3)]
    client = FakeMolitClient(rent_items=rent, trade_items=[])

    raw = await diagnosis_agent.run_quick_diagnosis(
        address="서울특별시 강서구 가양동 가양강변아파트",
        user_deposit=30000 * 10000,
        area_sqm=60,
        housing_type="apt",
        contract_stage=None,
        client=client,  # type: ignore[arg-type]
    )

    response = QuickDiagnosisResponse(**raw)
    assert response.market_analysis.scope in ("gu", "gu_all")
    assert any(
        "폴백" in m or "시군구" in m for m in response.missing_information
    )


@pytest.mark.asyncio
async def test_quick_diagnosis_overpriced_triggers_signal():
    """보증금이 평균 대비 1.2배인 경우 OVERPRICED 시그널 발생."""
    rent = [_rent("가양강변아파트", "가양동", 60, 30000) for _ in range(5)]
    trade = [_trade("가양강변아파트", "가양동", 60, 80000) for _ in range(3)]
    client = FakeMolitClient(rent_items=rent, trade_items=trade)

    raw = await diagnosis_agent.run_quick_diagnosis(
        address="서울특별시 강서구 가양동 가양강변아파트",
        user_deposit=int(30000 * 10000 * 1.2),
        area_sqm=60,
        housing_type="apt",
        contract_stage=None,
        client=client,  # type: ignore[arg-type]
    )
    response = QuickDiagnosisResponse(**raw)
    assert response.market_analysis.deposit_status == "overpriced"
    codes = {s.code for s in response.risk_signals}
    assert "MARKET_RENT_OVERPRICED" in codes


@pytest.mark.asyncio
async def test_quick_diagnosis_high_jeonse_ratio_critical_signal():
    """전세가율 90%↑ 케이스 — CRITICAL 시그널 발생."""
    rent = [_rent("가양강변아파트", "가양동", 60, 30000) for _ in range(5)]
    trade = [_trade("가양강변아파트", "가양동", 60, 32000) for _ in range(3)]
    client = FakeMolitClient(rent_items=rent, trade_items=trade)

    raw = await diagnosis_agent.run_quick_diagnosis(
        address="서울특별시 강서구 가양동 가양강변아파트",
        user_deposit=30000 * 10000,
        area_sqm=60,
        housing_type="apt",
        contract_stage=None,
        client=client,  # type: ignore[arg-type]
    )
    response = QuickDiagnosisResponse(**raw)
    assert response.jeonse_ratio_analysis.risk_level == "very_high"
    codes = {s.code for s in response.risk_signals}
    assert "JEONSE_RATIO_OVER_90" in codes


@pytest.mark.asyncio
async def test_quick_diagnosis_invalid_address_raises():
    client = FakeMolitClient()
    with pytest.raises(ValueError):
        await diagnosis_agent.run_quick_diagnosis(
            address="알 수 없는시 알 수 없구",
            user_deposit=300_000_000,
            area_sqm=60,
            housing_type="apt",
            contract_stage=None,
            client=client,  # type: ignore[arg-type]
        )
