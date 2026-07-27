from app.services import hs_estimator


def test_no_key_uses_keyword_fallback():
    result = hs_estimator.estimate_hs_candidates("봉제 인형", api_key="")
    assert result["fallback"] is True
    assert result["candidates"][0]["hs_code"] == "9503"
    assert "유니패스" in result["notice"]


def test_llm_error_falls_back(monkeypatch):
    def boom(description, api_key):
        raise RuntimeError("api down")

    monkeypatch.setattr(hs_estimator, "_call_claude", boom)
    result = hs_estimator.estimate_hs_candidates("봉제 인형", api_key="sk-test")
    assert result["fallback"] is True
    assert result["candidates"][0]["hs_code"] == "9503"
    assert result["notice"].startswith(hs_estimator.LOW_CONFIDENCE_NOTICE)


def test_low_confidence_adds_direct_check_notice(monkeypatch):
    monkeypatch.setattr(
        hs_estimator,
        "_call_claude",
        lambda d, k: [{"hs_code": "9503", "name": "완구", "confidence": 0.2, "reason": "모호"}],
    )
    result = hs_estimator.estimate_hs_candidates("동그란 물건", api_key="sk-test")
    assert result["fallback"] is False
    assert result["notice"].startswith(hs_estimator.LOW_CONFIDENCE_NOTICE)


def test_confident_result_keeps_unipass_notice(monkeypatch):
    monkeypatch.setattr(
        hs_estimator,
        "_call_claude",
        lambda d, k: [{"hs_code": "9503", "name": "완구", "confidence": 0.9, "reason": "봉제 인형은 완구류"}],
    )
    result = hs_estimator.estimate_hs_candidates("봉제 인형", api_key="sk-test")
    assert result["fallback"] is False
    assert not result["notice"].startswith(hs_estimator.LOW_CONFIDENCE_NOTICE)
    assert "유니패스" in result["notice"]


def test_unknown_description_returns_empty_fallback():
    result = hs_estimator.estimate_hs_candidates("정체불명의 무언가", api_key="")
    assert result["candidates"] == []
    assert "유니패스" in result["notice"]
