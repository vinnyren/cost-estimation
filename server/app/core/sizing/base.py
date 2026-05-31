"""SizeMethod 协议：功能规模测量策略的公共接口。"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class SizeMethod(Protocol):
    size_unit: str   # "FP" 或 "CFP"
    input_model: str  # "ifpug_style" 或 "cosmic"

    def compute_entry_size(self, entry: dict) -> float:
        """计算单个功能点/功能过程的未调整规模。

        entry 是 FunctionPoint 字段的字典，含 category/det/ret/ftr
        或 cosmic_entry/exit/read/write，视 input_model 而定。
        信息不足时返回兜底值（average UFP 或 0.0），不抛异常。
        """
        ...
