# 造价算法/基准数据/参数 UI/反算补全 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 GB/T 42449 完善 FP 计数与造价算法、基准数据对齐 2025 PDF、补全全局参数保存/还原 UI、反算按三级模块树细化并 AI 补全 FP。

**Architecture:** 后端 FastAPI 三层（core 纯算法 / services 业务装配 / api 路由），core 新增 `ifpug.py` 实现 IFPUG 复杂度查表，`forward.py` 按变更类型分类汇总规模；数据层用 `csbmk_202510.json` 作 seed 源经 `seed_from_csbmk` 落 `ParamGlobal` 表。前端 Vue3 + Pinia，`ParamManager.vue` 接通全局草稿编辑，`ResultView.vue` 反算分摊表改三级树，复用既有 `AiTask` 机制新增 `reverse_fill` 任务类型与 `cost-fill` 插件命令。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic + pytest（后端）；Vue 3 + TypeScript + Vitest（前端）。

---

## 文件结构

### 新建文件

| 文件 | 职责 |
|---|---|
| `server/app/core/ifpug.py` | IFPUG GB/T 42449 复杂度查表 + FP 取值（`classify_complexity` / `fp_value`） |
| `server/alembic/versions/c1a2b3d4e5f6_ifpug_columns_and_assessment_kind.py` | FP 加 `det/ret/ftr`、`modify_type` 旧值 `new`→`add`、Project 加 `assessment_kind` |
| `server/tests/unit/test_ifpug.py` | `classify_complexity` / `fp_value` 全分支单测 |
| `server/tests/unit/test_forward_dfp_efp.py` | forward 开发/增强口径单测 |
| `server/tests/integration/test_v2_8_ifpug_columns.py` | FP 创建/读取携带 det/ret/ftr 的集成测试 |
| `server/tests/integration/test_v2_8_csbmk_data.py` | `csbmk_202510.json` schema/数值校验测试 |
| `server/tests/integration/test_v2_8_reseed_migration.py` | reset+re-seed 迁移后 `ParamGlobal` 值正确性测试 |
| `server/tests/unit/test_module_tree_allocation.py` | 三级树分摊单测 |
| `server/tests/integration/test_v2_8_reverse_fill_task.py` | `reverse_fill` 任务创建与缺口计算集成测试 |
| `commands/cost-fill.md` | `reverse_fill` AI 任务的插件命令 |
| `web/src/__tests__/FpFormModal-ifpug.test.ts` | FpFormModal 复杂度联动单测 |
| `web/src/__tests__/views/ParamManager-global-draft.test.ts` | 全局草稿编辑/保存/撤销/还原单测 |
| `web/src/__tests__/views/ResultView-module-tree.test.ts` | 树形分摊表 + 补全按钮单测 |

### 修改文件

| 文件 | 改动 |
|---|---|
| `server/app/db/models.py` | FunctionPoint 加 `det/ret/ftr` 列、Project 加 `assessment_kind` 列 |
| `server/app/schemas/functions.py` | FunctionPointBase/Patch 加 `det/ret/ftr`，`modify_type` 取值改 `add/change/delete/convert` |
| `server/app/schemas/project.py` | ProjectCreate/Patch/BundleItem 加 `assessment_kind` |
| `server/app/core/forward.py` | `FpItem` 加 `modify_type`，`ForwardInput` 加 `assessment_kind`，`calculate_forward` 按口径汇总 |
| `server/app/services/calc.py` | `_resolve_items` 透传 modify_type；`run_forward` 传 assessment_kind；`_allocate_ufp_to_modules` 改三级树 |
| `server/app/services/functions.py` | `create` 自动按 IFPUG 重算 ufp/us（det/ret/ftr 提供时） |
| `server/app/services/ai_tasks.py` | `create_task` 接受 `reverse_fill` kind；新增 `spawn_claude_reverse_fill` |
| `server/app/api/ai_tasks.py` | `start_task` 按 kind 分派 spawn 函数 |
| `server/app/schemas/ai_tasks.py` | `AiTaskCreate.kind` 加 `reverse_fill` |
| `server/app/data/csbmk_202510.json` | Part B 全量对齐 2025 PDF |
| `server/app/data/csbmk_factors_meta.json` | 删除 `软件集成` 档 meta，补吻合度/软件类型/涉密因子 meta |
| `web/src/api/functions.ts` | FunctionPoint 类型加 `det/ret/ftr`，modify_type 取值更新 |
| `web/src/api/calc.ts` | `ModuleUfpAllocation` 改树形 `ModuleAllocationNode` |
| `web/src/api/params.ts` | `paramsApi.patchGlobal` 改为逐 leaf key 的 `{key,value}` 形态 |
| `web/src/api/aiTasks.ts` | `AiTaskKind` 加 `reverse_fill` |
| `web/src/components/fp/FpFormModal.vue` | 增 DET/RET/FTR 输入，按 IFPUG 实时算复杂度与 UFP |
| `web/src/views/ParamManager.vue` | 全局模式草稿编辑 + 保存/撤销/还原三按钮 |
| `web/src/views/ResultView.vue` | 反算分摊表改三级树 + 「按反算补全 FP」按钮 |

---

## Phase A — 造价算法完善（GB/T 42449-2023）

### Task A1: alembic migration — IFPUG 列 + modify_type 迁移 + assessment_kind

**Files:**
- Create `server/alembic/versions/c1a2b3d4e5f6_ifpug_columns_and_assessment_kind.py`
- Test `server/tests/integration/test_v2_8_ifpug_columns.py`

> **dev 库兼容说明**：本项目 `bootstrap.py` 用 `create_all`（不 drop），dev 库可能没有 alembic 版本戳。本 migration 的 `down_revision` 设为当前 head `4b7939b0712d`。生产/CI 库通过 `alembic upgrade head` 应用；dev 库若 `alembic` 检测不到版本戳无法自动升级，需手动执行以下 SQL（migration 文件头注释里也写明）：
> ```sql
> ALTER TABLE function_points ADD COLUMN det INTEGER;
> ALTER TABLE function_points ADD COLUMN ret INTEGER;
> ALTER TABLE function_points ADD COLUMN ftr INTEGER;
> ALTER TABLE projects ADD COLUMN assessment_kind VARCHAR DEFAULT 'development' NOT NULL;
> UPDATE function_points SET modify_type='add' WHERE modify_type='new';
> ```
> 测试用 in-memory engine 走 `Base.metadata.create_all`，新列由 model 定义直接建出，不依赖 migration 执行。

- [ ] Step 1 写失败测试 `server/tests/integration/test_v2_8_ifpug_columns.py`：

```python
"""v2.8 — FunctionPoint 新增 det/ret/ftr 列、Project 新增 assessment_kind 列。"""
import pytest
from app.db.models import Project, FunctionPoint

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


def _seed(db, pid="p-ifpug-cols"):
    p = Project(id=pid, name="ifpug cols",
                project_type="dev_only", phase="bidding",
                city="北京", industry="电子政务",
                mode="forward", basis_data_ver="CSBMK-202510",
                assessment_kind="development")
    db.add(p)
    db.commit()
    return p


def test_project_has_assessment_kind_column(db_session):
    p = _seed(db_session)
    assert p.assessment_kind == "development"
    cols = {c.name for c in Project.__table__.columns}
    assert "assessment_kind" in cols


def test_function_point_has_ifpug_columns(db_session):
    cols = {c.name for c in FunctionPoint.__table__.columns}
    assert {"det", "ret", "ftr"} <= cols


@pytest.mark.asyncio
async def test_create_fp_with_ifpug_fields_persists(client_factory, db_session):
    _seed(db_session, pid="p-ifpug-create")
    async with await client_factory() as client:
        r = await client.post(
            "/api/projects/p-ifpug-create/functions",
            headers={**H, "Content-Type": "application/json"},
            json={
                "name": "用户表", "category": "ILF", "complexity": "average",
                "det": 25, "ret": 3, "ufp": 10, "us": 10, "modify_type": "add",
            },
        )
        assert r.status_code == 201
        data = r.json()["data"]
        assert data["det"] == 25
        assert data["ret"] == 3
        assert data["modify_type"] == "add"
```

- [ ] Step 2 跑测试确认失败：
```
cd server && .venv/bin/python -m pytest tests/integration/test_v2_8_ifpug_columns.py -q
```
预期失败：`AttributeError: 'Project' object has no attribute 'assessment_kind'`，以及 `assert {'det','ret','ftr'} <= cols` 为 False。

- [ ] Step 3 写最小实现。先建 migration 文件 `server/alembic/versions/c1a2b3d4e5f6_ifpug_columns_and_assessment_kind.py`：

```python
"""ifpug_columns_and_assessment_kind

Revision ID: c1a2b3d4e5f6
Revises: 4b7939b0712d
Create Date: 2026-05-18 09:00:00.000000

v2.8 Part A：
- function_points 新增 det/ret/ftr（IFPUG GB/T 42449 复杂度查表输入），均可空。
- function_points.modify_type 旧值 'new' 迁移为 'add'（对齐 42449 ADD/CHGA/DEL/CFP）。
- projects 新增 assessment_kind（development | enhancement），默认 development。

dev 库兼容：本项目 bootstrap 用 create_all，dev 库可能无 alembic 版本戳，
无法 `alembic upgrade head`。此时手动执行：
  ALTER TABLE function_points ADD COLUMN det INTEGER;
  ALTER TABLE function_points ADD COLUMN ret INTEGER;
  ALTER TABLE function_points ADD COLUMN ftr INTEGER;
  ALTER TABLE projects ADD COLUMN assessment_kind VARCHAR DEFAULT 'development' NOT NULL;
  UPDATE function_points SET modify_type='add' WHERE modify_type='new';
"""
from alembic import op
import sqlalchemy as sa


revision = "c1a2b3d4e5f6"
down_revision = "4b7939b0712d"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("function_points") as batch:
        batch.add_column(sa.Column("det", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("ret", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("ftr", sa.Integer(), nullable=True))
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column(
            "assessment_kind", sa.String(),
            server_default="development", nullable=False,
        ))
    op.execute(
        "UPDATE function_points SET modify_type='add' WHERE modify_type='new'"
    )


def downgrade():
    op.execute(
        "UPDATE function_points SET modify_type='new' WHERE modify_type='add'"
    )
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("assessment_kind")
    with op.batch_alter_table("function_points") as batch:
        batch.drop_column("ftr")
        batch.drop_column("ret")
        batch.drop_column("det")
```

然后改 `server/app/db/models.py` —— 在 `FunctionPoint` 类的 `complexity` 列之后加：

```python
    # v2.8 — IFPUG GB/T 42449 复杂度查表输入，均可空（老数据兼容）。
    det = Column(Integer)  # 数据元素类型数 Data Element Types
    ret = Column(Integer)  # 记录元素类型数 Record Element Types（数据功能用）
    ftr = Column(Integer)  # 引用文件数 File Types Referenced（事务功能用）
```

在 `Project` 类的 `basis_data_ver` 列之后加：

```python
    # v2.8 — 评估口径：development 开发项目 / enhancement 增强项目。
    # 独立于 project_type（dev_only/...），决定 forward 规模公式（DFP vs EFP）。
    assessment_kind = Column(
        String, nullable=False, server_default="development"
    )
```

- [ ] Step 4 跑测试确认通过：
```
cd server && .venv/bin/python -m pytest tests/integration/test_v2_8_ifpug_columns.py -q
```
预期 3 passed。

- [ ] Step 5 提交：
```
git add server/alembic/versions/c1a2b3d4e5f6_ifpug_columns_and_assessment_kind.py server/app/db/models.py server/tests/integration/test_v2_8_ifpug_columns.py
git commit -m "feat(server): IFPUG 列(det/ret/ftr) + assessment_kind + modify_type 迁移"
```

---

### Task A2: core/ifpug.py — IFPUG 复杂度查表

**Files:**
- Create `server/app/core/ifpug.py`
- Test `server/tests/unit/test_ifpug.py`

- [ ] Step 1 写失败测试 `server/tests/unit/test_ifpug.py`：

```python
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
    # RET 1 + DET 20-50 → average
    assert classify_complexity(category, det=30, ret=1, ftr=None) == "average"


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
```

- [ ] Step 2 跑测试确认失败：
```
cd server && .venv/bin/python -m pytest tests/unit/test_ifpug.py -q
```
预期失败：`ModuleNotFoundError: No module named 'app.core.ifpug'`。

- [ ] Step 3 写最小实现 `server/app/core/ifpug.py`：

