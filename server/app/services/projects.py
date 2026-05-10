import json
import shutil
import uuid

from sqlalchemy.orm import Session

from ..config import settings
from ..db.models import Project as ProjectORM
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
