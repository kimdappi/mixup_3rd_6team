# DestinyHouse Backend (Saju Agent)

청년 전세 안전 컨설턴트 — 사주 Agent 백엔드. FastAPI + sajupy + Kakao Local API.

## 빠른 시작

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # KAKAO_REST_API_KEY 입력
uvicorn app.main:app --reload --port 8000
```

- API 문서: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

## 테스트

```bash
pytest tests/
```

## 엔드포인트

### `POST /api/saju`

요청 예시:
```json
{
  "name": "홍길동",
  "year": 1998, "month": 6, "day": 15,
  "hour": 14, "minute": 30,
  "city": "서울",
  "address": "서울 강서구 가양동 강변아파트 101동 802호"
}
```

응답: `app/models/saju_models.py`의 `SajuResponse` 참고.

## 아키텍처

```
routers/saju.py
  └─ agents/saju_agent.py (파이프라인)
       ├─ services/saju_calc.py    (sajupy 래퍼)
       ├─ services/kakao_map.py    (카카오 Local API)
       ├─ services/solar_pro.py    (해석 — 현재 stub)
       └─ core/oheng_mapping.py    (오행 → 환경 룰)
```

## 주의

- `KAKAO_REST_API_KEY`가 비어있으면 환경 분석은 빈 결과로 진행됨 (감점 위주).
- Solar Pro3는 stub. API 들어오면 `services/solar_pro.py:interpret_saju`만 교체.
- `sajupy 0.2.0`은 천간·지지만 반환 → 오행 카운트는 `services/saju_calc.py`에서 매핑.

## 트러블슈팅

### 1) Frontend가 mock 응답을 보여줘요 (예: "5호선 인접" / "지원님")
> 현재 frontend는 mock fallback이 제거되어, 백엔드 응답을 못 받으면 에러 화면을 띄웁니다.
> 그래도 mock 같은 결과가 보인다면 brower 캐시 또는 빌드 잔재일 수 있어요.
> `frontend/`에서 `npm run dev` 재실행 + 하드 새로고침(⌘+Shift+R).

### 2) CORS 에러 (브라우저 콘솔에 "blocked by CORS policy")
- `backend/.env`의 `FRONTEND_ORIGIN` 값이 frontend dev 서버 origin과 **정확히 일치**해야 해요.
- 기본값: `http://localhost:5173` (trailing slash 없이, http/https 구분, 포트 포함)
- 변경 후 백엔드 **재시작** 필수 (`.env`는 시작 시 1회만 로드).

### 3) 카카오 403 — `OPEN_MAP_AND_LOCAL service disabled`
- https://developers.kakao.com/console/app/<APP_ID>/product/map 에서 **활성화 ON** + 저장.
- 카카오 키가 미설정이거나 비활성 상태여도 사주 응답 자체는 반환됩니다 (점수가 낮아질 뿐).

### 4) sajupy city 인자
- 현재 코드는 `city="서울"`을 그대로 전달합니다. `sajupy 0.2.0`은 한글 도시명을 정상 처리해요.
- 영문 `"Seoul"`도 동일하게 동작합니다.
- 직접 검증: `python -c "from sajupy import calculate_saju; print(calculate_saju(year=1998, month=6, day=15, hour=14, minute=30, city='서울', use_solar_time=True))"`

### 5) 헬스체크
```bash
curl -s http://localhost:8000/health
# {"status":"ok"}
```

### 6) API 직접 호출 (frontend 없이)
```bash
curl -X POST http://localhost:8000/api/saju \
  -H "Content-Type: application/json" \
  -d '{"name":"테스트","year":1998,"month":6,"day":15,"hour":14,"minute":30,"city":"서울","address":"서울 강서구 가양동"}'
```
응답이 200 + JSON이면 백엔드 단독으론 정상. 그 후에도 frontend가 실패하면 CORS 또는 dev 서버 origin 문제.

### 7) 백엔드 콘솔에서 traceback 보기
`routers/saju.py`는 `logger.exception()`으로 풀 traceback을 찍습니다.
uvicorn 실행 중인 터미널에 빨간 traceback이 나오면 그 줄을 그대로 확인하세요.
