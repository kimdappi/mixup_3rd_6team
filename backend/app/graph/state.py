from typing import TypedDict

from app.clients.molit import RentTransaction, TradeTransaction
from app.models.diagnoses_models import DiagnosisResponse, QuickDiagnosisRequest, RiskSignal
from app.services.address_parser import ParsedAddress


class DiagnosisState(TypedDict, total=False):
    request: QuickDiagnosisRequest
    parsed_address: ParsedAddress
    rents: list[RentTransaction]
    trades: list[TradeTransaction]
    rent_scope: str
    scoped_rents: list[RentTransaction]
    trade_scope: str
    scoped_trades: list[TradeTransaction]
    risk_signals: list[RiskSignal]
    response: DiagnosisResponse
