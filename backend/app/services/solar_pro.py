"""Solar Pro (Upstage) 자연어 변환 모듈.

원칙
=====
1. **판정은 룰 엔진, 설명만 LLM.**
   risk_signal / deposit_status / risk_level 코드는 모두 룰 엔진이 만든다.
   여기서는 그 코드와 숫자를 prompt의 "근거 데이터"로 LLM에 넘기고
   응답을 자연어로만 받는다. 절대 LLM에게 코드/등급을 만들게 하지 않는다.

2. **Grounding 강제.**
   응답에 context에 없는 지명·금액·통계가 등장하면 즉시 stub fallback.
   system prompt에 명시 + 응답 후 코드로 검증, 2중 안전망.

3. **Stub fallback 유지.**
   실 API 실패(rate limit, timeout, 네트워크 오류, grounding 실패) 시 stub으로 폴백.
   서비스가 절대 빈 화면을 보이지 않도록.

4. **보증보험 흔적 0.**
   LLM 응답에 "보증보험"·"HUG"·"안심전세" 등 키워드가 등장하면 차단.
"""
import logging
import re

from openai import OpenAI, OpenAIError

from app.core.config import SOLAR_PRO_API_KEY
from app.services.formatters import format_won

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Solar 클라이언트 (Upstage Console에서 발급한 OpenAI 호환 endpoint)
# ---------------------------------------------------------------------------

_SOLAR_BASE_URL = "https://api.upstage.ai/v1/solar"
# TODO: Solar Pro3 정식 model string 확정 시 교체. 현재는 Pro2 사용.
_SOLAR_MODEL = "solar-pro2"
_client: OpenAI | None = None


def is_available() -> bool:
    return bool(SOLAR_PRO_API_KEY)


def _get_client() -> OpenAI | None:
    global _client
    if _client is None and SOLAR_PRO_API_KEY:
        _client = OpenAI(
            api_key=SOLAR_PRO_API_KEY,
            base_url=_SOLAR_BASE_URL,
        )
    return _client


def _call_solar(system: str, user: str, temperature: float = 0.3) -> str:
    """Solar Pro 실 호출. 실패 시 예외 raise.

    Args:
        temperature: hallucination을 억제하기 위해 0.3 고정.
                     임의로 올리지 말 것.
    """
    client = _get_client()
    if client is None:
        raise RuntimeError("SOLAR_PRO_API_KEY not set")

    resp = client.chat.completions.create(
        model=_SOLAR_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=300,
        timeout=10,
    )
    return (resp.choices[0].message.content or "").strip()


# ---------------------------------------------------------------------------
# Grounding 검증
# ---------------------------------------------------------------------------

# 사주 응답에서 허용되지 않은 지명 키워드 (allowed_places의 일부가 아니면 차단)
_SAJU_BANNED_KEYWORDS = ["한강", "공원", "산", "역", "타워", "광장", "강변"]

# 진단 응답에서 절대 등장하면 안 되는 보증보험 관련 키워드 (이중 안전망)
_DIAG_BANNED_KEYWORDS = [
    "보증보험", "보증 보험", "전세보증금반환보증", "보증가입",
    "HUG", "허그", "안심전세",
]

# v3 — LLM이 주관적 판단/위로/권유를 섞으면 차단. "사실 나열과 비교만" 원칙.
_SUBJECTIVE_PATTERNS = [
    "안심하", "안심해", "걱정 없", "걱정마세", "걱정 마세",
    "추천드려", "추천드립", "추천해",
    "위험해요", "위험합니다", "위험하니",
    "조심하세요", "조심하시", "주의하세요",
]

