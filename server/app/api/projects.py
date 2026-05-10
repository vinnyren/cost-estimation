from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schemas.project import ProjectCreate, ProjectRead, ProjectPatch
from ..services import projects as svc

router = APIRouter(prefix="/api/projects")


def _wrap(data):
    return {"ok": True, "data": data}


# v2.0 T6 — 列表端点用 success/data/meta 三段式信封；其它端点保留旧的 ok/data 信封
# 以避免改动前端契约。
def _read(p) -> dict:
    return ProjectRead.model_validate(p).model_dump(mode="json")


class ProjectCopyIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)


@router.post("", status_code=201)
def create(payload: ProjectCreate, db: Session = Depends(get_db)):
    p = svc.create(db, payload)
    return _wrap(_read(p))


@router.get("")
def list_all(
    q: str | None = Query(None, max_length=100),
    city: str | None = Query(None, max_length=20),
    industry: str | None = Query(None, max_length=40),
    phase: str | None = Query(None, pattern="^(budget|bidding|planning|change|settled)$"),
    mode: str | None = Query(None, pattern="^(forward|reverse)$"),
    sort: str = Query("created_at", pattern="^(created_at|updated_at|name|target_cost)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    rows, total = svc.list_with_query(
        db,
        q=q,
        city=city,
        industry=industry,
        phase=phase,
        mode=mode,
        sort=sort,
        order=order,
        page=page,
        size=size,
    )
    return {
        "success": True,
        "data": [_read(p) for p in rows],
        "error": None,
        "meta": {"total": total, "page": page, "size": size},
    }


@router.get("/{project_id}")
def get_one(project_id: str, db: Session = Depends(get_db)):
    p = svc.get(db, project_id)
    if not p:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND"}})
    return _wrap(_read(p))


@router.patch("/{project_id}")
def patch_one(project_id: str, payload: ProjectPatch, db: Session = Depends(get_db)):
    p = svc.patch(db, project_id, payload)
    if not p:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND"}})
    return _wrap(_read(p))


@router.delete("/{project_id}")
def delete_one(project_id: str, db: Session = Depends(get_db)):
    ok = svc.delete(db, project_id)
    if not ok:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND"}})
    return _wrap({"deleted": project_id})


@router.post("/{project_id}/copy", status_code=201)
def copy(project_id: str, payload: ProjectCopyIn, db: Session = Depends(get_db)) -> dict:
    try:
        new = svc.copy_project(db, project_id, payload.name)
    except ValueError as e:
        if "NOT_FOUND" in str(e):
            raise HTTPException(404, detail={"error": {"code": "PROJECT_NOT_FOUND"}})
        raise
    return {"success": True, "data": _read(new), "error": None}
