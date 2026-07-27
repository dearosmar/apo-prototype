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


def test_restore_spacing_restores_spaceless_korean():
    mangled = "봉제인형은부드러운것으로채워진충진완구로분류된다안전확인대상어린이제품에완구가포함된다"
    restored = rag.restore_spacing(mangled)
    if rag.get_kiwi() is None:
        assert restored == mangled
    else:
        assert " " in restored
        assert restored.replace(" ", "") == mangled


def test_restore_spacing_keeps_normal_text():
    text = "이미 공백이 정상인 문장은 그대로 둔다."
    assert rag.restore_spacing(text) == text


@pytest.mark.skipif(rag.get_kiwi() is None, reason="kiwipiepy 미설치")
def test_bm25_tokens_include_bigrams():
    tokens = rag.bm25_tokens("봉제 인형 수입")
    assert "봉제" in tokens and "인형" in tokens
    assert "봉제_인형" in tokens


HTML_DOC = rag.DOCS_DIR / "kc" / "어린이제품_안전확인.html"


@pytest.mark.skipif(not HTML_DOC.exists(), reason="문서 미수집")
def test_extract_html_sections_removes_nav_and_keeps_tables():
    sections = rag.extract_html_sections(HTML_DOC)
    assert sections
    full = " ".join(s["text"] for s in sections)
    assert "오시는길" not in full  # 사이트 메뉴·탭 제거
    assert "완구" in full  # 안전확인대상 품목 표 유지
    assert any("안전확인" in s["title"] for s in sections)


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


@pytest.mark.skipif(not rag.index_exists(), reason="인덱스 미생성")
def test_decompose_query_extracts_rare_token_run():
    queries = rag.decompose_query("봉제 인형 수입 시 KC 인증 필요해?")
    assert queries[0] == "봉제 인형 수입 시 KC 인증 필요해?"
    assert "봉제 인형" in queries[1:]


@pytest.mark.skipif(not rag.index_exists(), reason="인덱스 미생성")
def test_search_multihop_question_covers_classification_and_regime():
    hits = rag.search("봉제 인형 수입 시 KC 인증 필요해?", top_k=4)
    assert any(
        h["doc"] == "완구_안전기준_부속서6" and "봉제인형" in h["text"].replace(" ", "")
        for h in hits
    )  # 봉제인형=완구 품목분류 근거
    assert any(h["doc"] == "어린이제품_안전확인" for h in hits)  # 완구=안전확인 대상 근거


@pytest.mark.skipif(not rag.index_exists(), reason="인덱스 미생성")
def test_search_diversity_caps_chunks_per_doc():
    from collections import Counter

    hits = rag.search("봉제 인형 수입 시 KC 인증 필요해?", top_k=4)
    counts = Counter(h["doc"] for h in hits)
    assert max(counts.values()) <= rag.MAX_PER_DOC
    assert len(counts) >= 2
