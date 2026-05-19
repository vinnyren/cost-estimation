"""v2.8 — 反算三级模块树逐层分摊单元测试。"""
from app.services.calc import build_module_tree, _flatten_tree_leaves


class _FP:
    """轻量 FP stub（只有树分摊用到的字段）。"""
    def __init__(self, subsystem, l1, l2, ufp):
        self.subsystem = subsystem
        self.l1_module = l1
        self.l2_module = l2
        self.ufp = ufp


def test_single_branch_proportional_split():
    fps = [
        _FP("结算", "资金", "查询", 40),
        _FP("结算", "资金", "对账", 60),
    ]
    tree = build_module_tree(fps, target_ufp=200)
    assert len(tree) == 1
    sub = tree[0]
    assert sub["subsystem"] == "结算"
    assert sub["current_ufp"] == 100
    assert sub["allocated_ufp"] == 200
    l1 = sub["children"][0]
    assert l1["l1_module"] == "资金"
    assert l1["allocated_ufp"] == 200
    leaves = {c["l2_module"]: c for c in l1["children"]}
    assert abs(leaves["查询"]["allocated_ufp"] - 80) < 0.01
    assert abs(leaves["对账"]["allocated_ufp"] - 120) < 0.01
    assert abs(leaves["查询"]["delta_ufp"] - 40) < 0.01


def test_multi_subsystem_split():
    fps = [
        _FP("A", "m1", "f1", 30),
        _FP("B", "m2", "f2", 70),
    ]
    tree = build_module_tree(fps, target_ufp=100)
    subs = {n["subsystem"]: n for n in tree}
    assert abs(subs["A"]["allocated_ufp"] - 30) < 0.01
    assert abs(subs["B"]["allocated_ufp"] - 70) < 0.01
    assert abs(subs["A"]["ratio"] - 0.3) < 0.001


def test_empty_fps_returns_empty_tree():
    assert build_module_tree([], target_ufp=100) == []


def test_node_carries_current_allocated_delta_ratio_children():
    fps = [_FP("S", "L1", "L2", 50)]
    tree = build_module_tree(fps, target_ufp=120)
    node = tree[0]
    for key in ("subsystem", "current_ufp", "allocated_ufp",
                "delta_ufp", "ratio", "children"):
        assert key in node
    l1 = node["children"][0]
    for key in ("l1_module", "current_ufp", "allocated_ufp",
                "delta_ufp", "ratio", "children"):
        assert key in l1
    l2 = l1["children"][0]
    for key in ("l2_module", "current_ufp", "allocated_ufp",
                "delta_ufp", "ratio"):
        assert key in l2


def test_zero_total_current_ufp_no_div_by_zero():
    fps = [_FP("S", "L1", "L2", 0)]
    tree = build_module_tree(fps, target_ufp=100)
    assert tree[0]["ratio"] == 0.0
    assert tree[0]["allocated_ufp"] == 0.0


def test_flatten_tree_leaves_produces_leaf_list():
    fps = [
        _FP("结算", "资金", "查询", 40),
        _FP("结算", "资金", "对账", 60),
        _FP("报表", "统计", "汇总", 50),
    ]
    tree = build_module_tree(fps, target_ufp=300)
    leaves = _flatten_tree_leaves(tree)
    # 3 个叶子，每个含三级路径 + 分摊字段
    assert len(leaves) == 3
    for leaf in leaves:
        for key in ("subsystem", "l1_module", "l2_module",
                    "current_ufp", "allocated_ufp", "delta_ufp", "ratio"):
            assert key in leaf
    by_l2 = {leaf["l2_module"]: leaf for leaf in leaves}
    assert by_l2["查询"]["subsystem"] == "结算"
    assert by_l2["查询"]["l1_module"] == "资金"
