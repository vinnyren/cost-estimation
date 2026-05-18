import json
import shutil
import uuid
from calendar import monthrange
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ..config import settings
from ..db.models import FunctionPoint, ParamOverride, Project as ProjectORM
from ..schemas.project import ProjectCreate, ProjectPatch


def _dump_factors(payload_dict: dict) -> dict:
    """Pop factors_dev / factors_ops dicts and remap to JSON-string columns.

    v2.0: payload 字段是 dict，落盘是 TEXT (json.dumps)；NULL = 未配置。
    """
    out = dict(payload_dict)
    if "factors_dev" in out:
        v = out.pop("factors_dev")
        out["factors_dev_json"] = json.dumps(v) if v is not None else None
    if "factors_ops" in out:
        v = out.pop("factors_ops")
        out["factors_ops_json"] = json.dumps(v) if v is not None else None
    return out


def create(db: Session, payload: ProjectCreate) -> ProjectORM:
    data = _dump_factors(payload.model_dump())
    project = ProjectORM(id=f"prj-{uuid.uuid4().hex[:12]}", **data)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def list_all(db: Session) -> list[ProjectORM]:
    return db.query(ProjectORM).order_by(ProjectORM.updated_at.desc()).all()


# v2.0 GAP-F — 列表筛选/排序/分页。
# 白名单 sort 列由 router 层做正则校验，service 层再 getattr 兜底 created_at。
_SORT_COLUMNS = {"created_at", "updated_at", "name", "target_cost"}


def list_with_query(
    db: Session,
    *,
    q: Optional[str] = None,
    city: Optional[str] = None,
    industry: Optional[str] = None,
    phase: Optional[str] = None,
    mode: Optional[str] = None,
    sort: str = "created_at",
    order: str = "desc",
    page: int = 1,
    size: int = 50,
) -> tuple[list[ProjectORM], int]:
    """Return (rows, total). Total ignores pagination."""
    qs = db.query(ProjectORM)
    if q:
        qs = qs.filter(ProjectORM.name.ilike(f"%{q}%"))
    if city:
        qs = qs.filter_by(city=city)
    if industry:
        qs = qs.filter_by(industry=industry)
    if phase:
        qs = qs.filter_by(phase=phase)
    if mode:
        qs = qs.filter_by(mode=mode)

    total = qs.count()
    sort_col_name = sort if sort in _SORT_COLUMNS else "created_at"
    sort_col = getattr(ProjectORM, sort_col_name)
    qs = qs.order_by(sort_col.desc() if order == "desc" else sort_col.asc())
    qs = qs.offset((page - 1) * size).limit(size)
    return qs.all(), total


def copy_project(db: Session, src_id: str, new_name: str) -> ProjectORM:
    """GAP-I — clone project metadata + function points + param overrides.

    Results 和 fp_snapshots 不复制（语义：副本是一个干净的工作起点，不继承历史
    计算结果，避免误导用户以为新项目已经算过）。
    """
    src = db.query(ProjectORM).filter_by(id=src_id).first()
    if not src:
        raise ValueError("PROJECT_NOT_FOUND")

    new_id = f"prj-{uuid.uuid4().hex[:12]}"
    new = ProjectORM(
        id=new_id,
        name=new_name,
        project_type=src.project_type,
        phase=src.phase,
        city=src.city,
        industry=src.industry,
        client=src.client,
        evaluator=src.evaluator,
        mode=src.mode,
        target_cost=src.target_cost,
        other_cost=src.other_cost,
        include_ops=src.include_ops,
        alpha_dev=src.alpha_dev,
        fp_method=src.fp_method,
        basis_data_ver=src.basis_data_ver,
        factors_dev_json=src.factors_dev_json,
        factors_ops_json=src.factors_ops_json,
    )
    db.add(new)

    for fp in src.function_points:
        db.add(FunctionPoint(
            id=f"fp-{uuid.uuid4().hex[:12]}",
            project_id=new_id,
            version=1,
            subsystem=fp.subsystem,
            l1_module=fp.l1_module,
            l2_module=fp.l2_module,
            description=fp.description,
            name=fp.name,
            category=fp.category,
            complexity=fp.complexity,
            fp_kind=fp.fp_kind,
            ufp=fp.ufp,
            reuse_level=fp.reuse_level,
            modify_type=fp.modify_type,
            us=fp.us,
            source="copied",
            locked=fp.locked,
            notes=fp.notes,
            ord=fp.ord,
        ))

    for po in src.param_overrides:
        db.add(ParamOverride(
            project_id=new_id,
            key=po.key,
            value=po.value,
            reason=f"(copied from {src_id})",
        ))

    db.commit()
    db.refresh(new)
    return new


