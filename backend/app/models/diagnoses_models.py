from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RiskSeverity = Literal["info", "low", "medium", "high", "critical"]
Confidence = Literal["high", "medium", "low", "null"]


# ── 요청 ──────────────────────────────────────────────────────────
class QuickDiagnosisRequest(BaseModel):
    address: str
    area_sqm: float = Field(gt=0)
    user_deposit: int = Field(gt=0)
    housing_type: str = "apartment"
    contract_stage: str = "before_contract"


# ── 공통 ─────────────────────────────────────────────────────────
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


# ── 시세 분석 ─────────────────────────────────────────────────────
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


# ── 문서 파싱 결과 ────────────────────────────────────────────────
class ParsedRegistry(BaseModel):
    """등기부등본 구조화 파싱 결과"""
    owner: str | None = None
    address: str | None = None
    issue_date: str | None = None
    mortgage_total: int = 0          # 근저당 채권최고액 합계(원)
    has_trust: bool = False
    has_seizure: bool = False         # 압류
    has_provisional_seizure: bool = False  # 가압류
    has_provisional_disposition: bool = False  # 가처분
    has_auction: bool = False         # 경매개시결정
    has_lease_right: bool = False     # 전세권·임차권 등기
    mortgage_details: list[str] = Field(default_factory=list)
    raw_text: str = ""


class ParsedLedger(BaseModel):
    """건축물대장 구조화 파싱 결과"""
    address: str | None = None
    exclusive_area: float | None = None   # 전용면적(㎡)
    main_purpose: str | None = None       # 주용도
    approval_date: str | None = None      # 사용승인일
    has_illegal_building: bool = False    # 위반건축물 여부
    ledger_type: str | None = None        # 대장 종류
    raw_text: str = ""


class ParsedContract(BaseModel):
    """임대차계약서 초안 구조화 파싱 결과"""
    address: str | None = None
    landlord: str | None = None
    tenant: str | None = None
    deposit: int | None = None
    contract_start: str | None = None
    contract_end: str | None = None
    balance_date: str | None = None
    has_special_terms: bool = False
    has_bank_account: bool = False
    raw_text: str = ""


# ── 문서 분석 ─────────────────────────────────────────────────────
class DocumentAnalysis(BaseModel):
    registry_grade: Literal["safe", "warning", "danger", "missing"] = "missing"
    ledger_grade: Literal["safe", "warning", "danger", "missing"] = "missing"
    contract_grade: Literal["safe", "warning", "danger", "missing"] = "missing"
    cross_check_results: list[str] = Field(default_factory=list)
    details: list[str] = Field(default_factory=list)


# ── 등기부 분석 (프론트 호환 필드) ────────────────────────────────
class RegistryAnalysis(BaseModel):
    mortgage_max: int = 0
    has_trust: bool = False
    has_seizure: bool = False
    grade: Literal["safe", "warning", "danger"] = "safe"
    conversational: str = "문서가 업로드되지 않아 등기부 분석을 보류했습니다."
    details: list[str] = Field(default_factory=list)


# ── 보증보험 분석 ─────────────────────────────────────────────────
class InsuranceAnalysis(BaseModel):
    eligible: bool | None
    grade: Literal["safe", "warning", "danger"]
    conversational: str
    details: list[str]
    blocking_reasons: list[str] = Field(default_factory=list)
    estimated_guarantee_limit: int | None = None
    guarantee_limit_confidence: Literal["high", "medium", "low", "null"] = "null"


# ── 특약 초안 ─────────────────────────────────────────────────────
class ClauseSuggestion(BaseModel):
    risk_code: str
    draft: str
    reason: str
    condition: str
    needs_expert_review: bool = True


# ── 체크리스트 ────────────────────────────────────────────────────
class StructuredChecklist(BaseModel):
    urgent: list[str] = Field(default_factory=list)           # 지금 반드시
    before_contract: list[str] = Field(default_factory=list)  # 계약 전까지
    missing_documents: list[str] = Field(default_factory=list) # 빠진 문서
    risk_based: list[str] = Field(default_factory=list)       # 위험신호 기반 추가


# ── 거래 항목 ─────────────────────────────────────────────────────
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


# ── 최종 응답 ─────────────────────────────────────────────────────
class DiagnosisResponse(BaseModel):
    address: str
    overall_risk: OverallRisk
    market_analysis: MarketAnalysis
    registry_analysis: RegistryAnalysis
    insurance_analysis: InsuranceAnalysis
    checklist: list[str]                                          # 단순 목록 (프론트 호환)
    structured_checklist: StructuredChecklist = Field(           # 구조화 체크리스트
        default_factory=StructuredChecklist
    )
    transaction_items: list[TransactionItem]
    trade_items: list[TradeItem]
    risk_signals: list[RiskSignal]
    missing_information: list[str]
    clause_suggestions: list[ClauseSuggestion] = Field(default_factory=list)
    document_analysis: DocumentAnalysis | None = None
    saju_unlocked: bool = True
    saju_lock_message: str | None = None
