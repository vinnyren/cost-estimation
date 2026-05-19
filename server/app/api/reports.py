from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services import reports as svc

router = APIRouter(prefix="/api/reports")


@router.get("/excel/{project_id}")
def download_excel(
    project_id: str,
    band: Optional[Literal["P10", "P50", "P90"]] = None,
    db: Session = Depends(get_db),
):
    try:
        out = svc.generate_excel(db, project_id, band=band)
    except ValueError as e:
        code = str(e).split(":")[0]
        if code == "PROJECT_NOT_FOUND":
            raise HTTPException(404, detail={"error": {"code": code}})
        raise HTTPException(400, detail={"error": {"code": code,
                                                    "problem": str(e),
                                                    "fix": "至少添加一个 FP 项后重试"}})
    return FileResponse(
        path=str(out),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=out.name)
