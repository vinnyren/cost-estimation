"""审计日志只读查询接口。

- GET /api/projects/{project_id}/audit — 项目作用域时间线（v2.0 GAP-J）
- GET /api/audit                       — 全局跨项目聚合时间线（v2.7）

审计写入由 app/middleware/audit.py 在响应阶段隐式完成 — 本路由不负责写。

游标分页约定：客户端首次请求不带 before_id，拿到本页最小 id 后下次以
该 id 作 before_id 传入，服务端返回 id < before_id 的更早记录。limit
默认 100，上限 500。详见 services/audit.py。

鉴权由全局 X-Auth-Token 中间件（deps.py）统一拦截，本路由无需逐路由
Depends。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schemas.audit import AuditGlobalOut, AuditOut
from ..services import audit as svc

router = APIRouter(prefix="/api/projects", tags=["audit"])
# 全局端点用独立 router，prefix 不能落在 /api/projects 下 —— 否则会被
# /{project_id}/audit 之外的项目级路由语义混淆，且 main.py 注册更清晰。
global_router = APIRouter(prefix="/api", tags=["audit"])


@router.get("/{project_id}/audit")
def list_audit(
    project_id: str,
    limit: int = Query(100, ge=1, le=500),
    before_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
) -> dict:
    rows = svc.list_for_project(db, project_id, limit, before_id)
    return {
        "success": True,
        "data": [AuditOut.model_validate(r).model_dump(mode="json") for r in rows],
        "error": None,
    }


@global_router.get("/audit")
def list_audit_global(
    limit: int = Query(100, ge=1, le=500),
    before_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
) -> dict:
    pairs = svc.list_global(db, limit, before_id)
    data = [
        AuditGlobalOut(
            id=log.id,
            project_id=log.project_id,
            project_name=project_name,
            ts=log.ts,
            actor=log.actor,
            action=log.action,
            target=log.target,
            diff_json=log.diff_json,
        ).model_dump(mode="json")
        for log, project_name in pairs
    ]
    return {"success": True, "data": data, "error": None}
