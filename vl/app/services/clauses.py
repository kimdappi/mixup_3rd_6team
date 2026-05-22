from app.models.schemas import RiskSignal


CLAUSE_TEMPLATES = {
    "MORTGAGE_FOUND": "잔금일 전까지 등기부상 근저당권을 말소하지 않을 경우 임차인은 계약을 해제할 수 있고, 임대인은 계약금을 즉시 반환한다.",
    "JEONSE_RATIO_OVER_80": "전세보증금 반환보증 가입이 불가능한 경우 임차인은 계약을 해제할 수 있고, 임대인은 계약금을 즉시 반환한다.",
    "JEONSE_RATIO_OVER_90": "전세보증금 반환보증 가입이 불가능한 경우 임차인은 계약을 해제할 수 있고, 임대인은 계약금을 즉시 반환한다.",
    "OWNER_LANDLORD_MISMATCH": "임대인은 등기부상 소유자와 계약 당사자의 권한 관계를 증명하는 서류를 계약 체결 전 제공한다.",
}


def suggest_clauses(risk_signals: list[RiskSignal]) -> list[str]:
    clauses: list[str] = []
    for signal in risk_signals:
        template = CLAUSE_TEMPLATES.get(signal.code)
        if template and template not in clauses:
            clauses.append(template)
    return clauses
