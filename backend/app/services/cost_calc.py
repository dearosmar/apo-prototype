from typing import Dict, Optional

from app.services.snapshots import load_snapshot

TARIFF_FILE = "tariff_rates.json"
VAT_RATE = 0.1


def load_tariff_table() -> dict:
    return load_snapshot(TARIFF_FILE)


def lookup_tariff(hs_code: str) -> Optional[Dict]:
    prefix = hs_code.replace(".", "")[:4]
    for item in load_tariff_table()["rates"]:
        if item["hs_code"] == prefix:
            return item
    return None


def default_tariff_rate() -> float:
    return load_tariff_table()["default_tariff_rate"]


def calc_landed_cost(
    goods_value_krw: float,
    freight_krw: float,
    tariff_rate: float,
    quantity: int,
    vat_rate: float = VAT_RATE,
) -> Dict:
    if quantity <= 0:
        raise ValueError("quantity는 1 이상이어야 합니다")
    if goods_value_krw < 0 or freight_krw < 0:
        raise ValueError("금액은 음수일 수 없습니다")
    if not 0 <= tariff_rate < 1 or not 0 <= vat_rate < 1:
        raise ValueError("세율은 0 이상 1 미만이어야 합니다")

    taxable_value = goods_value_krw + freight_krw
    duty = round(taxable_value * tariff_rate)
    vat = round((taxable_value + duty) * vat_rate)
    landed_cost = taxable_value + duty + vat
    return {
        "goods_value_krw": goods_value_krw,
        "freight_krw": freight_krw,
        "taxable_value_krw": taxable_value,
        "tariff_rate": tariff_rate,
        "duty_krw": duty,
        "vat_krw": vat,
        "landed_cost_krw": landed_cost,
        "unit_cost_krw": round(landed_cost / quantity, 2),
    }


def calc_margin_rate(unit_cost_krw: float, target_price_krw: float) -> float:
    if target_price_krw <= 0:
        raise ValueError("목표 판매가는 0보다 커야 합니다")
    return round((target_price_krw - unit_cost_krw) / target_price_krw, 4)
