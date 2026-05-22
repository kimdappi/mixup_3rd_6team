"""등기부등본 위험도 판정 룰 엔진.

v4 (단순화 버전): 근저당권 + 채권최고액 vs 사용자 전세금 비율만 사용.

판정 규칙:
    1. 근저당권 없음 → safe
    2. 근저당권 있고 채권최고액 추출 실패 → caution (불확실하니 보수적)
    3. user_deposit_won <= 0 → caution (비교 불가)
    4. ratio = max_claim_amount / user_deposit_won
       - ratio >= 1.0  → very_high  (깡통전세 위험 명확)
       - ratio >= 0.7  → high
       - ratio >= 0.4  → caution
       - 그 외          → caution    (근저당권은 존재하니까)

판정·코드는 모두 룰 엔진 산출. LLM은 자연어로 풀기만 함.
"""
from dataclasses import asdict, dataclass
from typing import Literal

from app.services.registry_parser import RegistryInfo

RegistryRiskLevel = Literal["safe", "caution", "high", "very_high"]


@dataclass
class RegistryRiskResult:
    risk_level: RegistryRiskLevel
    risk_signal: str                 # 룰 코드 (LLM context에 전달)
    rule_reason: str                 # 룰 엔진의 판정 사유 (한국어, 사용자 표시용)
    claim_to_deposit_ratio: float | None  # 채권최고액 / 전세금

    def to_dict(self) -> dict:
        return asdict(self)


def assess_registry_risk(
    info: RegistryInfo,
    user_deposit_won: int,
) -> RegistryRiskResult:
    """등기부 정보 + 사용자 입력 전세금 → 위험도 판정."""

    # 1. 근저당권 없음 → safe
    if not info.has_mortgage:
        return RegistryRiskResult(
            risk_level="safe",
            risk_signal="REGISTRY_NO_MORTGAGE",
            rule_reason="을구에 소유권 이외의 권리에 관한 기록사항이 없습니다.",
            claim_to_deposit_ratio=None,
        )

    # 2. 근저당권 있지만 채권최고액을 못 읽음 → caution
    claim = info.max_claim_amount
    if claim is None:
        return RegistryRiskResult(
            risk_level="caution",
            risk_signal="REGISTRY_MORTGAGE_AMOUNT_UNKNOWN",
            rule_reason="근저당권이 설정되어 있으나 채권최고액을 확인하지 못했습니다.",
            claim_to_deposit_ratio=None,
        )

    # 3. 전세금 정보 없음 → caution
    if user_deposit_won <= 0:
        return RegistryRiskResult(
            risk_level="caution",
            risk_signal="REGISTRY_DEPOSIT_MISSING",
            rule_reason="전세금 정보가 없어 채권최고액과의 비교가 불가합니다.",
            claim_to_deposit_ratio=None,
        )

    # 4. 비율 기반 판정
    ratio = claim / user_deposit_won
    if claim >= user_deposit_won:
        level: RegistryRiskLevel = "very_high"
        reason = (
            f"채권최고액({claim:,}원)이 전세금({user_deposit_won:,}원) 이상입니다."
        )
    elif ratio >= 0.7:
        level = "high"
        reason = f"채권최고액이 전세금의 {ratio * 100:.0f}% 수준입니다."
    elif ratio >= 0.4:
        level = "caution"
        reason = f"채권최고액이 전세금의 {ratio * 100:.0f}% 수준입니다."
    else:
        level = "caution"
        reason = (
            f"근저당권이 존재하나 채권최고액 비율은 {ratio * 100:.0f}%입니다."
        )

    return RegistryRiskResult(
        risk_level=level,
        risk_signal=f"REGISTRY_MORTGAGE_RATIO_{level.upper()}",
        rule_reason=reason,
        claim_to_deposit_ratio=round(ratio, 4),
    )
