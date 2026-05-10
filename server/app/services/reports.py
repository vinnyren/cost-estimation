from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from ..config import settings
from ..core.context import EvaluationContext, ProjectInputs
from ..core.forward import calculate_forward, ForwardInput, FpItem
from ..db.models import Project, FunctionPoint
from ..exporters.excel import render, TemplateBrokenError
from ..exporters.fallback import render_fallback
from . import params as ps


TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "report-v1.xlsx"


def _exports_dir(project_id: str) -> Path:
    # settings.export_dir 在 Settings._derive_paths 中派生为 data_dir/exports
    # （除非 COST_EXPORT_DIR 显式设置）。
    assert settings.export_dir is not None
    p = settings.export_dir / project_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def generate_excel(db: Session, project_id: str) -> Path:
    proj = db.query(Project).filter_by(id=project_id).first()
    if not proj:
        raise ValueError("PROJECT_NOT_FOUND")

    fps = db.query(FunctionPoint).filter_by(project_id=project_id).all()
    if not fps:
        raise ValueError("FP_EMPTY")

    full_params = ps.get_global(db)
    ctx = EvaluationContext.from_dict(
        full_params,
        ProjectInputs(industry=proj.industry, city=proj.city, phase=proj.phase),
    )

    fp_items = [FpItem(us=fp.us) for fp in fps]
    inp = ForwardInput(items=fp_items, dev_factor=1.0, ops_factor=1.0,
                       include_dev=(proj.project_type != "ops_only"),
                       include_ops=(proj.project_type != "dev_only" and proj.include_ops),
                       other_cost=proj.other_cost or 0.0)
    r = calculate_forward(ctx, inp)

    out = _exports_dir(project_id) / f"评估报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    render_kwargs = dict(
        project_name=proj.name,
        project_overview=f"客户：{proj.client or '—'} / 评估方：{proj.evaluator or '—'} / 阶段：{proj.phase}",
        scale_adjusted=r.scale_adjusted,
        effort_dev=r.effort_dev_hours,
        cost_dev=r.cost_dev_yuan,
        cost_total_p50_yuan=r.cost_total_yuan["P50"],
        functions=[{
            "subsystem": fp.subsystem, "l1_module": fp.l1_module, "l2_module": fp.l2_module,
            "description": fp.description, "name": fp.name, "category": fp.category,
            "ufp": fp.ufp, "reuse_level": fp.reuse_level, "modify_type": fp.modify_type,
            "us": fp.us, "source": fp.source, "notes": fp.notes,
        } for fp in fps],
        factors=[
            {"category": "规模变更", "name": "CF", "value": r.cf_used},
            {"category": "开发", "name": "总因子链", "value": inp.dev_factor},
            {"category": "运维", "name": "总因子链", "value": inp.ops_factor},
        ],
        steps=[
            {"step": "1", "desc": "未调整规模 US", "formula": "Σ us", "result": r.scale_us},
            {"step": "2", "desc": "调整后规模 S", "formula": "US × CF", "result": r.scale_adjusted},
            {"step": "3", "desc": "工作量 P50", "formula": "S × PDR_P50 × 因子",
             "result": r.effort_dev_hours["P50"]},
            {"step": "4", "desc": "成本 P50", "formula": "AE / 174 × 城市费率",
             "result": r.cost_dev_yuan["P50"]},
        ],
        params=[
            {"key": "城市", "value": proj.city, "source": "user"},
            {"key": "行业", "value": proj.industry, "source": "user"},
            {"key": "阶段", "value": proj.phase, "source": "user"},
            {"key": "基准数据版本", "value": proj.basis_data_ver, "source": "system"},
        ],
    )

    try:
        render(TEMPLATE_PATH, out, **render_kwargs)
    except TemplateBrokenError:
        render_fallback(out, **render_kwargs)
    return out
