from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict


class FunctionPointBase(BaseModel):
    subsystem: Optional[str] = None
    l1_module: Optional[str] = None
    l2_module: Optional[str] = None
    description: Optional[str] = None
    name: Optional[str] = None
    category: Literal["EI", "EO", "EQ", "ILF", "EIF"]
    complexity: Literal["low", "average", "high"]
    ufp: float
    reuse_level: Optional[Literal["low", "high"]] = "low"
    modify_type: Optional[Literal["new", "modify", "delete"]] = "new"
    us: float
    source: Optional[
        Literal["manual", "imported", "ai_extracted", "claude_draft", "allocator"]
    ] = "manual"
    locked: bool = False
    notes: Optional[str] = None
    ord: Optional[int] = None


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
    ufp: Optional[float] = None
    us: Optional[float] = None
    locked: Optional[bool] = None
    notes: Optional[str] = None


class BulkRequest(BaseModel):
    items: list[FunctionPointCreate]
    replace: bool = False  # True 时清空原 FP 后写入；False 时追加
