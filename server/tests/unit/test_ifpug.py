"""v2.8 — IFPUG GB/T 42449-2023 复杂度查表单元测试。"""
import pytest
from app.core.ifpug import classify_complexity, fp_value


# ── 数据功能 ILF/EIF：按 RET × DET ──────────────────────────────────
@pytest.mark.parametrize("category", ["ILF", "EIF"])
def test_data_function_low(category):
    # RET 1 且 DET 1-19 → low
    assert classify_complexity(category, det=10, ret=1, ftr=None) == "low"


@pytest.mark.parametrize("category", ["ILF", "EIF"])
def test_data_function_average_mid_det(category):
    # RET 2-5 + DET 20-50 → average（表 1）
    assert classify_complexity(category, det=30, ret=3, ftr=None) == "average"


@pytest.mark.parametrize("category", ["ILF", "EIF"])
def test_data_function_high(category):
    # RET >5 且 DET >50 → high
    assert classify_complexity(category, det=60, ret=6, ftr=None) == "high"


def test_data_function_ret_2to5_det_high():
    # RET 2-5 + DET >50 → high
    assert classify_complexity("ILF", det=55, ret=3, ftr=None) == "high"


# ── 事务功能 EI：按 FTR × DET（表 6）─────────────────────────────────
def test_ei_low():
    # FTR 0-1 + DET 1-4 → low
    assert classify_complexity("EI", det=3, ret=None, ftr=1) == "low"


def test_ei_average():
    # FTR 2 + DET 5-15 → average
    assert classify_complexity("EI", det=10, ret=None, ftr=2) == "average"


def test_ei_high():
    # FTR >2 + DET >15 → high
    assert classify_complexity("EI", det=20, ret=None, ftr=3) == "high"


# ── 事务功能 EO/EQ：按 FTR × DET（表 7）─────────────────────────────
@pytest.mark.parametrize("category", ["EO", "EQ"])
def test_eo_eq_low(category):
    # FTR 0-1 + DET 1-5 → low
    assert classify_complexity(category, det=4, ret=None, ftr=1) == "low"


@pytest.mark.parametrize("category", ["EO", "EQ"])
def test_eo_eq_high(category):
    # FTR >3 + DET >19 → high
    assert classify_complexity(category, det=25, ret=None, ftr=4) == "high"


# ── 信息不足 → 默认 average ─────────────────────────────────────────
def test_missing_info_defaults_average():
    assert classify_complexity("ILF", det=None, ret=None, ftr=None) == "average"
    assert classify_complexity("EI", det=None, ret=None, ftr=None) == "average"


# ── fp_value：表 2 / 表 8 ───────────────────────────────────────────
def test_fp_value_data_functions():
    assert fp_value("ILF", "low") == 7
    assert fp_value("ILF", "average") == 10
    assert fp_value("ILF", "high") == 15
    assert fp_value("EIF", "low") == 5
    assert fp_value("EIF", "average") == 7
    assert fp_value("EIF", "high") == 10


def test_fp_value_transaction_functions():
    assert fp_value("EI", "low") == 3
    assert fp_value("EI", "average") == 4
    assert fp_value("EI", "high") == 6
    assert fp_value("EO", "low") == 4
    assert fp_value("EO", "average") == 5
    assert fp_value("EO", "high") == 7
    assert fp_value("EQ", "low") == 3
    assert fp_value("EQ", "average") == 4
    assert fp_value("EQ", "high") == 6


def test_fp_value_unknown_category_raises():
    with pytest.raises(ValueError):
        fp_value("XXX", "low")
