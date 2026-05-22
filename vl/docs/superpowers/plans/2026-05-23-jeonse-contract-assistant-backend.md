# Jeonse Contract Assistant Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a backend-only FastAPI + LangGraph prototype that diagnoses jeonse contract risk from user input, MOLIT apartment transactions, optional documents, rule engines, and LLM-generated explanations.

**Architecture:** FastAPI exposes quick and full diagnosis endpoints. LangGraph orchestrates deterministic nodes for address parsing, MOLIT fetch, market filtering, market diagnosis, document extraction, document rule checks, HUG precheck, clause suggestions, checklist generation, and final report building. LLM calls are isolated behind an `LLMClient` interface and used only for wording/report generation.

**Tech Stack:** Python, FastAPI, Pydantic, pydantic-settings, LangGraph, LangChain `init_chat_model`, HTTPX, pytest, python-dotenv, python-multipart.

---

## File Structure

- Create: `pyproject.toml`  
  Project metadata and dependencies.
- Create: `.gitignore`  
  Ignore virtualenv, caches, `.env`, and generated files.
- Create: `.env.example`  
  Document required environment variables without secrets.
- Create: `app/main.py`  
  FastAPI app and route registration.
- Create: `app/api/routes/diagnoses.py`  
  `/diagnoses/quick` and `/diagnoses/full` endpoints.
- Create: `app/core/config.py`  
  Pydantic settings, environment variable loading, validation.
- Create: `app/models/schemas.py`  
  API input/output schemas and shared domain models.
- Create: `app/data/lawd_map.json`  
  Prototype LAWD code map. Start with sample entries used in tests.
- Create: `app/services/address_parser.py`  
  Address normalization, LAWD_CD lookup, dong and apartment keyword parsing.
- Create: `app/clients/molit.py`  
  MOLIT rent/trade API client and response normalization.
- Create: `app/services/market_filter.py`  
  Hierarchical filtering: `complex -> dong -> gu -> gu_all`.
- Create: `app/services/market_diagnosis.py`  
  Deposit status, jeonse rate, gangtong risk, confidence, market risk signals.
- Create: `app/services/document_extractor.py`  
  Document type interface and prototype text extraction hooks.
- Create: `app/services/document_rules.py`  
  Rule-based document cross-checking.
- Create: `app/services/hug_precheck.py`  
  HUG precheck fact evaluation and missing information classification.
- Create: `app/services/clauses.py`  
  Risk signal to clause template mapping.
- Create: `app/services/checklist.py`  
  Stage-based checklist template and risk-based additions.
- Create: `app/clients/llm.py`  
  `LLMClient`, `OpenAILLMClient`, `FakeLLMClient`.
- Create: `app/graph/state.py`  
  LangGraph state type.
- Create: `app/graph/workflow.py`  
  LangGraph workflow assembly and node functions.
- Create: `tests/` files listed per task.

---

### Task 1: Project Scaffold And Settings

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `app/__init__.py`
- Create: `app/core/__init__.py`
- Create: `app/core/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write failing config tests**

```python
# tests/test_config.py
import pytest

from app.core.config import Settings


def test_settings_reads_llm_and_molit_values():
    settings = Settings(
        llm_provider="openai",
        llm_model="gpt-4.1-mini",
        openai_api_key="sk-test",
        molit_api_service_key="molit-test",
        ocr_provider="external",
        ocr_api_key="ocr-test",
        ocr_api_url="https://ocr.example.test",
        llm_timeout_seconds=30,
        llm_max_retries=2,
        llm_temperature=0.2,
    )

    assert settings.llm_provider == "openai"
    assert settings.llm_model == "gpt-4.1-mini"
    assert settings.openai_api_key.get_secret_value() == "sk-test"
    assert settings.molit_api_service_key.get_secret_value() == "molit-test"
    assert settings.ocr_api_key is not None
    assert settings.ocr_api_key.get_secret_value() == "ocr-test"
    assert settings.ocr_api_url == "https://ocr.example.test"
    assert settings.llm_temperature == 0.2


def test_settings_rejects_missing_required_keys():
    with pytest.raises(Exception):
        Settings(llm_provider="openai", llm_model="gpt-4.1-mini")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`  
Expected: FAIL because `app.core.config` does not exist.

- [ ] **Step 3: Create project metadata and settings**

```toml
# pyproject.toml
[project]
name = "jeonse-contract-assistant"
version = "0.1.0"
description = "Backend-only jeonse contract risk diagnosis prototype"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.30.0",
  "pydantic>=2.8.0",
  "pydantic-settings>=2.4.0",
  "python-dotenv>=1.0.1",
  "python-multipart>=0.0.9",
  "httpx>=0.27.0",
  "langgraph>=0.2.0",
  "langchain>=0.3.0",
  "langchain-openai>=0.2.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3.0",
  "pytest-asyncio>=0.24.0",
  "respx>=0.21.1",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

```gitignore
# .gitignore
.env
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
.mypy_cache/
.superpowers/
dist/
build/
*.egg-info/
```

```env
# .env.example
APP_ENV=local
LOG_LEVEL=INFO
LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1-mini
OPENAI_API_KEY=
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
LLM_TEMPERATURE=0.2
MOLIT_API_SERVICE_KEY=
OCR_PROVIDER=local
OCR_API_KEY=
OCR_API_URL=
```

```python
# app/core/config.py
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"

    llm_provider: str = Field(default="openai")
    llm_model: str
    openai_api_key: SecretStr
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 2
    llm_temperature: float = 0.2

    molit_api_service_key: SecretStr
    ocr_provider: str = "local"
    ocr_api_key: SecretStr | None = None
    ocr_api_url: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`  
Expected: PASS.

---

### Task 2: API Schemas

**Files:**
- Create: `app/models/__init__.py`
- Create: `app/models/schemas.py`
- Test: `tests/test_schemas.py`

- [ ] **Step 1: Write failing schema tests**

```python
# tests/test_schemas.py
from app.models.schemas import QuickDiagnosisRequest, RiskSignal


def test_quick_request_uses_frontend_field_names():
    request = QuickDiagnosisRequest(
        address="서울 강서구 가양동 강변아파트",
        area_sqm=50.0,
        user_deposit=250_000_000,
        housing_type="apartment",
        contract_stage="before_contract",
    )

    assert request.area_sqm == 50.0
    assert request.user_deposit == 250_000_000


def test_risk_signal_has_traceable_fields():
    signal = RiskSignal(
        code="JEONSE_RATIO_OVER_80",
        title="전세가율 높음",
        severity="high",
        confidence="medium",
        evidence="전세가율 83%",
        source="market_diagnosis",
        recommended_action="HUG 가입 가능 여부를 확인하세요.",
    )

    assert signal.code == "JEONSE_RATIO_OVER_80"
    assert signal.source == "market_diagnosis"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_schemas.py -v`  
