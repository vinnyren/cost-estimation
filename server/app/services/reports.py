from datetime import datetime
from pathlib import Path
from typing import Literal, Optional
from sqlalchemy.orm import Session

from ..config import settings
from ..core.forward import BANDS
from ..db.models import Project, FunctionPoint
from ..exporters.report_builder import build_report
from . import calc as calc_svc
from . import params as params_svc


# 目标造价以「万元」录入/存储，计算层以「元」运算 —— 边界处换算。
WAN = 10000.0


def _exports_dir(project_id: str) -> Path:
    # settings.export_dir 在 Settings._derive_paths 中派生为 data_dir/exports
    # （除非 COST_EXPORT_DIR 显式设置）。
    assert settings.export_dir is not None
    p = settings.export_dir / project_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _reverse_figures(db: Session, project_id: str, proj: Project) -> dict:
    """反算项目：以目标造价反推规模，再逐档正向求工作量/成本。

    单一规模模型下每档的规模都满足 forward(规模)=目标，所以 cost_total 各档
    都 ≈ 目标造价 —— 这正是反算报告该有的样子（总费用 = 目标）。
    """
    target_yuan = (proj.target_cost or 0.0) * WAN
    if target_yuan <= 0:
        raise ValueError("REVERSE_TARGET_MISSING: 反算项目缺少目标造价")
    include_ops = proj.project_type != "dev_only" and bool(proj.include_ops)
    rev = calc_svc.run_reverse(
        db, project_id, {"target_total": target_yuan, "include_ops": include_ops})

    effort_dev: dict[str, float] = {}
    cost_dev: dict[str, float] = {}
    cost_ops: dict[str, float] = {}
    cost_total: dict[str, float] = {}
    trace = {}
    for b in BANDS:
        us_b = rev["scale_unadjusted_bands"][b]
        fwd_b = calc_svc.run_forward(db, project_id, {
            "items": [{"us": us_b}],
            "include_dev": proj.project_type != "ops_only",
            "include_ops": include_ops,
        })
        effort_dev[b] = fwd_b["effort_dev_hours"][b]
        cost_dev[b] = fwd_b["cost_dev_yuan"][b]
        cost_ops[b] = fwd_b["cost_ops_yuan"][b]
        cost_total[b] = fwd_b["cost_total_yuan"][b]
        if b == "P50":
            trace = fwd_b.get("trace", {})

    return {
        "scale_us": rev["scale_unadjusted_bands"]["P50"],
        "scale_adjusted": rev["scale_adjusted_bands"]["P50"],
        # 反算每档规模不同 —— 派生基准生产率时需按档取对应 S。
        "scale_adjusted_bands": rev["scale_adjusted_bands"],
        "cf_used": rev["cf_used"],
        "effort_dev": effort_dev,
        "cost_dev": cost_dev,
        "cost_ops": cost_ops,
        "cost_total": cost_total,
        "dev_factor": trace.get("dev_factor", 1.0),
        "rate_dev": trace.get("f_city", 0.0),
        "hours_per_pm": trace.get("pm", 174.0),
        "other_cost": 0.0,
    }


def _forward_figures(db: Session, project_id: str, proj: Project) -> dict:
    fwd = calc_svc.run_forward(db, project_id, {
        "include_dev": proj.project_type != "ops_only",
        "include_ops": proj.project_type != "dev_only" and bool(proj.include_ops),
    })
    trace = fwd.get("trace", {})
    return {
        "scale_us": fwd["scale_us"],
        "scale_adjusted": fwd["scale_adjusted"],
        # 正向各档共用同一规模。
        "scale_adjusted_bands": {b: fwd["scale_adjusted"] for b in BANDS},
        "cf_used": fwd["cf_used"],
        "effort_dev": fwd["effort_dev_hours"],
        "cost_dev": fwd["cost_dev_yuan"],
        "cost_ops": fwd["cost_ops_yuan"],
        "cost_total": fwd["cost_total_yuan"],
        "dev_factor": trace.get("dev_factor", 1.0),
        "rate_dev": trace.get("f_city", 0.0),
        "hours_per_pm": trace.get("pm", 174.0),
        "other_cost": fwd.get("cost_other_yuan", 0.0),
        # v2.9 A9: pass trace so report_builder can read fp_count_declaration
        "trace": trace,
    }


def generate_excel(
    db: Session,
    project_id: str,
    band: Optional[Literal["P10", "P50", "P90"]] = None,
) -> Path:
    proj = db.query(Project).filter_by(id=project_id).first()
    if not proj:
        raise ValueError("PROJECT_NOT_FOUND")

    fps = db.query(FunctionPoint).filter_by(project_id=project_id).all()
    if not fps:
        raise ValueError("FP_EMPTY")

    # 显式 band 参数优先；其次用项目持久化的选择；最后兜底 P50。
    effective_band: str = band or getattr(proj, "selected_band", None) or "P50"

    is_reverse = proj.mode == "reverse"
    # 报告口径与结果页一致 —— 同样走 calc 服务（有效参数 + 项目因子）。
    fig = (_reverse_figures(db, project_id, proj) if is_reverse
           else _forward_figures(db, project_id, proj))

    out = _exports_dir(project_id) / (
        f"评估报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

    # v2.9 A9: resolve measurement_method and cfp_to_fp for report declaration
    measurement_method = getattr(proj, "measurement_method", "nesma_estimated") or "nesma_estimated"
    eff = params_svc.get_effective(db, project_id)
    cfp_to_fp = float(eff.get("cfp_to_fp", 1.2))

    build_report(
        out,
        project=proj,
        functions=fps,
        figures=fig,
        is_reverse=is_reverse,
        target_cost_wan=(proj.target_cost or 0.0) if is_reverse else None,
        selected_band=effective_band,
        measurement_method=measurement_method,
        cfp_to_fp=cfp_to_fp,
    )
    return out
