# 전세계약 리스크 진단 Agent Backend 설계

## 1. 목표

전세계약 전 사용자가 확인해야 하는 가격, 문서, 보증, 계약서 리스크를 backend API에서 자동 진단한다.

초기 프로토타입은 웹앱을 포함하지 않는다. 사용자는 API를 통해 주소, 보증금, 면적, 주택유형을 입력하고, 선택적으로 등기부등본, 건축물대장, 임대차계약서 초안을 업로드한다. 서버는 공개 실거래 데이터, OCR 추출 결과, 룰 기반 비교, LLM 설명 생성을 조합해 전세계약 리스크 리포트를 반환한다.

이 시스템은 전세사기 여부를 확정하는 서비스가 아니다. 목표는 계약 전 위험 신호를 발견하고, 사용자가 다음 확인 행동을 수행하도록 돕는 것이다.

## 2. 범위

### 포함

- 국토교통부 실거래가 API 기반 시세 적정성 진단
- 국토교통부 실거래가 API 기반 전세가율 및 깡통전세 위험 추정
- OCR 기반 등기부등본, 건축물대장, 계약서 초안 텍스트 추출
- 룰 기반 문서 교차검증
- 상황별 특약 초안 제안
- HUG 전세보증금 반환보증 가입 사전진단
- 계약 단계별 행동지침 및 체크리스트 생성
- LLM 기반 리포트 요약, 설명, 다음 행동 안내

### 제외

- 웹 프론트엔드
- HF, SGI 보증상품 정밀 비교
- RAG 기반 기준 문서 검색
- 임대인 신용평가
- 세금 체납 자동 조회
- 공인중개사 공모 탐지
- 신분증 진위 확인
- 법률 판단, 소송 가능성 예측, 고소장 자동화

## 3. 기술 스택

- Python
- FastAPI
- LangGraph
- LangChain model wrapper
- Pydantic
- HTTPX
- PDF 텍스트 추출 및 OCR 라이브러리
- pytest

LangGraph는 전체 진단 workflow orchestration을 담당한다. LangChain은 LLM 호출, 모델 wrapper, 추후 RAG 확장을 위한 보조 컴포넌트로 사용한다.

## 4. 아키텍처

```text
FastAPI
  -> LangGraph diagnosis workflow
    -> input normalization service
    -> MOLIT transaction service
    -> market analysis rule engine
    -> jeonse ratio rule engine
    -> OCR/document extraction service
    -> document risk rule engine
    -> special clause service
    -> HUG precheck service
    -> checklist service
    -> LLM report service
```

핵심 원칙은 계산과 판정 근거를 백엔드 룰 엔진이 만들고, LLM은 설명과 행동지침 생성에만 사용한다는 것이다.

## 5. API 설계

### POST /diagnoses/quick

주소, 보증금, 면적, 주택유형 기반 빠른 진단 API다.

주요 입력:

- address
- area_sqm
- user_deposit
- housing_type
- contract_stage

주요 출력:

- market_analysis
- jeonse_ratio_analysis
- risk_signals
- missing_information
- checklist
- summary
- disclaimer

### POST /diagnoses/full

빠른 진단 입력에 문서 업로드를 추가한 정밀 진단 API다.

추가 입력:

- registry_document
- building_ledger_document
- draft_contract_document

추가 출력:

- document_analysis
- clause_suggestions
- hug_precheck
- document_based_risk_signals

## 6. LangGraph Workflow

```text
UserInput
  -> AddressParseNode
  -> MarketDataFetchNode
  -> MarketFilterNode
  -> MarketDiagnosisNode
  -> extract_documents
  -> analyze_document_risks
  -> RiskScoreNode
  -> generate_clause_suggestions
  -> run_hug_precheck
  -> generate_checklist
  -> ReportBuildNode
```

문서가 업로드되지 않은 경우 `extract_documents`와 `analyze_document_risks`는 스킵하고, 문서 기반 항목은 `missing_information`과 `additional_check_required`로 처리한다.

## 7. 시세 진단 모듈

초기 프로토타입의 시세 진단 모듈은 프론트엔드의 `realEstateApi.js`와 `mockApi.js` 로직을 백엔드 LangGraph 노드로 이관하는 것을 기준으로 한다.

초기 구현은 국토교통부 아파트 전월세/매매 실거래 API만 사용한다. 따라서 시세 진단 결과는 아파트 실거래 기반 추정이며, 빌라, 연립, 다세대, 오피스텔 등은 별도 API 확장 전까지 같은 정확도로 지원하지 않는다.

