# 多标准功能规模测量 + SSM-BK-202509 基准数据 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为项目引入五种国标功能规模测量方法（IFPUG / NESMA 三级 / COSMIC），将基准数据从 CSBMK®-202510 迁移至 SSM-BK-202509，并打通从规模录入到报告输出的全链路。

**Architecture:** 后端新建 `core/sizing/` 策略包，通过 `get_method(measurement_method)` 注册表按项目选择规模算法；`services/functions.py` 的 `_apply_sizing` 和 `services/calc.py` 的 forward/reverse 调用该策略；COSMIC CFP 经 `cfp_to_fp` 系数换算为 FP 当量后复用现有成本流水线。前端 `FpFormModal` 按方法条件渲染录入区，`ProjectWizard` 新增方法选择器，方法切换时对跨录入模型变更做二次确认。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic + pytest（后端）；Vue 3 + TypeScript + Vitest（前端）。

---

## 文件结构

### 新增文件

| 路径 | 说明 |
|---|---|
| `server/alembic/versions/<12hex>_measurement_method_and_cosmic.py` | migration：替换 fp_method → measurement_method，加 4 个 cosmic_* 列 |
| `server/app/core/sizing/__init__.py` | 策略注册表 `get_method` |
| `server/app/core/sizing/base.py` | `SizeMethod` Protocol |
| `server/app/core/sizing/ifpug.py` | `IfpugMethod` |
| `server/app/core/sizing/nesma.py` | `NesmaDetailedMethod` / `NesmaEstimatedMethod` / `NesmaIndicativeMethod` |
| `server/app/core/sizing/cosmic.py` | `CosmicMethod` |
| `server/app/data/ssm_bk_202509.json` | SSM-BK-202509 基准数据 |
| `server/tests/integration/test_v2_9_measurement_method.py` | migration + schema 集成测试 |
| `server/tests/integration/test_v2_9_ssm_bk_data.py` | SSM-BK 数据正确性测试 |
| `server/tests/integration/test_v2_9_calc_methods.py` | 多方法正向/反向计算测试 |
| `server/tests/integration/test_v2_9_report_method.py` | 报告方法声明测试 |
| `server/tests/unit/test_sizing.py` | 策略包单元测试 |
| `web/src/__tests__/FpFormModal-methods.test.ts` | FpFormModal 按方法渲染测试 |

### 修改文件

| 路径 | 变更内容 |
|---|---|
| `server/app/db/models.py` | Project: `fp_method` → `measurement_method`；FunctionPoint: 加 `cosmic_*` 列 |
| `server/app/schemas/project.py` | `fp_method` → `measurement_method`；ProjectPatch 加 Optional measurement_method |
| `server/app/schemas/functions.py` | FunctionPointBase / Patch 加 `cosmic_entry/exit/read/write` |
| `server/app/core/context.py` | 加 `cfp_to_fp` 属性 |
| `server/app/core/forward.py` | `ForwardInput` 加 `size_declaration` 字段；trace 使用该字段 |
| `server/app/services/functions.py` | `_apply_ifpug` → `_apply_sizing(method, data)` |
| `server/app/services/calc.py` | forward/reverse 读 `measurement_method`，COSMIC 做 CFP÷cfp_to_fp |
| `server/app/exporters/report_builder.py` | 方法声明 + COSMIC 换算备注 |
| `server/app/services/reports.py` | 传递方法声明参数 |
| `server/app/config.py` | `csbmk_seed_path` 指向 `ssm_bk_202509.json` |
| `web/src/api/projects.ts` | `fp_method` → `measurement_method` |
| `web/src/components/fp/FpFormModal.vue` | 接受 `measurementMethod` prop，按方法切换录入区 |
| `web/src/views/FpEditor.vue` | 加载项目并传 `measurement_method` 给 FpFormModal |
| `web/src/views/ProjectWizard.vue` | 加 `measurement_method` 字段与选择器 |
| `web/src/views/ParamManager.vue` | 规模变更 tab 暴露 `cfp_to_fp` OverrideField |
| `commands/cost.md` | AI 提取按方法分支 |
| `README.md` | 修正 GB/T 42452-2023 标注；补充标准合规列表 |

---

## Phase A — 多标准功能规模测量框架

### Task A1: Alembic migration — measurement_method + COSMIC 列

**Files:**
- Create: `server/alembic/versions/a9f3c0b1d2e7_measurement_method_and_cosmic.py`
- Modify: `server/app/db/models.py`
- Test: `server/tests/integration/test_v2_9_measurement_method.py`

> **注意：** 12 位 hex revision ID 由实施者随机生成，此处用 `a9f3c0b1d2e7` 占位；实际文件名与 `revision = "a9f3c0b1d2e7"` 保持一致即可。

- [ ] **Step 1: 写失败测试**

```python
# server/tests/integration/test_v2_9_measurement_method.py
"""v2.9 migration：measurement_method 列 + COSMIC 列测试。

Task A1 覆盖：Project 有 measurement_method / 无 fp_method；
FunctionPoint 有 4 个 cosmic_* 列。
Task A3 扩展：同文件后续追加 schema 和 PATCH 测试。
Task A4 扩展：同文件后续追加 _apply_sizing HTTP 测试。
"""
import pytest
from sqlalchemy import inspect as sa_inspect
from app.db.models import Project, FunctionPoint

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


def test_project_has_measurement_method(db_session):
    """Project model 应有 measurement_method 列，不再有 fp_method。"""
    cols = {c.name for c in Project.__table__.columns}
    assert "measurement_method" in cols
    assert "fp_method" not in cols


def test_fp_has_cosmic_columns(db_session):
    """FunctionPoint model 应有 4 个 cosmic_* 整数可空列。"""
    cols = {c.name: c for c in FunctionPoint.__table__.columns}
    for col_name in ("cosmic_entry", "cosmic_exit", "cosmic_read", "cosmic_write"):
        assert col_name in cols, f"缺列 {col_name}"
        assert cols[col_name].nullable is True, f"{col_name} 应可空"
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_9_measurement_method.py -q
```

预期：`FAILED` — `measurement_method` 尚不存在于 models，`fp_method` 还在。

- [ ] **Step 3: 写最小实现**

3a. 创建 migration 文件（实施者将 `a9f3c0b1d2e7` 替换为自己生成的随机 12 位 hex）：

```python
# server/alembic/versions/a9f3c0b1d2e7_measurement_method_and_cosmic.py
"""measurement_method_and_cosmic

Revision ID: a9f3c0b1d2e7
Revises: f3a7d9e2c841
Create Date: 2026-05-19 12:00:00.000000

v2.9 — 多标准功能规模测量（measurement_method）+ COSMIC 数据移动列：
- projects.measurement_method 取代死字段 fp_method（值迁移后删除旧列）。
- function_points 新增 cosmic_entry / cosmic_exit / cosmic_read / cosmic_write。

dev 库兼容：本项目 bootstrap 用 create_all，dev 库可能无 alembic 版本戳，
无法 `alembic upgrade head`。此时手动执行：
  ALTER TABLE projects ADD COLUMN measurement_method VARCHAR NOT NULL DEFAULT 'nesma_estimated';
  ALTER TABLE projects DROP COLUMN fp_method;
  ALTER TABLE function_points ADD COLUMN cosmic_entry INTEGER;
  ALTER TABLE function_points ADD COLUMN cosmic_exit INTEGER;
  ALTER TABLE function_points ADD COLUMN cosmic_read INTEGER;
  ALTER TABLE function_points ADD COLUMN cosmic_write INTEGER;
"""
from alembic import op
import sqlalchemy as sa

revision = "a9f3c0b1d2e7"
down_revision = "f3a7d9e2c841"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. projects：加 measurement_method，迁移旧值，删 fp_method
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column(
            "measurement_method", sa.String(),
            server_default="nesma_estimated", nullable=False,
        ))
    op.execute(
        "UPDATE projects SET measurement_method = fp_method "
        "WHERE fp_method IN ('ifpug', 'nesma_estimated')"
    )
    op.execute(
        "UPDATE projects SET measurement_method = 'nesma_estimated' "
        "WHERE fp_method = 'quick'"
    )
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("fp_method")

    # 2. function_points：加 4 个 COSMIC 数据移动列（可空整数）
    with op.batch_alter_table("function_points") as batch:
        batch.add_column(sa.Column("cosmic_entry", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("cosmic_exit",  sa.Integer(), nullable=True))
        batch.add_column(sa.Column("cosmic_read",  sa.Integer(), nullable=True))
        batch.add_column(sa.Column("cosmic_write", sa.Integer(), nullable=True))


def downgrade() -> None:
    # 删 COSMIC 列
    with op.batch_alter_table("function_points") as batch:
        batch.drop_column("cosmic_write")
        batch.drop_column("cosmic_read")
        batch.drop_column("cosmic_exit")
        batch.drop_column("cosmic_entry")

    # 恢复 fp_method，从 measurement_method 回迁，删 measurement_method
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column(
            "fp_method", sa.String(),
            server_default="nesma_estimated", nullable=True,
        ))
    op.execute("UPDATE projects SET fp_method = measurement_method")
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("measurement_method")
```

3b. 修改 `server/app/db/models.py`：

在 `Project`（L18–96）中，找到：
```python
    fp_method = Column(String, default="nesma_estimated")
```
替换为：
```python
    measurement_method = Column(String, nullable=False, server_default="nesma_estimated")
```

在 `FunctionPoint`（L99–132）中，在 `ftr` 行（L120）之后、`fp_kind` 之前插入：
```python
    # v2.9 COSMIC 数据移动列（可空，仅 cosmic 方法使用）
    cosmic_entry = Column(Integer, nullable=True)
    cosmic_exit  = Column(Integer, nullable=True)
    cosmic_read  = Column(Integer, nullable=True)
    cosmic_write = Column(Integer, nullable=True)
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_9_measurement_method.py -q
```

预期：`2 passed`。

> 注：Task A3 会在同文件追加 schema/PATCH 测试，届时再运行完整文件。

- [ ] **Step 5: 提交**

```bash
git add server/alembic/versions/a9f3c0b1d2e7_measurement_method_and_cosmic.py \
        server/app/db/models.py \
        server/tests/integration/test_v2_9_measurement_method.py
git commit -m "feat(db): measurement_method + COSMIC 列 migration (v2.9 A1)"
```

---

### Task A2: core/sizing/ 策略包

**Files:**
- Create: `server/app/core/sizing/__init__.py`
- Create: `server/app/core/sizing/base.py`
- Create: `server/app/core/sizing/ifpug.py`
- Create: `server/app/core/sizing/nesma.py`
- Create: `server/app/core/sizing/cosmic.py`
- Test: `server/tests/unit/test_sizing.py`

- [ ] **Step 1: 写失败测试**

