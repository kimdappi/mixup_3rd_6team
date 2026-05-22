"""시세 진단 룰 엔진.

명세서 7.4 ~ 7.9절을 코드로 구현한다.
계산과 판정만 수행하며, 자연어 설명은 Solar Pro가 담당한다.
"""
from dataclasses import dataclass, field
from statistics import mean
from typing import Optional

from app.core.risk_signals import RiskSignal, Severity
from app.services.address_parser import ParsedAddress

AREA_TOLERANCE = 0.20  # 면적 ±20%
MIN_DEALS_FOR_SCOPE = 3  # 각 단계 채택 최소 거래 수


# ============================================================
# 1. 데이터 정규화
# ============================================================

def _to_int_won(value) -> Optional[int]:
    """국토부 금액 필드(만원 단위, 콤마 포함 문자열)를 원 단위 int로 변환."""
    if value is None or value == "":
        return None
    try:
        cleaned = str(value).replace(",", "").strip()
        return int(cleaned) * 10000
    except (ValueError, TypeError):
        return None


def _to_float(value) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def normalize_rent_deal(raw: dict) -> Optional[dict]:
    """원본 전세 거래를 표준 dict로 변환. 월세 거래는 None 반환."""
    monthly = raw.get("월세금액") or raw.get("monthlyRent") or 0
    try:
        monthly_int = int(str(monthly).replace(",", "").strip() or 0)
    except (ValueError, TypeError):
        monthly_int = 0

    # 월세 거래 제외 (보증금만 있는 순수 전세만 사용)
    if monthly_int != 0:
        return None

    deposit = _to_int_won(raw.get("보증금액") or raw.get("deposit"))
    area = _to_float(raw.get("전용면적") or raw.get("excluUseAr"))
    apt_name = raw.get("아파트") or raw.get("aptNm") or ""
    dong = raw.get("법정동") or raw.get("umdNm") or ""

    if deposit is None or area is None:
        return None

    return {
        "apt_name": str(apt_name).strip(),
        "dong": str(dong).strip(),
        "area": area,
        "deposit_won": deposit,
        "floor": raw.get("층") or raw.get("floor"),
        "year": raw.get("년") or raw.get("dealYear"),
        "month": raw.get("월") or raw.get("dealMonth"),
    }


def normalize_trade_deal(raw: dict) -> Optional[dict]:
    """원본 매매 거래를 표준 dict로 변환. 취소 거래는 None 반환."""
    cancelled = raw.get("해제여부") or raw.get("dealingGbn") or ""
    if str(cancelled).strip().upper() == "Y":
        return None

    price = _to_int_won(raw.get("거래금액") or raw.get("dealAmount"))
    area = _to_float(raw.get("전용면적") or raw.get("excluUseAr"))
    apt_name = raw.get("아파트") or raw.get("aptNm") or ""
    dong = raw.get("법정동") or raw.get("umdNm") or ""

    if price is None or area is None:
        return None

    return {
        "apt_name": str(apt_name).strip(),
        "dong": str(dong).strip(),
        "area": area,
        "price_won": price,
        "floor": raw.get("층") or raw.get("floor"),
        "year": raw.get("년") or raw.get("dealYear"),
        "month": raw.get("월") or raw.get("dealMonth"),
    }


def _is_area_match(item_area: float, user_area: float) -> bool:
    if user_area <= 0:
        return False
    return abs(item_area - user_area) / user_area <= AREA_TOLERANCE


# ============================================================
# 2. 계층적 근처 필터
# ============================================================

@dataclass
class NearbyFilterResult:
    """필터링 결과. 전세와 매매는 독립적으로 scope가 결정될 수 있다."""
    rent_deals: list[dict]
    trade_deals: list[dict]
    rent_scope: str   # 'complex' | 'dong' | 'gu' | 'gu_all'
    trade_scope: str

    @property
    def scope(self) -> str:
        """대표 scope. 명세서에 따라 전세 기준."""
        return self.rent_scope

    @property
    def jeonse_count(self) -> int:
        return len(self.rent_deals)

    @property
    def trade_count(self) -> int:
        return len(self.trade_deals)


