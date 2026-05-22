from app.core.oheng_mapping import OHENG_ENVIRONMENT, find_lacking
from app.services import kakao_map, saju_calc, solar_pro

DISCLAIMER = "사주는 전통 문화 콘텐츠로 제공됩니다. 계약 결정은 안전성 분석을 우선해주세요."


async def run(
    name: str,
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    city: str,
    address: str,
) -> dict:
    # 1. 사주 계산 (sync)
    saju = saju_calc.calculate(year, month, day, hour, minute, city)
    oheng_count = saju["oheng_count"]

    # 2. 부족한 오행 식별
    lacking = find_lacking(oheng_count)

    # 3. 카카오맵으로 주변 환경 분석 — 오행별 실제 매칭 장소 정보 반환.
    nearby = await kakao_map.analyze_environment(address, lacking) if lacking else {}

    # 4. 점수 + 세부 계산 (실제 place_name을 factor로 사용)
    score, details = _calculate_score(lacking, nearby)
    grade = _grade_from_score(score)

    # 5. Solar Pro3 해석 (stub) — 매칭된 장소 정보를 grounding 근거로 전달.
    conversational = solar_pro.interpret_saju(
        {
            "name": name,
            "lacking": lacking,
            "nearby": nearby,
            "match_score": score,
        }
    )

    return {
        "saju_pillars": saju["pillars"],
        "oheng_distribution": oheng_count,
        "lacking_oheng": lacking,
        "match_score": score,
        "match_grade": grade,
        "match_details": details,
        "conversational": conversational,
        "disclaimer": DISCLAIMER,
    }


def _calculate_score(
    lacking: list[str],
    nearby: dict[str, dict],
) -> tuple[int, list[dict]]:
    """
    50점 base. 부족한 오행마다:
      - nearby에 실제 매칭된 장소 있음 → 거리 가까울수록 가점(최대 +30)
      - 없음 → -5 (단, 火·土처럼 검증 불가 오행은 -5 부과 안 함)
    """
    score = 50
    details: list[dict] = []

    for o in lacking:
        if o in nearby:
            place = nearby[o]
            distance = place["distance_m"]
            points = max(0, 30 - (distance // 100))
            score += points
            details.append(
                {
                    "factor": f"{place['place_name']} 인접 ({o} 보완)",
                    "points": points,
                }
            )
        else:
            env = OHENG_ENVIRONMENT.get(o, {})
            queries = env.get("search_queries", []) or []
            if not queries:
                # 火·土 — 카카오로 검증 불가 → 가점도 감점도 없음.
                continue
            score -= 5
            details.append(
                {
                    "factor": f"{env['description']} 요소 부족 ({o})",
                    "points": -5,
                }
            )

    return max(0, min(100, score)), details


def _grade_from_score(score: int) -> str:
    if score >= 80:
        return "아주 좋음"
    if score >= 65:
        return "양호"
    return "보통"
