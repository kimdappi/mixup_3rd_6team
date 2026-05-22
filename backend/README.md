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
