import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import FRONTEND_ORIGIN
from app.routers import saju

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="DestinyHouse API")

# FRONTEND_ORIGIN이 쉼표로 여러 origin을 받을 수 있게 처리.
# Vite가 포트 충돌 시 5174로 fallback하는 흔한 케이스 커버.
_allowed = [o.strip() for o in FRONTEND_ORIGIN.split(",") if o.strip()]
_default_dev = ["http://localhost:5173", "http://localhost:5174"]
_allow_origins = sorted(set(_allowed + _default_dev))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(saju.router)


@app.get("/health")
def health():
    return {"status": "ok"}
