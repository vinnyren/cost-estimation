from sqlalchemy.orm import Session
from ..core.context import EvaluationContext, ProjectInputs
from ..core.forward import calculate_forward, ForwardInput, FpItem
from ..core.reverse import calculate_reverse, ReverseInput
from ..db.models import Project
from . import params as ps


def run_forward(db: Session, project_id: str, payload: dict) -> dict:
    proj = db.query(Project).filter_by(id=project_id).first()
    if not proj:
        raise ValueError("PROJECT_NOT_FOUND")
    full_params = ps.get_global(db)
    ctx = EvaluationContext.from_dict(
        full_params,
        ProjectInputs(industry=proj.industry, city=proj.city, phase=proj.phase),
    )
    inp = ForwardInput(
        items=[FpItem(us=i["us"]) for i in payload.get("items", [])],
        dev_factor=payload.get("dev_factor", 1.0),
        ops_factor=payload.get("ops_factor", 1.0),
        include_dev=payload.get("include_dev", True),
        include_ops=payload.get("include_ops", False),
        other_cost=payload.get("other_cost", 0.0),
    )
    r = calculate_forward(ctx, inp)
    return r.__dict__


def run_reverse(db: Session, project_id: str, payload: dict) -> dict:
    proj = db.query(Project).filter_by(id=project_id).first()
    if not proj:
        raise ValueError("PROJECT_NOT_FOUND")
    full_params = ps.get_global(db)
    ctx = EvaluationContext.from_dict(
        full_params,
        ProjectInputs(industry=proj.industry, city=proj.city, phase=proj.phase),
    )
    inp = ReverseInput(
        target_total=payload["target_total"],
        other_cost=payload.get("other_cost", 0.0),
        include_ops=payload.get("include_ops", False),
        alpha_dev=payload.get("alpha_dev", 1.0),
        dev_factor=payload.get("dev_factor", 1.0),
        ops_factor=payload.get("ops_factor", 1.0),
    )
    r = calculate_reverse(ctx, inp)
    return r.__dict__
