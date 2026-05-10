from pathlib import Path
import pytest
from openpyxl import load_workbook
from app.exporters.excel import render, TemplateBrokenError, REQUIRED_SHEETS, REQUIRED_NAMES

TEMPLATE = Path(__file__).parent.parent.parent / "templates" / "report-v1.xlsx"


def test_render_creates_valid_excel(tmp_path):
    out = tmp_path / "report.xlsx"
    render(
        TEMPLATE, out,
        project_name="测试项目", project_overview="项目概述文本",
        scale_adjusted=332.75,
        effort_dev={"P10": 678, "P50": 2236, "P90": 5773},
        cost_dev={"P10": 126237, "P50": 415565, "P90": 1067711},
        cost_total_p50_yuan=489180,
        functions=[{"name": "门户首页", "category": "EQ", "ufp": 4, "us": 4}],
        factors=[{"category": "开发", "name": "应用类型", "value": 1.0}],
        steps=[{"step": "1", "desc": "求和", "formula": "Σ us", "result": 275}],
        params=[{"key": "city", "value": "北京", "source": "user"}],
    )
    wb = load_workbook(out)
    # Sheet 数齐全
    for s in REQUIRED_SHEETS:
        assert s in wb.sheetnames
    # 命名区域值正确
    summary = wb["评估结果摘要"]
    assert summary["C2"].value == 332.75
    assert summary["C9"].value == round(489180 / 10000, 4)


def test_render_broken_template_raises(tmp_path):
    from openpyxl import Workbook
    bad = tmp_path / "bad.xlsx"
    Workbook().save(str(bad))  # 没有任何必备 sheet
    out = tmp_path / "out.xlsx"
    with pytest.raises(TemplateBrokenError, match="missing sheets"):
        render(bad, out, project_name="x", project_overview="",
               scale_adjusted=0, effort_dev={"P10": 0, "P50": 0, "P90": 0},
               cost_dev={"P10": 0, "P50": 0, "P90": 0}, cost_total_p50_yuan=0,
               functions=[], factors=[], steps=[], params=[])