```python
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


# 查表矩阵：[row_band][col_band] → complexity。row=RET/FTR，col=DET。
# 低复杂度区在左上，高复杂度区在右下。
_MATRIX: list[list[Complexity]] = [
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
        return _MATRIX[_ret_band(ret)][_data_det_band(det)]
    if category in ("EI", "EO", "EQ"):
        if det is None or ftr is None:
            return _DEFAULT
        ftr_band = _ftr_band_ei(ftr) if category == "EI" else _ftr_band_eo_eq(ftr)
        return _MATRIX[ftr_band][_txn_det_band(det)]
    return _DEFAULT


def fp_value(category: str, complexity: str) -> int:
    """(category, complexity) → 未调整功能点数。未知 category 抛 ValueError。"""
    table = _FP_VALUE.get(category)
    if table is None:
        raise ValueError(f"UNKNOWN_CATEGORY: {category!r}")
    return table[complexity]
```

- [ ] Step 4 跑测试确认通过：
```
cd server && .venv/bin/python -m pytest tests/unit/test_ifpug.py -q
```
预期所有用例 PASS（含 parametrize 共约 24 项）。

- [ ] Step 5 提交：
```
git add server/app/core/ifpug.py server/tests/unit/test_ifpug.py
git commit -m "feat(server): core/ifpug.py — GB/T 42449 复杂度查表 + FP 取值"
```

---

### Task A3: forward 算法按变更类型分类汇总（DFP / EFP）

**Files:**
- Modify `server/app/core/forward.py`
- Test `server/tests/unit/test_forward_dfp_efp.py`

- [ ] Step 1 写失败测试 `server/tests/unit/test_forward_dfp_efp.py`：

```python
"""v2.8 — forward 按 assessment_kind 分类汇总规模（DFP / EFP）。"""
from app.core.forward import calculate_forward, ForwardInput, FpItem
from app.core.context import EvaluationContext, ProjectInputs


PARAMS = {
    "productivity": {
        "dev": {"电子政务": {"P10": 2.04, "P50": 6.41, "P90": 15.36}},
        "ops": {"全行业": {"P10": 0.21, "P50": 0.74, "P90": 2.07}},
    },
    "city_rate": {"北京": {"dev": 32198, "ops": 26335, "class": "A"}},
    "cf": {"bidding": 1.21},
    "hours_per_pm": 174,
}


def _ctx():
    return EvaluationContext.from_dict(
        PARAMS, ProjectInputs(industry="电子政务", city="北京", phase="bidding"))


def test_development_uses_add_and_convert_only():
    # 开发项目 DFP = ADD + CFP；change/delete 不计入。
    items = [
        FpItem(us=10, modify_type="add"),
        FpItem(us=5, modify_type="convert"),
        FpItem(us=100, modify_type="change"),
        FpItem(us=100, modify_type="delete"),
    ]
    inp = ForwardInput(items=items, assessment_kind="development",
                       include_dev=True, include_ops=False)
    r = calculate_forward(_ctx(), inp)
    assert r.scale_us == 15  # 10 + 5


def test_enhancement_sums_all_change_types():
    # 增强项目 EFP = ADD + CHGA + CFP + DEL。
    items = [
        FpItem(us=10, modify_type="add"),
        FpItem(us=20, modify_type="change"),
        FpItem(us=5, modify_type="convert"),
        FpItem(us=8, modify_type="delete"),
    ]
    inp = ForwardInput(items=items, assessment_kind="enhancement",
                       include_dev=True, include_ops=False)
    r = calculate_forward(_ctx(), inp)
    assert r.scale_us == 43  # 10 + 20 + 5 + 8


def test_missing_modify_type_treated_as_add():
    # 老数据 modify_type 为 None → 视为 add，开发口径计入。
    items = [FpItem(us=18, modify_type=None)]
    inp = ForwardInput(items=items, assessment_kind="development",
                       include_dev=True, include_ops=False)
    r = calculate_forward(_ctx(), inp)
    assert r.scale_us == 18


def test_fp_count_declaration_in_trace():
    # 报告用 FP 计数声明字符串挂在 trace。
    items = [FpItem(us=18, modify_type="add")]
    inp = ForwardInput(items=items, assessment_kind="development",
                       include_dev=True, include_ops=False)
    r = calculate_forward(_ctx(), inp)
    assert r.trace["fp_count_declaration"] == "18 FP (IFPUG-GB/T 42449-2023)"
```

- [ ] Step 2 跑测试确认失败：
```
cd server && .venv/bin/python -m pytest tests/unit/test_forward_dfp_efp.py -q
```
预期失败：`TypeError: FpItem.__init__() got an unexpected keyword argument 'modify_type'`。

- [ ] Step 3 写最小实现。改 `server/app/core/forward.py` —— 替换 `FpItem` 和 `ForwardInput` dataclass，并改 `calculate_forward`：

```python
from dataclasses import dataclass, field
from .context import EvaluationContext


# 开发项目计入 add(ADD) + convert(CFP)；增强项目额外计入 change(CHGA) + delete(DEL)。
_DEV_TYPES = {"add", "convert"}
_ENHANCEMENT_TYPES = {"add", "convert", "change", "delete"}


@dataclass
class FpItem:
    us: float
    # v2.8 — 变更类型（add/change/delete/convert）。None 视为 add（老数据兼容）。
    modify_type: str | None = "add"


@dataclass
class ForwardInput:
    items: list[FpItem]
    dev_factor: float = 1.0
    ops_factor: float = 1.0
    include_dev: bool = True
    include_ops: bool = False
    other_cost: float = 0.0
    # v2.8 — development 开发项目 / enhancement 增强项目。
    assessment_kind: str = "development"
```

把 `calculate_forward` 函数体开头的 `us = sum(i.us for i in inp.items)` 替换为：

```python
def calculate_forward(ctx: EvaluationContext, inp: ForwardInput) -> ForwardResult:
    # v2.8 — 按 assessment_kind 选取计入规模的变更类型集合。
    counted = (_ENHANCEMENT_TYPES if inp.assessment_kind == "enhancement"
               else _DEV_TYPES)
    us = sum(i.us for i in inp.items
             if (i.modify_type or "add") in counted)
    cf = ctx.cf()
```

并在 `trace` dict 里增加 `fp_count_declaration`（在 `trace = {` 块内 `"total_p50": total["P50"],` 之后加一行）：

```python
        "total_p50": total["P50"],
        "fp_count_declaration": f"{us:g} FP (IFPUG-GB/T 42449-2023)",
```

- [ ] Step 4 跑测试确认通过：
```
cd server && .venv/bin/python -m pytest tests/unit/test_forward_dfp_efp.py tests/unit/test_forward.py -q
```
预期 `test_forward_dfp_efp.py` 4 passed；`test_forward.py` 既有 2 项仍 passed（FpItem 默认 modify_type="add" 兼容旧调用）。

- [ ] Step 5 提交：
```
git add server/app/core/forward.py server/tests/unit/test_forward_dfp_efp.py
git commit -m "feat(server): forward 按 assessment_kind 分类汇总规模(DFP/EFP)"
```

---

### Task A4: schemas + calc 服务接通 IFPUG 字段与口径

**Files:**
- Modify `server/app/schemas/functions.py`, `server/app/schemas/project.py`, `server/app/services/calc.py`, `server/app/services/functions.py`
- Test `server/tests/integration/test_v2_8_ifpug_columns.py`（追加用例）

- [ ] Step 1 在 `server/tests/integration/test_v2_8_ifpug_columns.py` 末尾追加失败测试：

```python
@pytest.mark.asyncio
async def test_create_fp_autocomputes_ufp_from_ifpug(client_factory, db_session):
    """提供 det/ret 时 create 按 IFPUG 重算 ufp/us，忽略请求里的手填值。"""
    _seed(db_session, pid="p-ifpug-auto")
    async with await client_factory() as client:
        r = await client.post(
            "/api/projects/p-ifpug-auto/functions",
            headers={**H, "Content-Type": "application/json"},
            json={
                "name": "用户表", "category": "ILF", "complexity": "low",
                "det": 60, "ret": 6, "ufp": 999, "us": 999, "modify_type": "add",
            },
        )
        assert r.status_code == 201
        data = r.json()["data"]
        # det=60 ret=6 → high → ILF high = 15；complexity 也被重算为 high
        assert data["complexity"] == "high"
        assert data["ufp"] == 15
        assert data["us"] == 15


@pytest.mark.asyncio
async def test_forward_uses_assessment_kind(client_factory, db_session):
    """enhancement 项目 forward 计入 change/delete。"""
    from app.db.models import FunctionPoint
    p = _seed(db_session, pid="p-ifpug-efp")
    p.assessment_kind = "enhancement"
    for mt, us in [("add", 10), ("change", 20), ("delete", 5)]:
        db_session.add(FunctionPoint(
            id=f"fp-{mt}", project_id="p-ifpug-efp", version=1,
            category="EI", complexity="average", modify_type=mt,
            ufp=us, us=us))
    db_session.commit()
    async with await client_factory() as client:
        r = await client.post(
            "/api/calc/forward",
            headers={**H, "Content-Type": "application/json"},
            json={"project_id": "p-ifpug-efp"},
        )
        assert r.status_code == 200
        assert r.json()["data"]["scale_us"] == 35  # 10 + 20 + 5
```

- [ ] Step 2 跑测试确认失败：
```
cd server && .venv/bin/python -m pytest tests/integration/test_v2_8_ifpug_columns.py -q
```
预期新增 2 项失败：`autocomputes` 拿到 `ufp == 999`（未重算）；`forward_uses_assessment_kind` 拿到 `scale_us == 10`（仅 add，因为 calc 未透传 modify_type/assessment_kind）。

- [ ] Step 3 写最小实现。

改 `server/app/schemas/functions.py` —— `FunctionPointBase` 的 `complexity` 行之后加三列，并替换 `modify_type` 行：

```python
    category: Literal["EI", "EO", "EQ", "ILF", "EIF"]
    complexity: Literal["low", "average", "high"]
    # v2.8 — IFPUG GB/T 42449 复杂度查表输入，均可空。
    det: Optional[int] = Field(default=None, ge=0)
    ret: Optional[int] = Field(default=None, ge=0)
    ftr: Optional[int] = Field(default=None, ge=0)
    # dev = 开发功能点 / ops = 运维功能点。默认 dev 兼容历史数据。
    fp_kind: Literal["dev", "ops"] = "dev"
```

把 `FunctionPointBase` 里的 `modify_type` 行改为：

```python
    # v2.8 — 对齐 GB/T 42449 ADD/CHGA/DEL/CFP。
    modify_type: Optional[Literal["add", "change", "delete", "convert"]] = "add"
```

把 `FunctionPointPatch` 里 `fp_kind` 行之后加：

```python
    det: Optional[int] = Field(default=None, ge=0)
    ret: Optional[int] = Field(default=None, ge=0)
    ftr: Optional[int] = Field(default=None, ge=0)
    modify_type: Optional[Literal["add", "change", "delete", "convert"]] = None
```

改 `server/app/schemas/project.py` —— `ProjectCreate` 的 `basis_data_ver` 行之后加：

```python
    basis_data_ver: str
    # v2.8 — 评估口径：development 开发项目 / enhancement 增强项目。
    assessment_kind: Literal["development", "enhancement"] = "development"
```

`ProjectPatch` 的 `project_type` 行之后加：

```python
    assessment_kind: Optional[Literal["development", "enhancement"]] = None
```

`ProjectBundleItem` 的 `basis_data_ver` 行之后加：

```python
    basis_data_ver: str
    assessment_kind: Literal["development", "enhancement"] = "development"
```

改 `server/app/services/functions.py` —— 在文件顶部 import 后加 IFPUG import，并在 `create` 函数里 build `FunctionPoint` 之前重算：

```python
import uuid, json
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..db.models import FunctionPoint, FPSnapshot, Project, Result
from ..schemas.functions import FunctionPointCreate, FunctionPointPatch
from ..core.ifpug import classify_complexity, fp_value
```

把 `create` 函数体替换为：

```python
def create(db: Session, project_id: str, payload: FunctionPointCreate) -> FunctionPoint:
    if not db.query(Project).filter_by(id=project_id).first():
        raise ValueError("PROJECT_NOT_FOUND")
    version = _next_version(db, project_id)
    data = payload.model_dump()
    # v2.8 — 提供了足够的 IFPUG 输入时，按 GB/T 42449 重算 complexity/ufp/us，
    # 覆盖请求里的手填值（避免前端旧版漏算）。信息不足则保留请求值。
    data = _apply_ifpug(data)
    fp = FunctionPoint(id=f"fp-{uuid.uuid4().hex[:12]}",
                        project_id=project_id, version=version, **data)
    db.add(fp); db.commit(); db.refresh(fp)
    _mark_results_stale(db, project_id)
    return fp


def _apply_ifpug(data: dict) -> dict:
    """提供了 IFPUG 复杂度查表所需输入时重算 complexity/ufp/us。

    数据功能需 det+ret；事务功能需 det+ftr。信息不足时原样返回。
    返回新 dict（不就地改入参）。
    """
    category = data.get("category")
    det, ret, ftr = data.get("det"), data.get("ret"), data.get("ftr")
    has_input = (
        (category in ("ILF", "EIF") and det is not None and ret is not None)
        or (category in ("EI", "EO", "EQ") and det is not None and ftr is not None)
    )
    if not has_input:
        return data
    complexity = classify_complexity(category, det, ret, ftr)
    ufp = fp_value(category, complexity)
    return {**data, "complexity": complexity, "ufp": ufp, "us": ufp}
```

