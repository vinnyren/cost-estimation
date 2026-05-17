import pytest
from app.core.reverse import calculate_reverse, ReverseInput
from app.core.forward import calculate_forward, ForwardInput, FpItem
from app.core.context import EvaluationContext, ProjectInputs


PARAMS = {
    "productivity": {
        "dev": {"电子政务": {"P10": 2.04, "P50": 6.41, "P90": 15.36}},
        "ops": {"全行业": {"P10": 0.21, "P50": 0.74, "P90": 2.07}},
    },
    "city_rate": {"北京": {"dev": 32198, "ops": 26335, "class": "A"}},
    "cf": {"bidding": 1.21},
    "hours_per_pm": 174,
}


def _ctx():
    return EvaluationContext.from_dict(
        PARAMS, ProjectInputs(industry="电子政务", city="北京", phase="bidding"))


def test_reverse_dev_only():
    inp = ReverseInput(target_total=500000, other_cost=0, include_ops=False)
    r = calculate_reverse(_ctx(), inp)
    # dev-only：s × pdr_dev × dev_factor / pm × rate_dev = budget
    unit_p50 = 6.41 / 174 * 32198
    expected_s = 500000 / unit_p50
    assert abs(r.scale_adjusted_bands["P50"] - expected_s) < 0.5


def test_reverse_budget_negative_raises():
    inp = ReverseInput(target_total=10000, other_cost=20000, include_ops=False)
    with pytest.raises(ValueError, match="BUDGET_NEGATIVE"):
        calculate_reverse(_ctx(), inp)


def test_reverse_bands_ordered():
    # P10 乐观（PDR 最低 → 同预算买到的规模最大）> P50 > P90
    r = calculate_reverse(_ctx(), ReverseInput(target_total=500000, include_ops=True))
    assert r.scale_adjusted_bands["P10"] > r.scale_adjusted_bands["P50"]
    assert r.scale_adjusted_bands["P50"] > r.scale_adjusted_bands["P90"]


def test_reverse_single_scale_roundtrips_to_target():
    # 单一规模模型核心保证：反算出的 US 经正向计算精确复现目标总额（dev+ops 同规模）
    target = 600000
    r = calculate_reverse(_ctx(), ReverseInput(target_total=target, include_ops=True))
    for b in ("P10", "P50", "P90"):
        us = r.scale_unadjusted_bands[b]
        fwd = calculate_forward(_ctx(), ForwardInput(
            items=[FpItem(us=us)], include_dev=True, include_ops=True))
        assert abs(fwd.cost_total_yuan[b] - target) < 1.0


def test_reverse_roundtrips_with_other_cost():
    target, other = 600000, 80000
    r = calculate_reverse(_ctx(), ReverseInput(
        target_total=target, other_cost=other, include_ops=True))
    us = r.scale_unadjusted_bands["P50"]
    fwd = calculate_forward(_ctx(), ForwardInput(
        items=[FpItem(us=us)], include_dev=True, include_ops=True,
        other_cost=other))
    assert abs(fwd.cost_total_yuan["P50"] - target) < 1.0


def test_reverse_budget_split_sums_to_fp_budget():
    # budget_for_dev + budget_for_ops == target - other（推荐档 P50 派生）
    r = calculate_reverse(_ctx(), ReverseInput(
        target_total=600000, other_cost=50000, include_ops=True))
    assert abs(r.budget_for_dev + r.budget_for_ops - 550000) < 1.0


def test_reverse_dev_only_ops_budget_zero():
    r = calculate_reverse(_ctx(), ReverseInput(target_total=500000, include_ops=False))
    assert r.budget_for_ops == 0.0
    assert abs(r.budget_for_dev - 500000) < 1.0
