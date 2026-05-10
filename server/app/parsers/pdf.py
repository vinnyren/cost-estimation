from dataclasses import dataclass, field
from pathlib import Path
import pdfplumber

@dataclass
class ParsedDocument:
    text: str
    page_count: int
    metadata: dict = field(default_factory=dict)

def parse_pdf(path: Path) -> ParsedDocument:
    """提取 PDF 全文。同步 IO，调用方应通过 run_in_threadpool 包装。"""
    if not path.exists():
        raise FileNotFoundError(f"PDF 文件不存在: {path}")
    pages = []
    with pdfplumber.open(path) as pdf:
        page_count = len(pdf.pages)
        for p in pdf.pages:
            pages.append(p.extract_text() or "")
    return ParsedDocument(
        text="\n".join(pages),
        page_count=page_count,
        metadata={"source": str(path), "type": "pdf"})