改 `server/app/services/calc.py` —— 替换 `_resolve_items` 的返回行和 `run_forward` 里的 `ForwardInput` 构造。

`_resolve_items` 函数里两处构造 `FpItem` 改为带 `modify_type`：

```python
    raw_items = payload.get("items")
    if raw_items:
        return [FpItem(us=i["us"], modify_type=i.get("modify_type", "add"))
                for i in raw_items]
    db_items = fs.list_for_project(db, project_id)
    if not db_items and mode == "forward":
        raise ValueError(
            "NO_FUNCTION_POINTS: 项目暂无功能点，请先在 FP 编辑屏添加或上传文档让 AI 提取"
        )
    return [FpItem(us=fp.us, modify_type=fp.modify_type or "add")
            for fp in db_items]
```

`run_forward` 里 `ForwardInput(...)` 构造增加 `assessment_kind`：

```python
    inp = ForwardInput(
        items=_resolve_items(db, project_id, payload, mode="forward"),
        dev_factor=dev_factor,
        ops_factor=ops_factor,
        include_dev=payload.get("include_dev", True),
        include_ops=payload.get("include_ops", proj.include_ops or False),
        other_cost=payload.get("other_cost", proj.other_cost or 0.0),
        assessment_kind=getattr(proj, "assessment_kind", None) or "development",
    )
```

- [ ] Step 4 跑测试确认通过：
```
cd server && .venv/bin/python -m pytest tests/integration/test_v2_8_ifpug_columns.py tests/integration/test_calc_api.py tests/integration/test_functions_api.py -q
```
预期 `test_v2_8_ifpug_columns.py` 全 passed，既有 calc/functions 测试不回归。

- [ ] Step 5 提交：
```
git add server/app/schemas/functions.py server/app/schemas/project.py server/app/services/calc.py server/app/services/functions.py server/tests/integration/test_v2_8_ifpug_columns.py
git commit -m "feat(server): calc/functions 接通 IFPUG 重算与 assessment_kind 口径"
```

---

### Task A5: FpFormModal 前端 IFPUG 复杂度联动

**Files:**
- Modify `web/src/components/fp/FpFormModal.vue`, `web/src/api/functions.ts`
- Test `web/src/__tests__/FpFormModal-ifpug.test.ts`

- [ ] Step 1 写失败测试 `web/src/__tests__/FpFormModal-ifpug.test.ts`：

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import FpFormModal from "@/components/fp/FpFormModal.vue";
import { functionsApi } from "@/api/functions";

vi.mock("@/api/functions", () => ({
  functionsApi: { create: vi.fn().mockResolvedValue({}), patch: vi.fn() },
}));

describe("FpFormModal — IFPUG 复杂度联动", () => {
  beforeEach(() => vi.clearAllMocks());

  it("ILF + DET 60 + RET 6 → 复杂度 high、UFP 15", async () => {
    const w = mount(FpFormModal, { props: { open: true, projectId: "p-1" } });
    await flushPromises();
    await w.find("#fp-category").setValue("ILF");
    await w.find("#fp-det").setValue("60");
    await w.find("#fp-ret").setValue("6");
    await flushPromises();
    expect(w.text()).toContain("15");
    // 复杂度显示为「高」
    expect(w.find("[data-testid='fp-complexity-auto']").text()).toContain("高");
  });

  it("EI + DET 3 + FTR 1 → 复杂度 low、UFP 3", async () => {
    const w = mount(FpFormModal, { props: { open: true, projectId: "p-1" } });
    await flushPromises();
    await w.find("#fp-category").setValue("EI");
    await w.find("#fp-det").setValue("3");
    await w.find("#fp-ftr").setValue("1");
    await flushPromises();
    expect(w.find("[data-testid='fp-complexity-auto']").text()).toContain("低");
    expect(w.text()).toContain("3");
  });

  it("信息不足 → 默认 average，提交带 det/ret", async () => {
    const w = mount(FpFormModal, { props: { open: true, projectId: "p-1" } });
    await flushPromises();
    await w.find("#fp-name").setValue("查询客户");
    await w.find("#fp-category").setValue("ILF");
    await w.find("#fp-det").setValue("25");
    await w.find("#fp-ret").setValue("3");
    await w.find("form").trigger("submit");
    await flushPromises();
    expect(functionsApi.create).toHaveBeenCalledWith(
      "p-1",
      expect.objectContaining({ det: 25, ret: 3, category: "ILF" }),
    );
  });
});
```

- [ ] Step 2 跑测试确认失败：
```
cd web && npx vitest run src/__tests__/FpFormModal-ifpug.test.ts
```
预期失败：`Cannot read properties of undefined`（`#fp-det` 不存在）。

- [ ] Step 3 写最小实现。

改 `web/src/api/functions.ts` —— 找到 `FunctionPoint` 接口，加 `det/ret/ftr` 并更新 `modify_type`（若该接口存在 `modify_type` 字段则改其字面量为 `"add" | "change" | "delete" | "convert"`；若不存在则补上 `det?: number; ret?: number; ftr?: number;`）。在 `FunctionPoint` 接口体内 `complexity` 字段之后加：

```typescript
  det?: number | null;
  ret?: number | null;
  ftr?: number | null;
  modify_type?: "add" | "change" | "delete" | "convert" | null;
```

改 `web/src/components/fp/FpFormModal.vue` —— 在 `<script setup>` 内：

替换 IFPUG 查表逻辑。在 `UFP_TABLE` 常量之后加 IFPUG 查表函数：

```typescript
// IFPUG GB/T 42449 复杂度查表（与 server/app/core/ifpug.py 对齐）
const COMPLEXITY_MATRIX: FpComplexity[][] = [
  ["low", "low", "average"],
  ["low", "average", "high"],
  ["average", "high", "high"],
];

function retBand(ret: number): number {
  return ret <= 1 ? 0 : ret <= 5 ? 1 : 2;
}
function dataDetBand(det: number): number {
  return det <= 19 ? 0 : det <= 50 ? 1 : 2;
}
function ftrBandEi(ftr: number): number {
  return ftr <= 1 ? 0 : ftr === 2 ? 1 : 2;
}
function ftrBandEoEq(ftr: number): number {
  return ftr <= 1 ? 0 : ftr <= 3 ? 1 : 2;
}
function txnDetBand(det: number): number {
  return det <= 5 ? 0 : det <= 19 ? 1 : 2;
}

function classifyComplexity(
  cat: FpCategory,
  det: number | null,
  ret: number | null,
  ftr: number | null,
): FpComplexity {
  if (cat === "ILF" || cat === "EIF") {
    if (det === null || ret === null) return "average";
    return COMPLEXITY_MATRIX[retBand(ret)][dataDetBand(det)];
  }
  if (det === null || ftr === null) return "average";
  const band = cat === "EI" ? ftrBandEi(ftr) : ftrBandEoEq(ftr);
  return COMPLEXITY_MATRIX[band][txnDetBand(det)];
}
```

在 `const category = ref<FpCategory>("EI");` 之后、删除 `const complexity = ref<FpComplexity>("low");` 行，改为 det/ret/ftr refs + computed 复杂度：

```typescript
const det = ref<number | null>(null);
const ret = ref<number | null>(null);
const ftr = ref<number | null>(null);

const complexity = computed<FpComplexity>(() =>
  classifyComplexity(category.value, det.value, ret.value, ftr.value),
);
```

`computedUfp` 改为依赖 computed complexity（保持原 `UFP_TABLE[category.value][complexity.value]`，因 complexity 现已是 computed，无需改动该行）。

`resetForm` 里把 `complexity.value = "low";` 改为：

```typescript
  det.value = null;
  ret.value = null;
  ftr.value = null;
```

`prefillForm` 里把 `complexity.value = fp.complexity;` 改为：

```typescript
  det.value = fp.det ?? null;
  ret.value = fp.ret ?? null;
  ftr.value = fp.ftr ?? null;
```

`onSubmit` 里 `payload` 对象加 `det/ret/ftr`：

```typescript
  const payload: Partial<FunctionPoint> = {
    name: name.value.trim(),
    description: description.value.trim() || undefined,
    subsystem: subsystem.value.trim() || undefined,
    l1_module: l1_module.value.trim() || undefined,
    l2_module: l2_module.value.trim() || undefined,
    category: category.value,
    complexity: complexity.value,
    det: det.value ?? undefined,
    ret: ret.value ?? undefined,
    ftr: ftr.value ?? undefined,
    ufp,
    us: ufp,
    ...(props.editing ? {} : { source: "manual" }),
  };
```

`<template>` 里把「类别 / 复杂度 / UFP（自动）」那个 `form-row` 替换为类别 + DET + RET/FTR + 自动复杂度 + UFP：

```html
        <div class="form-row">
          <div class="form-group">
            <label for="fp-category" class="form-label">类别</label>
            <select id="fp-category" v-model="category" class="form-input form-select">
              <option v-for="cat in CATEGORIES" :key="cat" :value="cat">{{ cat }}</option>
            </select>
          </div>
          <div class="form-group">
            <label for="fp-det" class="form-label">DET（数据元素数）</label>
            <input id="fp-det" v-model.number="det" type="number" min="0"
                   class="form-input" placeholder="字段数">
          </div>
          <div class="form-group" v-if="category === 'ILF' || category === 'EIF'">
            <label for="fp-ret" class="form-label">RET（记录元素数）</label>
            <input id="fp-ret" v-model.number="ret" type="number" min="0"
                   class="form-input" placeholder="记录类型数">
          </div>
          <div class="form-group" v-else>
            <label for="fp-ftr" class="form-label">FTR（引用文件数）</label>
            <input id="fp-ftr" v-model.number="ftr" type="number" min="0"
                   class="form-input" placeholder="引用文件数">
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="form-label">复杂度（IFPUG 自动）</label>
            <div class="ufp-display">
              <span data-testid="fp-complexity-auto" class="ufp-value">
                {{ complexity === 'low' ? '低' : complexity === 'high' ? '高' : '中' }}
              </span>
              <span class="ufp-hint muted">按 GB/T 42449 查表</span>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">UFP（自动）</label>
            <div class="ufp-display">
              <span class="ufp-value">{{ computedUfp }}</span>
              <span class="ufp-hint muted">按 IFPUG 标准表自动计算</span>
            </div>
          </div>
        </div>
```

- [ ] Step 4 跑测试确认通过：
```
cd web && npx vitest run src/__tests__/FpFormModal-ifpug.test.ts src/__tests__/FpFormModal.test.ts && npx vue-tsc --noEmit
```
预期 `FpFormModal-ifpug.test.ts` 3 passed；既有 `FpFormModal.test.ts` 不回归；vue-tsc 无错误。

- [ ] Step 5 提交：
```
git add web/src/components/fp/FpFormModal.vue web/src/api/functions.ts web/src/__tests__/FpFormModal-ifpug.test.ts
git commit -m "feat(web): FpFormModal — DET/RET/FTR 输入 + IFPUG 复杂度联动"
```

---

## Phase B — 基准数据全量对齐 2025 PDF

> **PDF 取数说明**：B1 的 6 处数值修正在 spec 里已给精确值，直接写入。B2 的补缺表数值源是 `doc/《2025年中国软件行业基准数据》.pdf` —— 实施者**必须用 Read 工具读该 PDF 的对应表**取数。本计划给出每张表的 JSON 结构骨架（键名/嵌套形状由计划定，数值由 PDF 定）。

### Task B1: 修正 csbmk_202510.json 数值错误

**Files:**
- Modify `server/app/data/csbmk_202510.json`, `server/app/data/csbmk_factors_meta.json`
- Test `server/tests/integration/test_v2_8_csbmk_data.py`

- [ ] Step 1 写失败测试 `server/tests/integration/test_v2_8_csbmk_data.py`：

```python
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
```

- [ ] Step 2 跑测试确认失败：
```
cd server && .venv/bin/python -m pytest tests/integration/test_v2_8_csbmk_data.py -q
```
预期 7 项全失败（当前 JSON 是旧值）。

