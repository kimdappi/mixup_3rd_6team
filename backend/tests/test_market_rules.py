"""market_rules.py 단위 테스트.

v2 명세서 11번 섹션 "test_market_rules.py" 요구사항을 모두 커버한다.
부등호 방향(`> 1.15` vs `>= 0.90`)을 특히 정확히 검증한다.
"""
import pytest

from app.services import address_parser, market_rules


# ============================================================
# 헬퍼
# ============================================================

def _rent_raw(name, dong, area, deposit_man, monthly=0):
    """국토부 전세 응답 한 건을 흉내내는 raw dict."""
    return {
        "아파트": name,
        "법정동": dong,
        "전용면적": str(area),
        "보증금액": f"{deposit_man:,}",
        "월세금액": str(monthly),
    }


def _trade_raw(name, dong, area, price_man, cancelled=""):
    """국토부 매매 응답 한 건을 흉내내는 raw dict."""
    return {
        "아파트": name,
        "법정동": dong,
        "전용면적": str(area),
        "거래금액": f"{price_man:,}",
        "해제여부": cancelled,
    }


def _parsed_gangseo(dong="가양동", apt_prefix="가양강변"):
    """address_parser.parse 결과를 흉내내는 헬퍼."""
    return address_parser.ParsedAddress(
        raw="서울특별시 강서구 가양동 가양강변아파트",
        normalized="서울특별시 강서구 가양동 가양강변아파트",
        lawd_cd="11500",
        sigungu="서울특별시 강서구",
        dong=dong,
        apt_prefix=apt_prefix,
    )


def _make_nearby(rent_n=0, trade_n=0, rent_scope="dong", trade_scope="dong"):
    """판정 함수 직접 검증용. count와 scope만 의미가 있다."""
    rent_deals = [
        {"apt_name": "X", "dong": "가양동", "area": 60.0, "deposit_won": 300_000_000}
        for _ in range(rent_n)
    ]
    trade_deals = [
        {"apt_name": "X", "dong": "가양동", "area": 60.0, "price_won": 800_000_000}
        for _ in range(trade_n)
    ]
    return market_rules.NearbyFilterResult(
        rent_deals=rent_deals,
        trade_deals=trade_deals,
        rent_scope=rent_scope,
        trade_scope=trade_scope,
    )


# ============================================================
# 1. 데이터 정규화
# ============================================================

def test_normalize_rent_deal_korean_fields():
    raw = {
        "아파트": "가양강변아파트",
        "법정동": "가양동",
        "전용면적": "59.92",
        "보증금액": "23,000",
        "월세금액": "0",
    }
    out = market_rules.normalize_rent_deal(raw)
    assert out is not None
    assert out["apt_name"] == "가양강변아파트"
    assert out["dong"] == "가양동"
    assert out["area"] == pytest.approx(59.92)
    # 23,000 만원 → 230,000,000 원
    assert out["deposit_won"] == 230_000_000


def test_normalize_rent_deal_english_fields():
    raw = {
        "aptNm": "Sample",
        "umdNm": "가양동",
        "excluUseAr": 84.5,
        "deposit": "30,000",
        "monthlyRent": 0,
    }
    out = market_rules.normalize_rent_deal(raw)
    assert out is not None
    assert out["apt_name"] == "Sample"
    assert out["deposit_won"] == 300_000_000


def test_normalize_rent_deal_excludes_monthly_rent():
    """월세금액 != 0이면 None."""
    raw = _rent_raw("X", "가양동", 60, 5000, monthly=50)
    assert market_rules.normalize_rent_deal(raw) is None


def test_normalize_trade_deal_excludes_cancelled():
    """해제여부 == 'Y' 면 None."""
    raw = _trade_raw("X", "가양동", 60, 80000, cancelled="Y")
    assert market_rules.normalize_trade_deal(raw) is None


@pytest.mark.parametrize("cancelled", ["", None, "N", "n"])
def test_normalize_trade_deal_accepts_empty_none_n(cancelled):
    raw = {
        "아파트": "X", "법정동": "가양동", "전용면적": "60",
        "거래금액": "80,000",
    }
    if cancelled is not None:
        raw["해제여부"] = cancelled
    out = market_rules.normalize_trade_deal(raw)
    assert out is not None
    assert out["price_won"] == 800_000_000


# ============================================================
# 2. 면적 ±20% 경계값
# ============================================================

def test_area_match_boundary_inclusive():
    """user_area=45 기준: 36, 54는 통과(=20% 경계)."""
    assert market_rules._is_area_match(36.0, 45.0) is True
    assert market_rules._is_area_match(54.0, 45.0) is True


def test_area_match_boundary_exclusive():
    """user_area=45 기준: 35.9, 54.1은 제외(>20%)."""
    assert market_rules._is_area_match(35.9, 45.0) is False
    assert market_rules._is_area_match(54.1, 45.0) is False


# ============================================================
# 3. 계층적 필터
# ============================================================

def test_filter_complex_when_three_or_more():
    """complex 단계 3건 이상이면 채택."""
    parsed = _parsed_gangseo()
    rent = [
        _rent_raw("가양강변아파트", "가양동", 60, 30000),
        _rent_raw("가양강변아파트", "가양동", 60, 31000),
        _rent_raw("가양강변아파트", "가양동", 60, 32000),
        _rent_raw("다른아파트", "가양동", 60, 25000),
        _rent_raw("타지역", "다른동", 60, 40000),
    ]
    nearby = market_rules.filter_nearby(rent, [], parsed, area_sqm=60)
    assert nearby.rent_scope == "complex"
    assert nearby.jeonse_count == 3