def _filter_by_scope(
    deals: list[dict],
    parsed: ParsedAddress,
    area_sqm: float,
) -> tuple[list[dict], str]:
    """단일 거래 풀(전세 또는 매매)에 대해 계층적 필터를 수행."""

    # 1단계: complex (아파트명 prefix + 동 + 면적)
    if parsed.apt_prefix and parsed.dong:
        complex_deals = [
            d for d in deals
            if d["apt_name"].startswith(parsed.apt_prefix)
            and parsed.dong in d["dong"]
            and _is_area_match(d["area"], area_sqm)
        ]
        if len(complex_deals) >= MIN_DEALS_FOR_SCOPE:
            return complex_deals, "complex"

    # 2단계: dong (같은 동 + 면적)
    if parsed.dong:
        dong_deals = [
            d for d in deals
            if parsed.dong in d["dong"]
            and _is_area_match(d["area"], area_sqm)
        ]
        if len(dong_deals) >= MIN_DEALS_FOR_SCOPE:
            return dong_deals, "dong"

    # 3단계: gu (시군구 + 면적)
    gu_deals = [
        d for d in deals
        if _is_area_match(d["area"], area_sqm)
    ]
    if len(gu_deals) >= MIN_DEALS_FOR_SCOPE:
        return gu_deals, "gu"

    # 4단계: gu_all (시군구 전체)
    return deals, "gu_all"


def filter_nearby(
    rent_deals_raw: list[dict],
    trade_deals_raw: list[dict],
    parsed: ParsedAddress,
    area_sqm: float,
) -> NearbyFilterResult:
    """전세·매매를 독립적으로 필터링한다."""

    # 정규화
    rent_normalized = [
        d for d in (normalize_rent_deal(r) for r in rent_deals_raw) if d
    ]
    trade_normalized = [
        d for d in (normalize_trade_deal(r) for r in trade_deals_raw) if d
    ]

    rent_filtered, rent_scope = _filter_by_scope(rent_normalized, parsed, area_sqm)
    trade_filtered, trade_scope = _filter_by_scope(trade_normalized, parsed, area_sqm)

    return NearbyFilterResult(
        rent_deals=rent_filtered,
        trade_deals=trade_filtered,
        rent_scope=rent_scope,
        trade_scope=trade_scope,
    )


# ============================================================
# 3. 평균 계산 및 보증금 상태 판정
# ============================================================

def calculate_averages(
    nearby: NearbyFilterResult,
) -> tuple[Optional[float], Optional[float]]:
    """전세·매매 평균을 원 단위로 반환. 거래가 없으면 None."""
    avg_jeonse = (
        mean(d["deposit_won"] for d in nearby.rent_deals)
        if nearby.rent_deals else None
    )
    avg_sale = (
        mean(d["price_won"] for d in nearby.trade_deals)
        if nearby.trade_deals else None
    )
    return avg_jeonse, avg_sale


def diagnose_deposit_status(
    user_deposit: int,
    avg_jeonse: Optional[float],
) -> tuple[Optional[float], Optional[str]]:
    """보증금이 인근 시세 대비 어떤 수준인지 판정.

    명세서 7.6절 5단계:
        > 1.15  → overpriced
        > 1.05  → slightly_high
        >= 0.90 → fair
        >= 0.75 → cheap
        그 외   → suspicious
    """
    if avg_jeonse is None or avg_jeonse == 0:
        return None, None

    ratio = user_deposit / avg_jeonse

    if ratio > 1.15:
        status = "overpriced"
    elif ratio > 1.05:
        status = "slightly_high"
    elif ratio >= 0.90:
        status = "fair"
    elif ratio >= 0.75:
        status = "cheap"
    else:
        status = "suspicious"

    return ratio, status


# ============================================================
# 4. 신뢰도 판정
# ============================================================

def judge_confidence(
    nearby: NearbyFilterResult,
) -> tuple[str, str]:
    """명세서 7.8절 신뢰도 3단계 판정.

    Returns:
        (confidence, reason_text)
    """
    jc = nearby.jeonse_count
    tc = nearby.trade_count
    scope = nearby.scope

    if jc >= 10 and tc >= 5 and scope not in ("gu", "gu_all"):
        confidence = "high"
    elif (jc >= 5 and tc >= 3) or (scope == "complex" and jc >= 3):
        confidence = "medium"
    else:
        confidence = "low"

    scope_label = {
        "complex": "동일 단지",
        "dong": "같은 동",
        "gu": "같은 시군구",
        "gu_all": "시군구 전체",
    }.get(scope, scope)

    reason = (
        f"{scope_label} 기준 전세 {jc}건 · 매매 {tc}건 (국토부 아파트 전용)"
    )
    return confidence, reason


# ============================================================
# 5. Risk Signal 생성
# ============================================================

