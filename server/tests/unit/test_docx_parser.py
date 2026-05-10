from pathlib import Path
import pytest
from app.parsers.docx import parse_docx
from app.parsers.pdf import ParsedDocument  # 复用 dataclass

FIX = Path(__file__).parent.parent / "fixtures"

def test_parse_docx_extracts_text():
    doc = parse_docx(FIX / "sample.docx")
    assert isinstance(doc, ParsedDocument)
    assert "政务服务平台" in doc.text
    assert "门户首页" in doc.text
    assert "新闻管理" in doc.text

def test_parse_docx_extracts_tables():
    doc = parse_docx(FIX / "sample.docx")
    # 表格内容应作为额外段落提取
    assert "模块" in doc.text
    assert "新闻新增" in doc.text

def test_parse_docx_nonexistent_raises():
    with pytest.raises(FileNotFoundError):
        parse_docx(FIX / "nope.docx")
