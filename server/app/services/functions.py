import uuid, json
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..db.models import FunctionPoint, FPSnapshot, Project, Result
from ..schemas.functions import FunctionPointCreate, FunctionPointPatch
from ..core.ifpug import classify_complexity
from ..core.sizing import get_method


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


def list_snapshots(db: Session, project_id: str) -> list[dict]:
    """Return snapshot metadata (no payload) so the UI can render a history
    list cheaply. snapshot_json itself can be large — load it only when the
    user actually invokes restore."""
    rows = (
        db.query(FPSnapshot)
        .filter_by(project_id=project_id)
        .order_by(FPSnapshot.id.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "version": s.version,
            "snapshot_at": s.snapshot_at.isoformat() if s.snapshot_at else None,
            "reason": s.reason,
            # 同一 project 同一 version 可能有多条快照（restore 也会再快照），
            # 这里一并 expose；前端按时间降序展示即可。
            "fp_count": len(json.loads(s.snapshot_json) or []),
        }
        for s in rows
    ]


def _apply_sizing(method: str, data: dict) -> dict:
    """按项目 measurement_method 重算 ufp / us，并（部分方法）重算 complexity。

    返回新 dict，不就地修改 data（不可变原则）。
    """
    try:
        method_obj = get_method(method)
    except ValueError:
        return data  # 未知方法：退化到原样返回

    size = method_obj.compute_entry_size(data)

    if method_obj.input_model == "ifpug_style":
        if method in ("ifpug", "nesma_detailed"):
            cat = data.get("category")
            det, ret, ftr = data.get("det"), data.get("ret"), data.get("ftr")
            has_input = (
                (cat in ("ILF", "EIF") and det is not None and ret is not None)
                or (cat in ("EI", "EO", "EQ") and det is not None and ftr is not None)
            )
            if has_input:
                complexity = classify_complexity(cat, det, ret, ftr)
            else:
                # 无足够 DET/RET/FTR 时：保留 data 中已有的 complexity（如
                # PATCH 时显式传入的值），无则退回 "average"。
                complexity = data.get("complexity") or "average"
        elif method == "nesma_estimated":
            complexity = "average"
        else:  # nesma_indicative：保留原 complexity
            complexity = data.get("complexity", "average")
        return {**data, "complexity": complexity, "ufp": size, "us": size}

    # cosmic：不动 complexity；写入 ufp/us（CFP 值）
    return {**data, "ufp": size, "us": size}


def create(db: Session, project_id: str, payload: FunctionPointCreate) -> FunctionPoint:
    proj = db.query(Project).filter_by(id=project_id).first()
    if not proj:
        raise ValueError("PROJECT_NOT_FOUND")
    version = _next_version(db, project_id)
    method = getattr(proj, "measurement_method", "nesma_estimated") or "nesma_estimated"
    data = _apply_sizing(method, payload.model_dump())
    fp = FunctionPoint(id=f"fp-{uuid.uuid4().hex[:12]}",
                        project_id=project_id, version=version,
                        **data)
    db.add(fp); db.commit(); db.refresh(fp)
    _mark_results_stale(db, project_id)
    return fp


def patch(db: Session, project_id: str, fp_id: str, payload: FunctionPointPatch) -> FunctionPoint | None:
    fp = db.query(FunctionPoint).filter_by(id=fp_id, project_id=project_id).first()
    if not fp:
        return None
    updates = payload.model_dump(exclude_unset=True)
    # Merge existing column values with patch updates, then recompute sizing
    # fields (complexity/ufp/us) per the project's measurement method.
    merged = {c.name: getattr(fp, c.name) for c in fp.__table__.columns}
    merged.update(updates)
    proj_obj = db.query(Project).filter_by(id=project_id).first()
    if proj_obj is None:
        return None
    method = getattr(proj_obj, "measurement_method", "nesma_estimated") or "nesma_estimated"
    merged = _apply_sizing(method, merged)
    for k, v in updates.items():
        setattr(fp, k, v)
    for k in ("complexity", "ufp", "us"):
        if merged.get(k) is not None:
            setattr(fp, k, merged[k])
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

    # 当 replace=True 且 DB 已有功能点（可能是通过 POST /functions 单体
    # create 或 PATCH 添加的），先做一道 pre-replace 快照。否则那些通过
    # create/patch 路径写入但从未触发过 bulk_write 的行，会被 replace
    # 永久销毁、且不在任何快照里、无法 restore。
    # /review round 5 adversarial discovery (ISSUE-024)。
    # 用 current_max 作为快照版本（这些行的真实 version）；若该 version
    # 上已经有快照（比如来自上一次 bulk_write 的 post-write 快照）则不再
    # 重复写，避免与新的 UNIQUE(project_id, version) 约束冲突。
    if replace:
        current_max = (
            db.query(func.max(FunctionPoint.version))
            .filter_by(project_id=project_id)
            .scalar()
        )
        if current_max is not None:
            existing_snap = (
                db.query(FPSnapshot)
                .filter_by(project_id=project_id, version=current_max)
                .first()
            )
            if not existing_snap:
                _snapshot(db, project_id, current_max, reason="pre_bulk_replace")

    next_v = _next_version(db, project_id)

    if replace:
        db.query(FunctionPoint).filter_by(project_id=project_id).delete()
        db.commit()

    for it in items:
        db.add(FunctionPoint(id=f"fp-{uuid.uuid4().hex[:12]}",
                              project_id=project_id, version=next_v,
                              **it.model_dump()))
    db.commit()

    # Snapshot AFTER the write so snapshot v=N captures the state OF version N
    # (the data restore(version=N) will read back). Storing the post-state
    # avoids the off-by-one trap where "restore v=1" otherwise rolls back to
    # whatever existed BEFORE v=1, defeating the point of versioning.
    _snapshot(db, project_id, next_v, reason=reason)
    _mark_results_stale(db, project_id)
    return len(items)


