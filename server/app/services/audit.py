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
    """Insert one audit row. Commits immediately.

    立即 commit 是因为本函数被 AuditMiddleware 在 response 之后调用 —
    那时业务事务已结束，沿用调用方 session 没有意义；独立 commit 也让
    审计写入失败不影响主请求结果（中间件会 swallow 异常）。
    """
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

    游标分页：`before_id` 严格小于（id < before_id），不是 ≤ — 避免上一页
    的边界行重复出现。客户端把本页最后一行（也是 id 最小的那行）的 id
    作为下一次的 before_id 即可。

    与 AuditMiddleware 的关系：写入由中间件完成，读取由本函数完成；两者
    通过 AuditLog 表解耦，本函数对写入路径无任何依赖。
    """
    q = db.query(AuditLog).filter_by(project_id=project_id)
    if before_id is not None:
        q = q.filter(AuditLog.id < before_id)
    return q.order_by(AuditLog.id.desc()).limit(limit).all()
