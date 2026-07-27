from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services import rag

router = APIRouter()

SYSTEM_PROMPT = """너는 '바다 건너 사장님'의 무역 길잡이 에이전트다. 처음 수입을 시작하는 1인 소상공인의 질문에 답한다.

규칙:
- 반드시 [근거]에 있는 내용만으로 답한다. 근거에 없는 내용은 추측하거나 일반 지식으로 보충하지 않는다.
- 근거가 질문에 답하기에 부족하면 답변을 정확히 "확인이 필요해요."로 시작하고, 무엇을 어느 기관(관세청 125, 제품안전정보센터 등)에 확인해야 하는지 안내한다.
- 세율·기준금액 등 구체 수치는 근거에 그대로 있을 때만 인용한다.
- 사용한 근거를 문장 끝에 [1], [2] 형태로 표기한다.
- 전문용어는 풀어서, 5문장 이내로 간결하게 답한다."""

NO_INDEX_ANSWER = (
    "확인이 필요해요. 아직 자료 인덱스가 준비되지 않았습니다. "
    "관리자: `python scripts/build_index.py`로 인덱스를 생성해 주세요."
)
NO_KEY_ANSWER = (
    "[폴백 모드] LLM 키가 없어 답변 생성 없이 관련 자료만 찾아 드려요. "
    "아래 출처 문서에서 해당 내용을 확인해 주세요."
)
ERROR_ANSWER = (
    "확인이 필요해요. 일시적인 오류로 답변을 생성하지 못했습니다. "
    "잠시 후 다시 시도하거나 아래 출처 문서를 직접 확인해 주세요."
)


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=4, ge=1, le=10)


class Source(BaseModel):
    doc: str
    page: Optional[int] = None
    snippet: str


class AskResponse(BaseModel):
    answer: str
    sources: List[Source]
    fallback: bool = False


def generate_answer(question: str, hits: List[dict], api_key: str) -> str:
    import anthropic

    evidence = "\n\n".join(
        "[{}] 문서: {}{}\n{}".format(
            i,
            hit["doc"],
            f" (p.{hit['page']})" if hit["page"] else "",
            hit["text"],
        )
        for i, hit in enumerate(hits, start=1)
    )
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-opus-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"[근거]\n{evidence}\n\n[질문]\n{question}"}],
    )
    if response.stop_reason == "refusal":
        return ERROR_ANSWER
    return next((b.text for b in response.content if b.type == "text"), ERROR_ANSWER)


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    if not rag.index_exists():
        return AskResponse(answer=NO_INDEX_ANSWER, sources=[], fallback=True)

    hits = rag.search(req.question, top_k=req.top_k)
    sources = [Source(doc=h["doc"], page=h["page"], snippet=h["snippet"]) for h in hits]
    if not hits:
        return AskResponse(
            answer="확인이 필요해요. 관련 자료를 찾지 못했습니다. 관세청 고객센터(125)에 문의해 주세요.",
            sources=[],
            fallback=True,
        )

    api_key = get_settings().anthropic_api_key
    if not api_key:
        return AskResponse(answer=NO_KEY_ANSWER, sources=sources, fallback=True)

    try:
        answer = generate_answer(req.question, hits, api_key)
    except Exception:
        return AskResponse(answer=ERROR_ANSWER, sources=sources, fallback=True)
    return AskResponse(answer=answer, sources=sources, fallback=False)
