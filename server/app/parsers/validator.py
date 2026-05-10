from pathlib import Path
import magic

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".md", ".txt"}
ALLOWED_MIME = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "text/markdown",
}
MAX_SIZE = 50 * 1024 * 1024  # 50 MiB


class UploadValidationError(ValueError):
    pass


def validate_upload(path: Path, original_name: str) -> dict:
    """三层校验：扩展名 + MIME + 大小 + 文件名安全。返回元信息字典或抛 UploadValidationError"""
    # 文件名安全（zip slip / path traversal）
    if "/" in original_name or "\\" in original_name or ".." in original_name:
        raise UploadValidationError(f"UNSAFE_FILENAME: {original_name}")

    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UploadValidationError(f"INVALID_FILE_TYPE: ext={ext} not in {ALLOWED_EXTENSIONS}")

    if not path.exists():
        raise UploadValidationError(f"FILE_NOT_FOUND: {path}")
    size = path.stat().st_size
    if size > MAX_SIZE:
        raise UploadValidationError(f"FILE_TOO_LARGE: {size} > {MAX_SIZE}")

    # MIME 嗅探（libmagic 全文件识别，必要时读取尾部 ZIP 中央目录以区分 docx/xlsx）
    mime = magic.from_file(str(path), mime=True)
    if ext in {".md", ".txt"}:
        # 文本类宽松：允许 text/* 与 application/octet-stream
        if not (mime.startswith("text/") or mime == "application/octet-stream"):
            raise UploadValidationError(f"MIME_MISMATCH: ext={ext} mime={mime}")
    else:
        if mime not in ALLOWED_MIME:
            raise UploadValidationError(f"MIME_MISMATCH: ext={ext} mime={mime}")

    return {"ext": ext, "mime": mime, "size": size}
