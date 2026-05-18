from typing import Any


# OWASP CSV / Excel injection 防护：用户输入字符串若以这些字符开头，Excel
# 会把它当公式执行（=HYPERLINK / =cmd|... 等是已知 RCE 路径）。在写入前
# 加单引号让 Excel 显式当文本处理。
# 覆盖范围：ASCII = + - @ + Tab + CR。Excel 不把全角 ＝＋－＠ 视为公式触发，
# 所以不需要列入。NUL/换行不会被 Excel 解析为公式。
_FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")


def _safe_text(v: Any) -> Any:
    """If v is a string starting with a formula-trigger char, prefix it with
    a single quote so Excel renders it as text. Pass through everything else
    (numbers, None) as-is."""
    if isinstance(v, str) and v.startswith(_FORMULA_TRIGGERS):
        return "'" + v
    return v
