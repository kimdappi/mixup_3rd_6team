# 운명하우스 (DestinyHouse) 🔮

청년 전세 안전 컨설턴트 — **국토부 실거래가**·**등기부등본 OCR**·**사주 궁합**을 한 화면에서 풀어주는 해커톤 프로젝트.

전세사기 피해자 3명 중 2명이 청년이라는 통계에서 출발해, 등기부등본·전세가율·시세 비교처럼 부동산 초보에게 어려운 정보를 친구가 풀어주듯 보여주는 게 목표.

---

## 한눈에 보기

| 영역 | 스택 | 핵심 |
|---|---|---|
| **Backend** | FastAPI · httpx · PyMuPDF · openai (Solar 호환) | 룰 엔진(판정) + LLM(설명) 분리, grounding 강제 |
| **Frontend** | React 18 · Vite · TailwindCSS · React Router | 4단계 흐름 (Landing → AnalyzeInput → AnalyzeRunning → Result) |
| **외부 API** | 국토교통부 실거래가 · 카카오 Local · Google Vision · Upstage Solar | 키마다 분리 .env, 미설정 시 graceful fallback |
| **테스트** | pytest · pytest-asyncio | **203 passed** (사주 14 + 시세/주소/룰 64 + 솔라 53 + 체크리스트 8 + OCR/파서/룰/포맷 64) |

```
              ┌────────────────────────────────┐
              │   Frontend (Vite + React)      │
              │   / → /analyze → /running →    │
              │       /result → /result/saju   │
              └─────┬────────────┬─────────────┘
                    │            │
            POST    │            │  multipart
       /api/saju    │            │  /api/registry/analyze
                    ▼            ▼
       /api/diagnoses/quick  /api/registry/analyze
                    │            │
        ┌───────────┴────────────┴───────────┐
        │       FastAPI (backend)            │
        │                                    │
        │  Rule Engine ── 판정/숫자/코드     │
        │       │                            │
        │       ▼                            │
        │  Solar Pro ── 설명/자연어          │
        │       (grounding 2~3중 검증)       │
        └─────┬────────────┬────────────┬────┘
              │            │            │
          MOLIT       Google Vision   Kakao Local
        실거래가        OCR            장소 검색
```

---

## 세 가지 기능

### 1. 사주 매칭 — `/api/saju`
[backend/app/agents/saju_agent.py](backend/app/agents/saju_agent.py) · [frontend/src/pages/Saju.jsx](frontend/src/pages/Saju.jsx)

- 생년월일시 → sajupy로 사주 계산 → 부족한 오행 도출
- 카카오 Local API로 매물 근처 장소(공원·강·역) 검색 → 오행 매칭
- Solar Pro가 `nearby` place_name만 사용해 풀이 한 줄 생성
- 매칭 점수가 일정 이상이면 `/result/saju` 잠금 해제

### 2. 전세 시세 진단 — `/api/diagnoses/quick`
[backend/app/agents/diagnosis_agent.py](backend/app/agents/diagnosis_agent.py) · [frontend/src/pages/Result.jsx](frontend/src/pages/Result.jsx)

워크플로우 노드(LangGraph 없이 async 함수 체인):
```
parse_address → fetch_market_data → filter_nearby_deals
  → diagnose_market (보증금 ±15%/±5%/±25% 등 5단계 판정)
  → diagnose_jeonse_ratio (전세가율 90%/80%/70% 4단계 위험)
  → compose_checklist (베이스 안전 점검 + 시그널별 권고)
  → select_similar_listings (±10% 이내 매물 최대 3건)
  → generate_diagnosis_summary (Solar Pro, 4항목 풀버전)
  → generate_diagnosis_oneline (룰 엔진 1줄 요약)
```
- **법정동코드 사전**: 서울 25개 구 / 467개 동을 hierarchical JSON으로 보유. 다른 구의 동 이름이 우연히 주소에 들어가도 거부 ([core/seoul_lawd_codes.json](backend/app/core/seoul_lawd_codes.json))
- **계층적 필터**: complex(아파트명+동+면적) → dong → gu → gu_all 폴백
- **자연 표기**: 응답 금액은 `format_won`이 "10억 4,783만원" 형태로 통일

