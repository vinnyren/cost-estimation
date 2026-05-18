from sqlalchemy.orm import Session
from ..core.context import EvaluationContext, ProjectInputs
from ..core.forward import calculate_forward, ForwardInput, FpItem
from ..core.reverse import calculate_reverse, ReverseInput
from ..core.allocator import allocate, allocate_with_validation, AllocatorInput, FpDraft
from ..db.models import Project
from . import factors as fsvc
from . import params as ps
from . import functions as fs


def _resolve_items(
    db: Session, project_id: str, payload: dict, mode: str = "forward"
) -> list[FpItem]:
    """Get FpItem list from payload, or fall back to DB functions for the project.

    Server keeps items optional in schema; if caller does not supply, we read
    every FunctionPoint of the project. This keeps existing API tests (which
    pass items explicitly) working while letting the frontend send only
    project_id.

    forward 模式下若既无 payload.items 也无 DB function points，抛
    NO_FUNCTION_POINTS（返回 422 给前端，避免静默 scale_us=0 的"看似坏了"体验）。
    reverse 模式不需要 items（仅用 target_total），所以不强制。
    """
    raw_items = payload.get("items")
    if raw_items:
        return [FpItem(us=i["us"]) for i in raw_items]
    db_items = fs.list_for_project(db, project_id)
    if not db_items and mode == "forward":
        raise ValueError(
            "NO_FUNCTION_POINTS: 项目暂无功能点，请先在 FP 编辑屏添加或上传文档让 AI 提取"
        )
    return [FpItem(us=fp.us) for fp in db_items]


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
    dev_factor, ops_factor, warnings = _resolve_factors(proj, eff, payload)
    inp = ForwardInput(
        items=_resolve_items(db, project_id, payload, mode="forward"),
        dev_factor=dev_factor,
        ops_factor=ops_factor,
        include_dev=payload.get("include_dev", True),
        include_ops=payload.get("include_ops", proj.include_ops or False),
        other_cost=payload.get("other_cost", proj.other_cost or 0.0),
    )
    r = calculate_forward(ctx, inp)
    out = r.__dict__.copy()
    out["warning_messages"] = list(out.get("warning_messages") or []) + warnings
    return out


def _allocate_ufp_to_modules(
    db: Session, project_id: str, target_ufp: float
) -> list[dict]:
    """细化分摊：把反算出的目标 UFP 按现有 FP 表各一级模块的 UFP 占比拆下去。

    每个模块给出现有 UFP、分摊后的目标 UFP、需细化增加的 UFP 差额。
    FP 表为空时返回空列表。
    """
    fps = fs.list_for_project(db, project_id)
    groups: dict[tuple[str, str], float] = {}
    for fp in fps:
        key = (fp.subsystem or "未分组", fp.l1_module or "未分类")
        groups[key] = groups.get(key, 0.0) + float(fp.ufp or 0.0)
    total_current = sum(groups.values())
    out: list[dict] = []
    for (sub, mod), cur in sorted(groups.items()):
        ratio = cur / total_current if total_current > 0 else 0.0
        allocated = target_ufp * ratio
        out.append({
            "subsystem": sub,
            "l1_module": mod,
            "current_ufp": round(cur, 2),
            "allocated_ufp": round(allocated, 2),
            "delta_ufp": round(allocated - cur, 2),
            "ratio": round(ratio, 4),
        })
    return out


def run_reverse(db: Session, project_id: str, payload: dict) -> dict:
    proj = db.query(Project).filter_by(id=project_id).first()
    if not proj:
        raise ValueError("PROJECT_NOT_FOUND")
    eff = ps.get_effective(db, project_id)
    ctx = EvaluationContext.from_dict(
        ps.effective_to_calc_dict(eff),
        ProjectInputs(industry=proj.industry, city=proj.city, phase=proj.phase),
    )
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
    # 以「细化增加 UFP」为核心：反算总规模（推荐档未调整规模 = UFP 口径）
    # 按现有 FP 表各一级模块的 UFP 占比细化分摊到模块。
    rec = out.get("recommended_band", "P50")
    target_ufp = out["scale_unadjusted_bands"][rec]
    out["target_ufp"] = round(target_ufp, 2)
    out["module_allocation"] = _allocate_ufp_to_modules(db, project_id, target_ufp)
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
