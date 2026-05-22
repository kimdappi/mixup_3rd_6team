from app.models.schemas import RiskSignal


BASE_CHECKLIST = {
    "before_visit": ["주변 실거래가를 확인하세요.", "건축물대장 확인 가능 여부를 확인하세요."],
    "before_contract": ["최신 등기부등본을 확인하세요.", "계약서 주소와 등기부 주소가 일치하는지 확인하세요."],
    "before_balance": ["잔금일 당일 등기부등본을 다시 확인하세요.", "전입신고와 확정일자 준비를 확인하세요."],
    "after_move_in": ["전입신고와 확정일자를 완료하세요.", "HUG 보증 신청 상태를 확인하세요."],
}


def build_checklist(contract_stage: str, risk_signals: list[RiskSignal], missing_information: list[str]) -> list[str]:
    items = list(BASE_CHECKLIST.get(contract_stage, BASE_CHECKLIST["before_contract"]))
    codes = {signal.code for signal in risk_signals}
    if "JEONSE_RATIO_OVER_80" in codes or "JEONSE_RATIO_OVER_90" in codes:
        items.append("HUG 전세보증금 반환보증 가입 가능 여부를 계약 전 확인하세요.")
    if "MORTGAGE_FOUND" in codes:
        items.append("근저당 말소 조건을 계약서 특약에 반영하세요.")
    for missing in missing_information:
        items.append(f"{missing} 정보를 추가로 확인하세요.")
    return items
