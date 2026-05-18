"""IFPUG GB/T 42449-2023 功能点复杂度查表。

数据功能（ILF/EIF）按 RET × DET 定复杂度（表 1）；
事务功能 EI 按 FTR × DET（表 6），EO/EQ 按 FTR × DET（表 7）。
fp_value 把 (category, complexity) 映射为未调整功能点数（表 2 / 表 8）。
"""
from typing import Literal, Optional

Category = Literal["EI", "EO", "EQ", "ILF", "EIF"]
Complexity = Literal["low", "average", "high"]

_DEFAULT: Complexity = "average"

# 表 2 / 表 8 — (category, complexity) → UFP
_FP_VALUE: dict[str, dict[str, int]] = {
    "ILF": {"low": 7, "average": 10, "high": 15},
    "EIF": {"low": 5, "average": 7, "high": 10},
    "EI": {"low": 3, "average": 4, "high": 6},
    "EO": {"low": 4, "average": 5, "high": 7},
    "EQ": {"low": 3, "average": 4, "high": 6},
}


def _ret_band(ret: int) -> int:
    """RET 分档：1 → 0；2-5 → 1；>5 → 2。"""
    if ret <= 1:
        return 0
    if ret <= 5:
        return 1
    return 2


def _data_det_band(det: int) -> int:
    """数据功能 DET 分档：1-19 → 0；20-50 → 1；>50 → 2。"""
    if det <= 19:
        return 0
    if det <= 50:
        return 1
    return 2


def _ftr_band_ei(ftr: int) -> int:
    """EI 的 FTR 分档：0-1 → 0；2 → 1；>2 → 2。"""
    if ftr <= 1:
        return 0
    if ftr == 2:
        return 1
    return 2


def _ftr_band_eo_eq(ftr: int) -> int:
    """EO/EQ 的 FTR 分档：0-1 → 0；2-3 → 1；>3 → 2。"""
    if ftr <= 1:
        return 0
    if ftr <= 3:
        return 1
    return 2


def _txn_det_band(det: int) -> int:
    """事务功能 DET 分档：1-4(EI)/1-5(EO/EQ) 简化为 1-5 → 0；6-19 → 1；>19 → 2。"""
    if det <= 5:
        return 0
    if det <= 19:
        return 1
    return 2


# 数据功能查表矩阵（ILF/EIF 表 1）：[RET_band][DET_band] → complexity。
# GB/T 42449: RET=1 时 DET=20-50 已达 average。
_DATA_MATRIX: list[list[Complexity]] = [
    ["low", "average", "high"],   # RET=1
    ["low", "average", "high"],   # RET=2-5
    ["average", "high", "high"],  # RET>5
]

# 事务功能查表矩阵（EI/EO/EQ 表 6/7）：[FTR_band][DET_band] → complexity。
_TXN_MATRIX: list[list[Complexity]] = [
    ["low", "low", "average"],
    ["low", "average", "high"],
    ["average", "high", "high"],
]


def classify_complexity(
    category: str,
    det: Optional[int],
    ret: Optional[int],
    ftr: Optional[int],
) -> Complexity:
    """按 GB/T 42449 查表得复杂度。信息不足时返回 average。

    数据功能（ILF/EIF）需 det+ret；事务功能（EI/EO/EQ）需 det+ftr。
    缺任一必需输入即默认 average。
    """
    if category in ("ILF", "EIF"):
        if det is None or ret is None:
            return _DEFAULT
        return _DATA_MATRIX[_ret_band(ret)][_data_det_band(det)]
    if category in ("EI", "EO", "EQ"):
        if det is None or ftr is None:
            return _DEFAULT
        ftr_band = _ftr_band_ei(ftr) if category == "EI" else _ftr_band_eo_eq(ftr)
        return _TXN_MATRIX[ftr_band][_txn_det_band(det)]
    return _DEFAULT


def fp_value(category: str, complexity: str) -> int:
    """(category, complexity) → 未调整功能点数。未知 category 抛 ValueError。"""
    table = _FP_VALUE.get(category)
    if table is None:
        raise ValueError(f"UNKNOWN_CATEGORY: {category!r}")
    return table[complexity]
