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
    """冻结当前 effective_params 为一份快照。

    scope="global" 时快照全局参数；scope=<project_id> 时快照该项目的
    effective params（含 override 层）。返回 201 + SnapshotOut。
    """
    snap = svc.create_snapshot(db, payload.scope, payload.label)
    return _wrap(SnapshotOut.model_validate(snap).model_dump(mode="json"))


@router.get("")
def list_(
    scope: str | None = None, db: Session = Depends(get_db)
) -> dict:
    """列出快照（可选按 scope 过滤）。

    未传 scope 时返回所有 scope 的快照；用于"全局快照"+"项目快照"
    管理面统一拉取。结果按 created_at desc，由 service 层保证。
    """
    rows = svc.list_snapshots(db, scope)
    return _wrap(
        [SnapshotOut.model_validate(r).model_dump(mode="json") for r in rows]
    )


@router.post("/{snap_id}/restore")
def restore(snap_id: int, db: Session = Depends(get_db)) -> dict:
    """把指定快照回灌为当前 effective params，返回回灌后的 effective。

    错误码：
    - SNAPSHOT_NOT_FOUND：快照 id 不存在。
    - PROJECT_NOT_FOUND：快照 scope 指向的项目已被删除（孤儿快照）。
    """
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
    """删除一份快照。成功返回 204（无 body）；不存在返回 SNAPSHOT_NOT_FOUND。"""
    try:
        svc.delete_snapshot(db, snap_id)
    except ValueError as e:
        if "SNAPSHOT_NOT_FOUND" in str(e):
            raise HTTPException(
                404, detail={"error": {"code": "SNAPSHOT_NOT_FOUND"}}
            )
        raise
    return Response(status_code=204)
