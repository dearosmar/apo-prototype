from typing import Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import get_settings
from app.services import pi_checker

router = APIRouter()

OCR_FALLBACK = "이미지 OCR은 iOS 동행 앱에서 지원 예정이에요. 지금은 PDF나 텍스트 파일로 올려 주세요."
SUMMARY_FALLBACK = "규칙 점검 결과만 표시해요. 항목별 판정 사유를 확인해 주세요."

SYSTEM_PROMPT = """너는 '바다 건너 사장님'의 서류 점검 도우미다. 처음 수입하는 1인 소상공인에게 한국어 해요체로 설명한다.
주어진 추출 결과와 항목별 판정만 근거로, 이 PI로 거래해도 되는지 3문장 이내로 요약한다. 새로운 사실이나 수치를 만들지 않는다."""


class Check(BaseModel):
    item: str
    status: str
    finding: str
    basis: str


class DocCheckResponse(BaseModel):
    filename: str
    label: Optional[str] = None
    extracted: Dict
    checks: List[Check]
    overall: str
    summary: str
    fallback: bool = False


def generate_summary(fields: Dict, checks: List[Dict], overall: str, api_key: str) -> str:
    import json

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    payload = {"추출": fields, "판정": checks, "종합": overall}
    response = client.messages.create(
        model="claude-opus-5",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    )
    if response.stop_reason == "refusal":
        return SUMMARY_FALLBACK
    return next((b.text for b in response.content if b.type == "text"), SUMMARY_FALLBACK)


def analyze(filename: str, text: str, label: Optional[str] = None) -> DocCheckResponse:
    fields = pi_checker.parse_fields(text)
    checks = pi_checker.run_checks(fields)
    overall = pi_checker.overall_status(checks)

    api_key = get_settings().anthropic_api_key
    fallback = False
    if api_key:
        try:
            summary = generate_summary(fields, checks, overall, api_key)
        except Exception:
            summary, fallback = SUMMARY_FALLBACK, True
    else:
        summary, fallback = SUMMARY_FALLBACK, True

    return DocCheckResponse(
        filename=filename,
        label=label,
        extracted=fields,
        checks=[Check(**c) for c in checks],
        overall=overall,
        summary=summary,
        fallback=fallback,
    )


@router.post("/doc-check", response_model=DocCheckResponse)
async def doc_check(file: UploadFile = File(...)) -> DocCheckResponse:
    data = await file.read()
    text = pi_checker.extract_text(file.filename or "upload", data)
    if not text or not text.strip():
        raise HTTPException(status_code=422, detail=OCR_FALLBACK)
    return analyze(file.filename or "upload", text)


@router.get("/doc-check/samples")
def list_samples() -> List[Dict]:
    return [
        {"name": name, "label": label, "filename": filename}
        for name, (filename, label) in pi_checker.SAMPLES.items()
    ]


@router.post("/doc-check/sample/{name}", response_model=DocCheckResponse)
def check_sample(name: str) -> DocCheckResponse:
    if name not in pi_checker.SAMPLES:
        raise HTTPException(status_code=404, detail="없는 샘플이에요 (normal | risky)")
    sample = pi_checker.load_sample(name)
    return analyze(sample["filename"], sample["text"], label=sample["label"])
