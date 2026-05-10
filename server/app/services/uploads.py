import uuid
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..db.models import Upload, Project
from ..parsers.validator import validate_upload
from ..parsers.pdf import parse_pdf
from ..parsers.docx import parse_docx
from ..parsers.xlsx import parse_xlsx


def _uploads_dir(project_id: str) -> Path:
    # settings.upload_dir 在 Settings._derive_paths 中派生为 data_dir/uploads
    # （除非 COST_UPLOAD_DIR 显式设置）。
    assert settings.upload_dir is not None
    p = settings.upload_dir / project_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _parsed_dir(project_id: str) -> Path:
    assert settings.parsed_dir is not None
    p = settings.parsed_dir / project_id
    p.mkdir(parents=True, exist_ok=True)
    return p


async def save_and_parse(db: Session, project_id: str, file: UploadFile) -> Upload:
    """保存上传文件 + 验证 + 解析为纯文本（写入磁盘，DB 仅存路径）。

    Disk paths are prefixed with a per-upload uuid so two uploads with the same
    filename (or same basename + different extensions) cannot silently overwrite
    each other on disk or in the parsed-text mirror — see ISSUE-010 round 2 QA.
    """
    proj = db.query(Project).filter_by(id=project_id).first()
    if not proj:
        raise ValueError("PROJECT_NOT_FOUND")

    original_name = file.filename or "untitled"
    upload_uid = uuid.uuid4().hex[:12]
    safe_name = f"{upload_uid}__{original_name}"

    target = _uploads_dir(project_id) / safe_name
    content = await file.read()
    target.write_bytes(content)

    try:
        info = validate_upload(target, original_name=original_name)
    except Exception:
        # Validation failed — don't leave the rejected blob on disk. The caller
        # propagates the exception to the API layer where it becomes a 400.
        target.unlink(missing_ok=True)
        raise

    from fastapi.concurrency import run_in_threadpool
    text = ""
    if info["ext"] == ".pdf":
        doc = await run_in_threadpool(parse_pdf, target)
        text = doc.text
    elif info["ext"] == ".docx":
        doc = await run_in_threadpool(parse_docx, target)
        text = doc.text
    elif info["ext"] == ".xlsx":
        sheets = await run_in_threadpool(parse_xlsx, target)
        text = "\n\n".join(
            f"=== Sheet: {s.name} ===\n" + "\n".join(
                [" | ".join(s.headers)] + [" | ".join(str(c) for c in r) for r in s.rows])
            for s in sheets)
    else:
        text = target.read_text(encoding="utf-8", errors="ignore")

    parsed_path = _parsed_dir(project_id) / f"{upload_uid}__{Path(original_name).stem}.txt"
    parsed_path.write_text(text, encoding="utf-8")

    rec = Upload(
        project_id=project_id,
        filename=original_name,
        size=info["size"],
        filetype=info["ext"].lstrip("."),
        parsed_text_path=str(parsed_path))
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def list_for_project(db: Session, project_id: str) -> list[Upload]:
    return db.query(Upload).filter_by(project_id=project_id).order_by(Upload.id.desc()).all()
