"""registry_parser 단위 테스트.

실제 OCR 픽스처(safe_page_001.txt, risky_page_001.txt)로 검증.
"""
from pathlib import Path

from app.services.registry_parser import parse_registry

_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "registry"


def _read(name: str) -> str:
    return (_FIXTURE_DIR / name).read_text(encoding="utf-8")


# ============================================================
# 실제 픽스처 기반 통합
# ============================================================

class TestParseSafe:
    def setup_method(self):
        self.info = parse_registry(_read("safe_page_001.txt"))

    def test_no_mortgage(self):
        assert self.info.has_mortgage is False

    def test_no_max_claim(self):
        assert self.info.max_claim_amount is None

    def test_no_mortgage_holder(self):
        assert self.info.mortgage_holder is None

    def test_address_includes_jibun(self):
        assert self.info.address is not None
        assert "용산구 이태원동" in self.info.address
        # "22-2" 의 dash 포함 여부
        assert "22-2" in self.info.address

    def test_owner_name(self):
        assert self.info.owner_name == "정하늘"

    def test_building_area(self):
        assert self.info.building_area == 141.0


class TestParseRisky:
    def setup_method(self):
        self.info = parse_registry(_read("risky_page_001.txt"))

    def test_has_mortgage_despite_ocr_linebreak(self):
        """OCR이 '근저당권설\\n정'으로 끊어놔도 인식해야 한다."""
        assert self.info.has_mortgage is True

    def test_max_claim_extracted(self):
        assert self.info.max_claim_amount == 1_200_000_000

    def test_mortgage_holder(self):
        assert self.info.mortgage_holder == "운명은행 주식회사"

    def test_address_includes_jibun(self):
        assert self.info.address is not None
        assert "22-2" in self.info.address


# ============================================================
# 정답 라인 차단
# ============================================================

class TestAnswerLineIgnored:
    def test_answer_line_does_not_set_mortgage(self):
        """파서가 정답 라인을 보고 has_mortgage=True가 되면 안 됨."""
        text = (
            "[을구] 1 기록사항 없음\n"
            "현재 소유권 이외의 권리에 관한 등기사 항없음\n"
            "[테스트용 가상 문서] 실제 등기사항증명서가 아니며 법적 효력이 없습니다.\n"
            "참고: 선순위 근저당권 채권최고액 1,200,000,000원 확인.\n"
            "전세보증금 테스트 입력값: 1,300,000,000원/ 최종 위험도: HIGH"
        )
        info = parse_registry(text)
        assert info.has_mortgage is False
        # 정답 라인에 있는 채권최고액 1,200,000,000원도 무시되어야 함
        assert info.max_claim_amount is None


# ============================================================
# 엣지 케이스
# ============================================================

class TestEdgeCases:
    def test_empty_text(self):
        info = parse_registry("")
        assert info.has_mortgage is False
        assert info.max_claim_amount is None
        assert info.address is None
        assert info.raw_text_length == 0

    def test_none_text(self):
        info = parse_registry(None)
        assert info.has_mortgage is False
        assert info.raw_text_length == 0

    def test_mortgage_with_no_amount(self):
        text = "[을구] 근저당권설정 등기 (금액 정보 누락)"
        info = parse_registry(text)
        assert info.has_mortgage is True
        assert info.max_claim_amount is None
