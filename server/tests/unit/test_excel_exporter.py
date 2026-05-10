from pathlib import Path
import importlib
import pytest
from openpyxl import load_workbook

TEMPLATE = Path(__file__).parent.parent.parent / "templates" / "report-v1.xlsx"


def _excel_module():
    """Re-import每次拿到当前 app.exporters.excel 模块，避免被 integration 测试重载替换后类不匹配。"""
    return importlib.import_module("app.exporters.excel")


def test_render_creates_valid_excel(tmp_path):
    excel = _excel_module()
    out = tmp_path / "report.xlsx"
    excel.render(
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
    for s in excel.REQUIRED_SHEETS:
        assert s in wb.sheetnames
    # 命名区域值正确
    summary = wb["评估结果摘要"]
    assert summary["C2"].value == 332.75
    assert summary["C9"].value == round(489180 / 10000, 4)


def test_render_broken_template_raises(tmp_path):
    excel = _excel_module()
    from openpyxl import Workbook
    bad = tmp_path / "bad.xlsx"
    Workbook().save(str(bad))  # 没有任何必备 sheet
    out = tmp_path / "out.xlsx"
    with pytest.raises(excel.TemplateBrokenError, match="missing sheets"):
        excel.render(bad, out, project_name="x", project_overview="",
                     scale_adjusted=0, effort_dev={"P10": 0, "P50": 0, "P90": 0},
                     cost_dev={"P10": 0, "P50": 0, "P90": 0}, cost_total_p50_yuan=0,
                     functions=[], factors=[], steps=[], params=[])


def test_fallback_renders_when_template_corrupt(tmp_path, monkeypatch):
    # 用空 workbook 替换模板路径
    from openpyxl import Workbook
    bad = tmp_path / "bad.xlsx"
    Workbook().save(str(bad))

    import app.services.reports as reports_mod
    monkeypatch.setattr(reports_mod, "TEMPLATE_PATH", bad)

    # 这里需要建 db + project + fp，简化用 e2e fixture（在 integration test 重做更合适）
    # 此处仅证明 fallback 能直接调用
    fallback_mod = importlib.import_module("app.exporters.fallback")
    out = tmp_path / "report.xlsx"
    fallback_mod.render_fallback(out, project_name="X", project_overview="",
                                 scale_adjusted=100,
                                 effort_dev={"P50": 1, "P10": 0.5, "P90": 2},
                                 cost_dev={"P50": 1000, "P10": 500, "P90": 2000},
                                 cost_total_p50_yuan=1500,
                                 functions=[], factors=[], steps=[], params=[])
    assert out.exists()
    wb = load_workbook(out)
    assert "评估结果摘要" in wb.sheetnames
