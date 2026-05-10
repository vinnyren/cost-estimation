import pytest
from app.core.context import EvaluationContext, ProjectInputs


PARAMS = {
    "productivity": {"dev": {"电子政务": {"P10": 2.04, "P50": 6.41, "P90": 15.36}}},
    "city_rate": {"北京": {"dev": 32198, "ops": 26335, "class": "A"}},
    "cf": {"bidding": 1.21},
    "hours_per_pm": 174,
}


def test_context_resolves_pdr_three_bands():
    ctx = EvaluationContext.from_dict(
        PARAMS, ProjectInputs(industry="电子政务", city="北京", phase="bidding"))
    assert ctx.pdr_dev("P50") == 6.41
    assert ctx.city_rate_dev() == 32198
    assert ctx.cf() == 1.21
    assert ctx.hours_per_pm == 174


def test_context_unknown_industry_raises():
    with pytest.raises(KeyError):
        EvaluationContext.from_dict(
            {"productivity": {"dev": {}}, "city_rate": {"北京": {"dev": 1, "ops": 1}},
             "cf": {"bidding": 1.0}, "hours_per_pm": 174},
            ProjectInputs(industry="未知", city="北京", phase="bidding")
        ).pdr_dev("P50")
