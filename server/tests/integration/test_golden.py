import json
from pathlib import Path

from app.core.context import EvaluationContext, ProjectInputs
from app.core.forward import calculate_forward, ForwardInput, FpItem
from app.core.factors import ops_factor_chain

GOLDEN = Path(__file__).parent.parent / "golden"


def test_golden_appendix_d():
    """实施规程附录 D 算例黄金测试 → 总费用中值 = 48.92 万元 ±0.01 万元

    这是 Plan 1 完成的核心证据：算法实现与国家标准实施规程示例字符级一致。
    """
    params = json.loads((GOLDEN / "csbmk_202210.json").read_text(encoding="utf-8"))
    case = json.loads((GOLDEN / "appendix_d.json").read_text(encoding="utf-8"))
    inp_data = case["inputs"]
    expected = case["expected"]

    ctx = EvaluationContext.from_dict(
        params,
        ProjectInputs(industry=inp_data["industry"],
                      city=inp_data["city"],
                      phase=inp_data["phase"]),
    )

    # 验证运维因子链 = 1.18
    ops_f = ops_factor_chain(**inp_data["ops_factor_components"])
    assert abs(ops_f - inp_data["ops_factor"]) < 0.005, \
        f"ops factor chain {ops_f:.4f} vs expected {inp_data['ops_factor']}"

    # 跑 forward
    inp = ForwardInput(
        items=[FpItem(us=inp_data["items_us_total"])],
        dev_factor=inp_data["dev_factor"],
        ops_factor=inp_data["ops_factor"],
        include_dev=inp_data["include_dev"],
        include_ops=inp_data["include_ops"],
        other_cost=inp_data["other_cost"],
    )
    r = calculate_forward(ctx, inp)

    tol_yuan = expected["tolerance_yuan"]
    tol_hours = expected["tolerance_hours"]

    # 关键断言 1：调整后规模 = 332.75
    assert abs(r.scale_adjusted - expected["scale_adjusted"]) < 0.5, \
        f"S={r.scale_adjusted} vs expected {expected['scale_adjusted']}"

    # 关键断言 2：开发工作量 P50
    assert abs(r.effort_dev_hours["P50"] - expected["effort_dev_p50_hours"]) < tol_hours, \
        f"dev hours P50={r.effort_dev_hours['P50']:.2f} vs expected {expected['effort_dev_p50_hours']}"

    # 关键断言 3：运维工作量 P50
    assert abs(r.effort_ops_hours["P50"] - expected["effort_ops_p50_hours"]) < tol_hours, \
        f"ops hours P50={r.effort_ops_hours['P50']:.2f} vs expected {expected['effort_ops_p50_hours']}"

    # 关键断言 4（核心）：总费用 P50 = 48.92 万元
    assert abs(r.cost_total_yuan["P50"] - expected["cost_total_p50_yuan"]) < tol_yuan, \
        f"total P50={r.cost_total_yuan['P50']:.2f} vs expected {expected['cost_total_p50_yuan']}"

    # 边界档：由于 spec v1.1 使用 PDR P10/P50/P90 替代 ±20%，
    # P10/P90 与实施规程附录 D 的 39.65/58.19 万元（±20%）会有显著差异，
    # 此处仅做单调性检查
    assert r.cost_total_yuan["P10"] < r.cost_total_yuan["P50"] < r.cost_total_yuan["P90"]


def test_golden_appendix_d_factor_components_in_csbmk_202510():
    """额外验证：用同样的因子组件查 CSBMK®-202510，能复现 1.18 ±0.005"""
    repo_root = Path(__file__).parent.parent.parent
    csbmk_2510 = json.loads((repo_root / "app" / "data" / "csbmk_202510.json").read_text(encoding="utf-8"))
    f_ops = csbmk_2510["factors_ops"]
    chain = (f_ops["business_importance"]["core"] *
             f_ops["security_level"]["L4"] *
             f_ops["support"]["remote"] *
             f_ops["update_freq"]["quarterly"] *
             f_ops["response_time"]["24h"] *
             f_ops["integrity_level"]["C/D"] *
             1.0 *  # platform 在 CSBMK-2510 ops 因子里没有列，按 1.0
             f_ops["team_exp"]["related"] *
             f_ops["deployment"]["centralized"] *
             f_ops["user_scale"][">10k"] *
             f_ops["system_relevance"]["1-5"])
    assert abs(chain - 1.18) < 0.005, f"CSBMK-2510 factor chain = {chain}"