- [ ] Step 3 写最小实现。改 `server/app/data/csbmk_202510.json`：

`factors_dev.app_type` 块删除 `"软件集成": 1.20,` 这一行。

`factors_dev.platform` 块替换为：
```json
    "platform": {
      "C": 1.2,
      "JAVA": 1.0,
      "C++": 1.0,
      "C#": 1.0,
      "PowerBuilder": 0.8,
      "ASP": 0.8
    }
```

`factors_ops.update_freq` 替换为：
```json
    "update_freq": {"quarterly": 0.78, "monthly": 1.00, "frequent": 1.12},
```

`factors_ops.support` 替换为：
```json
    "support": {"remote": 0.90, "onsite": 1.00, "pure_onsite": 1.20},
```

`factors_ops.user_scale` 替换为：
```json
    "user_scale": {"<=1k": 0.93, "<=10k": 1.00, ">10k": 1.12},
```

`factors_ops.system_relevance` 替换为：
```json
    "system_relevance": {"none": 0.97, "1-10": 1.00, "10+": 1.14}
```

`scale_change` 块替换为：
```json
  "scale_change": {
    "add": 1.00,
    "modify": 0.80,
    "remove": 0.20,
    "threshold": 0.05
  },
```

改 `server/app/data/csbmk_factors_meta.json` —— 在 `factors_dev.app_type.options` 内删除 `软件集成` 条目；`factors_ops.user_scale` / `support` / `update_freq` 的 options label 中含旧数值的描述若与新值冲突，同步更新描述文字（如 `support.remote` 描述改为 `×0.90`，`system_relevance` 的 `1-5`/`6+` key 改为 `1-10`/`10+`）。

- [ ] Step 4 跑测试确认通过：
```
cd server && .venv/bin/python -m pytest tests/integration/test_v2_8_csbmk_data.py -q
```
预期 7 passed。同时跑 `python -c "import json; json.load(open('app/data/csbmk_202510.json'))"` 确认 JSON 合法。

- [ ] Step 5 提交：
```
git add server/app/data/csbmk_202510.json server/app/data/csbmk_factors_meta.json server/tests/integration/test_v2_8_csbmk_data.py
git commit -m "fix(server): csbmk 数值对齐 2025 PDF — 修改类型/平台/支持/用户规模等"
```

---

### Task B2: 补齐缺表 — 因子表 + 展示数据 + 附录 C

**Files:**
- Modify `server/app/data/csbmk_202510.json`
- Test `server/tests/integration/test_v2_8_csbmk_data.py`（追加用例）

> **取数指令**：本 Task 实施时必须用 Read 工具读 `doc/《2025年中国软件行业基准数据》.pdf`。需读取的表与节：
> - 表 A.2 吻合度因子；表 A.8 软件类型因子（运维侧）；表 A.19 涉密因子
> - 表 4.4 / 4.5 缺陷密度与交付质量基准；表 4.6 阶段工作量分布；第 4.6 节功能点单价
> - 运维费用占比 P10-P90（当前 JSON 仅 `ops_cost_ratio.P50`，需补全分位）
> - 附录 C：表 C.1 硬件运维单位工作量；表 C.2 安全服务规模单价
> 把读到的精确数值按下方结构骨架填入 JSON。结构骨架的键名与嵌套形状由本计划固定，不得改名。

- [ ] Step 1 在 `server/tests/integration/test_v2_8_csbmk_data.py` 末尾追加失败测试：

```python
def test_compliance_factor_present():
    cf = _seed()["factors_dev"]["compliance"]
    # 表 A.2：吻合度 高 1/3 / 中 2/3 / 低 1
    assert set(cf.keys()) == {"high", "medium", "low"}
    assert cf["low"] == 1.0


def test_ops_software_type_factor_present():
    st = _seed()["factors_ops"]["software_type"]
    assert isinstance(st, dict) and len(st) >= 2


def test_confidentiality_factor_present():
    conf = _seed()["factors_dev"]["confidentiality"]
    assert isinstance(conf, dict) and len(conf) >= 2


def test_defect_density_table_present():
    dd = _seed()["display"]["defect_density"]
    assert "P50" in dd


def test_phase_effort_distribution_present():
    pe = _seed()["display"]["phase_effort"]
    # 阶段工作量分布各阶段占比之和约等于 1
    total = sum(pe.values())
    assert abs(total - 1.0) < 0.05


def test_fp_unit_price_present():
    up = _seed()["display"]["fp_unit_price"]
    assert isinstance(up, dict) and len(up) >= 1


def test_ops_cost_ratio_all_bands():
    ocr = _seed()["ops_cost_ratio"]
    assert {"P10", "P50", "P90"} <= set(ocr.keys())


def test_appendix_c_tables_present():
    appc = _seed()["appendix_c"]
    assert "hw_ops_unit_effort" in appc      # 表 C.1
    assert "security_service_unit_price" in appc  # 表 C.2
```

- [ ] Step 2 跑测试确认失败：
```
cd server && .venv/bin/python -m pytest tests/integration/test_v2_8_csbmk_data.py -q
```
预期新增 8 项失败（`KeyError`）。

- [ ] Step 3 写最小实现。先用 Read 工具读 PDF 取数，然后改 `server/app/data/csbmk_202510.json`，按以下结构骨架补充（数值用 PDF 实际值替换占位 `<...>`）。

`factors_dev` 块内新增（吻合度因子表 A.2、涉密因子表 A.19）：
```json
    "compliance": {
      "high": <表A.2 高>,
      "medium": <表A.2 中>,
      "low": <表A.2 低>
    },
    "confidentiality": {
      "<档位名1>": <表A.19 值1>,
      "<档位名2>": <表A.19 值2>
    }
```

`factors_ops` 块内新增（软件类型因子表 A.8）：
```json
    "software_type": {
      "<类型名1>": <表A.8 值1>,
      "<类型名2>": <表A.8 值2>
    }
```

`ops_cost_ratio` 替换为三档：
```json
  "ops_cost_ratio": {"P10": <PDF P10>, "P50": 0.0902, "P90": <PDF P90>},
```

顶层新增 `display` 块（缺陷密度表 4.4/4.5、阶段工作量分布表 4.6、功能点单价第 4.6 节）：
```json
  "display": {
    "defect_density": {
      "P10": <表4.4 P10>, "P50": <表4.4 P50>, "P90": <表4.4 P90>
    },
    "delivery_quality": {
      "P10": <表4.5 P10>, "P50": <表4.5 P50>, "P90": <表4.5 P90>
    },
    "phase_effort": {
      "<阶段1>": <表4.6 占比>, "<阶段2>": <表4.6 占比>,
      "<阶段3>": <表4.6 占比>, "<阶段4>": <表4.6 占比>
    },
    "fp_unit_price": {
      "<行业或档位>": <第4.6节 单价>
    }
  },
```

顶层新增 `appendix_c` 块（仅入库数据，不建算法 — 见 spec YAGNI）：
```json
  "appendix_c": {
    "hw_ops_unit_effort": {
      "<设备类型1>": <表C.1 单位工作量>,
      "<设备类型2>": <表C.1 单位工作量>
    },
    "security_service_unit_price": {
      "<服务类型1>": <表C.2 单价>,
      "<服务类型2>": <表C.2 单价>
    }
  }
```

> 实施者需根据 PDF 实际的档位数量扩展骨架里的键值对（不止两条）。`phase_effort` 各阶段占比之和应约为 1。

- [ ] Step 4 跑测试确认通过：
```
cd server && .venv/bin/python -m pytest tests/integration/test_v2_8_csbmk_data.py -q
```
预期 15 passed（B1 的 7 + B2 的 8）。同时确认 JSON 合法。

- [ ] Step 5 提交：
```
git add server/app/data/csbmk_202510.json server/tests/integration/test_v2_8_csbmk_data.py
git commit -m "feat(server): csbmk 补齐因子表/展示数据/附录C — 对齐 2025 PDF"
```

---

### Task B3: ParamGlobal reset+re-seed 迁移

**Files:**
- Modify `server/app/bootstrap.py`
- Test `server/tests/integration/test_v2_8_reseed_migration.py`

> 设计：`csbmk_202510.json` 是 seed 源，旧库里 `ParamGlobal` 已 seed 的旧值需对齐新 JSON。`seed_from_csbmk` 用「key 已存在则跳过」策略，无法刷新已存在的 key。`reset_global` 能 wipe+re-seed，但它会清掉用户改动。方案：bootstrap 增加一个按 `basis_version` 判定的一次性 re-seed —— 若库内 `params_global` 全部 `modified=False` 且 `basis_version` 不等于新 JSON 的 version 标记，则整体 re-seed；若存在 `modified=True` 行（用户改过），仅 re-seed 未改动的 key（删除 `modified=False` 行后重新插入）。给 JSON 的 `version` 字段 bump 一个子版本标记以触发判定。

- [ ] Step 1 写失败测试 `server/tests/integration/test_v2_8_reseed_migration.py`：

```python
"""v2.8 — ParamGlobal reset+re-seed 迁移：旧库刷新到新 csbmk JSON。"""
import json
from app.db.models import ParamGlobal
from app.bootstrap import reseed_if_outdated


def _insert_stale(db, key, value, version="CSBMK®-202510", modified=False):
    db.add(ParamGlobal(key=key, value=json.dumps(value, ensure_ascii=False),
                        basis_version=version, modified=modified))
    db.commit()


def test_reseed_refreshes_unmodified_keys(db_session):
    # 旧库里 modify 因子是旧值 0.70
    _insert_stale(db_session, "scale_change.modify", 0.70)
    reseed_if_outdated(db_session)
    row = db_session.query(ParamGlobal).filter_by(key="scale_change.modify").first()
    # 新 JSON 是 0.80
    assert json.loads(row.value) == 0.80


def test_reseed_preserves_user_modified_keys(db_session):
    # 用户改过 city_rate.北京.dev → modified=True，不应被覆盖
    _insert_stale(db_session, "city_rate.北京.dev", 99999, modified=True)
    _insert_stale(db_session, "scale_change.modify", 0.70, modified=False)
    reseed_if_outdated(db_session)
    user_row = db_session.query(ParamGlobal).filter_by(key="city_rate.北京.dev").first()
    assert json.loads(user_row.value) == 99999  # 用户改动保留
    sc_row = db_session.query(ParamGlobal).filter_by(key="scale_change.modify").first()
    assert json.loads(sc_row.value) == 0.80  # 未改动 key 被刷新


def test_reseed_idempotent_on_fresh_db(db_session):
    # 空库 → 全量 seed，不报错
    reseed_if_outdated(db_session)
    n = db_session.query(ParamGlobal).count()
    assert n > 0
    # 再跑一次不重复插入也不报错
    reseed_if_outdated(db_session)
    assert db_session.query(ParamGlobal).count() == n
```

- [ ] Step 2 跑测试确认失败：
```
cd server && .venv/bin/python -m pytest tests/integration/test_v2_8_reseed_migration.py -q
```
预期失败：`ImportError: cannot import name 'reseed_if_outdated' from 'app.bootstrap'`。

- [ ] Step 3 写最小实现。在 `server/app/data/csbmk_202510.json` 顶层把 `version` 字段改为带迁移戳：
```json
  "version": "CSBMK®-202510-v2.8",
```

在 `server/app/bootstrap.py` 文件末尾（`if __name__` 之前）新增函数：

```python
def reseed_if_outdated(session) -> int:
    """v2.8 — 把 params_global 里未被用户改动的行刷新到当前 csbmk JSON。

    判定与策略：
    - 删除所有 modified=False 的行，按当前 JSON 重新插入（扁平 key）。
    - modified=True 的行（用户改过）原样保留。
    - 空库 → 等价于全量 seed。
    返回重新插入的行数。
    """
    from app.config import settings
    from app.db.models import ParamGlobal

    raw = json.loads(settings.csbmk_seed_path.read_text(encoding="utf-8"))
    version = raw.get("version", "CSBMK®-unknown")
    flat: dict = {}
    _flatten("", raw, flat)

    modified_keys = {
        row.key for row in
        session.query(ParamGlobal).filter_by(modified=True).all()
    }
    session.query(ParamGlobal).filter_by(modified=False).delete()
    inserted = 0
    for k, v in flat.items():
        if k in modified_keys:
            continue  # 用户改过的 key 不动
        session.add(ParamGlobal(
            key=k, value=json.dumps(v, ensure_ascii=False),
            basis_version=version, modified=False,
        ))
        inserted += 1
    session.commit()
    return inserted
```

并在 `cli` 函数里把幂等跳过分支改为：原来 `if existing and existing > 0:` 的分支里调用一次 `reseed_if_outdated`，使已有库也能刷新（在 `with Session() as session:` 块里，`existing` 判定后）：

