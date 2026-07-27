import json
import re
from functools import lru_cache
from typing import Dict, List, Optional

from app.config import BACKEND_DIR

DOCS_DIR = BACKEND_DIR / "data" / "docs"
VECTORSTORE_DIR = BACKEND_DIR / "data" / "vectorstore"
INDEX_FILE = VECTORSTORE_DIR / "index.faiss"
CHUNKS_FILE = VECTORSTORE_DIR / "chunks.json"

EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
CHUNK_SIZE = 700
CHUNK_OVERLAP = 150
SNIPPET_LEN = 160


def extract_pdf_pages(path) -> List[Dict]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = " ".join((page.extract_text() or "").split())
        if text:
            pages.append({"page": i, "text": text})
    return pages


def extract_html_text(path) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    for tag in soup(["script", "style", "header", "footer", "nav"]):
        tag.decompose()
    main = None
    for selector in ("#contents", "#content", ".content", "main"):
        main = soup.select_one(selector)
        if main is not None:
            break
    text = (main or soup.body or soup).get_text(" ")
    return " ".join(text.split())


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
            for piece in chunk_text(extract_html_text(path)):
                chunks.append({"doc": path.stem, "page": None, "text": piece})
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


def search(query: str, top_k: int = 4) -> List[Dict]:
    import numpy as np

    index, chunks = _load_index()
    vector = embed_texts([query], is_query=True).astype(np.float32)
    scores, ids = index.search(vector, top_k)
    results = []
    for score, idx in zip(scores[0], ids[0]):
        if idx < 0:
            continue
        chunk = chunks[idx]
        results.append(
            {
                "doc": chunk["doc"],
                "page": chunk["page"],
                "snippet": chunk["text"][:SNIPPET_LEN],
                "text": chunk["text"],
                "score": float(score),
            }
        )
    return results