Expected: FAIL because schemas do not exist.

- [ ] **Step 3: Implement schemas**

```python
# app/models/schemas.py
from typing import Literal

from pydantic import BaseModel, Field


RiskSeverity = Literal["info", "low", "medium", "high", "critical"]
Confidence = Literal["high", "medium", "low", "null"]


class QuickDiagnosisRequest(BaseModel):
    address: str
    area_sqm: float = Field(gt=0)
    user_deposit: int = Field(gt=0)
    housing_type: str = "apartment"
    contract_stage: str = "before_contract"


class RiskSignal(BaseModel):
    code: str
    title: str
    severity: RiskSeverity
    confidence: str
    evidence: str
    source: str
    recommended_action: str


class OverallRisk(BaseModel):
    grade: Literal["A", "B", "C", "D"]
    score: int
    level: Literal["안전", "주의", "위험", "매우 위험"]
    one_line_summary: str


class MarketAnalysis(BaseModel):
    average_market_price: int | None
    deposit: int
    jeonse_ratio: float | None
    grade: Literal["safe", "warning", "danger"]
    conversational: str
    details: list[str]
    gangtong_risk: Literal["very_high", "high", "caution", "safe", "null"]
    confidence: Confidence
    confidence_label: Literal["높음", "보통", "낮음", "null"]
    confidence_reason: str | None
    jeonse_count: int
    trade_count: int
    market_jeonse_rate: float | None
    user_jeonse_rate: float | None


class RegistryAnalysis(BaseModel):
    mortgage_max: int = 0
    has_trust: bool = False
    has_seizure: bool = False
    grade: Literal["safe", "warning", "danger"] = "safe"
    conversational: str = "문서가 업로드되지 않아 등기부 분석을 보류했습니다."
    details: list[str] = Field(default_factory=list)


class InsuranceAnalysis(BaseModel):
    eligible: bool | None
    grade: Literal["safe", "warning", "danger"]
    conversational: str
    details: list[str]


class TransactionItem(BaseModel):
    name: str
    dong: str
    area: float
    floor: str | None
    deposit: int
    year: str
    month: str


class TradeItem(BaseModel):
    name: str
    dong: str
    area: float
    floor: str | None
    price: int
    year: str
    month: str


class DiagnosisResponse(BaseModel):
    address: str
    overall_risk: OverallRisk
    market_analysis: MarketAnalysis
    registry_analysis: RegistryAnalysis
    insurance_analysis: InsuranceAnalysis
    checklist: list[str]
    transaction_items: list[TransactionItem]
    trade_items: list[TradeItem]
    risk_signals: list[RiskSignal]
    missing_information: list[str]
    saju_unlocked: bool = True
    saju_lock_message: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_schemas.py -v`  
Expected: PASS.

---

### Task 3: Address Parsing

**Files:**
- Create: `app/data/lawd_map.json`
- Create: `app/services/__init__.py`
- Create: `app/services/address_parser.py`
- Test: `tests/test_address_parser.py`

- [ ] **Step 1: Write failing address parser tests**

```python
# tests/test_address_parser.py
from app.services.address_parser import parse_address


def test_parse_seoul_gangseo_address():
    result = parse_address("서울 강서구 가양동 강변아파트")

    assert result.normalized_address == "서울특별시 강서구 가양동 강변아파트"
    assert result.lawd_cd == "11500"
    assert result.dong == "가양동"
    assert result.apt_keyword == "강변아파"


def test_parse_gyeonggi_suwon_address_long_key_first():
    result = parse_address("경기 수원시 장안구 정자동")

    assert result.normalized_address == "경기도 수원시 장안구 정자동"
    assert result.lawd_cd == "41111"
    assert result.dong == "정자동"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_address_parser.py -v`  
Expected: FAIL because parser does not exist.

- [ ] **Step 3: Implement address parser**

```json
// app/data/lawd_map.json
{
  "서울특별시 강서구": "11500",
  "경기도 수원시 장안구": "41111"
}
```

```python
# app/services/address_parser.py
import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParsedAddress:
    original_address: str
    normalized_address: str
    lawd_cd: str
    dong: str | None
    apt_name: str | None
    apt_keyword: str | None


REPLACEMENTS = [
    ("서울시", "서울특별시"),
    ("서울 ", "서울특별시 "),
    ("부산시", "부산광역시"),
    ("부산 ", "부산광역시 "),
    ("대구시", "대구광역시"),
    ("인천시", "인천광역시"),
    ("광주시", "광주광역시"),
    ("대전시", "대전광역시"),
    ("울산시", "울산광역시"),
    ("경기 ", "경기도 "),
    ("충북 ", "충청북도 "),
    ("충남 ", "충청남도 "),
    ("전북 ", "전라북도 "),
    ("전남 ", "전라남도 "),
    ("경북 ", "경상북도 "),
    ("경남 ", "경상남도 "),
]


def normalize_sido(address: str) -> str:
    normalized = " ".join(address.strip().split())
    for source, target in REPLACEMENTS:
        if normalized.startswith(source):
            normalized = normalized.replace(source, target, 1)
            break
    return normalized


def load_lawd_map() -> dict[str, str]:
    path = Path(__file__).resolve().parents[1] / "data" / "lawd_map.json"
    return json.loads(path.read_text(encoding="utf-8"))


def find_lawd_cd(normalized_address: str, lawd_map: dict[str, str]) -> str:
    for key in sorted(lawd_map, key=len, reverse=True):
        if key in normalized_address:
            return lawd_map[key]
    raise ValueError(f"LAWD_CD를 찾을 수 없습니다: {normalized_address}")


def extract_dong(address: str) -> str | None:
    match = re.search(r"([가-힣]+[동읍면리])\b", address)
    return match.group(1) if match else None


def extract_apt_name(address: str) -> str | None:
    match = re.search(
        r"[동읍면리]\s+([가-힣\w·]+(?:아파트|APT|빌라|오피스텔|타운|파크|힐스|자이|푸르지오|래미안|아이파크|e편한세상|SK뷰|롯데캐슬|현대|두산|대림))",
        address,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def parse_address(address: str) -> ParsedAddress:
    normalized = normalize_sido(address)
    lawd_map = load_lawd_map()
    apt_name = extract_apt_name(normalized)
    return ParsedAddress(
        original_address=address,
        normalized_address=normalized,
        lawd_cd=find_lawd_cd(normalized, lawd_map),
        dong=extract_dong(normalized),
        apt_name=apt_name,
        apt_keyword=apt_name[:4] if apt_name else None,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_address_parser.py -v`  
