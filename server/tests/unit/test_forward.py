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


def test_forward_unadjusted_size_sum():
    inp = ForwardInput(
        items=[FpItem(us=4), FpItem(us=10), FpItem(us=4)],
        dev_factor=1.0, ops_factor=1.0,
        include_dev=True, include_ops=False, other_cost=0)
    r = calculate_forward(_ctx(), inp)
    assert r.scale_us == 18
    assert abs(r.scale_adjusted - 18 * 1.21) < 1e-6


def test_forward_three_bands():
    inp = ForwardInput(
        items=[FpItem(us=275)], dev_factor=1.0, ops_factor=1.0,
        include_dev=True, include_ops=False, other_cost=0)
    r = calculate_forward(_ctx(), inp)
    s = 275 * 1.21
    expected_p50_hours = s * 6.41
    assert abs(r.effort_dev_hours["P50"] - expected_p50_hours) < 0.01
