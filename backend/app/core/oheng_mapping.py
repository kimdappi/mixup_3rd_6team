OHENG_ENVIRONMENT: dict[str, dict] = {
    "水": {
        # 카카오 키워드 검색에 던질 쿼리들.
        # 짧은 "강" 단독은 "강가정의학과의원" 같은 무관한 상호도 매칭되므로 제외.
        "search_queries": ["한강공원", "하천", "호수"],
        # 카카오 category_name 위계(예: "여행 > 관광,명소 > 도시공원 > 한강공원")에
        # 이 단어 중 하나가 등장하면 valid. "한강설렁탕" 같은 음식점은 카테고리가
        # "음식점 > 한식"이라 매칭되지 않음.
        "valid_category_keywords": ["한강공원", "하천", "호수"],
        "description": "강·호수·물 근처",
        "direction": "북",
    },
    "木": {
        # 짧은 "산" 단독은 "자산관리서비스" 같은 카테고리의 "자산"에 매칭되는
        # false positive를 일으키므로 제외. "공원"·"수목원"으로 충분히 커버됨.
        "search_queries": ["공원", "수목원"],
        # category 위계(예: "여행 > 관광,명소 > 도시공원")에 등장하는 정확한
        # segment만 허용. "산" 단독은 짧아서 제외.
        "valid_category_keywords": ["공원", "수목원"],
        "description": "공원·녹지·산 근처",
        "direction": "동",
    },
    "火": {
        # 남향은 카카오 keyword API로 검증 불가능한 추상 개념 — 점수 산정 제외.
        "search_queries": [],
        "valid_category_keywords": [],
        "description": "햇볕 잘 드는 남향",
        "direction": "남",
    },
    "土": {
        # 평지도 마찬가지로 카카오로 검증 불가 — 점수 산정 제외.
        "search_queries": [],
        "valid_category_keywords": [],
        "description": "안정된 평지",
        "direction": "중앙",
    },
    "金": {
        "search_queries": ["지하철역", "도심"],
        "valid_category_keywords": ["지하철역", "철도", "교통"],
        "description": "정돈된 도심·역세권",
        "direction": "서",
    },
}

OHENG_KEYS = ["木", "火", "土", "金", "水"]


def find_lacking(oheng_count: dict[str, int]) -> list[str]:
    """카운트가 1 이하인 오행을 '부족'으로 판정."""
    return [o for o in OHENG_KEYS if oheng_count.get(o, 0) <= 1]


def is_valid_match(place: dict, oheng: str) -> bool:
    """카카오 응답이 해당 오행에 진짜 부합하는 카테고리인지 검증.

    valid_category_keywords가 비어있으면(火·土) 검증 룰 없음 → True.
    """
    valid_kws = OHENG_ENVIRONMENT[oheng]["valid_category_keywords"]
    if not valid_kws:
        return True
    category = place.get("category", "") or ""
    return any(kw in category for kw in valid_kws)