Expected: PASS.

---

### Task 4: MOLIT Client And Normalization

**Files:**
- Create: `app/clients/__init__.py`
- Create: `app/clients/molit.py`
- Test: `tests/test_molit_client.py`

- [ ] **Step 1: Write failing normalization tests**

```python
# tests/test_molit_client.py
from app.clients.molit import normalize_rent_items, normalize_trade_items


def test_normalize_rent_items_filters_monthly_rent_and_converts_to_won():
    raw = [
        {"aptNm": "강변아파트", "umdNm": "가양동", "excluUseAr": "50.0", "deposit": "25,000", "monthlyRent": "0", "floor": "3", "dealYear": "2024", "dealMonth": "11"},
        {"aptNm": "월세아파트", "umdNm": "가양동", "excluUseAr": "50.0", "deposit": "1,000", "monthlyRent": "50", "floor": "4", "dealYear": "2024", "dealMonth": "11"},
    ]

    result = normalize_rent_items(raw)

    assert len(result) == 1
    assert result[0].deposit == 250_000_000


def test_normalize_trade_items_filters_cancelled_and_converts_to_won():
    raw = [
        {"aptNm": "강변아파트", "umdNm": "가양동", "excluUseAr": "50.0", "dealAmount": "45,000", "dealingGbn": "", "floor": "5", "dealYear": "2024", "dealMonth": "10"},
        {"aptNm": "취소아파트", "umdNm": "가양동", "excluUseAr": "50.0", "dealAmount": "40,000", "dealingGbn": "Y", "floor": "5", "dealYear": "2024", "dealMonth": "10"},
    ]

    result = normalize_trade_items(raw)

    assert len(result) == 1
    assert result[0].price == 450_000_000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_molit_client.py -v`  
Expected: FAIL because MOLIT client does not exist.

- [ ] **Step 3: Implement MOLIT models and normalizers**

```python
# app/clients/molit.py
from dataclasses import dataclass
from datetime import date

import httpx


APT_RENT_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
APT_TRADE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"


@dataclass(frozen=True)
class RentTransaction:
    name: str
    dong: str
    area: float
    floor: str | None
    deposit: int
    year: str
    month: str


@dataclass(frozen=True)
class TradeTransaction:
    name: str
    dong: str
    area: float
    floor: str | None
    price: int
    year: str
    month: str


def _get(item: dict, *keys: str, default: str = "") -> str:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return default


def _money_manwon_to_won(value: str) -> int:
    return int(value.replace(",", "").strip()) * 10_000


def normalize_rent_items(raw_items: list[dict]) -> list[RentTransaction]:
    normalized: list[RentTransaction] = []
    for item in raw_items:
        monthly_rent = int(_get(item, "월세금액", "monthlyRent", default="0").replace(",", ""))
        if monthly_rent != 0:
            continue
        normalized.append(
            RentTransaction(
                name=_get(item, "아파트", "aptNm"),
                dong=_get(item, "법정동", "umdNm"),
                area=float(_get(item, "전용면적", "excluUseAr", default="0")),
                floor=_get(item, "층", "floor", default="") or None,
                deposit=_money_manwon_to_won(_get(item, "보증금액", "deposit", default="0")),
                year=_get(item, "년", "dealYear"),
                month=_get(item, "월", "dealMonth"),
            )
        )
    return normalized


def normalize_trade_items(raw_items: list[dict]) -> list[TradeTransaction]:
    normalized: list[TradeTransaction] = []
    for item in raw_items:
        if _get(item, "해제여부", "dealingGbn", default="") == "Y":
            continue
        normalized.append(
            TradeTransaction(
                name=_get(item, "아파트", "aptNm"),
                dong=_get(item, "법정동", "umdNm"),
                area=float(_get(item, "전용면적", "excluUseAr", default="0")),
                floor=_get(item, "층", "floor", default="") or None,
                price=_money_manwon_to_won(_get(item, "거래금액", "dealAmount", default="0")),
                year=_get(item, "년", "dealYear"),
                month=_get(item, "월", "dealMonth"),
            )
        )
    return normalized


def recent_deal_months(today: date, months: int = 6) -> list[str]:
    result: list[str] = []
    year = today.year
    month = today.month
    for _ in range(months):
        result.append(f"{year}{month:02d}")
        month -= 1
        if month == 0:
            year -= 1
            month = 12
    return result


class MolitClient:
    def __init__(self, service_key: str, timeout_seconds: float = 10.0) -> None:
        self.service_key = service_key
        self.timeout_seconds = timeout_seconds

    async def _fetch_items(self, url: str, lawd_cd: str, deal_ymd: str) -> list[dict]:
        params = {
            "serviceKey": self.service_key,
            "LAWD_CD": lawd_cd,
            "DEAL_YMD": deal_ymd,
            "numOfRows": 1000,
            "pageNo": 1,
            "_type": "json",
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            body = response.json()
        items = body.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if isinstance(items, dict):
            return [items]
        return items or []

    async def fetch_rents(self, lawd_cd: str, deal_ymds: list[str]) -> list[RentTransaction]:
        raw: list[dict] = []
        for deal_ymd in deal_ymds:
            raw.extend(await self._fetch_items(APT_RENT_URL, lawd_cd, deal_ymd))
        return normalize_rent_items(raw)

    async def fetch_trades(self, lawd_cd: str, deal_ymds: list[str]) -> list[TradeTransaction]:
        raw: list[dict] = []
        for deal_ymd in deal_ymds:
            raw.extend(await self._fetch_items(APT_TRADE_URL, lawd_cd, deal_ymd))
        return normalize_trade_items(raw)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_molit_client.py -v`  
Expected: PASS.

---

### Task 5: Market Filtering

**Files:**
- Create: `app/services/market_filter.py`
- Test: `tests/test_market_filter.py`

- [ ] **Step 1: Write failing market filter tests**

