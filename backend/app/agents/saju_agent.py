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

    # 2. 부족한 오행 → 검색 키워드 집합
    lacking = find_lacking(oheng_count)
    keywords = sorted(
        {kw for o in lacking for kw in OHENG_ENVIRONMENT[o]["keywords"]}
    )

    # 3. 카카오맵으로 주변 환경 분석 (async)
    nearby = await kakao_map.analyze_environment(address, keywords) if keywords else {}

    # 4. 점수 + 세부 계산
    score, details = _calculate_score(lacking, nearby)
    grade = _grade_from_score(score)

    # 5. Solar Pro3 해석 (stub) — 이름 포함 context 전달
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
    nearby: dict[str, int],
) -> tuple[int, list[dict]]:
    """
    50점 base. 부족한 오행마다:
      - 키워드 매칭되는 장소가 가까울수록 가점(최대 +30)
      - 매칭 없으면 -5
    """
    score = 50
    details: list[dict] = []

    for o in lacking:
        env = OHENG_ENVIRONMENT[o]
        matched = False
        for kw in env["keywords"]:
            if kw in nearby:
                distance = nearby[kw]
                points = max(0, 30 - (distance // 100))
                score += points
                details.append(
                    {"factor": f"{kw} 인접 ({o} 보완)", "points": points}
                )
                matched = True
                break
        if not matched:
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
