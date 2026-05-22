import pytest

from app.agents.saju_agent import _calculate_score, _grade_from_score
from app.services import saju_calc


def test_grade_from_score():
    assert _grade_from_score(85) == "아주 좋음"
    assert _grade_from_score(70) == "양호"
    assert _grade_from_score(50) == "보통"


def test_calculate_score_with_water_match():
    score, details = _calculate_score(["水"], {"한강": 500})
    assert score > 50
    assert any("한강" in d["factor"] for d in details)


def test_calculate_score_without_match_penalizes():
    score, details = _calculate_score(["水"], {})
    assert score < 50
    assert details[0]["points"] == -5


def test_calculate_score_clamped():
    # 매우 많은 부족 + 아무 매칭 없음 — 음수로 안 떨어지는지
    score, _ = _calculate_score(["木", "火", "土", "金", "水"], {})
    assert 0 <= score <= 100


def test_saju_calc_returns_pillars_and_oheng():
    """sajupy 통합 테스트 — 1998-06-15 14:30 서울."""
    result = saju_calc.calculate(1998, 6, 15, 14, 30, "서울")
    assert "pillars" in result
    assert "戊寅" in result["pillars"]  # 연주
    oheng = result["oheng_count"]
    assert sorted(oheng.keys()) == sorted(["木", "火", "土", "金", "水"])
    assert sum(oheng.values()) == 8  # 천간 4 + 지지 4


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
    assert "match_score" in result
    assert 0 <= result["match_score"] <= 100
    assert result["match_grade"] in {"아주 좋음", "양호", "보통"}
    # 이름이 conversational 문장에 포함되어야 함. (stub fallback도 모두 이름을 사용.)
    assert "테스트" in result["conversational"]


@pytest.mark.asyncio
async def test_saju_agent_run_custom_name():
    """다른 이름을 줘도 conversational에 정확히 반영되는지."""
    from app.agents import saju_agent

    result = await saju_agent.run(
        name="홍길동",
        year=1998, month=6, day=15, hour=14, minute=30,
        city="서울", address="서울 강서구 가양동",
    )
    assert "홍길동" in result["conversational"]
    assert "지원" not in result["conversational"]  # 하드코딩된 이름이 나오면 안 됨