```python
# tests/test_market_filter.py
from app.clients.molit import RentTransaction
from app.services.market_filter import select_market_scope


def test_selects_complex_scope_when_three_complex_matches():
    items = [
        RentTransaction("강변아파트", "가양동", 50.0, "1", 250_000_000, "2024", "10"),
        RentTransaction("강변아파트", "가양동", 51.0, "2", 260_000_000, "2024", "11"),
        RentTransaction("강변아파트", "가양동", 49.0, "3", 255_000_000, "2024", "12"),
        RentTransaction("다른아파트", "가양동", 50.0, "4", 200_000_000, "2024", "12"),
    ]

    result = select_market_scope(items, dong="가양동", apt_keyword="강변아파", area_sqm=50.0)

    assert result.scope == "complex"
    assert len(result.items) == 3


def test_falls_back_to_gu_all_when_area_matches_are_insufficient():
    items = [
        RentTransaction("A", "가양동", 80.0, "1", 250_000_000, "2024", "10"),
        RentTransaction("B", "가양동", 85.0, "2", 260_000_000, "2024", "11"),
        RentTransaction("C", "등촌동", 90.0, "3", 255_000_000, "2024", "12"),
    ]

    result = select_market_scope(items, dong="가양동", apt_keyword="강변아파", area_sqm=50.0)

    assert result.scope == "gu_all"
    assert len(result.items) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_market_filter.py -v`  
Expected: FAIL because service does not exist.

- [ ] **Step 3: Implement market filter**

```python
# app/services/market_filter.py
from dataclasses import dataclass
from typing import Protocol, TypeVar


class AreaNamedTransaction(Protocol):
    name: str
    dong: str
    area: float


T = TypeVar("T", bound=AreaNamedTransaction)


@dataclass(frozen=True)
class ScopedTransactions[T]:
    scope: str
    items: list[T]


def filter_by_area(items: list[T], area_sqm: float, tolerance: float = 0.20) -> list[T]:
    if not area_sqm or area_sqm <= 0:
        return items
    return [item for item in items if abs(item.area - area_sqm) / area_sqm <= tolerance]


def select_market_scope(items: list[T], dong: str | None, apt_keyword: str | None, area_sqm: float) -> ScopedTransactions[T]:
    if apt_keyword and dong:
        complex_items = [item for item in items if item.dong == dong and item.name.startswith(apt_keyword)]
        complex_area_items = filter_by_area(complex_items, area_sqm)
        if len(complex_area_items) >= 3:
            return ScopedTransactions(scope="complex", items=complex_area_items)

    if dong:
        dong_items = [item for item in items if item.dong == dong]
        dong_area_items = filter_by_area(dong_items, area_sqm)
        if len(dong_area_items) >= 3:
            return ScopedTransactions(scope="dong", items=dong_area_items)

    gu_area_items = filter_by_area(items, area_sqm)
    if len(gu_area_items) >= 3:
        return ScopedTransactions(scope="gu", items=gu_area_items)

    return ScopedTransactions(scope="gu_all", items=items)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_market_filter.py -v`  
Expected: PASS.

---

### Task 6: Market Diagnosis Rules

**Files:**
- Create: `app/services/market_diagnosis.py`
- Test: `tests/test_market_diagnosis.py`

- [ ] **Step 1: Write failing market diagnosis tests**

```python
# tests/test_market_diagnosis.py
from app.clients.molit import RentTransaction, TradeTransaction
from app.services.market_diagnosis import diagnose_market


def test_diagnose_market_calculates_rates_and_high_risk():
    rents = [
        RentTransaction("강변아파트", "가양동", 50.0, "1", 250_000_000, "2024", "10"),
        RentTransaction("강변아파트", "가양동", 51.0, "2", 260_000_000, "2024", "11"),
        RentTransaction("강변아파트", "가양동", 49.0, "3", 255_000_000, "2024", "12"),
    ]
    trades = [
        TradeTransaction("강변아파트", "가양동", 50.0, "5", 300_000_000, "2024", "10"),
        TradeTransaction("강변아파트", "가양동", 51.0, "6", 310_000_000, "2024", "11"),
        TradeTransaction("강변아파트", "가양동", 49.0, "7", 305_000_000, "2024", "12"),
    ]

    result = diagnose_market(
        address="서울 강서구 가양동 강변아파트",
        user_deposit=250_000_000,
        rent_scope="complex",
        rents=rents,
        trade_scope="complex",
        trades=trades,
    )

    assert result.market_analysis.user_jeonse_rate is not None
    assert result.market_analysis.gangtong_risk == "high"
    assert result.market_analysis.jeonse_count == 3
    assert result.market_analysis.trade_count == 3


def test_diagnose_market_handles_missing_sale_data():
    rents = [
        RentTransaction("강변아파트", "가양동", 50.0, "1", 250_000_000, "2024", "10"),
        RentTransaction("강변아파트", "가양동", 51.0, "2", 260_000_000, "2024", "11"),
        RentTransaction("강변아파트", "가양동", 49.0, "3", 255_000_000, "2024", "12"),
    ]

    result = diagnose_market(
        address="서울 강서구 가양동 강변아파트",
        user_deposit=250_000_000,
        rent_scope="complex",
        rents=rents,
        trade_scope="gu_all",
        trades=[],
    )

    assert result.market_analysis.gangtong_risk == "null"
    assert result.market_analysis.user_jeonse_rate is None
    assert any(signal.code == "NO_SALE_TRANSACTION_DATA" for signal in result.risk_signals)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_market_diagnosis.py -v`  
Expected: FAIL because service does not exist.

- [ ] **Step 3: Implement market diagnosis**

