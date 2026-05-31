from sqlalchemy.orm import Session
from ..core.context import EvaluationContext, ProjectInputs
from ..core.forward import calculate_forward, ForwardInput, FpItem
from ..core.reverse import calculate_reverse, ReverseInput
from ..core.allocator import allocate_with_validation, AllocatorInput, FpDraft
from ..db.models import Project
from . import factors as fsvc
from . import params as ps
from . import functions as fs


_METHOD_DECLARATION = {
    "ifpug":            "FP (IFPUG-GB/T 42449-2023)",
    "nesma_detailed":   "FP (NESMA-GB/T 42588-2023, 详细级)",
    "nesma_estimated":  "FP (NESMA-GB/T 42588-2023, 估算级)",
    "nesma_indicative": "FP (NESMA-GB/T 42588-2023, 预估级)",
    "cosmic":           "FP 当量 (COSMIC-GB/T 42452-2023, 经 CFP 换算)",
}


def _declaration_for(measurement_method: str) -> str:
    """返回 measurement_method 对应的规模声明字符串。"""
    return _METHOD_DECLARATION.get(measurement_method, "FP (IFPUG-GB/T 42449-2023)")


def _resolve_items(
    db: Session, project_id: str, payload: dict, mode: str = "forward",
    cfp_to_fp: float = 1.2, is_cosmic: bool = False,
) -> list[FpItem]:
    """Get FpItem list from payload, or fall back to DB functions for the project.

    Server keeps items optional in schema; if caller does not supply, we read
    every FunctionPoint of the project. This keeps existing API tests (which
    pass items explicitly) working while letting the frontend send only
    project_id.

    forward 模式下若既无 payload.items 也无 DB function points，抛
    NO_FUNCTION_POINTS（返回 422 给前端，避免静默 scale_us=0 的"看似坏了"体验）。
    reverse 模式不需要 items（仅用 target_total），所以不强制。

    v2.9 — COSMIC 项目：CFP ÷ cfp_to_fp 换算为 FP 等量后再进成本管道。
    """
    raw_items = payload.get("items")
    if raw_items:
        items = [FpItem(us=i["us"], modify_type=i.get("modify_type", "add")) for i in raw_items]
    else:
        db_items = fs.list_for_project(db, project_id)
        if not db_items and mode == "forward":
            raise ValueError(
                "NO_FUNCTION_POINTS: 项目暂无功能点，请先在 FP 编辑屏添加或上传文档让 AI 提取"
            )
        items = [FpItem(us=fp.us, modify_type=fp.modify_type or "add") for fp in db_items]

    # COSMIC CFP → FP 等量换算（仅 forward，仅 COSMIC 方法）
    if is_cosmic:
        if not (cfp_to_fp and cfp_to_fp > 0):
            raise ValueError("INVALID_CFP_TO_FP: COSMIC 换算系数 cfp_to_fp 必须 > 0")
        items = [FpItem(us=item.us / cfp_to_fp, modify_type=item.modify_type)
                 for item in items]

    return items


def _resolve_factors(
    proj: Project, eff: dict, payload: dict
) -> tuple[float, float, list[str]]:
    """If caller explicitly passes dev_factor/ops_factor in the payload, honor
    those (legacy API tests + direct overrides). Otherwise derive from the
    project's factors_dev_json / factors_ops_json via the factors service.

    Returns (dev_factor, ops_factor, warning_messages).
    """
    explicit_dev = "dev_factor" in payload
    explicit_ops = "ops_factor" in payload
    if explicit_dev and explicit_ops:
        return payload["dev_factor"], payload["ops_factor"], []

    dev_f, ops_f, warnings = fsvc.project_factors(proj, eff)
    if explicit_dev:
        dev_f = payload["dev_factor"]
        warnings = [
            w for w in warnings if "开发调整因子" not in w
        ]
    if explicit_ops:
        ops_f = payload["ops_factor"]
        warnings = [
            w for w in warnings if "运维调整因子" not in w
        ]
    return dev_f, ops_f, warnings


