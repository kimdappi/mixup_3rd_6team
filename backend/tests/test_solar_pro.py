"""solar_pro.py 단위 테스트.

핵심 검증:
  - grounding 검증 함수가 허용/거부를 정확히 판단
  - API 키 미설정 시 stub fallback
  - API 호출 실패 시 stub fallback
  - 보증보험 키워드 누출 시 stub fallback
  - 실제 API 호출 자체는 mock으로 처리
"""
from unittest.mock import patch

from openai import OpenAIError

from app.services import solar_pro
from app.services.jeonse_rules import select_similar_listings
from app.services.solar_pro import (
    _strip_markdown_emphasis,
    _validate_diagnosis_grounding,
    _validate_saju_grounding,
    generate_diagnosis_oneline,
    generate_diagnosis_summary,
    interpret_saju,
)


# ============================================================
# Grounding 검증
# ============================================================

class TestSajuGrounding:
    def test_blocks_unknown_place(self):
        """allowed_places에 없는 '한강'은 차단."""
        text = "한강이 가까워서 좋아요"
        assert _validate_saju_grounding(text, allowed_places=["반포공원"]) is False

    def test_allows_known_place_keyword_substring(self):
        """allowed_places의 일부에 키워드가 포함되면 통과.
        '한강시민공원 망원지구'가 있으면 '한강'·'공원' 단어 등장은 허용.
        """
        text = "한강시민공원 망원지구가 가까워요"
        assert _validate_saju_grounding(text, ["한강시민공원 망원지구"]) is True

    def test_no_banned_keyword_passes(self):
        """금지 키워드 자체가 없으면 통과."""
        text = "이 집은 잘 어울리는 흐름이에요"
        assert _validate_saju_grounding(text, []) is True

    def test_blocks_partial_match(self):
        """allowed가 '반포공원'인데 응답에 '한강'이 등장하면 차단."""
        text = "한강 근처라서 좋아요"
        assert _validate_saju_grounding(text, ["반포공원"]) is False


class TestDiagnosisGrounding:
    def test_blocks_unknown_3plus_digit_number(self):
        """context에 없는 5만 같은 숫자가 응답에 등장하면 차단."""
        ctx = {
            "market_analysis": {"avg_jeonse": 320_000_000},
            "jeonse_analysis": {},
            "user_deposit": 300_000_000,
        }
        text = "이 지역 평균은 50000만원입니다"   # 50000이 없는 숫자
        assert _validate_diagnosis_grounding(text, ctx) is False

    def test_allows_won_amount(self):
        """원 단위 그대로 사용된 숫자는 허용."""
        ctx = {
            "market_analysis": {"avg_jeonse": 320_000_000},
            "jeonse_analysis": {},
            "user_deposit": 300_000_000,
        }
        text = "보증금 300000000원, 평균 320000000원이에요"
        assert _validate_diagnosis_grounding(text, ctx) is True

    def test_allows_manwon_amount(self):
        """만원 단위로 환산된 숫자도 허용."""
        ctx = {
            "market_analysis": {"avg_jeonse": 320_000_000},
            "jeonse_analysis": {},
            "user_deposit": 300_000_000,
        }
        text = "보증금 30000만원, 평균 32000만원이에요"
        assert _validate_diagnosis_grounding(text, ctx) is True

    def test_allows_percentage_from_ratio(self):
        """deposit_ratio=0.853 → '85'를 허용 숫자에 포함."""
        ctx = {
            "market_analysis": {"deposit_ratio": 0.853},
            "jeonse_analysis": {},
        }
        # "85"는 2자리라 정규식 \d{3,}에 안 잡힘 — 그래도 통과해야 함
        text = "보증금이 평균의 85% 수준이에요"
        assert _validate_diagnosis_grounding(text, ctx) is True

    def test_short_numbers_not_validated(self):
        """1~2자리 숫자는 검증 대상이 아니다 — 자연어 표현 보호."""
        ctx = {"market_analysis": {}, "jeonse_analysis": {}}
        text = "근처 3건이 비슷한 가격이에요"
        assert _validate_diagnosis_grounding(text, ctx) is True

    def test_empty_text_passes(self):
        ctx = {"market_analysis": {}, "jeonse_analysis": {}}
        assert _validate_diagnosis_grounding("", ctx) is True


