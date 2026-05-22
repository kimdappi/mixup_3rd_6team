"""법정동코드 매핑.

서울 25개 구 + 모든 동을 지원한다.
원본 데이터는 `seoul_lawd_codes.json` (hierarchical 구조)에서 로드한다.

세 가지 인덱스를 메모리에 구성:
    1. LAWD_CODE_MAP       : 시군구 풀네임 → LAWD_CD (v2 호환)
    2. DONG_BY_SIGUNGU     : 시군구 → 동 이름 집합 (동 검증용)
    3. FULL_CODE_BY_DONG   : (시군구, 동) → 10자리 풀 코드 (향후 확장용)
"""
import json
from pathlib import Path
from typing import Final

_DATA_PATH: Final = Path(__file__).parent / "seoul_lawd_codes.json"


def _load_raw() -> list[dict]:
    """JSON 원본을 로드. 파일이 없거나 깨졌으면 즉시 예외를 발생시킨다.

    Raises:
        FileNotFoundError: JSON 파일이 존재하지 않음
        ValueError: JSON 구조가 예상과 다름
    """
    if not _DATA_PATH.exists():
        raise FileNotFoundError(
            f"법정동코드 사전 파일을 찾을 수 없다: {_DATA_PATH}"
        )

    with open(_DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("seoul_lawd_codes.json은 비어 있지 않은 배열이어야 한다")

    # 최소 25개 시군구 확인
    if len(data) < 25:
        raise ValueError(
            f"서울 25개 구가 모두 있어야 한다. 현재: {len(data)}개"
        )

    return data


_RAW: Final = _load_raw()


# ============================================================
# 인덱스 1: LAWD_CODE_MAP (v2 호환)
# ============================================================
LAWD_CODE_MAP: Final[dict[str, str]] = {
    item["full_name"]: item["lawd_cd"]
    for item in _RAW
}


# ============================================================
# 인덱스 2: DONG_BY_SIGUNGU (동 검증용 - 이번 패치의 핵심)
# ============================================================
DONG_BY_SIGUNGU: Final[dict[str, frozenset[str]]] = {
    item["sigungu"]: frozenset(d["dong"] for d in item["dongs"])
    for item in _RAW
}


# ============================================================
# 인덱스 3: FULL_CODE_BY_DONG (향후 확장용)
# ============================================================
FULL_CODE_BY_DONG: Final[dict[tuple[str, str], str]] = {
    (item["sigungu"], d["dong"]): d["full_code"]
    for item in _RAW
    for d in item["dongs"]
}


# ============================================================
# 공개 헬퍼 함수
# ============================================================
def validate_dong(sigungu: str, dong: str) -> bool:
    """동이 해당 시군구에 실제로 존재하는지 검증한다.

    Args:
        sigungu: 시군구 짧은 이름 (예: '강서구')
        dong: 동/읍/면/리 이름 (예: '가양동')

    Returns:
        True if dong exists in sigungu, else False.

    Examples:
        >>> validate_dong("강서구", "가양동")
        True
        >>> validate_dong("강서구", "신정동")  # 신정동은 양천구
        False
        >>> validate_dong("존재하지않는구", "가양동")
        False
    """
    return dong in DONG_BY_SIGUNGU.get(sigungu, frozenset())


def get_dongs_of(sigungu: str) -> frozenset[str]:
    """특정 시군구의 모든 동 이름을 반환한다."""
    return DONG_BY_SIGUNGU.get(sigungu, frozenset())
