import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParsedAddress:
    original_address: str
    normalized_address: str
    lawd_cd: str
    dong: str | None
    apt_name: str | None
    apt_keyword: str | None


REPLACEMENTS = [
    ("서울시", "서울특별시"),
    ("서울 ", "서울특별시 "),
    ("부산시", "부산광역시"),
    ("부산 ", "부산광역시 "),
    ("대구시", "대구광역시"),
    ("인천시", "인천광역시"),
    ("광주시", "광주광역시"),
    ("대전시", "대전광역시"),
    ("울산시", "울산광역시"),
    ("경기 ", "경기도 "),
    ("충북 ", "충청북도 "),
    ("충남 ", "충청남도 "),
    ("전북 ", "전라북도 "),
    ("전남 ", "전라남도 "),
    ("경북 ", "경상북도 "),
    ("경남 ", "경상남도 "),
]


def normalize_sido(address: str) -> str:
    normalized = " ".join(address.strip().split())
    for source, target in REPLACEMENTS:
        if normalized.startswith(source):
            return normalized.replace(source, target, 1)
    return normalized


def load_lawd_map() -> dict[str, str]:
    path = Path(__file__).resolve().parents[1] / "data" / "lawd_map.json"
    return json.loads(path.read_text(encoding="utf-8"))


def find_lawd_cd(normalized_address: str, lawd_map: dict[str, str]) -> str:
    for key in sorted(lawd_map, key=len, reverse=True):
        if key in normalized_address:
            return lawd_map[key]
    raise ValueError(f"LAWD_CD를 찾을 수 없습니다: {normalized_address}")


def extract_dong(address: str) -> str | None:
    match = re.search(r"([가-힣]+[동읍면리])\b", address)
    return match.group(1) if match else None


def extract_apt_name(address: str) -> str | None:
    match = re.search(
        r"[동읍면리]\s+([가-힣\w·]+(?:아파트|APT|빌라|오피스텔|타운|파크|힐스|자이|푸르지오|래미안|아이파크|e편한세상|SK뷰|롯데캐슬|현대|두산|대림))",
        address,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def parse_address(address: str) -> ParsedAddress:
    normalized = normalize_sido(address)
    lawd_map = load_lawd_map()
    apt_name = extract_apt_name(normalized)
    return ParsedAddress(
        original_address=address,
        normalized_address=normalized,
        lawd_cd=find_lawd_cd(normalized, lawd_map),
        dong=extract_dong(normalized),
        apt_name=apt_name,
        apt_keyword=apt_name[:4] if apt_name else None,
    )