def run_forward(db: Session, project_id: str, payload: dict) -> dict:
    proj = db.query(Project).filter_by(id=project_id).first()
    if not proj:
        raise ValueError("PROJECT_NOT_FOUND")
    eff = ps.get_effective(db, project_id)
    ctx = EvaluationContext.from_dict(
        ps.effective_to_calc_dict(eff),
        ProjectInputs(industry=proj.industry, city=proj.city, phase=proj.phase),
    )
    method = getattr(proj, "measurement_method", "nesma_estimated") or "nesma_estimated"
    is_cosmic = (method == "cosmic")
    dev_factor, ops_factor, warnings = _resolve_factors(proj, eff, payload)
    inp = ForwardInput(
        items=_resolve_items(
            db, project_id, payload, mode="forward",
            cfp_to_fp=ctx.cfp_to_fp, is_cosmic=is_cosmic,
        ),
        dev_factor=dev_factor,
        ops_factor=ops_factor,
        include_dev=payload.get("include_dev", True),
        include_ops=payload.get("include_ops", proj.include_ops or False),
        other_cost=payload.get("other_cost", proj.other_cost or 0.0),
        assessment_kind=getattr(proj, "assessment_kind", None) or "development",
        size_declaration=_declaration_for(method),
    )
    r = calculate_forward(ctx, inp)
    out = r.__dict__.copy()
    out["warning_messages"] = list(out.get("warning_messages") or []) + warnings
    return out


def build_module_tree(fps: list, target_ufp: float) -> list[dict]:
    """沿 子系统→一级→二级 模块树逐层分摊目标 UFP。

    纯函数：fps 是带 subsystem/l1_module/l2_module/ufp 属性的对象列表。
    每层按现有 UFP 占比把上层 allocated_ufp 分到子节点。
    返回子系统节点列表，每节点含 current_ufp/allocated_ufp/delta_ufp/
    ratio/children。FP 列表为空 → 返回 []。
    """
    if not fps:
        return []

    tree: dict[str, dict[str, dict[str, float]]] = {}
    for fp in fps:
        sub = fp.subsystem or "未分组"
        l1 = fp.l1_module or "未分类"
        l2 = fp.l2_module or "未细分"
        tree.setdefault(sub, {}).setdefault(l1, {})
        tree[sub][l1][l2] = tree[sub][l1].get(l2, 0.0) + float(fp.ufp or 0.0)

    total = sum(
        u for subv in tree.values()
        for l1v in subv.values() for u in l1v.values()
    )

    def _split(current: float, parent_alloc: float, parent_total: float) -> tuple[float, float]:
        ratio = current / parent_total if parent_total > 0 else 0.0
        return ratio, parent_alloc * ratio

    out: list[dict] = []
    for sub in sorted(tree.keys()):
        sub_cur = sum(u for l1v in tree[sub].values() for u in l1v.values())
        sub_ratio, sub_alloc = _split(sub_cur, target_ufp, total)
        sub_node = {
            "subsystem": sub,
            "current_ufp": round(sub_cur, 2),
            "allocated_ufp": round(sub_alloc, 2),
            "delta_ufp": round(sub_alloc - sub_cur, 2),
            "ratio": round(sub_ratio, 4),
            "children": [],
        }
        for l1 in sorted(tree[sub].keys()):
            l1_cur = sum(tree[sub][l1].values())
            l1_ratio, l1_alloc = _split(l1_cur, sub_alloc, sub_cur)
            l1_node = {
                "l1_module": l1,
                "current_ufp": round(l1_cur, 2),
                "allocated_ufp": round(l1_alloc, 2),
                "delta_ufp": round(l1_alloc - l1_cur, 2),
                "ratio": round(l1_ratio, 4),
                "children": [],
            }
            for l2 in sorted(tree[sub][l1].keys()):
                l2_cur = tree[sub][l1][l2]
                l2_ratio, l2_alloc = _split(l2_cur, l1_alloc, l1_cur)
                l1_node["children"].append({
                    "l2_module": l2,
                    "current_ufp": round(l2_cur, 2),
                    "allocated_ufp": round(l2_alloc, 2),
                    "delta_ufp": round(l2_alloc - l2_cur, 2),
                    "ratio": round(l2_ratio, 4),
                })
            sub_node["children"].append(l1_node)
        out.append(sub_node)
    return out


