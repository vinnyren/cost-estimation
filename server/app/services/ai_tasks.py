"""v2.2 — AiTask service：CRUD + 进度更新。"""
import uuid
from sqlalchemy.orm import Session
from ..db.models import AiTask


def create_task(db: Session, project_id: str, kind: str) -> AiTask:
    task = AiTask(id=str(uuid.uuid4()), project_id=project_id, kind=kind, status="queued",
                  progress_pct=0.0, stage_log="")
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: str) -> AiTask | None:
    return db.query(AiTask).filter(AiTask.id == task_id).first()


def list_for_project(db: Session, project_id: str, limit: int = 10) -> list[AiTask]:
    return (db.query(AiTask)
            .filter(AiTask.project_id == project_id)
            .order_by(AiTask.created_at.desc())
            .limit(limit).all())


def update_task(
    db: Session, task_id: str, *,
    status: str | None = None,
    progress_pct: float | None = None,
    stage_log_append: str | None = None,
    output_json: str | None = None,
    error_message: str | None = None,
) -> AiTask | None:
    t = get_task(db, task_id)
    if not t:
        return None
    if status is not None:
        t.status = status
    if progress_pct is not None:
        t.progress_pct = progress_pct
    if stage_log_append is not None:
        t.stage_log = (t.stage_log or "") + stage_log_append + "\n"
    if output_json is not None:
        t.output_json = output_json
    if error_message is not None:
        t.error_message = error_message
    db.commit()
    db.refresh(t)
    return t
