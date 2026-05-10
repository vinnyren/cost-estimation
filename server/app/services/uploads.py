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
    """保存上传文件 + 验证 + 解析为纯文本（写入磁盘，DB 仅存路径）"""
    proj = db.query(Project).filter_by(id=project_id).first()
    if not proj:
        raise ValueError("PROJECT_NOT_FOUND")

    # 保存到磁盘
    target = _uploads_dir(project_id) / (file.filename or "untitled")
    content = await file.read()
    target.write_bytes(content)

    # 验证
    info = validate_upload(target, original_name=file.filename or "")

    # 解析（同步 IO，但走 worker 线程不阻塞 event loop）
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

    parsed_path = _parsed_dir(project_id) / (target.stem + ".txt")
    parsed_path.write_text(text, encoding="utf-8")

    rec = Upload(
        project_id=project_id,
        filename=file.filename or "",
        size=info["size"],
        filetype=info["ext"].lstrip("."),
        parsed_text_path=str(parsed_path))
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def list_for_project(db: Session, project_id: str) -> list[Upload]:
    return db.query(Upload).filter_by(project_id=project_id).order_by(Upload.id.desc()).all()
