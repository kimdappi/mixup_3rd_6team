"""
국토교통부 공공데이터포털 실거래가 API 클라이언트.

전세 API와 매매 API는 같은 service key를 공유한다.
- 전세: RTMSDataSvcAptRent/getRTMSDataSvcAptRent
- 매매: RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade

금액 단위는 만원 → 원 변환 시 *10000.
"""
import logging
from typing import Any

import httpx

from app.core.config import MOLIT_API_SERVICE_KEY, MOLIT_API_TRADE_SERVICE_KEY

logger = logging.getLogger(__name__)

# 2024년부터 국토부 실거래가 API는 data.go.kr 통합 호스트로 이전됐다.
# 옛 호스트(openapi.molit.go.kr/OpenAPI_ToolInstallPackage/service/rest)는 폐기 예정이며
# 호출 시 0건 또는 4xx로 침묵 실패한다.
BASE_URL = "https://apis.data.go.kr/1613000"
RENT_PATH = "/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
TRADE_PATH = "/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
DEFAULT_NUM_OF_ROWS = 1000
DEFAULT_TIMEOUT = 10.0

# data.go.kr WAF가 일부 클라이언트 UA를 차단하므로 명시적인 UA를 보낸다.
_HEADERS = {
    "User-Agent": "DestinyHouse/1.0 (https://github.com/) httpx",
    "Accept": "application/json",
}


