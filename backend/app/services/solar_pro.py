"""
Solar Pro3 해석 모듈 — 실 API 미존재로 stub.

GROUNDING RULES (LLM 통합 시 반드시 지킬 것)
============================================
실제 LLM(Solar Pro3 등)을 연결할 때는 system prompt에 다음 규칙을 명시할 것:

  당신은 사주 해석가입니다. 아래 [근거 데이터]의 장소 이름과 거리만 사용하세요.
  데이터에 없는 지명·랜드마크·거리를 절대 만들어내지 마세요.
  데이터에 없는 정보는 언급하지 마세요.

  [근거 데이터]
  - 사용자 이름: {name}
  - 부족한 오행: {lacking}
  - 매칭된 장소:
    {nearby의 각 오행별 place_name, category, distance_m을 그대로 나열}

응답 생성 후 검증 단계 권장:
  응답 텍스트에 등장하는 모든 지명이 nearby[*].place_name 리스트 안에 있는지
  확인. 없는 지명(예: "한강", "공원")이 등장하면 재생성하거나 폴백 사용.

이 stub은 동일한 규칙을 코드로 강제한다 — 어떤 분기에서도 "한강", "공원" 같은
하드코딩 지명을 출력에 박지 않고, place["place_name"]만 사용한다.
"""

from app.core.config import SOLAR_PRO_API_KEY


def is_available() -> bool:
    return bool(SOLAR_PRO_API_KEY)


def interpret_saju(context: dict) -> str:
    """
    context = {
        "name":    "홍길동",
        "lacking": ["水", "金", ...],
        "nearby":  {"水": {"place_name": "한강시민공원 망원지구", "distance_m": 640, ...}, ...},
        "match_score": 78,
    }
    """
    if not is_available():
        return _stub_interpret(context)
    # TODO: Solar Pro3 실제 호출. 응답 후 grounding 검증 필수.
    return _stub_interpret(context)


def _stub_interpret(context: dict) -> str:
    name = (context.get("name") or "").strip() or "고객"
    lacking = context.get("lacking", []) or []
    nearby = context.get("nearby", {}) or {}

    # 매칭된 장소가 있는 오행을 우선순위(水 → 木 → 金) 순으로 멘트 생성.
    if "水" in lacking and "水" in nearby:
        place = nearby["水"]
        walk_min = max(1, place["distance_m"] // 80)
        return (
            f"{name}님은 물(水) 기운이 부족한 사주신데, "
            f"이 집은 '{place['place_name']}'에서 도보 약 {walk_min}분 거리예요! "
            f"부족한 기운을 자연스럽게 채워줄 수 있어요. 👍"
        )

    if "木" in lacking and "木" in nearby:
        place = nearby["木"]
        return (
            f"{name}님은 나무(木) 기운이 부족한데, "
            f"근처 '{place['place_name']}'이 {place['distance_m']}m 거리에 있어요. "
            f"산책하기 좋은 환경이에요. 👍"
        )

    if "金" in lacking and "金" in nearby:
        place = nearby["金"]
        return (
            f"{name}님은 정돈된 금(金) 기운이 부족한데, "
            f"'{place['place_name']}'이 가까워 일상 동선이 깔끔해요. 👍"
        )

    # 火·土는 카카오 검증 불가 → 일반 멘트만 (구체적 지명 언급 금지).
    if "火" in lacking:
        return f"{name}님은 햇볕(火) 기운이 부족한 사주신데, 남향이라면 잘 어울려요."
    if "土" in lacking:
        return f"{name}님은 토(土) 기운이 부족한 사주신데, 안정된 평지의 단지면 좋아요."

    return f"{name}님 사주와 이 집은 전반적으로 무난하게 어울리는 흐름이에요. 👍"


# ---------------------------------------------------------------------------
# 시세 진단용 summary
# ---------------------------------------------------------------------------

def generate_diagnosis_summary(context: dict) -> str:
    """전세 진단 결과를 사용자 친화적 문장으로 변환.

    실제 Solar Pro API 미연결 상태에서는 stub 응답을 반환한다.
    LLM 연결 시에도 grounding 규칙을 지킬 것:
      - context의 숫자와 risk_signal 코드만 사용
      - 데이터에 없는 지명·금액·추정을 만들어내지 말 것
    """
    if not is_available():
        return _stub_diagnosis_summary(context)
    # TODO: Solar Pro API 호출. 응답 후 grounding 검증 필수.
    return _stub_diagnosis_summary(context)


def _stub_diagnosis_summary(context: dict) -> str:
    market = context.get("market_analysis", {}) or {}
    jeonse = context.get("jeonse_analysis", {}) or {}

    status = market.get("deposit_status")
    risk = jeonse.get("risk_level")

    if status == "overpriced":
        market_msg = "입력하신 보증금이 인근 평균보다 15% 이상 높아요. 동일 단지 최근 거래를 다시 확인해보세요."
    elif status == "slightly_high":
        market_msg = "보증금이 인근 평균보다 약간 높은 편이에요."
    elif status == "fair":
        market_msg = "보증금이 인근 시세와 비슷한 수준이에요."
    elif status == "cheap":
        market_msg = "보증금이 인근 평균보다 낮아요."
    elif status == "suspicious":
        market_msg = "보증금이 인근 평균보다 25% 이상 낮아요. 너무 싼 매물은 오히려 확인이 필요해요."
    else:
        market_msg = "시세 비교에 필요한 데이터가 부족해요."

    if risk == "very_high":
        risk_msg = " 다만 전세가율이 90% 이상으로 매우 높아 깡통전세 위험이 큽니다."
    elif risk == "high":
        risk_msg = " 전세가율이 80%를 넘어 주의가 필요해요."
    elif risk == "caution":
        risk_msg = " 전세가율이 70~80% 구간이에요."
    elif risk == "safe":
        risk_msg = " 전세가율은 안전한 범위예요."
    else:
        risk_msg = ""

    return market_msg + risk_msg
