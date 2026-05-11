"""Pydantic schemas for ParamSnapshot endpoints (v2.0 GAP-H, T4).

`scope` is either the literal "global" (snapshot of global params) or a
project_id string (snapshot of a project's effective params, including its
override layer).
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SnapshotCreate(BaseModel):
    # "global" → 快照全局参数；其他值 → project_id（快照该项目 effective params）
    scope: str = Field(..., min_length=1, max_length=64)
    # 用户可读备注（"上线前基准 v1.0" 等），可空。max 200 防滥用
    label: str | None = Field(None, max_length=200)


class SnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int                # 主键，也是 restore/delete 的 path param
    scope: str             # 同上：'global' 或 project_id
    label: str | None      # 同上：可空
    created_at: datetime   # 服务端时间戳；列表按此 desc 排序
