"""LangGraph 전세계약 리스크 진단 워크플로우 (완전 구현)

스펙 기준 노드:
  AddressParseNode → MarketDataFetchNode → MarketFilterNode
  → DocumentExtractNode (문서 있을 때만)
  → RiskScoreNode → ClauseSuggestionNode → HugPrecheckNode
  → ChecklistNode → ReportBuildNode
"""
from __future__ import annotations

import logging
from datetime import date

from langgraph.graph import END, START, StateGraph

from app.clients.llm import LLMClient, LLMError, ReportGenerationInput
from app.clients.molit import MolitClient, recent_deal_months
from app.graph.state import DiagnosisState
from app.models.diagnoses_models import (
    ClauseSuggestion,
    DiagnosisResponse,
    DocumentAnalysis,
    OverallRisk,
    QuickDiagnosisRequest,
    RegistryAnalysis,
    RiskSignal,
    TradeItem,
    TransactionItem,
)
from app.services.address_parser import parse_address
from app.services.checklist import build_checklist, build_structured_checklist
from app.services.clauses import suggest_clauses
from app.services.document_crosscheck import crosscheck_documents
from app.services.document_extractor import extract_text_from_upload
from app.services.document_parser import parse_contract, parse_ledger, parse_registry
from app.services.document_rules import build_registry_analysis_from_parsed, analyze_registry_text
from app.services.hug_precheck import run_hug_precheck
from app.services.market_diagnosis import diagnose_market
from app.services.market_filter import select_market_scope

logger = logging.getLogger(__name__)


# ── 종합 등급 산정 ────────────────────────────────────────────────
def _score_from_signals(codes: set[str]) -> OverallRisk:
    if "JEONSE_RATIO_OVER_90" in codes or "AUCTION_START_FOUND" in codes:
        return OverallRisk(grade="D", score=35, level="매우 위험",
                           one_line_summary="매우 높은 위험 신호가 발견되었습니다. 계약 전 정밀 확인이 필요합니다.")
    if "JEONSE_RATIO_OVER_80" in codes or "SEIZURE_FOUND" in codes or "TRUST_REGISTRATION_FOUND" in codes:
        return OverallRisk(grade="C", score=60, level="위험",
                           one_line_summary="전세가율이 높거나 등기부에 위험 신호가 있습니다. 보증과 권리관계 확인이 필요합니다.")
    if ("JEONSE_RATIO_OVER_70" in codes or "LOW_MARKET_CONFIDENCE" in codes
            or "MORTGAGE_FOUND" in codes or "OWNER_LANDLORD_MISMATCH" in codes):
        return OverallRisk(grade="B", score=78, level="주의",
                           one_line_summary="일부 확인이 필요한 신호가 있습니다.")
    return OverallRisk(grade="A", score=90, level="안전",
                       one_line_summary="공개 실거래 기준 주요 가격 위험 신호는 낮습니다.")


