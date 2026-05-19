"""IfpugMethod：复用 core/ifpug.py 的 classify_complexity + fp_value。"""
from ..ifpug import classify_complexity, fp_value


class IfpugMethod:
    size_unit = "FP"
    input_model = "ifpug_style"

    def compute_entry_size(self, entry: dict) -> float:
        """按 IFPUG GB/T 42449 复杂度矩阵查表得 UFP。

        缺少 det/ret/ftr 时回退到 average 复杂度。
        """
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
