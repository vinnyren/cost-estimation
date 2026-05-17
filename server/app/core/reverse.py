from dataclasses import dataclass, field
from .context import EvaluationContext
from .forward import BANDS


@dataclass
class ReverseInput:
    target_total: float
    other_cost: float = 0.0
    include_ops: bool = False
    dev_factor: float = 1.0
    ops_factor: float = 1.0


@dataclass
class ReverseResult:
    """三档对应预算口径（不是团队效率）：
    - P10 = 乐观（行业最高生产率，可买到的最大规模）
    - P50 = 中位（推荐档，多数项目能达到）
    - P90 = 保守（行业较低生产率，可保证完成的最小规模）

    单一规模模型：开发与运维共用同一个功能点规模 s（与 forward 一致）。
    budget_for_dev / budget_for_ops 是该规模下推导出的成本拆分（推荐档 P50），
    而非输入 —— 拆分比例由生产率与费率决定。
    """
    budget_for_dev: float
    budget_for_ops: float
    scale_adjusted_bands: dict            # 三档调整后规模 S（开发+运维共用）
    scale_unadjusted_bands: dict          # 三档未调整规模 US
    cf_used: float
    recommended_band: str = "P50"
    # v2.0 T7：因子缺失等提示。
    warning_messages: list[str] = field(default_factory=list)


def calculate_reverse(ctx: EvaluationContext, inp: ReverseInput) -> ReverseResult:
    fp_budget = inp.target_total - inp.other_cost
    if fp_budget <= 0:
        raise ValueError(
            f"BUDGET_NEGATIVE: target {inp.target_total} - other {inp.other_cost} <= 0"
        )

    cf = ctx.cf()
    pm = ctx.hours_per_pm
    rate_dev = ctx.city_rate_dev()
    rate_ops = ctx.city_rate_ops()

    # 单一规模模型：对每档求一个调整后规模 s，使 forward(s) 的总成本恰好
    # 等于 fp_budget。forward 里 cost = s × (unit_dev + unit_ops)，其中
    # unit_x = pdr_x(b) × factor_x / pm × rate_x。开发与运维共用同一个 s。
    s_adjusted: dict[str, float] = {}
    s_unadjusted: dict[str, float] = {}
    unit_dev: dict[str, float] = {}
    unit_ops: dict[str, float] = {}
    for b in BANDS:
        ud = ctx.pdr_dev(b) * inp.dev_factor / pm * rate_dev
        uo = (ctx.pdr_ops(b) * inp.ops_factor / pm * rate_ops
              if inp.include_ops else 0.0)
        unit_dev[b] = ud
        unit_ops[b] = uo
        s = fp_budget / (ud + uo)
        s_adjusted[b] = s
        s_unadjusted[b] = s / cf

    rec = "P50"
    budget_dev = s_adjusted[rec] * unit_dev[rec]
    budget_ops = s_adjusted[rec] * unit_ops[rec]

    return ReverseResult(
        budget_for_dev=budget_dev,
        budget_for_ops=budget_ops,
        scale_adjusted_bands=s_adjusted,
        scale_unadjusted_bands=s_unadjusted,
        cf_used=cf,
    )