```python
# server/tests/unit/test_sizing.py
"""core/sizing/ 策略包单元测试。"""
import pytest
from app.core.sizing import get_method
from app.core.sizing.ifpug import IfpugMethod
from app.core.sizing.nesma import (
    NesmaDetailedMethod, NesmaEstimatedMethod, NesmaIndicativeMethod,
)
from app.core.sizing.cosmic import CosmicMethod


# ── IfpugMethod ──────────────────────────────────────────────────────────────

class TestIfpugMethod:
    def setup_method(self):
        self.m = IfpugMethod()

    def test_size_unit(self):
        assert self.m.size_unit == "FP"

    def test_input_model(self):
        assert self.m.input_model == "ifpug_style"

    def test_ilf_with_det_ret(self):
        # ILF det=10, ret=1 → low → 7 FP
        entry = {"category": "ILF", "det": 10, "ret": 1, "ftr": None}
        assert self.m.compute_entry_size(entry) == 7.0

    def test_ei_with_det_ftr(self):
        # EI det=5, ftr=2 → average → 4 FP
        entry = {"category": "EI", "det": 5, "ftr": 2, "ret": None}
        assert self.m.compute_entry_size(entry) == 4.0

    def test_missing_inputs_fallback_to_average(self):
        # EI 缺 det/ftr → average → 4 FP
        entry = {"category": "EI", "det": None, "ftr": None, "ret": None}
        assert self.m.compute_entry_size(entry) == 4.0


# ── NesmaDetailedMethod ───────────────────────────────────────────────────────

class TestNesmaDetailedMethod:
    def setup_method(self):
        self.m = NesmaDetailedMethod()

    def test_size_unit_and_model(self):
        assert self.m.size_unit == "FP"
        assert self.m.input_model == "ifpug_style"

    def test_same_as_ifpug_for_ilf(self):
        # NESMA 详细级复杂度表与 IFPUG 一致 (GB/T 42588 附录B)
        entry = {"category": "ILF", "det": 10, "ret": 1, "ftr": None}
        from app.core.sizing.ifpug import IfpugMethod
        assert self.m.compute_entry_size(entry) == IfpugMethod().compute_entry_size(entry)


# ── NesmaEstimatedMethod ──────────────────────────────────────────────────────

class TestNesmaEstimatedMethod:
    def setup_method(self):
        self.m = NesmaEstimatedMethod()

    def test_size_unit_and_model(self):
        assert self.m.size_unit == "FP"
        assert self.m.input_model == "ifpug_style"

    def test_ei_average(self):
        # 估算级固定 average → EI average = 4
        entry = {"category": "EI", "det": 999, "ftr": 999}
        assert self.m.compute_entry_size(entry) == 4.0

    def test_ilf_average(self):
        # ILF average = 10
        entry = {"category": "ILF", "det": 1, "ret": 1}
        assert self.m.compute_entry_size(entry) == 10.0

    def test_ignores_det_ret_ftr(self):
        # 不管 det/ret/ftr，均固定 average
        entry = {"category": "EO", "det": None, "ftr": None}
        assert self.m.compute_entry_size(entry) == 5.0


# ── NesmaIndicativeMethod ─────────────────────────────────────────────────────

class TestNesmaIndicativeMethod:
    def setup_method(self):
        self.m = NesmaIndicativeMethod()

    def test_size_unit_and_model(self):
        assert self.m.size_unit == "FP"
        assert self.m.input_model == "ifpug_style"

    def test_ilf_returns_35(self):
        assert self.m.compute_entry_size({"category": "ILF"}) == 35.0

    def test_eif_returns_15(self):
        assert self.m.compute_entry_size({"category": "EIF"}) == 15.0

    def test_transaction_returns_0(self):
        # EI/EO/EQ 不参与预估级计数，返回 0
        for cat in ("EI", "EO", "EQ"):
            assert self.m.compute_entry_size({"category": cat}) == 0.0


# ── CosmicMethod ──────────────────────────────────────────────────────────────

class TestCosmicMethod:
    def setup_method(self):
        self.m = CosmicMethod()

    def test_size_unit(self):
        assert self.m.size_unit == "CFP"

    def test_input_model(self):
        assert self.m.input_model == "cosmic"

    def test_sum_of_four_movements(self):
        entry = {"cosmic_entry": 2, "cosmic_exit": 1,
                 "cosmic_read": 3, "cosmic_write": 2}
        assert self.m.compute_entry_size(entry) == 8.0

    def test_missing_fields_treated_as_zero(self):
        # 信息不足按兜底处理（记 0），不崩溃
        entry = {"cosmic_entry": 1}
        assert self.m.compute_entry_size(entry) == 1.0

    def test_all_none_returns_zero(self):
        entry = {}
        assert self.m.compute_entry_size(entry) == 0.0


# ── 注册表 get_method ─────────────────────────────────────────────────────────

class TestGetMethod:
    def test_returns_ifpug(self):
        assert isinstance(get_method("ifpug"), IfpugMethod)

    def test_returns_nesma_detailed(self):
        assert isinstance(get_method("nesma_detailed"), NesmaDetailedMethod)

    def test_returns_nesma_estimated(self):
        assert isinstance(get_method("nesma_estimated"), NesmaEstimatedMethod)

    def test_returns_nesma_indicative(self):
        assert isinstance(get_method("nesma_indicative"), NesmaIndicativeMethod)

    def test_returns_cosmic(self):
        assert isinstance(get_method("cosmic"), CosmicMethod)

    def test_unknown_raises_value_error(self):
        with pytest.raises(ValueError, match="unknown measurement_method"):
            get_method("quick")
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd server && .venv/bin/python -m pytest tests/unit/test_sizing.py -q
```

预期：`ModuleNotFoundError` — `core/sizing/` 尚未创建。

- [ ] **Step 3: 写最小实现**

3a. `server/app/core/sizing/base.py`

```python
# server/app/core/sizing/base.py
"""SizeMethod 协议：功能规模测量策略的公共接口。"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class SizeMethod(Protocol):
    size_unit: str   # "FP" 或 "CFP"
    input_model: str # "ifpug_style" 或 "cosmic"

    def compute_entry_size(self, entry: dict) -> float:
        """计算单个功能点/功能过程的未调整规模。

        entry 是 FunctionPoint 字段的字典，包含 category/det/ret/ftr
        或 cosmic_entry/exit/read/write，视 input_model 而定。
        信息不足时返回兜底值（average UFP 或 0.0），不抛出异常。
        """
        ...
```

3b. `server/app/core/sizing/ifpug.py`

```python
# server/app/core/sizing/ifpug.py
"""IfpugMethod：复用 core/ifpug.py 的 classify_complexity + fp_value。"""
from ..ifpug import classify_complexity, fp_value


class IfpugMethod:
    size_unit = "FP"
    input_model = "ifpug_style"

    def compute_entry_size(self, entry: dict) -> float:
        """按 IFPUG GB/T 42449 复杂度矩阵查表得 UFP。

        缺少 det/ret/ftr 时回退到 average 复杂度（与 v2.8 _apply_ifpug 行为一致）。
        """
        category = entry.get("category")
        det = entry.get("det")
        ret = entry.get("ret")
        ftr = entry.get("ftr")
        has_input = (
            (category in ("ILF", "EIF") and det is not None and ret is not None)
            or (category in ("EI", "EO", "EQ") and det is not None and ftr is not None)
        )
        if has_input:
            complexity = classify_complexity(category, det, ret, ftr)
        else:
            complexity = "average"
        return float(fp_value(category, complexity))
```

3c. `server/app/core/sizing/nesma.py`

```python
# server/app/core/sizing/nesma.py
"""NESMA 三个精度级别策略（GB/T 42588）。

详细级（nesma_detailed）：按 DET/RET/FTR 查复杂度矩阵，与 IFPUG 一致
（GB/T 42588 附录 B 规范性赋值表）。
估算级（nesma_estimated）：每个功能取「中」复杂度（average），不需 DET/RET/FTR。
预估级（nesma_indicative）：仅数 ILF/EIF，常数 35/15
（NESMA 预估惯用值；实施者应对照 GB/T 42588 附录确认）。
"""
from ..ifpug import classify_complexity, fp_value


class NesmaDetailedMethod:
    """NESMA 详细级：复杂度矩阵与 IFPUG 一致，可直接复用。"""
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
        if has_input:
            complexity = classify_complexity(category, det, ret, ftr)
        else:
            complexity = "average"
        return float(fp_value(category, complexity))


class NesmaEstimatedMethod:
    """NESMA 估算级：固定取「中（average）」复杂度，忽略 DET/RET/FTR。"""
    size_unit = "FP"
    input_model = "ifpug_style"

    def compute_entry_size(self, entry: dict) -> float:
        category = entry.get("category")
        return float(fp_value(category, "average"))


class NesmaIndicativeMethod:
    """NESMA 预估级：仅 ILF=35 / EIF=15，事务类功能返回 0.

    常数 35/15 为 NESMA 预估级惯用值，实施者须对照 GB/T 42588 原文确认。
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
```

3d. `server/app/core/sizing/cosmic.py`

```python
# server/app/core/sizing/cosmic.py
"""CosmicMethod：CFP = 入口 + 出口 + 读 + 写（GB/T 42452-2023）。

每个功能过程理论上至少含一个入口与一个出口或写（GB/T 42452 §规则），
信息不足时该项 CFP 按 0 处理并由 _apply_sizing 记入 trace，不崩溃。
"""


class CosmicMethod:
    size_unit = "CFP"
    input_model = "cosmic"

    def compute_entry_size(self, entry: dict) -> float:
        """CFP = sum(cosmic_entry, cosmic_exit, cosmic_read, cosmic_write)。

        任一字段缺失或 None 按 0 处理。
        """
        return float(
            (entry.get("cosmic_entry") or 0)
            + (entry.get("cosmic_exit") or 0)
            + (entry.get("cosmic_read") or 0)
            + (entry.get("cosmic_write") or 0)
        )
```

3e. `server/app/core/sizing/__init__.py`

```python
# server/app/core/sizing/__init__.py
"""功能规模测量策略注册表。

get_method(measurement_method) 返回对应的 SizeMethod 实例。
"""
from .base import SizeMethod
from .ifpug import IfpugMethod
from .nesma import NesmaDetailedMethod, NesmaEstimatedMethod, NesmaIndicativeMethod
from .cosmic import CosmicMethod

_METHODS: dict[str, SizeMethod] = {
    "ifpug":             IfpugMethod(),
    "nesma_detailed":    NesmaDetailedMethod(),
    "nesma_estimated":   NesmaEstimatedMethod(),
    "nesma_indicative":  NesmaIndicativeMethod(),
    "cosmic":            CosmicMethod(),
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
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd server && .venv/bin/python -m pytest tests/unit/test_sizing.py -q
```

