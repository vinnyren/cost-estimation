from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..parsers.validator import UploadValidationError
from ..schemas.uploads import UploadRead
from ..services import uploads as svc

router = APIRouter(prefix="/api/projects/{project_id}/uploads")


@router.post("", status_code=201)
async def upload_one(project_id: str, file: UploadFile = File(...),
                      db: Session = Depends(get_db)):
    try:
        rec = await svc.save_and_parse(db, project_id, file)
    except UploadValidationError as e:
        code = str(e).split(":")[0]
        raise HTTPException(400, detail={"error": {"code": code, "problem": str(e),
                                                     "fix": "确认文件类型为 PDF/Word/Excel/MD/TXT 且小于 50MB"}})
    except ValueError as e:
        raise HTTPException(404, detail={"error": {"code": str(e)}})
    return {"ok": True, "data": UploadRead.model_validate(rec).model_dump(mode="json")}


@router.get("")
def list_uploads(project_id: str, db: Session = Depends(get_db)):
    rows = svc.list_for_project(db, project_id)
    return {"ok": True, "data": [UploadRead.model_validate(r).model_dump(mode="json") for r in rows]}


@router.delete("/{upload_id}", status_code=204)
def delete_upload_endpoint(project_id: str, upload_id: int, db: Session = Depends(get_db)):
    """v2.5 — 删除上传记录 + 物理文件。"""
    ok = svc.delete_upload(db, project_id, upload_id)
    if not ok:
        raise HTTPException(404, detail={"error": {"code": "UPLOAD_NOT_FOUND"}})
    return None
