import pytest

from app.agents.saju_agent import _calculate_score, _grade_from_score
from app.core.oheng_mapping import is_valid_match
from app.services import saju_calc


def test_grade_from_score():
    assert _grade_from_score(85) == "아주 좋음"
    assert _grade_from_score(70) == "양호"
    assert _grade_from_score(50) == "보통"


def test_calculate_score_with_water_match():
    """오행별 place 정보 dict 형식으로 점수 계산되는지."""
    nearby = {
        "水": {
            "place_name": "한강시민공원 망원지구",
            "distance_m": 500,
            "category": "여행 > 관광,명소 > 도시공원",
            "address": "서울 마포구 망원동",
        }
    }
    score, details = _calculate_score(["水"], nearby)
    assert score > 50
    # 검색 키워드가 아닌 실제 place_name이 factor에 들어가야 함.
    assert any("한강시민공원 망원지구" in d["factor"] for d in details)
    # 옛 하드코딩 키워드 단독 형태("한강 인접")는 등장하면 안 됨.
    assert not any(d["factor"].startswith("한강 인접") for d in details)


def test_calculate_score_without_match_penalizes():
    """검증 가능한 오행이 매칭 실패 시 -5 부과."""
    score, details = _calculate_score(["水"], {})
    assert score < 50
    assert details[0]["points"] == -5


def test_calculate_score_skips_fire_earth_unverifiable():
    """火·土는 카카오 검증 불가 — 매칭 없어도 감점 안 함."""
    score, details = _calculate_score(["火", "土"], {})
    assert score == 50
    assert details == []


def test_calculate_score_clamped():
    """전 오행 부족 + 매칭 없음에서도 0~100 범위 유지."""
    score, _ = _calculate_score(["木", "火", "土", "金", "水"], {})
    assert 0 <= score <= 100


def test_saju_calc_returns_pillars_and_oheng():
    """sajupy 통합 테스트 — 1998-06-15 14:30 서울."""
    result = saju_calc.calculate(1998, 6, 15, 14, 30, "서울")
    assert "pillars" in result
    assert "戊寅" in result["pillars"]
    oheng = result["oheng_count"]
    assert sorted(oheng.keys()) == sorted(["木", "火", "土", "金", "水"])
    assert sum(oheng.values()) == 8


def test_is_valid_match_filters_false_positives():
    """'한강설렁탕' 같은 음식점 카테고리는 水로 매칭되면 안 됨."""
    fake_restaurant = {
        "place_name": "한강설렁탕",
        "category": "음식점 > 한식 > 설렁탕",
    }
    assert is_valid_match(fake_restaurant, "水") is False


def test_is_valid_match_木_does_not_match_financial_services():
    """'알찬자산관리서비스' 같은 금융업의 '자산' 카테고리가 木으로 잡히면 안 됨."""
    fake_finance = {
        "place_name": "알찬자산관리서비스",
        "category": "금융,재정 > 자산관리",
    }
    assert is_valid_match(fake_finance, "木") is False


def test_is_valid_match_木_accepts_real_park():
    """실제 공원 카테고리는 木으로 통과."""
    real_park = {
        "place_name": "선유도공원 자생습초지",
        "category": "여행 > 관광,명소 > 도시공원",
    }
    assert is_valid_match(real_park, "木") is True


def test_is_valid_match_accepts_real_river_category():
    """실제 강 카테고리는 통과."""
    real_river = {
        "place_name": "한강시민공원 망원지구",
        "category": "여행 > 관광,명소 > 도시공원 > 한강공원",
    }
    assert is_valid_match(real_river, "水") is True


def test_is_valid_match_passes_unverifiable_oheng():
    """火·土처럼 valid_category_keywords가 비어있는 오행은 항상 True."""
    anything = {"place_name": "X", "category": "Y"}
    assert is_valid_match(anything, "火") is True
    assert is_valid_match(anything, "土") is True


@pytest.mark.asyncio
async def test_saju_agent_run_without_kakao_key():
    """KAKAO_REST_API_KEY 없을 때도 파이프라인이 죽지 않아야 함."""
    from app.agents import saju_agent

    result = await saju_agent.run(
        name="테스트",
        year=1998, month=6, day=15, hour=14, minute=30,
        city="서울", address="서울 강서구 가양동",
    )
    assert "saju_pillars" in result
    assert "oheng_distribution" in result
    assert 0 <= result["match_score"] <= 100
    assert result["match_grade"] in {"아주 좋음", "양호", "보통"}
    assert "테스트" in result["conversational"]


@pytest.mark.asyncio
async def test_saju_agent_run_custom_name():
    """다른 이름이 conversational에 정확히 반영되는지."""
    from app.agents import saju_agent

    result = await saju_agent.run(
        name="홍길동",
        year=1998, month=6, day=15, hour=14, minute=30,
        city="서울", address="서울 강서구 가양동",
    )
    assert "홍길동" in result["conversational"]
    assert "지원" not in result["conversational"]


def test_calculate_score_factor_uses_actual_place_name_not_keyword():
    """factor 문자열에 검색 키워드(예: '한강 인접')가 아닌 실제 place_name이 등장.

    이 테스트는 hallucination 회귀 방지의 핵심.
    """
    nearby = {
        "水": {
            "place_name": "안양천",
            "distance_m": 300,
            "category": "지명 > 강",
            "address": "서울 영등포구",
        }
    }
    _, details = _calculate_score(["水"], nearby)
    # 실제 카카오가 반환한 "안양천"이 factor에 등장
    assert any("안양천" in d["factor"] for d in details)
    # 검색 키워드 "강"이 단독으로 factor에 들어가는 옛 버그 회귀 방지
    assert not any(d["factor"].strip().startswith("강 인접") for d in details)
