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
    measurement_method: Literal[
        "ifpug", "nesma_indicative", "nesma_estimated", "nesma_detailed", "cosmic"
    ] = "nesma_estimated"
    basis_data_ver: str
    # v2.8 — 评估口径：development 开发项目 / enhancement 增强项目。
    assessment_kind: Literal["development", "enhancement"] = "development"
    # v2.9 — 用户在结果页选定的成本档位（P10/P50/P90）— 决定报告导出用哪一档。
    selected_band: Literal["P10", "P50", "P90"] = "P50"
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
    # 编辑设定可改评估方式与项目类型 —— 缺这两项时前端改「正向↔反向」会被静默丢弃。
    mode: Optional[Literal["forward", "reverse"]] = None
    project_type: Optional[Literal["dev_only", "ops_only", "dev_and_ops"]] = None
    assessment_kind: Optional[Literal["development", "enhancement"]] = None
    selected_band: Optional[Literal["P10", "P50", "P90"]] = None
    target_cost: Optional[float] = None
    other_cost: Optional[float] = None
    include_ops: Optional[bool] = None
    alpha_dev: Optional[float] = None
    # v2.0 — per-project 调整因子选择
    factors_dev: Optional[dict] = None
    factors_ops: Optional[dict] = None
    measurement_method: Optional[Literal[
        "ifpug", "nesma_indicative", "nesma_estimated", "nesma_detailed", "cosmic"
    ]] = None


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


# ── v2.7 导出 / 导入 bundle ────────────────────────────────────────────────

from .functions import FunctionPointBase  # noqa: E402


class ParamOverrideItem(BaseModel):
    key: str
    value: str
    reason: Optional[str] = None


class ProjectBundleItem(BaseModel):
    """单个项目的可移植快照 — 不含运行时与历史数据。"""

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
    measurement_method: Literal[
        "ifpug", "nesma_indicative", "nesma_estimated", "nesma_detailed", "cosmic"
    ] = "nesma_estimated"
    basis_data_ver: str
    assessment_kind: Literal["development", "enhancement"] = "development"
    selected_band: Literal["P10", "P50", "P90"] = "P50"
    factors_dev: Optional[dict] = None
    factors_ops: Optional[dict] = None
    param_overrides: list[ParamOverrideItem] = Field(default_factory=list, max_length=500)
    function_points: list[FunctionPointBase] = Field(default_factory=list, max_length=5000)


class ProjectBundle(BaseModel):
    """导出 / 导入的 JSON bundle 顶层结构。"""

    version: str
    exported_at: str
    projects: list[ProjectBundleItem] = Field(..., max_length=200)


class ProjectExportRequest(BaseModel):
    ids: list[str]


class ProjectImportResult(BaseModel):
    imported: int
    project_ids: list[str]