### 3. 등기부등본 OCR + 위험도 — `/api/registry/analyze`
[backend/app/routers/registry.py](backend/app/routers/registry.py) · [frontend/src/components/RegistryAnalysisCard.jsx](frontend/src/components/RegistryAnalysisCard.jsx)

```
PDF 업로드 → PyMuPDF (PDF→PNG) → Google Vision OCR
  → registry_parser (정답 라인 차단 + OCR 줄바꿈 정규화)
  → registry_rules (채권최고액/전세금 비율 → safe/caution/high/very_high)
  → interpret_registry (Solar Pro, 사실 나열만)
```
- "`[테스트용 가상 문서]` 이후 텍스트 무시" → 테스트 PDF의 정답 라인이 파서에 새지 않도록 잘라냄
- OCR이 "근저당권설\n정" 으로 단어를 끊어도 `\s*` 정규식으로 인식
- 채권최고액 ≥ 전세금이면 `very_high` 즉시 판정

---

## 설계 원칙

이 코드베이스 전체를 관통하는 5가지 룰:

1. **판정은 룰 엔진, 설명만 LLM** — `risk_signal`/`deposit_status`/`risk_level`은 모두 `services/*_rules.py`에서 결정. LLM은 그 코드를 자연어로 풀기만 함
2. **Grounding 강제** — LLM 응답에 context에 없는 숫자/지명이 등장하면 stub fallback. 콤마 정규화 + 만원/억 분리값으로 자연 표기는 통과시키되 hallucinated 숫자는 차단 ([solar_pro.py:_validate_*_grounding](backend/app/services/solar_pro.py))
3. **Stub fallback 유지** — API 키 없음/timeout/grounding 실패 어떤 경로로도 사용자에겐 일관된 자연어가 전달
4. **보증보험 흔적 0** — HUG API 미연결 영역이라 `보증보험`/`HUG`/`허그`/`안심전세` 키워드를 코드·prompt·LLM 응답 어디에도 두지 않음 (LLM이 만들어내면 응답 차단)
5. **LLM 주관 표현 차단** — "안심하세요"·"추천드려요"·"위험해요" 같은 권유/판단 표현은 응답 후 정규식 검사로 차단, stub fallback. "사실 나열과 비교만"

---

## 빠른 시작

### 사전 준비

