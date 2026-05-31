"""功能规模测量策略注册表。

get_method(measurement_method) 返回对应的 SizeMethod 实例。
"""
from .base import SizeMethod
from .ifpug import IfpugMethod
from .nesma import NesmaDetailedMethod, NesmaEstimatedMethod, NesmaIndicativeMethod
from .cosmic import CosmicMethod

_METHODS: dict[str, SizeMethod] = {
    "ifpug": IfpugMethod(),
    "nesma_detailed": NesmaDetailedMethod(),
    "nesma_estimated": NesmaEstimatedMethod(),
    "nesma_indicative": NesmaIndicativeMethod(),
    "cosmic": CosmicMethod(),
}


def get_method(name: str) -> SizeMethod:
    """返回 name 对应的 SizeMethod 实例。未知名称抛 ValueError。"""
    try:
        return _METHODS[name]
    except KeyError:
        raise ValueError(
            f"unknown measurement_method: {name!r}. "
            f"有效值: {list(_METHODS.keys())}"
        )
