import pytest

from app.clients.llm import FakeLLMClient
from app.clients.molit import RentTransaction, TradeTransaction
from app.graph.workflow import run_quick_diagnosis
from app.models.diagnoses_models import QuickDiagnosisRequest


class FakeMolitClient:
    async def fetch_rents(self, lawd_cd: str, deal_ymds: list[str]):
        return [
            RentTransaction("강변아파트", "가양동", 50.0, "1", 250_000_000, "2024", "10"),
            RentTransaction("강변아파트", "가양동", 51.0, "2", 260_000_000, "2024", "11"),
            RentTransaction("강변아파트", "가양동", 49.0, "3", 255_000_000, "2024", "12"),
        ]

    async def fetch_trades(self, lawd_cd: str, deal_ymds: list[str]):
        return [
            TradeTransaction("강변아파트", "가양동", 50.0, "5", 300_000_000, "2024", "10"),
            TradeTransaction("강변아파트", "가양동", 51.0, "6", 310_000_000, "2024", "11"),
            TradeTransaction("강변아파트", "가양동", 49.0, "7", 305_000_000, "2024", "12"),
        ]


@pytest.mark.asyncio
async def test_quick_workflow_returns_frontend_compatible_response():
    response = await run_quick_diagnosis(
        request=QuickDiagnosisRequest(
            address="서울 강서구 가양동 강변아파트",
            area_sqm=50.0,
            user_deposit=250_000_000,
            housing_type="apartment",
            contract_stage="before_contract",
        ),
        molit_client=FakeMolitClient(),
        llm_client=FakeLLMClient(),
    )

    assert response.address == "서울 강서구 가양동 강변아파트"
    assert response.market_analysis.jeonse_count == 3
    assert response.transaction_items[0].deposit == 250_000_000
    assert response.saju_unlocked is True
