from datetime import date

from langgraph.graph import END, START, StateGraph

from app.clients.llm import LLMClient, ReportGenerationInput
from app.clients.molit import MolitClient, recent_deal_months
from app.graph.state import DiagnosisState
from app.models.diagnoses_models import (
    DiagnosisResponse,
    OverallRisk,
    QuickDiagnosisRequest,
    RegistryAnalysis,
    TradeItem,
    TransactionItem,
)
from app.services.address_parser import parse_address
from app.services.checklist import build_checklist
from app.services.hug_precheck import run_hug_precheck
from app.services.market_diagnosis import diagnose_market
from app.services.market_filter import select_market_scope


def _score_from_signals(codes: set[str]) -> OverallRisk:
    if "JEONSE_RATIO_OVER_90" in codes:
        return OverallRisk(grade="D", score=35, level="매우 위험", one_line_summary="전세가율이 매우 높아 계약 전 정밀 확인이 필요합니다.")
    if "JEONSE_RATIO_OVER_80" in codes:
        return OverallRisk(grade="C", score=60, level="위험", one_line_summary="전세가율이 높아 보증과 권리관계 확인이 필요합니다.")
    if "JEONSE_RATIO_OVER_70" in codes or "LOW_MARKET_CONFIDENCE" in codes:
        return OverallRisk(grade="B", score=78, level="주의", one_line_summary="일부 확인이 필요한 매물입니다.")
    return OverallRisk(grade="A", score=90, level="안전", one_line_summary="공개 실거래 기준 주요 가격 위험 신호는 낮습니다.")


def build_quick_graph(molit_client: MolitClient, llm_client: LLMClient):
    async def address_parse_node(state: DiagnosisState) -> DiagnosisState:
        return {"parsed_address": parse_address(state["request"].address)}

    async def market_data_fetch_node(state: DiagnosisState) -> DiagnosisState:
        deal_ymds = recent_deal_months(date.today(), months=6)
        parsed = state["parsed_address"]
        rents = await molit_client.fetch_rents(parsed.lawd_cd, deal_ymds)
        trades = await molit_client.fetch_trades(parsed.lawd_cd, deal_ymds)
        return {"rents": rents, "trades": trades}

    async def market_filter_node(state: DiagnosisState) -> DiagnosisState:
        request = state["request"]
        parsed = state["parsed_address"]
        scoped_rents = select_market_scope(state["rents"], parsed.dong, parsed.apt_keyword, request.area_sqm)
        scoped_trades = select_market_scope(state["trades"], parsed.dong, parsed.apt_keyword, request.area_sqm)
        return {
            "rent_scope": scoped_rents.scope,
            "scoped_rents": scoped_rents.items,
            "trade_scope": scoped_trades.scope,
            "scoped_trades": scoped_trades.items,
        }

    async def report_build_node(state: DiagnosisState) -> DiagnosisState:
        request = state["request"]
        market_result = diagnose_market(
            address=request.address,
            user_deposit=request.user_deposit,
            rent_scope=state["rent_scope"],
            rents=state["scoped_rents"],
            trade_scope=state["trade_scope"],
            trades=state["scoped_trades"],
        )
        risk_signals = list(market_result.risk_signals)
        missing_information = ["등기부등본", "건축물대장", "계약서 초안"]
        checklist = build_checklist(request.contract_stage, risk_signals, missing_information)
        insurance = run_hug_precheck(
            user_deposit=request.user_deposit,
            estimated_sale_price=market_result.market_analysis.average_market_price,
            senior_debt_amount=None,
            has_illegal_building=None,
            has_right_restriction=None,
            has_move_in_report=None,
            has_fixed_date=None,
            contract_start_date=None,
            contract_end_date=None,
            balance_date=None,
        )
        report = llm_client.generate_report(
            ReportGenerationInput(address=request.address, risk_signals=risk_signals, missing_information=missing_information)
        )
        overall = _score_from_signals({signal.code for signal in risk_signals})
        overall.one_line_summary = report.summary
        response = DiagnosisResponse(
            address=request.address,
            overall_risk=overall,
            market_analysis=market_result.market_analysis,
            registry_analysis=RegistryAnalysis(details=["문서가 업로드되지 않아 등기부 분석을 보류했습니다."]),
            insurance_analysis=insurance,
            checklist=checklist,
            transaction_items=[
                TransactionItem(
                    name=item.name,
                    dong=item.dong,
                    area=item.area,
                    floor=item.floor,
                    deposit=item.deposit,
                    year=item.year,
                    month=item.month,
                )
                for item in state["scoped_rents"]
            ],
            trade_items=[
                TradeItem(
                    name=item.name,
                    dong=item.dong,
                    area=item.area,
                    floor=item.floor,
                    price=item.price,
                    year=item.year,
                    month=item.month,
                )
                for item in state["scoped_trades"]
            ],
            risk_signals=risk_signals,
            missing_information=missing_information,
            saju_unlocked=True,
            saju_lock_message=None,
        )
        return {"risk_signals": risk_signals, "response": response}

    graph = StateGraph(DiagnosisState)
    graph.add_node("AddressParseNode", address_parse_node)
    graph.add_node("MarketDataFetchNode", market_data_fetch_node)
    graph.add_node("MarketFilterNode", market_filter_node)
    graph.add_node("ReportBuildNode", report_build_node)
    graph.add_edge(START, "AddressParseNode")
    graph.add_edge("AddressParseNode", "MarketDataFetchNode")
    graph.add_edge("MarketDataFetchNode", "MarketFilterNode")
    graph.add_edge("MarketFilterNode", "ReportBuildNode")
    graph.add_edge("ReportBuildNode", END)
    return graph.compile()


async def run_quick_diagnosis(
    *,
    request: QuickDiagnosisRequest,
    molit_client: MolitClient,
    llm_client: LLMClient,
) -> DiagnosisResponse:
    graph = build_quick_graph(molit_client, llm_client)
    state = await graph.ainvoke({"request": request})
    return state["response"]
