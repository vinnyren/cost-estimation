"""GET /api/projects/{project_id}/audit (v2.0 GAP-J, Task T5).

只读查询接口。审计写入由 app/middleware/audit.py 在响应阶段隐式完成 —
本路由不负责写。

游标分页约定：客户端首次请求不带 before_id，拿到本页最小 id 后下次以
该 id 作 before_id 传入，服务端返回 id < before_id 的更早记录。limit
默认 100，上限 500。详见 services/audit.py:list_for_project。

鉴权由全局 X-Auth-Token 中间件（deps.py）统一拦截，本路由无需逐路由
Depends。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schemas.audit import AuditOut
from ..services import audit as svc

router = APIRouter(prefix="/api/projects", tags=["audit"])


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