```python
# app/services/market_diagnosis.py
from dataclasses import dataclass
from statistics import mean

from app.clients.molit import RentTransaction, TradeTransaction
from app.models.schemas import MarketAnalysis, RiskSignal


@dataclass(frozen=True)
class MarketDiagnosisResult:
    market_analysis: MarketAnalysis
    risk_signals: list[RiskSignal]


SCOPE_LABELS = {
    "complex": "단지",
    "dong": "동",
    "gu": "구",
    "gu_all": "구 전체",
}


def _gangtong_risk(rate: float | None) -> str:
    if rate is None:
        return "null"
    if rate >= 0.90:
        return "very_high"
    if rate >= 0.80:
        return "high"
    if rate >= 0.70:
        return "caution"
    return "safe"


def _confidence(rent_count: int, trade_count: int, scope: str) -> tuple[str, str]:
    if rent_count >= 10 and trade_count >= 5 and scope not in ("gu", "gu_all"):
        return "high", "높음"
    if (rent_count >= 5 and trade_count >= 3) or (scope == "complex" and rent_count >= 3):
        return "medium", "보통"
    return "low", "낮음"


def _deposit_status(deposit_ratio: float) -> str:
    if deposit_ratio > 1.15:
        return "overpriced"
    if deposit_ratio > 1.05:
        return "slightly_high"
    if deposit_ratio >= 0.90:
        return "fair"
    if deposit_ratio >= 0.75:
        return "cheap"
    return "suspicious"


def diagnose_market(
    *,
    address: str,
    user_deposit: int,
    rent_scope: str,
    rents: list[RentTransaction],
    trade_scope: str,
    trades: list[TradeTransaction],
) -> MarketDiagnosisResult:
    rent_count = len(rents)
    trade_count = len(trades)
    avg_jeonse = int(mean([item.deposit for item in rents])) if rents else None
    avg_sale = int(mean([item.price for item in trades])) if trades else None

    user_jeonse_rate = user_deposit / avg_sale if avg_sale else None
    market_jeonse_rate = avg_jeonse / avg_sale if avg_jeonse and avg_sale else None
    gangtong = _gangtong_risk(user_jeonse_rate)

    confidence, confidence_label = _confidence(rent_count, trade_count, rent_scope)
    confidence_reason = f"{SCOPE_LABELS.get(rent_scope, rent_scope)} 기준 전세 {rent_count}건 · 매매 {trade_count}건 (국토부 아파트 전용)"

    signals: list[RiskSignal] = []
    details: list[str] = []

    if avg_jeonse:
        deposit_ratio = user_deposit / avg_jeonse
        status = _deposit_status(deposit_ratio)
        details.append(f"입력 보증금은 평균 전세 보증금 대비 {deposit_ratio:.1%} 수준입니다.")
        if status == "overpriced":
            signals.append(RiskSignal(code="MARKET_RENT_OVERPRICED", title="전세 보증금 과다", severity="medium", confidence=confidence, evidence="주변 평균 전세보다 15% 초과", source="market_diagnosis", recommended_action="동일 단지와 주변 거래를 추가 확인하세요."))
        elif status == "slightly_high":
            signals.append(RiskSignal(code="MARKET_RENT_SLIGHTLY_HIGH", title="전세 보증금 다소 높음", severity="low", confidence=confidence, evidence="주변 평균 전세보다 5% 초과", source="market_diagnosis", recommended_action="가격 협상 또는 추가 거래 사례 확인이 필요합니다."))
        elif status == "cheap":
            signals.append(RiskSignal(code="MARKET_RENT_CHEAP", title="전세 보증금 저렴", severity="info", confidence=confidence, evidence="주변 평균 전세보다 낮음", source="market_diagnosis", recommended_action="저렴한 사유를 확인하세요."))
        elif status == "suspicious":
            signals.append(RiskSignal(code="MARKET_RENT_SUSPICIOUSLY_LOW", title="비정상 저가 가능성", severity="medium", confidence=confidence, evidence="주변 평균 전세보다 25% 이상 낮음", source="market_diagnosis", recommended_action="허위매물 또는 특수 조건 여부를 확인하세요."))

    if user_jeonse_rate is None:
        signals.append(RiskSignal(code="NO_SALE_TRANSACTION_DATA", title="매매 거래 없음", severity="info", confidence="low", evidence="최근 6개월 매매 거래 표본 없음", source="market_diagnosis", recommended_action="매매가 기반 전세가율 판단을 보류하세요."))
    elif user_jeonse_rate >= 0.90:
        signals.append(RiskSignal(code="JEONSE_RATIO_OVER_90", title="전세가율 매우 높음", severity="critical", confidence=confidence, evidence=f"전세가율 {user_jeonse_rate:.1%}", source="market_diagnosis", recommended_action="계약 전 HUG 가입 가능성과 선순위 권리를 반드시 확인하세요."))
    elif user_jeonse_rate >= 0.80:
        signals.append(RiskSignal(code="JEONSE_RATIO_OVER_80", title="전세가율 높음", severity="high", confidence=confidence, evidence=f"전세가율 {user_jeonse_rate:.1%}", source="market_diagnosis", recommended_action="보증보험 가입 가능 여부를 확인하세요."))
    elif user_jeonse_rate >= 0.70:
        signals.append(RiskSignal(code="JEONSE_RATIO_OVER_70", title="전세가율 주의", severity="medium", confidence=confidence, evidence=f"전세가율 {user_jeonse_rate:.1%}", source="market_diagnosis", recommended_action="집값 하락 가능성을 감안해 등기부와 보증 가능성을 확인하세요."))

    if confidence == "low":
        signals.append(RiskSignal(code="LOW_MARKET_CONFIDENCE", title="시세 추정 신뢰도 낮음", severity="info", confidence="low", evidence=confidence_reason, source="market_diagnosis", recommended_action="실거래 표본이 적어 추가 자료 확인이 필요합니다."))

    grade = "safe"
    if gangtong in ("caution", "high"):
        grade = "warning"
    if gangtong == "very_high":
        grade = "danger"

    market_analysis = MarketAnalysis(
        average_market_price=avg_sale,
        deposit=user_deposit,
        jeonse_ratio=user_jeonse_rate,
        grade=grade,
        conversational="국토교통부 아파트 실거래 기준으로 시세와 전세가율을 추정했습니다.",
        details=details,
        gangtong_risk=gangtong,
        confidence=confidence,
        confidence_label=confidence_label,
        confidence_reason=confidence_reason,
        jeonse_count=rent_count,
        trade_count=trade_count,
        market_jeonse_rate=market_jeonse_rate,
        user_jeonse_rate=user_jeonse_rate,
    )
    return MarketDiagnosisResult(market_analysis=market_analysis, risk_signals=signals)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_market_diagnosis.py -v`  
Expected: PASS.

---

### Task 7: LLM Client Interface

**Files:**
- Create: `app/clients/llm.py`
- Test: `tests/test_llm_client.py`

- [ ] **Step 1: Write failing LLM client tests**

```python
# tests/test_llm_client.py
from app.clients.llm import FakeLLMClient, ReportGenerationInput


def test_fake_llm_client_returns_stable_report_text():
    client = FakeLLMClient()
    result = client.generate_report(
        ReportGenerationInput(
            address="서울 강서구 가양동 강변아파트",
            risk_signals=[],
            missing_information=[],
        )
    )

    assert result.summary
    assert "사전진단" in result.disclaimer
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm_client.py -v`  
Expected: FAIL because client does not exist.

- [ ] **Step 3: Implement LLM client interface**

