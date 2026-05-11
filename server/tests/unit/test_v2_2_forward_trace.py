"""v2.2 — forward calc 返回 trace + composition 字段。"""
from app.core.forward import calculate_forward, ForwardInput, FpItem
from app.core.context import EvaluationContext, ProjectInputs


PARAMS = {
    "productivity": {
        "dev": {"电子政务": {"P10": 4.0, "P50": 6.41, "P90": 10.0}},
        "ops": {"全行业": {"P10": 0.50, "P50": 0.74, "P90": 1.20}},
    },
    "city_rate": {"北京": {"dev": 32200, "ops": 28800}},
    "cf": {"bidding": 1.21, "settled": 1.0},
    "hours_per_pm": 174,
}


def _ctx():
    return EvaluationContext.from_dict(
        PARAMS, ProjectInputs(industry="电子政务", city="北京", phase="bidding"))


def test_forward_returns_trace():
    res = calculate_forward(_ctx(), ForwardInput(
        items=[FpItem(us=275.0)],
        dev_factor=1.0, ops_factor=1.0,
        include_dev=True, include_ops=False, other_cost=25000,
    ))
    assert hasattr(res, "trace")
    t = res.trace
    assert t["us"] == 275.0
    assert "cf" in t
    assert "s_adjusted" in t
    assert "pdr_p50" in t
    assert "dev_factor" in t
    assert "eff_pm_p50" in t
    assert "eff_hours_p50" in t
    assert "f_city" in t
    assert "ops_plus_other" in t
    assert "total_p50" in t


def test_forward_returns_composition():
    res = calculate_forward(_ctx(), ForwardInput(
        items=[FpItem(us=275.0)],
        dev_factor=1.0, ops_factor=1.0,
        include_dev=True, include_ops=True, other_cost=25000,
    ))
    assert hasattr(res, "composition")
    c = res.composition
    assert "dev_labor" in c
    assert "ops_labor" in c
    assert "other" in c
    assert "indirect" in c
    # 4 段相加约等 total
    total = c["dev_labor"] + c["ops_labor"] + c["other"] + c["indirect"]
    assert abs(total - res.cost_total_yuan["P50"]) < 1.0
