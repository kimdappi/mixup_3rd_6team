"""registry_rules.assess_registry_risk 단위 테스트."""
from app.services.registry_parser import RegistryInfo
from app.services.registry_rules import assess_registry_risk


def _info(has_mortgage: bool, max_claim: int | None = None) -> RegistryInfo:
    """테스트용 RegistryInfo 헬퍼."""
    return RegistryInfo(
        address=None,
        building_area=None,
        owner_name=None,
        has_mortgage=has_mortgage,
        max_claim_amount=max_claim,
        mortgage_holder=None,
        raw_text_length=0,
    )


# ============================================================
# safe (근저당권 없음)
# ============================================================

def test_safe_when_no_mortgage():
    result = assess_registry_risk(_info(has_mortgage=False), 900_000_000)
    assert result.risk_level == "safe"
    assert result.risk_signal == "REGISTRY_NO_MORTGAGE"
    assert result.claim_to_deposit_ratio is None


# ============================================================
# very_high (claim >= deposit)
# ============================================================

def test_very_high_when_claim_equals_deposit():
    result = assess_registry_risk(_info(True, 1_300_000_000), 1_300_000_000)
    assert result.risk_level == "very_high"
    assert result.risk_signal == "REGISTRY_MORTGAGE_RATIO_VERY_HIGH"


def test_very_high_when_claim_exceeds_deposit():
    result = assess_registry_risk(_info(True, 1_500_000_000), 1_000_000_000)
    assert result.risk_level == "very_high"


# ============================================================
# high (0.7 <= ratio < 1.0)
# ============================================================

def test_high_at_90_percent():
    # 1.2B / 1.3B ≈ 0.923 → high
    result = assess_registry_risk(_info(True, 1_200_000_000), 1_300_000_000)
    assert result.risk_level == "high"
    assert 0.92 <= result.claim_to_deposit_ratio <= 0.93


def test_high_at_70_percent_boundary():
    # 7억 / 10억 = 0.7 (경계) → high
    result = assess_registry_risk(_info(True, 700_000_000), 1_000_000_000)
    assert result.risk_level == "high"


def test_just_below_70_percent_is_caution():
    # 6.99억 / 10억 = 0.699 → caution
    result = assess_registry_risk(_info(True, 699_000_000), 1_000_000_000)
    assert result.risk_level == "caution"


# ============================================================
# caution (0.4 <= ratio < 0.7) and (ratio < 0.4 + mortgage)
# ============================================================

def test_caution_at_40_percent_boundary():
    result = assess_registry_risk(_info(True, 400_000_000), 1_000_000_000)
    assert result.risk_level == "caution"


def test_caution_when_ratio_below_40_percent_but_mortgage_exists():
    # 근저당권은 있는데 비율 작음 → caution (룰 4단계 마지막 분기)
    result = assess_registry_risk(_info(True, 100_000_000), 1_000_000_000)
    assert result.risk_level == "caution"


# ============================================================
# 불확실 케이스 → caution
# ============================================================

def test_caution_when_amount_unknown():
    result = assess_registry_risk(_info(True, None), 900_000_000)
    assert result.risk_level == "caution"
    assert result.risk_signal == "REGISTRY_MORTGAGE_AMOUNT_UNKNOWN"
    assert result.claim_to_deposit_ratio is None


def test_caution_when_deposit_missing():
    result = assess_registry_risk(_info(True, 500_000_000), 0)
    assert result.risk_level == "caution"
    assert result.risk_signal == "REGISTRY_DEPOSIT_MISSING"


def test_caution_when_deposit_negative():
    result = assess_registry_risk(_info(True, 500_000_000), -1)
    assert result.risk_level == "caution"
