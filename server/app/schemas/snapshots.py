"""Pydantic schemas for ParamSnapshot endpoints (v2.0 GAP-H, T4).

`scope` is either the literal "global" (snapshot of global params) or a
project_id string (snapshot of a project's effective params, including its
override layer).
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SnapshotCreate(BaseModel):
    scope: str = Field(..., min_length=1, max_length=64)
    label: str | None = Field(None, max_length=200)


class SnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scope: str
    label: str | None
    created_at: datetime
