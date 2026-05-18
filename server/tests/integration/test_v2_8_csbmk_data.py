"""v2.8 — csbmk_202510.json 数值对齐 2025 PDF 校验。"""
import json
from app.config import settings


def _seed() -> dict:
    return json.loads(settings.csbmk_seed_path.read_text(encoding="utf-8"))


def test_scale_change_corrected():
    sc = _seed()["scale_change"]
    assert sc["modify"] == 0.80
    assert sc["remove"] == 0.20
    assert "convert" not in sc  # 标准没有 convert 档


def test_dev_platform_corrected():
    plat = _seed()["factors_dev"]["platform"]
    assert plat["C"] == 1.2
    assert plat["PowerBuilder"] == 0.8
    assert plat["ASP"] == 0.8


def test_update_freq_corrected():
    assert _seed()["factors_ops"]["update_freq"]["quarterly"] == 0.78


def test_support_corrected():
    sup = _seed()["factors_ops"]["support"]
    assert sup["remote"] == 0.90
    assert sup["pure_onsite"] == 1.20


def test_user_scale_corrected():
    us = _seed()["factors_ops"]["user_scale"]
    assert us["<=1k"] == 0.93
    assert us[">10k"] == 1.12


def test_system_relevance_rebanded():
    rel = _seed()["factors_ops"]["system_relevance"]
    assert "1-10" in rel
    assert "10+" in rel
    assert "1-5" not in rel
    assert "6+" not in rel


def test_app_type_no_software_integration():
    # 标准没有「软件集成 1.20」档
    assert "软件集成" not in _seed()["factors_dev"]["app_type"]