```python
        if existing and existing > 0:
            from app.bootstrap import reseed_if_outdated
            n = reseed_if_outdated(session)
            click.echo(
                f"CSBMK 参数已存在（{existing} 行）；已 re-seed 未改动项 {n} 条。"
            )
```

- [ ] Step 4 跑测试确认通过：
```
cd server && .venv/bin/python -m pytest tests/integration/test_v2_8_reseed_migration.py tests/integration/test_bootstrap.py tests/integration/test_params_api.py -q
```
预期 `test_v2_8_reseed_migration.py` 3 passed；既有 bootstrap/params 测试不回归。

- [ ] Step 5 提交：
```
git add server/app/bootstrap.py server/app/data/csbmk_202510.json server/tests/integration/test_v2_8_reseed_migration.py
git commit -m "feat(server): ParamGlobal reseed_if_outdated — 旧库刷新到新 csbmk JSON"
```

---

## Phase C — 全局参数保存 / 撤销 / 还原（ParamManager）

### Task C1: paramsApi.patchGlobal 改为逐 leaf key 形态

**Files:**
- Modify `web/src/api/params.ts`
- Test `web/src/__tests__/api/params.test.ts`（追加用例）

> 现状：`paramsApi.patchGlobal` 类型签名是 `Partial<EffectiveParams>`，但后端 `PATCH /api/params/global` 收的是 `{key, value}` 单 leaf。前端从未真正调用过它（`patchOverride` 在 `!projectId` 时 return）。Part C 要逐 leaf 保存，先把 API 函数对齐后端契约。

- [ ] Step 1 在 `web/src/__tests__/api/params.test.ts` 末尾追加失败测试：

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { paramsApi } from "@/api/params";
import { api } from "@/api/client";

vi.mock("@/api/client", () => ({
  api: { get: vi.fn(), patch: vi.fn(), post: vi.fn() },
}));

describe("paramsApi.patchGlobal — 逐 leaf key", () => {
  beforeEach(() => vi.clearAllMocks());

  it("patchGlobal 发送 {key, value} 到 /api/params/global", async () => {
    (api.patch as ReturnType<typeof vi.fn>).mockResolvedValue({ updated: "x" });
    await paramsApi.patchGlobal("scale_change.modify", 0.85);
    expect(api.patch).toHaveBeenCalledWith("/api/params/global", {
      key: "scale_change.modify",
      value: 0.85,
    });
  });

  it("resetGlobal POST /api/params/global/reset", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({});
    await paramsApi.resetGlobal();
    expect(api.post).toHaveBeenCalledWith("/api/params/global/reset");
  });
});
```

- [ ] Step 2 跑测试确认失败：
```
cd web && npx vitest run src/__tests__/api/params.test.ts
```
预期新增 `patchGlobal` 用例失败：调用签名不符（旧版收 `Partial<EffectiveParams>`）。

- [ ] Step 3 写最小实现。改 `web/src/api/params.ts` —— 把 `patchGlobal` 行替换为：

```typescript
  patchGlobal: (key: string, value: unknown) =>
    api.patch<{ updated: string }>("/api/params/global", { key, value }),
```

- [ ] Step 4 跑测试确认通过：
```
cd web && npx vitest run src/__tests__/api/params.test.ts && npx vue-tsc --noEmit
```
预期 params.test.ts 全 passed；vue-tsc 无错误。

- [ ] Step 5 提交：
```
git add web/src/api/params.ts web/src/__tests__/api/params.test.ts
git commit -m "fix(web): paramsApi.patchGlobal 对齐后端 {key,value} 契约"
```

---

### Task C2: ParamManager 全局草稿编辑 + 保存/撤销/还原三按钮

**Files:**
- Modify `web/src/views/ParamManager.vue`
- Test `web/src/__tests__/views/ParamManager-global-draft.test.ts`

> 设计：全局模式（`projectId` 为 null）下，5 个参数 tab（费率/生产率/开发因子/运维因子/规模变更）改为草稿态。`patchOverride` 在全局模式不再 return，而是把改动写入本地 `draftBuffer`（`Record<string, unknown>`，key = leaf path）。每个 tab 顶部渲染三按钮。`OverrideField` / `FactorTable` 的 `model-value` 在全局模式优先读 `draftBuffer` 里的值。项目模式行为完全不变。

- [ ] Step 1 写失败测试 `web/src/__tests__/views/ParamManager-global-draft.test.ts`：

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ParamManager from "@/views/ParamManager.vue";
import { paramsApi } from "@/api/params";

vi.mock("@/api/params", () => ({
  paramsApi: {
    effective: vi.fn(),
    global: vi.fn(),
    override: vi.fn(),
    patchGlobal: vi.fn().mockResolvedValue({ updated: "x" }),
    resetGlobal: vi.fn(),
  },
}));
vi.mock("@/api/snapshots", () => ({
  snapshotsApi: { list: vi.fn().mockResolvedValue([]) },
}));

const globalEff = {
  cf: { bidding: 1.21 },
  productivity_dev: { 电子政务: { P10: 2.04, P50: 6.41, P90: 15.36 } },
  productivity_ops: {},
  city_rate: { 北京: { dev: 32198, ops: 26335, class: "A" } },
  factors_dev: {},
  factors_ops: {},
  hours_per_pm: 174,
  ops_cost_ratio: { P50: 0.0902 },
  overrides: {},
};

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: "/parameters", component: ParamManager, name: "global-params" }],
});

function mountGlobal() {
  return mount(ParamManager, {
    props: { projectId: null },
    global: { plugins: [createPinia(), router] },
  });
}

describe("ParamManager — 全局草稿编辑", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    (paramsApi.global as ReturnType<typeof vi.fn>).mockResolvedValue(globalEff);
    (paramsApi.resetGlobal as ReturnType<typeof vi.fn>).mockResolvedValue(globalEff);
  });

  it("全局模式改 OverrideField → 不即时落库，写入草稿", async () => {
    const w = mountGlobal();
    await flushPromises();
    const input = w.find("input[type='number']");
    await input.setValue(40000);
    await flushPromises();
    // 草稿态：patchGlobal 未被调用
    expect(paramsApi.patchGlobal).not.toHaveBeenCalled();
    // 出现未保存提示
    expect(w.find("[data-testid='draft-dirty']").exists()).toBe(true);
  });

  it("点保存 → 逐 leaf 调 patchGlobal", async () => {
    const w = mountGlobal();
    await flushPromises();
    const input = w.find("input[type='number']");
    await input.setValue(40000);
    await flushPromises();
    await w.find("[data-testid='draft-save']").trigger("click");
    await flushPromises();
    expect(paramsApi.patchGlobal).toHaveBeenCalledWith("city_rate.北京.dev", 40000);
  });

  it("点撤销 → 丢弃草稿，dirty 提示消失", async () => {
    const w = mountGlobal();
    await flushPromises();
    await w.find("input[type='number']").setValue(40000);
    await flushPromises();
    await w.find("[data-testid='draft-undo']").trigger("click");
    await flushPromises();
    expect(w.find("[data-testid='draft-dirty']").exists()).toBe(false);
  });

  it("点还原出厂 → 二次确认后调 resetGlobal", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const w = mountGlobal();
    await flushPromises();
    await w.find("[data-testid='draft-reset']").trigger("click");
    await flushPromises();
    expect(paramsApi.resetGlobal).toHaveBeenCalled();
  });

  it("还原出厂 — 用户取消确认 → 不调 resetGlobal", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const w = mountGlobal();
    await flushPromises();
    await w.find("[data-testid='draft-reset']").trigger("click");
    await flushPromises();
    expect(paramsApi.resetGlobal).not.toHaveBeenCalled();
  });
});
```

- [ ] Step 2 跑测试确认失败：
```
cd web && npx vitest run src/__tests__/views/ParamManager-global-draft.test.ts
```
预期失败：`[data-testid='draft-dirty']` 等元素不存在；且改值在全局模式被 `patchOverride` 的 `if(!projectId) return` 丢弃。

- [ ] Step 3 写最小实现。改 `web/src/views/ParamManager.vue` 的 `<script setup>`：

在 `const eff = computed(() => store.effective);` 之后新增草稿态：

```typescript
// ── 全局模式草稿态（项目模式不用）─────────────────────────────────
const draftBuffer = ref<Record<string, unknown>>({});
const isGlobal = computed(() => !props.projectId);
const isDirty = computed(() => Object.keys(draftBuffer.value).length > 0);
const savingDraft = ref(false);

// 草稿优先：全局模式下若某 leaf 在 draftBuffer 里，显示草稿值。
function draftValue(path: string, fallback: unknown): unknown {
  if (isGlobal.value && path in draftBuffer.value) {
    return draftBuffer.value[path];
  }
  return fallback;
}

async function saveDraft(): Promise<void> {
  savingDraft.value = true;
  try {
    for (const [key, value] of Object.entries(draftBuffer.value)) {
      await paramsApi.patchGlobal(key, value);
    }
    draftBuffer.value = {};
    await store.loadGlobal();
    results.markParamsChanged();
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "保存失败";
  } finally {
    savingDraft.value = false;
  }
}

function undoDraft(): void {
  draftBuffer.value = {};
}

async function resetToFactory(): Promise<void> {
  if (!window.confirm("还原出厂会丢弃所有全局参数改动，重置为 CSBMK 默认值。确定继续？")) {
    return;
  }
  try {
    await paramsApi.resetGlobal();
    draftBuffer.value = {};
    await store.loadGlobal();
    results.markParamsChanged();
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "还原失败";
  }
}
```

在文件顶部 import 区补 `import { paramsApi } from "@/api/params";`。

替换 `patchOverride` 函数：

```typescript
// 项目模式：即时落库（行为不变）。全局模式：写入草稿缓冲，不即时落库。
async function patchOverride(key: string, value: unknown): Promise<void> {
  if (props.projectId) {
    await store.applyOverride(props.projectId, { [key]: value });
    results.markParamsChanged();
  } else {
    draftBuffer.value = { ...draftBuffer.value, [key]: value };
  }
}
```

在 `<template>` 里，每个参数 tab 的 `<section role="tabpanel">` 内顶部（紧跟 `<h2>` 之后），统一加一个草稿工具条。最简洁做法是在 5 个 tab（rate / productivity / factors_dev / factors_ops / scale_change）共用的位置插入。在 `<div v-else class="card param-card">` 内、`<div role="tablist">` 之后、第一个 `<section>` 之前插入：

```html
      <div
        v-if="isGlobal"
        class="draft-toolbar"
      >
        <span
          v-if="isDirty"
          data-testid="draft-dirty"
          class="draft-dirty"
        >● 有未保存的修改</span>
        <span v-else class="draft-clean">参数已是最新保存状态</span>
        <div class="draft-actions">
          <button
            type="button"
            data-testid="draft-save"
            class="btn-primary"
            :disabled="!isDirty || savingDraft"
            @click="saveDraft"
          >{{ savingDraft ? "保存中…" : "保存" }}</button>
          <button
            type="button"
            data-testid="draft-undo"
            class="btn-secondary"
            :disabled="!isDirty"
            @click="undoDraft"
          >撤销</button>
          <button
            type="button"
            data-testid="draft-reset"
            class="btn-link"
            @click="resetToFactory"
          >还原出厂</button>
        </div>
      </div>
```

把各 tab 里 `OverrideField` 的 `:model-value` 从直接读 `eff` 改为经 `draftValue`。例如费率 tab 的开发费率：

```html
            <OverrideField
              :label="`${city}（开发）`"
              :model-value="draftValue(`city_rate.${String(city)}.dev`, rate.dev)"
              :default-value="rate.dev"
              :overridden="store.isOverridden(`city_rate.${String(city)}.dev`)"
              @update:model-value="(nv) => patchOverride(`city_rate.${String(city)}.dev`, nv)"
            />
```

对运维费率、生产率（dev/ops）、`scale_change` 的 `OverrideField` 同样把 `:model-value` 包成 `draftValue(path, 原值)`，`path` 用对应的 leaf 路径字符串。`factors_dev` / `factors_ops` 的 `FactorTable` 因走 `onFactorEdit → patchOverride`，无需改 model-value（FactorTable 的输入值在编辑后由 patchOverride 写入草稿，下次 store 刷新前显示沿用 FactorTable 内部 state）。

在 `<style scoped>` 末尾加：

```css
.draft-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-5);
  background: var(--color-bg-hover);
  border-bottom: 1px solid var(--color-border);
  font-size: var(--font-size-sm);
}
.draft-dirty {
  color: var(--color-danger, #b91c1c);
  font-weight: 600;
}
.draft-clean {
  color: var(--color-text-muted);
}
.draft-actions {
  display: flex;
  gap: var(--space-2);
}
.draft-actions .btn-link {
  background: transparent;
  border: none;
  color: var(--color-danger, #b91c1c);
  cursor: pointer;
  text-decoration: underline;
  font-family: inherit;
  font-size: var(--font-size-sm);
}
```