# v3.1 — stub_diagnosis_summary와 generate_diagnosis_oneline이 공유하는 1줄 시세 판정 문구.
# 문구를 바꾸려면 여기 한 곳만 수정한다.
_DEPOSIT_STATUS_LINES: dict[str, str] = {
    "overpriced":    "입력하신 보증금이 인근 평균보다 15% 이상 높은 편이에요.",
    "slightly_high": "입력하신 보증금이 인근 평균보다 약간 높은 편이에요.",
    "fair":          "입력하신 보증금이 인근 시세와 비슷한 수준이에요.",
    "cheap":         "입력하신 보증금이 인근 평균보다 낮은 편이에요.",
    "suspicious":    "입력하신 보증금이 인근 평균보다 25% 이상 낮아요.",
}
_DEPOSIT_STATUS_DEFAULT = "시세 비교에 필요한 데이터가 부족해요."


def _validate_saju_grounding(text: str, allowed_places: list[str]) -> bool:
    """응답에 허용되지 않은 지명 키워드가 섞였는지 검사.

    allowed_places 중 하나라도 키워드를 포함하면(예: 'allowed에 "한강시민공원 망원지구"'가
    있을 때 응답에 '한강'이 등장) 통과.
    """
    for kw in _SAJU_BANNED_KEYWORDS:
        if kw in text:
            if any(p and kw in p for p in allowed_places):
                continue
            return False
    return True