# ============================================================
# Fallback 시나리오
# ============================================================

class TestFallbackOnNoApiKey:
    def test_saju_fallback_when_key_missing(self, monkeypatch):
        monkeypatch.setattr("app.services.solar_pro.SOLAR_PRO_API_KEY", "")
        # 캐시된 클라이언트도 무력화
        monkeypatch.setattr("app.services.solar_pro._client", None)
        result = interpret_saju({
            "name": "테스트",
            "lacking": ["水"],
            "nearby": {"水": {"place_name": "한강시민공원 망원지구", "distance_m": 500}},
        })
        assert isinstance(result, str) and len(result) > 0
        # stub의 특징적 문구가 포함돼야 함
        assert "테스트" in result

    def test_diagnosis_fallback_when_key_missing(self, monkeypatch):
        monkeypatch.setattr("app.services.solar_pro.SOLAR_PRO_API_KEY", "")
        monkeypatch.setattr("app.services.solar_pro._client", None)
        result = generate_diagnosis_summary({
            "market_analysis": {"deposit_status": "fair"},
            "jeonse_analysis": {"risk_level": "safe"},
        })
        assert isinstance(result, str) and "비슷한 수준" in result


class TestFallbackOnApiError:
    def test_saju_fallback_on_openai_error(self, monkeypatch):
        """API가 OpenAIError를 던지면 stub fallback."""
        monkeypatch.setattr("app.services.solar_pro.SOLAR_PRO_API_KEY", "test-key")
        with patch(
            "app.services.solar_pro._call_solar",
            side_effect=OpenAIError("simulated"),
        ):
            result = interpret_saju({
                "name": "테스트",
                "lacking": ["水"],
                "nearby": {"水": {"place_name": "한강시민공원 망원지구", "distance_m": 500}},
            })
        assert "테스트" in result   # stub 특징

    def test_diagnosis_fallback_on_timeout_error(self, monkeypatch):
        monkeypatch.setattr("app.services.solar_pro.SOLAR_PRO_API_KEY", "test-key")
        with patch(
            "app.services.solar_pro._call_solar",
            side_effect=TimeoutError("network slow"),
        ):
            result = generate_diagnosis_summary({
                "market_analysis": {"deposit_status": "overpriced"},
                "jeonse_analysis": {"risk_level": "very_high"},
            })
        assert "15% 이상" in result   # stub overpriced 분기 특징


class TestFallbackOnGroundingFail:
    def test_diagnosis_fallback_on_grounding_violation(self, monkeypatch):
        """LLM이 context에 없는 50000 같은 숫자를 만들어내면 stub fallback."""
        monkeypatch.setattr("app.services.solar_pro.SOLAR_PRO_API_KEY", "test-key")
        with patch(
            "app.services.solar_pro._call_solar",
            return_value="이 지역 평균은 50000만원입니다",
        ):
            ctx = {
                "market_analysis": {"deposit_status": "fair", "avg_jeonse": 320_000_000},
                "jeonse_analysis": {"risk_level": "safe"},
                "user_deposit": 300_000_000,
            }
            result = generate_diagnosis_summary(ctx)
        # stub fair 분기 결과로 떨어져야 함
        assert "비슷한 수준" in result

    def test_diagnosis_fallback_on_banned_keyword(self, monkeypatch):
        """LLM이 '보증보험' 단어를 출력하면 stub fallback."""
        monkeypatch.setattr("app.services.solar_pro.SOLAR_PRO_API_KEY", "test-key")
        with patch(
            "app.services.solar_pro._call_solar",
            return_value="보증보험 가입을 추천드려요",
        ):
            result = generate_diagnosis_summary({
                "market_analysis": {"deposit_status": "fair"},
                "jeonse_analysis": {"risk_level": "safe"},
            })
        assert "보증보험" not in result   # 차단됨
        assert "비슷한 수준" in result    # stub fair 결과


# ============================================================
# 실 API 호출 경로 (mock으로 정상 응답 가정)
# ============================================================

