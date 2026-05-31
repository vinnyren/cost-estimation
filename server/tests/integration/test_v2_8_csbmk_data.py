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


def test_compliance_factor_present():
    cf = _seed()["factors_dev"]["compliance"]
    # 表 A.2：吻合度 高 1/3 / 中 2/3 / 低 1
    assert set(cf.keys()) == {"high", "medium", "low"}
    assert cf["low"] == 1.0


def test_ops_software_type_factor_present():
    st = _seed()["factors_ops"]["software_type"]
    assert isinstance(st, dict) and len(st) >= 2
    # 表 A.8 软件类型因子（运维侧）已核对值
    assert st["操作系统"] == 0.90
    assert st["数据库"] == 1.00


def test_confidentiality_factor_present():
    conf = _seed()["factors_dev"]["confidentiality"]
    assert isinstance(conf, dict) and len(conf) >= 2
    # 表 A.19 涉密因子已核对值
    assert conf["非涉密"] == 1.00
    assert conf["涉密"] == 1.18


def test_defect_density_table_present():
    dd = _seed()["display"]["defect_density"]
    assert "P50" in dd
    # SSM-BK-202509 表 3-5 缺陷密度已核对值（P50 由 0.23 更新为 0.12）
    assert dd["P50"] == 0.12


def test_phase_effort_distribution_present():
    pe = _seed()["display"]["phase_effort"]
    # 阶段工作量分布各阶段占比之和约等于 1
    total = sum(pe.values())
    assert abs(total - 1.0) < 0.05


def test_fp_unit_price_present():
    up = _seed()["display"]["fp_unit_price"]
    assert isinstance(up, dict) and len(up) >= 1
    # SSM-BK-202509 第 3.14 节 功能点单价已核对值（北京开发，由 1243.52 更新为 1336.00）
    assert up["北京_开发"] == 1336.00


def test_ops_cost_ratio_all_bands():
    ocr = _seed()["ops_cost_ratio"]
    assert {"P10", "P50", "P90"} <= set(ocr.keys())


def test_appendix_c_tables_present():
    appc = _seed()["appendix_c"]
    assert "hw_ops_unit_effort" in appc      # 表 C.1
    assert "security_service_unit_price" in appc  # 表 C.2
    assert len(appc["hw_ops_unit_effort"]) > 0
    assert len(appc["security_service_unit_price"]) > 0
