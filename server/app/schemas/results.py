import math
from pydantic import BaseModel, Field, field_validator


def _check_finite(v: float, allow_zero: bool = True) -> float:
    """Reject NaN/Inf so a stray "NaN" payload becomes a Pydantic 422 instead
    of an unhandled ZeroDivision/NaN propagation that surfaces as 500
    (ISSUE-020 round 3 QA)."""
    if not math.isfinite(v):
        raise ValueError("must be a finite number (NaN/Inf rejected)")
    return v


class FpItemIn(BaseModel):
    us: float = Field(ge=0)

    @field_validator("us")
    @classmethod
    def _f(cls, v: float) -> float:
        return _check_finite(v)


class CalcForwardRequest(BaseModel):
    project_id: str
    items: list[FpItemIn] | None = None
    dev_factor: float = 1.0
    ops_factor: float = 1.0
    include_dev: bool = True
    include_ops: bool = False
    other_cost: float = Field(default=0.0, ge=0)

    @field_validator("dev_factor", "ops_factor", "other_cost")
    @classmethod
    def _f(cls, v: float) -> float:
        return _check_finite(v)


class CalcReverseRequest(BaseModel):
    project_id: str
    # 反算目标必须 > 0 — 业务上「目标造价 0 元」无意义。core/reverse.py 内部
    # 仍有 BUDGET_NEGATIVE 守护，这里 schema 层先拒一道。
    target_total: float = Field(gt=0)
    other_cost: float = Field(default=0.0, ge=0)
    include_ops: bool = False
    alpha_dev: float = Field(default=1.0, gt=0)
    dev_factor: float = Field(default=1.0, gt=0)
    ops_factor: float = Field(default=1.0, gt=0)

    @field_validator("target_total", "other_cost", "alpha_dev",
                     "dev_factor", "ops_factor")
    @classmethod
    def _f(cls, v: float) -> float:
        return _check_finite(v)


class FpDraftIn(BaseModel):
    name: str
    weight: float = Field(ge=0)
    locked: bool = False
    locked_us: float = Field(default=0.0, ge=0)

    @field_validator("weight", "locked_us")
    @classmethod
    def _f(cls, v: float) -> float:
        return _check_finite(v)


class AllocateRequest(BaseModel):
    project_id: str
    target_us: float = Field(ge=0)
    cf: float = Field(default=1.21, gt=0)
    # v2.4 review fix: 至少 1 个模块 — 空 drafts 无意义且会返回 100% 误差
    drafts: list[FpDraftIn] = Field(min_length=1)

    @field_validator("target_us", "cf")
    @classmethod
    def _f(cls, v: float) -> float:
        return _check_finite(v)