### 7.1 입력값

- `address`: 사용자 입력 주소 자유형식
- `area_sqm`: 전용면적 제곱미터
- `user_deposit`: 보증금 원 단위

### 7.2 외부 API

전세 API:

- 제공처: 국토교통부 공공데이터포털
- 엔드포인트: `RTMSDataSvcAptRent/getRTMSDataSvcAptRent`
- 주요 파라미터: `serviceKey`, `LAWD_CD`, `DEAL_YMD`, `numOfRows=1000`, `pageNo=1`, `_type=json`

매매 API:

- 제공처: 국토교통부 공공데이터포털
- 엔드포인트: `RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade`
- 주요 파라미터: `serviceKey`, `LAWD_CD`, `DEAL_YMD`, `numOfRows=1000`, `pageNo=1`, `_type=json`

공통 원칙:

- 조회 기간은 최근 6개월로 한다.
- API 금액 단위는 만원이므로 원 단위 변환 시 `* 10000`을 적용한다.
- 서비스키는 URL 파라미터로 전달하며 인코딩 문제를 별도 처리한다.

### 7.3 주소 파싱 및 LAWD_CD 변환

주소는 먼저 시도 약칭을 정규화한다.

- `서울시`, `서울 ` -> `서울특별시`
- `부산시`, `부산 ` -> `부산광역시`
- `대구시` -> `대구광역시`
- `인천시` -> `인천광역시`
- `광주시` -> `광주광역시`
- `대전시` -> `대전광역시`
- `울산시` -> `울산광역시`
- `경기 ` -> `경기도`
- `충북 ` -> `충청북도`
- `충남 ` -> `충청남도`
- `전북 ` -> `전라북도`
- `전남 ` -> `전라남도`
- `경북 ` -> `경상북도`
- `경남 ` -> `경상남도`

`LAWD_CD`는 법정동코드 앞 5자리인 시군구 코드다. 초기 구현에서는 전국 시군구 JSON map을 사용하며, 주소 문자열 포함 여부로 매칭한다. 매칭은 긴 키 우선으로 수행한다.

동 추출은 정규식 `([가-힣]+[동읍면리])\b`를 사용한다. 아파트명은 동/읍/면/리 이후에 나오는 단지성 키워드를 우선 추출하고, 단지 필터에는 아파트명 앞 4글자를 사용한다.

### 7.4 데이터 전처리

전세 거래는 월세 거래를 제거한다.

- `월세금액` 또는 `monthlyRent`가 0인 거래만 사용한다.

매매 거래는 취소 거래를 제거한다.

- `해제여부`가 `Y`인 거래는 제외한다.
- 빈 문자열, `None`, `N`은 유효 거래로 본다.

전세와 매매 주요 필드는 한글 필드명과 영문 필드명을 모두 허용한다.

- 아파트명: `아파트` 또는 `aptNm`
- 법정동명: `법정동` 또는 `umdNm`
- 전용면적: `전용면적` 또는 `excluUseAr`
- 보증금: `보증금액` 또는 `deposit`
- 월세: `월세금액` 또는 `monthlyRent`
- 매매가: `거래금액` 또는 `dealAmount`
- 취소 여부: `해제여부` 또는 `dealingGbn`
- 층: `층` 또는 `floor`
- 계약 연도: `년` 또는 `dealYear`
- 계약 월: `월` 또는 `dealMonth`

### 7.5 계층적 근처 필터

좌표 없이 행정구역 계층으로 근처를 정의한다. 전세와 매매는 각각 독립적으로 필터링한다. 전세 scope가 `complex`여도 매매 scope는 `dong`이 될 수 있다. 최종 응답의 대표 scope는 전세 기준으로 둔다.

필터 우선순위:

1. `complex`: 아파트명 앞 4글자와 동이 일치하는 거래 중 면적 ±20%
2. `dong`: 같은 동 거래 중 면적 ±20%
3. `gu`: 같은 시군구 거래 중 면적 ±20%
4. `gu_all`: 같은 시군구 전체 거래

각 단계에서 최소 3건 이상 확보되면 해당 범위를 채택한다. 면적 필터는 `abs(item_area - area_sqm) / area_sqm <= 0.20` 기준을 사용한다.

### 7.6 계산 공식

전세 보증금 평균:

```text
avg_jeonse = mean(jeonse_deposits)
```

매매가 평균:

```text
avg_sale = mean(trade_prices) or null
```

