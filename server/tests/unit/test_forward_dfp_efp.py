"""v2.8 — forward 按 assessment_kind 分类汇总规模（DFP / EFP）。"""
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


def test_development_uses_add_and_convert_only():
    # 开发项目 DFP = ADD + CFP；change/delete 不计入。
    items = [
        FpItem(us=10, modify_type="add"),
        FpItem(us=5, modify_type="convert"),
        FpItem(us=100, modify_type="change"),
        FpItem(us=100, modify_type="delete"),
    ]
    inp = ForwardInput(items=items, assessment_kind="development",
                       include_dev=True, include_ops=False)
    r = calculate_forward(_ctx(), inp)
    assert r.scale_us == 15  # 10 + 5


def test_enhancement_sums_all_change_types():
    # 增强项目 EFP = ADD + CHGA + CFP + DEL。
    items = [
        FpItem(us=10, modify_type="add"),
        FpItem(us=20, modify_type="change"),
        FpItem(us=5, modify_type="convert"),
        FpItem(us=8, modify_type="delete"),
    ]
    inp = ForwardInput(items=items, assessment_kind="enhancement",
                       include_dev=True, include_ops=False)
    r = calculate_forward(_ctx(), inp)
    assert r.scale_us == 43  # 10 + 20 + 5 + 8


def test_missing_modify_type_treated_as_add():
    # 老数据 modify_type 为 None → 视为 add，开发口径计入。
    items = [FpItem(us=18, modify_type=None)]
    inp = ForwardInput(items=items, assessment_kind="development",
                       include_dev=True, include_ops=False)
    r = calculate_forward(_ctx(), inp)
    assert r.scale_us == 18


def test_fp_count_declaration_in_trace():
    # 报告用 FP 计数声明字符串挂在 trace。
    items = [FpItem(us=18, modify_type="add")]
    inp = ForwardInput(items=items, assessment_kind="development",
                       include_dev=True, include_ops=False)
    r = calculate_forward(_ctx(), inp)
    assert r.trace["fp_count_declaration"] == "18 FP (IFPUG-GB/T 42449-2023)"
