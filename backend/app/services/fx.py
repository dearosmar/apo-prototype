from typing import Dict

from app.services.snapshots import get_rate, load_exchange_rates, parse_rate

CURRENCY_ALIASES = {
    "CNY": "CNH",
    "RMB": "CNH",
    "JPY": "JPY(100)",
}
PER_100_UNITS = ("JPY(100)", "IDR(100)")


def resolve_krw_rate(currency: str) -> Dict:
    currency = currency.upper()
    cur_unit = CURRENCY_ALIASES.get(currency, currency)
    item = get_rate(cur_unit)
    if item is None:
        raise LookupError(f"지원하지 않는 통화입니다: {currency}")
    rate = parse_rate(item["deal_bas_r"])
    if cur_unit in PER_100_UNITS:
        rate = rate / 100
    snapshot = load_exchange_rates()
    return {
        "currency": currency,
        "cur_unit": cur_unit,
        "krw_per_unit": rate,
        "source": snapshot["source"],
        "snapshot_date": snapshot["snapshot_date"],
    }