보증금 시세 비율:

```text
deposit_ratio = user_deposit / avg_jeonse
```

보증금 상태:

- `deposit_ratio > 1.15`: `overpriced`
- `deposit_ratio > 1.05`: `slightly_high`
- `deposit_ratio >= 0.90`: `fair`
- `deposit_ratio >= 0.75`: `cheap`
- 그 외: `suspicious`

사용자 전세가율:

```text
user_jeonse_rate = user_deposit / avg_sale
```

지역 평균 전세가율:

```text
market_jeonse_rate = avg_jeonse / avg_sale
```

매매 데이터가 없으면 `user_jeonse_rate`와 `market_jeonse_rate`는 `null`이다.

### 7.7 깡통전세 위험 판정

전세가율 위험 판정은 법적 확정 기준이 아니라 MVP 리스크 휴리스틱이다.

- 90% 이상: `very_high`
- 80% 이상 90% 미만: `high`
- 70% 이상 80% 미만: `caution`
- 70% 미만: `safe`
- 매매 데이터 없음: `null`

### 7.8 신뢰도 판정

신뢰도는 표본 수와 필터 scope를 기준으로 산정한다.

- `high`: 전세 10건 이상, 매매 5건 이상, scope가 `gu` 또는 `gu_all`이 아님
- `medium`: 전세 5건 이상 및 매매 3건 이상, 또는 scope가 `complex`이고 전세 3건 이상
- `low`: 그 외

신뢰도 설명 문구는 다음 구조를 사용한다.

```text
{scope_label} 기준 전세 {jeonse_count}건 · 매매 {trade_count}건 (국토부 아파트 전용)
```

### 7.9 시세 진단 risk signal

주요 risk signal:

- `MARKET_RENT_OVERPRICED`
- `MARKET_RENT_SLIGHTLY_HIGH`
- `MARKET_RENT_CHEAP`
- `MARKET_RENT_SUSPICIOUSLY_LOW`
- `JEONSE_RATIO_OVER_70`
- `JEONSE_RATIO_OVER_80`
- `JEONSE_RATIO_OVER_90`
- `LOW_MARKET_CONFIDENCE`
- `NO_SALE_TRANSACTION_DATA`

## 8. 프론트엔드 호환 응답 스키마

초기 backend 응답은 기존 `Result.jsx`가 렌더링할 수 있도록 다음 필드명을 유지한다. 내부적으로는 `risk_signal` 기반 모델을 사용하되, `ReportBuildNode`에서 프론트 호환 응답으로 조립한다.

최상위 필드:

- `address`
- `overall_risk`
- `market_analysis`
- `registry_analysis`
- `insurance_analysis`
- `checklist`
- `transaction_items`
- `trade_items`
- `saju_unlocked`
- `saju_lock_message`

`overall_risk`:

- `grade`: `A`, `B`, `C`, `D`
- `score`: 0부터 100까지 정수
- `level`: `안전`, `주의`, `위험`, `매우 위험`
- `one_line_summary`

`market_analysis`:

- `average_market_price`
- `deposit`
- `jeonse_ratio`
- `grade`: `safe`, `warning`, `danger`
- `conversational`
- `details`
- `gangtong_risk`: `very_high`, `high`, `caution`, `safe`, `null`
- `confidence`: `high`, `medium`, `low`, `null`
- `confidence_label`: `높음`, `보통`, `낮음`, `null`
- `confidence_reason`
- `jeonse_count`
- `trade_count`
- `market_jeonse_rate`
- `user_jeonse_rate`

`transaction_items`는 전세 거래 목록이며 `name`, `dong`, `area`, `floor`, `deposit`, `year`, `month`를 포함한다.

`trade_items`는 매매 거래 목록이며 `name`, `dong`, `area`, `floor`, `price`, `year`, `month`를 포함한다.

`saju_unlocked`와 `saju_lock_message`는 기존 프론트 호환을 위해 유지하되, backend risk diagnosis 도메인 로직에는 사용하지 않는다.

## 9. 문서 리스크 분석

초기 프로토타입은 OCR, 구조화 추출, 룰 기반 비교, LLM 설명 구조로 구현한다. RAG는 사용하지 않는다.

문서 처리 흐름:

```text
문서 업로드
  -> 문서 유형 분류
  -> PDF 텍스트 추출
  -> OCR fallback
  -> 핵심 필드 구조화
  -> 사용자 입력 및 문서 간 교차검증
  -> risk signal 생성
```

