"""GET /api/projects/{project_id}/audit (v2.0 GAP-J, Task T5).

Writes happen implicitly via app/middleware/audit.py — this router only
exposes read access. Auth is enforced by the global X-Auth-Token middleware
(see deps.py), so no per-route Depends is required.
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
