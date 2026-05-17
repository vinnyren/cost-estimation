from hypothesis import given, strategies as st, settings, assume

from app.core.context import EvaluationContext, ProjectInputs
from app.core.forward import calculate_forward, ForwardInput, FpItem
from app.core.reverse import calculate_reverse, ReverseInput

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


@given(target=st.floats(min_value=10000, max_value=100_000_000),
       factor=st.floats(min_value=0.5, max_value=2.0),
       include_ops=st.booleans())
@settings(max_examples=100, deadline=None)
def test_reverse_then_forward_p50_recovers_target(target, factor, include_ops):
    """反推 P50 → 正向 P50 的总费用应接近 target（误差 ≤ 1%）。

    单一规模模型下，开发与运维共用同一个规模，dev+ops 也必须能精确复现目标。
    """
    rev_inp = ReverseInput(
        target_total=target, other_cost=0,
        include_ops=include_ops,
        dev_factor=factor, ops_factor=1.0,
    )
    rev = calculate_reverse(_ctx(), rev_inp)
    s_p50 = rev.scale_adjusted_bands["P50"]
    assume(s_p50 > 0.01)

    # 反推得到的 S 是已含 cf 的，需除回 cf 才能作为 items.us 输入
    us_p50 = s_p50 / rev.cf_used
    fwd_inp = ForwardInput(
        items=[FpItem(us=us_p50)],
        dev_factor=factor, ops_factor=1.0,
        include_dev=True, include_ops=include_ops, other_cost=0,
    )
    fwd = calculate_forward(_ctx(), fwd_inp)
    error = abs(fwd.cost_total_yuan["P50"] - target) / target
    assert error < 0.01, \
        f"roundtrip error {error:.3%}, fwd={fwd.cost_total_yuan['P50']:.2f}, target={target:.2f}"
