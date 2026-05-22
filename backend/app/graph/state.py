from __future__ import annotations

from typing import TypedDict

from app.clients.molit import RentTransaction, TradeTransaction
from app.models.diagnoses_models import (
    ClauseSuggestion,
    DiagnosisResponse,
    DocumentAnalysis,
    ParsedContract,
    ParsedLedger,
    ParsedRegistry,
    QuickDiagnosisRequest,
    RegistryAnalysis,
    RiskSignal,
    StructuredChecklist,
)
from app.services.address_parser import ParsedAddress


class DiagnosisState(TypedDict, total=False):
    # ── 입력 ─────────────────────────────────────────────────────
    request: QuickDiagnosisRequest
    uploaded_documents: list[tuple[str, bytes]]   # [(filename, bytes), ...]

    # ── 주소 파싱 ─────────────────────────────────────────────────
    parsed_address: ParsedAddress

    # ── 시세 데이터 ───────────────────────────────────────────────
    rents: list[RentTransaction]
    trades: list[TradeTransaction]
    rent_scope: str
    scoped_rents: list[RentTransaction]
    trade_scope: str
    scoped_trades: list[TradeTransaction]

    # ── 문서 파싱 ─────────────────────────────────────────────────
    parsed_registry: ParsedRegistry | None
    parsed_ledger: ParsedLedger | None
    parsed_contract: ParsedContract | None

    # ── 리스크 집계 ───────────────────────────────────────────────
    market_risk_signals: list[RiskSignal]
    document_risk_signals: list[RiskSignal]
    all_risk_signals: list[RiskSignal]

    # ── 분석 결과 ─────────────────────────────────────────────────
    registry_analysis: RegistryAnalysis
    document_analysis: DocumentAnalysis | None
    clause_suggestions: list[ClauseSuggestion]
    structured_checklist: StructuredChecklist

    # ── 최종 응답 ─────────────────────────────────────────────────
    response: DiagnosisResponse