def get(db: Session, project_id: str) -> ProjectORM | None:
    return db.query(ProjectORM).filter_by(id=project_id).first()


def patch(db: Session, project_id: str, payload: ProjectPatch) -> ProjectORM | None:
    p = get(db, project_id)
    if not p:
        return None
    data = _dump_factors(payload.model_dump(exclude_unset=True))
    for k, v in data.items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


def delete(db: Session, project_id: str) -> bool:
    p = get(db, project_id)
    if not p:
        return False
    # 删除磁盘上传/解析/导出目录，避免 cascade 后磁盘留下孤儿文件。
    # 失败用 ignore_errors=True 容忍权限或路径异常 — DB cascade 仍要正常推进。
    for base in (settings.upload_dir, settings.parsed_dir, settings.export_dir):
        if base is None:
            continue
        target = base / project_id
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
    db.delete(p)  # cascade 自动清 fps/snapshots/results/overrides/uploads 行
    db.commit()
    return True


BUNDLE_VERSION = "2.7"


def export_projects(db: Session, ids: list[str]) -> dict:
    """把指定项目导出为可移植 bundle dict。

    不存在的 id 静默跳过；全部不存在则 projects 为空数组。bundle 只含
    可移植数据 — 不含 id / created_at / updated_at / results / snapshots /
    uploads / ai_tasks / audit_log（运行时与历史数据）。
    """
    projects_out: list[dict] = []
    for pid in ids:
        p = db.query(ProjectORM).filter_by(id=pid).first()
        if not p:
            continue
        fps = [
            {
                "subsystem": fp.subsystem,
                "l1_module": fp.l1_module,
                "l2_module": fp.l2_module,
                "description": fp.description,
                "name": fp.name,
                "category": fp.category,
                "complexity": fp.complexity,
                "fp_kind": fp.fp_kind,
                "ufp": fp.ufp,
                "reuse_level": fp.reuse_level,
                "modify_type": fp.modify_type,
                "us": fp.us,
                "source": fp.source,
                "locked": fp.locked,
                "notes": fp.notes,
                "ord": fp.ord,
            }
            for fp in p.function_points
        ]
        overrides = [
            {"key": po.key, "value": po.value, "reason": po.reason}
            for po in p.param_overrides
        ]
        projects_out.append({
            "name": p.name,
            "project_type": p.project_type,
            "phase": p.phase,
            "city": p.city,
            "industry": p.industry,
            "client": p.client,
            "evaluator": p.evaluator,
            "mode": p.mode,
            "target_cost": p.target_cost,
            "other_cost": p.other_cost,
            "include_ops": p.include_ops,
            "alpha_dev": p.alpha_dev,
            "fp_method": p.fp_method,
            "basis_data_ver": p.basis_data_ver,
            "factors_dev": json.loads(p.factors_dev_json) if p.factors_dev_json else None,
            "factors_ops": json.loads(p.factors_ops_json) if p.factors_ops_json else None,
            "param_overrides": overrides,
            "function_points": fps,
        })
    return {
        "version": BUNDLE_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "projects": projects_out,
    }