# ── 워크플로우 빌더 ───────────────────────────────────────────────
def build_diagnosis_graph(molit_client: MolitClient, llm_client: LLMClient):

    # 1. 주소 파싱
    async def address_parse_node(state: DiagnosisState) -> DiagnosisState:
        return {"parsed_address": parse_address(state["request"].address)}

    # 2. 시세 데이터 조회
    async def market_data_fetch_node(state: DiagnosisState) -> DiagnosisState:
        deal_ymds = recent_deal_months(date.today(), months=6)
        parsed = state["parsed_address"]
        rents = await molit_client.fetch_rents(parsed.lawd_cd, deal_ymds)
        trades = await molit_client.fetch_trades(parsed.lawd_cd, deal_ymds)
        return {"rents": rents, "trades": trades}

    # 3. 시세 범위 필터
    async def market_filter_node(state: DiagnosisState) -> DiagnosisState:
        request = state["request"]
        parsed = state["parsed_address"]
        scoped_rents = select_market_scope(
            state["rents"], parsed.dong, parsed.apt_keyword, request.area_sqm
        )
        scoped_trades = select_market_scope(
            state["trades"], parsed.dong, parsed.apt_keyword, request.area_sqm
        )
        return {
            "rent_scope": scoped_rents.scope,
            "scoped_rents": scoped_rents.items,
            "trade_scope": scoped_trades.scope,
            "scoped_trades": scoped_trades.items,
        }

    # 4. 문서 추출 + 구조화 파싱 + 교차검증 (문서가 있을 때만 실행)
    async def document_extract_node(state: DiagnosisState) -> DiagnosisState:
        docs = state.get("uploaded_documents") or []
        parsed_reg: "ParsedRegistry | None" = None
        parsed_led: "ParsedLedger | None" = None
        parsed_con: "ParsedContract | None" = None

        for filename, content in docs:
            extracted = extract_text_from_upload(filename, content)
            if extracted.document_type == "registry":
                parsed_reg = parse_registry(extracted.text)
            elif extracted.document_type == "building_ledger":
                parsed_led = parse_ledger(extracted.text)
            elif extracted.document_type == "contract":
                parsed_con = parse_contract(extracted.text)

        return {
            "parsed_registry": parsed_reg,
            "parsed_ledger": parsed_led,
            "parsed_contract": parsed_con,
        }

    # 5. 리스크 종합 (시세 + 문서)
    async def risk_score_node(state: DiagnosisState) -> DiagnosisState:
        request = state["request"]

        # 5-1. 시세 진단
        market_result = diagnose_market(
            address=request.address,
            user_deposit=request.user_deposit,
            rent_scope=state.get("rent_scope", "gu_all"),
            rents=state.get("scoped_rents", []),
            trade_scope=state.get("trade_scope", "gu_all"),
            trades=state.get("scoped_trades", []),
        )
        market_signals: list[RiskSignal] = list(market_result.risk_signals)

        # 5-2. 등기부 분석
        parsed_reg = state.get("parsed_registry")
        doc_signals: list[RiskSignal] = []
        registry_analysis: RegistryAnalysis

        if parsed_reg:
            registry_analysis, reg_signals = build_registry_analysis_from_parsed(parsed_reg)
            doc_signals.extend(reg_signals)
        else:
            registry_analysis = RegistryAnalysis(
                details=["문서가 업로드되지 않아 등기부 분석을 보류했습니다."]
            )

        # 5-3. 문서 교차검증
        crosscheck_signals = crosscheck_documents(
            user_address=request.address,
            user_deposit=request.user_deposit,
            user_area_sqm=request.area_sqm,
            user_housing_type=request.housing_type,
            registry=parsed_reg,
            ledger=state.get("parsed_ledger"),
            contract=state.get("parsed_contract"),
        )
        doc_signals.extend(crosscheck_signals)

        # 5-4. DocumentAnalysis 조립
        parsed_led = state.get("parsed_ledger")
        parsed_con = state.get("parsed_contract")
        cross_results: list[str] = [s.evidence for s in crosscheck_signals]
        doc_analysis = DocumentAnalysis(
            registry_grade=(
                registry_analysis.grade if parsed_reg else "missing"   # type: ignore[arg-type]
            ),
            ledger_grade=(
                ("danger" if parsed_led and parsed_led.has_illegal_building else "safe")
                if parsed_led else "missing"
            ),
            contract_grade="safe" if parsed_con else "missing",
            cross_check_results=cross_results,
            details=[s.evidence for s in doc_signals],
        )

        return {
            "market_risk_signals": market_signals,
            "document_risk_signals": doc_signals,
            "all_risk_signals": market_signals + doc_signals,
            "registry_analysis": registry_analysis,
            "document_analysis": doc_analysis,
            # market_analysis를 임시로 state에 저장
            "_market_analysis": market_result.market_analysis,  # type: ignore[misc]
        }

    # 6. 특약 초안 제안
    async def clause_suggestion_node(state: DiagnosisState) -> DiagnosisState:
        signals = state.get("all_risk_signals", [])
        raw_clauses = suggest_clauses(signals)

        # LLM 문장 정리 (실패해도 원본 반환)
        parsed_con = state.get("parsed_contract")
        contract_facts = {}
        if parsed_con:
            contract_facts = {
                "address": parsed_con.address,
                "landlord": parsed_con.landlord,
                "deposit": parsed_con.deposit,
                "contract_start": parsed_con.contract_start,
                "contract_end": parsed_con.contract_end,
                "balance_date": parsed_con.balance_date,
            }

        try:
            clauses = llm_client.rewrite_clause_drafts(raw_clauses, contract_facts)
        except LLMError as exc:
            logger.warning("특약 LLM 재작성 건너뜀 (%s) — 원본 사용", exc.code)
            clauses = raw_clauses

        return {"clause_suggestions": clauses}

    # 7. HUG 사전진단
    async def hug_precheck_node(state: DiagnosisState) -> DiagnosisState:
        request = state["request"]
        parsed_reg = state.get("parsed_registry")
        parsed_con = state.get("parsed_contract")
        parsed_led = state.get("parsed_ledger")

        # 문서에서 추출한 facts 우선 사용
        senior_debt = parsed_reg.mortgage_total if parsed_reg else None
        has_illegal = parsed_led.has_illegal_building if parsed_led else None
        has_restriction = (
            (parsed_reg.has_seizure or parsed_reg.has_provisional_seizure
             or parsed_reg.has_provisional_disposition or parsed_reg.has_trust)
            if parsed_reg else None
        )

        # 수도권 여부 (주소에 서울/경기/인천 포함 여부로 판단)
        addr = request.address
        is_metro = any(k in addr for k in ("서울", "경기", "인천"))

        # 시세에서 추정 매매가 가져오기
        market_analysis = state.get("_market_analysis")  # type: ignore[misc]
        est_price = market_analysis.average_market_price if market_analysis else None

        insurance = run_hug_precheck(
            user_deposit=request.user_deposit,
            estimated_sale_price=est_price,
            senior_debt_amount=senior_debt,
            has_illegal_building=has_illegal,
            has_right_restriction=has_restriction,
            has_move_in_report=None,     # 계약서에서 추출 불가 (사용자 직접 입력 필요)
            has_fixed_date=None,
            contract_start_date=parsed_con.contract_start if parsed_con else None,
            contract_end_date=parsed_con.contract_end if parsed_con else None,
            balance_date=parsed_con.balance_date if parsed_con else None,
            is_metropolitan=is_metro,
        )
        return {"_insurance": insurance}  # type: ignore[misc]

    # 8. 체크리스트 생성
    async def checklist_node(state: DiagnosisState) -> DiagnosisState:
        request = state["request"]
        all_signals = state.get("all_risk_signals", [])
        missing_info: list[str] = []

        if not state.get("parsed_registry"):
            missing_info.append("등기부등본")
        if not state.get("parsed_ledger"):
            missing_info.append("건축물대장")
        if not state.get("parsed_contract"):
            missing_info.append("계약서 초안")

        structured = build_structured_checklist(request.contract_stage, all_signals, missing_info)
        flat = build_checklist(request.contract_stage, all_signals, missing_info)

        # LLM 문장 정리 (실패 시 원본)
        from app.clients.llm import ChecklistRewriteInput
        try:
            rewrite_input = ChecklistRewriteInput(
                contract_stage=request.contract_stage,
                items=flat,
                risk_summary=", ".join(s.code for s in all_signals[:5]),
            )
            result = llm_client.rewrite_checklist(rewrite_input)
            flat = result.rewritten_items
        except LLMError as exc:
            logger.warning("체크리스트 LLM 재작성 건너뜀 (%s)", exc.code)

        return {
            "structured_checklist": structured,
            "_flat_checklist": flat,           # type: ignore[misc]
            "_missing_info": missing_info,     # type: ignore[misc]
        }

    # 9. 최종 리포트 조립
    async def report_build_node(state: DiagnosisState) -> DiagnosisState:
        request = state["request"]
        all_signals: list[RiskSignal] = state.get("all_risk_signals", [])
        codes = {s.code for s in all_signals}
        market_analysis = state.get("_market_analysis")  # type: ignore[misc]
        insurance = state.get("_insurance")               # type: ignore[misc]
        flat_checklist = state.get("_flat_checklist", []) # type: ignore[misc]
        missing_info = state.get("_missing_info", [])     # type: ignore[misc]

        # LLM 최종 요약 (실패 시 기본 문구)
        try:
            report = llm_client.generate_report(
                ReportGenerationInput(
                    address=request.address,
                    risk_signals=all_signals,
                    missing_information=missing_info,
                )
            )
            summary = report.summary
        except LLMError as exc:
            logger.warning("최종 리포트 LLM 생성 실패 (%s) — 기본 문구 사용", exc.code)
            summary = f"{request.address}에 대한 전세계약 리스크 사전진단 결과입니다. (LLM 설명 생성 제한)"

        overall = _score_from_signals(codes)
        overall.one_line_summary = summary

        scoped_rents = state.get("scoped_rents", [])
        scoped_trades = state.get("scoped_trades", [])

        response = DiagnosisResponse(
            address=request.address,
            overall_risk=overall,
            market_analysis=market_analysis,
            registry_analysis=state.get("registry_analysis", RegistryAnalysis()),
            insurance_analysis=insurance,
            checklist=flat_checklist,
            structured_checklist=state.get("structured_checklist"),
            transaction_items=[
                TransactionItem(
                    name=i.name, dong=i.dong, area=i.area, floor=i.floor,
                    deposit=i.deposit, year=i.year, month=i.month,
                )
                for i in scoped_rents
            ],
            trade_items=[
                TradeItem(
                    name=i.name, dong=i.dong, area=i.area, floor=i.floor,
                    price=i.price, year=i.year, month=i.month,
                )
                for i in scoped_trades
            ],
            risk_signals=all_signals,
            missing_information=missing_info,
            clause_suggestions=state.get("clause_suggestions", []),
            document_analysis=state.get("document_analysis"),
            saju_unlocked=True,
            saju_lock_message=None,
        )
        return {"response": response}

    # ── 조건 분기: 문서 있으면 DocumentExtractNode, 없으면 RiskScoreNode ──
    def _route_after_filter(state: DiagnosisState) -> str:
        if state.get("uploaded_documents"):
            return "DocumentExtractNode"
        return "RiskScoreNode"

    # ── 그래프 조립 ───────────────────────────────────────────────
    graph = StateGraph(DiagnosisState)
    graph.add_node("AddressParseNode", address_parse_node)
    graph.add_node("MarketDataFetchNode", market_data_fetch_node)
    graph.add_node("MarketFilterNode", market_filter_node)
    graph.add_node("DocumentExtractNode", document_extract_node)
    graph.add_node("RiskScoreNode", risk_score_node)
    graph.add_node("ClauseSuggestionNode", clause_suggestion_node)
    graph.add_node("HugPrecheckNode", hug_precheck_node)
    graph.add_node("ChecklistNode", checklist_node)
    graph.add_node("ReportBuildNode", report_build_node)

    graph.add_edge(START, "AddressParseNode")
    graph.add_edge("AddressParseNode", "MarketDataFetchNode")
    graph.add_edge("MarketDataFetchNode", "MarketFilterNode")
    graph.add_conditional_edges(
        "MarketFilterNode",
        _route_after_filter,
        {"DocumentExtractNode": "DocumentExtractNode", "RiskScoreNode": "RiskScoreNode"},
    )
    graph.add_edge("DocumentExtractNode", "RiskScoreNode")
    graph.add_edge("RiskScoreNode", "ClauseSuggestionNode")
    graph.add_edge("ClauseSuggestionNode", "HugPrecheckNode")
    graph.add_edge("HugPrecheckNode", "ChecklistNode")
    graph.add_edge("ChecklistNode", "ReportBuildNode")
    graph.add_edge("ReportBuildNode", END)
    return graph.compile()


async def run_quick_diagnosis(
    *,
    request: QuickDiagnosisRequest,
    molit_client: MolitClient,
    llm_client: LLMClient,
) -> DiagnosisResponse:
    graph = build_diagnosis_graph(molit_client, llm_client)
    state = await graph.ainvoke({"request": request, "uploaded_documents": []})
    return state["response"]


async def run_full_diagnosis(
    *,
    request: QuickDiagnosisRequest,
    uploaded_documents: list[tuple[str, bytes]],
    molit_client: MolitClient,
    llm_client: LLMClient,
) -> DiagnosisResponse:
    graph = build_diagnosis_graph(molit_client, llm_client)
    state = await graph.ainvoke({
        "request": request,
        "uploaded_documents": uploaded_documents,
    })
    return state["response"]
