"""ParamSnapshot 服务层 — 创建 / 列出 / restore / delete (v2.0 GAP-H, T4).

存储模型：每个 ParamSnapshot 行携带一份 effective_params 的 JSON 快照与一
个 scope（"global" 或 project_id）。restore 时把 payload 还原成 leaf-by-leaf
的 PATCH，让现有的 patch_global / apply_overrides 校验通道（_path_resolves_to_leaf）
拒掉那些已经不再属于权威树的孤儿 key（例如 CSBMK 版本升级后被删的字段）。

注意：snapshot payload 来自 get_effective()，而后者会附带一个 "overrides"
辅助字段供前端 UI 显示「已覆盖」徽标 — 它不属于参数树本身，所以入库前必
须剥掉，否则 restore 会把它的子路径当作 leaf 喂给 patch_global / apply_overrides
被 INVALID_PARAM_KEY 拒掉。
"""
import json
from copy import deepcopy
from typing import Any

from sqlalchemy.orm import Session

from ..db.models import ParamOverride, ParamSnapshot, Result
from . import params as ps


def _capture_payload(db: Session, scope: str) -> dict[str, Any]:
    """Build the snapshot payload for a given scope.

    For "global" we read effective with no project (so no overrides layer),
    for project scopes we read effective with overrides included. In both
    cases the auxiliary "overrides" map is stripped — it's a UI affordance,
    not a parameter."""
    if scope == "global":
        eff = ps.get_effective(db, project_id=None)  # type: ignore[arg-type]
    else:
        eff = ps.get_effective(db, project_id=scope)
    payload = deepcopy(eff)
    payload.pop("overrides", None)
    return payload


def create_snapshot(
    db: Session, scope: str, label: str | None = None
) -> ParamSnapshot:
    payload = _capture_payload(db, scope)
    snap = ParamSnapshot(
        scope=scope,
        label=label,
        payload_json=json.dumps(payload, ensure_ascii=False),
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def list_snapshots(
    db: Session, scope: str | None = None
) -> list[ParamSnapshot]:
    q = db.query(ParamSnapshot)
    if scope:
        q = q.filter_by(scope=scope)
    return q.order_by(ParamSnapshot.id.desc()).all()


def get_snapshot(db: Session, snap_id: int) -> ParamSnapshot | None:
    return db.query(ParamSnapshot).filter_by(id=snap_id).first()


def restore_snapshot(db: Session, snap_id: int) -> dict[str, Any]:
    """Replay a snapshot's payload back into ParamGlobal / ParamOverride.

    global scope:
      - reset global params back to seed first (so any leaves that vanished
        from the snapshot get cleared), then PATCH each captured leaf.
    project scope:
      - drop all existing ParamOverride rows for that project, then
        apply_overrides with the captured (path, value) map.

    Leaves whose path no longer resolves in the current canonical tree are
    silently dropped (CSBMK version drift). Result rows for the affected
    project are marked stale.
    """
    snap = get_snapshot(db, snap_id)
    if not snap:
        raise ValueError("SNAPSHOT_NOT_FOUND")
    payload = json.loads(snap.payload_json)
    payload.pop("overrides", None)  # defense — older snapshots may have it
    leaves = ps._leaf_paths(payload)

    if snap.scope == "global":
        ps.reset_global(db)
        for path, value in leaves:
            try:
                ps.patch_global(db, path, value)
            except ValueError:
                # leaf no longer in canonical tree (productivity_dev shape
                # mismatch after _raw_to_flat projection, or CSBMK drift)
                continue
        return _capture_payload(db, "global")

    # project scope — wipe overrides then re-apply
    db.query(ParamOverride).filter_by(project_id=snap.scope).delete()
    db.commit()
    valid_items: dict[str, Any] = {}
    raw_eff = ps._raw_to_flat(ps.get_global(db))
    for path, value in leaves:
        if ps._path_resolves_to_leaf(raw_eff, path):
            valid_items[path] = value
    if valid_items:
        try:
            ps.apply_overrides(db, snap.scope, valid_items)
        except ValueError:
            # PROJECT_NOT_FOUND or similar — propagate cleanly to caller
            raise
    db.query(Result).filter_by(project_id=snap.scope).update(
        {Result.is_stale: True}
    )
    db.commit()
    return _capture_payload(db, snap.scope)


def delete_snapshot(db: Session, snap_id: int) -> None:
    snap = get_snapshot(db, snap_id)
    if not snap:
        raise ValueError("SNAPSHOT_NOT_FOUND")
    db.delete(snap)
    db.commit()
