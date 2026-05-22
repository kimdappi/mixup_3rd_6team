import pytest

from app.services import address_parser


def test_full_sido_address_matches_gangseo():
    parsed = address_parser.parse("서울특별시 강서구 가양동 1234 가양아파트")
    assert parsed.lawd_cd == "11500"
    assert parsed.sigungu == "서울특별시 강서구"
    assert parsed.dong == "가양동"


def test_full_sido_address_matches_gangnam():
    parsed = address_parser.parse("서울특별시 강남구 역삼동 678 역삼래미안")
    assert parsed.lawd_cd == "11680"
    assert parsed.sigungu == "서울특별시 강남구"


def test_full_sido_address_matches_seocho():
    parsed = address_parser.parse("서울특별시 서초구 반포동")
    assert parsed.lawd_cd == "11650"


def test_full_sido_address_matches_songpa():
    parsed = address_parser.parse("서울특별시 송파구 잠실동")
    assert parsed.lawd_cd == "11710"


def test_full_sido_address_matches_mapo():
    parsed = address_parser.parse("서울특별시 마포구 망원동")
    assert parsed.lawd_cd == "11440"


def test_short_sido_normalized_to_full():
    """'서울시' / '서울 '가 '서울특별시'로 정규화되어야 함."""
    parsed = address_parser.parse("서울시 강서구 가양동")
    assert parsed.lawd_cd == "11500"
    assert "서울특별시" in parsed.normalized

    parsed2 = address_parser.parse("서울 강서구 가양동")
    assert parsed2.lawd_cd == "11500"


def test_long_key_wins_over_short_key():
    """'서울특별시 강서구'가 '강서구' 단독 매칭보다 먼저 잡혀야 함."""
    # 정확히 같은 'gu' 접미사를 가진 한 구만 존재해야 충돌이 일어남.
    # LAWD_CODE_MAP에 '강서구' 단일 키는 없으니 긴 키만 매칭되어야 함.
    parsed = address_parser.parse("서울특별시 강서구 가양동")
    assert parsed.sigungu == "서울특별시 강서구"


def test_unknown_address_raises_value_error():
    with pytest.raises(ValueError):
        address_parser.parse("화성시 동탄동")


def test_dong_extraction_with_dong_suffix():
    parsed = address_parser.parse("서울특별시 강서구 가양동")
    assert parsed.dong == "가양동"


def test_dong_extraction_unknown_dong_falls_back_to_none():
    """v2.1: 정규식으로 잡힌 동이 사전에 없으면 dong=None.

    (서울에는 읍/면/리가 없어서 '어느읍' 같은 가짜 후보는 모두 거부된다.)
    """
    parsed = address_parser.parse("서울특별시 강서구 어느읍 123")
    assert parsed.dong is None


def test_apt_prefix_extraction():
    """동 이후에 한글 아파트명이 있으면 앞 4글자 추출."""
    parsed = address_parser.parse("서울특별시 강서구 가양동 1234 가양강변아파트")
    assert parsed.apt_prefix is not None
    assert len(parsed.apt_prefix) <= 4
    assert parsed.apt_prefix.startswith("가양")


def test_apt_prefix_none_when_no_apt_text():
    parsed = address_parser.parse("서울특별시 강서구 가양동 1234")
    assert parsed.apt_prefix is None


# ============================================================
# v2.1 패치: 동 사전 검증 기반 false positive 차단
# ============================================================

from app.services.address_parser import parse  # noqa: E402


class TestDongValidation:
    """v2.1 패치: 동 사전 검증 기반 false positive 차단."""

    def test_wrong_sigungu_dong_is_rejected(self):
        """다른 시군구의 동 이름이 우연히 포함되어도 인정하지 않아야 한다.

        시나리오: '강서구'와 '신정동'(양천구 소속)이 같이 등장하는 주소.
        v2 동작: 신정동을 동으로 채택 → 항상 매칭 실패
        v2.1 동작: 신정동은 강서구의 동이 아니므로 거부 → 가양동이 채택됨.
        """
        result = parse("서울 강서구 신정로 가양동 100")
        # 가양동이 정상적으로 우선 채택되어야 함
        assert result.dong == "가양동"

    def test_only_wrong_dong_returns_none(self):
        """잘못된 동만 있으면 dong = None."""
        # '신정동'은 강서구에 없는 동
        result = parse("서울 강서구 강변북로 신정상가 1층")
        # 어떤 동 후보도 강서구의 사전에 없음
        # → dong = None (시군구 단위로 폴백)
        assert result.dong is None

    def test_no_dong_keyword_returns_none(self):
        """동 키워드 자체가 없는 주소는 dong = None."""
        result = parse("서울 강서구 강변북로 320")
        assert result.dong is None

    def test_real_dong_still_works(self):
        """정상 입력은 v2와 동일하게 동작해야 한다 (회귀 방지)."""
        result = parse("서울 강서구 가양동 강변아파트 101동")
        assert result.dong == "가양동"
        assert result.lawd_cd == "11500"
        assert result.apt_prefix is not None


class TestDataLoading:
    """v2.1 패치: JSON 로딩 안전성."""

    def test_module_loads_without_error(self):
        """모듈 import가 예외 없이 성공해야 한다."""
        from app.core import lawd_codes
        # 인덱스가 모두 비어있지 않은지 확인
        assert len(lawd_codes.LAWD_CODE_MAP) > 0
        assert len(lawd_codes.DONG_BY_SIGUNGU) > 0
