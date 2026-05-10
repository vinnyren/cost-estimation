from pathlib import Path
import pytest
from app.parsers.xlsx import parse_xlsx, ParsedSheet

FIX = Path(__file__).parent.parent / "fixtures"

def test_parse_xlsx_returns_sheets():
    sheets = parse_xlsx(FIX / "sample.xlsx")
    assert len(sheets) == 1
    s = sheets[0]
    assert isinstance(s, ParsedSheet)
    assert s.name == "功能清单"
    assert s.headers == ["子系统", "一级模块", "二级模块", "功能项描述"]
    assert len(s.rows) == 4
    assert s.rows[0] == ["政务服务平台", "业务功能", "门户首页", "新闻列表"]

def test_parse_xlsx_nonexistent_raises():
    with pytest.raises(FileNotFoundError):
        parse_xlsx(FIX / "nope.xlsx")
