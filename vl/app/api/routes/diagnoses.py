from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.clients.llm import FakeLLMClient, OpenAILLMClient
from app.clients.molit import MolitClient
from app.core.config import get_settings
from app.graph.workflow import run_quick_diagnosis
from app.models.schemas import DiagnosisResponse, QuickDiagnosisRequest
from app.services.document_extractor import extract_text_from_upload
from app.services.document_rules import analyze_registry_text


router = APIRouter(prefix="/diagnoses", tags=["diagnoses"])


def _build_clients() -> tuple[MolitClient, FakeLLMClient | OpenAILLMClient]:
    settings = get_settings()
    molit_client = MolitClient(settings.molit_api_service_key.get_secret_value())
    if settings.app_env == "test":
        llm_client = FakeLLMClient()
    else:
        llm_client = OpenAILLMClient(
            provider=settings.llm_provider,
            model_name=settings.llm_model,
            temperature=settings.llm_temperature,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
    return molit_client, llm_client


@router.post("/quick", response_model=DiagnosisResponse)
async def quick_diagnosis(request: QuickDiagnosisRequest) -> DiagnosisResponse:
    try:
        molit_client, llm_client = _build_clients()
        return await run_quick_diagnosis(request=request, molit_client=molit_client, llm_client=llm_client)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="진단 처리 중 외부 API 또는 설정 오류가 발생했습니다.") from exc


@router.post("/full", response_model=DiagnosisResponse)
async def full_diagnosis(
    address: str = Form(...),
    area_sqm: float = Form(...),
    user_deposit: int = Form(...),
    housing_type: str = Form("apartment"),
    contract_stage: str = Form("before_contract"),
    registry_document: UploadFile | None = File(default=None),
    building_ledger_document: UploadFile | None = File(default=None),
    draft_contract_document: UploadFile | None = File(default=None),
) -> DiagnosisResponse:
    request = QuickDiagnosisRequest(
        address=address,
        area_sqm=area_sqm,
        user_deposit=user_deposit,
        housing_type=housing_type,
        contract_stage=contract_stage,
    )
    response = await quick_diagnosis(request)
    if registry_document is not None:
        content = await registry_document.read()
        extracted = extract_text_from_upload(registry_document.filename or "registry", content)
        registry_analysis, document_signals = analyze_registry_text(extracted.text)
        response.registry_analysis = registry_analysis
        response.risk_signals.extend(document_signals)
    return response
