import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import ask as ask_router
from app.services import rag

client = TestClient(app)


def test_ask_without_index_falls_back(monkeypatch):
    monkeypatch.setattr(rag, "index_exists", lambda: False)
    res = client.post("/ask", json={"question": "인형 수입 절차 알려줘"})
    assert res.status_code == 200
    body = res.json()
    assert body["fallback"] is True
    assert "인덱스" in body["answer"]
    assert body["sources"] == []


def test_sanitize_citations_drops_out_of_range():
    answer, cited = ask_router.sanitize_citations("완구는 안전확인 대상이에요 [1][3]. 절차는 이래요 [9].", 4)
    assert cited == {1, 3}
    assert "[9]" not in answer
    assert "[1]" in answer and "[3]" in answer


def test_ask_empty_question_rejected():
    res = client.post("/ask", json={"question": ""})
    assert res.status_code == 422


@pytest.mark.skipif(not rag.index_exists(), reason="인덱스 미생성")
def test_ask_smoke_with_stubbed_llm(monkeypatch):
    monkeypatch.setattr(
        ask_router, "generate_answer", lambda question, hits, api_key: "봉제 인형은 어린이제품 안전확인 대상이에요 [1]."
    )
    res = client.post("/ask", json={"question": "봉제 인형 수입 시 KC 인증 필요해?"})
    assert res.status_code == 200
    body = res.json()
    assert body["fallback"] is False
    assert len(body["sources"]) > 0
    assert {"doc", "page", "snippet", "cited"} <= set(body["sources"][0])
    assert body["sources"][0]["cited"] is True


@pytest.mark.skipif(not rag.index_exists(), reason="인덱스 미생성")
def test_ask_every_citation_matches_a_source(monkeypatch):
    monkeypatch.setattr(
        ask_router,
        "generate_answer",
        lambda question, hits, api_key: "완구는 안전확인 대상이에요 [2]. 근거 없는 인용 [7][12].",
    )
    res = client.post("/ask", json={"question": "완구 KC", "top_k": 3})
    body = res.json()
    numbers = {int(n) for n in ask_router.CITATION_RE.findall(body["answer"])}
    assert numbers <= set(range(1, len(body["sources"]) + 1))
    cited_flags = [s["cited"] for s in body["sources"]]
    assert cited_flags == [False, True, False]