- [ ] Step 4 跑测试确认通过：
```
cd web && npx vitest run src/__tests__/views/ParamManager-global-draft.test.ts src/__tests__/views/ParamManager.test.ts && npx vue-tsc --noEmit
```
预期 `ParamManager-global-draft.test.ts` 5 passed；既有 `ParamManager.test.ts`（项目模式即时保存）不回归；vue-tsc 无错误。

- [ ] Step 5 提交：
```
git add web/src/views/ParamManager.vue web/src/__tests__/views/ParamManager-global-draft.test.ts
git commit -m "feat(web): ParamManager 全局草稿编辑 + 保存/撤销/还原三按钮"
```

---

## Phase D — 反算三级模块树细化 + AI 补全 FP

### Task D1: 三级模块树分摊

**Files:**
- Modify `server/app/services/calc.py`
- Test `server/tests/unit/test_module_tree_allocation.py`

> `_allocate_ufp_to_modules` 从「按一级模块一层分摊」改为「沿 子系统→一级→二级 树逐层分摊」。改为纯函数 `_build_module_tree(fps, target_ufp)`，便于单测（不依赖 DB）。`run_reverse` 调它产出 `module_allocation_tree`。同时保留 `module_allocation`（扁平叶子列表）供旧前端兼容期内不破坏 —— 但本计划 D3 会把前端切到 tree，保留扁平字段一个版本即可，这里两者都输出。

- [ ] Step 1 写失败测试 `server/tests/unit/test_module_tree_allocation.py`：

```python
"""v2.8 — 反算三级模块树逐层分摊单元测试。"""
from app.services.calc import build_module_tree


class _FP:
    """轻量 FP stub（只有树分摊用到的字段）。"""
    def __init__(self, subsystem, l1, l2, ufp):
        self.subsystem = subsystem
        self.l1_module = l1
        self.l2_module = l2
        self.ufp = ufp


def test_single_branch_proportional_split():
    fps = [
        _FP("结算", "资金", "查询", 40),
        _FP("结算", "资金", "对账", 60),
    ]
    tree = build_module_tree(fps, target_ufp=200)
    # 根下一个子系统节点
    assert len(tree) == 1
    sub = tree[0]
    assert sub["subsystem"] == "结算"
    assert sub["current_ufp"] == 100
    assert sub["allocated_ufp"] == 200
    # 一级模块「资金」承载全部
    l1 = sub["children"][0]
    assert l1["l1_module"] == "资金"
    assert l1["allocated_ufp"] == 200
    # 二级：查询 40/100 → 80；对账 60/100 → 120
    leaves = {c["l2_module"]: c for c in l1["children"]}
    assert abs(leaves["查询"]["allocated_ufp"] - 80) < 0.01
    assert abs(leaves["对账"]["allocated_ufp"] - 120) < 0.01
    assert abs(leaves["查询"]["delta_ufp"] - 40) < 0.01


def test_multi_subsystem_split():
    fps = [
        _FP("A", "m1", "f1", 30),
        _FP("B", "m2", "f2", 70),
    ]
    tree = build_module_tree(fps, target_ufp=100)
    subs = {n["subsystem"]: n for n in tree}
    assert abs(subs["A"]["allocated_ufp"] - 30) < 0.01
    assert abs(subs["B"]["allocated_ufp"] - 70) < 0.01
    assert abs(subs["A"]["ratio"] - 0.3) < 0.001


def test_empty_fps_returns_empty_tree():
    assert build_module_tree([], target_ufp=100) == []


def test_node_carries_current_allocated_delta_ratio_children():
    fps = [_FP("S", "L1", "L2", 50)]
    tree = build_module_tree(fps, target_ufp=120)
    node = tree[0]
    for key in ("subsystem", "current_ufp", "allocated_ufp",
                "delta_ufp", "ratio", "children"):
        assert key in node


def test_zero_total_current_ufp_no_div_by_zero():
    fps = [_FP("S", "L1", "L2", 0)]
    tree = build_module_tree(fps, target_ufp=100)
    # 全 0 → ratio 0，allocated 0，不抛 ZeroDivisionError
    assert tree[0]["ratio"] == 0.0
    assert tree[0]["allocated_ufp"] == 0.0
```

- [ ] Step 2 跑测试确认失败：
```
cd server && .venv/bin/python -m pytest tests/unit/test_module_tree_allocation.py -q
```
预期失败：`ImportError: cannot import name 'build_module_tree' from 'app.services.calc'`。

- [ ] Step 3 写最小实现。在 `server/app/services/calc.py` 里，替换 `_allocate_ufp_to_modules` 函数为 `build_module_tree` + 一个 `run_reverse` 适配。

新增纯函数（放在 `_allocate_ufp_to_modules` 原位置）：

```python
def build_module_tree(fps: list, target_ufp: float) -> list[dict]:
    """沿 子系统→一级→二级 模块树逐层分摊目标 UFP。

    纯函数：fps 是带 subsystem/l1_module/l2_module/ufp 属性的对象列表。
    每层按现有 UFP 占比把上层 allocated_ufp 分到子节点。
    返回子系统节点列表，每节点含 current_ufp/allocated_ufp/delta_ufp/
    ratio/children。FP 列表为空 → 返回 []。
    """
    if not fps:
        return []

    # 三级分组：subsystem → l1 → l2 → 累计 ufp
    tree: dict[str, dict[str, dict[str, float]]] = {}
    for fp in fps:
        sub = fp.subsystem or "未分组"
        l1 = fp.l1_module or "未分类"
        l2 = fp.l2_module or "未细分"
        tree.setdefault(sub, {}).setdefault(l1, {})
        tree[sub][l1][l2] = tree[sub][l1].get(l2, 0.0) + float(fp.ufp or 0.0)

    total = sum(
        u for subv in tree.values()
        for l1v in subv.values() for u in l1v.values()
    )

    def _split(current: float, parent_alloc: float, parent_total: float) -> tuple:
        """返回 (ratio, allocated)。parent_total 为 0 时 ratio=0。"""
        ratio = current / parent_total if parent_total > 0 else 0.0
        return ratio, parent_alloc * ratio

    out: list[dict] = []
    for sub in sorted(tree.keys()):
        sub_cur = sum(u for l1v in tree[sub].values() for u in l1v.values())
        sub_ratio, sub_alloc = _split(sub_cur, target_ufp, total)
        sub_node = {
            "subsystem": sub,
            "current_ufp": round(sub_cur, 2),
            "allocated_ufp": round(sub_alloc, 2),
            "delta_ufp": round(sub_alloc - sub_cur, 2),
            "ratio": round(sub_ratio, 4),
            "children": [],
        }
        for l1 in sorted(tree[sub].keys()):
            l1_cur = sum(tree[sub][l1].values())
            l1_ratio, l1_alloc = _split(l1_cur, sub_alloc, sub_cur)
            l1_node = {
                "l1_module": l1,
                "current_ufp": round(l1_cur, 2),
                "allocated_ufp": round(l1_alloc, 2),
                "delta_ufp": round(l1_alloc - l1_cur, 2),
                "ratio": round(l1_ratio, 4),
                "children": [],
            }
            for l2 in sorted(tree[sub][l1].keys()):
                l2_cur = tree[sub][l1][l2]
                l2_ratio, l2_alloc = _split(l2_cur, l1_alloc, l1_cur)
                l1_node["children"].append({
                    "l2_module": l2,
                    "current_ufp": round(l2_cur, 2),
                    "allocated_ufp": round(l2_alloc, 2),
                    "delta_ufp": round(l2_alloc - l2_cur, 2),
                    "ratio": round(l2_ratio, 4),
                })
            sub_node["children"].append(l1_node)
        out.append(sub_node)
    return out


def _flatten_tree_leaves(tree: list[dict]) -> list[dict]:
    """把三级树压成叶子列表（兼容旧前端 module_allocation 字段）。"""
    leaves: list[dict] = []
    for sub in tree:
        for l1 in sub["children"]:
            for l2 in l1["children"]:
                leaves.append({
                    "subsystem": sub["subsystem"],
                    "l1_module": l1["l1_module"],
                    "l2_module": l2["l2_module"],
                    "current_ufp": l2["current_ufp"],
                    "allocated_ufp": l2["allocated_ufp"],
                    "delta_ufp": l2["delta_ufp"],
                    "ratio": l2["ratio"],
                })
    return leaves
```

改 `run_reverse` 函数末尾 —— 把 `out["module_allocation"] = _allocate_ufp_to_modules(...)` 那段替换为：

```python
    rec = out.get("recommended_band", "P50")
    target_ufp = out["scale_unadjusted_bands"][rec]
    out["target_ufp"] = round(target_ufp, 2)
    fps = fs.list_for_project(db, project_id)
    tree = build_module_tree(fps, target_ufp)
    out["module_allocation_tree"] = tree
    out["module_allocation"] = _flatten_tree_leaves(tree)
    return out
```

- [ ] Step 4 跑测试确认通过：
```
cd server && .venv/bin/python -m pytest tests/unit/test_module_tree_allocation.py tests/integration/test_calc_api.py -q
```
预期 `test_module_tree_allocation.py` 5 passed；既有 calc 测试不回归。

- [ ] Step 5 提交：
```
git add server/app/services/calc.py server/tests/unit/test_module_tree_allocation.py
git commit -m "feat(server): 反算三级模块树逐层分摊 build_module_tree"
```

---

### Task D2: reverse_fill AI 任务类型 + 缺口计算

**Files:**
- Modify `server/app/schemas/ai_tasks.py`, `server/app/services/ai_tasks.py`, `server/app/api/ai_tasks.py`
- Create `commands/cost-fill.md`
- Test `server/tests/integration/test_v2_8_reverse_fill_task.py`

> 设计：`reverse_fill` 复用现有 `AiTask` 表 + spawn + 轮询机制。后端任务类型 `reverse_fill`；`start_task` 按 `task.kind` 分派 —— `extract` → `spawn_claude_extract`（跑 `/cost-estimation:cost`）；`reverse_fill` → `spawn_claude_reverse_fill`（跑 `/cost-estimation:cost-fill`）。`cost-fill.md` 命令的 prompt 要点见下。缺口计算：插件拿到反算 `module_allocation_tree`，对每个叶子比较 `delta_ufp`，缺口（delta>0）生成 FP 草稿、超出（delta<0）下调现有 FP 的 us。

- [ ] Step 1 写失败测试 `server/tests/integration/test_v2_8_reverse_fill_task.py`：

```python
"""v2.8 — reverse_fill AI 任务：创建 + 状态机 + 缺口分摊。"""
import pytest
from app.db.models import Project, FunctionPoint

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


def _seed(db, pid="p-revfill"):
    p = Project(id=pid, name="reverse fill",
                project_type="dev_only", phase="bidding",
                city="北京", industry="电子政务",
                mode="reverse", basis_data_ver="CSBMK-202510",
                target_cost=1000000)
    db.add(p)
    db.add(FunctionPoint(id="fp-seed-1", project_id=pid, version=1,
                         subsystem="结算", l1_module="资金", l2_module="查询",
                         category="EQ", complexity="average",
                         modify_type="add", ufp=4, us=4))
    db.commit()
    return p


@pytest.mark.asyncio
async def test_create_reverse_fill_task(client_factory, db_session):
    _seed(db_session)
    async with await client_factory() as client:
        r = await client.post("/api/ai-tasks", headers=H,
                               json={"project_id": "p-revfill", "kind": "reverse_fill"})
        assert r.status_code == 201
        body = r.json()
        assert body["kind"] == "reverse_fill"
        assert body["status"] == "queued"


@pytest.mark.asyncio
async def test_reverse_fill_task_progress_flow(client_factory, db_session):
    """模拟 cost-fill 插件的进度上报序列。"""
    _seed(db_session, pid="p-revfill-2")
    async with await client_factory() as client:
        r = await client.post("/api/ai-tasks", headers=H,
                               json={"project_id": "p-revfill-2", "kind": "reverse_fill"})
        task_id = r.json()["id"]
        for pct, log in [
            (15, "✓ 加载反算模块树"),
            (45, "✓ 计算各叶子缺口"),
            (80, "✓ 生成补全 FP 草稿"),
        ]:
            r = await client.patch(f"/api/ai-tasks/{task_id}", headers=H,
                                   json={"status": "running", "progress_pct": pct,
                                         "stage_log_append": log})
            assert r.status_code == 200
        r = await client.patch(f"/api/ai-tasks/{task_id}", headers=H,
                               json={"status": "done", "progress_pct": 100,
                                     "stage_log_append": "✓ 完成"})
        assert r.json()["status"] == "done"
        assert "计算各叶子缺口" in r.json()["stage_log"]


@pytest.mark.asyncio
async def test_reverse_fill_writes_reverse_draft_fp(client_factory, db_session):
    """cost-fill 写入的 FP source=reverse_draft，能被 functions API 读出。"""
    _seed(db_session, pid="p-revfill-3")
    async with await client_factory() as client:
        r = await client.post(
            "/api/projects/p-revfill-3/functions/bulk",
            headers={**H, "Content-Type": "application/json"},
            json={"items": [{
                "subsystem": "结算", "l1_module": "资金", "l2_module": "查询",
                "name": "AI补全-账户明细查询", "category": "EQ",
                "complexity": "average", "det": 12, "ftr": 2,
                "ufp": 4, "us": 4, "modify_type": "add",
                "source": "reverse_draft",
                "description": "按反算缺口补全的功能点草稿",
            }], "replace": False},
        )
        assert r.status_code == 201
        r = await client.get("/api/projects/p-revfill-3/functions", headers=H)
        sources = {fp["source"] for fp in r.json()["data"]}
        assert "reverse_draft" in sources
```

