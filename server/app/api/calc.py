from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schemas.results import CalcForwardRequest, CalcReverseRequest, AllocateRequest
from ..services import calc as svc

router = APIRouter(prefix="/api/calc")


@router.post("/forward")
def forward(payload: CalcForwardRequest, db: Session = Depends(get_db)):
    try:
        result = svc.run_forward(db, payload.project_id, payload.model_dump())
    except ValueError as e:
        raise HTTPException(404, detail={"error": {"code": str(e)}})
    return {"ok": True, "data": result}


@router.post("/reverse")
def reverse(payload: CalcReverseRequest, db: Session = Depends(get_db)):
    try:
        return {"ok": True, "data": svc.run_reverse(db, payload.project_id, payload.model_dump())}
    except ValueError as e:
        code = str(e).split(":")[0]
        raise HTTPException(400, detail={"error": {"code": code, "problem": str(e),
                                                     "fix": "调整目标金额或其他费用"}})


@router.post("/allocate")
def allocate_route(payload: AllocateRequest):
    try:
        return {"ok": True, "data": svc.run_allocate(payload.model_dump())}
    except ValueError as e:
        code = str(e).split(":")[0]
        raise HTTPException(400, detail={"error": {"code": code, "problem": str(e),
                                                     "fix": "解锁部分锁定项或提高 target_us"}})
