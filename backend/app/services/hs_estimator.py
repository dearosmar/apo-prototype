import json
from typing import Dict, List

UNIPASS_NOTICE = "HS코드는 추정 후보예요. 실제 세율은 관세청 유니패스(unipass.customs.go.kr)에서 HS 10자리 기준으로 최종 확인하세요."
LOW_CONFIDENCE_NOTICE = "확신도가 낮아 관세사 상담 또는 직접 확인이 필요해요. "
CONFIDENCE_THRESHOLD = 0.5

KEYWORD_RULES = [
    (("인형", "완구", "장난감", "토이"), {"hs_code": "9503", "name": "완구(인형·장난감 포함)"}),
    (("티셔츠", "셔츠", "의류"), {"hs_code": "6109", "name": "티셔츠·메리야스(편물제)"}),
    (("가방", "파우치", "케이스"), {"hs_code": "4202", "name": "가방·케이스류"}),
    (("화장품", "립스틱", "크림"), {"hs_code": "3304", "name": "미용·메이크업용 화장품"}),
    (("주전자", "전열", "히터"), {"hs_code": "8516", "name": "가정용 전열기기"}),
]

HS_SCHEMA = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "hs_code": {"type": "string", "description": "HS 4자리 호(예: 9503)"},
                    "name": {"type": "string"},
                    "confidence": {"type": "number"},
                    "reason": {"type": "string"},
                },
                "required": ["hs_code", "name", "confidence", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["candidates"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """너는 한국 수입 실무의 HS코드 분류 보조 도구다. 품목 설명을 보고 한국 관세율표 기준 HS 4자리(호) 후보를 최대 3개 추정한다.
- confidence는 0~1 사이 수치로, 설명이 모호할수록 낮게 준다.
- reason은 소상공인이 이해할 수 있는 한 문장으로 쓴다.
- 후보를 특정할 수 없으면 빈 배열을 반환한다."""


def _keyword_fallback(description: str) -> List[Dict]:
    for keywords, item in KEYWORD_RULES:
        if any(k in description for k in keywords):
            return [
                {
                    "hs_code": item["hs_code"],
                    "name": item["name"],
                    "confidence": 0.5,
                    "reason": "키워드 규칙 매칭 결과예요(오프라인 폴백).",
                }
            ]
    return []


def _call_claude(description: str, api_key: str) -> List[Dict]:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-opus-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": HS_SCHEMA}},
        messages=[{"role": "user", "content": f"품목 설명: {description}"}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("refusal")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)["candidates"]


def estimate_hs_candidates(description: str, api_key: str) -> Dict:
    if not api_key:
        return {
            "candidates": _keyword_fallback(description),
            "notice": LOW_CONFIDENCE_NOTICE + UNIPASS_NOTICE,
            "fallback": True,
        }
    try:
        candidates = _call_claude(description, api_key)
    except Exception:
        return {
            "candidates": _keyword_fallback(description),
            "notice": LOW_CONFIDENCE_NOTICE + UNIPASS_NOTICE,
            "fallback": True,
        }

    low_confidence = not candidates or max(c["confidence"] for c in candidates) < CONFIDENCE_THRESHOLD
    notice = (LOW_CONFIDENCE_NOTICE if low_confidence else "") + UNIPASS_NOTICE
    return {"candidates": candidates, "notice": notice, "fallback": False}