- [ ] Step 2 跑测试确认失败：
```
cd server && .venv/bin/python -m pytest tests/integration/test_v2_8_reverse_fill_task.py -q
```
预期失败：`create_reverse_fill_task` 因 `AiTaskCreate.kind` 不接受 `reverse_fill`（pydantic 422）；`writes_reverse_draft_fp` 因 FP schema `source` 字面量不含 `reverse_draft`（422）。

- [ ] Step 3 写最小实现。

改 `server/app/schemas/ai_tasks.py` —— `AiTaskCreate.kind` 字面量加 `reverse_fill`：

```python
class AiTaskCreate(BaseModel):
    project_id: str
    kind: Literal["extract", "allocate", "reverse_fill"]
```

改 `server/app/schemas/functions.py` —— `FunctionPointBase.source` 字面量加 `reverse_draft`：

```python
    source: Optional[
        Literal["manual", "imported", "ai_extracted", "claude_draft",
                "allocator", "copied", "reverse_draft"]
    ] = "manual"
```

改 `server/app/services/ai_tasks.py` —— 在 `spawn_claude_extract` 之后新增 `spawn_claude_reverse_fill`（与 `spawn_claude_extract` 几乎一致，仅 stdin 喂的命令不同）：

```python
def spawn_claude_reverse_fill(
    task_id: str,
    project_id: str,
    base_url: str,
    token: str,
) -> int | None:
    """v2.8 — 后台 spawn claude 跑 /cost-estimation:cost-fill <project_id>。

    与 spawn_claude_extract 同构（env vars + stdin 喂命令），仅命令不同：
    cost-fill 命令读反算模块树缺口、生成补全 FP 草稿写回 FP 表。
    """
    claude_bin = shutil.which("claude")
    if not claude_bin:
        return None
    cmd = [claude_bin, "--print", "--allowed-tools", "Bash Read"]
    _local_hosts = "127.0.0.1,localhost"
    _existing_np = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""
    _no_proxy = (f"{_existing_np},{_local_hosts}".strip(",")
                 if _existing_np else _local_hosts)
    env = {
        **os.environ,
        "BASE": base_url, "TOKEN": token,
        "PROJECT_ID": project_id, "TASK_ID": task_id,
        "NO_PROXY": _no_proxy, "no_proxy": _no_proxy,
    }
    log_path = Path(os.environ.get("COST_DATA_DIR", "/tmp")) / f"ai-task-{task_id}.log"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_fh = open(log_path, "w")  # noqa: SIM115
    except OSError:
        log_fh = subprocess.DEVNULL  # type: ignore[assignment]
    proc = subprocess.Popen(
        cmd, env=env, stdin=subprocess.PIPE,
        stdout=log_fh, stderr=subprocess.STDOUT, start_new_session=True,
    )
    try:
        assert proc.stdin is not None
        proc.stdin.write(f"/cost-estimation:cost-fill {project_id}\n".encode())
        proc.stdin.close()
    except (BrokenPipeError, OSError):
        pass
    if log_fh is not subprocess.DEVNULL:
        try:
            log_fh.close()
        except OSError:
            pass
    return proc.pid
```

改 `server/app/api/ai_tasks.py` —— `start_task` 按 kind 分派。把 `pid = svc.spawn_claude_extract(...)` 行替换为：

```python
    base_url = os.environ.get("COST_BASE_URL", "http://127.0.0.1:8788")
    token = os.environ.get("COST_AUTH_TOKEN", "")
    if t.kind == "reverse_fill":
        pid = svc.spawn_claude_reverse_fill(t.id, t.project_id, base_url, token)
    else:
        pid = svc.spawn_claude_extract(t.id, t.project_id, base_url, token)
```

新建 `commands/cost-fill.md`：

```markdown
---
description: 对 <project_id> 按反算模块树缺口 AI 补全功能点草稿
allowed-tools: Bash, Read
---

# /cost-fill — 反算补全功能点

参数：**`<project_id>`**（必填）。对该项目执行反算缺口补全。

要求：后端已在运行、项目为反算模式且已设置目标造价。

## Step 1：读取鉴权信息 + 健康检查

```bash
DATA_DIR="$HOME/.claude/projects/cost-estimation"
PORT=$(cat "$DATA_DIR/.port" 2>/dev/null)
TOKEN=$(cat "$DATA_DIR/.token" 2>/dev/null)
if [ -z "$PORT" ] || [ -z "$TOKEN" ]; then
  echo "✗ 找不到运行中的服务。请先运行 /cost-estimation:cost 启动。"
  exit 1
fi
BASE="http://127.0.0.1:$PORT"
curl -fsS "$BASE/health" >/dev/null || { echo "✗ 后端无响应。"; exit 1; }
```

所有 `/api/*` 请求带 header `X-Auth-Token: $TOKEN` 与 `Content-Type: application/json`。

## Step 2：创建 reverse_fill 任务

```bash
PROJECT_ID="<project_id>"
TASK_ID=$(curl -fsS -X POST "$BASE/api/ai-tasks" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d "{\"project_id\":\"$PROJECT_ID\",\"kind\":\"reverse_fill\"}" | jq -r .id)
```

## Step 3：拉取反算结果（含三级模块树）

```bash
curl -fsS -X POST "$BASE/api/calc/reverse" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d "{\"project_id\":\"$PROJECT_ID\"}" > /tmp/reverse-$TASK_ID.json
```

读 `/tmp/reverse-$TASK_ID.json` 的 `module_allocation_tree`。进度上报：

```bash
curl -fsS -X PATCH "$BASE/api/ai-tasks/$TASK_ID" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d '{"status":"running","progress_pct":15,"stage_log_append":"✓ 加载反算模块树"}' \
  > /dev/null || true
```

## Step 4：逐叶子计算缺口并生成 FP 草稿

遍历 `module_allocation_tree` 的每个二级叶子节点：

- **缺口（`delta_ufp` > 0）**：为该叶子模块生成若干功能点草稿，UFP 合计 ≈ `delta_ufp`。
  每条草稿要给出 `name`（结合 `subsystem/l1_module/l2_module` 语境的合理功能名）、
  `description`（一句话功能说明）、`category`（EI/EO/EQ/ILF/EIF）、`det` + `ret`/`ftr`
  （按 IFPUG 估计）。`source` 必须为 `"reverse_draft"`。
- **超出（`delta_ufp` < 0）**：不新增 FP，按比例下调该叶子模块现有 FP 的 `us`。
  这是反算补全的预期行为（用户主动触发「按反算补全 FP」），只下调规模、不删条目。
  做法：对该叶子模块 `GET /api/projects/<project_id>/functions`，按
  `subsystem` + `l1_module` + `l2_module` 过滤出属于它的 FP，算
  `ratio = allocated_ufp / current_ufp`（0 < ratio < 1），逐条
  `PATCH /api/projects/<project_id>/functions/<fp_id>` 把 `us` 改为
  `round(us × ratio, 2)`。`ufp` 不动（IFPUG 计数值），只调 `us`（规模口径）。
  下调完成后 stage_log 注明「模块 X 现有 FP 规模已按 ratio 下调」。

  下调单条 FP 的命令形如：
  ```bash
  curl -fsS -X PATCH "$BASE/api/projects/<project_id>/functions/<fp_id>" \
    -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
    -d "{\"us\": <us×ratio>}" > /dev/null || true
  ```

若项目已上传文档，先 `GET /api/projects/<project_id>/uploads` 拿语境，让草稿名称
更贴合真实需求。进度上报 45：

```bash
curl -fsS -X PATCH "$BASE/api/ai-tasks/$TASK_ID" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d '{"progress_pct":45,"stage_log_append":"✓ 计算各叶子缺口"}' > /dev/null || true
```

## Step 5：批量写入 FP 表

```bash
curl -fsS -X POST "$BASE/api/projects/<project_id>/functions/bulk" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d '{"items":[ ... reverse_draft 草稿数组 ... ],"replace":false}'
```

- `source` 必须为 `"reverse_draft"`，`replace=false`（追加，不覆盖用户 FP）。
- `subsystem` + `l1_module` 必填，`l2_module` 用叶子节点的 `l2_module`。
- `ufp` / `us` 按 IFPUG 类别 × 复杂度取值；草稿合计 ≈ 各叶子缺口。

进度上报 80，完成后置 done：

```bash
curl -fsS -X PATCH "$BASE/api/ai-tasks/$TASK_ID" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d '{"progress_pct":80,"stage_log_append":"✓ 生成补全 FP 草稿"}' > /dev/null || true
curl -fsS -X PATCH "$BASE/api/ai-tasks/$TASK_ID" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d '{"status":"done","progress_pct":100,"stage_log_append":"✓ 完成"}' > /dev/null || true
```

## 错误兜底

任何步骤失败，退出前调用：

```bash
curl -fsS -X PATCH "$BASE/api/ai-tasks/$TASK_ID" \
  -H "X-Auth-Token: $TOKEN" -H "content-type: application/json" \
  -d '{"status":"failed","error_message":"反算补全流程中断"}' > /dev/null || true
```

## 不要做的事

- 不要**删除**用户已有 FP（超出场景只按比例下调现有 FP 的 `us`，不删条目、不动 `ufp`）。
- 缺口场景写入的草稿一律 `source="reverse_draft"`、`replace=false`，不覆盖用户 FP。
- 不要修改 params_global。
- 不要绕过 token 鉴权。
```

- [ ] Step 4 跑测试确认通过：
```
cd server && .venv/bin/python -m pytest tests/integration/test_v2_8_reverse_fill_task.py tests/integration/test_v2_2_ai_tasks_api.py tests/integration/test_v2_5_ai_task_spawn.py -q
```
预期 `test_v2_8_reverse_fill_task.py` 3 passed；既有 ai-tasks 测试不回归。

- [ ] Step 5 提交：
```
git add server/app/schemas/ai_tasks.py server/app/schemas/functions.py server/app/services/ai_tasks.py server/app/api/ai_tasks.py commands/cost-fill.md server/tests/integration/test_v2_8_reverse_fill_task.py
git commit -m "feat(server): reverse_fill AI 任务 + cost-fill 插件命令"
```

---

### Task D3: 前端反算树形分摊表 + 「按反算补全 FP」按钮

**Files:**
- Modify `web/src/api/calc.ts`, `web/src/api/aiTasks.ts`, `web/src/views/ResultView.vue`
- Test `web/src/__tests__/views/ResultView-module-tree.test.ts`

- [ ] Step 1 写失败测试 `web/src/__tests__/views/ResultView-module-tree.test.ts`：

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import ResultView from "@/views/ResultView.vue";
import { calcApi } from "@/api/calc";
import { projectsApi } from "@/api/projects";
import { aiTasksApi } from "@/api/aiTasks";

vi.mock("@/api/calc", () => ({
  calcApi: { forward: vi.fn(), reverse: vi.fn(), allocate: vi.fn() },
}));
vi.mock("@/api/projects", () => ({
  projectsApi: { get: vi.fn() },
}));
vi.mock("@/api/aiTasks", () => ({
  aiTasksApi: {
    create: vi.fn().mockResolvedValue({ id: "task-rf" }),
    start: vi.fn().mockResolvedValue({ pid: 123 }),
    list: vi.fn().mockResolvedValue([]),
    get: vi.fn(),
  },
}));

const reverseResult = {
  budget_for_dev: 800000,
  budget_for_ops: 0,
  scale_adjusted_bands: { P10: 100, P50: 200, P90: 300 },
  scale_unadjusted_bands: { P10: 80, P50: 165, P90: 250 },
  cf_used: 1.21,
  recommended_band: "P50",
  target_ufp: 165,
  module_allocation: [],
  module_allocation_tree: [
    {
      subsystem: "结算", current_ufp: 100, allocated_ufp: 165,
      delta_ufp: 65, ratio: 1.0,
      children: [
        {
          l1_module: "资金", current_ufp: 100, allocated_ufp: 165,
          delta_ufp: 65, ratio: 1.0,
          children: [
            { l2_module: "查询", current_ufp: 40, allocated_ufp: 66,
              delta_ufp: 26, ratio: 0.4 },
            { l2_module: "对账", current_ufp: 60, allocated_ufp: 99,
              delta_ufp: 39, ratio: 0.6 },
          ],
        },
      ],
    },
  ],
};

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: "/projects/:id/result", component: ResultView, name: "result" }],
});

async function mountResult() {
  (projectsApi.get as ReturnType<typeof vi.fn>).mockResolvedValue({
    id: "p-1", name: "T", mode: "reverse", target_cost: 100,
  });
  (calcApi.reverse as ReturnType<typeof vi.fn>).mockResolvedValue(reverseResult);
  router.push("/projects/p-1/result");
  await router.isReady();
  const w = mount(ResultView, {
    props: { projectId: "p-1" },
    global: { plugins: [createPinia(), router] },
  });
  await flushPromises();
  return w;
}

describe("ResultView — 反算三级模块树", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("渲染三级树节点（子系统/一级/二级）", async () => {
    const w = await mountResult();
    expect(w.text()).toContain("结算");
    expect(w.text()).toContain("资金");
    expect(w.text()).toContain("查询");
    expect(w.text()).toContain("对账");
  });

  it("「按反算补全 FP」按钮触发 reverse_fill AI 任务", async () => {
    const w = await mountResult();
    await w.find("[data-testid='reverse-fill-btn']").trigger("click");
    await flushPromises();
    expect(aiTasksApi.create).toHaveBeenCalledWith("p-1", "reverse_fill");
    expect(aiTasksApi.start).toHaveBeenCalledWith("task-rf");
  });
});
```

- [ ] Step 2 跑测试确认失败：
```
cd web && npx vitest run src/__tests__/views/ResultView-module-tree.test.ts
```
预期失败：`[data-testid='reverse-fill-btn']` 不存在；树节点未渲染（旧表只读扁平 `module_allocation`）。

- [ ] Step 3 写最小实现。

改 `web/src/api/calc.ts` —— 把 `ModuleUfpAllocation` 接口之后新增树节点类型，并在 `ReverseResult` 加 `module_allocation_tree`：

```typescript
/** 反算三级模块树节点。subsystem/l1_module/l2_module 三层各一种形状。 */
export interface ModuleTreeL2 {
  l2_module: string;
  current_ufp: number;
  allocated_ufp: number;
  delta_ufp: number;
  ratio: number;
}
export interface ModuleTreeL1 {
  l1_module: string;
  current_ufp: number;
  allocated_ufp: number;
  delta_ufp: number;
  ratio: number;
  children: ModuleTreeL2[];
}
export interface ModuleTreeSubsystem {
  subsystem: string;
  current_ufp: number;
  allocated_ufp: number;
  delta_ufp: number;
  ratio: number;
  children: ModuleTreeL1[];
}
```

`ReverseResult` 接口体内 `module_allocation` 行之后加：

```typescript
  module_allocation_tree?: ModuleTreeSubsystem[];
