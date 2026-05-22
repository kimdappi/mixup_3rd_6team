"""전세가율(jeonse_ratio) 진단 룰 엔진.

명세서 7.6, 7.7절의 전세가율 계산 및 깡통전세 위험 판정을 담당한다.
"""
from dataclasses import dataclass, field
from typing import Optional

from app.core.risk_signals import RiskSignal, Severity
from app.services.market_rules import NearbyFilterResult, calculate_averages

# ============================================================
# 비슷한 매물 선별 (v3 — LLM 리포트의 "비슷한 매물" 항목 근거 데이터)
# ============================================================

SIMILAR_LISTING_TOLERANCE = 0.10  # ±10%
SIMILAR_LISTING_MAX = 3


def select_similar_listings(
    user_deposit: float,
    samples: list[dict],
    tolerance: float = SIMILAR_LISTING_TOLERANCE,
    max_count: int = SIMILAR_LISTING_MAX,
) -> list[dict]:
    """제시 보증금 ±tolerance 범위 내 표본을 선별.

    Args:
        user_deposit: 사용자가 입력한 보증금 (원 단위 — 코드베이스 통일 단위)
        samples: diagnosis_agent._pick_samples 결과. 각 dict는
                 `price_won`, `area_sqm`, `apt_name`, `dong`, `floor`,
                 `year`, `month` 필드를 가진다.
        tolerance: 허용 오차 (0.10 = ±10%)
        max_count: 최대 반환 개수

    Returns:
        조건 매칭 표본 리스트 (거래일 최근순 max_count개).
        매칭이 0건이면 빈 리스트.

    선별 규칙:
        - |sample.price_won - user_deposit| / user_deposit <= tolerance
        - 매칭이 max_count보다 많으면 (year, month) 내림차순으로 자르기
        - 단위는 원으로 통일되어 있다고 가정 (`_pick_samples` 출력 구조)
    """
    if not user_deposit or not samples:
        return []

    matched: list[dict] = []
    for s in samples:
        price = s.get("price_won")
        if not price:
            continue
        diff_ratio = abs(price - user_deposit) / user_deposit
        if diff_ratio <= tolerance:
            matched.append(s)

    # 거래일 내림차순 정렬. (year, month) 튜플 비교가 가장 안전 — 문자열 정렬은
    # zero-padding 누락 시 깨질 수 있다.
    def sort_key(s: dict) -> tuple[int, int]:
        try:
            return (int(s.get("year") or 0), int(s.get("month") or 0))
        except (TypeError, ValueError):
            return (0, 0)

    matched.sort(key=sort_key, reverse=True)
    return matched[:max_count]


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
            recommended_action="전세가율이 매우 높아 보증금 회수 위험이 큽니다. 임대인 채무·국세 체납 여부, 등기부 권리관계를 면밀히 점검하고, 가능하면 반전세 전환을 검토하세요.",
        ))
    elif risk_level == "high":
        signals.append(RiskSignal(
            code="JEONSE_RATIO_OVER_80",
            title=f"전세가율 {rate_pct}% — 주의 필요",
            severity=Severity.WARNING,
            confidence=confidence,
            evidence={"user_jeonse_rate": user_jeonse_rate},
            source="MOLIT_REALTIME_TRADE",
            recommended_action="임대인의 미납 국세·근저당 등 선순위 권리관계를 등기부등본에서 직접 확인하세요.",
        ))
    elif risk_level == "caution":
        signals.append(RiskSignal(
            code="JEONSE_RATIO_OVER_70",
            title=f"전세가율 {rate_pct}% — 주의 구간",
            severity=Severity.CAUTION,
            confidence=confidence,
            evidence={"user_jeonse_rate": user_jeonse_rate},
            source="MOLIT_REALTIME_TRADE",
            recommended_action="안전 범위에 가깝지만, 등기부등본의 선순위 권리관계는 한 번 더 확인하세요.",
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