class TestRealApiSuccess:
    def test_diagnosis_returns_llm_text_when_grounded(self, monkeypatch):
        """LLM 응답이 grounded이고 보증보험 키워드도 없으면 그대로 반환."""
        monkeypatch.setattr("app.services.solar_pro.SOLAR_PRO_API_KEY", "test-key")
        with patch(
            "app.services.solar_pro._call_solar",
            return_value="보증금이 평균과 비슷해요. 안정적인 수준이에요.",
        ):
            result = generate_diagnosis_summary({
                "market_analysis": {"deposit_status": "fair"},
                "jeonse_analysis": {"risk_level": "safe"},
            })
        # LLM 텍스트 그대로 반환
        assert result == "보증금이 평균과 비슷해요. 안정적인 수준이에요."

    def test_saju_returns_llm_text_when_grounded(self, monkeypatch):
        monkeypatch.setattr("app.services.solar_pro.SOLAR_PRO_API_KEY", "test-key")
        with patch(
            "app.services.solar_pro._call_solar",
            return_value="이 집은 잘 어울려요. ✨",
        ):
            result = interpret_saju({
                "name": "테스트",
                "lacking": ["水"],
                "nearby": {"水": {"place_name": "한강시민공원 망원지구", "distance_m": 500}},
            })
        assert result == "이 집은 잘 어울려요. ✨"


# ============================================================
# is_available
# ============================================================

class TestStripMarkdownEmphasis:
    """LLM 응답의 `**bold**`/`__bold__` 강조 표기 제거."""

    def test_strips_double_asterisk_pairs(self):
        result = _strip_markdown_emphasis("이것은 **시세 판정** 입니다")
        assert result == "이것은 시세 판정 입니다"

    def test_strips_double_underscore_pairs(self):
        result = _strip_markdown_emphasis("__중요한__ 정보")
        assert result == "중요한 정보"

    def test_strips_multiple_emphasis_blocks(self):
        text = "① **시세 판정**\n입력 보증금 **9억**\n② **전세가율**"
        out = _strip_markdown_emphasis(text)
        assert "**" not in out
        assert "시세 판정" in out
        assert "9억" in out
        assert "전세가율" in out

    def test_strips_unpaired_marker_too(self):
        # 짝이 안 맞아도 안전한 쪽: 그냥 제거
        assert _strip_markdown_emphasis("**열린 채로 끝") == "열린 채로 끝"

    def test_empty_input(self):
        assert _strip_markdown_emphasis("") == ""
        assert _strip_markdown_emphasis(None) is None

    def test_no_markdown_unchanged(self):
        assert _strip_markdown_emphasis("순수 텍스트") == "순수 텍스트"


class TestLLMResponseStripsMarkdown:
    """LLM이 마크다운 강조를 만들어내도 사용자에겐 평문이 가야 한다."""

    def test_diagnosis_strips_markdown_from_llm(self, monkeypatch):
        monkeypatch.setattr("app.services.solar_pro.SOLAR_PRO_API_KEY", "test-key")
        with patch(
            "app.services.solar_pro._call_solar",
            return_value="① **시세 판정**\n보증금이 평균과 비슷해요.",
        ):
            result = generate_diagnosis_summary({
                "market_analysis": {"deposit_status": "fair"},
                "jeonse_analysis": {"risk_level": "safe"},
            })
        assert "**" not in result, f"마크다운 누출: {result!r}"

    def test_saju_strips_markdown_from_llm(self, monkeypatch):
        monkeypatch.setattr("app.services.solar_pro.SOLAR_PRO_API_KEY", "test-key")
        with patch(
            "app.services.solar_pro._call_solar",
            return_value="**한강시민공원 망원지구**가 가까워요. ✨",
        ):
            result = interpret_saju({
                "name": "테스트",
                "lacking": ["水"],
                "nearby": {"水": {"place_name": "한강시민공원 망원지구", "distance_m": 500}},
            })
        assert "**" not in result, f"마크다운 누출: {result!r}"