class MolitApiClient:
    """국토교통부 실거래가 통합 클라이언트.

    전세·매매 두 엔드포인트가 같은 service key를 사용하므로,
    인증 정보는 클라이언트에 한 번만 저장한다.
    """

    def __init__(
        self,
        service_key: str,
        trade_service_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """국토부 실거래가 클라이언트.

        Args:
            service_key: 전세 API용 인증키. (필수)
            trade_service_key: 매매 API용 인증키. 비어 있으면 service_key를 폴백.
                data.go.kr이 활용신청을 API별로 받기 때문에, 한 키가
                두 API 모두에 통하면 None으로 두면 되고, 분리되어 있으면
                매매 키를 따로 전달한다.
            timeout: 단일 호출 timeout (초).
        """
        if not service_key:
            raise ValueError("MOLIT_API_SERVICE_KEY가 설정되지 않았다")
        self.service_key = service_key
        self.trade_service_key = trade_service_key or service_key
        self.timeout = timeout

    async def fetch_rent_deals(
        self, lawd_cd: str, deal_ymd: str
    ) -> list[dict[str, Any]]:
        """전세 거래 조회.

        Args:
            lawd_cd: 시군구 5자리 코드 (예: '11500')
            deal_ymd: 거래연월 6자리 (예: '202510')
        """
        return await self._fetch(RENT_PATH, lawd_cd, deal_ymd)

    async def fetch_trade_deals(
        self, lawd_cd: str, deal_ymd: str
    ) -> list[dict[str, Any]]:
        """매매 거래 조회."""
        return await self._fetch(TRADE_PATH, lawd_cd, deal_ymd)

    async def fetch_recent_months(
        self,
        lawd_cd: str,
        months: int = 6,
        kind: str = "rent",
    ) -> list[dict[str, Any]]:
        """최근 N개월치 거래를 한 번에 조회.

        Args:
            kind: 'rent' 또는 'trade'

        Note:
            한 달이라도 4xx/5xx로 실패하면 명시적인 경고를 남긴다.
            특히 403은 "해당 API에 키가 신청되지 않음"을 의미하므로
            로그를 보고 사용자가 data.go.kr에서 신청해야 한다.
        """
        from datetime import date

        today = date.today()
        ymd_list = []
        for i in range(months):
            year = today.year
            month = today.month - i
            while month <= 0:
                month += 12
                year -= 1
            ymd_list.append(f"{year}{month:02d}")

        fetcher = (
            self.fetch_rent_deals if kind == "rent" else self.fetch_trade_deals
        )
        all_deals: list[dict[str, Any]] = []
        first_failure_logged = False
        for ymd in ymd_list:
            try:
                deals = await fetcher(lawd_cd, ymd)
                all_deals.extend(deals)
            except httpx.HTTPStatusError as e:
                if not first_failure_logged:
                    body = (e.response.text or "")[:200]
                    server = e.response.headers.get("server", "")
                    if e.response.status_code == 403:
                        # 응답에 Server 헤더가 비어 있으면 API 서버 도달 전 WAF/게이트웨이 차단.
                        # JSON resultCode가 있으면 인증/구독 문제.
                        likely_cause = (
                            "WAF/네트워크 차단 가능성 (Server 헤더 없음 - 클라우드 IP 차단 등)"
                            if not server else
                            "키 구독 상태 또는 쿼터 문제 가능성"
                        )
                        logger.error(
                            "MOLIT %s 403 Forbidden — %s. data.go.kr에서 해당 API 신청 상태와 "
                            "사용 IP 정책을 함께 확인하세요. lawd=%s server=%r body=%r",
                            kind, likely_cause, lawd_cd, server, body,
                        )
                    else:
                        logger.warning(
                            "molit %s HTTP %s lawd=%s ymd=%s body=%r",
                            kind, e.response.status_code, lawd_cd, ymd, body,
                        )
                    first_failure_logged = True
            except httpx.HTTPError as e:
                logger.warning(
                    "molit fetch failed lawd=%s ymd=%s kind=%s: %s",
                    lawd_cd, ymd, kind, e
                )
        return all_deals

    async def _fetch(
        self, path: str, lawd_cd: str, deal_ymd: str
    ) -> list[dict[str, Any]]:
        # 매매·전세 API는 활용신청이 분리될 수 있으므로 path에 따라 키를 선택.
        key = self.trade_service_key if path == TRADE_PATH else self.service_key
        params = {
            "serviceKey": key,
            "LAWD_CD": lawd_cd,
            "DEAL_YMD": deal_ymd,
            "numOfRows": DEFAULT_NUM_OF_ROWS,
            "pageNo": 1,
            "_type": "json",
        }
        async with httpx.AsyncClient(timeout=self.timeout, headers=_HEADERS) as client:
            res = await client.get(BASE_URL + path, params=params)
            res.raise_for_status()
            # data.go.kr는 키 오류 시 XML <OpenAPI_ServiceResponse>를 200으로 반환할 수 있다.
            ct = res.headers.get("content-type", "")
            if "json" not in ct.lower():
                logger.error(
                    "MOLIT 비JSON 응답 (키 오류 가능). path=%s ct=%s body=%r",
                    path, ct, (res.text or "")[:300],
                )
                return []
            data = res.json()

        # 응답 본문의 resultCode 확인. '000'(OK)이 아니면 키·쿼터 문제.
        header = (data.get("response") or {}).get("header") or {}
        result_code = header.get("resultCode")
        if result_code and result_code != "000":
            logger.error(
                "MOLIT resultCode=%s msg=%s path=%s lawd=%s ymd=%s",
                result_code, header.get("resultMsg"), path, lawd_cd, deal_ymd,
            )
            return []

        items = (
            data.get("response", {})
            .get("body", {})
            .get("items", {})
        )
        if items is None or items == "":
            return []
        item_list = items.get("item", []) if isinstance(items, dict) else []
        if isinstance(item_list, dict):
            return [item_list]
        return item_list


def get_default_client() -> MolitApiClient:
    """FastAPI 의존성 주입용 팩토리.

    환경변수가 비어 있으면 HTTP 503으로 명시적으로 알려준다.
    (서버는 정상 기동, 진단 호출만 차단.)
    """
    from fastapi import HTTPException

    if not MOLIT_API_SERVICE_KEY:
        raise HTTPException(
            status_code=503,
            detail="MOLIT_API_SERVICE_KEY가 설정되지 않아 시세 진단을 사용할 수 없습니다.",
        )
    return MolitApiClient(
        service_key=MOLIT_API_SERVICE_KEY,
        trade_service_key=MOLIT_API_TRADE_SERVICE_KEY or None,
    )
