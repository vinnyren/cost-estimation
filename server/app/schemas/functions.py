import math
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class FunctionPointBase(BaseModel):
    subsystem: Optional[str] = None
    l1_module: Optional[str] = None
    l2_module: Optional[str] = None
    description: Optional[str] = None
    name: Optional[str] = None
    category: Literal["EI", "EO", "EQ", "ILF", "EIF"]
    complexity: Literal["low", "average", "high"]
    # ufp / us 必须 ≥ 0 — 负值会让 forward calc 产出负造价，业务无意义
    # （ISSUE-021 round 3 QA：曾有 ufp=-5 通过 schema → cost_dev_yuan 也是负）
    ufp: float = Field(ge=0)
    reuse_level: Optional[Literal["low", "high"]] = "low"
    modify_type: Optional[Literal["new", "modify", "delete"]] = "new"
    us: float = Field(ge=0)
    # v2.0 T6 — "copied" 标记由 /projects/{id}/copy 写入，提示该 FP 来源于另一个
    # 项目的副本（与 manual 区分以便日后审计/统计）。
    source: Optional[
        Literal["manual", "imported", "ai_extracted", "claude_draft", "allocator", "copied"]
    ] = "manual"
    locked: bool = False
    notes: Optional[str] = None
    ord: Optional[int] = None

    @field_validator("ufp", "us")
    @classmethod
    def _finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("must be a finite number (NaN/Inf rejected)")
        return v


class FunctionPointCreate(FunctionPointBase):
    pass


class FunctionPointRead(FunctionPointBase):
    id: str
    project_id: str
    version: int
    model_config = ConfigDict(from_attributes=True)


class FunctionPointPatch(BaseModel):
    subsystem: Optional[str] = None
    l1_module: Optional[str] = None
    l2_module: Optional[str] = None
    description: Optional[str] = None
    name: Optional[str] = None
    category: Optional[Literal["EI", "EO", "EQ", "ILF", "EIF"]] = None
    complexity: Optional[Literal["low", "average", "high"]] = None
    ufp: Optional[float] = Field(default=None, ge=0)
    us: Optional[float] = Field(default=None, ge=0)
    locked: Optional[bool] = None
    notes: Optional[str] = None

    @field_validator("ufp", "us")
    @classmethod
    def _finite_optional(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not math.isfinite(v):
            raise ValueError("must be a finite number (NaN/Inf rejected)")
        return v


class BulkRequest(BaseModel):
    items: list[FunctionPointCreate]
    replace: bool = False  # True 时清空原 FP 后写入；False 时追加