```

改 `web/src/api/aiTasks.ts` —— `AiTaskKind` 加 `reverse_fill`：

```typescript
export type AiTaskKind = "extract" | "allocate" | "reverse_fill";
```

改 `web/src/views/ResultView.vue`：

`<script setup>` 里 import 补 `aiTasksApi`（若已 import 则跳过），并新增补全任务状态：

```typescript
import { aiTasksApi } from "@/api/aiTasks";

const reverseFillPending = ref(false);
const reverseFillMsg = ref("");

async function triggerReverseFill(): Promise<void> {
  reverseFillPending.value = true;
  reverseFillMsg.value = "";
  try {
    const task = await aiTasksApi.create(props.projectId, "reverse_fill");
    await aiTasksApi.start(task.id);
    reverseFillMsg.value = "已启动 AI 补全任务，请在 FP 编辑页的任务面板查看进度";
  } catch (e: unknown) {
    reverseFillMsg.value = e instanceof Error ? e.message : "补全任务启动失败";
  } finally {
    reverseFillPending.value = false;
  }
}
```

> 注：`ResultView.vue` 的 props 若是 `projectId`，用 `props.projectId`；若组件内已有 `const projectId = ...` 则改用该变量。实施时按文件实际命名对齐。

`<template>` 里把「反算 UFP 模块细化分摊」那个 `<div class="card">`（含旧的扁平 `<table>`）整体替换为三级树展示 + 补全按钮：

```html
        <!-- 反算 UFP 三级模块树细化分摊 -->
        <div
          v-if="reverseResult!.module_allocation_tree && reverseResult!.module_allocation_tree.length"
          class="card"
          style="padding: 20px"
        >
          <div
            style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px"
          >
            <div class="section-title">反算 UFP 模块树细化分摊</div>
            <button
              type="button"
              data-testid="reverse-fill-btn"
              class="btn btn-primary btn-sm"
              :disabled="reverseFillPending"
              @click="triggerReverseFill"
            >
              {{ reverseFillPending ? "启动中…" : "按反算补全 FP" }}
            </button>
          </div>
          <div class="muted" style="font-size: 12px; margin-bottom: 12px">
            目标可承载 UFP <b class="mono">{{ reverseResult!.target_ufp.toFixed(2) }}</b>，
            沿 子系统 → 一级 → 二级 模块树逐层按现有 UFP 占比分摊。
            「按反算补全 FP」会让 AI 为有缺口的叶子模块生成功能点草稿（需人工审核后采纳）。
          </div>
          <div
            v-if="reverseFillMsg"
            class="banner banner-green"
            role="status"
            style="margin-bottom: 12px"
          >
            {{ reverseFillMsg }}
          </div>
          <table class="table">
            <thead>
              <tr>
                <th>模块层级</th>
                <th style="text-align: right">现有 UFP</th>
                <th style="text-align: right">分摊后 UFP</th>
                <th style="text-align: right">缺口 / 超出</th>
                <th style="text-align: right">占比</th>
              </tr>
            </thead>
            <tbody>
              <template
                v-for="sub in reverseResult!.module_allocation_tree"
                :key="sub.subsystem"
              >
                <tr class="tree-row-l0">
                  <td><b>{{ sub.subsystem }}</b></td>
                  <td class="mono" style="text-align: right">{{ sub.current_ufp.toFixed(2) }}</td>
                  <td class="mono" style="text-align: right">{{ sub.allocated_ufp.toFixed(2) }}</td>
                  <td
                    class="mono"
                    style="text-align: right"
                    :style="{ color: sub.delta_ufp >= 0 ? 'var(--green)' : 'var(--red)' }"
                  >{{ sub.delta_ufp >= 0 ? "+" : "" }}{{ sub.delta_ufp.toFixed(2) }}</td>
                  <td class="mono" style="text-align: right">{{ (sub.ratio * 100).toFixed(1) }}%</td>
                </tr>
                <template
                  v-for="l1 in sub.children"
                  :key="`${sub.subsystem}/${l1.l1_module}`"
                >
                  <tr class="tree-row-l1">
                    <td style="padding-left: 24px">{{ l1.l1_module }}</td>
                    <td class="mono" style="text-align: right">{{ l1.current_ufp.toFixed(2) }}</td>
                    <td class="mono" style="text-align: right">{{ l1.allocated_ufp.toFixed(2) }}</td>
                    <td
                      class="mono"
                      style="text-align: right"
                      :style="{ color: l1.delta_ufp >= 0 ? 'var(--green)' : 'var(--red)' }"
                    >{{ l1.delta_ufp >= 0 ? "+" : "" }}{{ l1.delta_ufp.toFixed(2) }}</td>
                    <td class="mono" style="text-align: right">{{ (l1.ratio * 100).toFixed(1) }}%</td>
                  </tr>
                  <tr
                    v-for="l2 in l1.children"
                    :key="`${sub.subsystem}/${l1.l1_module}/${l2.l2_module}`"
                    class="tree-row-l2"
                  >
                    <td style="padding-left: 48px" class="muted">{{ l2.l2_module }}</td>
                    <td class="mono" style="text-align: right">{{ l2.current_ufp.toFixed(2) }}</td>
                    <td class="mono" style="text-align: right; font-weight: 500">
                      {{ l2.allocated_ufp.toFixed(2) }}
                    </td>
                    <td
                      class="mono"
                      style="text-align: right"
                      :style="{ color: l2.delta_ufp >= 0 ? 'var(--green)' : 'var(--red)' }"
                    >{{ l2.delta_ufp >= 0 ? "+" : "" }}{{ l2.delta_ufp.toFixed(2) }}</td>
                    <td class="mono" style="text-align: right">{{ (l2.ratio * 100).toFixed(1) }}%</td>
                  </tr>
                </template>
              </template>
            </tbody>
          </table>
        </div>
```

在 `<style scoped>` 末尾加：

```css
.tree-row-l0 td {
  background: var(--color-bg-hover, #f8fafc);
  font-weight: 600;
}
.tree-row-l1 td {
  font-weight: 500;
}
.tree-row-l2 td {
  font-size: 12px;
}
```

- [ ] Step 4 跑测试确认通过：
```
cd web && npx vitest run src/__tests__/views/ResultView-module-tree.test.ts src/__tests__/views/ResultView.test.ts && npx vue-tsc --noEmit
```
预期 `ResultView-module-tree.test.ts` 2 passed；既有 `ResultView.test.ts` 不回归；vue-tsc 无错误。

- [ ] Step 5 提交：
```
git add web/src/api/calc.ts web/src/api/aiTasks.ts web/src/views/ResultView.vue web/src/__tests__/views/ResultView-module-tree.test.ts
git commit -m "feat(web): 反算结果页三级模块树 + 按反算补全 FP 按钮"
```

---

## Task E1: 最终验收 — 全套测试 + 类型检查 + 构建

**Files:** 无新增；仅运行验证。

- [ ] Step 1 后端全套 pytest：
```
cd server && .venv/bin/python -m pytest -q
```
预期：全部 passed，含本计划新增的 `test_ifpug.py` / `test_forward_dfp_efp.py` / `test_module_tree_allocation.py` / `test_v2_8_*.py`，且既有测试零回归。

- [ ] Step 2 前端全套 vitest：
```
cd web && npx vitest run
```
预期：全部 passed，含本计划新增的 `FpFormModal-ifpug.test.ts` / `ParamManager-global-draft.test.ts` / `ResultView-module-tree.test.ts` / `api/params.test.ts` 追加用例，且既有测试零回归。

- [ ] Step 3 前端类型检查：
```
cd web && npx vue-tsc --noEmit
```
预期：无类型错误。

- [ ] Step 4 前端生产构建：
```
cd web && npm run build
```
预期：构建成功，无错误。

- [ ] Step 5 若 Step 1-4 全绿，提交验收记录（仅当有未提交改动时）：
```
git add -A
git commit -m "chore: v2.8 验收 — pytest/vitest/vue-tsc/build 全绿" || echo "无待提交改动"
```

---

## 验收对照（spec 每一项）

- **A1 IFPUG 复杂度查表**：Task A1（列）+ A2（`core/ifpug.py`）+ A5（前端联动）。
- **A2 增强项目口径**：Task A1（`assessment_kind` 列、`modify_type` 迁移）+ A3（forward DFP/EFP）+ A4（calc 透传）。报告 IFPUG 计数声明：A3 的 `trace.fp_count_declaration`。
- **B1 修正数值**：Task B1（6 处修正 + 删 `软件集成`/`convert`）。
- **B2 补缺表**：Task B2（吻合度/软件类型/涉密因子 + 缺陷密度/工作量分布/功能点单价/运维占比 P10-P90 + 附录 C）。
- **B3 库迁移**：Task B3（`reseed_if_outdated`）。
- **C1 接通全局编辑**：Task C2（`patchOverride` 全局模式不再 return）。
- **C2 草稿态 + 三按钮**：Task C1（API 契约）+ C2（草稿缓冲 + 保存/撤销/还原）。
- **D1 三级树分摊**：Task D1（`build_module_tree`）。
- **D2 AI 补全 FP**：Task D2（`reverse_fill` 任务 + `cost-fill.md`）。
- **D3 前端树形 + 补全按钮**：Task D3。