등기부등본 추출 항목:

- 발급일
- 부동산 주소
- 소유자
- 갑구 권리관계
- 을구 권리관계
- 근저당권
- 압류, 가압류, 가처분
- 신탁등기
- 경매개시결정
- 전세권, 임차권 등기
- 채권최고액
- 말소 여부
- 권리 설정일

건축물대장 추출 항목:

- 주소
- 건축물 종류
- 주용도
- 전용면적
- 층, 호수 정보
- 위반건축물 여부
- 사용승인일
- 대장 종류

계약서 초안 추출 항목:

- 계약 주소
- 임대인
- 임차인
- 보증금
- 계약기간
- 잔금일
- 특약
- 계좌 정보 존재 여부

교차검증 항목:

- 사용자 입력 주소와 등기부 주소 일치 여부
- 사용자 입력 주소와 건축물대장 주소 일치 여부
- 계약서 주소와 등기부 주소 일치 여부
- 계약서 임대인과 등기부 소유자 일치 여부
- 입력 보증금과 계약서 보증금 일치 여부
- 입력 면적과 건축물대장 면적 차이
- 입력 주택유형과 건축물대장 용도 일치 여부
- 등기부 발급일이 오래됐는지 여부

주요 risk signal:

- `OWNER_LANDLORD_MISMATCH`
- `ADDRESS_MISMATCH`
- `AREA_MISMATCH`
- `MORTGAGE_FOUND`
- `SEIZURE_FOUND`
- `PROVISIONAL_SEIZURE_FOUND`
- `TRUST_REGISTRATION_FOUND`
- `AUCTION_START_FOUND`
- `ILLEGAL_BUILDING_FOUND`
- `NON_RESIDENTIAL_USAGE_FOUND`
- `OLD_REGISTRY_DOCUMENT`

## 10. 특약 초안 제안

특약은 LLM 단독 생성이 아니라 룰 기반 상황 분류, 특약 템플릿, LLM 문장 정리 구조로 구현한다.

처리 흐름:

```text
risk signal
  -> 상황 분류
  -> 특약 템플릿 선택
  -> 계약 정보 변수 삽입
  -> LLM 문장 정리
  -> 주의 문구 포함 출력
```

초기 특약 카테고리:

- 근저당 말소 조건
- 권리변동 금지
- HUG 보증 가입 불가 시 계약 해제
- 임대인과 소유자 불일치 확인
- 대리인 계약 시 권한 확인
- 위반건축물 또는 용도 불일치 확인
- 잔금일 등기부 재확인 조건

특약 출력은 초안, 필요한 이유, 적용 조건, 확인할 사항, 전문가 검토 필요 문구를 포함한다.

## 11. HUG 가입 사전진단

초기 프로토타입은 HUG 전세보증금 반환보증만 대상으로 한다. HF, SGI는 제외한다.

처리 흐름:

```text
사용자 입력 + 가격 분석 + 문서 분석
  -> HUG 진단 facts 생성
  -> HUG 룰 엔진
  -> 가입 가능성 분류
  -> 부족한 정보 생성
  -> LLM 설명 생성
```

체크 항목:

- 보증금 한도
- 주택유형
- 계약기간
- 신청 가능 시점
- 계약 시작일 및 종료일
- 잔금일
- 전입신고 및 확정일자 여부
- 위반건축물 여부
- 근저당, 압류, 가압류, 가처분, 신탁 등 권리관계
- 선순위채권 금액
- 보증금과 선순위채권의 추정 주택가격 대비 비율
- 임대인과 소유자 일치 여부

출력 단계:

- 가입 가능성 있음
- 추가 확인 필요
- 가입 어려울 가능성 높음

HUG 결과에는 `blocking_reasons`, `missing_information`, `estimated_guarantee_limit`, `guarantee_limit_confidence`를 포함한다. 선순위채권 금액, 최신 등기부, 위반건축물 여부, 전입신고 여부, 확정일자 여부, 계약 시작일, 계약 종료일, 잔금일이 없으면 가입 가능성을 확정하지 않고 추가 확인 필요로 분류한다.

HUG 사전진단은 공식 심사를 대체하지 않는다. 국토교통부 실거래가 기반 주택가격은 기관이 인정하는 공식 주택가격이 아니라 추정값으로만 사용한다.

## 12. 계약 단계별 행동지침

체크리스트는 정적 템플릿, risk signal 기반 동적 항목 추가, LLM 설명으로 구현한다.

