from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schemas.functions import (FunctionPointCreate, FunctionPointRead,
                                    FunctionPointPatch, BulkRequest)
from ..services import functions as svc


router = APIRouter(prefix="/api/projects/{project_id}/functions")


def _read(fp):
    return FunctionPointRead.model_validate(fp).model_dump(mode="json")


@router.get("")
def list_all(project_id: str, db: Session = Depends(get_db)):
    return {"ok": True, "data": [_read(fp) for fp in svc.list_for_project(db, project_id)]}


@router.post("", status_code=201)
def create(project_id: str, payload: FunctionPointCreate, db: Session = Depends(get_db)):
    try:
        fp = svc.create(db, project_id, payload)
    except ValueError as e:
        raise HTTPException(404, detail={"error": {"code": str(e)}})
    return {"ok": True, "data": _read(fp)}


@router.patch("/{fp_id}")
def patch_one(project_id: str, fp_id: str, payload: FunctionPointPatch,
               db: Session = Depends(get_db)):
    fp = svc.patch(db, project_id, fp_id, payload)
    if not fp:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND"}})
    return {"ok": True, "data": _read(fp)}


@router.delete("/{fp_id}")
def delete_one(project_id: str, fp_id: str, db: Session = Depends(get_db)):
    if not svc.delete(db, project_id, fp_id):
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND"}})
    return {"ok": True, "data": {"deleted": fp_id}}


@router.post("/bulk", status_code=201)
def bulk(project_id: str, payload: BulkRequest, db: Session = Depends(get_db)):
    try:
        n = svc.bulk_write(db, project_id, payload.items, payload.replace)
    except ValueError as e:
        raise HTTPException(404, detail={"error": {"code": str(e)}})
    return {"ok": True, "data": {"written": n}}


@router.post("/restore")
def restore(project_id: str, version: int, db: Session = Depends(get_db)):
    try:
        n = svc.restore(db, project_id, version)
    except ValueError as e:
        msg = str(e)
        if "PROJECT_NOT_FOUND" in msg:
            raise HTTPException(404, detail={"error": {"code": "PROJECT_NOT_FOUND"}})
        if "SNAPSHOT_NOT_FOUND" in msg:
            raise HTTPException(404, detail={"error": {"code": "SNAPSHOT_NOT_FOUND"}})
        raise
    return {"ok": True, "data": {"restored_version": version, "fp_count": n}}
