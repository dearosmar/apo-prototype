import re
from typing import List, Optional, Set, Tuple

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services import rag

router = APIRouter()

SYSTEM_PROMPT = """너는 '바다 건너 사장님'의 무역 길잡이 에이전트다. 처음 수입을 시작하는 1인 소상공인의 질문에 한국어 해요체로 답한다.

답변 구조 (이 순서를 지킬 것):
① 근거로 확실하게 말할 수 있는 사실
② 불확실한 부분과 왜 불확실한지 (없으면 생략)
③ 사용자가 다음에 하면 되는 행동

규칙:
- 반드시 [근거] 안의 내용만 사용한다. 근거에 없는 내용은 추측하거나 일반 지식으로 보충하지 않는다.
- 확실한 사실이 하나라도 있으면 ①로 시작한다. "확인이 필요해요" 같은 유보 문구로 답변을 시작하지 않는다.
- 세율·기준금액 등 구체 수치는 근거에 그대로 있을 때만 인용한다.
- 사용한 근거 번호를 해당 문장 끝에 [1], [2] 형태로 표기한다. 근거 목록에 없는 번호는 쓰지 않는다.
- 전문용어는 풀어 쓰고, 7문장 이내로 간결하게 답한다."""

NO_INDEX_ANSWER = (
    "자료 인덱스가 아직 준비되지 않았어요. "
    "관리자가 `python scripts/build_index.py`를 실행한 뒤 다시 시도해 주세요."
)
NO_HITS_ANSWER = (
    "질문과 관련된 자료를 찾지 못했어요. "
    "관세청 고객센터(125)나 제품안전정보센터에 문의해 주세요."
)
NO_KEY_ANSWER = (
    "[폴백 모드] LLM 키가 없어 답변 생성 없이 관련 자료만 찾아 드려요. "
    "아래 출처 문서에서 해당 내용을 확인해 주세요."
)
ERROR_ANSWER = (
    "일시적인 오류로 답변을 만들지 못했어요. "
    "잠시 후 다시 시도하거나 아래 출처 문서를 직접 확인해 주세요."
)

CITATION_RE = re.compile(r"\[(\d+)\]")


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=4, ge=1, le=10)


class Source(BaseModel):
    doc: str
    page: Optional[int] = None
    snippet: str
    cited: bool = False


class AskResponse(BaseModel):
    answer: str
    sources: List[Source]
    fallback: bool = False


def sanitize_citations(answer: str, n_sources: int) -> Tuple[str, Set[int]]:
    cited: Set[int] = set()

    def keep_valid(match: "re.Match") -> str:
        n = int(match.group(1))
        if 1 <= n <= n_sources:
            cited.add(n)
            return match.group(0)
        return ""

    cleaned = CITATION_RE.sub(keep_valid, answer)
    return " ".join(cleaned.split()), cited


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
        max_tokens=2048,
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
        return AskResponse(answer=NO_HITS_ANSWER, sources=[], fallback=True)

    api_key = get_settings().anthropic_api_key
    if not api_key:
        return AskResponse(answer=NO_KEY_ANSWER, sources=sources, fallback=True)

    try:
        raw_answer = generate_answer(req.question, hits, api_key)
    except Exception:
        return AskResponse(answer=ERROR_ANSWER, sources=sources, fallback=True)

    answer, cited = sanitize_citations(raw_answer, len(sources))
    for n in cited:
        sources[n - 1].cited = True
    return AskResponse(answer=answer, sources=sources, fallback=False)
