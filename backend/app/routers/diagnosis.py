import logging

from fastapi import APIRouter, Depends, HTTPException

from app.agents import diagnosis_agent
from app.models.diagnosis_models import (
    QuickDiagnosisRequest,
    QuickDiagnosisResponse,
)
from app.services.molit_api import MolitApiClient, get_default_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/diagnoses", tags=["diagnosis"])


@router.post("/quick", response_model=QuickDiagnosisResponse)
async def quick_diagnosis(
    req: QuickDiagnosisRequest,
    client: MolitApiClient = Depends(get_default_client),
):
    try:
        return await diagnosis_agent.run_quick_diagnosis(
            address=req.address,
            user_deposit=req.user_deposit,
            area_sqm=req.area_sqm,
            housing_type=req.housing_type,
            contract_stage=req.contract_stage,
            client=client,
        )
    except ValueError as e:
        # 주소 파싱 실패, 또는 MOLIT_API_SERVICE_KEY 미설정
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("quick_diagnosis failed")
        raise HTTPException(status_code=500, detail="시세 진단 중 오류가 발생했습니다.")
