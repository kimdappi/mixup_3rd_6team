from typing import Protocol

from langchain.chat_models import init_chat_model
from pydantic import BaseModel

from app.models.diagnoses_models import RiskSignal


class ReportGenerationInput(BaseModel):
    address: str
    risk_signals: list[RiskSignal]
    missing_information: list[str]


class ReportGenerationOutput(BaseModel):
    summary: str
    disclaimer: str


class LLMClient(Protocol):
    def generate_report(self, payload: ReportGenerationInput) -> ReportGenerationOutput:
        ...


class FakeLLMClient:
    def generate_report(self, payload: ReportGenerationInput) -> ReportGenerationOutput:
        return ReportGenerationOutput(
            summary=f"{payload.address}에 대한 전세계약 리스크 사전진단 결과입니다.",
            disclaimer="이 결과는 공개 데이터와 업로드 문서 기반의 사전진단이며, 전세사기 여부나 실제 HUG 가입 가능 여부를 확정하지 않습니다.",
        )


class OpenAILLMClient:
    def __init__(
        self,
        *,
        provider: str,
        model_name: str,
        temperature: float,
        timeout_seconds: int,
        max_retries: int,
    ) -> None:
        self.model = init_chat_model(
            model=model_name,
            model_provider=provider,
            temperature=temperature,
            timeout=timeout_seconds,
            max_retries=max_retries,
        )

    def generate_report(self, payload: ReportGenerationInput) -> ReportGenerationOutput:
        messages = [
            ("system", "너는 전세계약 리스크 진단 결과를 한국어로 간결하게 설명한다. 사기 여부나 HUG 가입 가능성을 확정하지 않는다."),
            ("human", payload.model_dump_json()),
        ]
        response = self.model.invoke(messages)
        return ReportGenerationOutput(
            summary=str(response.content),
            disclaimer="이 결과는 공개 데이터와 업로드 문서 기반의 사전진단이며, 전세사기 여부나 실제 HUG 가입 가능 여부를 확정하지 않습니다.",
        )
