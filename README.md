
# 바다 건너 사장님 ⚓

> 1인 수입 셀러를 위한 무역·외환 AI 에이전트

<p>
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.11x-009688?logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/SwiftUI-iOS%2016+-F05138?logo=swift&logoColor=white" />
  <img src="https://img.shields.io/badge/Claude_API-Anthropic-D97757" />
  <img src="https://img.shields.io/badge/RAG-FAISS-0B2A46" />
</p>

---

## 왜 만들었나

중국 공장에 직접 발주해 본 적이 있습니다. 1688과 샤오홍슈에서 공장을 찾고, 위챗으로 중국어 견적을 받고, 위안화로 선금을 보냈습니다. 그 과정에서 두 번 크게 막혔습니다.

**첫째, 원가를 몰랐습니다.** 판매가를 먼저 정해 놓고 나서야 관세·부가세·인증 비용이 얹히는 걸 알았습니다. 계산할 방법을 몰라서가 아니라, 무엇을 계산해야 하는지를 몰랐습니다.

**둘째, 계약서를 읽을 수 없었습니다.** 중국어 PI에 적힌 `全款预付`(100% 선지급)가 어떤 위험인지, `EXW` 조건이 나에게 무엇을 떠넘기는지 판단할 기준이 없었습니다.

무역은 이미 노트북 앞 1인 셀러의 일이 됐는데, 이들에게는 신용장도 포워더도 관세사도 없습니다. 그 공백을 메우는 도구를 만들었습니다.

---

## 무엇을 하는가

자연어로 물으면, 오케스트레이터가 4개의 전문 에이전트 중 적합한 곳으로 라우팅합니다.

| 에이전트 | 하는 일 |
|---|---|
| **① 무역 길잡이** | 수입 절차·KC 인증 등을 RAG로 답변 — 문장마다 `[n]` 인용, 하단에 문서명·페이지 표기 |
| **② 진짜 원가 계산** | HS코드 후보 추정 → 관세·부가세·물류 합산 → 환율 시나리오별 마진 시뮬레이션 |
| **③ 외환·상품 매칭** | 노출 금액×기간 기반 환리스크 진단 → 금융상품 추천(사유·유의사항 병기) |
| **④ 서류 리스크 점검** | PI/인보이스 분석 → 핵심 조건 추출 → 항목별 신호등 리포트 (중국어 지원) |

### 스크린샷

| 무역 길잡이 — 출처가 붙는 답변 | 환리스크 진단 |
|---|---|
| ![](docs/screenshots/chat.png) | ![](docs/screenshots/fx.png) |

| 서류 리스크 리포트 | iOS 동행 앱 |
|---|---|
| ![](docs/screenshots/report.png) | ![](docs/screenshots/ios.png) |

---

## 기술적 의사결정

이 프로젝트에서 내린 판단들과 그 이유입니다.

### 1. 계산은 코드가, 추정과 설명은 LLM이

관세율·환율·세액 같은 **확정 수치는 LLM이 생성하지 않습니다.** 공공 API와 룰베이스 계산 엔진에서만 가져오고, LLM은 HS코드 후보 추정(확신도와 함께)과 결과 설명만 담당합니다.

돈이 걸린 도메인에서 그럴듯한 숫자를 지어내는 것은 틀린 답보다 위험합니다. 계산 함수는 순수 함수로 분리하고 pytest로 손계산과 대조해 검증했습니다.

```python
# 룰베이스: 검증 가능한 계산
cif = item_price + shipping_cost
duty = cif * tariff_rate          # 세율은 스냅숏/API에서만
vat = (cif + duty) * 0.1
landed_cost = cif + duty + vat

# LLM: 추정과 설명만
hs_candidates = estimate_hs_code(item_description)  # confidence 포함
```

### 2. 근거 없으면 답하지 않는다

검색된 문서에 없는 내용은 추측하지 않고, **무엇을 어디서 확인해야 하는지**를 안내합니다.

> "봉제 인형이 완구로 분류되는지, 어떤 인증 종류에 해당하는지는 근거에 나와 있지 않습니다. 제품안전정보센터에서 품목 분류를 확인해 주세요."

RAG 청크에 문서명·페이지 메타데이터를 유지하고, 답변의 모든 `[n]`이 실제 출처와 매칭되는지 회귀 테스트로 검증합니다.