def accept_drafts(db: Session, project_id: str) -> int:
    """把项目内所有 source='claude_draft' 的功能点采纳为 'ai_extracted'。

    改动前先存一次 FP 快照（reason='accept_drafts'）便于回退 —— 快照版本用
    当前最大 version，与 bulk_write 的 pre-replace 快照同一约定，避免与
    UNIQUE(project_id, version) 冲突时跳过重复写。
    项目不存在抛 PROJECT_NOT_FOUND；无 claude_draft 行时返回 0（非错误，
    且不写快照 —— 无改动无需快照）。
    """
    if not db.query(Project).filter_by(id=project_id).first():
        raise ValueError("PROJECT_NOT_FOUND")

    drafts = (
        db.query(FunctionPoint)
        .filter_by(project_id=project_id, source="claude_draft")
        .all()
    )
    if not drafts:
        return 0

    current_max = (
        db.query(func.max(FunctionPoint.version))
        .filter_by(project_id=project_id)
        .scalar()
    )
    if current_max is not None:
        existing_snap = (
            db.query(FPSnapshot)
            .filter_by(project_id=project_id, version=current_max)
            .first()
        )
        if not existing_snap:
            _snapshot(db, project_id, current_max, reason="accept_drafts")

    for fp in drafts:
        fp.source = "ai_extracted"
    db.commit()
    _mark_results_stale(db, project_id)
    return len(drafts)


def restore(db: Session, project_id: str, version: int) -> int:
    """Replay an earlier FPSnapshot back into function_points.

    Steps: verify project + snapshot, snapshot the *current* state (so the
    restore itself is undoable), wipe current rows, replay the snapshot's
    payload, mark dependent results stale. Returns the number of FP rows
    written.
    """
    if not db.query(Project).filter_by(id=project_id).first():
        raise ValueError("PROJECT_NOT_FOUND")
    # 同 (project_id, version) 可能有多条快照（无 UNIQUE 约束 + 重放路径）。
    # 选最新写入的一条（id 最大）作为权威版本，避免 .first() 在重复键上的
    # 不确定行为。/review round 5 adversarial 发现。
    snap = (
        db.query(FPSnapshot)
        .filter_by(project_id=project_id, version=version)
        .order_by(FPSnapshot.id.desc())
        .first()
    )
    if not snap:
        raise ValueError("SNAPSHOT_NOT_FOUND")
    # Take an "undo" snapshot of the live state before mutation. Skips the
    # snapshot when there are no current rows (nothing to preserve).
    next_v = _next_version(db, project_id)
    if db.query(FunctionPoint).filter_by(project_id=project_id).first():
        _snapshot(db, project_id, next_v, reason=f"pre_restore_to_v{version}")

    db.query(FunctionPoint).filter_by(project_id=project_id).delete()
    db.commit()

    payload = json.loads(snap.snapshot_json)
    written = 0
    for row in payload:
        # Snapshots store the full row including id/created_at/etc. Drop the
        # id so a fresh one is minted (avoids PK collisions if a row with the
        # same id was created elsewhere) and let SQLAlchemy ignore unknown
        # keys.
        cols = {c.name for c in FunctionPoint.__table__.columns}
        clean = {k: v for k, v in row.items() if k in cols and k != "id"}
        # version inside the row reflects when it was originally written;
        # keep that as historical tag, but ensure project_id matches.
        clean["project_id"] = project_id
        db.add(FunctionPoint(id=f"fp-{uuid.uuid4().hex[:12]}", **clean))
        written += 1
    db.commit()
    _mark_results_stale(db, project_id)
    return written
