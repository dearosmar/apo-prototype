import json
import re
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from app.config import BACKEND_DIR

DOCS_DIR = BACKEND_DIR / "data" / "docs"
VECTORSTORE_DIR = BACKEND_DIR / "data" / "vectorstore"
INDEX_FILE = VECTORSTORE_DIR / "index.faiss"
CHUNKS_FILE = VECTORSTORE_DIR / "chunks.json"

EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
CHUNK_SIZE = 700
CHUNK_OVERLAP = 150
SNIPPET_LEN = 150
MIN_SPACE_RATIO = 0.04
CANDIDATE_POOL = 40
MAX_PER_DOC = 2
MAX_SUBQUERIES = 2

TOKEN_RE = re.compile(r"[가-힣]+|[a-zA-Z]+|[0-9]+")
CONTENT_TAGS = ("N", "V", "M", "SL", "SN", "XR")


@lru_cache
def get_kiwi():
    try:
        from kiwipiepy import Kiwi
    except ImportError:
        return None
    return Kiwi()


def restore_spacing(text: str) -> str:
    if not text or text.count(" ") / len(text) >= MIN_SPACE_RATIO:
        return text
    kiwi = get_kiwi()
    if kiwi is None:
        return text
    return kiwi.space(text)


def tokenize(text: str) -> List[str]:
    kiwi = get_kiwi()
    if kiwi is None:
        return TOKEN_RE.findall(text.lower())
    return [t.form.lower() for t in kiwi.tokenize(text) if t.tag.startswith(CONTENT_TAGS)]


def bm25_tokens(text: str) -> List[str]:
    tokens = tokenize(text)
    return tokens + [a + "_" + b for a, b in zip(tokens, tokens[1:])]


def make_snippet(text: str, limit: int = SNIPPET_LEN) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    words: List[str] = []
    length = 0
    for word in text.split(" "):
        extra = len(word) + (1 if words else 0)
        if length + extra > limit:
            break
        words.append(word)
        length += extra
    if not words:
        return text[:limit]
    snippet = " ".join(words)
    boundary = snippet.rfind(". ")
    if boundary > 0:
        snippet = snippet[: boundary + 1]
    return snippet


def extract_pdf_pages(path) -> List[Dict]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = " ".join((page.extract_text() or "").split())
        if text:
            pages.append({"page": i, "text": restore_spacing(text)})
    return pages


MAX_SECTION_TITLE = 60


def extract_html_sections(path) -> List[Dict]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    for tag in soup(["script", "style", "header", "footer", "nav"]):
        tag.decompose()
    for tag in soup(["p", "ul", "ol"]):  # 링크 위주 요소(탭 바·메뉴)는 본문이 아니다
        text = " ".join(tag.get_text(" ").split())
        links = tag("a")
        if not text or len(links) < 2:
            continue
        link_text = " ".join(" ".join(a.get_text(" ").split()) for a in links)
        if len(link_text) / len(text) > 0.7:
            tag.decompose()
    main = None
    for selector in ("#contents", "#content", ".contents", ".content", "main"):
        main = soup.select_one(selector)
        if main is not None:
            break
    main = main or soup.body or soup

    from bs4 import Comment, NavigableString, Tag

    def is_heading(tag) -> bool:
        if tag.name in ("h1", "h2", "h3", "h4"):
            return True
        classes = " ".join(tag.get("class") or [])
        return "tit" in classes

    sections: List[Dict] = []
    title = ""
    buf: List[str] = []

    def flush() -> None:
        text = " ".join(" ".join(buf).split())
        if text:
            sections.append({"title": title, "text": text})

    for node in main.descendants:
        if isinstance(node, Tag) and is_heading(node):
            heading = " ".join(node.get_text(" ").split())
            if heading and len(heading) <= MAX_SECTION_TITLE:
                flush()
                title = heading
                buf = []
        elif isinstance(node, NavigableString):
            if isinstance(node, Comment):
                continue
            if any(isinstance(p, Tag) and is_heading(p) for p in node.parents):
                continue  # 제목 텍스트는 title로만 반영
            buf.append(str(node))
    flush()
    return sections


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    text = " ".join(text.split())
    if len(text) <= size:
        return [text] if text else []
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        if end < len(text):
            boundary = text.rfind(" ", start + size - 100, end)
            if boundary > start:
                end = boundary
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap
    return [c for c in chunks if c]


def build_corpus() -> List[Dict]:
    chunks = []
    for path in sorted(DOCS_DIR.rglob("*")):
        if path.suffix.lower() == ".pdf":
            for page in extract_pdf_pages(path):
                for piece in chunk_text(page["text"]):
                    chunks.append({"doc": path.stem, "page": page["page"], "text": piece})
        elif path.suffix.lower() in (".html", ".htm"):
            for section in extract_html_sections(path):
                for piece in chunk_text(section["text"]):
                    if section["title"] and section["title"] not in piece:
                        piece = section["title"] + " | " + piece
                    chunks.append(
                        {
                            "doc": path.stem,
                            "page": None,
                            "section": section["title"] or None,
                            "text": piece,
                        }
                    )
    return chunks


@lru_cache
def get_embedder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL)


def embed_texts(texts: List[str], is_query: bool = False):
    prefix = "query: " if is_query else "passage: "
    return get_embedder().encode(
        [prefix + t for t in texts],
        normalize_embeddings=True,
        show_progress_bar=False,
    )