预期：`20 passed`（或更多，视断言数量）。

- [ ] **Step 5: 提交**

```bash
git add server/app/core/sizing/ server/tests/unit/test_sizing.py
git commit -m "feat(core): sizing/ 策略包 — IFPUG / NESMA×3 / COSMIC (v2.9 A2)"
```

---

### Task A3: schemas — measurement_method + cosmic 字段

**Files:**
- Modify: `server/app/schemas/project.py`
- Modify: `server/app/schemas/functions.py`
- Test: `server/tests/integration/test_v2_9_measurement_method.py`

- [ ] **Step 1: 写失败测试（追加到已有文件）**

```python
# 追加到 server/tests/integration/test_v2_9_measurement_method.py

from app.schemas.project import ProjectCreate, ProjectPatch
from app.schemas.functions import FunctionPointBase, FunctionPointPatch


def test_project_create_measurement_method_default():
    """ProjectCreate 默认 measurement_method = nesma_estimated。"""
    p = ProjectCreate(
        name="test", city="北京", industry="全行业", phase="bidding",
        project_type="dev_only", assessment_kind="development",
    )
    assert p.measurement_method == "nesma_estimated"


def test_project_create_cosmic_method():
    """ProjectCreate 接受 measurement_method = cosmic。"""
    p = ProjectCreate(
        name="cosmic-proj", city="北京", industry="全行业", phase="bidding",
        project_type="dev_only", assessment_kind="development",
        measurement_method="cosmic",
    )
    assert p.measurement_method == "cosmic"


def test_project_patch_measurement_method_optional():
    """ProjectPatch 的 measurement_method 是 Optional，可不传。"""
    patch = ProjectPatch()
    assert patch.measurement_method is None
    patch2 = ProjectPatch(measurement_method="ifpug")
    assert patch2.measurement_method == "ifpug"


def test_fp_base_cosmic_fields_default_none():
    """FunctionPointBase 的 cosmic_* 字段默认 None。"""
    fp = FunctionPointBase(
        category="EI", complexity="average", ufp=4.0, us=4.0,
    )
    assert fp.cosmic_entry is None
    assert fp.cosmic_exit is None
    assert fp.cosmic_read is None
    assert fp.cosmic_write is None


def test_fp_base_cosmic_fields_set():
    """FunctionPointBase 可设置 cosmic_* 字段（非负整数）。"""
    fp = FunctionPointBase(
        category="EI", complexity="average", ufp=4.0, us=4.0,
        cosmic_entry=2, cosmic_exit=1, cosmic_read=3, cosmic_write=2,
    )
    assert fp.cosmic_entry == 2
    assert fp.cosmic_write == 2


def test_fp_patch_cosmic_fields():
    """FunctionPointPatch 支持 cosmic_* 可选字段。"""
    patch = FunctionPointPatch(cosmic_entry=1, cosmic_exit=2)
    assert patch.cosmic_entry == 1
    assert patch.cosmic_read is None
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_9_measurement_method.py -q
```

预期：新增的 schema 测试 `FAILED` — `measurement_method` 字段和 `cosmic_*` 字段尚未加入 schema。

- [ ] **Step 3: 写最小实现**

3a. 修改 `server/app/schemas/project.py`

找到 `ProjectCreate` 中的：
```python
    fp_method: Literal["nesma_estimated","ifpug","quick"] = "nesma_estimated"
```
替换为：
```python
    measurement_method: Literal[
        "ifpug", "nesma_indicative", "nesma_estimated", "nesma_detailed", "cosmic"
    ] = "nesma_estimated"
```

找到 `ProjectPatch`（L64-82），在其 Optional 字段块末尾追加：
```python
    measurement_method: Optional[Literal[
        "ifpug", "nesma_indicative", "nesma_estimated", "nesma_detailed", "cosmic"
    ]] = None
```

找到 `ProjectBundleItem`（L111-133），将其中的：
```python
    fp_method: ...
```
替换为：
```python
    measurement_method: Literal[
        "ifpug", "nesma_indicative", "nesma_estimated", "nesma_detailed", "cosmic"
    ] = "nesma_estimated"
```

3b. 修改 `server/app/schemas/functions.py`

在 `FunctionPointBase`（L7-48）的 `ftr` 字段之后、`fp_kind` 之前，追加：
```python
    # v2.9 COSMIC 数据移动字段（可空，仅 cosmic 方法使用）
    cosmic_entry: Optional[int] = Field(default=None, ge=0)
    cosmic_exit:  Optional[int] = Field(default=None, ge=0)
    cosmic_read:  Optional[int] = Field(default=None, ge=0)
    cosmic_write: Optional[int] = Field(default=None, ge=0)
```

在 `FunctionPointPatch`（L62-85）同样追加相同 4 个字段（均为 Optional[int]）：
```python
    cosmic_entry: Optional[int] = Field(default=None, ge=0)
    cosmic_exit:  Optional[int] = Field(default=None, ge=0)
    cosmic_read:  Optional[int] = Field(default=None, ge=0)
    cosmic_write: Optional[int] = Field(default=None, ge=0)
```

确保文件顶部 import 已有 `from pydantic import Field`（v2.8 已有）及 `Optional` 导入。

- [ ] **Step 4: 跑测试确认通过**

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_9_measurement_method.py -q
```

预期：`8 passed`（A1 的 2 个 + A3 新增的 6 个）。

- [ ] **Step 5: 提交**

```bash
git add server/app/schemas/project.py \
        server/app/schemas/functions.py \
        server/tests/integration/test_v2_9_measurement_method.py
git commit -m "feat(schemas): measurement_method + cosmic 字段 (v2.9 A3)"
```

---

### Task A4: _apply_sizing — 方法感知的规模重算

**Files:**
- Modify: `server/app/services/functions.py`
- Test: `server/tests/integration/test_v2_9_measurement_method.py`

- [ ] **Step 1: 写失败测试（追加到已有文件）**

```python
# 追加到 server/tests/integration/test_v2_9_measurement_method.py
# （使用 db_session fixture；按 test_v2_8_ifpug_columns.py 模式内联构造 ORM 对象）

import uuid
from app.db.models import Project, FunctionPoint
from app.services import functions as fn_svc


def _seed_project(db, pid: str, measurement_method: str = "nesma_estimated"):
    p = Project(
        id=pid, name=f"test-{measurement_method}",
        project_type="dev_only", phase="bidding",
        city="北京", industry="电子政务",
        mode="forward", basis_data_ver="SSM-BK-202509",
        assessment_kind="development",
        measurement_method=measurement_method,
    )
    db.add(p)
    db.commit()
    return p


def test_create_fp_under_cosmic_project_uses_cosmic_sizing(client_factory, db_session):
    """cosmic 项目下创建 FP：ufp/us = cosmic_entry + exit + read + write。"""
    _seed_project(db_session, "p-a4-cosmic", measurement_method="cosmic")
    async def _run():
        async with await client_factory() as client:
            r = await client.post(
                "/api/projects/p-a4-cosmic/functions",
                headers={**H, "Content-Type": "application/json"},
                json={
                    "name": "登录", "category": "EI", "complexity": "average",
                    "ufp": 0, "us": 0,
                    "cosmic_entry": 2, "cosmic_exit": 1,
                    "cosmic_read": 1, "cosmic_write": 2,
                },
            )
            assert r.status_code == 201
            data = r.json()["data"]
            assert data["ufp"] == pytest.approx(6.0)
            assert data["us"] == pytest.approx(6.0)
    import asyncio; asyncio.get_event_loop().run_until_complete(_run())


def test_create_fp_under_nesma_estimated_uses_average(client_factory, db_session):
    """nesma_estimated 项目：EO 无论 det/ftr 如何，ufp = 5（average）。"""
    _seed_project(db_session, "p-a4-nesma-est", measurement_method="nesma_estimated")
    async def _run():
        async with await client_factory() as client:
            r = await client.post(
                "/api/projects/p-a4-nesma-est/functions",
                headers={**H, "Content-Type": "application/json"},
                json={
                    "name": "查询报表", "category": "EO", "complexity": "low",
                    "ufp": 4, "us": 4, "det": 999, "ftr": 999,
                },
            )
            assert r.status_code == 201
            assert r.json()["data"]["ufp"] == pytest.approx(5.0)
    import asyncio; asyncio.get_event_loop().run_until_complete(_run())


def test_create_fp_under_ifpug_unchanged(client_factory, db_session):
    """ifpug 项目：行为与 v2.8 _apply_ifpug 一致。"""
    _seed_project(db_session, "p-a4-ifpug", measurement_method="ifpug")
    async def _run():
        async with await client_factory() as client:
            r = await client.post(
                "/api/projects/p-a4-ifpug/functions",
                headers={**H, "Content-Type": "application/json"},
                json={
                    "name": "用户表", "category": "ILF", "complexity": "average",
                    "ufp": 10, "us": 10, "det": 10, "ret": 1,
                },
            )
            assert r.status_code == 201
            data = r.json()["data"]
            # ILF det=10 ret=1 → low → 7 FP
            assert data["ufp"] == pytest.approx(7.0)
    import asyncio; asyncio.get_event_loop().run_until_complete(_run())
```

> **注意：** 测试使用 `client_factory` 和 `db_session` fixture（来自 `server/tests/conftest.py`），通过 HTTP API 创建 FP 并验证后端 `_apply_sizing` 的返回值。ORM 对象（`Project`）用 `_seed_project` 内联构造，不依赖任何不存在的 conftest 辅助函数。文件顶部须确保已定义 `H` 常量（同 `test_v2_8_ifpug_columns.py`）。

- [ ] **Step 2: 跑测试确认失败**

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_9_measurement_method.py::test_create_fp_under_cosmic_project_uses_cosmic_sizing -q
```

预期：`FAILED` — `_apply_ifpug` 不认识 cosmic 方法。

- [ ] **Step 3: 写最小实现**

修改 `server/app/services/functions.py`：

3a. 修改顶部导入，加入 sizing 策略包：
```python
# 替换
from ..core.ifpug import classify_complexity, fp_value
# 为
from ..core.sizing import get_method
from ..core.ifpug import classify_complexity, fp_value  # 保留，供 _apply_sizing 内部使用
```

