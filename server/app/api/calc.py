from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schemas.results import CalcForwardRequest, CalcReverseRequest, AllocateRequest
from ..services import calc as svc

router = APIRouter(prefix="/api/calc")


@router.post("/forward")
def forward(payload: CalcForwardRequest, db: Session = Depends(get_db)):
    try:
        # exclude_unset：让 service 能区分"用户没传 dev_factor"（→ 走 project
        # factors_dev_json 派生）vs "用户显式传了 1.0"（→ 不派生，直接用）。
        result = svc.run_forward(
            db, payload.project_id, payload.model_dump(exclude_unset=True)
        )
    except ValueError as e:
        msg = str(e)
        code = msg.split(":")[0]
        # PROJECT_NOT_FOUND → 404；其他业务可恢复错误（如 NO_FUNCTION_POINTS）→ 422
        if code == "PROJECT_NOT_FOUND":
            raise HTTPException(404, detail={"error": {"code": code}})
        raise HTTPException(
            422,
            detail={
                "error": {
                    "code": code,
                    "problem": msg,
                    "fix": "请先在 FP 编辑屏添加功能点，或上传文档让 AI 提取",
                }
            },
        )
    return {"ok": True, "data": result}


@router.post("/reverse")
def reverse(payload: CalcReverseRequest, db: Session = Depends(get_db)):
    try:
        return {
            "ok": True,
            "data": svc.run_reverse(
                db,
                payload.project_id,
                payload.model_dump(exclude_unset=True),
            ),
        }
    except ValueError as e:
        code = str(e).split(":")[0]
        raise HTTPException(400, detail={"error": {"code": code, "problem": str(e),
                                                     "fix": "调整目标金额或其他费用"}})


@router.post("/allocate")
def allocate_route(payload: AllocateRequest, db: Session = Depends(get_db)):
    try:
        return {
            "ok": True,
            "data": svc.run_allocate(db, payload.project_id, payload.model_dump()),
        }
    except ValueError as e:
        code = str(e).split(":")[0]
        if code == "PROJECT_NOT_FOUND":
            raise HTTPException(404, detail={"error": {"code": code}})
        raise HTTPException(400, detail={"error": {"code": code, "problem": str(e),
                                                     "fix": "解锁部分锁定项或提高 target_us"}})
