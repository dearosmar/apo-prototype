import pytest

from app.services.cost_calc import calc_landed_cost, calc_margin_rate, lookup_tariff


def test_scenario1_doll_500_hand_calculated():
    """시나리오① 손검산 대조: 인형 500개 × 12위안, CNH 191.67원, 운송비 30만원, 관세 8%.

    물품가 = 500 × 12 × 191.67 = 1,150,020원
    과세가격(CIF) = 1,150,020 + 300,000 = 1,450,020원
    관세 = 1,450,020 × 0.08 = 116,001.6 → 116,002원
    부가세 = (1,450,020 + 116,002) × 0.1 = 156,602.2 → 156,602원
    랜디드 코스트 = 1,450,020 + 116,002 + 156,602 = 1,722,624원
    단위당 원가 = 1,722,624 / 500 = 3,445.25원
    """
    result = calc_landed_cost(
        goods_value_krw=500 * 12 * 191.67,
        freight_krw=300_000,
        tariff_rate=0.08,
        quantity=500,
    )
    assert result["taxable_value_krw"] == 1_450_020
    assert result["duty_krw"] == 116_002
    assert result["vat_krw"] == 156_602
    assert result["landed_cost_krw"] == 1_722_624
    assert result["unit_cost_krw"] == 3_445.25
    assert calc_margin_rate(result["unit_cost_krw"], 15_000) == 0.7703


def test_tshirt_hand_calculated():
    """티셔츠 100장 × 10달러, USD 1,385.30원, 운송비 10만원, 관세 13%.

    물품가 = 1,000 × 1,385.30 = 1,385,300원 / 과세가격 = 1,485,300원
    관세 = 193,089원 / 부가세 = 167,838.9 → 167,839원 / 랜디드 = 1,846,228원
    """
    result = calc_landed_cost(
        goods_value_krw=1_000 * 1_385.30,
        freight_krw=100_000,
        tariff_rate=0.13,
        quantity=100,
    )
    assert result["duty_krw"] == 193_089
    assert result["vat_krw"] == 167_839
    assert result["landed_cost_krw"] == 1_846_228
    assert result["unit_cost_krw"] == 18_462.28


def test_zero_freight_zero_tariff_hand_calculated():
    """무관세·운송비 0원: 물품가 200,000원 → 관세 0, 부가세 20,000원, 랜디드 220,000원."""
    result = calc_landed_cost(goods_value_krw=200_000, freight_krw=0, tariff_rate=0.0, quantity=10)
    assert result["duty_krw"] == 0
    assert result["vat_krw"] == 20_000
    assert result["landed_cost_krw"] == 220_000
    assert result["unit_cost_krw"] == 22_000.0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"goods_value_krw": 1000, "freight_krw": 0, "tariff_rate": 0.08, "quantity": 0},
        {"goods_value_krw": 1000, "freight_krw": 0, "tariff_rate": 0.08, "quantity": -5},
        {"goods_value_krw": -1, "freight_krw": 0, "tariff_rate": 0.08, "quantity": 1},
        {"goods_value_krw": 1000, "freight_krw": -1, "tariff_rate": 0.08, "quantity": 1},
        {"goods_value_krw": 1000, "freight_krw": 0, "tariff_rate": 1.2, "quantity": 1},
    ],
)
def test_invalid_inputs_rejected(kwargs):
    with pytest.raises(ValueError):
        calc_landed_cost(**kwargs)


def test_margin_rate_invalid_target():
    with pytest.raises(ValueError):
        calc_margin_rate(1000, 0)


def test_lookup_tariff_by_prefix():
    toy = lookup_tariff("9503.00-1000")
    assert toy is not None
    assert toy["tariff_rate"] == 0.08
    assert "출처" not in toy or toy["basis"]
    assert lookup_tariff("0000") is None