3b. 将 `_apply_ifpug` 替换为 `_apply_sizing`：
```python
def _apply_sizing(method: str, data: dict) -> dict:
    """按项目 measurement_method 重算 ufp / us，并（部分方法）重算 complexity。

    返回新 dict，不就地修改 data（不可变原则）。
    信息不足时返回原 data 不变；cosmic 方法在 data 不含任何 cosmic_* 时 ufp/us 写 0。
    """
    try:
        method_obj = get_method(method)
    except ValueError:
        # 未知方法：退化到原样返回
        return data

    size = method_obj.compute_entry_size(data)

    if method_obj.input_model == "ifpug_style":
        # 顺便重算 complexity（估算级固定 average，预估级保留原值）
        if method in ("ifpug", "nesma_detailed"):
            cat = data.get("category")
            det, ret, ftr = data.get("det"), data.get("ret"), data.get("ftr")
            has_input = (
                (cat in ("ILF", "EIF") and det is not None and ret is not None)
                or (cat in ("EI", "EO", "EQ") and det is not None and ftr is not None)
            )
            complexity = classify_complexity(cat, det, ret, ftr) if has_input else "average"
        elif method == "nesma_estimated":
            complexity = "average"
        else:
            # nesma_indicative：保留原 complexity 字段
            complexity = data.get("complexity", "average")
        return {**data, "complexity": complexity, "ufp": size, "us": size}

    # cosmic：不修改 complexity；写入 ufp/us（CFP 值）
    return {**data, "ufp": size, "us": size}
```

3c. 修改 `create` 函数：
```python
def create(db: Session, project_id: str, payload: FunctionPointCreate) -> FunctionPoint:
    proj = db.query(Project).filter_by(id=project_id).first()
    if not proj:
        raise ValueError("PROJECT_NOT_FOUND")
    version = _next_version(db, project_id)
    method = getattr(proj, "measurement_method", "nesma_estimated") or "nesma_estimated"
    data = _apply_sizing(method, payload.model_dump())
    fp = FunctionPoint(id=f"fp-{uuid.uuid4().hex[:12]}",
                        project_id=project_id, version=version,
                        **data)
    db.add(fp); db.commit(); db.refresh(fp)
    _mark_results_stale(db, project_id)
    return fp
```

3d. 修改 `patch` 函数，将 `_apply_ifpug(merged)` 替换为：
```python
    proj_obj = db.query(Project).filter_by(id=project_id).first()
    method = getattr(proj_obj, "measurement_method", "nesma_estimated") or "nesma_estimated"
    merged = _apply_sizing(method, merged)
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_9_measurement_method.py -q
```

预期：所有测试（含 A1/A3）全部通过，`11 passed`（含 A1×2 + A3×6 + A4×3）。

- [ ] **Step 5: 提交**

```bash
git add server/app/services/functions.py \
        server/tests/integration/test_v2_9_measurement_method.py
git commit -m "feat(services): _apply_sizing 替换 _apply_ifpug，按方法重算规模 (v2.9 A4)"
```

---

## Phase B — SSM-BK-202509 基准数据

### Task B1: SSM-BK-202509 基准数据 JSON 重建

**Files:**
- Create: `server/app/data/ssm_bk_202509.json`
- Modify: `server/app/config.py`
- Test: `server/tests/integration/test_v2_9_ssm_bk_data.py`

- [ ] **Step 1: 写失败测试（含占位符）**

```python
# server/tests/integration/test_v2_9_ssm_bk_data.py
"""SSM-BK-202509 基准数据 JSON 正确性测试。

实施者须用 Read 工具读取以下 PDF 后，将 <从PDF取> 占位符替换为真实数值：
  doc/《2025年中国软件行业基准数据》.pdf（即 SSM-BK-202509 报告）

注：若文件不在 doc/ 目录，需先确认路径。
"""
import json
from pathlib import Path

DATA_PATH = Path(__file__).parents[3] / "app" / "data" / "ssm_bk_202509.json"


def _load():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_json_is_valid():
    data = _load()
    assert isinstance(data, dict)


def test_version_string():
    data = _load()
    assert data["version"] == "SSM-BK-202509"


def test_top_level_keys_present():
    """保持与 csbmk_202510.json 相同的顶层键结构，确保 EvaluationContext 不变。"""
    data = _load()
    required = {
        "version", "effective_date", "productivity", "city_rate",
        "cf", "factors_dev", "factors_ops", "scale_change",
        "hours_per_pm", "ops_cost_ratio", "display",
    }
    for key in required:
        assert key in data, f"缺少顶层键: {key}"


def test_productivity_dev_industries():
    """productivity.dev 应包含全行业及至少一个分行业键。"""
    data = _load()
    dev_keys = set(data["productivity"]["dev"].keys())
    assert "全行业" in dev_keys
    # SSM-BK-202509 分行业（实施者按 PDF 确认具体行业名，至少有 4 个）
    assert len(dev_keys) >= 2


def test_productivity_dev_bands():
    """每个行业含 P10/P25/P50/P75/P90 五档（或至少 P10/P50/P90）。"""
    data = _load()
    for industry, bands in data["productivity"]["dev"].items():
        for b in ("P10", "P50", "P90"):
            assert b in bands, f"{industry} 缺少 {b} 档"
            assert isinstance(bands[b], (int, float)), f"{industry}.{b} 应为数字"
            assert bands[b] > 0, f"{industry}.{b} 应为正数"


def test_productivity_ops_quan_hanghye():
    """productivity.ops 应有「全行业」键（EvaluationContext.pdr_ops 使用）。"""
    data = _load()
    assert "全行业" in data["productivity"]["ops"]


def test_hours_per_pm():
    data = _load()
    assert data["hours_per_pm"] == 174


# ── 关键数值校验（实施者从 PDF 取数后填入） ──────────────────────────────────
# 使用 Read 工具打开 doc/《2025年中国软件行业基准数据》.pdf
# 找到「全行业软件开发生产率」表，取 P50 行的数值填入下方。

def test_productivity_dev_quanhanghye_p50():
    """全行业开发生产率 P50 与 PDF 一致（实施者填入真实值）。"""
    data = _load()
    actual = data["productivity"]["dev"]["全行业"]["P50"]
    expected = "<从PDF取>"  # 实施者：将此字符串替换为从 PDF 读取的浮点数，例如 6.5
    # 实施者替换后，将下行的注释去掉：
    # assert actual == pytest.approx(expected, rel=0.01)
    assert actual > 0  # 替换前的临时断言，确保数据存在


def test_cf_phases_present():
    """cf 字典含评估阶段键（与 csbmk_202510.json 结构一致）。"""
    data = _load()
    for phase in ("budget", "bidding", "planning", "change", "settled"):
        assert phase in data["cf"], f"cf 缺少阶段 {phase}"
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_9_ssm_bk_data.py -q
```

预期：`FileNotFoundError` — `ssm_bk_202509.json` 尚未创建。

- [ ] **Step 3: 写最小实现**

> **实施者必须执行以下操作：**
>
> 1. 使用 `Read` 工具打开 `doc/《2025年中国软件行业基准数据》.pdf`（逐页读取，建议先读目录页确认结构）。
> 2. 提取以下数据填入 JSON：
>    - `productivity.dev`：全行业及各分行业（电子政务/金融/电信/制造/能源/交通等）P10/P25/P50/P75/P90 开发生产率（FP/人月）
>    - `productivity.ops`：全行业运维生产率 P10/P25/P50/P75/P90（FP/人月）
>    - 若 PDF 含「维护型开发生产率」或「AI+开发生产率」，作为扩展键入库（不改成本流水线，满足 YAGNI）
>    - 若 PDF 含「缺陷密度」，放入 `appendix_c` 扩展键
> 3. `factors_dev`、`factors_ops`、`scale_change`、`cf`、`city_rate`、`appendix_c`（若 PDF 无对应章节）从 `csbmk_202510.json` **原样复制**（保持结构一致）。
> 4. `effective_date` 设为 `"2025-10-01"`（SSM-BK-202509 生效日期）。

JSON 骨架（实施者按 PDF 填充数值后保存）：

```json
{
  "version": "SSM-BK-202509",
  "effective_date": "2025-10-01",
  "productivity": {
    "dev": {
      "全行业":   {"P10": null, "P25": null, "P50": null, "P75": null, "P90": null},
      "电子政务": {"P10": null, "P25": null, "P50": null, "P75": null, "P90": null},
      "金融":     {"P10": null, "P25": null, "P50": null, "P75": null, "P90": null},
      "电信":     {"P10": null, "P25": null, "P50": null, "P75": null, "P90": null},
      "制造":     {"P10": null, "P25": null, "P50": null, "P75": null, "P90": null},
      "能源":     {"P10": null, "P25": null, "P50": null, "P75": null, "P90": null},
      "交通":     {"P10": null, "P25": null, "P50": null, "P75": null, "P90": null}
    },
    "ops": {
      "全行业": {"P10": null, "P25": null, "P50": null, "P75": null, "P90": null}
    }
  },
  "city_rate": "【从 csbmk_202510.json 原样复制 city_rate 字典】",
  "cf": "【从 csbmk_202510.json 原样复制 cf 字典】",
  "factors_dev": "【从 csbmk_202510.json 原样复制 factors_dev】",
  "factors_ops": "【从 csbmk_202510.json 原样复制 factors_ops】",
  "scale_change": "【从 csbmk_202510.json 原样复制 scale_change】",
  "hours_per_pm": 174,
  "ops_cost_ratio": "【从 csbmk_202510.json 原样复制】",
  "display": "【从 csbmk_202510.json 原样复制】",
  "appendix_c": "【从 csbmk_202510.json 原样复制，或用 PDF 缺陷密度数据覆盖】",
  "cfp_to_fp": 1.2
}
```

> **重要：** 上面骨架中用字符串占位的字段（`"【从 csbmk_202510.json ...】"`）需替换为从 `csbmk_202510.json` 读取的真实 JSON 值，`null` 需替换为 PDF 中读取的浮点数。

修改 `server/app/config.py`，将：
```python
csbmk_seed_path = Path(__file__).parent / "data" / "csbmk_202510.json"
```
改为：
```python
csbmk_seed_path = Path(__file__).parent / "data" / "ssm_bk_202509.json"
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_9_ssm_bk_data.py -q
```

预期：所有测试通过（`test_productivity_dev_quanhanghye_p50` 临时断言 `actual > 0` 通过，待实施者填入真实值后改为精确断言）。

完成数值填充后，补充 `test_v2_9_ssm_bk_data.py` 中各关键数值的精确断言（全行业 P10/P50/P90 等），并再次运行确认。

- [ ] **Step 5: 提交**

```bash
git add server/app/data/ssm_bk_202509.json \
        server/app/config.py \
        server/tests/integration/test_v2_9_ssm_bk_data.py
git commit -m "feat(data): SSM-BK-202509 基准数据 + config 切换 (v2.9 B1)"
```

---

### Task B2: cfp_to_fp 换算系数

**Files:**
- Modify: `server/app/data/ssm_bk_202509.json`（B1 已含此字段，若已提交则确认存在）
- Modify: `server/app/core/context.py`
- Modify: `web/src/views/ParamManager.vue`
- Test: `server/tests/integration/test_v2_9_ssm_bk_data.py`
- Test: `server/tests/unit/test_context.py`（新建或追加）

- [ ] **Step 1: 写失败测试**

