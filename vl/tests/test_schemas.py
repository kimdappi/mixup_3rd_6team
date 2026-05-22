from app.models.schemas import QuickDiagnosisRequest, RiskSignal


def test_quick_request_uses_frontend_field_names():
    request = QuickDiagnosisRequest(
        address="서울 강서구 가양동 강변아파트",
        area_sqm=50.0,
        user_deposit=250_000_000,
        housing_type="apartment",
        contract_stage="before_contract",
    )

    assert request.area_sqm == 50.0
    assert request.user_deposit == 250_000_000


def test_risk_signal_has_traceable_fields():
    signal = RiskSignal(
        code="JEONSE_RATIO_OVER_80",
        title="전세가율 높음",
        severity="high",
        confidence="medium",
        evidence="전세가율 83%",
        source="market_diagnosis",
        recommended_action="HUG 가입 가능 여부를 확인하세요.",
    )

    assert signal.code == "JEONSE_RATIO_OVER_80"
    assert signal.source == "market_diagnosis"
