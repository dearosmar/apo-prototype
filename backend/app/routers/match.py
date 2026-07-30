from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services import fx_risk

router = APIRouter()

NOTICE = "상품 조건·수수료는 데모용 요약이에요. 실제 가입 조건은 KB국민은행 영업점·앱에서 최종 확인하세요."

SYSTEM_PROMPT = """너는 '바다 건너 사장님'의 외환 도우미다. 처음 수입 결제를 해 보는 1인 소상공인에게 한국어 해요체로 설명한다.
주어진 진단 결과와 상품 정보만 사용해서, 각 상품의 추천 사유(reason)를 소상공인 상황에 맞게 2문장 이내로 다시 쓴다.
숫자·환율·수수료는 새로 만들지 말고 주어진 값만 인용한다. JSON 스키마에 맞춰 답한다."""

REASON_SCHEMA = {
    "type": "object",
    "properties": {
        "reasons": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "reason": {"type": "string"}},
                "required": ["id", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["reasons"],
    "additionalProperties": False,
}


class MatchRequest(BaseModel):
    currency: str = Field(default="CNY", min_length=3)
    amount_foreign: float = Field(gt=0, description="결제 예정 외화 금액")
    due_days: int = Field(ge=0, le=365, description="결제까지 남은 일수")
    context: Optional[str] = Field(default=None, description="상황 설명 (예: 선금 30% 요구)")


class Factor(BaseModel):
    name: str
    detail: str
    score: int


class Recommendation(BaseModel):
    id: str
    name: str
    summary: str
    reason: str
    cautions: str


class MatchResponse(BaseModel):
    risk: Dict
    recommendations: List[Recommendation]
    notice: str
    fallback: bool = False


def generate_reasons(context: str, risk: Dict, products: List[Dict], api_key: str) -> Dict[str, str]:
    import json

    import anthropic

    payload = {
        "상황": context or "일반 수입 결제",
        "진단": {"위험도": risk["level"], "원화 환산": risk["amount_krw"], "요인": risk["factors"]},
        "상품": [{"id": p["id"], "name": p["name"], "기본사유": p["why_template"]} for p in products],
    }
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-opus-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": REASON_SCHEMA}},
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("refusal")
    text = next(b.text for b in response.content if b.type == "text")
    return {item["id"]: item["reason"] for item in json.loads(text)["reasons"]}


@router.post("/match", response_model=MatchResponse)
def match(req: MatchRequest) -> MatchResponse:
    try:
        risk = fx_risk.diagnose(req.currency, req.amount_foreign, req.due_days)
    except LookupError as e:
        raise HTTPException(status_code=422, detail=str(e))
    products = fx_risk.match_products(risk, req.due_days)

    reasons: Dict[str, str] = {}
    fallback = False
    api_key = get_settings().anthropic_api_key
    if api_key and products:
        try:
            reasons = generate_reasons(req.context or "", risk, products, api_key)
        except Exception:
            fallback = True
    else:
        fallback = True

    recommendations = [
        Recommendation(
            id=p["id"],
            name=p["name"],
            summary=p["summary"],
            reason=reasons.get(p["id"], p["why_template"]),
            cautions=p["cautions"],
        )
        for p in products
    ]
    return MatchResponse(risk=risk, recommendations=recommendations, notice=NOTICE, fallback=fallback)