| 키 | 발급처 | 용도 | 없으면 |
|---|---|---|---|
| `KAKAO_REST_API_KEY` | [developers.kakao.com](https://developers.kakao.com) | 사주 매칭의 장소 검색 | 사주 점수만 낮아짐, 동작은 함 |
| `SOLAR_PRO_API_KEY` | [console.upstage.ai](https://console.upstage.ai) | LLM 자연어 풀이 | 모든 자연어가 stub fallback (룰 엔진 결과는 항상 표시) |
| `MOLIT_API_SERVICE_KEY` | [data.go.kr](https://www.data.go.kr) "아파트 전세 실거래가" | 시세 진단 전세 풀 | 진단 호출 시 503 (서버는 정상 기동) |
| `MOLIT_API_TRADE_SERVICE_KEY` | data.go.kr "아파트 매매 실거래가" | 시세 진단 매매 풀 | 전세가율 산출 불가, `NO_SALE_TRANSACTION_DATA` 시그널 |
| `GOOGLE_VISION_API_KEY` | [console.cloud.google.com](https://console.cloud.google.com) Vision API | 등기부 OCR | `REGISTRY_OCR_MODE=demo` 로 두면 빈 응답으로 graceful |

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # 위 표의 키를 채워주세요
uvicorn app.main:app --reload --port 8000
```

- API 문서: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

테스트:
```bash
pytest tests/
```

### Frontend

```bash
cd frontend
npm install
npm run dev                       # 기본 http://localhost:5173
```

`VITE_API_BASE_URL` 환경변수로 백엔드 주소 변경 가능 (기본 `http://localhost:8000`).

---

## 디렉토리 구조

```
hackerton/
├── README.md                       # 이 파일
├── .gitignore
│
├── backend/
│   ├── .env / .env.example
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── README.md                   # backend 한정 가이드 + 트러블슈팅
│   ├── app/
│   │   ├── main.py                 # FastAPI app, CORS, 라우터 등록
│   │   ├── core/
│   │   │   ├── config.py           # .env 로드
│   │   │   ├── seoul_lawd_codes.json   # 서울 25구/467동 사전
│   │   │   ├── lawd_codes.py       # JSON 로더 + validate_dong()
│   │   │   ├── oheng_mapping.py    # 오행 → 환경 룰
│   │   │   └── risk_signals.py     # RiskSignal dataclass + 코드 enum
│   │   ├── routers/
│   │   │   ├── saju.py             # POST /api/saju
│   │   │   ├── diagnosis.py        # POST /api/diagnoses/quick
│   │   │   └── registry.py         # POST /api/registry/analyze
│   │   ├── agents/
│   │   │   ├── saju_agent.py       # 사주 파이프라인
│   │   │   └── diagnosis_agent.py  # 시세 진단 파이프라인
│   │   ├── services/
│   │   │   ├── saju_calc.py        # sajupy 래퍼
│   │   │   ├── kakao_map.py        # 카카오 Local API
│   │   │   ├── molit_api.py        # 국토부 실거래가 (전세/매매 분리키)
│   │   │   ├── address_parser.py   # 주소 → LAWD_CD + 동 사전 검증
│   │   │   ├── market_rules.py     # 시세 계층 필터 + 5단계 판정
│   │   │   ├── jeonse_rules.py     # 전세가율 4단계 위험 + similar_listings
│   │   │   ├── checklist_rules.py  # BASE_CHECKLIST + 시그널 합치기
│   │   │   ├── registry_ocr.py     # PyMuPDF + Google Vision
│   │   │   ├── registry_parser.py  # 정답 라인 차단 + OCR 줄바꿈 정규화
│   │   │   ├── registry_rules.py   # 채권최고액/전세금 비율 판정
│   │   │   ├── formatters.py       # format_won, format_won_from_origin
│   │   │   └── solar_pro.py        # 3개 진입점 + grounding/주관/마크다운 차단
│   │   └── models/
│   │       ├── saju_models.py
│   │       └── diagnosis_models.py
│   └── tests/
│       ├── fixtures/registry/      # safe/risky PDF + OCR txt
│       └── test_*.py               # 203 tests
│
└── frontend/
    ├── package.json
    ├── vite.config.js / tailwind.config.js
    └── src/
        ├── main.jsx / App.jsx
        ├── pages/
        │   ├── Landing.jsx
        │   ├── AnalyzeInput.jsx    # 주소/보증금/면적/PDF 입력
        │   ├── AnalyzeRunning.jsx  # 시세 + 등기부 병렬 호출 (Promise.allSettled)
        │   ├── Result.jsx          # 카드 6개 (시세/등기부/Solar 리포트/체크리스트/사주잠금)
        │   └── Saju.jsx
        ├── components/
        │   ├── AnalysisCard.jsx
        │   ├── RegistryAnalysisCard.jsx
        │   ├── ConversationalBox.jsx   # whitespace-pre-line으로 4항목 렌더
        │   ├── ProgressAgent.jsx       # pending/running/done/skipped/error 상태
        │   ├── RiskBadge.jsx
        │   └── OhengChart.jsx
        ├── api/
        │   ├── sajuApi.js
        │   ├── diagnosisApi.js
        │   ├── registryApi.js          # multipart
        │   ├── mapDiagnosis.js         # 백엔드 응답 → Result 스키마 매핑
        │   └── mockApi.js              # 시나리오 칩 데모용
        ├── data/scenarios.js           # safe/warning/danger 데모 데이터
        └── utils/{format,delay}.js
```

---

## API 엔드포인트

### `POST /api/saju`
```json
{
  "name": "홍길동",
  "year": 1998, "month": 6, "day": 15,
  "hour": 14, "minute": 30,
  "city": "서울",
  "address": "서울 강서구 가양동 강변아파트 101동 802호"
}
```
응답: `app/models/saju_models.py` 참고. `conversational` 필드에 Solar Pro 풀이.

### `POST /api/diagnoses/quick`
```json
{
  "address": "서울특별시 강서구 가양동 가양강변아파트",
  "user_deposit": 300000000,
  "area_sqm": 60,
  "housing_type": "apt"
}
```
응답 핵심 필드:
- `market_analysis` — `avg_jeonse`, `avg_sale`, `deposit_status`, `confidence`, `rent_samples[]`, `trade_samples[]`
- `jeonse_ratio_analysis` — `user_jeonse_rate`, `risk_level`
- `risk_signals[]` — `MARKET_RENT_*`, `JEONSE_RATIO_*`, `NO_SALE_TRANSACTION_DATA` 등 룰 엔진 코드
- `summary` (4항목 풀버전) / `oneline` (1줄 요약, 룰 엔진만)
- `checklist[]` — 베이스 4항목 + 시그널 권고
- `disclaimer`

### `POST /api/registry/analyze`
multipart/form-data:
- `file` — PDF (≤ 10MB)
- `user_deposit_won` — 원 단위 정수

응답:
- `info` — `has_mortgage`, `max_claim_amount`, `mortgage_holder`, `address`, `owner_name`, `building_area`
- `risk` — `risk_level` (`safe`/`caution`/`high`/`very_high`), `risk_signal`, `rule_reason`, `claim_to_deposit_ratio`
- `summary` — Solar Pro 자연어 풀이

OCR 원본 텍스트는 응답에 싣지 않음 (개인정보 보호).

---

## 개발 메모

### MOLIT API 키 운영 팁
- data.go.kr의 활용신청은 **API별 분리**. 전세/매매가 같은 키를 공유하지 않을 수 있음
- 신규 발급 직후 1~2시간 게이트웨이 동기화 대기 → 401 Unauthorized가 떠도 시간 두고 재시도
- 옛 호스트 `openapi.molit.go.kr`는 폐기. 신규 호스트 `apis.data.go.kr/1613000` 사용

### Solar Pro 3중 안전망
LLM 응답은 다음 순서로 검사:
1. **마크다운 강조 제거** — `**` / `__` 자동 strip
2. **숫자 grounding** — context에 없는 3+ 자리 숫자 등장하면 stub fallback
3. **금칙어 차단** — 보증보험/HUG/주관 표현 등장하면 stub fallback

stub fallback도 4항목 구조와 자연 표기를 유지하므로 사용자 경험은 일관.

### 테스트 정답 라인 차단 (등기부)
픽스처 PDF는 하단에 `[테스트용 가상 문서] ... 최종 위험도: HIGH` 같은 정답 라인을 포함. 파서가 그 줄을 보면 평가 누수가 발생하므로 마커 이전 텍스트만 처리.

---

## 트러블슈팅

[backend/README.md](backend/README.md)의 "트러블슈팅" 섹션 참고. 자주 묻는 항목:
- 카카오 403 → `OPEN_MAP_AND_LOCAL` 활성화 필요
- CORS → `FRONTEND_ORIGIN` 값과 dev 서버 origin 정확히 일치
- 백엔드 콘솔에서 traceback 확인 (`logger.exception`)
- MOLIT 403/401 → `Server` 헤더 유무로 WAF vs 키 권한 구분 ([molit_api.py](backend/app/services/molit_api.py))

---

## 라이선스 / 디스클레이머

본 프로젝트는 **공개 데이터 기반의 사전진단**이며 법률 자문이 아닙니다. 실제 계약 전에는 등기부등본·임대인 신원·관련 공식 문서를 직접 확인하세요. 분석 결과는 참고용입니다.