class TestIsAvailable:
    def test_returns_false_when_key_empty(self, monkeypatch):
        monkeypatch.setattr("app.services.solar_pro.SOLAR_PRO_API_KEY", "")
        assert solar_pro.is_available() is False

    def test_returns_true_when_key_present(self, monkeypatch):
        monkeypatch.setattr("app.services.solar_pro.SOLAR_PRO_API_KEY", "any-key")
        assert solar_pro.is_available() is True


# ============================================================
# v3: select_similar_listings
# ============================================================

class TestSimilarListingsSelection:
    def test_select_within_tolerance(self):
        """제시 ±10% 이내 매물만 채택."""
        samples = [
            {"price_won": 300_000_000, "year": 2026, "month": 4},   # 0%
            {"price_won": 325_000_000, "year": 2026, "month": 3},   # +8.3%
            {"price_won": 350_000_000, "year": 2026, "month": 2},   # +16.7% (제외)
        ]
        result = select_similar_listings(300_000_000, samples, tolerance=0.10)
        assert len(result) == 2

    def test_boundary_exactly_10_percent_included(self):
        samples = [
            {"price_won": 330_000_000, "year": 2026, "month": 4},   # +10% 경계
            {"price_won": 270_000_000, "year": 2026, "month": 3},   # -10% 경계
        ]
        result = select_similar_listings(300_000_000, samples, tolerance=0.10)
        assert len(result) == 2

    def test_empty_when_no_match(self):
        samples = [{"price_won": 500_000_000, "year": 2026, "month": 4}]
        assert select_similar_listings(300_000_000, samples) == []

    def test_max_count_cap(self):
        samples = [
            {"price_won": 300_000_000, "year": 2026, "month": m}
            for m in range(1, 7)
        ]
        result = select_similar_listings(300_000_000, samples, max_count=3)
        assert len(result) == 3

    def test_sorted_by_year_month_desc(self):
        samples = [
            {"price_won": 300_000_000, "year": 2025, "month": 12, "apt_name": "old"},
            {"price_won": 300_000_000, "year": 2026, "month": 4,  "apt_name": "new"},
            {"price_won": 300_000_000, "year": 2026, "month": 1,  "apt_name": "mid"},
        ]
        result = select_similar_listings(300_000_000, samples, max_count=3)
        assert [s["apt_name"] for s in result] == ["new", "mid", "old"]

    def test_empty_inputs(self):
        assert select_similar_listings(0, []) == []
        assert select_similar_listings(300_000_000, []) == []
        assert select_similar_listings(0, [{"price_won": 300_000_000}]) == []


# ============================================================
# v3: 확장된 grounding (similar_listings 숫자 허용 + 콤마 정규화)
# ============================================================

class TestDiagnosisGroundingV3:
    def test_similar_listing_price_allowed(self):
        ctx = {
            "market_analysis": {"avg_jeonse": 320_000_000},
            "jeonse_analysis": {"user_jeonse_rate": 0.39},
            "similar_listings": [
                {"price_won": 310_000_000, "area_sqm": 84.0, "floor": 5,
                 "year": 2026, "month": 4},
            ],
        }
        text = "비슷한 매물이 31000만원에 거래됐어요"
        assert _validate_diagnosis_grounding(text, ctx) is True

    def test_unknown_similar_number_blocked(self):
        ctx = {
            "market_analysis": {"avg_jeonse": 320_000_000},
            "jeonse_analysis": {"user_jeonse_rate": 0.39},
            "similar_listings": [
                {"price_won": 310_000_000, "year": 2026, "month": 4},
            ],
        }
        text = "비슷한 매물이 99999만원에 거래됐어요"
        assert _validate_diagnosis_grounding(text, ctx) is False

    def test_comma_separated_won_allowed(self):
        """LLM이 '300,000,000원' 같이 콤마 포함 표기를 써도 통과."""
        ctx = {
            "market_analysis": {"avg_jeonse": 300_000_000},
            "jeonse_analysis": {},
            "user_deposit": 300_000_000,
        }
        text = "보증금 300,000,000원으로 평균과 동일해요."
        assert _validate_diagnosis_grounding(text, ctx) is True

    def test_year_from_similar_allowed(self):
        ctx = {
            "market_analysis": {},
            "jeonse_analysis": {},
            "similar_listings": [
                {"price_won": 300_000_000, "year": 2026, "month": 4},
            ],
        }
        text = "2026.04 거래 사례가 있어요"
        assert _validate_diagnosis_grounding(text, ctx) is True


