from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schemas.params import ParamPatch
from ..services import params as svc

router = APIRouter()


@router.get("/api/params/global")
def get_global(db: Session = Depends(get_db)):
    return {"ok": True, "data": svc.get_global(db)}


@router.patch("/api/params/global")
def patch_global(payload: ParamPatch, db: Session = Depends(get_db)):
    svc.patch_global(db, payload.key, payload.value)
    return {"ok": True, "data": {"updated": payload.key}}


@router.post("/api/params/global/reset")
def reset_global(db: Session = Depends(get_db)):
    svc.reset_global(db)
    return {"ok": True, "data": svc.get_global(db)}


@router.get("/api/projects/{project_id}/params/effective")
def get_effective(project_id: str, db: Session = Depends(get_db)):
    from ..db.models import Project
    if not db.query(Project).filter_by(id=project_id).first():
        raise HTTPException(status_code=404, detail="PROJECT_NOT_FOUND")
    return {"ok": True, "data": svc.get_effective(db, project_id)}


@router.patch("/api/projects/{project_id}/params/override")
def patch_override(
    project_id: str,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
):
    try:
        eff = svc.apply_overrides(db, project_id, payload)
    except ValueError as e:
        if "PROJECT_NOT_FOUND" in str(e):
            raise HTTPException(status_code=404, detail="PROJECT_NOT_FOUND")
        raise
    return {"ok": True, "data": eff}
