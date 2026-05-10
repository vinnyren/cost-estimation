from dataclasses import dataclass
from .context import EvaluationContext
from .forward import BANDS


@dataclass
class ReverseInput:
    target_total: float
    other_cost: float = 0.0
    include_ops: bool = False
    alpha_dev: float = 1.0
    dev_factor: float = 1.0
    ops_factor: float = 1.0


@dataclass
class ReverseResult:
    """三档对应预算口径（不是团队效率）：
    - P10 = 乐观（行业最高生产率，可买到的最大规模）
    - P50 = 中位（推荐档，多数项目能达到）
    - P90 = 保守（行业较低生产率，可保证完成的最小规模）
    """
    budget_for_dev: float
    budget_for_ops: float
    scale_adjusted_bands: dict           # 开发三档调整后规模
    scale_unadjusted_bands: dict          # 开发三档未调整
    scale_adjusted_ops_bands: dict
    scale_unadjusted_ops_bands: dict
    cf_used: float
    recommended_band: str = "P50"


def calculate_reverse(ctx: EvaluationContext, inp: ReverseInput) -> ReverseResult:
    fp_budget = inp.target_total - inp.other_cost
    if fp_budget <= 0:
        raise ValueError(
            f"BUDGET_NEGATIVE: target {inp.target_total} - other {inp.other_cost} <= 0"
        )
    if inp.include_ops:
        budget_dev = fp_budget * inp.alpha_dev
        budget_ops = fp_budget * (1.0 - inp.alpha_dev)
    else:
        budget_dev = fp_budget
        budget_ops = 0.0

    cf = ctx.cf()
    pm_h = ctx.hours_per_pm

    # Dev 反算
    pm_dev = budget_dev / ctx.city_rate_dev()
    ae_dev = pm_dev * pm_h
    ue_dev = ae_dev / inp.dev_factor
    s_dev = {b: ue_dev / ctx.pdr_dev(b) for b in BANDS}
    us_dev = {b: s_dev[b] / cf for b in BANDS}

    # Ops 反算
    if budget_ops > 0:
        pm_ops = budget_ops / ctx.city_rate_ops()
        ae_ops = pm_ops * pm_h
        ue_ops = ae_ops / inp.ops_factor
        s_ops = {b: ue_ops / ctx.pdr_ops(b) for b in BANDS}
        us_ops = {b: s_ops[b] / cf for b in BANDS}
    else:
        s_ops = {b: 0.0 for b in BANDS}
        us_ops = {b: 0.0 for b in BANDS}

    return ReverseResult(
        budget_for_dev=budget_dev, budget_for_ops=budget_ops,
        scale_adjusted_bands=s_dev, scale_unadjusted_bands=us_dev,
        scale_adjusted_ops_bands=s_ops, scale_unadjusted_ops_bands=us_ops,
        cf_used=cf,
    )