def _add_numeric(allowed: set[str], v) -> None:
    """숫자 v를 다양한 한국어 표기에 등장할 형태로 allowed set에 추가.

    v3.1: 자연 표기 "10억 4,783만원"의 'eok'(10), 'man'(4783) 분리값도 포함.

    지원 표현:
      - 원 단위 raw: "300000000"
      - 만원 환산:    "30000"
      - 억 환산:      "3"
      - 만원 분리 (억-만): "10" + "4783"
      - 비율(float)의 정수 백분율: 0.853 → "85"
      - float의 정수부:           84.5  → "84"
    """
    if v is None:
        return
    try:
        if isinstance(v, float):
            allowed.add(str(int(round(v * 100))))
            allowed.add(str(int(v)))
            return
        won = int(v)
        if won == 0:
            return
        allowed.add(str(won))

        # 원 → 만원 (정수 환산일 때만)
        if won >= 10000 and won % 10000 == 0:
            allowed.add(str(won // 10000))
        # 원 → 억 (정수 환산일 때만)
        if won >= 100_000_000 and won % 100_000_000 == 0:
            allowed.add(str(won // 100_000_000))

        # v3.1: 만원 단위에서 억/만 분리값
        manwon = won // 10000
        if manwon >= 10000:
            eok = manwon // 10000
            man_part = manwon % 10000
            allowed.add(str(eok))
            if man_part > 0:
                allowed.add(str(man_part))
    except (ValueError, TypeError):
        pass


def _validate_diagnosis_grounding(text: str, context: dict) -> bool:
    """응답에 context에 없는 3자리 이상 숫자가 등장하면 차단.

    허용 숫자 집합:
      - 원 단위 보증금/매매가 (예: 350000000)
      - 만원 단위 보증금/매매가 (예: 35000)
      - 사용자 입력 user_deposit
      - jeonse/trade count 등 표본 수
      - 전세가율/보증금 비율의 정수 백분율 (예: 0.853 → "85")
      - v3: similar_listings의 price_won/area_sqm/year 등

    응답에 쉼표 포함 숫자("300,000,000")가 와도 통과하도록 검사 전 정규화.
    """
    market = context.get("market_analysis", {}) or {}
    jeonse = context.get("jeonse_analysis", {}) or {}
    similar = context.get("similar_listings", []) or []

    allowed: set[str] = set()

    for v in [
        market.get("avg_jeonse"),
        market.get("avg_sale"),
        market.get("jeonse_count"),
        market.get("trade_count"),
        jeonse.get("user_jeonse_rate"),
        jeonse.get("market_jeonse_rate"),
        market.get("deposit_ratio"),
        context.get("user_deposit"),
    ]:
        _add_numeric(allowed, v)

    # v3: similar_listings의 매물별 숫자
    for s in similar:
        _add_numeric(allowed, s.get("price_won"))
        _add_numeric(allowed, s.get("area_sqm"))
        _add_numeric(allowed, s.get("floor"))
        _add_numeric(allowed, s.get("year"))
        _add_numeric(allowed, s.get("month"))

    # "300,000,000" → "300000000" 정규화 후 검사 (LLM이 자연스러운 표기 시도)
    text_normalized = text.replace(",", "")
    found = re.findall(r"\d{3,}", text_normalized)
    for n in found:
        if n not in allowed:
            return False
    return True


# ---------------------------------------------------------------------------
# 사주 해석 (saju_agent.py에서 호출)
# ---------------------------------------------------------------------------

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

    nearby = context.get("nearby", {}) or {}
    allowed_places = [p.get("place_name", "") for p in nearby.values() if isinstance(p, dict)]

    system = (
        "당신은 사주를 친구처럼 풀어 설명하는 도우미입니다. "
        "아래 [근거 데이터]의 장소 이름과 거리만 사용하세요. "
        "데이터에 없는 지명·랜드마크·거리를 절대 만들어내지 마세요. "
        "데이터에 없는 정보는 언급하지 마세요. "
        "2~3문장, 친근한 존댓말로 답하고, 마지막에 이모지 하나 정도는 괜찮습니다."
    )

    nearby_lines = "\n".join(
        f"  - {elem}: {p.get('place_name')} ({p.get('distance_m')}m, {p.get('category', '')})"
        for elem, p in nearby.items()
        if isinstance(p, dict)
    ) or "  (매칭 장소 없음)"

    user = (
        f"[근거 데이터]\n"
        f"- 사용자 이름: {context.get('name', '고객')}\n"
        f"- 부족한 오행: {context.get('lacking', [])}\n"
        f"- 매칭된 장소:\n{nearby_lines}\n"
        f"- 매칭 점수: {context.get('match_score', 0)}\n\n"
        f"위 데이터를 바탕으로 이 집이 사용자 사주와 어울리는지 한두 문장으로 풀어주세요."
    )

    try:
        result = _call_solar(system, user)
        if not _validate_saju_grounding(result, allowed_places):
            logger.warning("[Solar grounding fail/saju] %s", result[:100])
            return _stub_interpret(context)
        return result
    except OpenAIError as e:
        logger.warning("[Solar API error/saju] %s", e)
        return _stub_interpret(context)
    except Exception as e:  # noqa: BLE001
        logger.warning("[Solar fallback/saju] %s", e)
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
# 시세 진단 요약 (diagnosis_agent.py에서 호출)
# ---------------------------------------------------------------------------

def _format_similar_listing_line(s: dict) -> str:
    """LLM prompt / stub fallback이 동일 포맷으로 매물을 표현하도록 통일.

    v3.1: 가격은 `format_won`으로 자연 표기 ("3억 1,000만원" 등).
    """
    apt = s.get("apt_name") or ""
    area = s.get("area_sqm")
    floor = s.get("floor")
    year = s.get("year")
    month = s.get("month")
    price_won = s.get("price_won") or 0
    price_str = format_won(price_won // 10000) if price_won else "0원"
    deal_date = (
        f"{year}.{int(month):02d}" if year and month else ""
    )
    area_str = f"{float(area):.1f}㎡" if area is not None else ""
    floor_str = f"{floor}층" if floor not in (None, "") else ""
    return f"{apt} · {area_str} · {floor_str} · {deal_date} · {price_str}"


def generate_diagnosis_summary(context: dict) -> str:
    """전세 진단 결과를 4개 항목 리포트로 변환.

    출력 형식: 줄바꿈으로 구분된 4개 항목
        ① 시세 판정
        ② 전세가율
        ③ 평균 비교
        ④ 비슷한 매물

    context 예시:
        {
            "user_deposit": 300000000,
            "market_analysis": {"deposit_status": ..., "avg_jeonse": ..., ...},
            "jeonse_analysis": {"risk_level": ..., "user_jeonse_rate": ..., ...},
            "similar_listings": [{"apt_name": ..., "price_won": ..., ...}, ...],
        }
    """
    if not is_available():
        return _stub_diagnosis_summary(context)

    market = context.get("market_analysis", {}) or {}
    jeonse = context.get("jeonse_analysis", {}) or {}
    similar = context.get("similar_listings", []) or []

    system = (
        "당신은 전세 시세 분석 결과를 사용자에게 친근하게 풀어 설명하는 도우미입니다.\n"
        "\n"
        "다음 규칙을 반드시 지키세요:\n"
        "1. 아래 [근거 데이터]의 숫자, 판정 코드, 매물 정보만 사용하세요.\n"
        "2. 데이터에 없는 금액·지명·통계·추정치를 절대 만들어내지 마세요.\n"
        "3. '안심하세요', '걱정 없어요', '추천드려요', '위험해요' 같은 "
        "주관적 판단·위로·권유 표현을 사용하지 마세요. 사실 나열과 비교만 하세요.\n"
        "4. 보증보험·전세보증금반환보증·보증가입·HUG·허그·안심전세 관련 언급을 "
        "절대 하지 마세요.\n"
        "5. 일반론('시장 상황은 변동성이 있으니', '부동산은 신중하게' 등)을 쓰지 마세요.\n"
        "6. 숫자는 콤마 없이 그대로 적어주세요. (예: 30000만원, 300000000원)\n"
        "\n"
        "출력 형식:\n"
        "다음 4개 항목을 순서대로, 각 항목당 1~2문장으로 풀어주세요.\n"
        "① 시세 판정\n"
        "② 전세가율\n"
        "③ 평균 비교\n"
        "④ 비슷한 매물 (similar_listings가 비어있으면 "
        "'비슷한 가격대 매물은 표본에 없습니다'라고만 쓰세요)\n"
        "\n"
        "친근한 존댓말을 사용하되, 주관적 위로/판단은 빼고 담백하게 사실만 전달하세요."
    )

    # 만원 단위로 환산 → format_won으로 자연 표기 ("10억 4,783만원")
    avg_jeonse_str = format_won(
        market.get("avg_jeonse") // 10000 if market.get("avg_jeonse") else None
    )
    avg_sale_str = format_won(
        market.get("avg_sale") // 10000 if market.get("avg_sale") else None
    )
    user_deposit_str = format_won(
        context.get("user_deposit") // 10000 if context.get("user_deposit") else None
    )
    # 전세가율은 percent 단위로 환산해서 prompt에 노출
    user_rate_pct = (
        round(float(jeonse.get("user_jeonse_rate")) * 100, 1)
        if jeonse.get("user_jeonse_rate") is not None else None
    )

    similar_lines = "\n".join(
        f"  - {_format_similar_listing_line(s)}" for s in similar
    ) or "  (해당 가격대 표본 없음)"

    user = (
        f"[근거 데이터]\n"
        f"\n"
        f"■ 시세 판정\n"
        f"  - 판정 코드: {market.get('deposit_status')}\n"
        f"  - 입력 보증금: {user_deposit_str}\n"
        f"  - 인근 평균 보증금: {avg_jeonse_str}\n"
        f"\n"
        f"■ 전세가율\n"
        f"  - 위험도: {jeonse.get('risk_level')}\n"
        f"  - 전세가율: {user_rate_pct}%\n"
        f"\n"
        f"■ 평균 비교 보조 정보\n"
        f"  - 인근 평균 매매가: {avg_sale_str}\n"
        f"  - 표본 수: 전세 {market.get('jeonse_count')}건 / 매매 {market.get('trade_count')}건\n"
        f"\n"
        f"■ 비슷한 가격대 매물 (제시 보증금 ±10% 이내, 최대 3건)\n"
        f"{similar_lines}\n"
        f"\n"
        f"금액은 위 표기 그대로(예: '10억 4,783만원')만 사용하고, 다른 표기로 바꾸지 마세요. "
        f"위 4개 항목을 순서대로 자연어로 풀어 설명해주세요."
    )

    try:
        result = _call_solar(system, user)

        # 1차: 숫자 grounding 검증
        if not _validate_diagnosis_grounding(result, context):
            logger.warning("[Solar grounding fail/diagnosis] %s", result[:120])
            return _stub_diagnosis_summary(context)

        # 2차: 보증보험 키워드 차단 (이중 안전망)
        if any(kw in result for kw in _DIAG_BANNED_KEYWORDS):
            logger.warning("[Solar insurance keyword leak/diagnosis] %s", result[:120])
            return _stub_diagnosis_summary(context)

        # 3차: 주관적 판단/위로/권유 표현 차단 (v3 — "사실만 전달" 원칙)
        if any(p in result for p in _SUBJECTIVE_PATTERNS):
            logger.warning("[Solar subjective leak/diagnosis] %s", result[:120])
            return _stub_diagnosis_summary(context)

        return result
    except OpenAIError as e:
        logger.warning("[Solar API error/diagnosis] %s", e)
        return _stub_diagnosis_summary(context)
    except Exception as e:  # noqa: BLE001
        logger.warning("[Solar fallback/diagnosis] %s", e)
        return _stub_diagnosis_summary(context)


def generate_diagnosis_oneline(context: dict) -> str:
    """시세 안전성 카드에 들어갈 1줄 요약 (v3.1).

    LLM 호출 없음. 룰 엔진의 deposit_status 코드만 보고 결정 → 재현성 100%, grounding 위험 0.
    `_stub_diagnosis_summary`의 ① 시세 판정 줄과 동일한 출처(`_DEPOSIT_STATUS_LINES`)를 공유한다.
    """
    market = context.get("market_analysis", {}) or {}
    status = market.get("deposit_status")
    return _DEPOSIT_STATUS_LINES.get(status, _DEPOSIT_STATUS_DEFAULT)


def _stub_diagnosis_summary(context: dict) -> str:
    """LLM 미사용/실패 시 4개 항목 구조의 fallback 응답.

    LLM 응답과 동일한 형식을 유지하기 위해 줄바꿈으로 4개 항목을 분리한다.
    프론트에서 `whitespace-pre-line` 으로 렌더되어야 한다.
    """
    market = context.get("market_analysis", {}) or {}
    jeonse = context.get("jeonse_analysis", {}) or {}
    similar = context.get("similar_listings", []) or []

    risk = jeonse.get("risk_level")

    avg_jeonse = market.get("avg_jeonse")
    user_deposit = context.get("user_deposit")
    user_rate = jeonse.get("user_jeonse_rate")
    user_rate_pct = round(float(user_rate) * 100, 1) if user_rate is not None else None

    # ① 시세 판정 — oneline과 공유
    line1 = generate_diagnosis_oneline(context)

    # ② 전세가율
    if user_rate_pct is None:
        line2 = "전세가율 데이터가 부족해요."
    else:
        risk_map = {
            "very_high": f"전세가율이 {user_rate_pct}%로 매우 높습니다.",
            "high": f"전세가율이 {user_rate_pct}%로 주의가 필요한 구간이에요.",
            "caution": f"전세가율이 {user_rate_pct}%로 보통 수준이에요.",
            "safe": f"전세가율은 {user_rate_pct}%로 안전한 범위예요.",
        }
        line2 = risk_map.get(risk, f"전세가율은 {user_rate_pct}%로 산정되었어요.")

    # ③ 평균 비교 — v3.1 자연 표기
    if user_deposit and avg_jeonse:
        avg_str = format_won(int(avg_jeonse // 10000))
        dep_str = format_won(int(user_deposit // 10000))
        line3 = f"인근 평균 보증금은 {avg_str}, 입력하신 보증금은 {dep_str}이에요."
    else:
        line3 = "평균 비교에 필요한 데이터가 부족해요."

    # ④ 비슷한 매물
    if similar:
        items = "\n".join(
            f"- {_format_similar_listing_line(s)}" for s in similar
        )
        line4 = f"제시 보증금 ±10% 이내 비슷한 매물:\n{items}"
    else:
        line4 = "제시 보증금 ±10% 이내 비슷한 매물은 표본에 없습니다."

    return f"{line1}\n{line2}\n{line3}\n{line4}"
