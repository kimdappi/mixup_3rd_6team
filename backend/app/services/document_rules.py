"""등기부 텍스트 키워드 기반 리스크 시그널 생성 (구조화 파싱 보조)"""
from __future__ import annotations

from app.models.diagnoses_models import ParsedRegistry, RegistryAnalysis, RiskSignal


def analyze_registry_text(text: str) -> tuple[RegistryAnalysis, list[RiskSignal]]:
    has_mortgage = "근저당" in text
    has_trust = "신탁" in text
    has_seizure = "압류" in text or "가압류" in text or "가처분" in text
    has_auction = "경매개시결정" in text
    signals: list[RiskSignal] = []

    if has_mortgage:
        signals.append(RiskSignal(
            code="MORTGAGE_FOUND",
            title="근저당 발견",
            severity="high",
            confidence="medium",
            evidence="등기부 텍스트에 근저당 키워드가 있습니다.",
            source="document_rules",
            recommended_action="선순위채권 금액과 말소 조건을 확인하세요.",
        ))
    if has_trust:
        signals.append(RiskSignal(
            code="TRUST_REGISTRATION_FOUND",
            title="신탁등기 발견",
            severity="high",
            confidence="medium",
            evidence="등기부 텍스트에 신탁 키워드가 있습니다.",
            source="document_rules",
            recommended_action="신탁원부와 임대 권한을 확인하세요.",
        ))
    if has_seizure:
        signals.append(RiskSignal(
            code="SEIZURE_FOUND",
            title="압류·가압류·가처분 발견",
            severity="critical",
            confidence="medium",
            evidence="등기부 텍스트에 압류/가압류/가처분 키워드가 있습니다.",
            source="document_rules",
            recommended_action="계약을 보류하고 권리관계를 확인하세요.",
        ))
    if has_auction:
        signals.append(RiskSignal(
            code="AUCTION_START_FOUND",
            title="경매개시결정 발견",
            severity="critical",
            confidence="high",
            evidence="등기부 텍스트에 경매개시결정 키워드가 있습니다.",
            source="document_rules",
            recommended_action="계약을 즉시 보류하고 법률 전문가와 상담하세요.",
        ))

    if has_auction or has_seizure or has_trust:
        grade = "danger"
    elif has_mortgage:
        grade = "warning"
    else:
        grade = "safe"

    return RegistryAnalysis(
        mortgage_max=0,
        has_trust=has_trust,
        has_seizure=has_seizure or has_auction,
        grade=grade,
        conversational="업로드 문서 텍스트 기준으로 등기부 위험 키워드를 확인했습니다.",
        details=[s.evidence for s in signals],
    ), signals


def build_registry_analysis_from_parsed(parsed: ParsedRegistry) -> tuple[RegistryAnalysis, list[RiskSignal]]:
    """구조화 파싱 결과에서 등기부 분석 객체 생성"""
    signals: list[RiskSignal] = []

    if parsed.mortgage_total > 0:
        signals.append(RiskSignal(
            code="MORTGAGE_FOUND",
            title="근저당 발견",
            severity="high",
            confidence="high",
            evidence=f"채권최고액 합계 {parsed.mortgage_total:,}원. {', '.join(parsed.mortgage_details)}",
            source="document_parser",
            recommended_action="선순위채권 금액과 말소 조건을 계약서 특약에 명시하세요.",
        ))
    if parsed.has_trust:
        signals.append(RiskSignal(
            code="TRUST_REGISTRATION_FOUND",
            title="신탁등기 발견",
            severity="high",
            confidence="high",
            evidence="등기부에 신탁등기가 확인됩니다.",
            source="document_parser",
            recommended_action="신탁원부와 임대 권한을 확인하세요.",
        ))
    if parsed.has_seizure or parsed.has_provisional_seizure or parsed.has_provisional_disposition:
        signals.append(RiskSignal(
            code="SEIZURE_FOUND",
            title="압류·가압류·가처분 발견",
            severity="critical",
            confidence="high",
            evidence="등기부에 압류 또는 가압류·가처분이 확인됩니다.",
            source="document_parser",
            recommended_action="계약을 보류하고 권리관계를 확인하세요.",
        ))
    if parsed.has_auction:
        signals.append(RiskSignal(
            code="AUCTION_START_FOUND",
            title="경매개시결정 발견",
            severity="critical",
            confidence="high",
            evidence="등기부에 경매개시결정 등기가 있습니다.",
            source="document_parser",
            recommended_action="계약을 즉시 보류하고 법률 전문가와 상담하세요.",
        ))

    any_critical = parsed.has_auction or parsed.has_seizure or parsed.has_provisional_seizure or parsed.has_provisional_disposition or parsed.has_trust
    grade = "danger" if any_critical else ("warning" if parsed.mortgage_total > 0 else "safe")

    conversational = (
        "등기부 분석 결과 심각한 위험 신호가 발견되었습니다. 계약 전 전문가 상담을 권합니다."
        if grade == "danger"
        else (
            f"근저당 {parsed.mortgage_total:,}원이 확인됩니다. 말소 조건을 특약으로 명시하세요."
            if grade == "warning"
            else "등기부에서 주요 위험 신호가 발견되지 않았습니다."
        )
    )

    return RegistryAnalysis(
        mortgage_max=parsed.mortgage_total,
        has_trust=parsed.has_trust,
        has_seizure=parsed.has_seizure or parsed.has_provisional_seizure or parsed.has_provisional_disposition,
        grade=grade,
        conversational=conversational,
        details=[s.evidence for s in signals],
    ), signals
