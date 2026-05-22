"""
Solar Pro3 해석 모듈 — 실 API 미존재로 stub.

실제 API 키가 들어오면 `interpret_saju`만 교체하면 됨.
"""

from app.core.config import SOLAR_PRO_API_KEY


def is_available() -> bool:
    return bool(SOLAR_PRO_API_KEY)


def interpret_saju(context: dict) -> str:
    """
    context = {
        "name":    "홍길동",
        "lacking": ["水", "金", ...],
        "nearby":  {"한강": 640, "공원": 320, ...},
        "match_score": 78,
    }
    """
    if not is_available():
        return _stub_interpret(context)
    # TODO: Solar Pro3 실제 호출 — 키 들어오면 구현.
    return _stub_interpret(context)


def _stub_interpret(context: dict) -> str:
    name = (context.get("name") or "").strip() or "고객"
    lacking = context.get("lacking", []) or []
    nearby = context.get("nearby", {}) or {}

    if "水" in lacking and "한강" in nearby:
        return (
            f"{name}님은 물(水) 기운이 부족한 사주신데, 이 집은 한강에서 도보 약 "
            f"{max(1, nearby['한강'] // 80)}분 거리예요! 부족한 기운을 자연스럽게 채워줄 수 있어요. 👍"
        )
    if "木" in lacking and "공원" in nearby:
        return (
            f"{name}님은 나무(木) 기운이 부족한데, 근처에 공원이 {nearby['공원']}m 거리에 있어요. "
            f"산책하기 좋은 환경이에요. 👍"
        )
    if "火" in lacking and "남향" in nearby:
        return f"{name}님은 햇볕(火) 기운이 부족한 사주신데, 남향 요소가 있어 빛이 잘 드는 환경이에요. 👍"
    if "金" in lacking and ("역" in nearby or "도심" in nearby):
        return f"{name}님은 정돈된 금(金) 기운이 부족한데, 역세권 도심 환경이라 일상 동선이 깔끔해요. 👍"

    return f"{name}님 사주와 이 집의 입지가 전반적으로 무난하게 어울리는 흐름이에요. 👍"