def _flatten_tree_leaves(tree: list[dict]) -> list[dict]:
    """把三级树压成叶子列表（兼容旧前端 module_allocation 字段）。"""
    leaves: list[dict] = []
    for sub in tree:
        for l1 in sub["children"]:
            for l2 in l1["children"]:
                leaves.append({
                    "subsystem": sub["subsystem"],
                    "l1_module": l1["l1_module"],
                    "l2_module": l2["l2_module"],
                    "current_ufp": l2["current_ufp"],
                    "allocated_ufp": l2["allocated_ufp"],
                    "delta_ufp": l2["delta_ufp"],
                    "ratio": l2["ratio"],
                })
    return leaves


def run_reverse(db: Session, project_id: str, payload: dict) -> dict:
    proj = db.query(Project).filter_by(id=project_id).first()
    if not proj:
        raise ValueError("PROJECT_NOT_FOUND")
    eff = ps.get_effective(db, project_id)
    ctx = EvaluationContext.from_dict(
        ps.effective_to_calc_dict(eff),
        ProjectInputs(industry=proj.industry, city=proj.city, phase=proj.phase),
    )
    method = getattr(proj, "measurement_method", "nesma_estimated") or "nesma_estimated"
    is_cosmic = (method == "cosmic")
    dev_factor, ops_factor, warnings = _resolve_factors(proj, eff, payload)
    inp = ReverseInput(
        target_total=payload["target_total"],
        other_cost=payload.get("other_cost", proj.other_cost or 0.0),
        include_ops=payload.get("include_ops", proj.include_ops or False),
        dev_factor=dev_factor,
        ops_factor=ops_factor,
    )
    r = calculate_reverse(ctx, inp)
    out = r.__dict__.copy()
    out["warning_messages"] = list(out.get("warning_messages") or []) + warnings
    # v2.9 — COSMIC：reverse 按 FP/人月生产率反推的规模是 FP 当量口径，须 ×cfp_to_fp
    # 还原为 CFP 当量，与 forward 的 CFP ÷ cfp_to_fp 对称，且与 CFP 口径的功能点表
    # （fp.ufp 存 CFP）同口径分摊，避免 allocated(FP当量) − current(CFP) 的口径错配。
    if is_cosmic:
        cfp = ctx.cfp_to_fp
        if not (cfp and cfp > 0):
            raise ValueError("INVALID_CFP_TO_FP: COSMIC 换算系数 cfp_to_fp 必须 > 0")
        out["scale_adjusted_bands"] = {
            b: v * cfp for b, v in out["scale_adjusted_bands"].items()
        }
        out["scale_unadjusted_bands"] = {
            b: v * cfp for b, v in out["scale_unadjusted_bands"].items()
        }
    # 以「细化增加 UFP」为核心：反算总规模（推荐档未调整规模 = UFP 口径）
    # 按现有 FP 表各一级模块的 UFP 占比细化分摊到模块。
    rec = out.get("recommended_band", "P50")
    target_ufp = out["scale_unadjusted_bands"][rec]
    out["target_ufp"] = round(target_ufp, 2)
    fps = fs.list_for_project(db, project_id)
    tree = build_module_tree(fps, target_ufp)
    out["module_allocation_tree"] = tree
    out["module_allocation"] = _flatten_tree_leaves(tree)
    return out


def run_allocate(db: Session, project_id: str, payload: dict) -> dict:
    """Allocator 算法本身不需要 project_id（纯数学切分），但 schema 要求是
    为了：1) 显式绑定到一个项目作为审计 / 权限作用域，2) 保证调用者拿到的
    drafts 之后能 bulk_write 回同一个项目。这里加一道存在性校验，避免对
    不存在的项目调用 allocate 也返回 200（ISSUE-012 round 2 QA）。

    v2.3 升级：返回 {items, validation} envelope。
    """
    if not db.query(Project).filter_by(id=project_id).first():
        raise ValueError("PROJECT_NOT_FOUND")
    drafts = [FpDraft(name=d["name"], weight=d["weight"],
                      locked=d.get("locked", False), locked_us=d.get("locked_us", 0.0))
              for d in payload["drafts"]]
    result = allocate_with_validation(AllocatorInput(
        target_us=payload["target_us"], drafts=drafts, cf=payload.get("cf", 1.21)))
    return {
        "items": [o.__dict__ for o in result["items"]],
        "validation": result["validation"],
    }
