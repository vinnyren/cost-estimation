from pydantic import BaseModel, ConfigDict
from typing import Literal, Optional
from datetime import datetime

class ProjectCreate(BaseModel):
    name: str
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

class ProjectRead(ProjectCreate):
    id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ProjectPatch(BaseModel):
    name: Optional[str] = None
    phase: Optional[str] = None
    city: Optional[str] = None
    industry: Optional[str] = None
    client: Optional[str] = None
    evaluator: Optional[str] = None
    target_cost: Optional[float] = None
    other_cost: Optional[float] = None
    include_ops: Optional[bool] = None
    alpha_dev: Optional[float] = None
