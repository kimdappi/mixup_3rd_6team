from app.models.diagnoses_models import InsuranceAnalysis


def run_hug_precheck(
    *,
    user_deposit: int,
    estimated_sale_price: int | None,
    senior_debt_amount: int | None,
    has_illegal_building: bool | None,
    has_right_restriction: bool | None,
    has_move_in_report: bool | None,
    has_fixed_date: bool | None,
    contract_start_date: str | None,
    contract_end_date: str | None,
    balance_date: str | None,
) -> InsuranceAnalysis:
    missing: list[str] = []
    if senior_debt_amount is None:
        missing.append("선순위채권 금액")
    if has_illegal_building is None:
        missing.append("위반건축물 여부")
    if has_right_restriction is None:
        missing.append("권리침해 여부")
    if has_move_in_report is None:
        missing.append("전입신고 여부")
    if has_fixed_date is None:
        missing.append("확정일자 여부")
    if contract_start_date is None:
        missing.append("계약 시작일")
    if contract_end_date is None:
        missing.append("계약 종료일")
    if balance_date is None:
        missing.append("잔금일")
    if estimated_sale_price is None:
        missing.append("추정 주택가격")

    if missing:
        return InsuranceAnalysis(
            eligible=None,
            grade="warning",
            conversational="HUG 가입 가능성 판단에 필요한 정보가 부족합니다.",
            details=missing,
        )

    if has_illegal_building or has_right_restriction:
        return InsuranceAnalysis(
            eligible=False,
            grade="danger",
            conversational="문서상 보증 가입을 어렵게 만들 수 있는 위험 신호가 있습니다.",
            details=["위반건축물 또는 권리침해 여부를 공식 문서로 재확인해야 합니다."],
        )

    return InsuranceAnalysis(
        eligible=True,
        grade="safe",
        conversational="입력 정보 기준 HUG 가입 가능성을 검토해볼 수 있습니다.",
        details=["실제 가입 가능 여부는 HUG 심사 결과에 따라 달라집니다."],
    )
