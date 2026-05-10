import uuid, json
from sqlalchemy.orm import Session
from ..db.models import FunctionPoint, FPSnapshot, Project, Result
from ..schemas.functions import FunctionPointCreate, FunctionPointPatch


def _next_version(db: Session, project_id: str) -> int:
    last = (db.query(FunctionPoint)
            .filter_by(project_id=project_id)
            .order_by(FunctionPoint.version.desc()).first())
    return (last.version + 1) if last else 1


def _snapshot(db: Session, project_id: str, version: int, reason: str) -> None:
    items = db.query(FunctionPoint).filter_by(project_id=project_id).all()
    payload = [{c.name: getattr(item, c.name) for c in item.__table__.columns} for item in items]
    db.add(FPSnapshot(project_id=project_id, version=version,
                       snapshot_json=json.dumps(payload, default=str, ensure_ascii=False),
                       reason=reason))
    db.commit()


def _mark_results_stale(db: Session, project_id: str) -> None:
    db.query(Result).filter_by(project_id=project_id).update({Result.is_stale: True})
    db.commit()


def list_for_project(db: Session, project_id: str) -> list[FunctionPoint]:
    return (db.query(FunctionPoint).filter_by(project_id=project_id)
            .order_by(FunctionPoint.ord.asc().nullslast(), FunctionPoint.id.asc()).all())


def create(db: Session, project_id: str, payload: FunctionPointCreate) -> FunctionPoint:
    if not db.query(Project).filter_by(id=project_id).first():
        raise ValueError("PROJECT_NOT_FOUND")
    version = _next_version(db, project_id)
    fp = FunctionPoint(id=f"fp-{uuid.uuid4().hex[:12]}",
                        project_id=project_id, version=version,
                        **payload.model_dump())
    db.add(fp); db.commit(); db.refresh(fp)
    _mark_results_stale(db, project_id)
    return fp


def patch(db: Session, project_id: str, fp_id: str, payload: FunctionPointPatch) -> FunctionPoint | None:
    fp = db.query(FunctionPoint).filter_by(id=fp_id, project_id=project_id).first()
    if not fp:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(fp, k, v)
    db.commit(); db.refresh(fp)
    _mark_results_stale(db, project_id)
    return fp


def delete(db: Session, project_id: str, fp_id: str) -> bool:
    fp = db.query(FunctionPoint).filter_by(id=fp_id, project_id=project_id).first()
    if not fp:
        return False
    db.delete(fp); db.commit()
    _mark_results_stale(db, project_id)
    return True


def bulk_write(db: Session, project_id: str, items: list[FunctionPointCreate],
                replace: bool, reason: str = "bulk_write") -> int:
    if not db.query(Project).filter_by(id=project_id).first():
        raise ValueError("PROJECT_NOT_FOUND")
    # 先做快照（即使 replace=False 也保留，便于回滚）
    next_v = _next_version(db, project_id)
    _snapshot(db, project_id, next_v, reason=reason)

    if replace:
        db.query(FunctionPoint).filter_by(project_id=project_id).delete()
        db.commit()

    for it in items:
        db.add(FunctionPoint(id=f"fp-{uuid.uuid4().hex[:12]}",
                              project_id=project_id, version=next_v,
                              **it.model_dump()))
    db.commit()
    _mark_results_stale(db, project_id)
    return len(items)
