"""LLM 클라이언트 인터페이스 + 구현체"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Protocol

from pydantic import BaseModel

from app.models.diagnoses_models import ClauseSuggestion, RiskSignal, StructuredChecklist

logger = logging.getLogger(__name__)


# ── LLM 오류 분류 ─────────────────────────────────────────────────
class LLMErrorCode(str, Enum):
    CONFIG_MISSING = "LLM_CONFIG_MISSING"
    TIMEOUT = "LLM_TIMEOUT"
    RATE_LIMITED = "LLM_RATE_LIMITED"
    PROVIDER_ERROR = "LLM_PROVIDER_ERROR"
    SCHEMA_INVALID = "LLM_SCHEMA_INVALID"


class LLMError(Exception):
    def __init__(self, code: LLMErrorCode, message: str) -> None:
        self.code = code
        super().__init__(f"[{code}] {message}")


# ── 입출력 스키마 ─────────────────────────────────────────────────
class ReportGenerationInput(BaseModel):
    address: str
    risk_signals: list[RiskSignal]
    missing_information: list[str]


class ReportGenerationOutput(BaseModel):
    summary: str
    disclaimer: str


class ClauseRewriteInput(BaseModel):
    risk_code: str
    draft: str
    reason: str
    contract_facts: dict  # 주소, 임대인, 잔금일 등 계약 정보


class ClauseRewriteOutput(BaseModel):
    rewritten: str
    note: str


class ChecklistRewriteInput(BaseModel):
    contract_stage: str
    items: list[str]
    risk_summary: str


class ChecklistRewriteOutput(BaseModel):
    rewritten_items: list[str]


# ── Protocol (인터페이스) ──────────────────────────────────────────
class LLMClient(Protocol):
    def generate_report(self, payload: ReportGenerationInput) -> ReportGenerationOutput: ...
    def rewrite_clause_drafts(self, clauses: list[ClauseSuggestion], contract_facts: dict) -> list[ClauseSuggestion]: ...
    def rewrite_checklist(self, payload: ChecklistRewriteInput) -> ChecklistRewriteOutput: ...


# ── FakeLLMClient (테스트·offline 용) ────────────────────────────
class FakeLLMClient:
    def generate_report(self, payload: ReportGenerationInput) -> ReportGenerationOutput:
        return ReportGenerationOutput(
            summary=f"{payload.address}에 대한 전세계약 리스크 사전진단 결과입니다.",
            disclaimer=(
                "이 결과는 공개 데이터와 업로드 문서 기반의 사전진단이며, "
                "전세사기 여부나 실제 HUG 가입 가능 여부를 확정하지 않습니다. "
                "실제 계약 전에는 최신 공식 문서와 보증기관 심사 결과, "
                "필요 시 전문가 검토를 확인해야 합니다."
            ),
        )

    def rewrite_clause_drafts(
        self, clauses: list[ClauseSuggestion], contract_facts: dict
    ) -> list[ClauseSuggestion]:
        # Fake: 원본 그대로 반환
        return clauses

    def rewrite_checklist(self, payload: ChecklistRewriteInput) -> ChecklistRewriteOutput:
        return ChecklistRewriteOutput(rewritten_items=payload.items)


# ── OpenAILLMClient ───────────────────────────────────────────────
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
        if not model_name:
            raise LLMError(LLMErrorCode.CONFIG_MISSING, "LLM_MODEL이 설정되지 않았습니다.")
        try:
            from langchain.chat_models import init_chat_model  # type: ignore
            self.model = init_chat_model(
                model=model_name,
                model_provider=provider,
                temperature=temperature,
                timeout=timeout_seconds,
                max_retries=max_retries,
            )
        except Exception as exc:
            raise LLMError(LLMErrorCode.CONFIG_MISSING, str(exc)) from exc

    def _invoke(self, messages: list) -> str:
        try:
            response = self.model.invoke(messages)
            return str(response.content)
        except Exception as exc:
            err_str = str(exc).lower()
            if "timeout" in err_str:
                raise LLMError(LLMErrorCode.TIMEOUT, str(exc)) from exc
            if "rate" in err_str or "429" in err_str:
                raise LLMError(LLMErrorCode.RATE_LIMITED, str(exc)) from exc
            raise LLMError(LLMErrorCode.PROVIDER_ERROR, str(exc)) from exc

    def generate_report(self, payload: ReportGenerationInput) -> ReportGenerationOutput:
        messages = [
            (
                "system",
                "너는 전세계약 리스크 진단 결과를 한국어로 간결하게 설명한다. "
                "사기 여부나 HUG 가입 가능성을 확정하지 않는다. "
                "반드시 주의·면책 문구를 포함한다.",
            ),
            ("human", payload.model_dump_json()),
        ]
        summary = self._invoke(messages)
        return ReportGenerationOutput(
            summary=summary,
            disclaimer=(
                "이 결과는 공개 데이터와 업로드 문서 기반의 사전진단이며, "
                "전세사기 여부나 실제 HUG 가입 가능 여부를 확정하지 않습니다. "
                "실제 계약 전에는 최신 공식 문서와 보증기관 심사 결과, "
                "필요 시 전문가 검토를 확인해야 합니다."
            ),
        )

    def rewrite_clause_drafts(
        self, clauses: list[ClauseSuggestion], contract_facts: dict
    ) -> list[ClauseSuggestion]:
        if not clauses:
            return []
        try:
            import json
            payload = json.dumps(
                {"contract_facts": contract_facts, "clauses": [c.model_dump() for c in clauses]},
                ensure_ascii=False,
            )
            messages = [
                (
                    "system",
                    "너는 전세계약 특약 초안을 한국어로 자연스럽게 다듬는다. "
                    "법적 확정 표현은 사용하지 않고 '확인 권장' 수준으로 작성한다. "
                    "각 특약의 draft 필드만 수정하고 나머지는 그대로 유지하며 JSON 배열로 반환한다.",
                ),
                ("human", payload),
            ]
            result = self._invoke(messages)
            # JSON 파싱 시도
            raw = json.loads(result)
            rewritten: list[ClauseSuggestion] = []
            for orig, new in zip(clauses, raw):
                rewritten.append(orig.model_copy(update={"draft": new.get("draft", orig.draft)}))
            return rewritten
        except Exception as exc:
            logger.warning("특약 LLM 재작성 실패 — 원본 반환: %s", exc)
            return clauses

    def rewrite_checklist(self, payload: ChecklistRewriteInput) -> ChecklistRewriteOutput:
        try:
            import json
            messages = [
                (
                    "system",
                    "너는 전세계약 체크리스트 항목을 사용자 친화적인 한국어로 다듬는다. "
                    "각 항목을 1~2문장으로 유지하고 JSON 배열로 반환한다.",
                ),
                ("human", payload.model_dump_json()),
            ]
            result = self._invoke(messages)
            items = json.loads(result)
            if isinstance(items, list):
                return ChecklistRewriteOutput(rewritten_items=[str(i) for i in items])
            return ChecklistRewriteOutput(rewritten_items=payload.items)
        except Exception as exc:
            logger.warning("체크리스트 LLM 재작성 실패 — 원본 반환: %s", exc)
            return ChecklistRewriteOutput(rewritten_items=payload.items)
