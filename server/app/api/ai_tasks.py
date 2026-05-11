"""v2.2 — /api/ai-tasks endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schemas.ai_tasks import AiTaskCreate, AiTaskUpdate, AiTaskRead
from ..services import ai_tasks as svc


router = APIRouter(prefix="/api/ai-tasks", tags=["ai-tasks"])


@router.post("", response_model=AiTaskRead, status_code=201)
def create(payload: AiTaskCreate, db: Session = Depends(get_db)):
    return svc.create_task(db, payload.project_id, payload.kind)


@router.get("", response_model=list[AiTaskRead])
def list_tasks(project_id: str, db: Session = Depends(get_db)):
    return svc.list_for_project(db, project_id)


@router.get("/{task_id}", response_model=AiTaskRead)
def read_one(task_id: str, db: Session = Depends(get_db)):
    t = svc.get_task(db, task_id)
    if not t:
        raise HTTPException(404, "task not found")
    return t


@router.patch("/{task_id}", response_model=AiTaskRead)
def patch(task_id: str, payload: AiTaskUpdate, db: Session = Depends(get_db)):
    t = svc.update_task(
        db, task_id,
        status=payload.status,
        progress_pct=payload.progress_pct,
        stage_log_append=payload.stage_log_append,
        output_json=payload.output_json,
        error_message=payload.error_message,
    )
    if not t:
        raise HTTPException(404, "task not found")
    return t
