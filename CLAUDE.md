# CLAUDE.md — 바다 건너 사장님 개발 가이드

KB AI Challenge 출품작. **8/3(월) 접수 마감**, 1인 개발 + Claude 페어 프로그래밍.
서비스 개요·아키텍처·기술 스택은 [README.md](README.md), 일자별 계획·DoD는 [docs/프로토타입_실행계획_0803.md](docs/프로토타입_실행계획_0803.md) 참고.

## 핵심 원칙 (절대 어기지 말 것)

1. **계산은 코드가, 추정과 설명은 LLM이.** 세율·환율·수수료 등 확정 수치는 룰 엔진/공공 API/스냅숏에서만 나온다. LLM은 의도 분류, HS 후보 추정(확신도 표기), 요약, 추천 사유 생성만 담당.
2. **API보다 폴백 먼저.** 모든 외부 API는 `backend/data/snapshots/`의 샘플 JSON으로 먼저 개발하고, 키가 나오면 스위치만 켠다. 네트워크를 꺼도 데모 3종이 돌아야 한다.
3. **매일 저녁 '동작하는 버전'.** 의미 단위로 커밋하고, 하루 끝에는 항상 시연 가능한 상태.
4. 밀리면 컷 순서: ① 환율 위젯 → ② iOS 스캔 → ③ 마진 차트. 절대 사수: 데모 시나리오 3종 + 출처 표기 + 폴백 모드.

## 컨벤션

- **브랜치**: `prefix/#이슈번호` (예: `feat/#6`, `chore/#5`, `task/#10`)
- **커밋**: `[prefix] #이슈번호 작업 내용` (prefix: feat / fix / docs / chore / test / refactor / merge)
- **커밋 작성자**: JUHUI CHOI <dear.ros.mar@gmail.com> 단일 명의. Co-Authored-By 트레일러 금지.
- **이슈/PR**: `.github/` 템플릿 사용. PR 본문에 `closed: #이슈번호` 표기.
- **주석**: 최소화. 코드로 드러나지 않는 제약만 TODO로 남긴다.

## 개발 메모

- 로컬 파이썬은 시스템 3.9 (README의 3.11+는 권장 사양) — `X | Y` 유니온 타입 문법 금지, `typing.Optional` 등 사용. 3.11+ 설치 시 이 항목 갱신할 것.
- 가상환경 `backend/.venv` / 실행 `cd backend && uvicorn app.main:app --reload` / 테스트 `cd backend && pytest`
- Claude 연동 확인: `python scripts/smoke_claude.py` (키 없으면 폴백 메시지)
- `.env`는 절대 커밋 금지 (`backend/.env.example`만 커밋).
- 스냅숏 JSON은 실제 API 응답 형식을 그대로 유지한다 — 키 발급 후 호출부만 갈아끼우기 위함.