```python
# 追加到 server/tests/integration/test_v2_9_ssm_bk_data.py

def test_cfp_to_fp_present_and_default():
    """ssm_bk_202509.json 含 cfp_to_fp = 1.2。"""
    data = _load()
    assert "cfp_to_fp" in data
    assert data["cfp_to_fp"] == pytest.approx(1.2)
```

```python
# 追加到 server/tests/unit/test_context.py（若不存在则新建）
"""EvaluationContext 新增属性测试。"""
import pytest
from app.core.context import EvaluationContext, ProjectInputs


def _make_ctx(extra: dict = None) -> EvaluationContext:
    """最小化 ctx，仅含必要键。"""
    import json
    from pathlib import Path
    base = json.loads(
        (Path(__file__).parents[3] / "app" / "data" / "ssm_bk_202509.json").read_text()
    )
    if extra:
        base.update(extra)
    return EvaluationContext.from_dict(
        base, ProjectInputs(industry="全行业", city="北京", phase="bidding")
    )


def test_cfp_to_fp_default():
    """EvaluationContext.cfp_to_fp 返回 1.2（JSON 默认值）。"""
    ctx = _make_ctx()
    assert ctx.cfp_to_fp == pytest.approx(1.2)


def test_cfp_to_fp_override():
    """当 JSON 中 cfp_to_fp = 1.5 时，属性返回 1.5。"""
    ctx = _make_ctx({"cfp_to_fp": 1.5})
    assert ctx.cfp_to_fp == pytest.approx(1.5)


def test_cfp_to_fp_missing_fallback():
    """若 JSON 中不含 cfp_to_fp，属性返回默认 1.2。"""
    ctx = _make_ctx()
    # 删除后重建 raw
    raw = dict(ctx.raw)
    raw.pop("cfp_to_fp", None)
    ctx2 = EvaluationContext.from_dict(raw, ctx.inputs)
    assert ctx2.cfp_to_fp == pytest.approx(1.2)
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_9_ssm_bk_data.py::test_cfp_to_fp_present_and_default tests/unit/test_context.py -q
```

预期：`AttributeError: 'EvaluationContext' object has no attribute 'cfp_to_fp'`。

- [ ] **Step 3: 写最小实现**

3a. 确认 `ssm_bk_202509.json` 已含 `"cfp_to_fp": 1.2`（B1 骨架已有，确认即可）。

3b. 修改 `server/app/core/context.py`，在 `hours_per_pm` 属性之后追加：

```python
    @property
    def cfp_to_fp(self) -> float:
        """COSMIC CFP → FP 当量换算系数。默认 1.2（1 NESMA-FP ≈ 1.2 CFP）。

        可在全局参数页（ParamManager）草稿编辑覆盖。
        """
        return float(self.raw.get("cfp_to_fp", 1.2))
```

3c. 修改 `web/src/views/ParamManager.vue`

找到「规模变更」tab（`scale_change` 相关区域）。在该 tab 的 OverrideField 列表末尾，追加一个 `cfp_to_fp` 字段的覆盖项（沿用现有 OverrideField 组件写法）：

```html
<!-- 在 scale_change tab 内，其他 OverrideField 之后追加 -->
<OverrideField
  leaf-key="cfp_to_fp"
  label="CFP→FP 换算系数"
  description="COSMIC CFP 转 FP 当量的系数（默认 1.2，即 1 NESMA-FP ≈ 1.2 CFP）"
/>
```

> 实施者注：参考现有 OverrideField 的 props 签名与所在位置（如 `scale_change` section），保持一致的嵌套层级和绑定方式。

- [ ] **Step 4: 跑测试确认通过**

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_9_ssm_bk_data.py tests/unit/test_context.py -q
```

预期：全部通过。

- [ ] **Step 5: 提交**

```bash
git add server/app/core/context.py \
        server/app/data/ssm_bk_202509.json \
        server/tests/integration/test_v2_9_ssm_bk_data.py \
        server/tests/unit/test_context.py \
        web/src/views/ParamManager.vue
git commit -m "feat(core/web): cfp_to_fp 换算系数属性 + ParamManager 暴露 (v2.9 B2)"
```

---

## Phase A（续）— 计算层、前端、AI 提取、报告

### Task A5: calc.py forward/reverse 按方法接入 + COSMIC 换算

**Files:**
- Modify: `server/app/core/forward.py`
- Modify: `server/app/services/calc.py`
- Test: `server/tests/integration/test_v2_9_calc_methods.py`

- [ ] **Step 1: 写失败测试**

```python
# server/tests/integration/test_v2_9_calc_methods.py
"""多方法 forward/reverse 计算集成测试（v2.9 A5）。"""
import pytest
from app.core.forward import ForwardInput, FpItem, calculate_forward
from app.core.context import EvaluationContext, ProjectInputs
from app.services import calc as calc_svc

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


def _seed(db, pid: str, measurement_method: str = "nesma_estimated",
          industry: str = "全行业", city: str = "北京", phase: str = "bidding"):
    from app.db.models import Project
    p = Project(
        id=pid, name=f"calc-test-{pid}",
        project_type="dev_only", phase=phase,
        city=city, industry=industry,
        mode="forward", basis_data_ver="SSM-BK-202509",
        assessment_kind="development",
        measurement_method=measurement_method,
    )
    db.add(p)
    db.commit()
    return p


def _make_ctx(cfp_to_fp: float = 1.2) -> EvaluationContext:
    import json
    from pathlib import Path
    raw = json.loads(
        (Path(__file__).parents[3] / "app" / "data" / "ssm_bk_202509.json").read_text()
    )
    raw["cfp_to_fp"] = cfp_to_fp
    return EvaluationContext.from_dict(
        raw, ProjectInputs(industry="全行业", city="北京", phase="bidding")
    )


class TestForwardDeclaration:
    """ForwardInput.size_declaration 控制 trace fp_count_declaration。"""

    def test_default_declaration_is_ifpug(self):
        ctx = _make_ctx()
        inp = ForwardInput(
            items=[FpItem(us=10.0)],
            size_declaration="FP (IFPUG-GB/T 42449-2023)",
        )
        result = calculate_forward(ctx, inp)
        assert "IFPUG" in result.trace["fp_count_declaration"]

    def test_nesma_estimated_declaration(self):
        ctx = _make_ctx()
        inp = ForwardInput(
            items=[FpItem(us=10.0)],
            size_declaration="FP (NESMA-GB/T 42588-2023, 估算级)",
        )
        result = calculate_forward(ctx, inp)
        assert "NESMA" in result.trace["fp_count_declaration"]

    def test_cosmic_declaration(self):
        ctx = _make_ctx()
        inp = ForwardInput(
            items=[FpItem(us=10.0)],
            size_declaration="CFP (COSMIC-GB/T 42452-2023)",
        )
        result = calculate_forward(ctx, inp)
        assert "COSMIC" in result.trace["fp_count_declaration"]


class TestCosmicCfpConversion:
    """COSMIC 项目：CFP ÷ cfp_to_fp 得 FP 当量后再算成本。"""

    def test_cosmic_forward_uses_cfp_conversion(self, db_session):
        """cosmic 项目 forward：ufp=12 CFP, cfp_to_fp=1.2 → scale_us=10 FP 等量。"""
        from app.db.models import FunctionPoint
        _seed(db_session, "p-a5-cosmic", measurement_method="cosmic")
        db_session.add(FunctionPoint(
            id="fp-a5-cosmic-1", project_id="p-a5-cosmic", version=1,
            category="EI", complexity="average", modify_type="add",
            ufp=12, us=12,
            cosmic_entry=3, cosmic_exit=3, cosmic_read=3, cosmic_write=3,
        ))
        db_session.commit()
        result = calc_svc.run_forward(db_session, "p-a5-cosmic", {})
        # 12 CFP ÷ 1.2 = 10 FP 等量
        assert result["scale_us"] == pytest.approx(10.0, rel=0.01)

    def test_nesma_forward_not_converted(self, db_session):
        """nesma_estimated 项目：us 直接用，不除 cfp_to_fp。"""
        from app.db.models import FunctionPoint
        _seed(db_session, "p-a5-nesma", measurement_method="nesma_estimated")
        db_session.add(FunctionPoint(
            id="fp-a5-nesma-1", project_id="p-a5-nesma", version=1,
            category="EO", complexity="average", modify_type="add",
            ufp=5, us=5,
        ))
        db_session.commit()
        result = calc_svc.run_forward(db_session, "p-a5-nesma", {})
        assert result["scale_us"] == pytest.approx(5.0, rel=0.01)


def test_declaration_helper_covers_all_methods():
    """_declaration_for 覆盖所有 5 种方法，不抛异常。"""
    from app.services.calc import _declaration_for
    for m in ("ifpug", "nesma_detailed", "nesma_estimated", "nesma_indicative", "cosmic"):
        decl = _declaration_for(m)
        assert isinstance(decl, str) and len(decl) > 0
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_9_calc_methods.py -q
```

预期：`ImportError` 或 `AttributeError` — `ForwardInput` 无 `size_declaration`，`_declaration_for` 不存在。

- [ ] **Step 3: 写最小实现**

3a. 修改 `server/app/core/forward.py`，在 `ForwardInput` 中追加字段（在 `assessment_kind` 之后）：

```python
    # v2.9：测量方法声明字符串，由 calc.py 按 measurement_method 注入，
    # 显示在 trace["fp_count_declaration"]。
    size_declaration: str = "FP (IFPUG-GB/T 42449-2023)"
```

在 `calculate_forward` 函数内，找到：
```python
        "fp_count_declaration": f"{us:g} FP (IFPUG-GB/T 42449-2023)",
```
替换为：
```python
        "fp_count_declaration": f"{us:g} {inp.size_declaration}",
```

3b. 修改 `server/app/services/calc.py`，在文件顶部 import 区追加：

```python
from ..core.sizing import get_method as _get_sizing_method
```

在文件适当位置（`run_forward` 之前）添加辅助函数：

```python
_METHOD_DECLARATION = {
    "ifpug":            "FP (IFPUG-GB/T 42449-2023)",
    "nesma_detailed":   "FP (NESMA-GB/T 42588-2023, 详细级)",
    "nesma_estimated":  "FP (NESMA-GB/T 42588-2023, 估算级)",
    "nesma_indicative": "FP (NESMA-GB/T 42588-2023, 预估级)",
    "cosmic":           "CFP (COSMIC-GB/T 42452-2023)",
}


def _declaration_for(measurement_method: str) -> str:
    """返回 measurement_method 对应的规模声明字符串。"""
    return _METHOD_DECLARATION.get(measurement_method, "FP (IFPUG-GB/T 42449-2023)")
