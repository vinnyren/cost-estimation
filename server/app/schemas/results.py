from pydantic import BaseModel


class FpItemIn(BaseModel):
    us: float


class CalcForwardRequest(BaseModel):
    project_id: str
    items: list[FpItemIn]
    dev_factor: float = 1.0
    ops_factor: float = 1.0
    include_dev: bool = True
    include_ops: bool = False
    other_cost: float = 0.0
