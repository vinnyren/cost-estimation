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

    # 存相对路径（相对 settings.parsed_dir），让 COST_DATA_DIR 迁移不会让
    # 历史 upload 记录变成 dangling 绝对路径。读取时用 resolve_parsed_path
    # 还原为当前 data_dir 下的绝对路径。/review round 5 (ISSUE-026).
    assert settings.parsed_dir is not None
    rel_parsed = str(parsed_path.relative_to(settings.parsed_dir))

    rec = Upload(
        project_id=project_id,
        filename=original_name,
        size=info["size"],
        filetype=info["ext"].lstrip("."),
        parsed_text_path=rel_parsed)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def resolve_parsed_path(rec: Upload) -> Path:
    """Read-side helper: turn the stored relative parsed_text_path back into
    an absolute Path under the current settings.parsed_dir. Tolerant of legacy
    rows that may still hold an absolute path."""
    assert settings.parsed_dir is not None
    stored = rec.parsed_text_path or ""
    p = Path(stored)
    if p.is_absolute():
        return p
    return settings.parsed_dir / stored


def list_for_project(db: Session, project_id: str) -> list[Upload]:
    return db.query(Upload).filter_by(project_id=project_id).order_by(Upload.id.desc()).all()


def get_upload(db: Session, project_id: str, upload_id: int) -> Upload | None:
    return db.query(Upload).filter_by(id=upload_id, project_id=project_id).first()


def read_parsed_text(rec: Upload) -> str | None:
    """读取 upload 的预解析纯文本；文件不存在返回 None。"""
    fp = resolve_parsed_path(rec)
    if not fp.exists():
        return None
    return fp.read_text(encoding="utf-8", errors="ignore")


def delete_upload(db: Session, project_id: str, upload_id: int) -> bool:
    """v2.5 — 删除上传记录 + 物理文件（解析文本 + 原始文件）。

    Returns True if deleted, False if not found.
    原始文件存储路径：settings.upload_dir / project_id / uid12__filename
    解析文本路径：由 resolve_parsed_path(rec) 还原为绝对路径。

    /review F1：从 parsed_text_path 提取 uid12 前缀，按精确路径删原文件；
    避免 glob `*__{filename}` 在同一项目同名文件场景下误删其它 upload。
    旧 row 若 parsed_text_path 为空，回退 glob 兜底。
    """
    rec = db.query(Upload).filter_by(id=upload_id, project_id=project_id).first()
    if not rec:
        return False

    # 删解析文本
    try:
        parsed_fp = resolve_parsed_path(rec)
        if parsed_fp.exists():
            parsed_fp.unlink()
    except Exception:
        pass  # 不阻断 DB 删除

    # 删原始文件 — 从 parsed_text_path basename 派生 uid12，按精确路径删
    try:
        upload_proj_dir = settings.upload_dir / project_id
        if upload_proj_dir.exists():
            uid_prefix = ""
            stored = rec.parsed_text_path or ""
            if stored:
                basename = Path(stored).name  # uid12__filename.txt
                if "__" in basename:
                    uid_prefix = basename.split("__", 1)[0]

            if uid_prefix:
                # 精确路径：uid12__{原始文件名}
                target = upload_proj_dir / f"{uid_prefix}__{rec.filename}"
                target.unlink(missing_ok=True)
            else:
                # 兜底：旧 row 无 parsed_text_path 时走 glob（可能误删同名文件，
                # 但旧数据本来就没办法精确定位）
                for f in upload_proj_dir.glob(f"*__{rec.filename}"):
                    f.unlink(missing_ok=True)
    except Exception:
        pass  # 不阻断 DB 删除

    db.delete(rec)
    db.commit()
    return True
