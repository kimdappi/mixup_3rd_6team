OHENG_ENVIRONMENT: dict[str, dict] = {
    "水": {
        "keywords": ["한강", "공원", "호수"],
        "description": "강·호수·물 근처",
        "direction": "북",
    },
    "木": {
        "keywords": ["공원", "산", "수목원"],
        "description": "공원·녹지·산 근처",
        "direction": "동",
    },
    "火": {
        "keywords": ["남향"],
        "description": "햇볕 잘 드는 남향",
        "direction": "남",
    },
    "土": {
        "keywords": ["평지"],
        "description": "안정된 평지",
        "direction": "중앙",
    },
    "金": {
        "keywords": ["역", "도심"],
        "description": "정돈된 도심·역세권",
        "direction": "서",
    },
}

OHENG_KEYS = ["木", "火", "土", "金", "水"]


def find_lacking(oheng_count: dict[str, int]) -> list[str]:
    """카운트가 1 이하인 오행을 '부족'으로 판정."""
    return [o for o in OHENG_KEYS if oheng_count.get(o, 0) <= 1]
