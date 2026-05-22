"""risk_signal 코드와 메타데이터 정의."""
from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    INFO = "info"
    CAUTION = "caution"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class RiskSignal:
    code: str
    title: str
    severity: Severity
    confidence: str  # "high" | "medium" | "low"
    evidence: dict = field(default_factory=dict)
    source: str = ""
    recommended_action: str = ""

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "title": self.title,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "source": self.source,
            "recommended_action": self.recommended_action,
        }


# 시세 진단 risk signal 코드
MARKET_SIGNAL_CODES = {
    "MARKET_RENT_OVERPRICED",
    "MARKET_RENT_SLIGHTLY_HIGH",
    "MARKET_RENT_CHEAP",
    "MARKET_RENT_SUSPICIOUSLY_LOW",
    "JEONSE_RATIO_OVER_70",
    "JEONSE_RATIO_OVER_80",
    "JEONSE_RATIO_OVER_90",
    "LOW_MARKET_CONFIDENCE",
    "NO_SALE_TRANSACTION_DATA",
}
