"""checklist_rules.compose_checklist 단위 테스트."""
from app.services.checklist_rules import BASE_CHECKLIST, compose_checklist


class TestComposeChecklist:
    def test_base_only_when_no_signals(self):
        """시그널이 없으면 베이스만 그대로 반환."""
        result = compose_checklist([])
        assert result == list(BASE_CHECKLIST)

    def test_base_comes_first(self):
        """베이스 항목이 시그널 항목보다 앞에 와야 한다."""
        signals = ["임대인 채무·국세 체납 여부를 확인하세요"]
        result = compose_checklist(signals)
        # 첫 N개는 베이스와 동일
        assert result[: len(BASE_CHECKLIST)] == list(BASE_CHECKLIST)
        # 마지막은 시그널 항목
        assert result[-1] == signals[0]

    def test_dedupe_exact_match(self):
        """시그널 recommended_action이 베이스와 글자 그대로 같으면 한 번만."""
        duplicate = BASE_CHECKLIST[0]   # 베이스 첫 항목과 동일
        result = compose_checklist([duplicate])
        # 중복이라 베이스 길이만큼만 나옴
        assert len(result) == len(BASE_CHECKLIST)
        assert result.count(duplicate) == 1

    def test_dedupe_within_signals(self):
        """시그널 항목들 사이의 중복도 제거."""
        result = compose_checklist(["동일 액션", "동일 액션", "다른 액션"])
        # 베이스 4 + 시그널 2 (동일 액션 1번, 다른 액션 1번)
        assert len(result) == len(BASE_CHECKLIST) + 2
        assert result.count("동일 액션") == 1
        assert result.count("다른 액션") == 1

    def test_empty_strings_filtered(self):
        """빈 문자열·공백·None은 제외."""
        result = compose_checklist(["", "  ", None, "실제 액션"])
        # 베이스 + "실제 액션" 한 개
        assert len(result) == len(BASE_CHECKLIST) + 1
        assert result[-1] == "실제 액션"

    def test_whitespace_normalized(self):
        """앞뒤 공백은 strip 후 비교."""
        # 시그널의 액션이 베이스와 같은데 공백만 다른 경우 → 중복 처리
        with_whitespace = f"  {BASE_CHECKLIST[0]}  "
        result = compose_checklist([with_whitespace])
        assert len(result) == len(BASE_CHECKLIST)

    def test_no_insurance_keywords_in_base(self):
        """베이스 항목에 보증보험/HUG/안심전세 키워드가 없어야 한다."""
        banned = ["보증보험", "HUG", "허그", "안심전세", "보증가입"]
        for item in BASE_CHECKLIST:
            for kw in banned:
                assert kw not in item, f"베이스에 금지 키워드 누출: {item!r}"

    def test_returns_list_not_tuple(self):
        """반환 타입은 list (frontend에서 mutable 처리 호환)."""
        assert isinstance(compose_checklist([]), list)
