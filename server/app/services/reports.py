from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from ..config import settings
from ..core.forward import BANDS
from ..db.models import Project, FunctionPoint
from ..exporters.excel import render, TemplateBrokenError
from ..exporters.fallback import render_fallback
from . import calc as calc_svc


TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "report-v1.xlsx"

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
    cost_total: dict[str, float] = {}
    for b in BANDS:
        us_b = rev["scale_unadjusted_bands"][b]
        fwd_b = calc_svc.run_forward(db, project_id, {
            "items": [{"us": us_b}],
            "include_dev": proj.project_type != "ops_only",
            "include_ops": include_ops,
        })
        effort_dev[b] = fwd_b["effort_dev_hours"][b]
        cost_dev[b] = fwd_b["cost_dev_yuan"][b]
        cost_total[b] = fwd_b["cost_total_yuan"][b]

    return {
        "scale_us": rev["scale_unadjusted_bands"]["P50"],
        "scale_adjusted": rev["scale_adjusted_bands"]["P50"],
        "cf_used": rev["cf_used"],
        "effort_dev": effort_dev,
        "cost_dev": cost_dev,
        "cost_total_p50_yuan": cost_total["P50"],
    }


def _forward_figures(db: Session, project_id: str, proj: Project) -> dict:
    fwd = calc_svc.run_forward(db, project_id, {
        "include_dev": proj.project_type != "ops_only",
        "include_ops": proj.project_type != "dev_only" and bool(proj.include_ops),
    })
    return {
        "scale_us": fwd["scale_us"],
        "scale_adjusted": fwd["scale_adjusted"],
        "cf_used": fwd["cf_used"],
        "effort_dev": fwd["effort_dev_hours"],
        "cost_dev": fwd["cost_dev_yuan"],
        "cost_total_p50_yuan": fwd["cost_total_yuan"]["P50"],
    }


def generate_excel(db: Session, project_id: str) -> Path:
    proj = db.query(Project).filter_by(id=project_id).first()
    if not proj:
        raise ValueError("PROJECT_NOT_FOUND")

    fps = db.query(FunctionPoint).filter_by(project_id=project_id).all()
    if not fps:
        raise ValueError("FP_EMPTY")

    is_reverse = proj.mode == "reverse"
    # 报告口径与结果页一致 —— 同样走 calc 服务（有效参数 + 项目因子）。
    fig = (_reverse_figures(db, project_id, proj) if is_reverse
           else _forward_figures(db, project_id, proj))

    out = _exports_dir(project_id) / f"评估报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    mode_label = "反算（目标造价 → 反推规模）" if is_reverse else "正向（功能点 → 造价）"
    if is_reverse:
        steps = [
            {"step": "1", "desc": "目标可用预算", "formula": "目标造价 − 其他费用",
             "result": round((proj.target_cost or 0.0) * WAN, 2)},
            {"step": "2", "desc": "反推未调整规模 US（推荐档 P50）",
             "formula": "预算 ÷ 单位规模成本", "result": round(fig["scale_us"], 4)},
            {"step": "3", "desc": "调整后规模 S", "formula": "US × CF",
             "result": round(fig["scale_adjusted"], 4)},
            {"step": "4", "desc": "总费用 P50（应复现目标造价）",
             "formula": "forward(S) 合计", "result": round(fig["cost_total_p50_yuan"], 2)},
        ]
    else:
        steps = [
            {"step": "1", "desc": "未调整规模 US", "formula": "Σ us", "result": fig["scale_us"]},
            {"step": "2", "desc": "调整后规模 S", "formula": "US × CF",
             "result": fig["scale_adjusted"]},
            {"step": "3", "desc": "工作量 P50", "formula": "S × PDR_P50 × 因子",
             "result": fig["effort_dev"]["P50"]},
            {"step": "4", "desc": "成本 P50", "formula": "AE / 174 × 城市费率",
             "result": fig["cost_dev"]["P50"]},
        ]

    render_kwargs = dict(
        project_name=proj.name,
        project_overview=(
            f"客户：{proj.client or '—'} / 评估方：{proj.evaluator or '—'} / "
            f"阶段：{proj.phase} / 评估方式：{mode_label}"
        ),
        scale_adjusted=fig["scale_adjusted"],
        effort_dev=fig["effort_dev"],
        cost_dev=fig["cost_dev"],
        cost_total_p50_yuan=fig["cost_total_p50_yuan"],
        functions=[{
            "subsystem": fp.subsystem, "l1_module": fp.l1_module, "l2_module": fp.l2_module,
            "description": fp.description, "name": fp.name, "category": fp.category,
            "ufp": fp.ufp, "reuse_level": fp.reuse_level, "modify_type": fp.modify_type,
            "us": fp.us, "source": fp.source, "notes": fp.notes,
        } for fp in fps],
        factors=[
            {"category": "规模变更", "name": "CF", "value": fig["cf_used"]},
        ],
        steps=steps,
        params=[
            {"key": "城市", "value": proj.city, "source": "user"},
            {"key": "行业", "value": proj.industry, "source": "user"},
            {"key": "阶段", "value": proj.phase, "source": "user"},
            {"key": "评估方式", "value": mode_label, "source": "user"},
            {"key": "基准数据版本", "value": proj.basis_data_ver, "source": "system"},
        ],
    )

    try:
        render(TEMPLATE_PATH, out, **render_kwargs)
    except TemplateBrokenError:
        render_fallback(out, **render_kwargs)
    return out