```

修改 `_resolve_items`，增加 `cfp_to_fp` 换算参数：

```python
def _resolve_items(
    db: Session, project_id: str, payload: dict,
    mode: str = "forward",
    cfp_to_fp: float = 1.2,
    is_cosmic: bool = False,
) -> list[FpItem]:
    """获取 FpItem 列表。cosmic 项目：us / cfp_to_fp 得 FP 当量。"""
    raw_items = payload.get("items")
    if raw_items:
        items = [FpItem(us=i["us"], modify_type=i.get("modify_type", "add"))
                 for i in raw_items]
    else:
        db_items = fs.list_for_project(db, project_id)
        if not db_items and mode == "forward":
            raise ValueError(
                "NO_FUNCTION_POINTS: 项目暂无功能点，请先在 FP 编辑屏添加或上传文档让 AI 提取"
            )
        items = [FpItem(us=fp.us, modify_type=fp.modify_type or "add") for fp in db_items]

    if is_cosmic and cfp_to_fp and cfp_to_fp != 0:
        items = [FpItem(us=item.us / cfp_to_fp, modify_type=item.modify_type)
                 for item in items]
    return items
```

修改 `run_forward`，读取 `measurement_method` 并传入：

```python
def run_forward(db: Session, project_id: str, payload: dict) -> dict:
    proj = db.query(Project).filter_by(id=project_id).first()
    if not proj:
        raise ValueError("PROJECT_NOT_FOUND")
    eff = ps.get_effective(db, project_id)
    ctx = EvaluationContext.from_dict(
        ps.effective_to_calc_dict(eff),
        ProjectInputs(industry=proj.industry, city=proj.city, phase=proj.phase),
    )
    method = getattr(proj, "measurement_method", "nesma_estimated") or "nesma_estimated"
    is_cosmic = (method == "cosmic")
    dev_factor, ops_factor, warnings = _resolve_factors(proj, eff, payload)
    inp = ForwardInput(
        items=_resolve_items(db, project_id, payload, mode="forward",
                             cfp_to_fp=ctx.cfp_to_fp, is_cosmic=is_cosmic),
        dev_factor=dev_factor,
        ops_factor=ops_factor,
        include_dev=payload.get("include_dev", True),
        include_ops=payload.get("include_ops", proj.include_ops or False),
        other_cost=payload.get("other_cost", proj.other_cost or 0.0),
        assessment_kind=getattr(proj, "assessment_kind", None) or "development",
        size_declaration=_declaration_for(method),
    )
    r = calculate_forward(ctx, inp)
    out = r.__dict__.copy()
    out["warning_messages"] = list(out.get("warning_messages") or []) + warnings
    return out
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_9_calc_methods.py -q
```

预期：全部通过（COSMIC 换算、声明字符串、辅助函数均通过）。

- [ ] **Step 5: 提交**

```bash
git add server/app/core/forward.py \
        server/app/services/calc.py \
        server/tests/integration/test_v2_9_calc_methods.py
git commit -m "feat(calc): 多方法规模接入 + COSMIC CFP÷cfp_to_fp 换算 (v2.9 A5)"
```

---

### Task A6: FpFormModal + FpEditor 按方法切换表单

**Files:**
- Modify: `web/src/views/FpEditor.vue`
- Modify: `web/src/components/fp/FpFormModal.vue`
- Test: `web/src/__tests__/FpFormModal-methods.test.ts`

- [ ] **Step 1: 写失败测试**

```typescript
// web/src/__tests__/FpFormModal-methods.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import FpFormModal from "@/components/fp/FpFormModal.vue";

const mockFunctionsApi = { create: vi.fn(), patch: vi.fn() };
vi.mock("@/api/functions", () => ({ functionsApi: mockFunctionsApi }));

function mountModal(measurementMethod: string, editing = null) {
  return mount(FpFormModal, {
    props: { open: true, projectId: "p1", editing, measurementMethod },
  });
}

describe("FpFormModal — ifpug/nesma_detailed 方法", () => {
  it("渲染 DET / RET / FTR 输入", () => {
    const w = mountModal("ifpug");
    expect(w.find("[data-testid='input-det']").exists()).toBe(true);
    expect(w.find("[data-testid='input-ret']").exists()).toBe(true);
    expect(w.find("[data-testid='input-ftr']").exists()).toBe(true);
  });

  it("nesma_detailed 同样渲染 DET/RET/FTR", () => {
    const w = mountModal("nesma_detailed");
    expect(w.find("[data-testid='input-det']").exists()).toBe(true);
  });
});

describe("FpFormModal — nesma_estimated 方法", () => {
  it("不渲染 DET/RET/FTR", () => {
    const w = mountModal("nesma_estimated");
    expect(w.find("[data-testid='input-det']").exists()).toBe(false);
  });

  it("复杂度显示固定为 '中'", () => {
    const w = mountModal("nesma_estimated");
    expect(w.text()).toContain("中");
  });
});

describe("FpFormModal — nesma_indicative 方法", () => {
  it("category 仅渲染 ILF / EIF 选项", () => {
    const w = mountModal("nesma_indicative");
    const options = w.findAll("[data-testid='category-option']");
    const values = options.map((o) => o.attributes("value") ?? o.text().trim());
    expect(values).toContain("ILF");
    expect(values).toContain("EIF");
    // 事务类不应出现
    expect(values).not.toContain("EI");
  });
});

