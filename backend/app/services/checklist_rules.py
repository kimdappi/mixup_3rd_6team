"""시세 진단 결과를 사용자 행동 체크리스트로 변환하는 룰 엔진.

원칙:
  - **베이스 항목**: 모든 전세 계약에 공통 적용되는 안전 점검 사항.
    매물의 위험도와 무관하게 **항상** 표시. 안전한 매물이라도 이걸 통과하면 더 안전해진다.
  - **시그널 항목**: `risk_signal[*].recommended_action`.
    매물별 상황에 특화된 점검 사항.
  - 출력 순서: 베이스 → 시그널 (사용자 행동 흐름: 준비 → 매물별 대응).
  - 보증보험/HUG 관련 표현은 어디에도 포함하지 않는다.
  - LLM이 만들지 않는다. 룰 엔진 산출이라 hallucination 가능성 0.
"""
from typing import Iterable

# 모든 전세 계약자가 공통으로 해야 할 안전 점검 항목.
# 순서: 준비(임대인 확인) → 계약 당일(전입신고/확정일자) → 잔금일(재확인)
BASE_CHECKLIST: tuple[str, ...] = (
    "임대인 신분증과 등기부상 소유자가 일치하는지 확인하세요",
    "임대인의 미납 국세를 홈택스에서 열람 신청하세요",
    "계약 당일 전입신고와 확정일자를 반드시 받으세요",
    "잔금일 당일 등기부등본을 다시 떼서 권리관계 변동이 없는지 재확인하세요",
)


def compose_checklist(signal_actions: Iterable[str]) -> list[str]:
    """베이스 + 시그널 recommended_action을 합쳐 최종 체크리스트 생성.

    중복 제거 규칙:
        - 동일 문자열은 한 번만 등장 (베이스 우선)
        - 빈 문자열/공백은 제외

    Args:
        signal_actions: risk_signal[*].recommended_action 문자열들

    Returns:
        베이스 → 시그널 순으로 정렬된, 중복 제거된 체크리스트
    """
    seen: set[str] = set()
    items: list[str] = []

    for raw in [*BASE_CHECKLIST, *signal_actions]:
        s = (raw or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        items.append(s)

    return items
