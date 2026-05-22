from app.models.schemas import RiskSignal
from app.services.checklist import build_checklist
from app.services.clauses import suggest_clauses
from app.services.hug_precheck import run_hug_precheck


def test_hug_precheck_requires_missing_document_facts():
    result = run_hug_precheck(
        user_deposit=250_000_000,
        estimated_sale_price=450_000_000,
        senior_debt_amount=None,
        has_illegal_building=None,
        has_right_restriction=None,
        has_move_in_report=None,
        has_fixed_date=None,
        contract_start_date=None,
        contract_end_date=None,
        balance_date=None,
    )

    assert result.eligible is None
    assert result.grade == "warning"
    assert "선순위채권 금액" in result.details


def test_clause_suggestions_follow_risk_signals():
    signal = RiskSignal(code="MORTGAGE_FOUND", title="근저당 발견", severity="high", confidence="medium", evidence="을구 근저당", source="document_rules", recommended_action="말소 조건 확인")

    result = suggest_clauses([signal])

    assert any("근저당" in item for item in result)


def test_checklist_adds_hug_action_for_high_jeonse_ratio():
    signal = RiskSignal(code="JEONSE_RATIO_OVER_80", title="전세가율 높음", severity="high", confidence="medium", evidence="전세가율 83%", source="market_diagnosis", recommended_action="HUG 확인")

    result = build_checklist(contract_stage="before_contract", risk_signals=[signal], missing_information=[])

    assert any("HUG" in item for item in result)