describe("FpFormModal — cosmic 方法", () => {
  it("渲染 4 个数据移动输入", () => {
    const w = mountModal("cosmic");
    expect(w.find("[data-testid='input-cosmic-entry']").exists()).toBe(true);
    expect(w.find("[data-testid='input-cosmic-exit']").exists()).toBe(true);
    expect(w.find("[data-testid='input-cosmic-read']").exists()).toBe(true);
    expect(w.find("[data-testid='input-cosmic-write']").exists()).toBe(true);
  });

  it("实时显示 CFP = 入口 + 出口 + 读 + 写", async () => {
    const w = mountModal("cosmic");
    await w.find("[data-testid='input-cosmic-entry']").setValue("2");
    await w.find("[data-testid='input-cosmic-exit']").setValue("1");
    await w.find("[data-testid='input-cosmic-read']").setValue("3");
    await w.find("[data-testid='input-cosmic-write']").setValue("2");
    expect(w.find("[data-testid='cfp-total']").text()).toContain("8");
  });

  it("提交时 payload 含 cosmic_entry/exit/read/write", async () => {
    const w = mountModal("cosmic");
    await w.find("[data-testid='input-name']").setValue("登录");
    await w.find("[data-testid='input-cosmic-entry']").setValue("1");
    await w.find("[data-testid='input-cosmic-exit']").setValue("1");
    await w.find("[data-testid='input-cosmic-read']").setValue("1");
    await w.find("[data-testid='input-cosmic-write']").setValue("1");
    await w.find("form").trigger("submit");
    expect(mockFunctionsApi.create).toHaveBeenCalledWith(
      "p1",
      expect.objectContaining({
        cosmic_entry: 1,
        cosmic_exit: 1,
        cosmic_read: 1,
        cosmic_write: 1,
      }),
    );
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd web && npx vitest run src/__tests__/FpFormModal-methods.test.ts
```

预期：测试失败 — `FpFormModal` 不接受 `measurementMethod` prop，亦无 cosmic 输入区。

- [ ] **Step 3: 写最小实现**

3a. 修改 `web/src/components/fp/FpFormModal.vue`

在 `props` 定义中追加 `measurementMethod`：
```typescript
const props = defineProps<{
  open: boolean;
  projectId: string;
  editing?: FunctionPoint | null;
  measurementMethod?: string;   // v2.9: 由 FpEditor 传入
}>();
```

在 script 区追加 cosmic 相关 refs：
```typescript
const cosmicEntry = ref<number | null>(null);
const cosmicExit  = ref<number | null>(null);
const cosmicRead  = ref<number | null>(null);
const cosmicWrite = ref<number | null>(null);

const isCosmic = computed(() => props.measurementMethod === "cosmic");
const isIfpugStyle = computed(() =>
  ["ifpug", "nesma_detailed"].includes(props.measurementMethod ?? "nesma_estimated")
);
const isNesmaEstimated = computed(() => props.measurementMethod === "nesma_estimated");
const isNesmaIndicative = computed(() => props.measurementMethod === "nesma_indicative");

const cosmicCfpTotal = computed(() =>
  (cosmicEntry.value ?? 0) + (cosmicExit.value ?? 0)
  + (cosmicRead.value ?? 0) + (cosmicWrite.value ?? 0)
);

const INDICATIVE_CATEGORIES: FpCategory[] = ["ILF", "EIF"];
const effectiveCategories = computed<FpCategory[]>(() =>
  isNesmaIndicative.value ? INDICATIVE_CATEGORIES : CATEGORIES
);
```

在 `resetForm` / `prefillForm` 中加入 cosmic 字段的重置与预填逻辑（参照 det/ret/ftr 模式）。

在 `onSubmit` 中，构造 payload 时：
- `isCosmic.value` 时：包含 `cosmic_entry/exit/read/write`（将 null 替换为 0），不包含 `det/ret/ftr`
- `isNesmaEstimated.value` 时：`complexity` 固定为 `"average"`，不包含 `det/ret/ftr`
- `isNesmaIndicative.value` 时：不包含 `det/ret/ftr`

在模板中，按 computed 条件渲染：
```html
<!-- DET/RET/FTR 区域：仅 ifpug / nesma_detailed 显示 -->
<template v-if="isIfpugStyle">
  <input data-testid="input-det" ... />
  <input data-testid="input-ret" ... />
  <input data-testid="input-ftr" ... />
</template>

<!-- nesma_estimated：显示固定"中"提示 -->
<template v-else-if="isNesmaEstimated">
  <p>复杂度：中（估算级固定）</p>
</template>

<!-- cosmic：4 个数据移动输入 + CFP 合计 -->
<template v-else-if="isCosmic">
  <input data-testid="input-cosmic-entry" type="number" v-model.number="cosmicEntry" />
  <input data-testid="input-cosmic-exit"  type="number" v-model.number="cosmicExit"  />
  <input data-testid="input-cosmic-read"  type="number" v-model.number="cosmicRead"  />
  <input data-testid="input-cosmic-write" type="number" v-model.number="cosmicWrite" />
  <span data-testid="cfp-total">CFP 合计：{{ cosmicCfpTotal }}</span>
</template>

<!-- category 选项：nesma_indicative 只显示 ILF / EIF -->
<select v-model="category">
  <option v-for="cat in effectiveCategories" :key="cat"
          data-testid="category-option" :value="cat">{{ cat }}</option>
</select>

<!-- name 输入（cosmic 模式下标签改为「功能过程名」） -->
<input data-testid="input-name" ... />
```

3b. 修改 `web/src/views/FpEditor.vue`

在 `onMounted` 或顶部 ref 区追加：
```typescript
import { projectsApi, type Project } from "@/api/projects";
const project = ref<Project | null>(null);
```

在 `onMounted` 中加载项目：
```typescript
onMounted(async () => {
  project.value = await projectsApi.get(props.projectId);
  // ... 原有 loadFunctions() 逻辑
});
```

在模板的 `<FpFormModal>` 上传入 prop：
```html
<FpFormModal
  :open="fpFormOpen"
  :project-id="props.projectId"
  :editing="editingFp"
  :measurement-method="project?.measurement_method ?? 'nesma_estimated'"
  @update:open="fpFormOpen = $event"
  @saved="loadFunctions"
/>
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd web && npx vitest run src/__tests__/FpFormModal-methods.test.ts && npx vue-tsc --noEmit
```

预期：所有测试通过，TypeScript 无错误。

- [ ] **Step 5: 提交**

```bash
git add web/src/components/fp/FpFormModal.vue \
        web/src/views/FpEditor.vue \
        web/src/__tests__/FpFormModal-methods.test.ts
git commit -m "feat(web/fp): FpFormModal 按方法切换录入区 + FpEditor 传递方法 (v2.9 A6)"
```

---

### Task A7: ProjectWizard 方法选择 + 切换警告 + projects.ts 类型

**Files:**
- Modify: `web/src/api/projects.ts`
- Modify: `web/src/views/ProjectWizard.vue`
- Test: `web/src/__tests__/ProjectWizard-steps.test.ts`

- [ ] **Step 1: 写失败测试（追加到现有文件）**

```typescript
// 追加到 web/src/__tests__/ProjectWizard-steps.test.ts

describe("ProjectWizard — measurement_method 字段 (v2.9)", () => {
  it("Step 2 渲染 5 个方法选项", async () => {
    const w = mountWizard();           // 沿用文件中现有的 mountWizard 辅助函数
    await advanceToStep(w, 2);         // 沿用现有 advanceToStep 辅助
    const options = w.findAll("[data-testid='method-option']");
    expect(options).toHaveLength(5);
    const values = options.map((o) => o.attributes("value") ?? o.element.getAttribute("value"));
    expect(values).toContain("ifpug");
    expect(values).toContain("nesma_indicative");
    expect(values).toContain("nesma_estimated");
    expect(values).toContain("nesma_detailed");
    expect(values).toContain("cosmic");
  });

  it("默认选中 nesma_estimated", async () => {
    const w = mountWizard();
    await advanceToStep(w, 2);
    const selected = w.find("[data-testid='method-option'][value='nesma_estimated']");
    // radio 类型：检查 checked
    expect((selected.element as HTMLInputElement).checked).toBe(true);
  });

  it("提交 payload 包含 measurement_method", async () => {
    const mockCreate = vi.fn().mockResolvedValue({ id: "p1" });
    vi.mocked(projectsApi.create).mockImplementation(mockCreate);
    const w = mountWizard();
    // 完成向导提交（沿用现有 fillAndSubmit 辅助或手动模拟）
    await fillAndSubmit(w, { measurement_method: "cosmic" });
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({ measurement_method: "cosmic" }),
    );
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd web && npx vitest run src/__tests__/ProjectWizard-steps.test.ts -t "measurement_method"
```

预期：测试失败 — `FormState` 无 `measurement_method`，向导无 5 选项。

- [ ] **Step 3: 写最小实现**

3a. 修改 `web/src/api/projects.ts`

找到 `Project` interface，将：
```typescript
  fp_method?: "nesma_estimated" | "ifpug" | "quick";
```
替换为：
```typescript
  measurement_method?: "ifpug" | "nesma_indicative" | "nesma_estimated" | "nesma_detailed" | "cosmic";
```

同样更新 `ProjectBundleItem` interface 中对应字段。

3b. 修改 `web/src/views/ProjectWizard.vue`

在 `FormState` interface 中追加：
```typescript
  measurement_method: "ifpug" | "nesma_indicative" | "nesma_estimated" | "nesma_detailed" | "cosmic";
```

在 `form` reactive 初始化中追加默认值：
```typescript
  measurement_method: "nesma_estimated",
```

在 Step 2 区域（`assessment_kind` radios 附近），追加方法选择器：
```html
<!-- measurement_method 选择（Step 2，参照 assessment_kind 的位置与样式） -->
<div class="field-group">
  <label>功能规模测量方法</label>
  <div class="radio-group">
    <label v-for="opt in METHOD_OPTIONS" :key="opt.value">
      <input
        type="radio"
        data-testid="method-option"
        :value="opt.value"
        v-model="form.measurement_method"
      />
      <span>{{ opt.label }}</span>
      <small>{{ opt.hint }}</small>
    </label>
  </div>
</div>
```

在 script 中定义选项：
```typescript
const METHOD_OPTIONS = [
  { value: "nesma_estimated",  label: "NESMA 估算级",  hint: "按类别取平均复杂度（推荐初期估算）" },
  { value: "nesma_detailed",   label: "NESMA 详细级",  hint: "按 DET/RET/FTR 精确查表（GB/T 42588）" },
  { value: "nesma_indicative", label: "NESMA 预估级",  hint: "仅数 ILF/EIF 数量（最快速估算）" },
  { value: "ifpug",            label: "IFPUG",         hint: "按 DET/RET/FTR 查表（GB/T 42449）" },
  { value: "cosmic",           label: "COSMIC",        hint: "按数据移动计数（GB/T 42452）" },
] as const;
```

在 submit 函数中，将 `measurement_method` 加入 payload（沿用其他字段的模式）。

在 EDIT 模式下，当 `form.measurement_method` 从/到 `"cosmic"` 切换时，在提交前弹出警告：
```typescript
// 在 submit 函数开头，判断是否跨录入模型切换
const originalMethod = props.projectId
  ? store.projects.find((p) => p.id === props.projectId)?.measurement_method
  : undefined;
const changingToCosmic = form.measurement_method === "cosmic" && originalMethod !== "cosmic";
const changingFromCosmic = form.measurement_method !== "cosmic" && originalMethod === "cosmic";
if ((changingToCosmic || changingFromCosmic) && hasFps) {
  const ok = window.confirm(
    "切换测量方法将导致录入模型不同（COSMIC ↔ 其他方法），\n" +
    "已有 FP 数据将保留但不参与新方法的计算，请重新录入对应格式的功能点。\n\n" +
    "确认切换？"
  );
  if (!ok) return;
}
```

> 注：`hasFps` 可通过检查项目 FP 列表长度或由 FpEditor store 提供，实施者根据现有数据获取方式实现。

- [ ] **Step 4: 跑测试确认通过**

```bash
cd web && npx vitest run src/__tests__/ProjectWizard-steps.test.ts && npx vue-tsc --noEmit
```

预期：原有测试 + 新增 measurement_method 测试全部通过，无 TS 错误。

- [ ] **Step 5: 提交**

```bash
git add web/src/api/projects.ts \
        web/src/views/ProjectWizard.vue \
        web/src/__tests__/ProjectWizard-steps.test.ts
git commit -m "feat(web/wizard): measurement_method 方法选择器 + 跨模型切换警告 (v2.9 A7)"
```

---

### Task A8: cost.md AI 提取按方法分支

**Files:**
- Modify: `commands/cost.md`

- [ ] **Step 1: 写失败测试（不可自动化，明确 Review Checklist）**

本任务为 markdown 命令文件编辑，无法用 vitest/pytest 自动验证。

**人工验收清单（实施后对照检查）：**
- [ ] Branch B Step 3 之前，已有 `GET /api/projects/{id}` 读取 `measurement_method` 的步骤
- [ ] extract prompt 中存在 IFPUG/NESMA 分支（保留原有 5 类功能 + DET/RET/FTR 提取逻辑）
- [ ] extract prompt 中存在 COSMIC 分支（提取功能过程名 + entry/exit/read/write 计数）
- [ ] bulk-write 时，COSMIC 分支的 item 包含 `cosmic_entry/exit/read/write` 字段
- [ ] bulk-write 时，COSMIC 分支的 `source` 仍为 `"claude_draft"`

- [ ] **Step 2: 写最小实现**

修改 `commands/cost.md` Branch B，在 Step 3（extract prompt 步骤）之前插入：

```markdown
**Step 2b: 读取项目测量方法**

\`\`\`bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:$PORT/api/projects/$PROJECT_ID" \
  | jq -r '.measurement_method // "nesma_estimated"'
\`\`\`

将结果存入变量 `MEASUREMENT_METHOD`。
```

在 Step 3 的 extract prompt 中，按 `$MEASUREMENT_METHOD` 分支：

**IFPUG / NESMA 分支**（`MEASUREMENT_METHOD` != `"cosmic"`，保留原有提取逻辑不变）：
- 提取 5 类功能（EI/EO/EQ/ILF/EIF）
- 提取 DET/RET/FTR 数量
- 按原有 UFP 表计算 ufp/us
- bulk item 字段：`name/category/det/ret/ftr/ufp/us/subsystem/l1_module/l2_module/description/source:"claude_draft"`

**COSMIC 分支**（`MEASUREMENT_METHOD` == `"cosmic"`）：

在 extract prompt 中增加 COSMIC 提取指令：
```
项目使用 COSMIC 功能规模测量方法（GB/T 42452-2023）。
请从文档中识别功能过程（Functional Process），对每个功能过程：
1. 名称（功能过程名，如「用户登录」「生成报告」）
2. 数据移动计数：
   - Entry（入口）：触发功能过程的数据移动
   - Exit（出口）：从软件流出的数据移动
   - Read（读）：从持久存储读取数据
   - Write（写）：向持久存储写入数据
3. 子系统 / 一级模块 / 二级模块分类

输出格式为 JSON 数组，每个元素：
{
  "name": "<功能过程名>",
  "description": "<简短描述>",
  "subsystem": "<子系统>",
  "l1_module": "<一级模块>",
  "l2_module": "<二级模块>",
  "category": "EI",          // COSMIC 模式下占位，固定 EI
  "complexity": "average",   // COSMIC 模式下占位
  "ufp": 0,                  // 后端按 cosmic_* 字段重算
  "us": 0,
  "cosmic_entry": <数量>,
  "cosmic_exit": <数量>,
  "cosmic_read": <数量>,
  "cosmic_write": <数量>,
  "fp_kind": "dev",
  "source": "claude_draft"
}
```

在 Step 4（bulk write）中按方法使用对应 item 结构（COSMIC item 含 `cosmic_entry/exit/read/write`）。

- [ ] **Step 3: 跑测试（人工验收）**

按上述清单逐条核对 `commands/cost.md` 的修改内容。

- [ ] **Step 4: 提交**

```bash
git add commands/cost.md
git commit -m "feat(commands): cost.md AI 提取按方法分支 — COSMIC 数据移动 (v2.9 A8)"
```

---

### Task A9: 报告体现方法

**Files:**
- Modify: `server/app/exporters/report_builder.py`
- Modify: `server/app/services/reports.py`
- Test: `server/tests/integration/test_v2_9_report_method.py`

- [ ] **Step 1: 写失败测试**

```python
# server/tests/integration/test_v2_9_report_method.py
"""报告方法声明测试（v2.9 A9）。"""
import pytest
from pathlib import Path
import tempfile
from openpyxl import load_workbook
from app.db.models import Project, FunctionPoint

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


def _seed(db, pid: str, measurement_method: str = "nesma_estimated",
          industry: str = "全行业", city: str = "北京", phase: str = "bidding"):
    p = Project(
        id=pid, name=f"report-test-{pid}",
        project_type="dev_only", phase=phase,
        city=city, industry=industry,
        mode="forward", basis_data_ver="SSM-BK-202509",
        assessment_kind="development",
        measurement_method=measurement_method,
    )
    db.add(p)
    db.commit()
    return p


def _export_report(db, project_id: str) -> Path:
    """调用现有 generate_excel 接口，返回 Excel 文件路径。"""
    from app.services.reports import generate_excel
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "report.xlsx"
        generate_excel(db, project_id, out)
        return out


def test_nesma_estimated_report_declaration(db_session):
    """nesma_estimated 项目报告：声明含 NESMA。"""
    _seed(db_session, "p-a9-nesma", measurement_method="nesma_estimated")
    db_session.add(FunctionPoint(
        id="fp-a9-nesma-1", project_id="p-a9-nesma", version=1,
        category="EO", complexity="average", modify_type="add",
        ufp=5, us=5,
    ))
    db_session.commit()
    out = _export_report(db_session, "p-a9-nesma")
    wb = load_workbook(str(out))
    # 检查「评估结果汇总」或「评估报告书」sheet 中包含 NESMA 声明
    found = False
    for ws_name in wb.sheetnames:
        ws = wb[ws_name]
        for row in ws.iter_rows(values_only=True):
            for cell in row:
                if cell and "NESMA" in str(cell):
                    found = True
                    break
    assert found, "报告中未找到 NESMA 声明"


def test_cosmic_report_declaration_and_conversion_note(db_session):
    """cosmic 项目报告：声明含 COSMIC，并有 CFP→FP 换算备注。"""
    _seed(db_session, "p-a9-cosmic", measurement_method="cosmic")
    db_session.add(FunctionPoint(
        id="fp-a9-cosmic-1", project_id="p-a9-cosmic", version=1,
        category="EI", complexity="average", modify_type="add",
        ufp=8, us=8,
        cosmic_entry=2, cosmic_exit=2, cosmic_read=2, cosmic_write=2,
    ))
    db_session.commit()
    out = _export_report(db_session, "p-a9-cosmic")
    wb = load_workbook(str(out))
    text_cells: list[str] = []
    for ws_name in wb.sheetnames:
        ws = wb[ws_name]
        for row in ws.iter_rows(values_only=True):
            for cell in row:
                if cell:
                    text_cells.append(str(cell))
    full_text = " ".join(text_cells)
    assert "COSMIC" in full_text, "报告中未找到 COSMIC 声明"
    assert "cfp_to_fp" in full_text.lower() or "换算" in full_text, \
        "COSMIC 项目报告未包含换算备注"
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_9_report_method.py -q
```

预期：`FAILED` — 报告暂不含 NESMA/COSMIC 声明。

- [ ] **Step 3: 写最小实现**

3a. 修改 `server/app/services/reports.py`

找到调用 `calculate_forward`（或 `run_forward`）后构建 `figures` 字典的位置，确保 `figures` 中含有 `trace` → `fp_count_declaration`（v2.9 A5 已由 `run_forward` 注入，此处直接透传）。

找到调用 `build_report(...)` 的位置，追加 `measurement_method` 参数：
```python
build_report(
    out_path,
    project=proj,
    functions=fps,
    figures=figures,
    is_reverse=is_reverse,
    target_cost_wan=target_cost_wan,
    selected_band=selected_band,
    measurement_method=getattr(proj, "measurement_method", "nesma_estimated"),
    cfp_to_fp=ctx.cfp_to_fp,  # 从 ctx 取，A5 已将 ctx 构建逻辑封装好
)
```

3b. 修改 `server/app/exporters/report_builder.py`

更新 `build_report` 签名，加入两个新参数：
```python
def build_report(
    out_path: Path,
    *,
    project: Any,
    functions: list,
    figures: dict,
    is_reverse: bool,
    target_cost_wan: float | None,
    selected_band: str = "P50",
    measurement_method: str = "nesma_estimated",
    cfp_to_fp: float = 1.2,
) -> Path:
```

在 `_sheet_narrative`（评估报告书 sheet）中，在方法描述段追加声明逻辑：

找到 `_sheet_narrative` 函数，在其方法描述部分追加：
```python
# 在函数内部，构建方法声明文本
_DECLARATION_LABEL = {
    "ifpug":            "IFPUG（GB/T 42449-2023）",
    "nesma_detailed":   "NESMA 详细级（GB/T 42588-2023）",
    "nesma_estimated":  "NESMA 估算级（GB/T 42588-2023）",
    "nesma_indicative": "NESMA 预估级（GB/T 42588-2023）",
    "cosmic":           "COSMIC（GB/T 42452-2023）",
}
method_label = _DECLARATION_LABEL.get(measurement_method, measurement_method)

# 将 fp_count_declaration 从 figures["trace"] 取出用于报告
fp_declaration = figures.get("trace", {}).get("fp_count_declaration", "")

# 对 COSMIC 追加换算备注
cosmic_note = ""
if measurement_method == "cosmic":
    cosmic_note = (
        f"注：本项目采用 COSMIC 功能规模测量方法，规模单位为 CFP。"
        f"评估结果经 CFP→FP 当量换算（系数 {cfp_to_fp}，即 1 NESMA-FP ≈ {cfp_to_fp} CFP），"
        f"因无直接 COSMIC 生产率基准，换算后的 FP 当量走与 IFPUG/NESMA 相同的 FP/人月生产率。"
    )
```

在评估报告书的「评估方法」行，写入 `method_label` 和 `fp_declaration`。
若 `cosmic_note` 非空，在报告书的「说明」段写入换算备注。

将这些参数透传给各需要的内部函数（`_sheet_summary`、`_sheet_narrative`）。

- [ ] **Step 4: 跑测试确认通过**

```bash
cd server && .venv/bin/python -m pytest tests/integration/test_v2_9_report_method.py -q
```

预期：`2 passed`。

- [ ] **Step 5: 提交**

```bash
git add server/app/exporters/report_builder.py \
        server/app/services/reports.py \
        server/tests/integration/test_v2_9_report_method.py
git commit -m "feat(report): 方法声明 + COSMIC 换算备注 (v2.9 A9)"
```

---

## Phase B（续）

### Task B3: README 更正

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 确认需要更正的内容**

在 README.md 中定位：
- 旧标注 `GB/T 42452-2023 — 软件开发成本度量规范应用指南`（或类似错误描述）
- 标准合规列表（通常在「合规标准」或「依据」章节）

- [ ] **Step 2: 写最小实现**

修改 `README.md`：

1. 将 `GB/T 42452-2023` 的描述从 `"软件开发成本度量规范应用指南"`（错误）改为 `"信息技术 软件测量 COSMIC 功能规模测量方法"` 或简称 `"COSMIC 功能规模测量方法"`。

2. 在标准合规列表中补充：
   - `GB/T 42449-2023 — 信息技术 软件测量 功能规模测量 第5部分：IFPUG功能规模测量方法的功能复杂性分类指南`（或简称 IFPUG 方法）
   - `GB/T 42588-2023 — 信息技术 软件测量 功能规模测量 NESMA 功能规模测量方法定义及计数指南`（或简称 NESMA 方法）

3. 若 README 中有「基准数据」或「数据版本」说明，将 `CSBMK®-202510` 更新为 `SSM-BK-202509`。

- [ ] **Step 3: 验证（人工）**

```bash
grep "42452" README.md   # 应见 COSMIC 功能规模测量方法
grep "42449" README.md   # 应见 IFPUG
grep "42588" README.md   # 应见 NESMA
```

- [ ] **Step 4: 提交**

```bash
git add README.md
git commit -m "docs(README): 修正 GB/T 42452-2023 标注；补充 IFPUG/NESMA 标准合规项 (v2.9 B3)"
```

---

## Task E1: 最终验收

**Files:** 无新增或修改（仅验证）

- [ ] **Step 1: 后端全量测试**

```bash
cd server && .venv/bin/python -m pytest -q
```

预期：全绿，0 errors，0 failures。

- [ ] **Step 2: 前端单元测试 + 类型检查**

```bash
cd web && npx vitest run
```

预期：全绿。

```bash
cd web && npx vue-tsc --noEmit
```

预期：无 TypeScript 错误。

- [ ] **Step 3: 前端生产构建**

```bash
cd web && npm run build
```

预期：构建成功，无 error。

- [ ] **Step 4: Alembic migration 验证**

```bash
cd server && .venv/bin/alembic upgrade head
```

预期：`a9f3c0b1d2e7 -> (head)` 成功应用（或 "up to date"）。

- [ ] **Step 5: 验收记录提交（仅当有未提交变更时）**

```bash
git status
# 若 clean，无需提交。若有验收记录文件，按需提交。
```

---

## 跨任务一致性核对

| 检查项 | 值 |
|---|---|
| `measurement_method` 5 个合法值 | `ifpug` / `nesma_indicative` / `nesma_estimated` / `nesma_detailed` / `cosmic` |
| `SizeMethod.size_unit` | `"FP"` 或 `"CFP"` |
| `SizeMethod.input_model` | `"ifpug_style"` 或 `"cosmic"` |
| `get_method` 未知值 | 抛 `ValueError("unknown measurement_method: ...")` |
| `_apply_sizing(method, data)` 签名 | A4 定义，A4 在 functions.py 中使用 |
| `_declaration_for(method)` | A5 在 calc.py 中定义，返回 str |
| `ForwardInput.size_declaration` | A5 新增字段，默认 `"FP (IFPUG-GB/T 42449-2023)"` |
| `EvaluationContext.cfp_to_fp` | B2 新增属性，A5 使用 |
| COSMIC CFP÷cfp_to_fp 在哪里换算 | A5 `_resolve_items` 内，不在 `_apply_sizing` 中 |
| `cosmic_*` 列：model / schema / FpFormModal 字段名 | `cosmic_entry / cosmic_exit / cosmic_read / cosmic_write` |
| SSM-BK 版本字符串 | `"SSM-BK-202509"` |
| `config.py` 种子路径 | `ssm_bk_202509.json` |
