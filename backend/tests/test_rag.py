import pytest

from app.services import rag


def test_chunk_text_short():
    assert rag.chunk_text("짧은 텍스트") == ["짧은 텍스트"]
    assert rag.chunk_text("   ") == []


def test_chunk_text_split_and_overlap():
    text = " ".join(f"단어{i}" for i in range(500))
    chunks = rag.chunk_text(text, size=200, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)
    assert chunks[1][:30] in chunks[0][-80:] + chunks[1][:30]


def test_make_snippet_limit_and_sentence_boundary():
    text = "첫 문장은 여기서 끝나요. " + "다음 문장은 아주 길게 이어집니다 " * 20
    snippet = rag.make_snippet(text, limit=150)
    assert len(snippet) <= 150
    assert snippet.endswith(".")


def test_make_snippet_never_cuts_url():
    text = ("안내 문구가 길게 이어집니다 " * 5) + "자세한 내용은 http://www.safetykorea.kr/policy/targetsSafetyCheck3 에서 확인하세요"
    snippet = rag.make_snippet(text, limit=150)
    source_words = set(text.split(" "))
    assert all(word in source_words for word in snippet.split(" "))


@pytest.mark.skipif(not rag.DOCS_DIR.exists(), reason="문서 미수집")
def test_build_corpus_metadata():
    corpus = rag.build_corpus()
    assert len(corpus) > 0
    assert {"doc", "page", "text"} <= set(corpus[0])
    docs = {c["doc"] for c in corpus}
    assert "어린이제품_안전인증" in docs


@pytest.mark.skipif(not rag.index_exists(), reason="인덱스 미생성")
def test_search_returns_scored_sources():
    results = rag.search("어린이 장난감 KC 안전인증", top_k=3)
    assert len(results) == 3
    assert all({"doc", "page", "snippet", "score"} <= set(r) for r in results)
    assert any("어린이" in r["doc"] for r in results)
