"""v2.2 — AiTask Pydantic schemas."""
from pydantic import BaseModel, ConfigDict
from typing import Literal, Optional
from datetime import datetime


class AiTaskCreate(BaseModel):
    project_id: str
    kind: Literal["extract", "allocate", "reverse_fill"]


class AiTaskUpdate(BaseModel):
    status: Optional[Literal["queued", "running", "done", "failed"]] = None
    progress_pct: Optional[float] = None
    stage_log_append: Optional[str] = None
    output_json: Optional[str] = None
    error_message: Optional[str] = None


class AiTaskRead(BaseModel):
    id: str
    project_id: str
    kind: str
    status: str
    progress_pct: float
    stage_log: str
    output_json: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