def import_bundle(db: Session, bundle) -> tuple[int, list[str]]:
    """把已校验的 ProjectBundle 落库为新建项目。

    bundle 形参是 schemas.project.ProjectBundle 实例（router 层用 Pydantic
    校验后传入，格式非法在 router 层就被拒为 400）。每个项目生成新 id，
    不覆盖、不合并、不按名匹配 —— 落库逻辑参照 copy。
    返回 (导入数量, 新项目 id 列表)。
    """
    new_ids: list[str] = []
    for item in bundle.projects:
        new_id = f"prj-{uuid.uuid4().hex[:12]}"
        new = ProjectORM(
            id=new_id,
            name=item.name,
            project_type=item.project_type,
            phase=item.phase,
            city=item.city,
            industry=item.industry,
            client=item.client,
            evaluator=item.evaluator,
            mode=item.mode,
            target_cost=item.target_cost,
            other_cost=item.other_cost,
            include_ops=item.include_ops,
            alpha_dev=item.alpha_dev,
            fp_method=item.fp_method,
            basis_data_ver=item.basis_data_ver,
            assessment_kind=item.assessment_kind,
            factors_dev_json=json.dumps(item.factors_dev) if item.factors_dev is not None else None,
            factors_ops_json=json.dumps(item.factors_ops) if item.factors_ops is not None else None,
        )
        db.add(new)
        for fp in item.function_points:
            data = fp.model_dump()
            if data.get("source") == "claude_draft":
                data["source"] = "ai_extracted"
            db.add(FunctionPoint(
                id=f"fp-{uuid.uuid4().hex[:12]}",
                project_id=new_id,
                version=1,
                **data,
            ))
        for po in item.param_overrides:
            db.add(ParamOverride(
                project_id=new_id,
                key=po.key,
                value=po.value,
                reason=po.reason,
            ))
        new_ids.append(new_id)
    db.commit()
    return len(new_ids), new_ids


def get_stats(db: Session, month: str | None = None) -> dict:
    """v2.2 — 项目 KPI 汇总（counts + 月度数）。

    无 Project.status / Project.result_p50_total 列 — 改用 derived counts:
    - draft       = 无 function_points 的项目
    - in_progress = 有 function_points 的项目
    - archived / delivered = 0 (future)
    - monthly_p50_sum      = 0.0 (no cached field; future enhancement)
    - monthly_growth_pct   = 0.0
    """
    if not month:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
    # v2.4 review fix: 校验 month 格式，invalid input fallback to current month
    # 避免 split("-") 或 int() 抛出 → 500
    try:
        year_str, mo_str = month.split("-")
        year, mo = int(year_str), int(mo_str)
        if mo < 1 or mo > 12:
            raise ValueError("month out of range")
    except (ValueError, AttributeError):
        now = datetime.now(timezone.utc)
        year, mo = now.year, now.month

    total = db.query(ProjectORM).count()

    # 子查询：拥有至少一个 FP 的项目 id 集合
    fp_project_ids = (
        db.query(FunctionPoint.project_id).distinct().subquery()
    )
    in_progress = (
        db.query(ProjectORM)
        .filter(ProjectORM.id.in_(fp_project_ids.select()))
        .count()
    )
    draft = total - in_progress

    counts = {
        "total": total,
        "draft": draft,
        "in_progress": in_progress,
        "archived": 0,
        "delivered": 0,
    }

    # 月度项目数（按 created_at）
    start = datetime(year, mo, 1, tzinfo=timezone.utc)
    end_day = monthrange(year, mo)[1]
    end = datetime(year, mo, end_day, 23, 59, 59, 999999, tzinfo=timezone.utc)
    monthly_count = (
        db.query(ProjectORM)
        .filter(ProjectORM.created_at >= start, ProjectORM.created_at <= end)
        .count()
    )

    return {
        "counts": counts,
        "monthly_count": monthly_count,
        "monthly_p50_sum": 0.0,
        "monthly_growth_pct": 0.0,
    }