def build_index() -> int:
    import faiss
    import numpy as np

    corpus = build_corpus()
    if not corpus:
        raise RuntimeError(f"청킹할 문서가 없습니다: {DOCS_DIR}")
    vectors = embed_texts([c["text"] for c in corpus]).astype(np.float32)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_FILE))
    CHUNKS_FILE.write_text(json.dumps(corpus, ensure_ascii=False), encoding="utf-8")
    return len(corpus)


def index_exists() -> bool:
    return INDEX_FILE.exists() and CHUNKS_FILE.exists()


@lru_cache
def _load_index():
    import faiss

    index = faiss.read_index(str(INDEX_FILE))
    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    return index, chunks


@lru_cache
def _load_bm25():
    from rank_bm25 import BM25Okapi

    _, chunks = _load_index()
    return BM25Okapi([bm25_tokens(c["text"]) for c in chunks])


def decompose_query(query: str) -> List[str]:
    tokens = tokenize(query)
    if len(tokens) < 3:
        return [query]
    idf = _load_bm25().idf
    mean_idf = sum(idf.get(t, 0.0) for t in tokens) / len(tokens)
    runs: List[List[str]] = []
    run: List[str] = []
    for token in tokens:
        if idf.get(token, 0.0) > mean_idf:
            run.append(token)
            continue
        if len(run) >= 2:
            runs.append(run)
        run = []
    if len(run) >= 2 and len(run) < len(tokens):
        runs.append(run)
    runs.sort(key=lambda r: sum(idf.get(t, 0.0) for t in r), reverse=True)
    return [query] + [" ".join(r) for r in runs[:MAX_SUBQUERIES]]


def _retrieve(query: str) -> Tuple["object", List[List[int]]]:
    import numpy as np

    index, chunks = _load_index()
    bm25 = _load_bm25()
    queries = decompose_query(query)
    n = len(chunks)
    total = np.zeros(n, dtype=np.float64)

    def normalized(scores):
        lo, hi = float(scores.min()), float(scores.max())
        if hi <= lo:
            return np.zeros_like(scores)
        return (scores - lo) / (hi - lo)

    vectors = embed_texts(queries, is_query=True).astype(np.float32)
    sims, ids = index.search(vectors, n)
    vec_lists: List[List[int]] = []
    bm25_lists: List[List[int]] = []
    for qi in range(len(queries)):
        dense = np.zeros(n, dtype=np.float64)
        dense[ids[qi]] = sims[qi]
        total += normalized(dense)
        vec_lists.append([int(i) for i in ids[qi][:CANDIDATE_POOL]])

        scores = np.asarray(bm25.get_scores(bm25_tokens(queries[qi])), dtype=np.float64)
        total += normalized(scores)
        order = np.argsort(scores)[::-1][:CANDIDATE_POOL]
        bm25_lists.append([int(i) for i in order if scores[i] > 0])

    # 좌석 우선순위: 희귀 토큰 부분쿼리(BM25→벡터)부터, 마지막에 원 쿼리 벡터.
    # 부분쿼리가 있으면 원 쿼리 BM25 좌석은 생략 — 희귀 토큰이 부분쿼리로 빠진 뒤라
    # 흔한 용어 빈도가 높은 문서가 좌석을 차지하는 노이즈가 된다(융합 점수에는 반영됨).
    seat_lists = []
    for qi in range(1, len(queries)):
        seat_lists += [bm25_lists[qi], vec_lists[qi]]
    seat_lists.append(vec_lists[0])
    if len(queries) == 1:
        seat_lists.append(bm25_lists[0])
    return total, seat_lists


def search(query: str, top_k: int = 4) -> List[Dict]:
    import numpy as np

    _, chunks = _load_index()
    total, seat_lists = _retrieve(query)
    fused_order = [int(i) for i in np.argsort(total)[::-1][:CANDIDATE_POOL]]

    picked: List[int] = []
    per_doc: Dict[str, int] = {}

    def try_pick(idx: int) -> bool:
        doc = chunks[idx]["doc"]
        if idx in picked or per_doc.get(doc, 0) >= MAX_PER_DOC:
            return False
        picked.append(idx)
        per_doc[doc] = per_doc.get(doc, 0) + 1
        return True

    for seat in seat_lists:  # 검색 관점(부분쿼리×검색기)별 최상위 근거 1개씩 보장
        if len(picked) >= top_k:
            break
        for idx in seat:
            if try_pick(idx):
                break
    # 표·절차가 청크 경계로 쪼개진 경우 보완: 뽑힌 청크의 같은 문서 인접 청크를 우선 보충
    neighbors = sorted(
        {
            nb
            for idx in picked
            for nb in (idx - 1, idx + 1)
            if 0 <= nb < len(chunks) and chunks[nb]["doc"] == chunks[idx]["doc"]
        },
        key=lambda nb: total[nb],
        reverse=True,
    )
    for idx in neighbors:
        if len(picked) >= top_k:
            break
        try_pick(idx)
    for idx in fused_order:
        if len(picked) >= top_k:
            break
        try_pick(idx)
    for idx in fused_order:  # 문서 다양성 제한 탓에 못 채웠으면 제한 없이 보충
        if len(picked) >= top_k:
            break
        if idx not in picked:
            picked.append(idx)

    results = []
    for idx in picked:
        chunk = chunks[idx]
        results.append(
            {
                "doc": chunk["doc"],
                "page": chunk["page"],
                "section": chunk.get("section"),
                "snippet": make_snippet(chunk["text"]),
                "text": chunk["text"],
                "score": float(total[idx]),
            }
        )
    return results
