import logging

import httpx

from app.core.config import KAKAO_REST_API_KEY
from app.core.oheng_mapping import OHENG_ENVIRONMENT, is_valid_match

logger = logging.getLogger(__name__)

BASE = "https://dapi.kakao.com/v2/local"


def _headers() -> dict:
    # 매 호출마다 헤더 생성 — 키가 런타임에 .env 갱신되어도 반영되도록.
    return {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}


async def geocode(address: str) -> tuple[float, float] | None:
    """주소 → (위도, 경도). 키 없음/카카오 에러 시 None (소프트페일)."""
    if not KAKAO_REST_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(
                f"{BASE}/search/address.json",
                headers=_headers(),
                params={"query": address},
            )
            res.raise_for_status()
            docs = res.json().get("documents", [])
            if not docs:
                return None
            return float(docs[0]["y"]), float(docs[0]["x"])
    except httpx.HTTPError as e:
        logger.warning("kakao geocode failed: %s: %s", type(e).__name__, e)
        return None


async def search_nearby(
    lat: float, lng: float, keyword: str, radius_m: int = 2000
) -> dict | None:
    """좌표 주변에서 키워드 검색 → 가장 가까운 결과의 상세 정보.

    Returns:
        {
            "place_name": "한강시민공원 망원지구",
            "category":   "여행 > 관광,명소 > 도시공원",
            "address":    "서울 마포구 망원동",
            "distance_m": 640,
        }
        없으면 None.
    """
    if not KAKAO_REST_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(
                f"{BASE}/search/keyword.json",
                headers=_headers(),
                params={
                    "query": keyword,
                    # ⚠️ 카카오는 x=경도(lng), y=위도(lat) — 일반 표기와 반대.
                    "x": lng,
                    "y": lat,
                    "radius": radius_m,
                    "sort": "distance",
                },
            )
            res.raise_for_status()
            docs = res.json().get("documents", [])
            if not docs:
                return None
            doc = docs[0]
            return {
                "place_name": doc.get("place_name", ""),
                "category": doc.get("category_name", ""),
                "address": doc.get("address_name", ""),
                "distance_m": int(doc.get("distance", 0) or 0),
            }
    except httpx.HTTPError as e:
        logger.warning(
            "kakao keyword search '%s' failed: %s: %s", keyword, type(e).__name__, e
        )
        return None


async def analyze_environment(
    address: str, lacking_oheng: list[str]
) -> dict[str, dict]:
    """주소 + 부족 오행 리스트 → 오행별 매칭된 실제 장소 정보.

    각 오행에 대해 `search_queries`를 순회하며 카테고리 검증을 통과한 결과 중
    가장 가까운 장소를 채택. 모든 쿼리가 실패하면 해당 오행은 결과에 미포함.

    Returns:
        {
          "水": {"place_name": "한강시민공원 망원지구", "distance_m": 640,
                 "category": "...", "address": "..."},
          ...
        }
    """
    if not lacking_oheng:
        return {}

    coords = await geocode(address)
    if not coords:
        return {}
    lat, lng = coords

    result: dict[str, dict] = {}
    for oheng in lacking_oheng:
        env = OHENG_ENVIRONMENT.get(oheng, {})
        queries: list[str] = env.get("search_queries", []) or []
        if not queries:
            # 火·土처럼 카카오로 검증 불가능한 추상 개념은 스킵.
            continue

        best_match: dict | None = None
        for query in queries:
            place = await search_nearby(lat, lng, query)
            if place is None:
                continue
            if not is_valid_match(place, oheng):
                # 카테고리 검증 실패 (예: "한강설렁탕" 음식점) → 다음 query.
                logger.info(
                    "category mismatch for oheng=%s query=%s: name=%s category=%s",
                    oheng,
                    query,
                    place["place_name"],
                    place["category"],
                )
                continue
            if best_match is None or place["distance_m"] < best_match["distance_m"]:
                best_match = place

        if best_match:
            result[oheng] = best_match

    return result
