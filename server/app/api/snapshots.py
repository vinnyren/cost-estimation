"""ParamSnapshot HTTP surface (v2.0 GAP-H, T4).

Four endpoints: POST create / GET list / POST {id}/restore / DELETE {id}.
Auth is enforced by the global X-Auth-Token middleware (see deps.py), so we
don't add per-route Depends here.
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schemas.snapshots import SnapshotCreate, SnapshotOut
from ..services import snapshots as svc

router = APIRouter(prefix="/api/params/snapshots", tags=["snapshots"])


def _wrap(data):
    return {"success": True, "data": data, "error": None}


@router.post("", status_code=201)
def create(payload: SnapshotCreate, db: Session = Depends(get_db)) -> dict:
    snap = svc.create_snapshot(db, payload.scope, payload.label)
    return _wrap(SnapshotOut.model_validate(snap).model_dump(mode="json"))


@router.get("")
def list_(
    scope: str | None = None, db: Session = Depends(get_db)
) -> dict:
    rows = svc.list_snapshots(db, scope)
    return _wrap(
        [SnapshotOut.model_validate(r).model_dump(mode="json") for r in rows]
    )


@router.post("/{snap_id}/restore")
def restore(snap_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        eff = svc.restore_snapshot(db, snap_id)
    except ValueError as e:
        msg = str(e)
        if "SNAPSHOT_NOT_FOUND" in msg:
            raise HTTPException(
                404, detail={"error": {"code": "SNAPSHOT_NOT_FOUND"}}
            )
        if "PROJECT_NOT_FOUND" in msg:
            raise HTTPException(
                404, detail={"error": {"code": "PROJECT_NOT_FOUND"}}
            )
        raise
    return _wrap(eff)


@router.delete("/{snap_id}", status_code=204)
def delete(snap_id: int, db: Session = Depends(get_db)) -> Response:
    try:
        svc.delete_snapshot(db, snap_id)
    except ValueError as e:
        if "SNAPSHOT_NOT_FOUND" in str(e):
            raise HTTPException(
                404, detail={"error": {"code": "SNAPSHOT_NOT_FOUND"}}
            )
        raise
    return Response(status_code=204)
