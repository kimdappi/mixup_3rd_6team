from dataclasses import dataclass
from statistics import mean

from app.clients.molit import RentTransaction, TradeTransaction
from app.models.schemas import MarketAnalysis, RiskSignal


@dataclass(frozen=True)
class MarketDiagnosisResult:
    market_analysis: MarketAnalysis
    risk_signals: list[RiskSignal]


SCOPE_LABELS = {
    "complex": "단지",
    "dong": "동",
    "gu": "구",
    "gu_all": "구 전체",
}


def _gangtong_risk(rate: float | None) -> str:
    if rate is None:
        return "null"
    if rate >= 0.90:
        return "very_high"
    if rate >= 0.80:
        return "high"
    if rate >= 0.70:
        return "caution"
    return "safe"


def _confidence(rent_count: int, trade_count: int, scope: str) -> tuple[str, str]:
    if rent_count >= 10 and trade_count >= 5 and scope not in ("gu", "gu_all"):
        return "high", "높음"
    if (rent_count >= 5 and trade_count >= 3) or (scope == "complex" and rent_count >= 3):
        return "medium", "보통"
    return "low", "낮음"


def _deposit_status(deposit_ratio: float) -> str:
    if deposit_ratio > 1.15:
        return "overpriced"
    if deposit_ratio > 1.05:
        return "slightly_high"
    if deposit_ratio >= 0.90:
        return "fair"
    if deposit_ratio >= 0.75:
        return "cheap"
    return "suspicious"


def diagnose_market(
    *,
    address: str,
    user_deposit: int,
    rent_scope: str,
    rents: list[RentTransaction],
    trade_scope: str,
    trades: list[TradeTransaction],
) -> MarketDiagnosisResult:
    rent_count = len(rents)
    trade_count = len(trades)
    avg_jeonse = int(mean([item.deposit for item in rents])) if rents else None
    avg_sale = int(mean([item.price for item in trades])) if trades else None

    user_jeonse_rate = user_deposit / avg_sale if avg_sale else None
    market_jeonse_rate = avg_jeonse / avg_sale if avg_jeonse and avg_sale else None
    gangtong = _gangtong_risk(user_jeonse_rate)

    confidence, confidence_label = _confidence(rent_count, trade_count, rent_scope)
    confidence_reason = f"{SCOPE_LABELS.get(rent_scope, rent_scope)} 기준 전세 {rent_count}건 · 매매 {trade_count}건 (국토부 아파트 전용)"

    signals: list[RiskSignal] = []
    details: list[str] = []

    if avg_jeonse:
        deposit_ratio = user_deposit / avg_jeonse
        status = _deposit_status(deposit_ratio)
        details.append(f"입력 보증금은 평균 전세 보증금 대비 {deposit_ratio:.1%} 수준입니다.")
        if status == "overpriced":
            signals.append(RiskSignal(code="MARKET_RENT_OVERPRICED", title="전세 보증금 과다", severity="medium", confidence=confidence, evidence="주변 평균 전세보다 15% 초과", source="market_diagnosis", recommended_action="동일 단지와 주변 거래를 추가 확인하세요."))
        elif status == "slightly_high":
            signals.append(RiskSignal(code="MARKET_RENT_SLIGHTLY_HIGH", title="전세 보증금 다소 높음", severity="low", confidence=confidence, evidence="주변 평균 전세보다 5% 초과", source="market_diagnosis", recommended_action="가격 협상 또는 추가 거래 사례 확인이 필요합니다."))
        elif status == "cheap":
            signals.append(RiskSignal(code="MARKET_RENT_CHEAP", title="전세 보증금 저렴", severity="info", confidence=confidence, evidence="주변 평균 전세보다 낮음", source="market_diagnosis", recommended_action="저렴한 사유를 확인하세요."))
        elif status == "suspicious":
            signals.append(RiskSignal(code="MARKET_RENT_SUSPICIOUSLY_LOW", title="비정상 저가 가능성", severity="medium", confidence=confidence, evidence="주변 평균 전세보다 25% 이상 낮음", source="market_diagnosis", recommended_action="허위매물 또는 특수 조건 여부를 확인하세요."))

    if user_jeonse_rate is None:
        signals.append(RiskSignal(code="NO_SALE_TRANSACTION_DATA", title="매매 거래 없음", severity="info", confidence="low", evidence="최근 6개월 매매 거래 표본 없음", source="market_diagnosis", recommended_action="매매가 기반 전세가율 판단을 보류하세요."))
    elif user_jeonse_rate >= 0.90:
        signals.append(RiskSignal(code="JEONSE_RATIO_OVER_90", title="전세가율 매우 높음", severity="critical", confidence=confidence, evidence=f"전세가율 {user_jeonse_rate:.1%}", source="market_diagnosis", recommended_action="계약 전 HUG 가입 가능성과 선순위 권리를 반드시 확인하세요."))
    elif user_jeonse_rate >= 0.80:
        signals.append(RiskSignal(code="JEONSE_RATIO_OVER_80", title="전세가율 높음", severity="high", confidence=confidence, evidence=f"전세가율 {user_jeonse_rate:.1%}", source="market_diagnosis", recommended_action="보증보험 가입 가능 여부를 확인하세요."))
    elif user_jeonse_rate >= 0.70:
        signals.append(RiskSignal(code="JEONSE_RATIO_OVER_70", title="전세가율 주의", severity="medium", confidence=confidence, evidence=f"전세가율 {user_jeonse_rate:.1%}", source="market_diagnosis", recommended_action="집값 하락 가능성을 감안해 등기부와 보증 가능성을 확인하세요."))

    if confidence == "low":
        signals.append(RiskSignal(code="LOW_MARKET_CONFIDENCE", title="시세 추정 신뢰도 낮음", severity="info", confidence="low", evidence=confidence_reason, source="market_diagnosis", recommended_action="실거래 표본이 적어 추가 자료 확인이 필요합니다."))

    grade = "safe"
    if gangtong in ("caution", "high"):
        grade = "warning"
    if gangtong == "very_high":
        grade = "danger"

    market_analysis = MarketAnalysis(
        average_market_price=avg_sale,
        deposit=user_deposit,
        jeonse_ratio=user_jeonse_rate,
        grade=grade,
        conversational=f"{address}에 대해 국토교통부 아파트 실거래 기준으로 시세와 전세가율을 추정했습니다.",
        details=details,
        gangtong_risk=gangtong,
        confidence=confidence,
        confidence_label=confidence_label,
        confidence_reason=confidence_reason,
        jeonse_count=rent_count,
        trade_count=trade_count,
        market_jeonse_rate=market_jeonse_rate,
        user_jeonse_rate=user_jeonse_rate,
    )
    return MarketDiagnosisResult(market_analysis=market_analysis, risk_signals=signals)
