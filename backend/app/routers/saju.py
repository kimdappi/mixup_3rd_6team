import logging

from fastapi import APIRouter, HTTPException

from app.agents import saju_agent
from app.models.saju_models import SajuRequest, SajuResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["saju"])


@router.post("/saju", response_model=SajuResponse)
async def analyze_saju(req: SajuRequest):
    try:
        return await saju_agent.run(
            name=req.name,
            year=req.year,
            month=req.month,
            day=req.day,
            hour=req.hour,
            minute=req.minute,
            city=req.city or "서울",
            address=req.address,
        )
    except Exception:
        logger.exception("saju_agent failed")
        raise HTTPException(status_code=500, detail="사주 분석 중 오류가 발생했습니다.")
