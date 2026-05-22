"""jeonse_rules.py 단위 테스트.

v2 명세서 11번 섹션 "test_jeonse_rules.py" 요구사항을 모두 커버한다.
판정 분기는 모두 `>=` 기준 (>=0.90 / >=0.80 / >=0.70).
"""
import pytest

from app.core.risk_signals import Severity
from app.services import jeonse_rules


# ============================================================
# 1. diagnose_jeonse_ratio 경계값
# ============================================================

@pytest.mark.parametrize("rate,expected", [
    (0.90, "very_high"),
    (0.899, "high"),
    (0.80, "high"),
    (0.799, "caution"),
    (0.70, "caution"),
    (0.699, "safe"),
])
def test_diagnose_jeonse_ratio_thresholds(rate, expected):
    """avg_sale=10억, user_deposit를 조절해 user_rate 정확히 맞춤."""
    avg_sale = 1_000_000_000.0
    user_deposit = int(round(avg_sale * rate))
    result = jeonse_rules.diagnose_jeonse_ratio(
        user_deposit=user_deposit,
        avg_jeonse=None,
        avg_sale=avg_sale,
    )
    assert result["risk_level"] == expected
    # user_jeonse_rate는 round 4자리, rate 자체와 거의 같아야 함
    assert result["user_jeonse_rate"] == pytest.approx(rate, abs=1e-3)


def test_diagnose_jeonse_ratio_no_sale_data():
    result = jeonse_rules.diagnose_jeonse_ratio(
        user_deposit=300_000_000,
        avg_jeonse=250_000_000.0,
        avg_sale=None,
    )
    assert result["risk_level"] is None
    assert result["user_jeonse_rate"] is None
    assert result["market_jeonse_rate"] is None


def test_diagnose_jeonse_ratio_zero_sale_treated_as_no_data():
    result = jeonse_rules.diagnose_jeonse_ratio(
        user_deposit=300_000_000,
        avg_jeonse=250_000_000.0,
        avg_sale=0,
    )
    assert result["risk_level"] is None
    assert result["user_jeonse_rate"] is None


def test_market_jeonse_rate_computed_when_both_present():
    result = jeonse_rules.diagnose_jeonse_ratio(
        user_deposit=300_000_000,
        avg_jeonse=400_000_000.0,
        avg_sale=500_000_000.0,
    )
    # market_rate = 400 / 500 = 0.8
    assert result["market_jeonse_rate"] == pytest.approx(0.8, abs=1e-4)
    # user_rate = 300 / 500 = 0.6 → safe
    assert result["user_jeonse_rate"] == pytest.approx(0.6, abs=1e-4)
    assert result["risk_level"] == "safe"


# ============================================================
# 2. build_jeonse_signals
# ============================================================

def test_safe_emits_no_signal():
    signals = jeonse_rules.build_jeonse_signals(
        user_jeonse_rate=0.6,
        risk_level="safe",
        confidence="medium",
    )
    assert signals == []


def test_none_risk_emits_no_sale_signal():
    """risk_level == None이면 NO_SALE_TRANSACTION_DATA 신호 1개."""
    signals = jeonse_rules.build_jeonse_signals(
        user_jeonse_rate=None,
        risk_level=None,
        confidence="medium",
    )
    assert len(signals) == 1
    assert signals[0].code == "NO_SALE_TRANSACTION_DATA"


def test_very_high_emits_critical_signal():
    """risk_level == 'very_high'면 JEONSE_RATIO_OVER_90 (severity=CRITICAL)."""
    signals = jeonse_rules.build_jeonse_signals(
        user_jeonse_rate=0.95,
        risk_level="very_high",
        confidence="high",
    )
    codes = {s.code for s in signals}
    assert "JEONSE_RATIO_OVER_90" in codes
    crit = next(s for s in signals if s.code == "JEONSE_RATIO_OVER_90")
    assert crit.severity == Severity.CRITICAL


def test_high_emits_warning_signal():
    signals = jeonse_rules.build_jeonse_signals(
        user_jeonse_rate=0.85,
        risk_level="high",
        confidence="medium",
    )
    codes = {s.code for s in signals}
    assert "JEONSE_RATIO_OVER_80" in codes
    sig = next(s for s in signals if s.code == "JEONSE_RATIO_OVER_80")
    assert sig.severity == Severity.WARNING


def test_caution_emits_caution_signal():
    signals = jeonse_rules.build_jeonse_signals(
        user_jeonse_rate=0.75,
        risk_level="caution",
        confidence="medium",
    )
    codes = {s.code for s in signals}
    assert "JEONSE_RATIO_OVER_70" in codes
    sig = next(s for s in signals if s.code == "JEONSE_RATIO_OVER_70")
    assert sig.severity == Severity.CAUTION


# ============================================================
# 3. diagnose 진입점 (NearbyFilterResult 기반)
# ============================================================

def test_diagnose_via_nearby_no_trade_data():
    """매매 거래가 없으면 risk_level=None, NO_SALE_TRANSACTION_DATA 신호."""
    from app.services.market_rules import NearbyFilterResult
    nearby = NearbyFilterResult(
        rent_deals=[
            {"deposit_won": 300_000_000, "apt_name": "X", "dong": "가양동", "area": 60}
        ],
        trade_deals=[],
        rent_scope="dong",
        trade_scope="gu_all",
    )
    result = jeonse_rules.diagnose(nearby, user_deposit=300_000_000, confidence="medium")
    assert result.risk_level is None
    assert result.user_jeonse_rate is None
    assert any(s.code == "NO_SALE_TRANSACTION_DATA" for s in result.signals)


def test_diagnose_via_nearby_very_high():
    """전세가율 95% 케이스 — JEONSE_RATIO_OVER_90 신호."""
    from app.services.market_rules import NearbyFilterResult
    nearby = NearbyFilterResult(
        rent_deals=[
            {"deposit_won": 950_000_000, "apt_name": "X", "dong": "가양동", "area": 60}
        ],
        trade_deals=[
            {"price_won": 1_000_000_000, "apt_name": "X", "dong": "가양동", "area": 60}
        ],
        rent_scope="complex",
        trade_scope="complex",
    )
    result = jeonse_rules.diagnose(nearby, user_deposit=950_000_000, confidence="high")
    assert result.risk_level == "very_high"
    assert result.user_jeonse_rate == pytest.approx(0.95, abs=1e-4)
    assert any(s.code == "JEONSE_RATIO_OVER_90" for s in result.signals)
