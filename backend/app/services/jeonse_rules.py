"""전세가율(jeonse_ratio) 진단 룰 엔진.

명세서 7.6, 7.7절의 전세가율 계산 및 깡통전세 위험 판정을 담당한다.
"""
from dataclasses import dataclass, field
from typing import Optional

from app.core.risk_signals import RiskSignal, Severity
from app.services.market_rules import NearbyFilterResult, calculate_averages


# ============================================================
# 1. 전세가율 계산 및 위험 판정
# ============================================================

def diagnose_jeonse_ratio(
    user_deposit: int,
    avg_jeonse: Optional[float],
    avg_sale: Optional[float],
) -> dict:
    """전세가율 두 종류를 계산하고 위험 단계를 판정한다.

    명세서 7.7절 4단계:
        >= 0.90 → very_high
        >= 0.80 → high
        >= 0.70 → caution
        < 0.70  → safe

    매매 데이터가 없으면 risk_level은 None.

    Returns:
        {
            "user_jeonse_rate": float | None,
            "market_jeonse_rate": float | None,
            "risk_level": str | None,
        }
    """
    if avg_sale is None or avg_sale == 0:
        return {
            "user_jeonse_rate": None,
            "market_jeonse_rate": None,
            "risk_level": None,
        }

    user_rate = user_deposit / avg_sale
    market_rate = avg_jeonse / avg_sale if avg_jeonse else None

    # 위험 판정은 사용자 전세가율 기준
    if user_rate >= 0.90:
        risk = "very_high"
    elif user_rate >= 0.80:
        risk = "high"
    elif user_rate >= 0.70:
        risk = "caution"
    else:
        risk = "safe"

    return {
        "user_jeonse_rate": round(user_rate, 4),
        "market_jeonse_rate": round(market_rate, 4) if market_rate else None,
        "risk_level": risk,
    }


# ============================================================
# 2. Risk Signal 생성
# ============================================================

def build_jeonse_signals(
    user_jeonse_rate: Optional[float],
    risk_level: Optional[str],
    confidence: str,
) -> list[RiskSignal]:
    """전세가율 위험 단계를 risk_signal로 변환."""

    if risk_level is None:
        # 매매 데이터 부재
        return [RiskSignal(
            code="NO_SALE_TRANSACTION_DATA",
            title="매매 실거래 데이터 없음",
            severity=Severity.INFO,
            confidence="high",
            evidence={},
            source="MOLIT_REALTIME_TRADE",
            recommended_action="전세가율 산정이 불가능합니다. 공시가격을 참고하거나 직접 매매 시세를 확인하세요.",
        )]

    signals: list[RiskSignal] = []
    rate_pct = round(user_jeonse_rate * 100, 1) if user_jeonse_rate else 0

    if risk_level == "very_high":
        signals.append(RiskSignal(
            code="JEONSE_RATIO_OVER_90",
            title=f"전세가율 {rate_pct}% — 깡통전세 위험 매우 높음",
            severity=Severity.CRITICAL,
            confidence=confidence,
            evidence={"user_jeonse_rate": user_jeonse_rate},
            source="MOLIT_REALTIME_TRADE",
            recommended_action="HUG 보증보험 가입을 반드시 확인하고, 가입이 어렵다면 계약을 재검토하세요.",
        ))
    elif risk_level == "high":
        signals.append(RiskSignal(
            code="JEONSE_RATIO_OVER_80",
            title=f"전세가율 {rate_pct}% — 주의 필요",
            severity=Severity.WARNING,
            confidence=confidence,
            evidence={"user_jeonse_rate": user_jeonse_rate},
            source="MOLIT_REALTIME_TRADE",
            recommended_action="HUG 보증보험 가입 가능 여부를 확인하세요.",
        ))
    elif risk_level == "caution":
        signals.append(RiskSignal(
            code="JEONSE_RATIO_OVER_70",
            title=f"전세가율 {rate_pct}% — 주의 구간",
            severity=Severity.CAUTION,
            confidence=confidence,
            evidence={"user_jeonse_rate": user_jeonse_rate},
            source="MOLIT_REALTIME_TRADE",
            recommended_action="안전 범위에 가깝지만 보증보험 가입을 고려해보세요.",
        ))
    # safe는 신호 없음

    return signals


# ============================================================
# 3. 통합 진단 결과
# ============================================================

@dataclass
class JeonseRatioAnalysis:
    user_jeonse_rate: Optional[float]
    market_jeonse_rate: Optional[float]
    risk_level: Optional[str]
    signals: list[RiskSignal] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "user_jeonse_rate": self.user_jeonse_rate,
            "market_jeonse_rate": self.market_jeonse_rate,
            "risk_level": self.risk_level,
        }


def diagnose(
    nearby: NearbyFilterResult,
    user_deposit: int,
    confidence: str = "medium",
) -> JeonseRatioAnalysis:
    """전세가율 진단의 진입점."""
    avg_jeonse, avg_sale = calculate_averages(nearby)

    ratio_result = diagnose_jeonse_ratio(user_deposit, avg_jeonse, avg_sale)
    signals = build_jeonse_signals(
        user_jeonse_rate=ratio_result["user_jeonse_rate"],
        risk_level=ratio_result["risk_level"],
        confidence=confidence,
    )

    return JeonseRatioAnalysis(
        user_jeonse_rate=ratio_result["user_jeonse_rate"],
        market_jeonse_rate=ratio_result["market_jeonse_rate"],
        risk_level=ratio_result["risk_level"],
        signals=signals,
    )
