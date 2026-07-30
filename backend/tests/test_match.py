import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import match as match_router
from app.services import fx_risk

client = TestClient(app)

SCENARIO2 = {
    "currency": "CNY",
    "amount_foreign": 1800,
    "due_days": 30,
    "context": "인형 대금 선금 30%를 위안화로 송금 요청받음",
}


def test_diagnose_scenario2_levels():
    risk = fx_risk.diagnose("CNY", 1800, 30)
    assert risk["amount_krw"] == round(1800 * 191.67)
    assert risk["level"] in ("낮음", "중간", "높음")
    assert len(risk["factors"]) == 3


def test_diagnose_score_monotonic_in_amount():
    small = fx_risk.diagnose("CNY", 1000, 30)
    big = fx_risk.diagnose("CNY", 200000, 30)
    assert big["score"] >= small["score"]


def test_diagnose_invalid_inputs():
    with pytest.raises(ValueError):
        fx_risk.diagnose("CNY", 0, 30)
    with pytest.raises(ValueError):
        fx_risk.diagnose("CNY", 100, -1)


def test_match_products_respects_conditions():
    risk = fx_risk.diagnose("CNY", 200000, 60)
    products = fx_risk.match_products(risk, 60)
    ids = {p["id"] for p in products}
    assert "forward" in ids
    short = fx_risk.match_products(fx_risk.diagnose("CNY", 200000, 5), 5)
    assert "forward" not in {p["id"] for p in short}


def test_match_endpoint_with_stubbed_llm(monkeypatch):
    monkeypatch.setattr(
        match_router, "generate_reasons", lambda c, r, p, k: {x["id"]: f"{x['name']} 맞춤 사유" for x in p}
    )
    res = client.post("/match", json=SCENARIO2)
    assert res.status_code == 200
    body = res.json()
    assert body["risk"]["level"] in ("낮음", "중간", "높음")
    assert len(body["recommendations"]) >= 1
    assert all(r["reason"] and r["cautions"] for r in body["recommendations"])
    assert "KB국민은행" in body["notice"]


def test_match_endpoint_llm_error_falls_back_to_templates(monkeypatch):
    def boom(c, r, p, k):
        raise RuntimeError("down")

    monkeypatch.setattr(match_router, "generate_reasons", boom)
    body = client.post("/match", json=SCENARIO2).json()
    assert body["fallback"] is True
    assert all(r["reason"] for r in body["recommendations"])


def test_match_unsupported_currency():
    res = client.post("/match", json={**SCENARIO2, "currency": "XYZ"})
    assert res.status_code == 422