단계:

- 집 보기 전
- 계약 전
- 잔금 전
- 입주 직후

처리 흐름:

```text
contract_stage
  + market signals
  + document signals
  + HUG precheck result
  + clause suggestions
  -> checklist rule engine
  -> priority sorting
  -> LLM wording
```

출력 구조:

- 지금 반드시 해야 할 일
- 계약 전까지 확인할 일
- 빠진 문서
- 위험 신호 때문에 추가된 항목
- 완료 여부 체크용 항목

초기 MVP에서는 리마인더 기능을 제외한다.

## 13. 공통 데이터 모델

모든 분석 결과는 `risk_signal` 중심으로 연결한다.

`risk_signal` 필드:

- code
- title
- severity
- confidence
- evidence
- source
- recommended_action

최종 리포트 필드:

- summary
- market_analysis
- jeonse_ratio_analysis
- document_analysis
- clause_suggestions
- hug_precheck
- checklist
- risk_signals
- missing_information
- disclaimer

## 14. LLM 사용 원칙

LLM이 담당하는 일:

- risk signal 설명
- 사용자 친화적 요약
- 다음 행동 안내
- 특약 초안 문장 정리
- 최종 리포트 생성

LLM이 담당하지 않는 일:

- 시세 계산
- 전세가율 계산
- 문서 간 일치 여부 최종 판단
- HUG 가입 가능 여부 확정
- 전세사기 여부 단정
- 법률 자문 확정

## 15. 검증 전략

초기 테스트는 룰 엔진과 workflow 중심으로 작성한다.

테스트 대상:

- 국토부 실거래 데이터 정규화
- 유사 거래 필터링
- 전세가율 계산
- risk signal 생성
- 문서 필드 추출 결과의 룰 비교
- 특약 템플릿 선택
- HUG 사전진단 분류
- 문서 없는 quick diagnosis 경로
- 문서 있는 full diagnosis 경로

LLM 출력은 엄격한 문장 단위 테스트보다 구조화 출력 스키마 검증, 금지 표현 필터링, 필수 고지 포함 여부를 테스트한다.

## 16. API Key 및 설정 관리

API Key와 외부 서비스 설정값은 코드에 저장하지 않는다. 로컬 개발에서는 `.env` 파일을 사용하고, 배포 환경에서는 secret manager 또는 배포 플랫폼의 environment variable 기능을 사용한다.

필요한 설정값:

- `LLM_PROVIDER`
- `LLM_MODEL`
- `OPENAI_API_KEY` 또는 선택한 LLM provider API key
- `MOLIT_API_SERVICE_KEY`
- `OCR_PROVIDER`
- `OCR_API_KEY`
- `OCR_API_URL`
- 로컬 OCR 사용 여부
- `APP_ENV`
- `LOG_LEVEL`

초기 프로토타입에서는 LLM provider를 교체할 수 있도록 wrapper 인터페이스를 둔다. 국토교통부 실거래가 API는 `MOLIT_API_SERVICE_KEY`를 통해 호출한다.

OCR은 초기 기본값을 `OCR_PROVIDER=local`로 둔다. 로컬 OCR 또는 PDF 텍스트 추출만 사용할 경우 API Key는 필요하지 않다. 외부 OCR 서비스를 사용하는 경우에만 `OCR_API_KEY`와 필요 시 `OCR_API_URL`을 설정한다. OCR provider가 `local`이 아닌데 `OCR_API_KEY`가 없으면 서버 시작 또는 OCR 실행 시 명확한 설정 오류를 반환한다.

### 16.1 LLM 호출 방식

LLM 호출은 application code에서 provider SDK를 직접 호출하지 않고 `LLMClient` 인터페이스를 통해서만 수행한다. LangGraph node는 `LLMClient`를 dependency로 주입받고, report generation, 특약 문장 정리, 체크리스트 문장 정리에만 사용한다.

초기 구현은 OpenAI-compatible chat completion client를 기본값으로 둔다.

환경변수:

