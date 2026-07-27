from app.services.snapshots import get_rate, load_exchange_rates, parse_rate


def test_load_exchange_rates():
    data = load_exchange_rates()
    assert len(data["rates"]) >= 4


def test_get_rate_found():
    usd = get_rate("USD")
    assert usd is not None
    assert usd["cur_nm"] == "미국 달러"


def test_get_rate_not_found():
    assert get_rate("XXX") is None


def test_parse_rate():
    assert parse_rate("1,385.30") == 1385.3