# ============================================================
# v3: 주관 표현 차단
# ============================================================

class TestSubjectiveExpressionBlock:
    def test_blocks_subjective_phrase(self, monkeypatch):
        """LLM이 '안심하셔도 됩니다' 같이 주관 위로를 섞으면 stub fallback."""
        monkeypatch.setattr("app.services.solar_pro.SOLAR_PRO_API_KEY", "test-key")
        with patch(
            "app.services.solar_pro._call_solar",
            return_value="평균과 비슷해요. 안심하셔도 됩니다.",
        ):
            result = generate_diagnosis_summary({
                "market_analysis": {"deposit_status": "fair"},
                "jeonse_analysis": {"risk_level": "safe"},
            })
        # 주관 표현 차단되고 stub 결과로 떨어짐
        assert "안심하" not in result
        # stub의 fair 분기 특징
        assert "비슷한 수준" in result

    def test_blocks_recommendation_phrase(self, monkeypatch):
        monkeypatch.setattr("app.services.solar_pro.SOLAR_PRO_API_KEY", "test-key")
        with patch(
            "app.services.solar_pro._call_solar",
            return_value="이 매물 추천드려요. 좋은 선택이에요.",
        ):
            result = generate_diagnosis_summary({
                "market_analysis": {"deposit_status": "fair"},
                "jeonse_analysis": {"risk_level": "safe"},
            })
        assert "추천드려" not in result


# ============================================================
# v3: 4항목 stub 구조 검증
# ============================================================

class TestStubFourItemStructure:
    def test_stub_outputs_four_lines(self, monkeypatch):
        monkeypatch.setattr("app.services.solar_pro.SOLAR_PRO_API_KEY", "")
        result = generate_diagnosis_summary({
            "user_deposit": 300_000_000,
            "market_analysis": {
                "deposit_status": "fair",
                "avg_jeonse": 310_000_000,
            },
            "jeonse_analysis": {
                "risk_level": "safe",
                "user_jeonse_rate": 0.38,
            },
            "similar_listings": [],
        })
        lines = result.split("\n")
        # 최소 4줄 (similar_listings 비어있을 때 ④는 1줄)
        assert len(lines) >= 4
        # 각 항목 키워드 등장
        assert "비슷한 수준" in lines[0]                 # ①
        assert "38" in lines[1] and "안전" in lines[1]    # ② percent + risk
        # v3.1 자연 표기: 31000만원 → "3억 1,000만원", 30000만원 → "3억"
        assert "3억 1,000만원" in lines[2] and "3억" in lines[2]   # ③
        assert "비슷한 매물은 표본에 없습니다" in lines[3]   # ④ empty case

    def test_stub_renders_similar_listing_lines(self, monkeypatch):
        monkeypatch.setattr("app.services.solar_pro.SOLAR_PRO_API_KEY", "")
        result = generate_diagnosis_summary({
            "user_deposit": 300_000_000,
            "market_analysis": {
                "deposit_status": "fair",
                "avg_jeonse": 310_000_000,
            },
            "jeonse_analysis": {
                "risk_level": "safe",
                "user_jeonse_rate": 0.38,
            },
            "similar_listings": [
                {"apt_name": "가양강변", "area_sqm": 84.5, "floor": 5,
                 "year": 2026, "month": 4, "price_won": 310_000_000},
            ],
        })
        # 매물 한 줄이 stub 본문에 포함되어야 함
        assert "가양강변" in result
        assert "84.5㎡" in result
        assert "5층" in result
        assert "2026.04" in result
        # v3.1 자연 표기: 31000만원 → "3억 1,000만원"
        assert "3억 1,000만원" in result


# ============================================================
# v3.1: generate_diagnosis_oneline
# ============================================================

