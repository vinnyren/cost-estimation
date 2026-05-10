from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..exporters.excel import TemplateBrokenError
from ..services import reports as svc

router = APIRouter(prefix="/api/reports")


@router.get("/excel/{project_id}")
def download_excel(project_id: str, db: Session = Depends(get_db)):
    try:
        out = svc.generate_excel(db, project_id)
    except ValueError as e:
        code = str(e)
        if code == "PROJECT_NOT_FOUND":
            raise HTTPException(404, detail={"error": {"code": code}})
        raise HTTPException(400, detail={"error": {"code": code,
                                                    "problem": code,
                                                    "fix": "至少添加一个 FP 项后重试"}})
    except TemplateBrokenError as e:
        raise HTTPException(500, detail={"error": {"code": "TEMPLATE_BROKEN", "problem": str(e),
                                                    "fix": "重新生成模板：python templates/_make_template.py"}})
    return FileResponse(
        path=str(out),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=out.name)
