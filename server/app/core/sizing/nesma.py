"""NESMA 三个精度级别策略（GB/T 42588）。

详细级：按 DET/RET/FTR 查复杂度矩阵，与 IFPUG 一致（GB/T 42588 附录 B）。
估算级：每个功能取「中」复杂度（average），不需 DET/RET/FTR。
预估级：仅数 ILF/EIF，常数 35/15（NESMA 预估惯用值，对照 GB/T 42588 确认）。
"""
from ..ifpug import classify_complexity, fp_value


class NesmaDetailedMethod:
    """NESMA 详细级：复杂度矩阵与 IFPUG 一致。"""
    size_unit = "FP"
    input_model = "ifpug_style"

    def compute_entry_size(self, entry: dict) -> float:
        category = entry.get("category")
        det = entry.get("det")
        ret = entry.get("ret")
        ftr = entry.get("ftr")
        has_input = (
            (category in ("ILF", "EIF") and det is not None and ret is not None)
            or (category in ("EI", "EO", "EQ") and det is not None and ftr is not None)
        )
        complexity = classify_complexity(category, det, ret, ftr) if has_input else "average"
        return float(fp_value(category, complexity))


class NesmaEstimatedMethod:
    """NESMA 估算级：固定取「中（average）」复杂度，忽略 DET/RET/FTR。"""
    size_unit = "FP"
    input_model = "ifpug_style"

    def compute_entry_size(self, entry: dict) -> float:
        category = entry.get("category")
        return float(fp_value(category, "average"))


class NesmaIndicativeMethod:
    """NESMA 预估级：仅 ILF=35 / EIF=15，事务类功能返回 0。

    常数 35/15 为 NESMA 预估级惯用值。
    """
    size_unit = "FP"
    input_model = "ifpug_style"

    _ILF_FP = 35.0
    _EIF_FP = 15.0

    def compute_entry_size(self, entry: dict) -> float:
        category = entry.get("category")
        if category == "ILF":
            return self._ILF_FP
        if category == "EIF":
            return self._EIF_FP
        return 0.0