```python
# app/clients/llm.py
from typing import Protocol

from langchain.chat_models import init_chat_model
from pydantic import BaseModel

from app.models.schemas import RiskSignal


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
            ("human", payload.model_dump_json(ensure_ascii=False)),
        ]
        response = self.model.invoke(messages)
        return ReportGenerationOutput(
            summary=str(response.content),
            disclaimer="이 결과는 공개 데이터와 업로드 문서 기반의 사전진단이며, 전세사기 여부나 실제 HUG 가입 가능 여부를 확정하지 않습니다.",
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_llm_client.py -v`  
Expected: PASS.

---

### Task 8: Document Rules, HUG Precheck, Clauses, Checklist

**Files:**
- Create: `app/services/document_extractor.py`
- Create: `app/services/document_rules.py`
- Create: `app/services/hug_precheck.py`
- Create: `app/services/clauses.py`
- Create: `app/services/checklist.py`
- Test: `tests/test_auxiliary_services.py`

- [ ] **Step 1: Write failing auxiliary service tests**

```python
# tests/test_auxiliary_services.py
from app.models.schemas import RiskSignal
from app.services.checklist import build_checklist
from app.services.clauses import suggest_clauses
from app.services.hug_precheck import run_hug_precheck


def test_hug_precheck_requires_missing_document_facts():
    result = run_hug_precheck(
        user_deposit=250_000_000,
        estimated_sale_price=450_000_000,
        senior_debt_amount=None,
        has_illegal_building=None,
        has_right_restriction=None,
        has_move_in_report=None,
        has_fixed_date=None,
        contract_start_date=None,
        contract_end_date=None,
        balance_date=None,
    )

    assert result.eligible is None
    assert result.grade == "warning"
    assert "선순위채권 금액" in result.details


def test_clause_suggestions_follow_risk_signals():
    signal = RiskSignal(code="MORTGAGE_FOUND", title="근저당 발견", severity="high", confidence="medium", evidence="을구 근저당", source="document_rules", recommended_action="말소 조건 확인")

    result = suggest_clauses([signal])

    assert any("근저당" in item for item in result)


def test_checklist_adds_hug_action_for_high_jeonse_ratio():
    signal = RiskSignal(code="JEONSE_RATIO_OVER_80", title="전세가율 높음", severity="high", confidence="medium", evidence="전세가율 83%", source="market_diagnosis", recommended_action="HUG 확인")

    result = build_checklist(contract_stage="before_contract", risk_signals=[signal], missing_information=[])

    assert any("HUG" in item for item in result)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_auxiliary_services.py -v`  
Expected: FAIL because services do not exist.

- [ ] **Step 3: Implement auxiliary services**

```python
# app/services/hug_precheck.py
from app.models.schemas import InsuranceAnalysis


def run_hug_precheck(
    *,
    user_deposit: int,
    estimated_sale_price: int | None,
    senior_debt_amount: int | None,
    has_illegal_building: bool | None,
    has_right_restriction: bool | None,
    has_move_in_report: bool | None,
    has_fixed_date: bool | None,
    contract_start_date: str | None,
    contract_end_date: str | None,
    balance_date: str | None,
) -> InsuranceAnalysis:
    missing: list[str] = []
    if senior_debt_amount is None:
        missing.append("선순위채권 금액")
    if has_illegal_building is None:
        missing.append("위반건축물 여부")
    if has_right_restriction is None:
        missing.append("권리침해 여부")
    if has_move_in_report is None:
        missing.append("전입신고 여부")
    if has_fixed_date is None:
        missing.append("확정일자 여부")
    if contract_start_date is None:
        missing.append("계약 시작일")
    if contract_end_date is None:
        missing.append("계약 종료일")
    if balance_date is None:
        missing.append("잔금일")
    if estimated_sale_price is None:
        missing.append("추정 주택가격")

    if missing:
        return InsuranceAnalysis(
            eligible=None,
            grade="warning",
            conversational="HUG 가입 가능성 판단에 필요한 정보가 부족합니다.",
            details=missing,
        )

    if has_illegal_building or has_right_restriction:
        return InsuranceAnalysis(
            eligible=False,
            grade="danger",
            conversational="문서상 보증 가입을 어렵게 만들 수 있는 위험 신호가 있습니다.",
            details=["위반건축물 또는 권리침해 여부를 공식 문서로 재확인해야 합니다."],
        )

    return InsuranceAnalysis(
        eligible=True,
        grade="safe",
        conversational="입력 정보 기준 HUG 가입 가능성을 검토해볼 수 있습니다.",
        details=["실제 가입 가능 여부는 HUG 심사 결과에 따라 달라집니다."],
    )
```

```python
# app/services/clauses.py
from app.models.schemas import RiskSignal


CLAUSE_TEMPLATES = {
    "MORTGAGE_FOUND": "잔금일 전까지 등기부상 근저당권을 말소하지 않을 경우 임차인은 계약을 해제할 수 있고, 임대인은 계약금을 즉시 반환한다.",
    "JEONSE_RATIO_OVER_80": "전세보증금 반환보증 가입이 불가능한 경우 임차인은 계약을 해제할 수 있고, 임대인은 계약금을 즉시 반환한다.",
    "OWNER_LANDLORD_MISMATCH": "임대인은 등기부상 소유자와 계약 당사자의 권한 관계를 증명하는 서류를 계약 체결 전 제공한다.",
}


def suggest_clauses(risk_signals: list[RiskSignal]) -> list[str]:
    clauses: list[str] = []
    for signal in risk_signals:
        template = CLAUSE_TEMPLATES.get(signal.code)
        if template and template not in clauses:
            clauses.append(template)
    return clauses
```

```python
# app/services/checklist.py
from app.models.schemas import RiskSignal


BASE_CHECKLIST = {
    "before_visit": ["주변 실거래가를 확인하세요.", "건축물대장 확인 가능 여부를 확인하세요."],
    "before_contract": ["최신 등기부등본을 확인하세요.", "계약서 주소와 등기부 주소가 일치하는지 확인하세요."],
    "before_balance": ["잔금일 당일 등기부등본을 다시 확인하세요.", "전입신고와 확정일자 준비를 확인하세요."],
    "after_move_in": ["전입신고와 확정일자를 완료하세요.", "HUG 보증 신청 상태를 확인하세요."],
}


def build_checklist(contract_stage: str, risk_signals: list[RiskSignal], missing_information: list[str]) -> list[str]:
    items = list(BASE_CHECKLIST.get(contract_stage, BASE_CHECKLIST["before_contract"]))
    codes = {signal.code for signal in risk_signals}
    if "JEONSE_RATIO_OVER_80" in codes or "JEONSE_RATIO_OVER_90" in codes:
        items.append("HUG 전세보증금 반환보증 가입 가능 여부를 계약 전 확인하세요.")
    if "MORTGAGE_FOUND" in codes:
        items.append("근저당 말소 조건을 계약서 특약에 반영하세요.")
    for missing in missing_information:
        items.append(f"{missing} 정보를 추가로 확인하세요.")
    return items
```

