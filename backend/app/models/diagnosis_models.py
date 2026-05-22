from typing import Literal, Optional

from pydantic import BaseModel, Field


class QuickDiagnosisRequest(BaseModel):
    address: str = Field(..., min_length=2)
    user_deposit: int = Field(..., gt=0, description="보증금 (원 단위)")
    area_sqm: float = Field(..., gt=0, description="전용면적 (제곱미터)")
    housing_type: Literal["apt", "villa", "officetel"] = "apt"
    contract_stage: Optional[
        Literal["pre_view", "pre_contract", "pre_balance", "post_move_in"]
    ] = None


class RiskSignalDto(BaseModel):
    code: str
    title: str
    severity: str
    confidence: str
    evidence: dict
    source: str
    recommended_action: str


class MarketAnalysisDto(BaseModel):
    avg_jeonse: Optional[int]
    avg_sale: Optional[int]
    deposit_ratio: Optional[float]
    deposit_status: Optional[str]
    scope: str
    jeonse_count: int
    trade_count: int
    confidence: str
    confidence_reason: str
    # 근거가 된 최근 거래 표본 (UI 상세 보기용). 최대 10건씩.
    rent_samples: list[dict] = []
    trade_samples: list[dict] = []


class JeonseRatioDto(BaseModel):
    user_jeonse_rate: Optional[float]
    market_jeonse_rate: Optional[float]
    risk_level: Optional[str]


class QuickDiagnosisResponse(BaseModel):
    address: str
    market_analysis: MarketAnalysisDto
    jeonse_ratio_analysis: JeonseRatioDto
    risk_signals: list[RiskSignalDto]
    summary: str
    missing_information: list[str]
    disclaimer: str
