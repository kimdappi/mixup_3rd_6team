from fastapi import FastAPI

from app.api.routes.diagnoses import router as diagnoses_router


app = FastAPI(title="Jeonse Contract Assistant Backend", version="0.1.0")
app.include_router(diagnoses_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