### 3. 폴백 우선 설계

모든 외부 API에 샘플 스냅숏 폴백을 내장했습니다. API 키가 없거나 네트워크가 끊겨도 전체 기능이 동작합니다. 키 발급을 기다리지 않고 개발할 수 있었고, 데모 환경에서도 안정적으로 돌아갑니다.

### 4. iOS는 네이티브에서만 가능한 것에 한정

웹으로 충분한 기능은 웹에 두고, iOS 앱은 두 가지만 맡습니다.

- **서류 촬영 스캔** — VisionKit 촬영 → `VNRecognizeTextRequest`(`zh-Hans`) 온디바이스 중국어 인식 → 점검 API
- **환율 위젯** — WidgetKit으로 결제 D-day까지 환율 트래킹

같은 백엔드를 호출하는 얇은 클라이언트라 로직 중복이 없습니다.

---

## 아키텍처

```
[Web · React+Vite]   [iOS · SwiftUI]
        │                   │
        └────────┬──────────┘
                 ▼
        [FastAPI 백엔드]
   오케스트레이터(Claude API) — 의도 분류·라우팅
   ├─ ① 길잡이   : RAG (임베딩 + FAISS, 출처 메타데이터)
   ├─ ② 원가 계산 : 룰베이스 엔진 + LLM HS 추정
   ├─ ③ 외환 매칭 : 리스크 진단 + 상품 DB
   └─ ④ 서류 점검 : 문서 파서 (텍스트 추출 · OCR)
                 │
                 ▼
   [외부 데이터] 한국수출입은행 환율 API · 관세청 오픈API · 가이드 문서
   (전 구간 스냅숏 폴백)
```

### 주요 API

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/health` | 헬스체크 |
| `POST` | `/ask` | 질문 → 출처 포함 답변 |
| `POST` | `/cost` | 품목·수량·단가 → 환율 시나리오별 마진 |

전체 명세: 서버 실행 후 `http://127.0.0.1:8000/docs`

---

## 기술 스택

**Frontend** React 18 · Vite · Zustand · styled-components
**Backend** FastAPI · Python 3.11
**AI** Claude API · 임베딩 + FAISS
**iOS** SwiftUI · VisionKit · Vision · WidgetKit
**Test** pytest

---

## 실행 방법

### 백엔드

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # API 키는 선택 — 없으면 폴백 모드
uvicorn app.main:app --reload --port 8000
```

### 프론트엔드

```bash
cd frontend
npm install && npm run dev   # http://localhost:5173
```

### 테스트

```bash
cd backend && pytest -v
```

### iOS

```bash
open BadaSajangnim/BadaSajangnim.xcodeproj
```

Signing에 Apple ID를 지정하고, `Config.swift`의 `baseURL`을 맥의 LAN IP(`ipconfig getifaddr en0`)로 변경한 뒤 실기기에서 실행합니다. 문서 카메라는 시뮬레이터에서 동작하지 않습니다.

---

## 프로젝트 구조

```
.
├── backend/
│   ├── app/
│   │   ├── agents/       # 오케스트레이터 · 4개 에이전트
│   │   └── services/     # 계산 룰 엔진 · RAG · 문서 파서
│   ├── data/
│   │   ├── docs/         # RAG 원문
│   │   └── snapshots/    # 폴백 데이터
│   └── tests/
├── frontend/
├── BadaSajangnim/        # iOS
└── docs/
```

---

## 데이터 출처

- 한국수출입은행 현재환율 API (공공데이터포털)
- 관세청 오픈API · 관세법령정보포털 — HS코드·관세율
- 관세청·한국무역협회·제품안전정보센터 공개 가이드 문서 (RAG 지식 베이스)

세율·환율에는 조회 시점과 출처를 함께 기록하며, 최종 확인처(관세청 유니패스 등)를 답변에 안내합니다.

---

## 개발 기록

2026.7.26 – 8.3 · 개인 프로젝트 · 이슈 단위 브랜치 → PR 워크플로

8일간의 일자별 계획과 완료 기준은 [docs/개발일지.md](docs/개발일지.md)에 정리했습니다.

---

*"신용장을 몰라도 되는 첫 수입"*
