from typing import Literal

from pydantic import BaseModel, Field


RiskSeverity = Literal["info", "low", "medium", "high", "critical"]
Confidence = Literal["high", "medium", "low", "null"]


class QuickDiagnosisRequest(BaseModel):
    address: str
    area_sqm: float = Field(gt=0)
    user_deposit: int = Field(gt=0)
    housing_type: str = "apartment"
    contract_stage: str = "before_contract"


class RiskSignal(BaseModel):
    code: str
    title: str
    severity: RiskSeverity
    confidence: str
    evidence: str
    source: str
    recommended_action: str


class OverallRisk(BaseModel):
    grade: Literal["A", "B", "C", "D"]
    score: int
    level: Literal["안전", "주의", "위험", "매우 위험"]
    one_line_summary: str


class MarketAnalysis(BaseModel):
    average_market_price: int | None
    deposit: int
    jeonse_ratio: float | None
    grade: Literal["safe", "warning", "danger"]
    conversational: str
    details: list[str]
    gangtong_risk: Literal["very_high", "high", "caution", "safe", "null"]
    confidence: Confidence
    confidence_label: Literal["높음", "보통", "낮음", "null"]
    confidence_reason: str | None
    jeonse_count: int
    trade_count: int
    market_jeonse_rate: float | None
    user_jeonse_rate: float | None


class RegistryAnalysis(BaseModel):
    mortgage_max: int = 0
    has_trust: bool = False
    has_seizure: bool = False
    grade: Literal["safe", "warning", "danger"] = "safe"
    conversational: str = "문서가 업로드되지 않아 등기부 분석을 보류했습니다."
    details: list[str] = Field(default_factory=list)


class InsuranceAnalysis(BaseModel):
    eligible: bool | None
    grade: Literal["safe", "warning", "danger"]
    conversational: str
    details: list[str]


class TransactionItem(BaseModel):
    name: str
    dong: str
    area: float
    floor: str | None
    deposit: int
    year: str
    month: str


class TradeItem(BaseModel):
    name: str
    dong: str
    area: float
    floor: str | None
    price: int
    year: str
    month: str


class DiagnosisResponse(BaseModel):
    address: str
    overall_risk: OverallRisk
    market_analysis: MarketAnalysis
    registry_analysis: RegistryAnalysis
    insurance_analysis: InsuranceAnalysis
    checklist: list[str]
    transaction_items: list[TransactionItem]
    trade_items: list[TradeItem]
    risk_signals: list[RiskSignal]
    missing_information: list[str]
    saju_unlocked: bool = True
    saju_lock_message: str | None = None
