import httpx

from app.core.config import KAKAO_REST_API_KEY

BASE = "https://dapi.kakao.com/v2/local"


def _headers() -> dict:
    # 매 호출마다 헤더 생성 — 키가 런타임에 .env 갱신되어도 반영되도록.
    return {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}


async def geocode(address: str) -> tuple[float, float] | None:
    """주소 → (위도, 경도). 실패 시 None."""
    if not KAKAO_REST_API_KEY:
        return None
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


async def search_nearby(
    lat: float, lng: float, keyword: str, radius_m: int = 2000
) -> int | None:
    """좌표 주변에서 키워드 검색 → 가장 가까운 결과까지의 거리(m). 없으면 None."""
    if not KAKAO_REST_API_KEY:
        return None
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
        return int(docs[0]["distance"])


async def analyze_environment(address: str, keywords: list[str]) -> dict[str, int]:
    """주소 주변에서 키워드별 가장 가까운 거리(m) 매핑을 반환."""
    coords = await geocode(address)
    if not coords:
        return {}
    lat, lng = coords
    result: dict[str, int] = {}
    for kw in keywords:
        try:
            distance = await search_nearby(lat, lng, kw)
        except httpx.HTTPError as e:
            print(f"[WARN] kakao keyword search failed for '{kw}': {e}")
            continue
        if distance is not None:
            result[kw] = distance
    return result
