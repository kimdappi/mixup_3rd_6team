"""시세 진단 워크플로우 (명세서의 LangGraph 노드 = 함수).

워크플로우:
    parse_address
      -> fetch_market_data
      -> filter_nearby_deals
      -> diagnose_market
      -> diagnose_jeonse_ratio
      -> collect_risk_signals
      -> generate_summary  (Solar Pro)
"""
from app.services import address_parser, jeonse_rules, market_rules, solar_pro
from app.services.molit_api import MolitApiClient

DISCLAIMER = (
    "이 결과는 공개 데이터 기반의 사전진단이며, 전세사기 여부나 실제 "
    "보증보험 가입 가능 여부를 확정하지 않습니다. 실제 계약 전에는 "
    "최신 공식 문서와 보증기관 심사 결과를 확인해야 합니다."
)


async def run_quick_diagnosis(
    address: str,
    user_deposit: int,
    area_sqm: float,
    housing_type: str,
    contract_stage: str | None,
    client: MolitApiClient,
) -> dict:
    """문서 없이 시세 기반 빠른 진단을 수행한다.

    Args:
        address: 자유형식 주소
        user_deposit: 보증금 (원 단위)
        area_sqm: 전용면적 (제곱미터)
        housing_type: 'apt' | 'villa' | 'officetel' (MVP는 apt만 정확)
        contract_stage: 'pre_view' | 'pre_contract' | 'pre_balance' | 'post_move_in'
        client: 의존성 주입된 MolitApiClient
    """
    # 1. 주소 파싱
    parsed = address_parser.parse(address)

    # 2. 전세·매매 데이터 조회 (최근 6개월)
    rent_deals = await client.fetch_recent_months(parsed.lawd_cd, months=6, kind="rent")
    trade_deals = await client.fetch_recent_months(parsed.lawd_cd, months=6, kind="trade")

    # 3. 정규화 + 필터링
    nearby = market_rules.filter_nearby(rent_deals, trade_deals, parsed, area_sqm)

    # 4. 시세 진단
    market_analysis = market_rules.diagnose(nearby, user_deposit, area_sqm)

    # 5. 전세가율 진단
    jeonse_analysis = jeonse_rules.diagnose(
        nearby, user_deposit, confidence=market_analysis.confidence
    )

    # 6. risk_signal 수집
    risk_signals = [*market_analysis.signals, *jeonse_analysis.signals]

    # 7. Solar Pro 요약 (stub)
    summary = solar_pro.generate_diagnosis_summary({
        "address": parsed.normalized,
        "market_analysis": market_analysis.to_dict(),
        "jeonse_analysis": jeonse_analysis.to_dict(),
        "risk_signals": [s.to_dict() for s in risk_signals],
    })

    # 8. 근거 표본 첨부 — UI에서 "상세 보기"로 펼쳐서 보여줄 용도.
    market_dict = market_analysis.to_dict()
    market_dict["rent_samples"] = _pick_samples(nearby.rent_deals, "deposit_won")
    market_dict["trade_samples"] = _pick_samples(nearby.trade_deals, "price_won")

    return {
        "address": parsed.normalized,
        "market_analysis": market_dict,
        "jeonse_ratio_analysis": jeonse_analysis.to_dict(),
        "risk_signals": [s.to_dict() for s in risk_signals],
        "summary": summary,
        "missing_information": _collect_missing_info(nearby, jeonse_analysis),
        "disclaimer": DISCLAIMER,
    }


def _pick_samples(deals: list[dict], price_field: str, limit: int = 10) -> list[dict]:
    """필터링된 거래 중 최근 N건을 UI용 dict로 추려낸다.

    정렬: (year, month) 내림차순. 동률은 입력 순서 유지.
    누출 방지: 응답 본문에는 표시 필드만 남기고 raw 원본은 빼낸다.
    """
    def sort_key(d: dict) -> tuple[int, int]:
        try:
            return (int(d.get("year") or 0), int(d.get("month") or 0))
        except (TypeError, ValueError):
            return (0, 0)

    ranked = sorted(deals, key=sort_key, reverse=True)[:limit]
    samples = []
    for d in ranked:
        samples.append({
            "apt_name": d.get("apt_name"),
            "dong": d.get("dong"),
            "area_sqm": d.get("area"),
            "price_won": d.get(price_field),
            "floor": d.get("floor"),
            "year": d.get("year"),
            "month": d.get("month"),
        })
    return samples


def _collect_missing_info(nearby, jeonse_analysis) -> list[str]:
    items: list[str] = []
    if nearby.trade_count == 0:
        items.append("매매 실거래 데이터 없음 - 전세가율 산정 불가")
    if nearby.scope in ("gu", "gu_all"):
        items.append("단지·동 단위 매칭 부족 - 시군구 단위로 폴백됨")
    return items
