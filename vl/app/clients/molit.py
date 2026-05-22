from dataclasses import dataclass
from datetime import date

import httpx


APT_RENT_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
APT_TRADE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"


@dataclass(frozen=True)
class RentTransaction:
    name: str
    dong: str
    area: float
    floor: str | None
    deposit: int
    year: str
    month: str


@dataclass(frozen=True)
class TradeTransaction:
    name: str
    dong: str
    area: float
    floor: str | None
    price: int
    year: str
    month: str


def _get(item: dict, *keys: str, default: str = "") -> str:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return default


def _money_manwon_to_won(value: str) -> int:
    return int(value.replace(",", "").strip()) * 10_000


def normalize_rent_items(raw_items: list[dict]) -> list[RentTransaction]:
    normalized: list[RentTransaction] = []
    for item in raw_items:
        monthly_rent = int(_get(item, "월세금액", "monthlyRent", default="0").replace(",", ""))
        if monthly_rent != 0:
            continue
        normalized.append(
            RentTransaction(
                name=_get(item, "아파트", "aptNm"),
                dong=_get(item, "법정동", "umdNm"),
                area=float(_get(item, "전용면적", "excluUseAr", default="0")),
                floor=_get(item, "층", "floor", default="") or None,
                deposit=_money_manwon_to_won(_get(item, "보증금액", "deposit", default="0")),
                year=_get(item, "년", "dealYear"),
                month=_get(item, "월", "dealMonth"),
            )
        )
    return normalized


def normalize_trade_items(raw_items: list[dict]) -> list[TradeTransaction]:
    normalized: list[TradeTransaction] = []
    for item in raw_items:
        if _get(item, "해제여부", "dealingGbn", default="") == "Y":
            continue
        normalized.append(
            TradeTransaction(
                name=_get(item, "아파트", "aptNm"),
                dong=_get(item, "법정동", "umdNm"),
                area=float(_get(item, "전용면적", "excluUseAr", default="0")),
                floor=_get(item, "층", "floor", default="") or None,
                price=_money_manwon_to_won(_get(item, "거래금액", "dealAmount", default="0")),
                year=_get(item, "년", "dealYear"),
                month=_get(item, "월", "dealMonth"),
            )
        )
    return normalized


def recent_deal_months(today: date, months: int = 6) -> list[str]:
    result: list[str] = []
    year = today.year
    month = today.month
    for _ in range(months):
        result.append(f"{year}{month:02d}")
        month -= 1
        if month == 0:
            year -= 1
            month = 12
    return result


class MolitClient:
    def __init__(self, service_key: str, timeout_seconds: float = 10.0) -> None:
        self.service_key = service_key
        self.timeout_seconds = timeout_seconds

    async def _fetch_items(self, url: str, lawd_cd: str, deal_ymd: str) -> list[dict]:
        params = {
            "serviceKey": self.service_key,
            "LAWD_CD": lawd_cd,
            "DEAL_YMD": deal_ymd,
            "numOfRows": 1000,
            "pageNo": 1,
            "_type": "json",
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            body = response.json()
        items = body.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if isinstance(items, dict):
            return [items]
        return items or []

    async def fetch_rents(self, lawd_cd: str, deal_ymds: list[str]) -> list[RentTransaction]:
        raw: list[dict] = []
        for deal_ymd in deal_ymds:
            raw.extend(await self._fetch_items(APT_RENT_URL, lawd_cd, deal_ymd))
        return normalize_rent_items(raw)

    async def fetch_trades(self, lawd_cd: str, deal_ymds: list[str]) -> list[TradeTransaction]:
        raw: list[dict] = []
        for deal_ymd in deal_ymds:
            raw.extend(await self._fetch_items(APT_TRADE_URL, lawd_cd, deal_ymd))
        return normalize_trade_items(raw)
