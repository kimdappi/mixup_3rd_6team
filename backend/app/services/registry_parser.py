"""등기부등본 OCR 텍스트 → 구조화된 정보(RegistryInfo) 추출 파서.

설계 원칙:
  1. **테스트 정답 라인 차단**: PDF 하단의 "[테스트용 가상 문서] ... 최종 위험도: HIGH"
     같은 줄은 정답지일 뿐이므로 파서가 절대 보지 않는다.
  2. **OCR 줄바꿈 정규화**: Vision API가 "근저당권설\\n정", "기록사항 없\\n음"처럼
     단어를 줄 중간에서 끊는 경우가 흔하다. 키워드 매칭 전에 줄바꿈을 공백으로 치환한
     "정규화 본문"을 만들어 사용.
  3. **본문 ↔ 마커 분리**: 정규화하더라도 정답 라인은 보지 않도록 마커 이전 텍스트만
     정규화 대상으로 한다.
"""
import re
from dataclasses import asdict, dataclass

# PDF 하단 정답 라인 차단 마커. 이 줄 이후의 텍스트는 파싱 대상에서 제외.
_TEST_ANSWER_MARKER = "[테스트용 가상 문서]"


@dataclass
class RegistryInfo:
    """등기부등본에서 추출한 핵심 정보."""
    # 표제부
    address: str | None          # 소재지번
    building_area: float | None  # 전용면적 (㎡)
    # 갑구
    owner_name: str | None       # 현재 소유자
    # 을구
    has_mortgage: bool           # 근저당권 존재 여부
    max_claim_amount: int | None  # 채권최고액 (원 단위)
    mortgage_holder: str | None  # 근저당권자
    # 메타
    raw_text_length: int         # OCR 원문 길이 (디버깅용)

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# 본문 정규화
# ============================================================

def _strip_answer_section(ocr_text: str) -> str:
    """정답 라인 차단 — 마커 이전 본문만 반환."""
    return ocr_text.split(_TEST_ANSWER_MARKER)[0]


def _normalize_for_keyword_match(body: str) -> str:
    """OCR 줄바꿈을 공백으로 치환하고 다중 공백을 한 칸으로 정리.

    Vision API가 "근저당권설\\n정"처럼 단어 중간을 끊는 경우에 대비.
    """
    one_line = re.sub(r"\s+", " ", body)
    return one_line


# ============================================================
# 필드별 추출 함수
# ============================================================

_RE_MORTGAGE_SETUP = re.compile(r"근저당권\s*설\s*정")


def _detect_mortgage(normalized: str) -> bool:
    """을구에서 근저당권 존재 여부 판정.

    "기록사항 없음" 패턴이 보이면 False (안전매물).
    "근저당권설정" / "근저당권 설정" / OCR 깨짐("근저당권설 정") 모두 True.
    """
    if "기록사항 없음" in normalized or "기록사항없음" in normalized:
        return False
    if _RE_MORTGAGE_SETUP.search(normalized):
        return True
    return False


_RE_MAX_CLAIM = re.compile(r"채권최고액\s*금?\s*([\d,]+)\s*원")


def _extract_max_claim(normalized: str) -> int | None:
    """채권최고액 추출. '금 1,200,000,000원' → 1_200_000_000."""
    m = _RE_MAX_CLAIM.search(normalized)
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None


_RE_MORTGAGE_HOLDER = re.compile(r"근저당권자\s+([가-힣A-Za-z0-9·\(\)]+(?:\s+주식회사)?)")


def _extract_mortgage_holder(normalized: str) -> str | None:
    """근저당권자 이름 추출. '근저당권자 운명은행 주식회사' → '운명은행 주식회사'."""
    m = _RE_MORTGAGE_HOLDER.search(normalized)
    if not m:
        return None
    return m.group(1).strip()


_RE_OWNER = re.compile(r"소유자\s+([가-힣]{2,4})")


def _extract_owner(normalized: str) -> str | None:
    """현재 소유자 이름 추출. '소유자 정하늘' → '정하늘'."""
    m = _RE_OWNER.search(normalized)
    if not m:
        return None
    return m.group(1).strip()


# 표제부 주소: "[건물] 서울특별시 ... -2 - 집합건물 -" 패턴.
# "- 집합건물" 또는 "[표제부]"가 본문 종결자. "22-2"의 dash는 그 안에 포함.
_RE_ADDRESS = re.compile(
    r"\[건물\]\s*(서울특별시[^\[]+?)\s*-\s*집합건물"
)


def _extract_address(body: str) -> str | None:
    """소재지번 추출. 첫 페이지 상단 '[건물] ... - 집합건물 -' 사이."""
    one_line = re.sub(r"\s+", " ", body)
    m = _RE_ADDRESS.search(one_line)
    if m:
        return m.group(1).strip()
    return None


_RE_AREA = re.compile(r"(\d{2,4}(?:\.\d+)?)\s*m[²2]")


def _extract_area(normalized: str) -> float | None:
    """전용면적 추출. '141.00m²' → 141.0."""
    m = _RE_AREA.search(normalized)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


# ============================================================
# 엔트리 포인트
# ============================================================

def parse_registry(ocr_text: str) -> RegistryInfo:
    """OCR 텍스트에서 구조화 정보 추출.

    규칙:
        - "[테스트용 가상 문서]" 마커 이후 텍스트는 무시 (정답 유출 차단).
        - OCR 줄바꿈은 키워드 매칭 전에 공백으로 정규화.
    """
    body = _strip_answer_section(ocr_text or "")
    normalized = _normalize_for_keyword_match(body)

    return RegistryInfo(
        address=_extract_address(body),
        building_area=_extract_area(normalized),
        owner_name=_extract_owner(normalized),
        has_mortgage=_detect_mortgage(normalized),
        max_claim_amount=_extract_max_claim(normalized),
        mortgage_holder=_extract_mortgage_holder(normalized),
        raw_text_length=len(ocr_text or ""),
    )
