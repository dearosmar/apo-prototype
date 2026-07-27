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
    assert body["answer"].startswith("확인이 필요해요")
    assert body["sources"] == []


def test_ask_empty_question_rejected():
    res = client.post("/ask", json={"question": ""})
    assert res.status_code == 422


@pytest.mark.skipif(not rag.index_exists(), reason="인덱스 미생성")
def test_ask_smoke_with_stubbed_llm(monkeypatch):
    monkeypatch.setattr(
        ask_router, "generate_answer", lambda question, hits, api_key: "봉제 인형은 어린이제품 안전확인 대상입니다 [1]."
    )
    res = client.post("/ask", json={"question": "봉제 인형 수입 시 KC 인증 필요해?"})
    assert res.status_code == 200
    body = res.json()
    assert body["fallback"] is False
    assert len(body["sources"]) > 0
    assert {"doc", "page", "snippet"} <= set(body["sources"][0])
