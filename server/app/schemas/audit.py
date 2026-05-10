"""Pydantic schemas for the audit-log surface (v2.0 GAP-J, Task T5)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditOut(BaseModel):
    id: int
    project_id: str
    ts: datetime
    actor: str | None
    action: str
    target: str | None
    diff_json: str | None

    model_config = ConfigDict(from_attributes=True)
