from typing import Dict, List

from app.services import fx
from app.services.snapshots import load_snapshot

PRODUCTS_FILE = "kb_fx_products.json"

VOLATILITY = {
    "USD": ("중간", 1),
    "CNH": ("중상", 2),
    "EUR": ("중상", 2),
    "JPY(100)": ("높음", 3),
}

AMOUNT_TIERS = [
    (30_000_000, 3, "3천만 원 이상 — 환율 1%만 움직여도 30만 원 이상 손익이 갈려요"),
    (5_000_000, 2, "5백만 원 이상 — 환율 변동이 마진에 직접 영향을 주는 규모예요"),
    (0, 1, "5백만 원 미만 — 환율 영향이 제한적인 규모예요"),
]

DUE_TIERS = [
    (60, 3, "결제까지 60일 이상 — 변동에 노출되는 기간이 길어요"),
    (30, 2, "결제까지 30일 이상 — 환율이 움직일 시간이 충분해요"),
    (0, 1, "결제까지 30일 미만 — 노출 기간이 짧아요"),
]

LEVELS = {(2, 4): "낮음", (5, 6): "중간", (7, 9): "높음"}


def load_products() -> dict:
    return load_snapshot(PRODUCTS_FILE)


def diagnose(currency: str, amount_foreign: float, due_days: int) -> Dict:
    if amount_foreign <= 0:
        raise ValueError("금액은 0보다 커야 합니다")
    if due_days < 0:
        raise ValueError("결제까지 남은 일수는 음수일 수 없습니다")

    fx_info = fx.resolve_krw_rate(currency)
    amount_krw = round(amount_foreign * fx_info["krw_per_unit"])

    factors: List[Dict] = []
    vol_label, vol_score = VOLATILITY.get(fx_info["cur_unit"], ("중간", 2))
    factors.append({"name": "통화 변동성", "detail": f"{fx_info['cur_unit']} 변동성 {vol_label}", "score": vol_score})
    for threshold, score, detail in AMOUNT_TIERS:
        if amount_krw >= threshold:
            factors.append({"name": "결제 금액", "detail": detail, "score": score})
            break
    for threshold, score, detail in DUE_TIERS:
        if due_days >= threshold:
            factors.append({"name": "노출 기간", "detail": detail, "score": score})
            break

    total = sum(f["score"] for f in factors)
    level = next(label for (lo, hi), label in LEVELS.items() if lo <= total <= hi)
    return {
        "level": level,
        "score": total,
        "factors": factors,
        "amount_krw": amount_krw,
        "fx": fx_info,
    }


def match_products(risk: Dict, due_days: int) -> List[Dict]:
    matched = []
    for product in load_products()["products"]:
        if risk["level"] not in product["risk_levels"]:
            continue
        if risk["amount_krw"] < product["min_amount_krw"]:
            continue
        if due_days < product["min_due_days"]:
            continue
        matched.append(product)
    return matched
