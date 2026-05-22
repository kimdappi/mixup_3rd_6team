from app.models.schemas import RegistryAnalysis, RiskSignal


def analyze_registry_text(text: str) -> tuple[RegistryAnalysis, list[RiskSignal]]:
    has_mortgage = "근저당" in text
    has_trust = "신탁" in text
    has_seizure = "압류" in text or "가압류" in text or "가처분" in text
    signals: list[RiskSignal] = []
    if has_mortgage:
        signals.append(RiskSignal(code="MORTGAGE_FOUND", title="근저당 발견", severity="high", confidence="medium", evidence="등기부 텍스트에 근저당 키워드가 있습니다.", source="document_rules", recommended_action="선순위채권 금액과 말소 조건을 확인하세요."))
    if has_trust:
        signals.append(RiskSignal(code="TRUST_REGISTRATION_FOUND", title="신탁등기 발견", severity="high", confidence="medium", evidence="등기부 텍스트에 신탁 키워드가 있습니다.", source="document_rules", recommended_action="신탁원부와 임대 권한을 확인하세요."))
    if has_seizure:
        signals.append(RiskSignal(code="SEIZURE_FOUND", title="압류 등 권리제한 발견", severity="critical", confidence="medium", evidence="등기부 텍스트에 압류/가압류/가처분 키워드가 있습니다.", source="document_rules", recommended_action="계약을 보류하고 권리관계를 확인하세요."))
    grade = "danger" if has_seizure or has_trust else "warning" if has_mortgage else "safe"
    return RegistryAnalysis(
        mortgage_max=0,
        has_trust=has_trust,
        has_seizure=has_seizure,
        grade=grade,
        conversational="업로드 문서 텍스트 기준으로 등기부 위험 키워드를 확인했습니다.",
        details=[signal.evidence for signal in signals],
    ), signals
