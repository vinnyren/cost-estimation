"""Audit-log service (v2.0 GAP-J, Task T5).

Thin wrapper around AuditLog for the middleware (write) and the GET endpoint
(list with cursor pagination). The middleware must call `write()` *after* the
response has been produced; failures here MUST be swallowed by the caller so
audit-log breakage never bubbles up to the user.
"""
from sqlalchemy.orm import Session

from ..db.models import AuditLog


def write(
    db: Session,
    project_id: str,
    action: str,
    target: str | None = None,
    diff_json: str | None = None,
    actor: str = "user",
) -> AuditLog:
    """Insert one audit row. Commits immediately."""
    log = AuditLog(
        project_id=project_id,
        actor=actor,
        action=action,
        target=target,
        diff_json=diff_json,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def list_for_project(
    db: Session,
    project_id: str,
    limit: int = 100,
    before_id: int | None = None,
) -> list[AuditLog]:
    """Return audit rows for `project_id`, newest first.

    `before_id` enables cursor pagination — pass the smallest id from the
    previous page and the next call yields strictly older rows.
    """
    q = db.query(AuditLog).filter_by(project_id=project_id)
    if before_id is not None:
        q = q.filter(AuditLog.id < before_id)
    return q.order_by(AuditLog.id.desc()).limit(limit).all()