def build_market_signals(
    deposit_ratio: Optional[float],
    deposit_status: Optional[str],
    avg_jeonse: Optional[float],
    confidence: str,
) -> list[RiskSignal]:
    """deposit_status를 risk_signal 리스트로 변환."""
    signals: list[RiskSignal] = []

    if deposit_status == "overpriced":
        signals.append(RiskSignal(
            code="MARKET_RENT_OVERPRICED",
            title="보증금이 인근 시세보다 매우 높음",
            severity=Severity.WARNING,
            confidence=confidence,
            evidence={
                "deposit_ratio": round(deposit_ratio, 3),
                "avg_jeonse_won": int(avg_jeonse) if avg_jeonse else None,
            },
            source="MOLIT_REALTIME_TRADE",
            recommended_action="동일 단지 최근 실거래 사례를 다시 확인해보세요.",
        ))
    elif deposit_status == "slightly_high":
        signals.append(RiskSignal(
            code="MARKET_RENT_SLIGHTLY_HIGH",
            title="보증금이 인근 평균보다 다소 높음",
            severity=Severity.CAUTION,
            confidence=confidence,
            evidence={"deposit_ratio": round(deposit_ratio, 3)},
            source="MOLIT_REALTIME_TRADE",
            recommended_action="협상 여지가 있는지 확인해보세요.",
        ))
    elif deposit_status == "cheap":
        signals.append(RiskSignal(
            code="MARKET_RENT_CHEAP",
            title="보증금이 인근 평균보다 저렴함",
            severity=Severity.INFO,
            confidence=confidence,
            evidence={"deposit_ratio": round(deposit_ratio, 3)},
            source="MOLIT_REALTIME_TRADE",
            recommended_action="조건이 좋은 매물일 수 있으나 권리관계도 확인하세요.",
        ))
    elif deposit_status == "suspicious":
        signals.append(RiskSignal(
            code="MARKET_RENT_SUSPICIOUSLY_LOW",
            title="보증금이 인근 평균 대비 비정상적으로 낮음",
            severity=Severity.WARNING,
            confidence=confidence,
            evidence={"deposit_ratio": round(deposit_ratio, 3)},
            source="MOLIT_REALTIME_TRADE",
            recommended_action="너무 저렴한 매물은 권리관계에 문제가 있을 수 있으니 등기부등본을 반드시 확인하세요.",
        ))

    # 신뢰도 낮음 신호
    if confidence == "low":
        signals.append(RiskSignal(
            code="LOW_MARKET_CONFIDENCE",
            title="시세 비교 데이터 표본 부족",
            severity=Severity.INFO,
            confidence="high",
            evidence={},
            source="MOLIT_REALTIME_TRADE",
            recommended_action="이 진단은 시군구 단위 데이터로 추정되었습니다. 동일 단지 시세를 별도 확인하세요.",
        ))

    return signals


# ============================================================
# 6. 통합 진단 결과
# ============================================================

@dataclass
class MarketAnalysis:
    avg_jeonse: Optional[int]
    avg_sale: Optional[int]
    deposit_ratio: Optional[float]
    deposit_status: Optional[str]
    scope: str
    jeonse_count: int
    trade_count: int
    confidence: str
    confidence_reason: str
    signals: list[RiskSignal] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "avg_jeonse": self.avg_jeonse,
            "avg_sale": self.avg_sale,
            "deposit_ratio": self.deposit_ratio,
            "deposit_status": self.deposit_status,
            "scope": self.scope,
            "jeonse_count": self.jeonse_count,
            "trade_count": self.trade_count,
            "confidence": self.confidence,
            "confidence_reason": self.confidence_reason,
        }


def diagnose(
    nearby: NearbyFilterResult,
    user_deposit: int,
    area_sqm: float,
) -> MarketAnalysis:
    """시세 진단의 진입점. filter_nearby 결과를 받아 MarketAnalysis를 만든다."""
    avg_jeonse, avg_sale = calculate_averages(nearby)
    deposit_ratio, deposit_status = diagnose_deposit_status(user_deposit, avg_jeonse)
    confidence, confidence_reason = judge_confidence(nearby)

    signals = build_market_signals(
        deposit_ratio=deposit_ratio,
        deposit_status=deposit_status,
        avg_jeonse=avg_jeonse,
        confidence=confidence,
    )

    return MarketAnalysis(
        avg_jeonse=int(avg_jeonse) if avg_jeonse else None,
        avg_sale=int(avg_sale) if avg_sale else None,
        deposit_ratio=round(deposit_ratio, 3) if deposit_ratio else None,
        deposit_status=deposit_status,
        scope=nearby.scope,
        jeonse_count=nearby.jeonse_count,
        trade_count=nearby.trade_count,
        confidence=confidence,
        confidence_reason=confidence_reason,
        signals=signals,
    )