- `LLM_PROVIDER=openai`
- `LLM_MODEL`
- `OPENAI_API_KEY`
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_RETRIES`
- `LLM_TEMPERATURE`

호출 원칙:

- LLM API Key는 서버 시작 시 환경변수에서만 읽는다.
- 요청 본문이나 응답 본문에 API Key를 포함하지 않는다.
- LangGraph state에는 LLM API Key를 저장하지 않는다.
- LLM 호출 함수는 구조화된 입력만 받는다. 원본 OCR 텍스트 전체를 무조건 넘기지 않고, rule engine이 만든 `risk_signal`, `missing_information`, `facts`를 우선 사용한다.
- 개인정보와 민감정보는 LLM 호출 전에 가능한 범위에서 마스킹한다.
- LLM 출력은 Pydantic schema로 검증한다.
- LLM 실패 시 전체 진단을 실패시키지 않고, 룰 기반 결과와 "LLM 설명 생성 실패" 상태를 반환한다.

LLM 사용 위치:

- `generate_final_report`
- `generate_clause_suggestions`의 문장 정리 단계
- `generate_checklist`의 사용자 안내 문장 정리 단계

LLM 비사용 위치:

- 국토교통부 실거래가 조회
- 시세 적정성 계산
- 전세가율 계산
- 문서 간 주소, 금액, 이름 일치 여부 비교
- HUG 가입 사전진단 분류
- risk signal severity 산정

### 16.2 LLM Client Interface

초기 구현에서 필요한 최소 인터페이스는 다음과 같다.

```python
class LLMClient:
    def generate_report(self, payload: ReportGenerationInput) -> ReportGenerationOutput:
        ...

    def rewrite_clause_drafts(self, payload: ClauseRewriteInput) -> ClauseRewriteOutput:
        ...

    def rewrite_checklist(self, payload: ChecklistRewriteInput) -> ChecklistRewriteOutput:
        ...
```

운영 구현체:

- `OpenAILLMClient`

테스트 구현체:

- `FakeLLMClient`

`FakeLLMClient`는 고정 응답을 반환해 unit test와 workflow test가 외부 LLM API 없이 실행되도록 한다.

### 16.3 LLM 오류 처리

LLM 호출 실패는 다음처럼 분류한다.

- `LLM_CONFIG_MISSING`: API Key 또는 model 설정 누락
- `LLM_TIMEOUT`: timeout 초과
- `LLM_RATE_LIMITED`: rate limit
- `LLM_PROVIDER_ERROR`: provider API 오류
- `LLM_SCHEMA_INVALID`: 응답이 schema 검증 실패

오류 발생 시 API 응답에는 내부 provider error 원문을 그대로 노출하지 않는다. 사용자 응답에는 설명 생성이 제한되었다는 상태와 룰 기반 진단 결과만 포함한다.

### 16.4 LLM 비용 및 토큰 관리

초기 프로토타입은 비용 예측 가능성을 위해 LLM 호출 횟수를 제한한다.

- quick diagnosis: 최종 리포트 생성 1회
- full diagnosis: 특약 문장 정리 1회, 체크리스트 문장 정리 1회, 최종 리포트 생성 1회

LLM에 전달하는 context는 원문 문서 전체가 아니라 구조화된 분석 결과를 기본으로 한다. OCR 원문이 필요한 경우에도 관련 snippet만 선택해 전달한다.

테스트 환경에서는 실제 API Key를 사용하지 않는다. 국토교통부 API, OCR, LLM 호출은 mock client 또는 fixture 응답으로 대체한다. CI에서도 실제 key 없이 룰 엔진과 workflow 테스트가 가능해야 한다.

보안 원칙:

- API Key는 repository에 커밋하지 않는다.
- `.env`는 `.gitignore`에 포함한다.
- 로그에 API Key, 원문 문서, 주민등록번호, 계좌번호 등 민감정보를 남기지 않는다.
- API 호출 실패 시 key 값을 포함하지 않는 안전한 에러 메시지를 반환한다.
- 운영 환경에서는 요청별 사용량과 외부 API 실패율을 기록하되, 개인정보는 최소화한다.

## 17. 주요 고지 문구

최종 리포트에는 다음 의미의 고지를 포함한다.

```text
이 결과는 공개 데이터와 업로드 문서 기반의 사전진단이며, 전세사기 여부나 실제 HUG 가입 가능 여부를 확정하지 않습니다. 실제 계약 전에는 최신 공식 문서와 보증기관 심사 결과, 필요 시 전문가 검토를 확인해야 합니다.
```

## 18. 향후 고도화

- RAG 기반 서울시 AtoZ, HUG 기준, 전세사기 유형 자료 연결
- HF, SGI 보증상품 비교
- 공인중개사 등록 확인
- 등기부 공식 조회 연동
- 사건 타임라인 및 피해 의심 대응 모드
- 리마인더 및 계약 일정 알림
- LangSmith 기반 trace, 평가, 회귀 테스트
