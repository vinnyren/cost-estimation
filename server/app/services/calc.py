from sqlalchemy.orm import Session
from ..core.context import EvaluationContext, ProjectInputs
from ..core.forward import calculate_forward, ForwardInput, FpItem
from ..core.reverse import calculate_reverse, ReverseInput
from ..core.allocator import allocate, AllocatorInput, FpDraft
from ..db.models import Project
from . import params as ps
from . import functions as fs


def _resolve_items(db: Session, project_id: str, payload: dict) -> list[FpItem]:
    """Get FpItem list from payload, or fall back to DB functions for the project.

    Server keeps items optional in schema; if caller does not supply, we read
    every FunctionPoint of the project. This keeps existing API tests (which
    pass items explicitly) working while letting the frontend send only
    project_id.
    """
    raw_items = payload.get("items")
    if raw_items:
        return [FpItem(us=i["us"]) for i in raw_items]
    db_items = fs.list_for_project(db, project_id)
    return [FpItem(us=fp.us) for fp in db_items]


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
        items=_resolve_items(db, project_id, payload),
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


def run_allocate(payload: dict) -> list[dict]:
    drafts = [FpDraft(name=d["name"], weight=d["weight"],
                      locked=d.get("locked", False), locked_us=d.get("locked_us", 0.0))
              for d in payload["drafts"]]
    out = allocate(AllocatorInput(
        target_us=payload["target_us"], drafts=drafts, cf=payload.get("cf", 1.21)))
    return [o.__dict__ for o in out]