```python
# app/services/document_extractor.py
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedDocument:
    document_type: str
    text: str


def extract_text_from_upload(filename: str, content: bytes) -> ExtractedDocument:
    text = content.decode("utf-8", errors="ignore")
    lowered = filename.lower()
    if "registry" in lowered or "등기" in filename:
        document_type = "registry"
    elif "ledger" in lowered or "건축물" in filename:
        document_type = "building_ledger"
    elif "contract" in lowered or "계약" in filename:
        document_type = "contract"
    else:
        document_type = "unknown"
    return ExtractedDocument(document_type=document_type, text=text)
```

```python
# app/services/document_rules.py
from app.models.schemas import RegistryAnalysis, RiskSignal


def analyze_registry_text(text: str) -> tuple[RegistryAnalysis, list[RiskSignal]]:
    has_mortgage = "근저당" in text
    has_trust = "신탁" in text
    has_seizure = "압류" in text or "가압류" in text or "가처분" in text
    signals: list[RiskSignal] = []
    if has_mortgage:
        signals.append(RiskSignal(code="MORTGAGE_FOUND", title="근저당 발견", severity="high", confidence="medium", evidence="등기부 텍스트에 근저당 키워드가 있습니다.", source="document_rules", recommended_action="선순위채권 금액과 말소 조건을 확인하세요."))
    if has_trust:
        signals.append(RiskSignal(code="TRUST_REGISTRATION_FOUND", title="신탁등기 발견", severity="high", confidence="medium", evidence="등기부 텍스트에 신탁 키워드가 있습니다.", source="document_rules", recommended_action="신탁원부와 임대 권한을 확인하세요."))
    if has_seizure:
        signals.append(RiskSignal(code="SEIZURE_FOUND", title="압류 등 권리제한 발견", severity="critical", confidence="medium", evidence="등기부 텍스트에 압류/가압류/가처분 키워드가 있습니다.", source="document_rules", recommended_action="계약을 보류하고 권리관계를 확인하세요."))
    grade = "danger" if has_seizure or has_trust else "warning" if has_mortgage else "safe"
    return RegistryAnalysis(
        mortgage_max=0,
        has_trust=has_trust,
        has_seizure=has_seizure,
        grade=grade,
        conversational="업로드 문서 텍스트 기준으로 등기부 위험 키워드를 확인했습니다.",
        details=[signal.evidence for signal in signals],
    ), signals
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_auxiliary_services.py -v`  
Expected: PASS.

---

### Task 9: LangGraph Workflow

**Files:**
- Create: `app/graph/__init__.py`
- Create: `app/graph/state.py`
- Create: `app/graph/workflow.py`
- Test: `tests/test_workflow.py`

- [ ] **Step 1: Write failing workflow test**

```python
# tests/test_workflow.py
import pytest

from app.clients.llm import FakeLLMClient
from app.clients.molit import RentTransaction, TradeTransaction
from app.graph.workflow import run_quick_diagnosis
from app.models.schemas import QuickDiagnosisRequest


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_workflow.py -v`  
Expected: FAIL because workflow does not exist.

- [ ] **Step 3: Implement workflow**

```python
# app/graph/state.py
from typing import TypedDict

from app.clients.molit import RentTransaction, TradeTransaction
from app.models.schemas import DiagnosisResponse, QuickDiagnosisRequest, RiskSignal
from app.services.address_parser import ParsedAddress


class DiagnosisState(TypedDict, total=False):
    request: QuickDiagnosisRequest
    parsed_address: ParsedAddress
    rents: list[RentTransaction]
    trades: list[TradeTransaction]
    rent_scope: str
    scoped_rents: list[RentTransaction]
    trade_scope: str
    scoped_trades: list[TradeTransaction]
    risk_signals: list[RiskSignal]
    response: DiagnosisResponse
```

```python
# app/graph/workflow.py
from datetime import date

from app.clients.llm import LLMClient, ReportGenerationInput
from app.clients.molit import MolitClient, recent_deal_months
from app.models.schemas import DiagnosisResponse, OverallRisk, QuickDiagnosisRequest, RegistryAnalysis
from app.services.address_parser import parse_address
from app.services.checklist import build_checklist
from app.services.hug_precheck import run_hug_precheck
from app.services.market_diagnosis import diagnose_market
from app.services.market_filter import select_market_scope


def _score_from_signals(codes: set[str]) -> OverallRisk:
    if "JEONSE_RATIO_OVER_90" in codes:
        return OverallRisk(grade="D", score=35, level="매우 위험", one_line_summary="전세가율이 매우 높아 계약 전 정밀 확인이 필요합니다.")
    if "JEONSE_RATIO_OVER_80" in codes:
        return OverallRisk(grade="C", score=60, level="위험", one_line_summary="전세가율이 높아 보증과 권리관계 확인이 필요합니다.")
    if "JEONSE_RATIO_OVER_70" in codes or "LOW_MARKET_CONFIDENCE" in codes:
        return OverallRisk(grade="B", score=78, level="주의", one_line_summary="일부 확인이 필요한 매물입니다.")
    return OverallRisk(grade="A", score=90, level="안전", one_line_summary="공개 실거래 기준 주요 가격 위험 신호는 낮습니다.")


async def run_quick_diagnosis(
    *,
    request: QuickDiagnosisRequest,
    molit_client: MolitClient,
    llm_client: LLMClient,
) -> DiagnosisResponse:
    parsed = parse_address(request.address)
    deal_ymds = recent_deal_months(date.today(), months=6)
    rents = await molit_client.fetch_rents(parsed.lawd_cd, deal_ymds)
    trades = await molit_client.fetch_trades(parsed.lawd_cd, deal_ymds)

    scoped_rents = select_market_scope(rents, parsed.dong, parsed.apt_keyword, request.area_sqm)
    scoped_trades = select_market_scope(trades, parsed.dong, parsed.apt_keyword, request.area_sqm)
    market_result = diagnose_market(
        address=request.address,
        user_deposit=request.user_deposit,
        rent_scope=scoped_rents.scope,
        rents=scoped_rents.items,
        trade_scope=scoped_trades.scope,
        trades=scoped_trades.items,
    )
    risk_signals = list(market_result.risk_signals)
    missing_information = ["등기부등본", "건축물대장", "계약서 초안"]
    checklist = build_checklist(request.contract_stage, risk_signals, missing_information)
    insurance = run_hug_precheck(
        user_deposit=request.user_deposit,
        estimated_sale_price=market_result.market_analysis.average_market_price,
        senior_debt_amount=None,
        has_illegal_building=None,
        has_right_restriction=None,
        has_move_in_report=None,
        has_fixed_date=None,
        contract_start_date=None,
        contract_end_date=None,
        balance_date=None,
    )
    report = llm_client.generate_report(
        ReportGenerationInput(address=request.address, risk_signals=risk_signals, missing_information=missing_information)
    )
    overall = _score_from_signals({signal.code for signal in risk_signals})
    overall.one_line_summary = report.summary

    return DiagnosisResponse(
        address=request.address,
        overall_risk=overall,
        market_analysis=market_result.market_analysis,
        registry_analysis=RegistryAnalysis(details=["문서가 업로드되지 않아 등기부 분석을 보류했습니다."]),
        insurance_analysis=insurance,
        checklist=checklist,
        transaction_items=scoped_rents.items,
        trade_items=scoped_trades.items,
        risk_signals=risk_signals,
        missing_information=missing_information,
        saju_unlocked=True,
        saju_lock_message=None,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_workflow.py -v`  
