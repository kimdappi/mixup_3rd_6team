import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import saju
from app.routers import diagnoses

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

settings = get_settings()

app = FastAPI(
    title="DestinyHouse API",
    description="사주 Agent + 전세계약 리스크 진단 통합 백엔드",
    version="0.2.0",
)

# CORS: 쉼표로 여러 origin 지정 가능. Vite가 포트 충돌 시 5174 fallback 커버.
_allowed = [o.strip() for o in settings.frontend_origin.split(",") if o.strip()]
_default_dev = ["http://localhost:5173", "http://localhost:5174"]
_allow_origins = sorted(set(_allowed + _default_dev))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 라우터 등록 ────────────────────────────────────────────────────
app.include_router(saju.router)          # /api/saju
app.include_router(diagnoses.router)     # /diagnoses/quick, /diagnoses/full


@app.get("/health")
def health():
    return {"status": "ok"}
