from pydantic import BaseModel


class FpItemIn(BaseModel):
    us: float


class CalcForwardRequest(BaseModel):
    project_id: str
    items: list[FpItemIn] | None = None
    dev_factor: float = 1.0
    ops_factor: float = 1.0
    include_dev: bool = True
    include_ops: bool = False
    other_cost: float = 0.0


class CalcReverseRequest(BaseModel):
    project_id: str
    target_total: float
    other_cost: float = 0.0
    include_ops: bool = False
    alpha_dev: float = 1.0
    dev_factor: float = 1.0
    ops_factor: float = 1.0


class FpDraftIn(BaseModel):
    name: str
    weight: float
    locked: bool = False
    locked_us: float = 0.0


class AllocateRequest(BaseModel):
    project_id: str
    target_us: float
    cf: float = 1.21
    drafts: list[FpDraftIn]