Expected: PASS.

---

### Task 10: FastAPI Endpoints

**Files:**
- Create: `app/api/__init__.py`
- Create: `app/api/routes/__init__.py`
- Create: `app/api/routes/diagnoses.py`
- Create: `app/main.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

```python
# tests/test_api.py
from fastapi.testclient import TestClient

from app.main import app


def test_health_check():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_quick_diagnosis_accepts_payload(monkeypatch):
    client = TestClient(app)
    payload = {
        "address": "서울 강서구 가양동 강변아파트",
        "area_sqm": 50.0,
        "user_deposit": 250000000,
        "housing_type": "apartment",
        "contract_stage": "before_contract"
    }

    response = client.post("/diagnoses/quick", json=payload)

    assert response.status_code in (200, 503)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py -v`  
Expected: FAIL because FastAPI app does not exist.

- [ ] **Step 3: Implement FastAPI app and routes**

```python
# app/api/routes/diagnoses.py
from fastapi import APIRouter, HTTPException

from app.clients.llm import FakeLLMClient, OpenAILLMClient
from app.clients.molit import MolitClient
from app.core.config import get_settings
from app.graph.workflow import run_quick_diagnosis
from app.models.schemas import DiagnosisResponse, QuickDiagnosisRequest


router = APIRouter(prefix="/diagnoses", tags=["diagnoses"])


@router.post("/quick", response_model=DiagnosisResponse)
async def quick_diagnosis(request: QuickDiagnosisRequest) -> DiagnosisResponse:
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
    try:
        return await run_quick_diagnosis(request=request, molit_client=molit_client, llm_client=llm_client)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="진단 처리 중 외부 API 또는 설정 오류가 발생했습니다.") from exc
```

```python
# app/main.py
from fastapi import FastAPI

from app.api.routes.diagnoses import router as diagnoses_router


app = FastAPI(title="Jeonse Contract Assistant Backend", version="0.1.0")
app.include_router(diagnoses_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_api.py -v`  
Expected: PASS or quick endpoint returns controlled 503 when API keys are absent.

---

### Task 11: Full Diagnosis Endpoint Skeleton

**Files:**
- Modify: `app/api/routes/diagnoses.py`
- Modify: `app/graph/workflow.py`
- Test: `tests/test_full_endpoint.py`

- [ ] **Step 1: Write failing full endpoint test**

```python
# tests/test_full_endpoint.py
from fastapi.testclient import TestClient

from app.main import app


def test_full_endpoint_exists():
    client = TestClient(app)
    response = client.post(
        "/diagnoses/full",
        data={
            "address": "서울 강서구 가양동 강변아파트",
            "area_sqm": "50.0",
            "user_deposit": "250000000",
            "housing_type": "apartment",
            "contract_stage": "before_contract",
        },
        files={"registry_document": ("registry.txt", "근저당".encode("utf-8"), "text/plain")},
    )

    assert response.status_code in (200, 503)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_full_endpoint.py -v`  
Expected: FAIL because endpoint does not exist.

- [ ] **Step 3: Add full endpoint skeleton**

```python
# append to app/api/routes/diagnoses.py
from fastapi import File, Form, UploadFile

from app.services.document_extractor import extract_text_from_upload
from app.services.document_rules import analyze_registry_text


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_full_endpoint.py -v`  
Expected: PASS or controlled 503 when API keys are absent.

---

### Task 12: Final Verification

**Files:**
- No new files.

- [ ] **Step 1: Run full test suite**

Run: `pytest -v`  
Expected: all tests PASS.

- [ ] **Step 2: Start API server**

Run: `uvicorn app.main:app --reload --port 8000`  
Expected: server starts and logs FastAPI startup.

- [ ] **Step 3: Verify health endpoint**

Run: `curl http://127.0.0.1:8000/health`  
Expected: `{"status":"ok"}`

- [ ] **Step 4: Verify quick endpoint with missing keys behavior**

Run:

```bash
curl -X POST http://127.0.0.1:8000/diagnoses/quick \
  -H "Content-Type: application/json" \
  -d '{"address":"서울 강서구 가양동 강변아파트","area_sqm":50.0,"user_deposit":250000000,"housing_type":"apartment","contract_stage":"before_contract"}'
```

Expected: either valid diagnosis when keys are configured or controlled `503` without secret leakage.

---

## Self-Review

- Spec coverage: quick diagnosis, MOLIT market module, address parsing, hierarchical filter, market diagnosis, LLM API abstraction, HUG precheck, document rule skeleton, special clauses, checklist, FastAPI endpoints are covered.
- Known scope limitation: the market module is apartment-only because the provided specification uses MOLIT apartment rent/trade APIs.
- Placeholder scan: no TODO/TBD placeholders are used in implementation steps.
- Type consistency: frontend-compatible names use `area_sqm` and `user_deposit`; internal response keeps `Result.jsx` field names.
