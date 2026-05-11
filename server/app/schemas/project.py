import json
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Any, Literal, Optional
from datetime import datetime

NAME_MAX = 120

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=NAME_MAX)
    project_type: Literal["dev_only", "ops_only", "dev_and_ops"]
    phase: Literal["budget", "bidding", "planning", "change", "settled"]
    city: str
    industry: str
    client: Optional[str] = None
    evaluator: Optional[str] = None
    mode: Literal["forward", "reverse"]
    target_cost: Optional[float] = None
    other_cost: float = 0
    include_ops: bool = False
    alpha_dev: float = 1.0
    fp_method: Literal["nesma_estimated", "ifpug", "quick"] = "nesma_estimated"
    basis_data_ver: str
    # v2.0 — per-project 调整因子选择（JSON 落盘 factors_dev_json / factors_ops_json）
    factors_dev: Optional[dict] = None
    factors_ops: Optional[dict] = None

class ProjectRead(ProjectCreate):
    id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _hydrate_factors_from_orm(cls, data: Any) -> Any:
        """ORM 用 factors_dev_json (TEXT)，schema 暴露 factors_dev (dict)。

        Pydantic from_attributes 读不到 factors_dev，需要在这里把 JSON 字符串
        解析回 dict。data 是 ORM 实例时把它整体转成 dict 再交给 Pydantic。
        """
        if data is None or isinstance(data, dict):
            return data
        # ORM instance → dict 展开 (只展开列, 不展开 relationship 避免 N+1)
        if hasattr(data, "__table__"):
            out = {c.name: getattr(data, c.name) for c in data.__table__.columns}
            out["factors_dev"] = _safe_json(out.get("factors_dev_json"))
            out["factors_ops"] = _safe_json(out.get("factors_ops_json"))
            return out
        return data


def _safe_json(raw: Any) -> Any:
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None

class ProjectPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=NAME_MAX)
    phase: Optional[str] = None
    city: Optional[str] = None
    industry: Optional[str] = None
    client: Optional[str] = None
    evaluator: Optional[str] = None
    target_cost: Optional[float] = None
    other_cost: Optional[float] = None
    include_ops: Optional[bool] = None
    alpha_dev: Optional[float] = None
    # v2.0 — per-project 调整因子选择
    factors_dev: Optional[dict] = None
    factors_ops: Optional[dict] = None


class ProjectStatsCounts(BaseModel):
    total: int
    draft: int
    in_progress: int
    archived: int
    delivered: int


class ProjectStats(BaseModel):
    counts: ProjectStatsCounts
    monthly_count: int
    monthly_p50_sum: float
    monthly_growth_pct: float