def test_falls_back_to_dong_when_complex_has_two():
    """complex 2건이면 dong으로 폴백."""
    parsed = _parsed_gangseo()
    rent = [
        _rent_raw("가양강변아파트", "가양동", 60, 30000),  # complex 1
        _rent_raw("가양강변아파트", "가양동", 60, 31000),  # complex 2 (3건 미달)
        _rent_raw("다른A", "가양동", 60, 32000),
        _rent_raw("다른B", "가양동", 60, 33000),
        _rent_raw("X", "발산동", 60, 40000),
    ]
    nearby = market_rules.filter_nearby(rent, [], parsed, area_sqm=60)
    assert nearby.rent_scope == "dong"
    assert nearby.jeonse_count == 4


def test_rent_complex_trade_gu_independent_scope():
    """전세는 complex, 매매는 gu로 서로 다른 scope가 가능."""
    parsed = _parsed_gangseo()
    rent = [
        _rent_raw("가양강변아파트", "가양동", 60, 30000),
        _rent_raw("가양강변아파트", "가양동", 60, 31000),
        _rent_raw("가양강변아파트", "가양동", 60, 32000),
    ]
    # 매매는 다른 동의 다른 아파트만 → complex/dong 실패, gu에서 채택
    trade = [
        _trade_raw("X", "다른동", 60, 80000),
        _trade_raw("Y", "다른동", 60, 81000),
        _trade_raw("Z", "다른동", 60, 82000),
    ]
    nearby = market_rules.filter_nearby(rent, trade, parsed, area_sqm=60)
    assert nearby.rent_scope == "complex"
    assert nearby.trade_scope == "gu"


# ============================================================
# 4. diagnose_deposit_status 경계값
# ============================================================

@pytest.mark.parametrize("ratio,expected", [
    (1.16, "overpriced"),
    (1.15, "slightly_high"),   # > 1.15 가 아니므로 overpriced 아님
    (1.06, "slightly_high"),
    (1.05, "fair"),            # > 1.05 가 아니므로 slightly_high 아님
    (0.90, "fair"),
    (0.89, "cheap"),
    (0.75, "cheap"),
    (0.74, "suspicious"),
])
def test_diagnose_deposit_status_thresholds(ratio, expected):
    avg_jeonse = 300_000_000.0
    user_deposit = int(round(avg_jeonse * ratio))
    actual_ratio, status = market_rules.diagnose_deposit_status(
        user_deposit, avg_jeonse
    )
    assert status == expected
    assert actual_ratio == pytest.approx(ratio, abs=1e-6)


def test_diagnose_deposit_status_none_avg():
    assert market_rules.diagnose_deposit_status(300_000_000, None) == (None, None)
    assert market_rules.diagnose_deposit_status(300_000_000, 0) == (None, None)


# ============================================================
# 5. judge_confidence
# ============================================================

def test_confidence_high_at_dong_with_many_deals():
    nearby = _make_nearby(rent_n=10, trade_n=5, rent_scope="dong")
    conf, _ = market_rules.judge_confidence(nearby)
    assert conf == "high"


def test_confidence_not_high_when_scope_is_gu():
    """전세 10, 매매 5라도 scope=gu이면 high가 아니어야 한다."""
    nearby = _make_nearby(rent_n=10, trade_n=5, rent_scope="gu")
    conf, _ = market_rules.judge_confidence(nearby)
    assert conf != "high"
    # 표본은 충분하므로 medium으로 떨어진다.
    assert conf == "medium"


def test_confidence_medium_at_dong_with_minimum_samples():
    nearby = _make_nearby(rent_n=5, trade_n=3, rent_scope="dong")
    conf, _ = market_rules.judge_confidence(nearby)
    assert conf == "medium"


def test_confidence_medium_at_complex_with_only_three_rent():
    nearby = _make_nearby(rent_n=3, trade_n=0, rent_scope="complex")
    conf, _ = market_rules.judge_confidence(nearby)
    assert conf == "medium"


def test_confidence_low_at_gu_all_with_few_deals():
    nearby = _make_nearby(rent_n=2, trade_n=0, rent_scope="gu_all")
    conf, _ = market_rules.judge_confidence(nearby)
    assert conf == "low"


# ============================================================
# 6. build_market_signals
# ============================================================

def test_fair_status_emits_no_market_signal():
    """fair는 시세 신호 없음 (confidence가 low가 아니어야 LOW 신호도 없음)."""
    signals = market_rules.build_market_signals(
        deposit_ratio=1.0,
        deposit_status="fair",
        avg_jeonse=300_000_000.0,
        confidence="medium",
    )
    codes = {s.code for s in signals}
    assert "MARKET_RENT_OVERPRICED" not in codes
    assert "MARKET_RENT_SLIGHTLY_HIGH" not in codes
    assert "MARKET_RENT_CHEAP" not in codes
    assert "MARKET_RENT_SUSPICIOUSLY_LOW" not in codes
    assert "LOW_MARKET_CONFIDENCE" not in codes
    assert signals == []


def test_overpriced_status_emits_overpriced_signal():
    signals = market_rules.build_market_signals(
        deposit_ratio=1.20,
        deposit_status="overpriced",
        avg_jeonse=300_000_000.0,
        confidence="high",
    )
    codes = {s.code for s in signals}
    assert "MARKET_RENT_OVERPRICED" in codes


def test_low_confidence_emits_additional_signal():
    """confidence == 'low'면 LOW_MARKET_CONFIDENCE 신호가 추가된다."""
    signals = market_rules.build_market_signals(
        deposit_ratio=None,
        deposit_status=None,
        avg_jeonse=None,
        confidence="low",
    )
    codes = {s.code for s in signals}
    assert "LOW_MARKET_CONFIDENCE" in codes
