import json
from typing import Dict, Optional

from app.config import SNAPSHOT_DIR

EXCHANGE_RATES_FILE = "exchange_rates_sample.json"


def load_snapshot(filename: str) -> dict:
    path = SNAPSHOT_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# TODO: KOREAEXIM_API_KEY 발급 후 실제 API 호출 추가 (반환 형식은 스냅숏과 동일 유지)
def load_exchange_rates() -> dict:
    return load_snapshot(EXCHANGE_RATES_FILE)


def get_rate(cur_unit: str) -> Optional[Dict]:
    for item in load_exchange_rates()["rates"]:
        if item["cur_unit"] == cur_unit:
            return item
    return None


def parse_rate(value: str) -> float:
    return float(value.replace(",", ""))
