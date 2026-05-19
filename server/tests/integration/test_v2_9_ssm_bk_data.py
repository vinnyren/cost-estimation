"""SSM-BK-202509 基准数据 JSON 正确性测试。"""
import json
import pytest
from pathlib import Path

DATA_PATH = Path(__file__).parents[2] / "app" / "data" / "ssm_bk_202509.json"


def _load():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_json_is_valid():
    assert isinstance(_load(), dict)


def test_version_string():
    assert _load()["version"] == "SSM-BK-202509"


def test_top_level_keys_present():
    data = _load()
    required = {
        "version", "effective_date", "productivity", "city_rate",
        "cf", "factors_dev", "factors_ops", "scale_change",
        "hours_per_pm", "ops_cost_ratio", "display",
    }
    for key in required:
        assert key in data, f"缺少顶层键: {key}"


def test_productivity_dev_industries():
    data = _load()
    dev_keys = set(data["productivity"]["dev"].keys())
    assert "全行业" in dev_keys
    assert len(dev_keys) >= 4


def test_productivity_dev_bands():
    data = _load()
    for industry, bands in data["productivity"]["dev"].items():
        for b in ("P10", "P50", "P90"):
            assert b in bands, f"{industry} 缺少 {b} 档"
            assert isinstance(bands[b], (int, float))
            assert bands[b] > 0


def test_productivity_ops_quanhanghye():
    data = _load()
    assert "全行业" in data["productivity"]["ops"]


def test_hours_per_pm():
    assert _load()["hours_per_pm"] == 174


def test_productivity_dev_quanhanghye_p50():
    """全行业开发生产率 P50 与 PDF 一致。"""
    actual = _load()["productivity"]["dev"]["全行业"]["P50"]
    assert actual == pytest.approx(6.96, rel=0.01)


def test_cf_phases_present():
    data = _load()
    for phase in ("budget", "bidding", "planning", "change", "settled"):
        assert phase in data["cf"], f"cf 缺少阶段 {phase}"
