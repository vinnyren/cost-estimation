from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schemas.results import CalcForwardRequest
from ..services import calc as svc

router = APIRouter(prefix="/api/calc")


@router.post("/forward")
def forward(payload: CalcForwardRequest, db: Session = Depends(get_db)):
    try:
        result = svc.run_forward(db, payload.project_id, payload.model_dump())
    except ValueError as e:
        raise HTTPException(404, detail={"error": {"code": str(e)}})
    return {"ok": True, "data": result}
