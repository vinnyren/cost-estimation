from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schemas.params import ParamPatch
from ..services import params as svc

router = APIRouter(prefix="/api/params")


@router.get("/global")
def get_global(db: Session = Depends(get_db)):
    return {"ok": True, "data": svc.get_global(db)}


@router.patch("/global")
def patch_global(payload: ParamPatch, db: Session = Depends(get_db)):
    svc.patch_global(db, payload.key, payload.value)
    return {"ok": True, "data": {"updated": payload.key}}
