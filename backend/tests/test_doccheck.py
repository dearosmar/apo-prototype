import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import doccheck as doccheck_router
from app.services import pi_checker

client = TestClient(app)


@pytest.fixture(autouse=True)
def stub_llm(monkeypatch):
    monkeypatch.setattr(
        doccheck_router, "generate_summary", lambda fields, checks, overall, key: "요약이에요."
    )


def test_parse_normal_sample_fields():
    text = pi_checker.load_sample("normal")["text"]
    fields = pi_checker.parse_fields(text)
    assert fields["deposit_pct"] == 30
    assert fields["incoterms"] == "FOB"
    assert fields["lead_time_days"] == 25
    assert fields["quantity"] == 500
    assert fields["total_amount"] == 6000.0
    assert fields["personal_account"] is False


def test_parse_risky_sample_fields():
    fields = pi_checker.parse_fields(pi_checker.load_sample("risky")["text"])
    assert fields["deposit_pct"] == 100
    assert fields["incoterms"] == "EXW"
    assert fields["lead_time_days"] is None
    assert fields["personal_account"] is True


def test_amount_mismatch_flagged_red():
    fields = {
        "payment_terms": "30% T/T",
        "deposit_pct": 30,
        "incoterms": "FOB",
        "lead_time_days": 25,
        "quantity": 500,
        "unit_price": 12.0,
        "total_amount": 9999.0,
        "beneficiary": "회사",
        "personal_account": False,
    }
    checks = pi_checker.run_checks(fields)
    amount = next(c for c in checks if c["item"] == "수량·금액")
    assert amount["status"] == "red"


def test_sample_endpoint_normal_is_green():
    body = client.post("/doc-check/sample/normal").json()
    assert body["overall"] == "green"
    assert all(c["status"] == "green" for c in body["checks"])
    assert body["extracted"]["deposit_pct"] == 30


def test_sample_endpoint_risky_is_red_with_reasons():
    body = client.post("/doc-check/sample/risky").json()
    assert body["overall"] == "red"
    reds = [c for c in body["checks"] if c["status"] == "red"]
    assert {"결제조건", "수취 계좌"} <= {c["item"] for c in reds}
    assert all(c["basis"] for c in body["checks"])


def test_upload_txt_file():
    text = pi_checker.load_sample("risky")["text"]
    res = client.post("/doc-check", files={"file": ("pi.txt", text.encode("utf-8"), "text/plain")})
    assert res.status_code == 200
    assert res.json()["overall"] == "red"


def test_upload_image_rejected_with_ocr_notice():
    res = client.post("/doc-check", files={"file": ("pi.jpg", b"\xff\xd8\xff", "image/jpeg")})
    assert res.status_code == 422
    assert "OCR" in res.json()["detail"]


def test_unknown_sample_404():
    assert client.post("/doc-check/sample/nope").status_code == 404
