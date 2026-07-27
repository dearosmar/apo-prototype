from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services import cost_calc, fx, hs_estimator

router = APIRouter()

SCENARIO_SHIFTS = [("환율 -5%", 0.95), ("기준 환율", 1.0), ("환율 +5%", 1.05)]


class CostRequest(BaseModel):
    description: str = Field(min_length=1, description="품목 설명 (예: 봉제 인형)")
    quantity: int = Field(gt=0)
    unit_price: float = Field(gt=0, description="단가 (통화 기준)")
    currency: str = Field(default="CNY", min_length=3)
    freight_krw: float = Field(default=0, ge=0, description="운송비 (원)")
    target_price_krw: Optional[float] = Field(default=None, gt=0, description="목표 판매가 (원)")


class HsCandidate(BaseModel):
    hs_code: str
    name: str
    confidence: float
    reason: str


class AppliedTariff(BaseModel):
    hs_code: str
    name: str
    tariff_rate: float
    basis: str


class Scenario(BaseModel):
    case: str
    krw_per_unit: float
    goods_value_krw: float
    taxable_value_krw: float
    duty_krw: float
    vat_krw: float
    landed_cost_krw: float
    unit_cost_krw: float
    margin_rate: Optional[float] = None


class CostResponse(BaseModel):
    hs: Dict
    applied_tariff: AppliedTariff
    fx: Dict
    scenarios: List[Scenario]
    fallback: bool = False


def _resolve_tariff(candidates: List[Dict]) -> AppliedTariff:
    for candidate in candidates:
        item = cost_calc.lookup_tariff(candidate["hs_code"])
        if item is not None:
            return AppliedTariff(
                hs_code=item["hs_code"],
                name=item["name"],
                tariff_rate=item["tariff_rate"],
                basis=item["basis"],
            )
    return AppliedTariff(
        hs_code="미확정",
        name="스냅숏에 없는 품목",
        tariff_rate=cost_calc.default_tariff_rate(),
        basis="데모 기본세율 가정 — 유니패스에서 실제 세율 확인 필요",
    )


@router.post("/cost", response_model=CostResponse)
def cost(req: CostRequest) -> CostResponse:
    hs = hs_estimator.estimate_hs_candidates(req.description, get_settings().anthropic_api_key)
    applied = _resolve_tariff(hs["candidates"])

    try:
        fx_info = fx.resolve_krw_rate(req.currency)
    except LookupError as e:
        raise HTTPException(status_code=422, detail=str(e))

    scenarios = []
    for case, shift in SCENARIO_SHIFTS:
        krw_per_unit = round(fx_info["krw_per_unit"] * shift, 2)
        goods_value_krw = round(req.quantity * req.unit_price * krw_per_unit, 2)
        breakdown = cost_calc.calc_landed_cost(
            goods_value_krw=goods_value_krw,
            freight_krw=req.freight_krw,
            tariff_rate=applied.tariff_rate,
            quantity=req.quantity,
        )
        margin = (
            cost_calc.calc_margin_rate(breakdown["unit_cost_krw"], req.target_price_krw)
            if req.target_price_krw
            else None
        )
        scenarios.append(
            Scenario(
                case=case,
                krw_per_unit=krw_per_unit,
                goods_value_krw=breakdown["goods_value_krw"],
                taxable_value_krw=breakdown["taxable_value_krw"],
                duty_krw=breakdown["duty_krw"],
                vat_krw=breakdown["vat_krw"],
                landed_cost_krw=breakdown["landed_cost_krw"],
                unit_cost_krw=breakdown["unit_cost_krw"],
                margin_rate=margin,
            )
        )

    return CostResponse(
        hs={"candidates": hs["candidates"], "notice": hs["notice"]},
        applied_tariff=applied,
        fx=fx_info,
        scenarios=scenarios,
        fallback=hs["fallback"],
    )
