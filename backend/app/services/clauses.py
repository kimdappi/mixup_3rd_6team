"""특약 초안 제안 — 룰 기반 템플릿 선택 + LLM 문장 정리(선택)"""
from __future__ import annotations

from app.models.diagnoses_models import ClauseSuggestion, RiskSignal

# ── 특약 템플릿 ───────────────────────────────────────────────────
_CLAUSE_TEMPLATES: dict[str, dict] = {
    "MORTGAGE_FOUND": {
        "draft": (
            "임대인은 잔금일 이전까지 본 부동산에 설정된 근저당권 일체를 말소하고, "
            "임대인이 이를 이행하지 않을 경우 임차인은 계약을 해제할 수 있으며 "
            "임대인은 수령한 계약금 전액을 즉시 반환한다."
        ),
        "reason": "근저당 설정 시 경매 진행 시 임차인 보증금 반환이 어려울 수 있습니다.",
        "condition": "등기부에 근저당 설정이 확인된 경우",
    },
    "TRUST_REGISTRATION_FOUND": {
        "draft": (
            "임대인은 계약 체결 전 신탁원부를 임차인에게 제공하고, "
            "수탁자의 임대 동의서(또는 신탁계약 상 임대 권한 확인서)를 첨부한다. "
            "신탁 구조로 인해 임차인의 대항력이 제한될 수 있으므로 임대인이 이를 사전 고지한다."
        ),
        "reason": "신탁등기 시 수탁자가 실소유자이므로 임대인 권한을 확인해야 합니다.",
        "condition": "등기부에 신탁등기가 확인된 경우",
    },
    "JEONSE_RATIO_OVER_80": {
        "draft": (
            "임차인이 HUG 전세보증금 반환보증에 가입하지 못하는 경우, "
            "임차인은 잔금 지급 전 계약을 해제할 수 있으며 임대인은 계약금 전액을 반환한다."
        ),
        "reason": "전세가율이 높아 보증보험 가입 불가 시 임차인의 안전장치가 사라집니다.",
        "condition": "전세가율 80% 이상으로 판정된 경우",
    },
    "JEONSE_RATIO_OVER_90": {
        "draft": (
            "임차인이 HUG 전세보증금 반환보증에 가입하지 못하는 경우, "
            "임차인은 잔금 지급 전 계약을 해제할 수 있으며 임대인은 계약금 전액을 반환한다."
        ),
        "reason": "전세가율 90% 이상 — 보증보험 가입 불가 가능성이 매우 높습니다.",
        "condition": "전세가율 90% 이상으로 판정된 경우",
    },
    "OWNER_LANDLORD_MISMATCH": {
        "draft": (
            "임대인은 등기부상 소유자와 계약 당사자의 권한 관계를 증명하는 서류 "
            "(위임장·인감증명서·가족관계증명서 등)를 계약 체결 전 임차인에게 제공한다."
        ),
        "reason": "임대인과 소유자가 다를 경우 계약 무효 위험이 있습니다.",
        "condition": "임대인과 등기부 소유자 명의가 다른 경우",
    },
    "ILLEGAL_BUILDING_FOUND": {
        "draft": (
            "임대인은 건축물대장에 기재된 위반건축물 사항을 임차인에게 사전 고지하며, "
            "이로 인해 임차인이 HUG 보증 가입이 불가하거나 행정처분을 받는 경우 "
            "임대인이 이에 따른 손해를 배상한다."
        ),
        "reason": "위반건축물은 HUG 보증 가입 거절 사유가 될 수 있습니다.",
        "condition": "건축물대장에 위반건축물 표시가 있는 경우",
    },
    "AREA_MISMATCH": {
        "draft": (
            "실제 전용면적이 건축물대장 기재 면적과 다를 경우 임대인은 그 사유를 계약 체결 전 고지하며, "
            "임차인은 면적 차이를 이유로 보증금 감액을 요청할 수 있다."
        ),
        "reason": "면적 불일치는 향후 분쟁의 원인이 될 수 있습니다.",
        "condition": "입력 면적과 건축물대장 면적이 10% 이상 차이 나는 경우",
    },
    "OLD_REGISTRY_DOCUMENT": {
        "draft": (
            "임대인은 잔금일 당일 발급한 최신 등기부등본을 임차인에게 제시하며, "
            "잔금일 기준 새로운 권리 설정이 없음을 확인한다."
        ),
        "reason": "계약 후 잔금일 사이에 권리 변동이 발생할 수 있습니다.",
        "condition": "등기부 발급일이 30일 이상 경과한 경우",
    },
}


def suggest_clauses(risk_signals: list[RiskSignal]) -> list[ClauseSuggestion]:
    seen: set[str] = set()
    clauses: list[ClauseSuggestion] = []
    for signal in risk_signals:
        tpl = _CLAUSE_TEMPLATES.get(signal.code)
        if tpl and signal.code not in seen:
            seen.add(signal.code)
            clauses.append(ClauseSuggestion(
                risk_code=signal.code,
                draft=tpl["draft"],
                reason=tpl["reason"],
                condition=tpl["condition"],
                needs_expert_review=True,
            ))
    return clauses
