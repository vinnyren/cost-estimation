from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..schemas.project import ProjectCreate, ProjectRead, ProjectPatch
from ..services import projects as svc

router = APIRouter(prefix="/api/projects")


def _wrap(data):
    return {"ok": True, "data": data}


@router.post("", status_code=201)
def create(payload: ProjectCreate, db: Session = Depends(get_db)):
    p = svc.create(db, payload)
    return _wrap(ProjectRead.model_validate(p).model_dump(mode="json"))


@router.get("")
def list_all(db: Session = Depends(get_db)):
    return _wrap([ProjectRead.model_validate(p).model_dump(mode="json") for p in svc.list_all(db)])


@router.get("/{project_id}")
def get_one(project_id: str, db: Session = Depends(get_db)):
    p = svc.get(db, project_id)
    if not p:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND"}})
    return _wrap(ProjectRead.model_validate(p).model_dump(mode="json"))


@router.patch("/{project_id}")
def patch_one(project_id: str, payload: ProjectPatch, db: Session = Depends(get_db)):
    p = svc.patch(db, project_id, payload)
    if not p:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND"}})
    return _wrap(ProjectRead.model_validate(p).model_dump(mode="json"))


@router.delete("/{project_id}")
def delete_one(project_id: str, db: Session = Depends(get_db)):
    ok = svc.delete(db, project_id)
    if not ok:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND"}})
    return _wrap({"deleted": project_id})
