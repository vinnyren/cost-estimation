from pathlib import Path
import pytest
from app.parsers.pdf import parse_pdf, ParsedDocument

FIX = Path(__file__).parent.parent / "fixtures"

def test_parse_pdf_returns_text():
    doc = parse_pdf(FIX / "sample.pdf")
    assert isinstance(doc, ParsedDocument)
    assert "门户首页" in doc.text
    assert "新闻管理" in doc.text
    assert doc.page_count >= 1

def test_parse_pdf_nonexistent_raises():
    with pytest.raises(FileNotFoundError):
        parse_pdf(FIX / "nonexistent.pdf")

def test_parse_pdf_empty_returns_empty_text(tmp_path):
    from reportlab.pdfgen import canvas
    p = tmp_path / "empty.pdf"
    c = canvas.Canvas(str(p))
    c.showPage()  # commit a blank page so PDF has page_count == 1
    c.save()
    doc = parse_pdf(p)
    assert doc.text == ""
    assert doc.page_count == 1
