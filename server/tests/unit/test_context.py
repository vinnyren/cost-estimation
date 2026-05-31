import json
import pytest
from pathlib import Path
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


# ── cfp_to_fp 新增属性测试 ────────────────────────────────────────────

def _make_ctx(extra: dict | None = None) -> EvaluationContext:
    base = json.loads(
        (Path(__file__).parents[2] / "app" / "data" / "ssm_bk_202509.json").read_text(encoding="utf-8")
    )
    if extra:
        base.update(extra)
    return EvaluationContext.from_dict(
        base, ProjectInputs(industry="全行业", city="北京", phase="bidding")
    )


def test_cfp_to_fp_default():
    """EvaluationContext.cfp_to_fp 返回 1.2（JSON 默认值）。"""
    assert _make_ctx().cfp_to_fp == pytest.approx(1.2)


def test_cfp_to_fp_override():
    """JSON 中 cfp_to_fp = 1.5 时属性返回 1.5。"""
    assert _make_ctx({"cfp_to_fp": 1.5}).cfp_to_fp == pytest.approx(1.5)


def test_cfp_to_fp_missing_fallback():
    """JSON 不含 cfp_to_fp 时属性返回默认 1.2。"""
    ctx = _make_ctx()
    raw = dict(ctx.raw)
    raw.pop("cfp_to_fp", None)
    ctx2 = EvaluationContext.from_dict(raw, ctx.inputs)
    assert ctx2.cfp_to_fp == pytest.approx(1.2)
