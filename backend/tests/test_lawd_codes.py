"""법정동코드 사전 로딩 및 검증 함수 테스트."""
from app.core.lawd_codes import (
    DONG_BY_SIGUNGU,
    FULL_CODE_BY_DONG,
    LAWD_CODE_MAP,
    get_dongs_of,
    validate_dong,
)


class TestDataIntegrity:
    """JSON 데이터 자체의 무결성."""

    def test_seoul_25_sigungu_loaded(self):
        """서울 25개 구가 모두 로드되어야 한다."""
        assert len(LAWD_CODE_MAP) == 25

    def test_known_sigungu_codes(self):
        """대표 시군구의 LAWD_CD가 정확한지."""
        assert LAWD_CODE_MAP["서울특별시 강서구"] == "11500"
        assert LAWD_CODE_MAP["서울특별시 강남구"] == "11680"
        assert LAWD_CODE_MAP["서울특별시 종로구"] == "11110"

    def test_all_lawd_codes_are_5_digits(self):
        """모든 LAWD_CD는 정확히 5자리."""
        for name, code in LAWD_CODE_MAP.items():
            assert len(code) == 5, f"{name}: {code}"
            assert code.isdigit(), f"{name}: {code}"

    def test_dong_by_sigungu_has_25_entries(self):
        """동 사전도 25개 시군구를 가져야 한다."""
        assert len(DONG_BY_SIGUNGU) == 25

    def test_full_code_by_dong_has_400_plus_entries(self):
        """서울 동은 400개 이상이다."""
        assert len(FULL_CODE_BY_DONG) >= 400


class TestValidateDong:
    """validate_dong 함수."""

    def test_real_dong_returns_true(self):
        """실제 존재하는 동은 True."""
        assert validate_dong("강서구", "가양동") is True
        assert validate_dong("강남구", "역삼동") is True
        assert validate_dong("종로구", "청운동") is True

    def test_dong_in_wrong_sigungu_returns_false(self):
        """다른 시군구의 동을 검증하면 False (핵심 케이스)."""
        # 신정동은 양천구의 동이지 강서구의 동이 아니다
        assert validate_dong("강서구", "신정동") is False
        # 역삼동은 강남구이지 서초구가 아니다
        assert validate_dong("서초구", "역삼동") is False

    def test_unknown_sigungu_returns_false(self):
        """존재하지 않는 시군구는 False."""
        assert validate_dong("존재하지않는구", "가양동") is False
        assert validate_dong("", "가양동") is False

    def test_empty_dong_returns_false(self):
        """빈 동 이름은 False."""
        assert validate_dong("강서구", "") is False


class TestGetDongsOf:
    """get_dongs_of 함수."""

    def test_returns_frozenset(self):
        """반환 타입은 frozenset (불변)."""
        result = get_dongs_of("강서구")
        assert isinstance(result, frozenset)

    def test_known_dong_in_result(self):
        """알려진 동이 결과에 포함되어야 한다."""
        gangseo = get_dongs_of("강서구")
        assert "가양동" in gangseo

    def test_unknown_sigungu_returns_empty(self):
        """없는 시군구는 빈 frozenset."""
        assert get_dongs_of("없는구") == frozenset()
