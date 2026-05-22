"""주소 문자열을 LAWD_CD(시군구 5자리)와 동/단지명으로 분해."""
import re
from dataclasses import dataclass

from app.core.lawd_codes import LAWD_CODE_MAP, validate_dong

# 시도 약칭 정규화 매핑
SIDO_NORMALIZE = {
    "서울시": "서울특별시",
    "서울 ": "서울특별시 ",
    "부산시": "부산광역시",
    "부산 ": "부산광역시 ",
    "대구시": "대구광역시",
    "인천시": "인천광역시",
    "광주시": "광주광역시",
    "대전시": "대전광역시",
    "울산시": "울산광역시",
    "경기 ": "경기도 ",
    "충북 ": "충청북도 ",
    "충남 ": "충청남도 ",
    "전북 ": "전라북도 ",
    "전남 ": "전라남도 ",
    "경북 ": "경상북도 ",
    "경남 ": "경상남도 ",
}

DONG_PATTERN = re.compile(r"([가-힣]+[동읍면리])\b")


@dataclass
class ParsedAddress:
    raw: str           # 원본 주소
    normalized: str    # 시도 정규화된 주소
    lawd_cd: str       # 시군구 코드 5자리
    sigungu: str       # 매칭된 시군구 이름 (예: "서울특별시 강서구")
    dong: str | None   # 추출된 동 이름 (예: "가양동")
    apt_prefix: str | None  # 아파트명 앞 4글자 (단지 필터용)


def normalize_sido(address: str) -> str:
    """시도 약칭을 정식 명칭으로 변환."""
    result = address
    for short, full in SIDO_NORMALIZE.items():
        result = result.replace(short, full)
    return result


def parse(address: str) -> ParsedAddress:
    """주소 문자열을 파싱한다.

    v2.1 변경점:
        동 추출 시 법정동 사전으로 검증한다.
        시군구에 실제로 존재하는 동만 인정하고, 그 외는 None 처리한다.
        이를 통해 다른 시군구의 동 이름이 우연히 주소 문자열에 포함되어
        잘못 매칭되는 false positive를 차단한다.

    Raises:
        ValueError: LAWD_CD를 찾지 못한 경우
    """
    normalized = normalize_sido(address.strip())

    # 1. 시군구 매칭 (긴 키 우선)
    matched_key = None
    matched_code = None
    for key in sorted(LAWD_CODE_MAP.keys(), key=len, reverse=True):
        if key in normalized:
            matched_key = key
            matched_code = LAWD_CODE_MAP[key]
            break

    if matched_code is None:
        raise ValueError(f"LAWD_CD를 찾을 수 없는 주소: {address}")

    # 시군구 짧은 이름 추출 (예: "서울특별시 강서구" → "강서구")
    sigungu_short = matched_key.replace("서울특별시 ", "").strip()

    # 2. 동 추출 + 사전 검증
    # findall로 모든 후보를 찾고, 사전에 실제 존재하는 것을 우선 채택.
    # 사전에 없는 후보는 무시 (false positive 차단).
    dong = None
    for candidate in DONG_PATTERN.findall(normalized):
        if validate_dong(sigungu_short, candidate):
            dong = candidate
            break
    # 모든 후보가 사전에 없으면 dong = None (시군구 단위로 폴백)

    # 3. 아파트명 prefix 추출 (기존 로직, 동이 있을 때만)
    apt_prefix = None
    if dong:
        after_dong = normalized.split(dong, 1)[1].strip()
        apt_text = re.sub(r"[^가-힣]", "", after_dong)
        if len(apt_text) >= 2:
            apt_prefix = apt_text[:4]

    return ParsedAddress(
        raw=address,
        normalized=normalized,
        lawd_cd=matched_code,
        sigungu=matched_key,
        dong=dong,
        apt_prefix=apt_prefix,
    )
