from pathlib import Path
import pytest
from app.parsers.validator import (
    validate_upload, UploadValidationError, ALLOWED_EXTENSIONS, MAX_SIZE)

FIX = Path(__file__).parent.parent / "fixtures"

def test_validate_pdf_pass():
    info = validate_upload(FIX / "sample.pdf", original_name="report.pdf")
    assert info["ext"] == ".pdf"
    assert info["mime"].startswith("application/pdf")

def test_validate_docx_pass():
    info = validate_upload(FIX / "sample.docx", original_name="needs.docx")
    assert info["ext"] == ".docx"

def test_validate_xlsx_pass():
    info = validate_upload(FIX / "sample.xlsx", original_name="list.xlsx")
    assert info["ext"] == ".xlsx"

def test_reject_bad_extension():
    with pytest.raises(UploadValidationError, match="INVALID_FILE_TYPE"):
        validate_upload(FIX / "sample.pdf", original_name="evil.exe")

def test_reject_size_over_limit(tmp_path):
    # 用稀疏文件把逻辑大小撑到上限 +1 —— st_size 报告超限，但不真占磁盘。
    big = tmp_path / "big.pdf"
    with big.open("wb") as f:
        f.write(b"%PDF-1.4\n")
        f.truncate(MAX_SIZE + 1)
    with pytest.raises(UploadValidationError, match="FILE_TOO_LARGE"):
        validate_upload(big, original_name="big.pdf")

def test_reject_path_traversal_in_name():
    with pytest.raises(UploadValidationError, match="UNSAFE_FILENAME"):
        validate_upload(FIX / "sample.pdf", original_name="../../etc/passwd.pdf")

def test_reject_mime_mismatch(tmp_path):
    fake_pdf = tmp_path / "fake.pdf"
    fake_pdf.write_bytes(b"<html>not a pdf</html>")
    with pytest.raises(UploadValidationError, match="MIME_MISMATCH"):
        validate_upload(fake_pdf, original_name="fake.pdf")
