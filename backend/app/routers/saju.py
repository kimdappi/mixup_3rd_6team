from fastapi import APIRouter, HTTPException

from app.agents import saju_agent
from app.models.saju_models import SajuRequest, SajuResponse

router = APIRouter(prefix="/api", tags=["saju"])


@router.post("/saju", response_model=SajuResponse)
async def analyze_saju(req: SajuRequest):
    try:
        return await saju_agent.run(
            year=req.year,
            month=req.month,
            day=req.day,
            hour=req.hour,
            minute=req.minute,
            city=req.city or "서울",
            address=req.address,
        )
    except Exception as e:
        # 운영 로그에는 traceback이 필요. 우선 print로 stdout에 남김.
        print(f"[ERROR] saju_agent: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="사주 분석 중 오류가 발생했습니다.")
