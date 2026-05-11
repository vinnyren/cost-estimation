"""项目级调整因子组装层（v2.0 GAP-B 闭环 / Task T7）。

calc.py 不再硬编码 dev_factor=1.0 / ops_factor=1.0 — 而是经由本层把：

    project.factors_dev_json  (用户在向导里选的标签集合)
        ⊕
    effective_params["factors_dev"] (CSBMK 因子表，{字段: {标签: 乘子}})

组装成最终乘子链交给 core.forward / core.reverse。

设计要点：
- factors_*_json 为空 → 整体 fallback 1.0，并附 warning_messages，避免
  silent "看着算了其实没用因子" 的尴尬。
- factors_*_json 部分缺字段 → 仅缺字段 fallback 1.0（不附 warning，因为
  用户可能本就只想要部分维度生效）。
- 字段值是 dict（如 non_func 的 4 项 -1/0/1 子选项）→ 走 non_func_factor。
- 字段值是 str 标签 → 在因子表里查 multiplier，找不到回退 1.0。
"""

from __future__ import annotations

import json
from typing import Any

from ..core.factors import dev_factor_chain, non_func_factor, ops_factor_chain
from ..db.models import Project


def _safe_load(json_str: str | None) -> dict[str, Any]:
    """Return parsed dict, or {} for None / non-dict / parse failure.

    Calc must never crash on a corrupted factors_*_json column — worst case
    is a 1.0 fallback with warning. (paranoia for ISSUE-class corrupted-row)
    """
    if not json_str:
        return {}
    try:
        parsed = json.loads(json_str)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _lookup_multiplier(
    table: dict[str, Any], field: str, value: Any
) -> float:
    """Lookup table[field][value] as float. Return 1.0 for any miss / bad type.

    Robust to:
    - field missing in factor table (CSBMK doesn't define that dimension)
    - value missing in field's choice map (label typo / outdated label)
    - non-numeric leaf (config drift)
    """
    field_table = table.get(field)
    if not isinstance(field_table, dict):
        return 1.0
    raw = field_table.get(value)
    if isinstance(raw, (int, float)):
        return float(raw)
    return 1.0


def _dev_non_func_multiplier(
    raw: Any, factor_table: dict[str, Any]
) -> float:
    """non_func 是个混合维度：

    - 用户传 4 项 -1/0/1 选项 dict → 走 core.non_func_factor(乘 0.025+1)
    - 用户传单一标签 str → 在 factors_dev["non_func"] 表里查（向后兼容）
    - 其他 → 1.0
    """
    if isinstance(raw, dict):
        try:
            return non_func_factor(
                distributed=int(raw.get("distributed", 0)),
                performance=int(raw.get("performance", 0)),
                reliability=int(raw.get("reliability", 0)),
                multi_site=int(raw.get("multi_site", 0)),
            )
        except (TypeError, ValueError):
            return 1.0
    if isinstance(raw, str):
        return _lookup_multiplier(factor_table, "non_func", raw)
    return 1.0


def _compute_dev_factor(
    selections: dict[str, Any], factor_table: dict[str, Any]
) -> float:
    """开发调整因子 5 维乘子链。

    维度按 CSBMK 规范的固定顺序参与 dev_factor_chain：
        1. app_type         应用类型
        2. integrity_level  完整性级别
        3. non_func         非功能性需求（混合维度，见 _dev_non_func_multiplier）
        4. platform         平台
        5. team_bg          团队背景

    selections 中任何维度缺失/标签不在 factor_table → 该维度回退 1.0
    （不抛错、不发 warning），允许向导只填部分维度。
    """
    app_type_m = _lookup_multiplier(
        factor_table, "app_type", selections.get("app_type")
    )
    integrity_m = _lookup_multiplier(
        factor_table, "integrity_level", selections.get("integrity_level")
    )
    non_func_m = _dev_non_func_multiplier(
        selections.get("non_func"), factor_table
    )
    platform_m = _lookup_multiplier(
        factor_table, "platform", selections.get("platform")
    )
    team_bg_m = _lookup_multiplier(
        factor_table, "team_bg", selections.get("team_bg")
    )
    return dev_factor_chain(
        app_type=app_type_m,
        non_func=non_func_m,
        integrity=integrity_m,
        platform=platform_m,
        team_bg=team_bg_m,
    )


# core.ops_factor_chain 的 11 个关键字参数 → factors_ops 表里的字段名映射。
# 用 tuple 让排序固定、便于阅读 review diff。
_OPS_DIMENSIONS: tuple[tuple[str, str], ...] = (
    ("business_importance", "business_importance"),
    ("security", "security_level"),
    ("support", "support"),
    ("update_freq", "update_freq"),
    ("response", "response_time"),
    ("integrity", "integrity_level"),
    ("platform", "platform"),
    ("team_exp", "team_exp"),
    ("deployment", "deployment"),
    ("user_scale", "user_scale"),
    ("relevance", "system_relevance"),
)


def _compute_ops_factor(
    selections: dict[str, Any], factor_table: dict[str, Any]
) -> float:
    """运维调整因子 11 维乘子链。

    维度顺序由 _OPS_DIMENSIONS 元组固定（见上）：business_importance、
    security、support、update_freq、response、integrity、platform、
    team_exp、deployment、user_scale、relevance。

    selections 用 factor_table 字段名作 key（如 "security_level"），需映射
    回 ops_factor_chain 形参名（如 "security"），故有 (kwarg, selection_key)
    两列。每一维缺失/标签查不到 → 该维度回退 1.0，整体不报错。
    """
    kwargs: dict[str, float] = {}
    for kwarg_name, selection_key in _OPS_DIMENSIONS:
        kwargs[kwarg_name] = _lookup_multiplier(
            factor_table, selection_key, selections.get(selection_key)
        )
    # factors_ops 没有内置 platform 表（seed 只在 factors_dev 下），但 ops
    # 仍然要乘 platform 维度 — 缺表时已经回退 1.0，逻辑正确。
    return ops_factor_chain(**kwargs)


def project_factors(
    project: Project, effective_params: dict
) -> tuple[float, float, list[str]]:
    """Return (dev_factor, ops_factor, warning_messages) for a project.

    Calc 主入口。封装两条规则：
    - factors_dev_json 为空 → dev_factor=1.0 + warning。
    - factors_ops_json 为空 + include_ops 启用 → ops_factor=1.0 + warning。
      （include_ops=False 时无 warning — 即便 factors_ops 空也不影响结果）
    """
    warnings: list[str] = []

    dev_table = effective_params.get("factors_dev") or {}
    dev_selections = _safe_load(project.factors_dev_json)
    if dev_selections:
        dev_factor = _compute_dev_factor(dev_selections, dev_table)
    else:
        dev_factor = 1.0
        warnings.append(
            "此项目缺少开发调整因子配置，已按 1.0 计算。请在项目设置中补充。"
        )

    ops_table = effective_params.get("factors_ops") or {}
    ops_selections = _safe_load(project.factors_ops_json)
    if ops_selections:
        ops_factor = _compute_ops_factor(ops_selections, ops_table)
    else:
        ops_factor = 1.0
        if getattr(project, "include_ops", False):
            warnings.append(
                "此项目启用了运维但缺少运维调整因子配置，已按 1.0 计算。"
            )

    return dev_factor, ops_factor, warnings