class TestDiagnosisOneline:
    def test_oneline_cheap(self):
        ctx = {"market_analysis": {"deposit_status": "cheap"}}
        assert "낮은 편" in generate_diagnosis_oneline(ctx)

    def test_oneline_overpriced(self):
        ctx = {"market_analysis": {"deposit_status": "overpriced"}}
        assert "15% 이상" in generate_diagnosis_oneline(ctx)

    def test_oneline_missing_status(self):
        ctx = {"market_analysis": {}}
        assert "데이터가 부족" in generate_diagnosis_oneline(ctx)

    def test_oneline_no_market_section(self):
        ctx = {}
        assert "데이터가 부족" in generate_diagnosis_oneline(ctx)

    def test_oneline_does_not_call_llm(self, monkeypatch):
        """oneline은 LLM 호출하지 않아야 함."""
        monkeypatch.setattr("app.services.solar_pro.SOLAR_PRO_API_KEY", "test-key")
        called = []
        monkeypatch.setattr(
            "app.services.solar_pro._call_solar",
            lambda *a, **kw: called.append(1) or "should not be called",
        )
        ctx = {"market_analysis": {"deposit_status": "fair"}}
        generate_diagnosis_oneline(ctx)
        assert called == []

    def test_oneline_returns_single_line(self):
        """oneline은 한 줄이어야 함 (개행 없음)."""
        for status in ["overpriced", "slightly_high", "fair", "cheap", "suspicious"]:
            ctx = {"market_analysis": {"deposit_status": status}}
            result = generate_diagnosis_oneline(ctx)
            assert "\n" not in result, f"{status} oneline contains newline: {result!r}"


# ============================================================
# v3.1: 자연 표기 grounding (콤마 + eok/man 분리)
# ============================================================

class TestNaturalFormatGrounding:
    def test_passes_eok_only_amount(self):
        """'3억' 같은 억 단위 표기 통과."""
        ctx = {
            "market_analysis": {"avg_jeonse": 300_000_000},
            "jeonse_analysis": {},
            "user_deposit": 300_000_000,
            "similar_listings": [],
        }
        # 1~2자리는 어차피 검증 안 됨 → 통과
        text = "보증금은 3억이에요."
        assert _validate_diagnosis_grounding(text, ctx) is True

    def test_passes_eok_man_split_with_comma(self):
        """'10억 4,783만원' → 콤마 정규화 후 '4783' 매칭."""
        # avg_jeonse = 104783 만원 → 1_047_830_000원
        ctx = {
            "market_analysis": {"avg_jeonse": 1_047_830_000},
            "jeonse_analysis": {},
            "similar_listings": [],
        }
        text = "인근 평균은 10억 4,783만원이에요."
        assert _validate_diagnosis_grounding(text, ctx) is True

    def test_blocks_fake_eok_man_amount(self):
        """포매팅된 형식이라도 context에 없는 숫자면 차단."""
        ctx = {
            "market_analysis": {"avg_jeonse": 1_047_830_000},
            "jeonse_analysis": {},
            "similar_listings": [],
        }
        text = "인근 평균은 50억 9,999만원이에요."  # context에 없는 숫자
        assert _validate_diagnosis_grounding(text, ctx) is False

    def test_passes_similar_listing_eok_man(self):
        """similar listing의 price_won이 eok/man 분리값으로 통과."""
        # price_won = 295_000_000 → 만원 = 29500 → eok=2, man=9500
        ctx = {
            "market_analysis": {},
            "jeonse_analysis": {},
            "similar_listings": [
                {"price_won": 295_000_000, "year": 2026, "month": 4},
            ],
        }
        text = "비슷한 매물 2억 9,500만원에 거래됐어요."
        assert _validate_diagnosis_grounding(text, ctx) is True

    def test_passes_natural_format_with_thousand_separator(self):
        """천 단위 콤마가 들어간 만원 표기도 통과 (예: 9,500만원)."""
        ctx = {
            "market_analysis": {"avg_jeonse": 95_000_000},
            "jeonse_analysis": {},
            "similar_listings": [],
        }
        # avg_jeonse=95_000_000 → manwon=9500 (<10000) → eok-split 안 일어남
        text = "평균은 9,500만원이에요."
        assert _validate_diagnosis_grounding(text, ctx) is True
