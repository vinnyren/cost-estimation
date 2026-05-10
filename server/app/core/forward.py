from dataclasses import dataclass, field
from .context import EvaluationContext


@dataclass
class FpItem:
    us: float


@dataclass
class ForwardInput:
    items: list[FpItem]
    dev_factor: float = 1.0
    ops_factor: float = 1.0
    include_dev: bool = True
    include_ops: bool = False
    other_cost: float = 0.0


@dataclass
class ForwardResult:
    scale_us: float
    scale_adjusted: float
    cf_used: float
    effort_dev_hours: dict
    effort_ops_hours: dict
    cost_dev_yuan: dict
    cost_ops_yuan: dict
    cost_other_yuan: float
    cost_total_yuan: dict
    # v2.0 T7：calc layer 把因子缺失等 non-fatal 提示挂这里返给前端，UI
    # 在 ResultCard 顶部以黄条形式展示，避免用户以为"算了就是这个数"。
    warning_messages: list[str] = field(default_factory=list)


BANDS = ("P10", "P50", "P90")


def calculate_forward(ctx: EvaluationContext, inp: ForwardInput) -> ForwardResult:
    us = sum(i.us for i in inp.items)
    cf = ctx.cf()
    s = us * cf
    eff_dev = ({b: s * ctx.pdr_dev(b) * inp.dev_factor for b in BANDS}
               if inp.include_dev else {b: 0.0 for b in BANDS})
    eff_ops = ({b: s * ctx.pdr_ops(b) * inp.ops_factor for b in BANDS}
               if inp.include_ops else {b: 0.0 for b in BANDS})
    pm = ctx.hours_per_pm
    rate_dev = ctx.city_rate_dev()
    rate_ops = ctx.city_rate_ops()
    cost_dev = {b: eff_dev[b] / pm * rate_dev for b in BANDS}
    cost_ops = {b: eff_ops[b] / pm * rate_ops for b in BANDS}
    total = {b: cost_dev[b] + cost_ops[b] + inp.other_cost for b in BANDS}
    return ForwardResult(
        scale_us=us, scale_adjusted=s, cf_used=cf,
        effort_dev_hours=eff_dev, effort_ops_hours=eff_ops,
        cost_dev_yuan=cost_dev, cost_ops_yuan=cost_ops,
        cost_other_yuan=inp.other_cost, cost_total_yuan=total,
    )
