import pytest
from app.core.reverse import calculate_reverse, ReverseInput
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


def test_reverse_dev_only_alpha_one():
    inp = ReverseInput(target_total=500000, other_cost=0,
                       include_ops=False, alpha_dev=1.0,
                       dev_factor=1.0, ops_factor=1.0)
    r = calculate_reverse(_ctx(), inp)
    expected_p50_s = (500000 / 32198 * 174) / 6.41
    assert abs(r.scale_adjusted_bands["P50"] - expected_p50_s) < 0.5


def test_reverse_budget_negative_raises():
    inp = ReverseInput(target_total=10000, other_cost=20000,
                       include_ops=False, alpha_dev=1.0,
                       dev_factor=1.0, ops_factor=1.0)
    with pytest.raises(ValueError, match="BUDGET_NEGATIVE"):
        calculate_reverse(_ctx(), inp)


def test_reverse_with_ops_split():
    inp = ReverseInput(target_total=600000, other_cost=0,
                       include_ops=True, alpha_dev=0.917,
                       dev_factor=1.0, ops_factor=1.0)
    r = calculate_reverse(_ctx(), inp)
    assert r.scale_adjusted_bands["P50"] > 0
    assert r.scale_adjusted_ops_bands["P50"] > 0
