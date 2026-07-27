import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import fx, hs_estimator

client = TestClient(app)

STUB_HS = {
    "candidates": [{"hs_code": "9503", "name": "완구", "confidence": 0.9, "reason": "봉제 인형은 완구류"}],
    "notice": hs_estimator.UNIPASS_NOTICE,
    "fallback": False,
}

SCENARIO1 = {
    "description": "봉제 인형",
    "quantity": 500,
    "unit_price": 12,
    "currency": "CNY",
    "freight_krw": 300000,
    "target_price_krw": 15000,
}


def test_cost_scenario1_matches_hand_calculation(monkeypatch):
    monkeypatch.setattr(hs_estimator, "estimate_hs_candidates", lambda d, k: STUB_HS)
    res = client.post("/cost", json=SCENARIO1)
    assert res.status_code == 200
    body = res.json()
    assert body["applied_tariff"]["hs_code"] == "9503"
    assert body["applied_tariff"]["tariff_rate"] == 0.08
    assert len(body["scenarios"]) == 3

    base = body["scenarios"][1]
    assert base["case"] == "기준 환율"
    assert base["krw_per_unit"] == 191.67
    assert base["taxable_value_krw"] == 1_450_020
    assert base["duty_krw"] == 116_002
    assert base["vat_krw"] == 156_602
    assert base["landed_cost_krw"] == 1_722_624
    assert base["unit_cost_krw"] == 3_445.25
    assert base["margin_rate"] == 0.7703


def test_cost_margin_decreases_as_rate_rises(monkeypatch):
    monkeypatch.setattr(hs_estimator, "estimate_hs_candidates", lambda d, k: STUB_HS)
    body = client.post("/cost", json=SCENARIO1).json()
    margins = [s["margin_rate"] for s in body["scenarios"]]
    assert margins[0] > margins[1] > margins[2]
    assert [s["case"] for s in body["scenarios"]] == ["환율 -5%", "기준 환율", "환율 +5%"]


def test_cost_without_target_price_omits_margin(monkeypatch):
    monkeypatch.setattr(hs_estimator, "estimate_hs_candidates", lambda d, k: STUB_HS)
    payload = {k: v for k, v in SCENARIO1.items() if k != "target_price_krw"}
    body = client.post("/cost", json=payload).json()
    assert all(s["margin_rate"] is None for s in body["scenarios"])


def test_cost_unknown_hs_uses_default_rate_with_warning(monkeypatch):
    monkeypatch.setattr(
        hs_estimator,
        "estimate_hs_candidates",
        lambda d, k: {"candidates": [], "notice": hs_estimator.UNIPASS_NOTICE, "fallback": True},
    )
    body = client.post("/cost", json=SCENARIO1).json()
    assert body["applied_tariff"]["hs_code"] == "미확정"
    assert body["applied_tariff"]["tariff_rate"] == 0.08
    assert "유니패스" in body["applied_tariff"]["basis"]
    assert body["fallback"] is True


def test_cost_unsupported_currency_rejected(monkeypatch):
    monkeypatch.setattr(hs_estimator, "estimate_hs_candidates", lambda d, k: STUB_HS)
    res = client.post("/cost", json={**SCENARIO1, "currency": "XYZ"})
    assert res.status_code == 422


def test_fx_jpy_per_100_scaled():
    info = fx.resolve_krw_rate("JPY")
    assert info["cur_unit"] == "JPY(100)"
    assert info["krw_per_unit"] == pytest.approx(9.3699)


def test_cost_invalid_quantity_rejected():
    res = client.post("/cost", json={**SCENARIO1, "quantity": 0})
    assert res.status_code == 422
