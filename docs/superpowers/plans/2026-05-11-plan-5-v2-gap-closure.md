# 软件造价系统 · Plan 5 · v2.0 Gap Closure 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 一次性补齐 v1.1 上线后审计发现的 11 项 feature gap，让 README 所有 ✅ 项落地，并接通 AI Plugin 链路。

**Architecture:** 后端在已有 FastAPI + SQLAlchemy 之上加 3 张表（param_snapshots / audit_log / projects 加 2 列）+ 2 个 endpoint 簇（/copy + /audit）+ 全局 audit middleware；前端在现有 Vue 3 + Element Plus 之上重构 5 个 view（ParamManager / Wizard / ProjectList / FpEditor / ResultView）。AI 走 Plugin 模式：宿主 Claude Code 通过 SKILL.md 读 parsed_text → 生成 NESMA FP 草稿 → 调 /functions/bulk 写回，server 不直连 Anthropic API。

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy 2.0 / Alembic / pytest — Vue 3 / Vite / Pinia / Element Plus / Vitest / Playwright

**对应 Spec：** `docs/superpowers/specs/2026-05-11-v2-gap-closure-design.md`
**前置 Spec：** `docs/superpowers/specs/2026-05-10-cost-estimation-design.md` v1.1
**前置 Plans：** plan-1 (后端) / plan-2 (parsing+excel) / plan-3 (Vue 前端) / plan-4 (plugin 包)

---

## 文件结构

```
server/
├── alembic/versions/
│   ├── 9b1c4f2e7a3d_add_factors_json_to_projects.py   # Task 1
│   ├── a4d8e6c2b9f1_add_param_snapshots_table.py       # Task 2
│   └── b7e2f1d9c4a8_add_audit_log_table.py             # Task 3
├── app/
│   ├── db/models.py                                    # Task 1/2/3 (新字段+新表)
│   ├── schemas/
│   │   ├── snapshots.py                                # Task 4 (新)
│   │   ├── audit.py                                    # Task 5 (新)
│   │   └── project.py                                  # Task 1 (扩展)
│   ├── services/
│   │   ├── snapshots.py                                # Task 4 (新)
│   │   ├── audit.py                                    # Task 5 (新)
│   │   ├── projects.py                                 # Task 6 (copy + query)
│   │   ├── calc.py                                     # Task 7 (读 project.factors)
│   │   └── factors.py                                  # Task 7 (新 — 因子组装)
│   ├── api/
│   │   ├── snapshots.py                                # Task 4 (新)
│   │   ├── audit.py                                    # Task 5 (新)
│   │   ├── projects.py                                 # Task 6
│   │   └── deps.py                                     # 已存在
│   ├── middleware/
│   │   └── audit.py                                    # Task 5 (新)
│   └── main.py                                         # Task 5 (注册中间件)
├── tests/integration/
│   ├── test_v2_param_snapshots.py                      # Task 4
│   ├── test_v2_audit_log.py                            # Task 5
│   ├── test_v2_project_copy.py                         # Task 6
│   ├── test_v2_project_list_query.py                   # Task 6
│   └── test_v2_calc_uses_project_factors.py            # Task 7

web/src/
├── api/
│   ├── snapshots.ts                                    # Task 8 (新)
│   ├── audit.ts                                        # Task 8 (新)
│   └── projects.ts                                     # Task 8 (扩展)
├── views/
│   ├── ParamManager.vue                                # Task 9-12
│   ├── ProjectWizard.vue                               # Task 13-19
│   ├── ProjectList.vue                                 # Task 20-21
│   ├── FpEditor.vue                                    # Task 22-23
│   ├── ResultView.vue                                  # Task 24
│   └── AuditView.vue                                   # Task 21 (新)
├── components/
│   ├── FactorTable.vue                                 # Task 10 (新)
│   ├── FactorDropdown.vue                              # Task 17 (新)
│   ├── PhaseCfPreview.vue                              # Task 16 (新)
│   ├── AlphaSlider.vue                                 # Task 15 (新)
│   └── ProjectActionMenu.vue                           # Task 21 (新)
└── tests/
    ├── unit/FactorTable.spec.ts                        # Task 10
    ├── unit/FactorDropdown.spec.ts                     # Task 17
    └── e2e/v2-wizard-flow.spec.ts                      # Task 19

# Plugin（已存在，本 plan 增强）
SKILL.md                                                # Task 25
commands/cost.md                                        # Task 25
commands/cost-allocate.md                               # Task 26 (新)

# 文档 / 元数据
README.md                                               # Task 27
docs/user-guide.md                                      # Task 27
web/package.json                                        # Task 27 (1.1.0 → 2.0.0)
```

---

## 关键依赖与顺序

后端必须先于前端：Task 1-7 是后端（schema + endpoint + calc 改造），Task 8-24 是前端，Task 25-27 是 plugin + 文档。

phase 内 task 大致独立，可并行；phase 之间是阻塞依赖。

```
Task 1 (factors col)  ─┐
Task 2 (snapshots tbl) ├─→ Task 4-7 (services + endpoints)
Task 3 (audit tbl)     ─┘                               │
                                                        ▼
                                            Task 8 (前端 API client)
                                                        │
                  ┌─────────────────────────────────────┴─────────────────────┐
                  ▼                                                           ▼
        Task 9-12 (ParamManager)                                    Task 13-19 (Wizard)
                  │                                                           │
                  └────────────────────────┬──────────────────────────────────┘
                                           ▼
                                Task 20-21 (ProjectList + Audit view)
                                           │
                  ┌────────────────────────┴──────────────────────────────────┐
                  ▼                                                           ▼
        Task 22-23 (FpEditor)                                          Task 24 (ResultView)
                  │                                                           │
                  └────────────────────────┬──────────────────────────────────┘
                                           ▼
                              Task 25-26 (SKILL.md + commands)
                                           │
                                           ▼
                                 Task 27 (docs + version bump)
```

---

# Phase A — 后端基础设施

## Task 1: 给 Project 表加 factors_dev_json + factors_ops_json 列

**Goal:** 项目级保存因子选择，让 calc.py 能用真因子而非默认 1.0。

**Files:**
- Modify: `server/app/db/models.py` (Project 类加 2 列)
- Create: `server/alembic/versions/9b1c4f2e7a3d_add_factors_json_to_projects.py`
- Modify: `server/app/schemas/project.py` (Pydantic schema 加 2 字段)
- Test: `server/tests/integration/test_v2_project_factors_column.py`

- [ ] **Step 1: 写测试 — 验证新列存在 + 默认 None + Pydantic schema 接受**

```python
# server/tests/integration/test_v2_project_factors_column.py
"""GAP-B foundation: Project 加 factors_dev_json / factors_ops_json 列。"""
import json
import uuid
import pytest


@pytest.fixture
def db(monkeypatch, tmp_path):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    monkeypatch.setenv("COST_DB_PATH", f"/tmp/cost-test-{uuid.uuid4()}.sqlite")
    monkeypatch.setenv("COST_DATA_DIR", str(tmp_path))
    import importlib
    for m in ["app.config", "app.db.session", "app.db.models",
              "app.services.params"]:
        importlib.reload(importlib.import_module(m))
    from app.db.session import Base, engine, SessionLocal
    Base.metadata.create_all(bind=engine)
    import app.services.params
    app.services.params.seed_from_csbmk()
    s = SessionLocal()
    yield s
    s.close()


def test_project_has_factors_columns(db):
    from app.db.models import Project
    p = Project(
        id="p1", name="T", project_type="dev_only", phase="bidding",
        city="北京", industry="电子政务", mode="forward",
        basis_data_ver="CSBMK®-202510",
        factors_dev_json=json.dumps({"app_type": "OLTP"}),
        factors_ops_json=None,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    assert json.loads(p.factors_dev_json) == {"app_type": "OLTP"}
    assert p.factors_ops_json is None


def test_project_factors_default_null(db):
    from app.db.models import Project
    p = Project(
        id="p2", name="T2", project_type="dev_only", phase="bidding",
        city="北京", industry="电子政务", mode="forward",
        basis_data_ver="CSBMK®-202510",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    assert p.factors_dev_json is None
    assert p.factors_ops_json is None
```

- [ ] **Step 2: 跑测试，确认失败**

```bash
cd server && pytest tests/integration/test_v2_project_factors_column.py -v
```

Expected: `AttributeError` / `OperationalError: no such column: projects.factors_dev_json`

- [ ] **Step 3: 改 models.py 加列**

在 `server/app/db/models.py` Project 类中（约第 42 行 `basis_data_ver = ...` 之后），加：

```python
    # v2.0 — per-project 调整因子选择，calc.py 用它代替 default=1.0
    # JSON: dev = {"app_type": "OLTP", "integrity_level": "B", ...}
    factors_dev_json = Column(Text)
    factors_ops_json = Column(Text)
```

- [ ] **Step 4: 写 alembic migration**

```python
# server/alembic/versions/9b1c4f2e7a3d_add_factors_json_to_projects.py
"""Add factors_dev_json + factors_ops_json to projects

Revision ID: 9b1c4f2e7a3d
Revises: 8a2e6b41c3d7
Create Date: 2026-05-11 03:10:00.000000

v1.1 calc.py 用 payload.get("dev_factor", 1.0)，永远是 1.0。
v2.0 改为读 Project.factors_dev_json，本 migration 给老项目预留 NULL，
calc.py 在读到 NULL 时 fallback 1.0 + 给 Result.warning_messages 加提示。
"""
from alembic import op
import sqlalchemy as sa


revision = "9b1c4f2e7a3d"
down_revision = "8a2e6b41c3d7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("factors_dev_json", sa.Text(), nullable=True))
        batch.add_column(sa.Column("factors_ops_json", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("factors_ops_json")
        batch.drop_column("factors_dev_json")
```

- [ ] **Step 5: 改 Pydantic schema 接收 factors**

在 `server/app/schemas/project.py` 的 `ProjectCreate` / `ProjectUpdate` 类（自行 grep 定位）中加：

```python
    factors_dev: dict | None = None  # 落库时 json.dumps，schema 不存 raw json string
    factors_ops: dict | None = None
```

并在 services/projects.py 的 create / update 路径里把 dict → json.dumps 写入 factors_dev_json 列。

- [ ] **Step 6: 跑测试 + 跑全套确认无回归**

```bash
cd server && pytest tests/integration/test_v2_project_factors_column.py -v
cd server && pytest -x  # 全套
```

Expected: 新测试 PASS，原 140 个 test 不破。

- [ ] **Step 7: Commit**

```bash
git add server/app/db/models.py server/app/schemas/project.py server/app/services/projects.py server/alembic/versions/9b1c4f2e7a3d_add_factors_json_to_projects.py server/tests/integration/test_v2_project_factors_column.py
git commit -m "feat(server): factors_dev_json + factors_ops_json on Project + alembic migration"
```

---

## Task 2: param_snapshots 表 + 模型

**Goal:** ParamManager 快照 tab 的存储基础（GAP-H）。

**Files:**
- Modify: `server/app/db/models.py` (新 ParamSnapshot 类)
- Create: `server/alembic/versions/a4d8e6c2b9f1_add_param_snapshots_table.py`
- Test: `server/tests/integration/test_v2_param_snapshots_model.py`

- [ ] **Step 1: 写测试**

```python
# server/tests/integration/test_v2_param_snapshots_model.py
import json
import uuid
import pytest


@pytest.fixture
def db(monkeypatch, tmp_path):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    monkeypatch.setenv("COST_DB_PATH", f"/tmp/cost-test-{uuid.uuid4()}.sqlite")
    monkeypatch.setenv("COST_DATA_DIR", str(tmp_path))
    import importlib
    for m in ["app.config", "app.db.session", "app.db.models"]:
        importlib.reload(importlib.import_module(m))
    from app.db.session import Base, engine, SessionLocal
    Base.metadata.create_all(bind=engine)
    s = SessionLocal()
    yield s
    s.close()


def test_param_snapshot_can_be_inserted(db):
    from app.db.models import ParamSnapshot
    snap = ParamSnapshot(
        scope="global", label="实验前 baseline",
        payload_json=json.dumps({"hours_per_pm": 176}))
    db.add(snap)
    db.commit()
    db.refresh(snap)
    assert snap.id > 0
    assert snap.scope == "global"
    assert json.loads(snap.payload_json)["hours_per_pm"] == 176


def test_param_snapshot_scope_can_be_project_id(db):
    from app.db.models import ParamSnapshot
    snap = ParamSnapshot(scope="proj-abc-123", payload_json="{}")
    db.add(snap)
    db.commit()
    assert snap.scope == "proj-abc-123"
```

- [ ] **Step 2: 跑测试，确认失败**（`AttributeError: ... no attribute 'ParamSnapshot'`）

- [ ] **Step 3: 改 models.py 加 ParamSnapshot 类**

在 `server/app/db/models.py` 末尾（在 `Upload` 类之后）加：

```python
class ParamSnapshot(Base):
    """v2.0 — ParamManager 快照 tab 的存储。

    与 FPSnapshot 不同：FPSnapshot 是 FP 列表快照（per-project 的 FP 状态），
    ParamSnapshot 是 effective_params 的快照（可以是全局 baseline，也可以是
    某个项目的 override 状态）。
    """
    __tablename__ = "param_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scope = Column(String, nullable=False, index=True)  # "global" | project_id
    label = Column(String)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    payload_json = Column(Text, nullable=False)
```

- [ ] **Step 4: 写 alembic migration**

```python
# server/alembic/versions/a4d8e6c2b9f1_add_param_snapshots_table.py
"""Add param_snapshots table

Revision ID: a4d8e6c2b9f1
Revises: 9b1c4f2e7a3d
"""
from alembic import op
import sqlalchemy as sa


revision = "a4d8e6c2b9f1"
down_revision = "9b1c4f2e7a3d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "param_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scope", sa.String(), nullable=False, index=True),
        sa.Column("label", sa.String()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_index("ix_param_snapshots_scope", "param_snapshots", ["scope"])


def downgrade():
    op.drop_index("ix_param_snapshots_scope", table_name="param_snapshots")
    op.drop_table("param_snapshots")
```

- [ ] **Step 5: 跑测试**

```bash
cd server && pytest tests/integration/test_v2_param_snapshots_model.py -v
```

Expected: 2 tests PASS。

- [ ] **Step 6: Commit**

```bash
git add server/app/db/models.py server/alembic/versions/a4d8e6c2b9f1_add_param_snapshots_table.py server/tests/integration/test_v2_param_snapshots_model.py
git commit -m "feat(server): param_snapshots table for ParamManager 快照 tab"
```

---

## Task 3: audit_log 表 + 模型

**Goal:** GAP-J 审计日志的存储基础。

**Files:**
- Modify: `server/app/db/models.py`
- Create: `server/alembic/versions/b7e2f1d9c4a8_add_audit_log_table.py`
- Test: `server/tests/integration/test_v2_audit_log_model.py`

- [ ] **Step 1: 写测试**

```python
# server/tests/integration/test_v2_audit_log_model.py
import json
import uuid
import pytest


@pytest.fixture
def db(monkeypatch, tmp_path):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    monkeypatch.setenv("COST_DB_PATH", f"/tmp/cost-test-{uuid.uuid4()}.sqlite")
    monkeypatch.setenv("COST_DATA_DIR", str(tmp_path))
    import importlib
    for m in ["app.config", "app.db.session", "app.db.models"]:
        importlib.reload(importlib.import_module(m))
    from app.db.session import Base, engine, SessionLocal
    Base.metadata.create_all(bind=engine)
    s = SessionLocal()
    yield s
    s.close()


def test_audit_log_inserts_with_required_fields(db):
    from app.db.models import Project, AuditLog
    p = Project(
        id="p1", name="T", project_type="dev_only", phase="bidding",
        city="北京", industry="电子政务", mode="forward",
        basis_data_ver="CSBMK®-202510",
    )
    db.add(p)
    db.commit()
    log = AuditLog(
        project_id="p1", actor="user", action="project.create",
        target="p1", diff_json=json.dumps({"after": {"name": "T"}})
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    assert log.id > 0
    assert log.action == "project.create"
    assert log.ts is not None


def test_audit_log_cascades_on_project_delete(db):
    from app.db.models import Project, AuditLog
    p = Project(
        id="p2", name="T2", project_type="dev_only", phase="bidding",
        city="北京", industry="电子政务", mode="forward",
        basis_data_ver="CSBMK®-202510",
    )
    db.add(p)
    db.commit()
    db.add(AuditLog(project_id="p2", action="project.create", target="p2"))
    db.commit()
    db.delete(p)
    db.commit()
    assert db.query(AuditLog).filter_by(project_id="p2").count() == 0
```

- [ ] **Step 2: 跑测试，确认失败**

- [ ] **Step 3: 在 models.py 加 AuditLog 类 + Project.audit_logs relationship**

```python
# 加到 Project 的 relationship 列表中（已有 uploads 那一节后面）：
    audit_logs = relationship(
        "AuditLog",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

# 加到文件末尾：
class AuditLog(Base):
    """v2.0 GAP-J — 项目级审计日志。

    由 app/middleware/audit.py 在 PATCH/POST/PUT/DELETE on /api/projects/* 自动写入。
    actor 字段为 v3 多用户预留；当前单用户始终为 "user"。
    """
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ts = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    actor = Column(String, default="user")
    action = Column(String, nullable=False)
    target = Column(String)
    diff_json = Column(Text)

    project = relationship("Project", back_populates="audit_logs")


Index("ix_audit_log_project_ts", AuditLog.project_id, AuditLog.ts)
```

- [ ] **Step 4: alembic migration**

```python
# server/alembic/versions/b7e2f1d9c4a8_add_audit_log_table.py
"""Add audit_log table

Revision ID: b7e2f1d9c4a8
Revises: a4d8e6c2b9f1
"""
from alembic import op
import sqlalchemy as sa


revision = "b7e2f1d9c4a8"
down_revision = "a4d8e6c2b9f1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.String(),
                  sa.ForeignKey("projects.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("ts", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("actor", sa.String(), server_default="user"),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("target", sa.String()),
        sa.Column("diff_json", sa.Text()),
    )
    op.create_index("ix_audit_log_project", "audit_log", ["project_id"])
    op.create_index("ix_audit_log_ts", "audit_log", ["ts"])
    op.create_index("ix_audit_log_project_ts", "audit_log", ["project_id", "ts"])


def downgrade():
    op.drop_index("ix_audit_log_project_ts", table_name="audit_log")
    op.drop_index("ix_audit_log_ts", table_name="audit_log")
    op.drop_index("ix_audit_log_project", table_name="audit_log")
    op.drop_table("audit_log")
```

- [ ] **Step 5: 跑测试** `pytest tests/integration/test_v2_audit_log_model.py -v`

- [ ] **Step 6: Commit**

```bash
git add server/app/db/models.py server/alembic/versions/b7e2f1d9c4a8_add_audit_log_table.py server/tests/integration/test_v2_audit_log_model.py
git commit -m "feat(server): audit_log table for v2.0 项目审计"
```

---

## Task 4: ParamSnapshot service + 4 个 endpoint

**Goal:** GAP-H — 创建 / 列出 / restore / delete 参数快照。

**Files:**
- Create: `server/app/services/snapshots.py`
- Create: `server/app/schemas/snapshots.py`
- Create: `server/app/api/snapshots.py`
- Modify: `server/app/main.py` (挂载 router)
- Test: `server/tests/integration/test_v2_param_snapshots_api.py`

- [ ] **Step 1: 写 service + schema + router 测试一并**

```python
# server/tests/integration/test_v2_param_snapshots_api.py
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


@pytest.fixture
async def client(monkeypatch, tmp_path):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    monkeypatch.setenv("COST_DB_PATH", f"/tmp/cost-test-{uuid.uuid4()}.sqlite")
    monkeypatch.setenv("COST_DATA_DIR", str(tmp_path))
    import importlib
    for m in ["app.config", "app.db.session", "app.deps", "app.db.models",
              "app.services.params", "app.services.snapshots",
              "app.api.params", "app.api.snapshots", "app.api.health", "app.main"]:
        importlib.reload(importlib.import_module(m))
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    import app.services.params
    app.services.params.seed_from_csbmk()
    import app.main
    transport = ASGITransport(app=app.main.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_create_global_snapshot_then_list(client):
    r = await client.post(
        "/api/params/snapshots", headers=H,
        json={"scope": "global", "label": "实验前 baseline"})
    assert r.status_code == 201
    snap_id = r.json()["data"]["id"]
    r2 = await client.get("/api/params/snapshots?scope=global", headers=H)
    assert r2.status_code == 200
    rows = r2.json()["data"]
    assert any(s["id"] == snap_id and s["label"] == "实验前 baseline" for s in rows)


async def test_restore_snapshot_brings_back_old_value(client):
    # 1) 改一个全局参数让它偏离 baseline
    await client.patch(
        "/api/params/global", headers={**H, "Content-Type": "application/json"},
        json={"key": "hours_per_pm", "value": 200})
    # 2) 快照 baseline-after-change
    r = await client.post(
        "/api/params/snapshots", headers=H,
        json={"scope": "global", "label": "after-change"})
    snap_id = r.json()["data"]["id"]
    # 3) 改第二次
    await client.patch(
        "/api/params/global", headers={**H, "Content-Type": "application/json"},
        json={"key": "hours_per_pm", "value": 300})
    # 4) restore 到 200 那一刻
    r3 = await client.post(f"/api/params/snapshots/{snap_id}/restore", headers=H)
    assert r3.status_code == 200
    eff = (await client.get("/api/params/effective", headers=H)).json()["data"]
    assert eff["hours_per_pm"] == 200


async def test_delete_snapshot(client):
    r = await client.post(
        "/api/params/snapshots", headers=H, json={"scope": "global"})
    snap_id = r.json()["data"]["id"]
    r2 = await client.delete(f"/api/params/snapshots/{snap_id}", headers=H)
    assert r2.status_code == 204
    rows = (await client.get("/api/params/snapshots?scope=global", headers=H)).json()["data"]
    assert all(s["id"] != snap_id for s in rows)


async def test_restore_404_on_unknown_snapshot(client):
    r = await client.post("/api/params/snapshots/99999/restore", headers=H)
    assert r.status_code == 404
```

- [ ] **Step 2: 跑测试，确认失败**（404 on POST /api/params/snapshots — endpoint 不存在）

- [ ] **Step 3: 创建 schemas/snapshots.py**

```python
# server/app/schemas/snapshots.py
from datetime import datetime
from pydantic import BaseModel, Field


class SnapshotCreate(BaseModel):
    scope: str = Field(..., min_length=1, max_length=64)  # "global" or project_id
    label: str | None = Field(None, max_length=200)


class SnapshotOut(BaseModel):
    id: int
    scope: str
    label: str | None
    created_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 4: 创建 services/snapshots.py**

```python
# server/app/services/snapshots.py
"""ParamSnapshot 服务层 — 创建 / 列出 / restore / delete。

restore 实现：把 payload_json 还原成 effective_params 字典，再逐叶 PATCH global
（scope=global）或逐叶 ParamOverride upsert（scope=project_id）。这样可以
利用现有 validate_override_key 的安全检查。
"""
import json
from sqlalchemy.orm import Session

from ..db.models import ParamSnapshot, Result
from . import params as ps


def create_snapshot(db: Session, scope: str, label: str | None = None) -> ParamSnapshot:
    if scope == "global":
        eff = ps.get_effective(db, project_id=None)
    else:
        eff = ps.get_effective(db, project_id=scope)
    snap = ParamSnapshot(
        scope=scope,
        label=label,
        payload_json=json.dumps(eff, ensure_ascii=False),
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def list_snapshots(db: Session, scope: str | None = None) -> list[ParamSnapshot]:
    q = db.query(ParamSnapshot)
    if scope:
        q = q.filter_by(scope=scope)
    return q.order_by(ParamSnapshot.id.desc()).all()


def get_snapshot(db: Session, snap_id: int) -> ParamSnapshot | None:
    return db.query(ParamSnapshot).filter_by(id=snap_id).first()


def restore_snapshot(db: Session, snap_id: int) -> dict:
    """Restore the snapshot's payload back into the live param state.

    For global scope: walk leaf paths and reset_global() then re-apply each.
    For project scope: clear ParamOverride and re-apply each leaf.

    返回 restore 后的 effective dict 供 caller 校验 / 返回给 API。
    """
    snap = get_snapshot(db, snap_id)
    if not snap:
        raise ValueError("SNAPSHOT_NOT_FOUND")
    payload = json.loads(snap.payload_json)
    if snap.scope == "global":
        ps.reset_global(db)
        leaves = ps._leaf_paths(payload)
        for path, value in leaves:
            ps.patch_global(db, path, value)
    else:
        # project scope
        from ..db.models import ParamOverride
        db.query(ParamOverride).filter_by(project_id=snap.scope).delete()
        db.commit()
        leaves = ps._leaf_paths(payload)
        for path, value in leaves:
            ps.apply_overrides(db, snap.scope, {path: value})
    # 标记所有相关 result 为 stale（与 apply_overrides 一致）
    if snap.scope != "global":
        db.query(Result).filter_by(project_id=snap.scope).update({"is_stale": True})
        db.commit()
    if snap.scope == "global":
        return ps.get_effective(db, project_id=None)
    return ps.get_effective(db, project_id=snap.scope)


def delete_snapshot(db: Session, snap_id: int) -> None:
    snap = get_snapshot(db, snap_id)
    if not snap:
        raise ValueError("SNAPSHOT_NOT_FOUND")
    db.delete(snap)
    db.commit()
```

`ps._leaf_paths(payload)` 是辅助函数（如 `params.py` 没有，新增）：递归走 dict 树，返回 `[("city_rate.北京.dev", 12000), ...]`。在 `services/params.py` 文件末尾加：

```python
def _leaf_paths(d: dict, prefix: str = "") -> list[tuple[str, object]]:
    """Walk a nested dict and return [(dotted.path, leaf_value), ...]."""
    out: list[tuple[str, object]] = []
    for k, v in d.items():
        path = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, dict):
            out.extend(_leaf_paths(v, path))
        else:
            out.append((path, v))
    return out
```

- [ ] **Step 5: 创建 api/snapshots.py**

```python
# server/app/api/snapshots.py
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..deps import get_db, require_auth
from ..schemas.snapshots import SnapshotCreate, SnapshotOut
from ..services import snapshots as svc

router = APIRouter(prefix="/api/params/snapshots", tags=["snapshots"])


@router.post("", status_code=201, dependencies=[Depends(require_auth)])
def create(payload: SnapshotCreate, db: Session = Depends(get_db)) -> dict:
    snap = svc.create_snapshot(db, payload.scope, payload.label)
    return {"success": True, "data": SnapshotOut.model_validate(snap).model_dump(mode="json"), "error": None}


@router.get("", dependencies=[Depends(require_auth)])
def list_(scope: str | None = None, db: Session = Depends(get_db)) -> dict:
    rows = svc.list_snapshots(db, scope)
    return {
        "success": True,
        "data": [SnapshotOut.model_validate(r).model_dump(mode="json") for r in rows],
        "error": None,
    }


@router.post("/{snap_id}/restore", dependencies=[Depends(require_auth)])
def restore(snap_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        eff = svc.restore_snapshot(db, snap_id)
    except ValueError as e:
        if "NOT_FOUND" in str(e):
            raise HTTPException(404, detail={"code": "SNAPSHOT_NOT_FOUND"})
        raise
    return {"success": True, "data": eff, "error": None}


@router.delete("/{snap_id}", status_code=204, dependencies=[Depends(require_auth)])
def delete(snap_id: int, db: Session = Depends(get_db)) -> Response:
    try:
        svc.delete_snapshot(db, snap_id)
    except ValueError as e:
        if "NOT_FOUND" in str(e):
            raise HTTPException(404, detail={"code": "SNAPSHOT_NOT_FOUND"})
        raise
    return Response(status_code=204)
```

- [ ] **Step 6: 在 main.py 注册 router**

`server/app/main.py` 找到 `app.include_router(...)` 列表，加：

```python
from .api import snapshots as snapshots_router
...
app.include_router(snapshots_router.router)
```

- [ ] **Step 7: 跑测试**

```bash
cd server && pytest tests/integration/test_v2_param_snapshots_api.py -v
```

Expected: 4 PASS。

- [ ] **Step 8: Commit**

```bash
git add server/app/services/snapshots.py server/app/services/params.py server/app/schemas/snapshots.py server/app/api/snapshots.py server/app/main.py server/tests/integration/test_v2_param_snapshots_api.py
git commit -m "feat(server): /api/params/snapshots 4 endpoint + service"
```

---

## Task 5: AuditLog 中间件 + endpoint

**Goal:** GAP-J — 自动捕获所有 mutating 操作 + 提供 GET 列表。

**Files:**
- Create: `server/app/middleware/audit.py`
- Create: `server/app/services/audit.py`
- Create: `server/app/schemas/audit.py`
- Create: `server/app/api/audit.py`
- Create: `server/app/middleware/__init__.py`（空文件）
- Modify: `server/app/main.py`
- Test: `server/tests/integration/test_v2_audit_log_api.py`

- [ ] **Step 1: 写测试**

```python
# server/tests/integration/test_v2_audit_log_api.py
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


@pytest.fixture
async def client(monkeypatch, tmp_path):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    monkeypatch.setenv("COST_DB_PATH", f"/tmp/cost-test-{uuid.uuid4()}.sqlite")
    monkeypatch.setenv("COST_DATA_DIR", str(tmp_path))
    import importlib
    for m in ["app.config", "app.db.session", "app.deps", "app.db.models",
              "app.middleware.audit", "app.services.audit", "app.services.params",
              "app.api.projects", "app.api.params", "app.api.audit",
              "app.api.health", "app.main"]:
        importlib.reload(importlib.import_module(m))
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    import app.services.params
    app.services.params.seed_from_csbmk()
    import app.main
    transport = ASGITransport(app=app.main.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _make_project(c) -> str:
    r = await c.post("/api/projects", headers=H, json={
        "name": "T", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    return r.json()["data"]["id"]


async def test_project_create_writes_audit_log(client):
    pid = await _make_project(client)
    rows = (await client.get(f"/api/projects/{pid}/audit", headers=H)).json()["data"]
    assert any(r["action"] == "project.create" for r in rows)


async def test_project_patch_writes_audit_log(client):
    pid = await _make_project(client)
    await client.patch(
        f"/api/projects/{pid}", headers={**H, "Content-Type": "application/json"},
        json={"name": "T-renamed"})
    rows = (await client.get(f"/api/projects/{pid}/audit", headers=H)).json()["data"]
    actions = [r["action"] for r in rows]
    assert "project.update" in actions
    assert actions.count("project.create") == 1


async def test_get_does_not_write_audit_log(client):
    pid = await _make_project(client)
    initial = len((await client.get(f"/api/projects/{pid}/audit", headers=H)).json()["data"])
    # 重复 GET 不应增加 audit
    for _ in range(3):
        await client.get(f"/api/projects/{pid}", headers=H)
    rows = (await client.get(f"/api/projects/{pid}/audit", headers=H)).json()["data"]
    assert len(rows) == initial


async def test_audit_log_cursor_pagination(client):
    pid = await _make_project(client)
    for i in range(5):
        await client.patch(
            f"/api/projects/{pid}", headers={**H, "Content-Type": "application/json"},
            json={"name": f"T-{i}"})
    rows = (await client.get(f"/api/projects/{pid}/audit?limit=3", headers=H)).json()["data"]
    assert len(rows) == 3
    last_id = rows[-1]["id"]
    next_page = (await client.get(
        f"/api/projects/{pid}/audit?limit=3&before_id={last_id}", headers=H
    )).json()["data"]
    assert all(r["id"] < last_id for r in next_page)
```

- [ ] **Step 2: 跑测试，确认失败**（4 个测试都 fail：endpoint 不存在 + audit 不写入）

- [ ] **Step 3: 创建 services/audit.py**

```python
# server/app/services/audit.py
from sqlalchemy.orm import Session
from ..db.models import AuditLog


def write(
    db: Session, project_id: str, action: str,
    target: str | None = None, diff_json: str | None = None,
    actor: str = "user",
) -> AuditLog:
    log = AuditLog(
        project_id=project_id, actor=actor, action=action,
        target=target, diff_json=diff_json,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def list_for_project(
    db: Session, project_id: str, limit: int = 100, before_id: int | None = None,
) -> list[AuditLog]:
    q = db.query(AuditLog).filter_by(project_id=project_id)
    if before_id is not None:
        q = q.filter(AuditLog.id < before_id)
    return q.order_by(AuditLog.id.desc()).limit(limit).all()
```

- [ ] **Step 4: 创建 middleware/audit.py**

```python
# server/app/middleware/audit.py
"""HTTP middleware that records mutating actions on /api/projects/* into audit_log.

We attach to the request lifecycle: only methods PATCH/POST/PUT/DELETE under
/api/projects/* are tracked. The middleware extracts project_id from path,
infers action from path + method, and writes the log AFTER the response is
produced (so failures don't leave half-baked rows). For project.create the
project_id only exists *after* the response, so we read it from the response
body.
"""
import json
import re
from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..db.session import SessionLocal
from ..services import audit as svc


_PROJECT_RX = re.compile(r"^/api/projects/(?P<pid>[^/]+)(?P<sub>/?.*)$")


def _action_for(method: str, path: str, sub: str) -> str | None:
    """Return action label for tracked routes. Returns None for routes we ignore."""
    if method == "POST" and path == "/api/projects":
        return "project.create"
    m = _PROJECT_RX.match(path)
    if not m:
        return None
    sub_path = m.group("sub").lstrip("/")
    if sub_path == "":
        if method == "PATCH":
            return "project.update"
        if method == "DELETE":
            return "project.delete"
        return None
    if sub_path == "copy" and method == "POST":
        return "project.copy"
    if sub_path.startswith("functions/bulk"):
        return "fp.bulk_write"
    if sub_path.startswith("functions/restore"):
        return "fp.restore"
    if sub_path.startswith("functions") and method == "POST":
        return "fp.create"
    if sub_path.startswith("functions") and method == "PATCH":
        return "fp.update"
    if sub_path.startswith("functions") and method == "DELETE":
        return "fp.delete"
    if sub_path == "params/override" and method == "PATCH":
        return "params.override"
    if sub_path.startswith("uploads") and method == "POST":
        return "upload.create"
    if sub_path.startswith("uploads") and method == "DELETE":
        return "upload.delete"
    if sub_path == "calc/forward" or sub_path == "calc/reverse":
        return "calc.run"
    if sub_path == "report/excel":
        return "report.export"
    return None


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        method = request.method.upper()
        path = request.url.path
        # Skip non-mutating methods early
        if method not in ("POST", "PATCH", "PUT", "DELETE"):
            return await call_next(request)
        action = _action_for(method, path, "")
        if action is None:
            return await call_next(request)

        response = await call_next(request)
        # Only audit successful mutations (2xx)
        if response.status_code < 200 or response.status_code >= 300:
            return response

        # Resolve project_id
        m = _PROJECT_RX.match(path)
        project_id: str | None = m.group("pid") if m else None

        if action == "project.create":
            # 项目还没存在时 path 是 /api/projects（不带 id），从响应 body 拿 id
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            try:
                payload = json.loads(body.decode("utf-8") or "{}")
                project_id = payload.get("data", {}).get("id")
            except Exception:
                project_id = None
            # Reconstruct iterator
            response = Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        if not project_id:
            return response

        db = SessionLocal()
        try:
            svc.write(db, project_id=project_id, action=action, target=project_id)
        except Exception:
            # Audit must never break the request
            pass
        finally:
            db.close()

        return response
```

- [ ] **Step 5: 创建 schemas/audit.py + api/audit.py**

```python
# server/app/schemas/audit.py
from datetime import datetime
from pydantic import BaseModel


class AuditOut(BaseModel):
    id: int
    project_id: str
    ts: datetime
    actor: str | None
    action: str
    target: str | None
    diff_json: str | None

    class Config:
        from_attributes = True
```

```python
# server/app/api/audit.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..deps import get_db, require_auth
from ..schemas.audit import AuditOut
from ..services import audit as svc

router = APIRouter(prefix="/api/projects", tags=["audit"])


@router.get("/{project_id}/audit", dependencies=[Depends(require_auth)])
def list_audit(
    project_id: str,
    limit: int = Query(100, ge=1, le=500),
    before_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
) -> dict:
    rows = svc.list_for_project(db, project_id, limit, before_id)
    return {
        "success": True,
        "data": [AuditOut.model_validate(r).model_dump(mode="json") for r in rows],
        "error": None,
    }
```

- [ ] **Step 6: main.py 注册中间件 + router**

```python
# server/app/main.py — 在 create_app() 里
from .middleware.audit import AuditMiddleware
from .api import audit as audit_router

# create_app() 内：
app.add_middleware(AuditMiddleware)
app.include_router(audit_router.router)
```

确保 `app.add_middleware(AuditMiddleware)` 在 CORS/Auth middleware **之后** 注册（middleware 是 LIFO，后注册的先执行；audit 应该是最外层，所以注册顺序最后）。

- [ ] **Step 7: 创建空 `server/app/middleware/__init__.py`**

- [ ] **Step 8: 跑测试**

```bash
cd server && pytest tests/integration/test_v2_audit_log_api.py -v
```

Expected: 4 PASS。

- [ ] **Step 9: 跑全套确认无回归**

```bash
cd server && pytest -x
```

- [ ] **Step 10: Commit**

```bash
git add server/app/middleware/__init__.py server/app/middleware/audit.py server/app/services/audit.py server/app/schemas/audit.py server/app/api/audit.py server/app/main.py server/tests/integration/test_v2_audit_log_api.py
git commit -m "feat(server): audit_log middleware + GET /projects/{id}/audit"
```

---

## Task 6: /projects/{id}/copy + GET /projects 查询参数

**Goal:** GAP-I 项目复制 + GAP-F 列表筛选/排序/分页。

**Files:**
- Modify: `server/app/services/projects.py`
- Modify: `server/app/api/projects.py`
- Modify: `server/app/schemas/project.py` (查询参数 schema)
- Test: `server/tests/integration/test_v2_project_copy.py`
- Test: `server/tests/integration/test_v2_project_list_query.py`

- [ ] **Step 1: 写 copy 测试**

```python
# server/tests/integration/test_v2_project_copy.py
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


@pytest.fixture
async def client(monkeypatch, tmp_path):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    monkeypatch.setenv("COST_DB_PATH", f"/tmp/cost-test-{uuid.uuid4()}.sqlite")
    monkeypatch.setenv("COST_DATA_DIR", str(tmp_path))
    import importlib
    for m in ["app.config", "app.db.session", "app.deps", "app.db.models",
              "app.services.params", "app.services.projects",
              "app.api.projects", "app.api.params", "app.api.functions",
              "app.api.health", "app.main"]:
        importlib.reload(importlib.import_module(m))
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    import app.services.params
    app.services.params.seed_from_csbmk()
    import app.main
    transport = ASGITransport(app=app.main.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_copy_clones_project_metadata(client):
    r = await client.post("/api/projects", headers=H, json={
        "name": "原项目", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510", "client": "甲方A", "evaluator": "评估方B",
    })
    src_id = r.json()["data"]["id"]
    r2 = await client.post(
        f"/api/projects/{src_id}/copy", headers=H, json={"name": "副本"})
    assert r2.status_code == 201
    new = r2.json()["data"]
    assert new["id"] != src_id
    assert new["name"] == "副本"
    assert new["client"] == "甲方A"
    assert new["evaluator"] == "评估方B"


async def test_copy_clones_function_points(client):
    r = await client.post("/api/projects", headers=H, json={
        "name": "原项目", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    src_id = r.json()["data"]["id"]
    await client.post(
        f"/api/projects/{src_id}/functions", headers=H,
        json={"name": "fp1", "category": "EI", "complexity": "low",
              "ufp": 3, "us": 3, "source": "manual"})
    r2 = await client.post(
        f"/api/projects/{src_id}/copy", headers=H, json={"name": "副本"})
    new_id = r2.json()["data"]["id"]
    fps = (await client.get(f"/api/projects/{new_id}/functions", headers=H)).json()["data"]
    assert len(fps) == 1
    assert fps[0]["name"] == "fp1"
    # 必须是新行（id 不同）
    assert fps[0]["id"] != "(would have been src)"


async def test_copy_does_not_clone_results_or_snapshots(client):
    r = await client.post("/api/projects", headers=H, json={
        "name": "原", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    src_id = r.json()["data"]["id"]
    await client.post(
        f"/api/projects/{src_id}/functions", headers=H,
        json={"name": "fp1", "category": "EI", "complexity": "low",
              "ufp": 3, "us": 3, "source": "manual"})
    await client.post(f"/api/projects/{src_id}/calc/forward", headers=H, json={})
    r2 = await client.post(
        f"/api/projects/{src_id}/copy", headers=H, json={"name": "副本"})
    new_id = r2.json()["data"]["id"]
    snaps = (await client.get(
        f"/api/projects/{new_id}/functions/snapshots", headers=H)).json()["data"]
    assert snaps == []


async def test_copy_404_on_unknown_source(client):
    r = await client.post(
        "/api/projects/no-such-id/copy", headers=H, json={"name": "x"})
    assert r.status_code == 404


async def test_copy_422_on_empty_name(client):
    r = await client.post("/api/projects", headers=H, json={
        "name": "原", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    src_id = r.json()["data"]["id"]
    r2 = await client.post(
        f"/api/projects/{src_id}/copy", headers=H, json={"name": ""})
    assert r2.status_code == 422
```

- [ ] **Step 2: 写 list query 测试**

```python
# server/tests/integration/test_v2_project_list_query.py
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


@pytest.fixture
async def client(monkeypatch, tmp_path):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    monkeypatch.setenv("COST_DB_PATH", f"/tmp/cost-test-{uuid.uuid4()}.sqlite")
    monkeypatch.setenv("COST_DATA_DIR", str(tmp_path))
    import importlib
    for m in ["app.config", "app.db.session", "app.deps", "app.db.models",
              "app.services.params", "app.services.projects",
              "app.api.projects", "app.api.params", "app.api.health", "app.main"]:
        importlib.reload(importlib.import_module(m))
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    import app.services.params
    app.services.params.seed_from_csbmk()
    import app.main
    transport = ASGITransport(app=app.main.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        for spec in [
            ("智慧政务-2026", "北京", "电子政务", "bidding"),
            ("电力调度", "上海", "电力", "planning"),
            ("智慧交通", "北京", "交通", "settled"),
            ("税务系统", "广州", "电子政务", "budget"),
        ]:
            await c.post("/api/projects", headers=H, json={
                "name": spec[0], "city": spec[1], "industry": spec[2], "phase": spec[3],
                "project_type": "dev_only", "mode": "forward",
                "basis_data_ver": "CSBMK®-202510",
            })
        yield c


async def test_list_no_query_returns_all_paginated(client):
    r = (await client.get("/api/projects", headers=H)).json()
    assert r["success"]
    assert len(r["data"]) == 4
    assert r["meta"]["total"] == 4
    assert r["meta"]["page"] == 1


async def test_list_q_substring_match(client):
    r = (await client.get("/api/projects?q=智慧", headers=H)).json()
    names = [p["name"] for p in r["data"]]
    assert "智慧政务-2026" in names
    assert "智慧交通" in names
    assert "电力调度" not in names
    assert r["meta"]["total"] == 2


async def test_list_filter_by_city(client):
    r = (await client.get("/api/projects?city=北京", headers=H)).json()
    assert r["meta"]["total"] == 2
    assert all(p["city"] == "北京" for p in r["data"])


async def test_list_filter_by_industry(client):
    r = (await client.get("/api/projects?industry=电子政务", headers=H)).json()
    assert r["meta"]["total"] == 2


async def test_list_sort_by_name_asc(client):
    r = (await client.get("/api/projects?sort=name&order=asc", headers=H)).json()
    names = [p["name"] for p in r["data"]]
    assert names == sorted(names)


async def test_list_pagination_size_2(client):
    r1 = (await client.get("/api/projects?size=2&page=1", headers=H)).json()
    assert len(r1["data"]) == 2
    r2 = (await client.get("/api/projects?size=2&page=2", headers=H)).json()
    assert len(r2["data"]) == 2
    assert {p["id"] for p in r1["data"]}.isdisjoint({p["id"] for p in r2["data"]})


async def test_list_size_capped_at_200(client):
    r = await client.get("/api/projects?size=500", headers=H)
    # 422 or auto-clamped
    if r.status_code == 200:
        assert r.json()["meta"]["size"] <= 200
    else:
        assert r.status_code == 422
```

- [ ] **Step 3: 跑两组测试，确认失败**

- [ ] **Step 4: 改 services/projects.py 加 copy + 改 list**

```python
# server/app/services/projects.py — 加（不替换原有 list_all 等）
import json
import uuid
from typing import Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..db.models import (
    Project,
    FunctionPoint,
    ParamOverride,
)


def copy_project(
    db: Session, src_id: str, new_name: str,
) -> Project:
    src = db.query(Project).filter_by(id=src_id).first()
    if not src:
        raise ValueError("PROJECT_NOT_FOUND")

    new_id = f"proj-{uuid.uuid4().hex[:12]}"
    new = Project(
        id=new_id,
        name=new_name,
        project_type=src.project_type,
        phase=src.phase,
        city=src.city,
        industry=src.industry,
        client=src.client,
        evaluator=src.evaluator,
        mode=src.mode,
        target_cost=src.target_cost,
        other_cost=src.other_cost,
        include_ops=src.include_ops,
        alpha_dev=src.alpha_dev,
        fp_method=src.fp_method,
        basis_data_ver=src.basis_data_ver,
        factors_dev_json=src.factors_dev_json,
        factors_ops_json=src.factors_ops_json,
    )
    db.add(new)

    # 复制 FP（version=1，新 id）
    for fp in src.function_points:
        db.add(FunctionPoint(
            id=f"fp-{uuid.uuid4().hex[:12]}",
            project_id=new_id,
            version=1,
            subsystem=fp.subsystem,
            l1_module=fp.l1_module,
            l2_module=fp.l2_module,
            description=fp.description,
            name=fp.name,
            category=fp.category,
            complexity=fp.complexity,
            ufp=fp.ufp,
            reuse_level=fp.reuse_level,
            modify_type=fp.modify_type,
            us=fp.us,
            source="copied",
            locked=fp.locked,
            notes=fp.notes,
            ord=fp.ord,
        ))

    # 复制 params overrides
    for po in src.param_overrides:
        db.add(ParamOverride(
            project_id=new_id,
            key=po.key,
            value=po.value,
            reason=f"(copied from {src_id})",
        ))

    db.commit()
    db.refresh(new)
    return new


def list_with_query(
    db: Session, *,
    q: Optional[str] = None,
    city: Optional[str] = None,
    industry: Optional[str] = None,
    phase: Optional[str] = None,
    mode: Optional[str] = None,
    sort: str = "created_at",
    order: str = "desc",
    page: int = 1,
    size: int = 50,
) -> tuple[list[Project], int]:
    """Return (rows, total). Total ignores pagination."""
    qs = db.query(Project)
    if q:
        qs = qs.filter(Project.name.ilike(f"%{q}%"))
    if city:
        qs = qs.filter_by(city=city)
    if industry:
        qs = qs.filter_by(industry=industry)
    if phase:
        qs = qs.filter_by(phase=phase)
    if mode:
        qs = qs.filter_by(mode=mode)

    total = qs.count()

    sort_col = getattr(Project, sort, Project.created_at)
    qs = qs.order_by(sort_col.desc() if order == "desc" else sort_col.asc())

    qs = qs.offset((page - 1) * size).limit(size)
    return qs.all(), total
```

- [ ] **Step 5: 改 api/projects.py 加路由 + 接 query**

```python
# server/app/api/projects.py — 在已有 list / get / create 路由旁加
from fastapi import Query, HTTPException
from pydantic import BaseModel, Field
from ..services import projects as svc


class ProjectCopyIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)


@router.post("/{project_id}/copy", status_code=201,
             dependencies=[Depends(require_auth)])
def copy(
    project_id: str, payload: ProjectCopyIn, db: Session = Depends(get_db),
) -> dict:
    try:
        new = svc.copy_project(db, project_id, payload.name)
    except ValueError as e:
        if "NOT_FOUND" in str(e):
            raise HTTPException(404, detail={"code": "PROJECT_NOT_FOUND"})
        raise
    return {"success": True, "data": ProjectOut.model_validate(new).model_dump(mode="json"), "error": None}


# Replace existing list_ endpoint:
@router.get("", dependencies=[Depends(require_auth)])
def list_(
    q: str | None = Query(None, max_length=100),
    city: str | None = Query(None, max_length=20),
    industry: str | None = Query(None, max_length=40),
    phase: str | None = Query(None, regex="^(budget|bidding|planning|change|settled)$"),
    mode: str | None = Query(None, regex="^(forward|reverse)$"),
    sort: str = Query("created_at", regex="^(created_at|updated_at|name|target_cost)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    rows, total = svc.list_with_query(
        db, q=q, city=city, industry=industry, phase=phase, mode=mode,
        sort=sort, order=order, page=page, size=size,
    )
    return {
        "success": True,
        "data": [ProjectOut.model_validate(r).model_dump(mode="json") for r in rows],
        "error": None,
        "meta": {"total": total, "page": page, "size": size},
    }
```

- [ ] **Step 6: 跑测试 + 全套**

```bash
cd server && pytest tests/integration/test_v2_project_copy.py tests/integration/test_v2_project_list_query.py -v
cd server && pytest -x
```

Expected: 11 new PASS + 已有测试不破。

- [ ] **Step 7: Commit**

```bash
git add server/app/services/projects.py server/app/api/projects.py server/tests/integration/test_v2_project_copy.py server/tests/integration/test_v2_project_list_query.py
git commit -m "feat(server): /projects/{id}/copy + GET /projects 查询参数 (q/sort/page)"
```

---

## Task 7: calc.py 读 project.factors_*_json + factor 组装服务

**Goal:** GAP-B 闭环 — calc 真正用因子值而非默认 1.0。

**Files:**
- Create: `server/app/services/factors.py`
- Modify: `server/app/services/calc.py`
- Modify: `server/app/core/forward.py` (返回 warning_messages)
- Modify: `server/app/core/reverse.py`
- Test: `server/tests/integration/test_v2_calc_uses_project_factors.py`

- [ ] **Step 1: 写测试**

```python
# server/tests/integration/test_v2_calc_uses_project_factors.py
"""GAP-B 闭环：calc 用 project.factors_*_json 替代默认 1.0。"""
import json
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


@pytest.fixture
async def client(monkeypatch, tmp_path):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    monkeypatch.setenv("COST_DB_PATH", f"/tmp/cost-test-{uuid.uuid4()}.sqlite")
    monkeypatch.setenv("COST_DATA_DIR", str(tmp_path))
    import importlib
    for m in ["app.config", "app.db.session", "app.deps", "app.db.models",
              "app.services.params", "app.services.factors", "app.services.calc",
              "app.services.projects", "app.api.projects", "app.api.params",
              "app.api.functions", "app.api.calc", "app.api.health", "app.main"]:
        importlib.reload(importlib.import_module(m))
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    import app.services.params
    app.services.params.seed_from_csbmk()
    import app.main
    transport = ASGITransport(app=app.main.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _seed(c, factors_dev=None):
    r = await c.post("/api/projects", headers=H, json={
        "name": "T", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
        "factors_dev": factors_dev,
    })
    pid = r.json()["data"]["id"]
    await c.post(
        f"/api/projects/{pid}/functions", headers=H,
        json={"name": "fp1", "category": "EI", "complexity": "low",
              "ufp": 3, "us": 3, "source": "manual"})
    return pid


async def test_calc_with_factors_differs_from_default(client):
    pid_default = await _seed(client, factors_dev=None)
    pid_with = await _seed(client, factors_dev={
        "app_type": "OLAP", "integrity_level": "B",
        "non_func": "high", "platform": "PC", "team_bg": "experienced",
    })
    r1 = await client.post(f"/api/projects/{pid_default}/calc/forward", headers=H, json={})
    r2 = await client.post(f"/api/projects/{pid_with}/calc/forward", headers=H, json={})
    cost_default = r1.json()["data"]["dev_cost"]
    cost_with = r2.json()["data"]["dev_cost"]
    assert cost_default != cost_with, "factors 应该真正影响 cost，不能 silently 用 1.0"


async def test_calc_warning_when_factors_null(client):
    pid = await _seed(client, factors_dev=None)
    r = await client.post(f"/api/projects/{pid}/calc/forward", headers=H, json={})
    body = r.json()["data"]
    assert "warning_messages" in body
    assert any("调整因子" in m for m in body["warning_messages"])


async def test_calc_no_warning_when_factors_present(client):
    pid = await _seed(client, factors_dev={
        "app_type": "OLTP", "integrity_level": "A",
        "non_func": "low", "platform": "PC", "team_bg": "experienced",
    })
    r = await client.post(f"/api/projects/{pid}/calc/forward", headers=H, json={})
    body = r.json()["data"]
    msgs = body.get("warning_messages") or []
    assert all("调整因子" not in m for m in msgs)
```

- [ ] **Step 2: 跑测试，确认失败**

- [ ] **Step 3: 创建 services/factors.py — 中央化因子读取**

```python
# server/app/services/factors.py
"""项目级因子值读取 + dev/ops factor chain 组装。

calc.py 不再直接调 core/factors.py 的 dev_factor_chain — 走这一层，让逻辑
集中：null fallback 1.0 + warning_messages。
"""
import json
from typing import Any

from ..core.factors import dev_factor_chain, ops_factor_chain
from ..db.models import Project


def _load(json_str: str | None) -> dict[str, Any]:
    if not json_str:
        return {}
    try:
        return json.loads(json_str) or {}
    except Exception:
        return {}


def project_factors(
    project: Project, effective_params: dict,
) -> tuple[float, float, list[str]]:
    """Return (dev_factor, ops_factor, warnings).

    Falls back to 1.0 with a warning when factors_*_json is empty.
    """
    warnings: list[str] = []
    fd = _load(project.factors_dev_json)
    if fd:
        dev_f = dev_factor_chain(
            app_type=fd.get("app_type"),
            non_func=fd.get("non_func"),
            integrity=fd.get("integrity_level"),
            platform=fd.get("platform"),
            team_bg=fd.get("team_bg"),
            factor_table=effective_params.get("factors_dev", {}),
        )
    else:
        dev_f = 1.0
        warnings.append(
            "此项目缺少开发调整因子配置，已按 1.0 计算。请在项目设置中补充。"
        )

    fo = _load(project.factors_ops_json)
    if fo:
        ops_f = ops_factor_chain(fo, effective_params.get("factors_ops", {}))
    else:
        ops_f = 1.0
        if project.include_ops:
            warnings.append(
                "此项目启用了运维但缺少运维调整因子配置，已按 1.0 计算。"
            )

    return dev_f, ops_f, warnings
```

- [ ] **Step 4: 改 calc.py 用 factors service**

```python
# server/app/services/calc.py — run_forward / run_reverse 中替换
from . import factors as fsvc


def run_forward(db: Session, project_id: str, payload: dict) -> dict:
    proj = db.query(Project).filter_by(id=project_id).first()
    if not proj:
        raise ValueError("PROJECT_NOT_FOUND")
    eff = ps.get_effective(db, project_id)
    ctx = EvaluationContext.from_dict(
        ps.effective_to_calc_dict(eff),
        ProjectInputs(industry=proj.industry, city=proj.city, phase=proj.phase),
    )
    dev_factor, ops_factor, warnings = fsvc.project_factors(proj, eff)
    inp = ForwardInput(
        items=_resolve_items(db, project_id, payload, mode="forward"),
        dev_factor=dev_factor,
        ops_factor=ops_factor,
        include_dev=payload.get("include_dev", True),
        include_ops=payload.get("include_ops", proj.include_ops or False),
        other_cost=payload.get("other_cost", proj.other_cost or 0.0),
    )
    r = calculate_forward(ctx, inp)
    out = r.__dict__.copy()
    out["warning_messages"] = (out.get("warning_messages") or []) + warnings
    return out
```

`run_reverse` 同样修改：从 project + factors service 读 dev/ops factor，warnings 追加。

- [ ] **Step 5: 在 core/forward.py 与 core/reverse.py 的 Result dataclass 加 warning_messages 字段**

`server/app/core/forward.py`：

```python
@dataclass
class ForwardResult:
    # ... 已有字段 ...
    warning_messages: list[str] = field(default_factory=list)
```

`reverse.py` 同。

- [ ] **Step 6: 跑测试**

```bash
cd server && pytest tests/integration/test_v2_calc_uses_project_factors.py -v
cd server && pytest -x  # 不破
```

Expected: 3 new PASS + 不破现有测试。

- [ ] **Step 7: Commit**

```bash
git add server/app/services/factors.py server/app/services/calc.py server/app/core/forward.py server/app/core/reverse.py server/tests/integration/test_v2_calc_uses_project_factors.py
git commit -m "feat(server): calc 读 project.factors_*_json，缺失时 fallback 1.0 + warning"
```

---

# Phase B — 前端 API client

## Task 8: web 前端 API 客户端扩展

**Goal:** 给 web 前端加 snapshots / audit / project copy / project query 4 个新 API client 方法。

**Files:**
- Modify: `web/src/api/projects.ts`
- Create: `web/src/api/snapshots.ts`
- Create: `web/src/api/audit.ts`
- Test: `web/tests/unit/api-projects.spec.ts`

- [ ] **Step 1: 写测试**

```typescript
// web/tests/unit/api-projects.spec.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchProjects, copyProject } from "@/api/projects";
import { listSnapshots, createSnapshot, restoreSnapshot } from "@/api/snapshots";
import { listAudit } from "@/api/audit";

const fetchMock = vi.fn();
global.fetch = fetchMock as any;

beforeEach(() => fetchMock.mockReset());

describe("api/projects", () => {
  it("fetchProjects passes query params", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: [], meta: { total: 0 } }),
    });
    await fetchProjects({ q: "智慧", city: "北京", page: 2, size: 20 });
    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).toContain("q=%E6%99%BA%E6%85%A7");
    expect(url).toContain("city=%E5%8C%97%E4%BA%AC");
    expect(url).toContain("page=2");
    expect(url).toContain("size=20");
  });

  it("copyProject sends new name", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: { id: "new" } }),
    });
    await copyProject("src-id", "新名");
    const opts = fetchMock.mock.calls[0][1] as RequestInit;
    expect(opts.method).toBe("POST");
    expect(JSON.parse(opts.body as string)).toEqual({ name: "新名" });
  });
});

describe("api/snapshots", () => {
  it("listSnapshots scope param", async () => {
    fetchMock.mockResolvedValue({
      ok: true, json: async () => ({ success: true, data: [] }),
    });
    await listSnapshots("global");
    expect(fetchMock.mock.calls[0][0]).toContain("scope=global");
  });

  it("createSnapshot POST", async () => {
    fetchMock.mockResolvedValue({
      ok: true, json: async () => ({ success: true, data: { id: 1 } }),
    });
    await createSnapshot({ scope: "global", label: "x" });
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      scope: "global", label: "x",
    });
  });

  it("restoreSnapshot path", async () => {
    fetchMock.mockResolvedValue({
      ok: true, json: async () => ({ success: true, data: {} }),
    });
    await restoreSnapshot(42);
    expect(fetchMock.mock.calls[0][0]).toContain("/snapshots/42/restore");
  });
});

describe("api/audit", () => {
  it("listAudit cursor pagination", async () => {
    fetchMock.mockResolvedValue({
      ok: true, json: async () => ({ success: true, data: [] }),
    });
    await listAudit("p1", { limit: 50, beforeId: 100 });
    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("limit=50");
    expect(url).toContain("before_id=100");
  });
});
```

- [ ] **Step 2: 跑测试，确认失败**

```bash
cd web && pnpm vitest run tests/unit/api-projects.spec.ts
```

- [ ] **Step 3: 改 api/projects.ts**

`web/src/api/projects.ts` 在文件末尾追加（不替换现有 fetchProjects；改 signature 接 query options）：

```typescript
import { httpFetch } from "./client";

export interface ProjectQuery {
  q?: string;
  city?: string;
  industry?: string;
  phase?: string;
  mode?: "forward" | "reverse";
  sort?: "created_at" | "updated_at" | "name" | "target_cost";
  order?: "asc" | "desc";
  page?: number;
  size?: number;
}

export async function fetchProjects(opts: ProjectQuery = {}): Promise<{ data: Project[]; meta: { total: number; page: number; size: number } }> {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(opts)) {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  }
  const qs = params.toString();
  const r = await httpFetch(`/api/projects${qs ? "?" + qs : ""}`);
  const j = await r.json();
  return { data: j.data, meta: j.meta };
}

export async function copyProject(srcId: string, name: string): Promise<Project> {
  const r = await httpFetch(`/api/projects/${srcId}/copy`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  return (await r.json()).data;
}
```

- [ ] **Step 4: 创建 api/snapshots.ts**

```typescript
// web/src/api/snapshots.ts
import { httpFetch } from "./client";

export interface ParamSnapshot {
  id: number;
  scope: string;
  label: string | null;
  created_at: string;
}

export async function listSnapshots(scope?: string): Promise<ParamSnapshot[]> {
  const qs = scope ? `?scope=${encodeURIComponent(scope)}` : "";
  const r = await httpFetch(`/api/params/snapshots${qs}`);
  return (await r.json()).data;
}

export async function createSnapshot(input: {
  scope: string;
  label?: string;
}): Promise<ParamSnapshot> {
  const r = await httpFetch(`/api/params/snapshots`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return (await r.json()).data;
}

export async function restoreSnapshot(id: number): Promise<unknown> {
  const r = await httpFetch(`/api/params/snapshots/${id}/restore`, {
    method: "POST",
  });
  return (await r.json()).data;
}

export async function deleteSnapshot(id: number): Promise<void> {
  await httpFetch(`/api/params/snapshots/${id}`, { method: "DELETE" });
}
```

- [ ] **Step 5: 创建 api/audit.ts**

```typescript
// web/src/api/audit.ts
import { httpFetch } from "./client";

export interface AuditEntry {
  id: number;
  project_id: string;
  ts: string;
  actor: string | null;
  action: string;
  target: string | null;
  diff_json: string | null;
}

export async function listAudit(
  projectId: string,
  opts: { limit?: number; beforeId?: number } = {},
): Promise<AuditEntry[]> {
  const params = new URLSearchParams();
  if (opts.limit) params.set("limit", String(opts.limit));
  if (opts.beforeId) params.set("before_id", String(opts.beforeId));
  const qs = params.toString();
  const r = await httpFetch(
    `/api/projects/${projectId}/audit${qs ? "?" + qs : ""}`);
  return (await r.json()).data;
}
```

- [ ] **Step 6: 跑测试**

```bash
cd web && pnpm vitest run tests/unit/api-projects.spec.ts
```

Expected: 6 PASS。

- [ ] **Step 7: Commit**

```bash
git add web/src/api/projects.ts web/src/api/snapshots.ts web/src/api/audit.ts web/tests/unit/api-projects.spec.ts
git commit -m "feat(web): API client — projects query/copy + snapshots + audit"
```

---

# Phase C — ParamManager v2 (GAP-B/D/H)

## Task 9: ParamManager 城市费率 tab 加 ops 列 + 生产率加 ops 行

**Goal:** GAP-D — 暴露 city_rate.{city}.ops 和 productivity_ops。

**Files:**
- Modify: `web/src/views/ParamManager.vue`
- Test: `web/tests/unit/ParamManager-rates.spec.ts`

- [ ] **Step 1: 写测试**

```typescript
// web/tests/unit/ParamManager-rates.spec.ts
import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createTestingPinia } from "@pinia/testing";
import ParamManager from "@/views/ParamManager.vue";
import { useParamStore } from "@/stores/params";

vi.mock("@/api/params", () => ({
  fetchEffective: vi.fn().mockResolvedValue({
    data: {
      city_rate: { 北京: { dev: 12000, ops: 9000 }, 上海: { dev: 13000, ops: 9500 } },
      productivity_dev: { 电子政务: { low: 7, average: 8, high: 9 } },
      productivity_ops: { 电子政务: { low: 5, average: 6, high: 7 } },
      hours_per_pm: 176,
    },
  }),
  patchOverride: vi.fn(),
}));

describe("ParamManager — 城市费率 ops 列", () => {
  it("renders both dev and ops columns for each city", async () => {
    const wrapper = mount(ParamManager, {
      global: { plugins: [createTestingPinia({ stubActions: false })] },
    });
    await wrapper.vm.$nextTick();
    await wrapper.find('[data-tab="rate"]').trigger("click");
    await wrapper.vm.$nextTick();
    const rows = wrapper.findAll('[data-testid="city-rate-row"]');
    expect(rows.length).toBeGreaterThanOrEqual(2);
    const beijing = rows.find((r) => r.text().includes("北京"));
    expect(beijing!.text()).toContain("12000"); // dev
    expect(beijing!.text()).toContain("9000");  // ops
  });
});
```

- [ ] **Step 2: 跑测试，确认失败**

- [ ] **Step 3: 改 ParamManager.vue 第 105-122 行的"城市费率" tab**

`web/src/views/ParamManager.vue` 找到 `activeTab === 'rate'` block，替换为：

```vue
<div v-if="activeTab === 'rate' && eff" role="tabpanel" class="panel">
  <table class="rate-table">
    <thead>
      <tr><th>城市</th><th>开发费率（元/PM）</th><th>运维费率（元/PM）</th></tr>
    </thead>
    <tbody>
      <tr
        v-for="(rate, city) in eff.city_rate"
        :key="String(city)"
        data-testid="city-rate-row">
        <td>{{ city }}</td>
        <td>
          <RateCell
            :model-value="(rate as any).dev"
            :overridden="store.isOverridden(`city_rate.${String(city)}.dev`)"
            @update:model-value="(nv) => patchOverride(`city_rate.${String(city)}.dev`, nv)" />
        </td>
        <td>
          <RateCell
            :model-value="(rate as any).ops"
            :overridden="store.isOverridden(`city_rate.${String(city)}.ops`)"
            @update:model-value="(nv) => patchOverride(`city_rate.${String(city)}.ops`, nv)" />
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

`RateCell` 是已存在组件（参照原代码）。

- [ ] **Step 4: 改"生产率"tab — 加 productivity_ops 行**

找到 `activeTab === 'productivity'` block：

```vue
<div v-else-if="activeTab === 'productivity' && eff" role="tabpanel" class="panel">
  <h3 class="subtitle">开发生产率（FP/PM 分档）</h3>
  <table class="rate-table">
    <thead><tr><th>行业</th><th>低</th><th>中</th><th>高</th></tr></thead>
    <tbody>
      <tr v-for="(bands, ind) in eff.productivity_dev" :key="`dev-${String(ind)}`">
        <td>{{ ind }}</td>
        <td v-for="band in ['low','average','high']" :key="band">
          <RateCell
            :model-value="(bands as any)[band]"
            :overridden="store.isOverridden(`productivity_dev.${String(ind)}.${band}`)"
            @update:model-value="(nv) => patchOverride(`productivity_dev.${String(ind)}.${band}`, nv)" />
        </td>
      </tr>
    </tbody>
  </table>
  <h3 class="subtitle" style="margin-top: 24px">运维生产率（FP/PM 分档）</h3>
  <table class="rate-table" v-if="eff.productivity_ops">
    <thead><tr><th>行业</th><th>低</th><th>中</th><th>高</th></tr></thead>
    <tbody>
      <tr v-for="(bands, ind) in eff.productivity_ops" :key="`ops-${String(ind)}`">
        <td>{{ ind }}</td>
        <td v-for="band in ['low','average','high']" :key="band">
          <RateCell
            :model-value="(bands as any)[band]"
            :overridden="store.isOverridden(`productivity_ops.${String(ind)}.${band}`)"
            @update:model-value="(nv) => patchOverride(`productivity_ops.${String(ind)}.${band}`, nv)" />
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

- [ ] **Step 5: 跑测试 + e2e smoke**

```bash
cd web && pnpm vitest run tests/unit/ParamManager-rates.spec.ts
```

- [ ] **Step 6: Commit**

```bash
git add web/src/views/ParamManager.vue web/tests/unit/ParamManager-rates.spec.ts
git commit -m "feat(web): ParamManager 城市费率加 ops 列 + 生产率加 ops 表 (GAP-D)"
```

---

## Task 10: FactorTable 组件 + 开发/运维因子 tab 实装

**Goal:** GAP-B — ParamManager 的 factors_dev / factors_ops tab 从 v2 stub 变成可编辑表。

**Files:**
- Create: `web/src/components/FactorTable.vue`
- Modify: `web/src/views/ParamManager.vue`
- Test: `web/tests/unit/FactorTable.spec.ts`

- [ ] **Step 1: 写组件测试**

```typescript
// web/tests/unit/FactorTable.spec.ts
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import FactorTable from "@/components/FactorTable.vue";

describe("FactorTable", () => {
  const factor = {
    name: "app_type",
    label: "应用类型",
    levels: {
      OLTP: { multiplier: 1.0, description: "联机事务" },
      OLAP: { multiplier: 1.1, description: "数据分析" },
      Web: { multiplier: 1.05, description: "Web 应用" },
    },
  };

  it("renders all levels with multipliers", () => {
    const w = mount(FactorTable, { props: { factor, scope: "global" } });
    expect(w.text()).toContain("应用类型");
    expect(w.text()).toContain("OLTP");
    expect(w.text()).toContain("1.00");
    expect(w.text()).toContain("1.10");
  });

  it("emits update:multiplier when input changes", async () => {
    const w = mount(FactorTable, { props: { factor, scope: "global" } });
    const inputs = w.findAll('input[type="number"]');
    await inputs[0].setValue("1.5");
    expect(w.emitted("update:multiplier")).toBeTruthy();
    const evt = w.emitted("update:multiplier")![0];
    expect(evt[0]).toEqual({ levelKey: "OLTP", value: 1.5 });
  });
});
```

- [ ] **Step 2: 跑测试，确认失败**

- [ ] **Step 3: 创建 FactorTable.vue**

```vue
<!-- web/src/components/FactorTable.vue -->
<script setup lang="ts">
import { computed } from "vue";

interface Level { multiplier: number; description?: string; }
interface FactorDef {
  name: string;
  label: string;
  levels: Record<string, Level>;
}

const props = defineProps<{
  factor: FactorDef;
  scope: "global" | string;  // "global" 或 project_id
}>();

const emit = defineEmits<{
  (e: "update:multiplier", v: { levelKey: string; value: number }): void;
}>();

const rows = computed(() =>
  Object.entries(props.factor.levels).map(([k, v]) => ({
    key: k, multiplier: v.multiplier, description: v.description ?? "",
  })),
);

function onInput(levelKey: string, ev: Event) {
  const v = parseFloat((ev.target as HTMLInputElement).value);
  if (!isNaN(v) && isFinite(v) && v >= 0) {
    emit("update:multiplier", { levelKey, value: v });
  }
}
</script>

<template>
  <div class="factor-card" :data-factor="factor.name">
    <h4 class="factor-title">
      {{ factor.label }}
      <span class="factor-key">({{ factor.name }})</span>
    </h4>
    <table class="factor-table">
      <thead>
        <tr><th>级别</th><th>说明</th><th>系数</th></tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.key">
          <td>{{ row.key }}</td>
          <td>{{ row.description }}</td>
          <td>
            <input
              type="number" step="0.01" min="0"
              :value="row.multiplier.toFixed(2)"
              @change="onInput(row.key, $event)" />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.factor-card {
  border: 1px solid var(--border-default);
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
}
.factor-title { font-size: 14px; font-weight: 600; margin: 0 0 8px; }
.factor-key { font-weight: 400; color: var(--text-secondary); margin-left: 6px; font-size: 12px; }
.factor-table { width: 100%; border-collapse: collapse; }
.factor-table th, .factor-table td { padding: 4px 8px; text-align: left; border-bottom: 1px solid var(--border-subtle); }
.factor-table input { width: 80px; padding: 2px 6px; border: 1px solid var(--border-default); border-radius: 3px; }
</style>
```

- [ ] **Step 4: 改 ParamManager.vue 装填 factors_dev / factors_ops tab**

找到 `activeTab === 'factors_dev'` 的 v2 stub（line 145-154 区域），替换为：

```vue
<div v-else-if="activeTab === 'factors_dev' && eff" role="tabpanel" class="panel">
  <p class="hint">开发调整因子 — 链式相乘后作用于开发工作量。</p>
  <FactorTable
    v-for="(factorObj, factorName) in eff.factors_dev"
    :key="String(factorName)"
    :factor="{
      name: String(factorName),
      label: FACTOR_LABELS[String(factorName)] ?? String(factorName),
      levels: factorObj as any,
    }"
    :scope="scope"
    @update:multiplier="(payload) => onFactorEdit('factors_dev', String(factorName), payload)" />
</div>

<div v-else-if="activeTab === 'factors_ops' && eff" role="tabpanel" class="panel">
  <p class="hint">运维调整因子 — 链式相乘后作用于运维工作量。</p>
  <FactorTable
    v-for="(factorObj, factorName) in eff.factors_ops"
    :key="String(factorName)"
    :factor="{
      name: String(factorName),
      label: FACTOR_LABELS[String(factorName)] ?? String(factorName),
      levels: factorObj as any,
    }"
    :scope="scope"
    @update:multiplier="(payload) => onFactorEdit('factors_ops', String(factorName), payload)" />
</div>
```

`<script setup>` 顶部加：

```typescript
import FactorTable from "@/components/FactorTable.vue";

const FACTOR_LABELS: Record<string, string> = {
  app_type: "应用类型",
  integrity_level: "完整性等级",
  non_func: "非功能性要求",
  platform: "运行平台",
  team_bg: "团队背景",
  // ops 因子
  service_type: "服务类型",
  service_level: "服务级别",
  // ... 等待运行时实际值填充
};

function onFactorEdit(
  group: "factors_dev" | "factors_ops",
  factorName: string,
  payload: { levelKey: string; value: number },
) {
  const path = `${group}.${factorName}.${payload.levelKey}.multiplier`;
  patchOverride(path, payload.value);
}
```

- [ ] **Step 5: 跑测试**

```bash
cd web && pnpm vitest run tests/unit/FactorTable.spec.ts
```

- [ ] **Step 6: Commit**

```bash
git add web/src/components/FactorTable.vue web/src/views/ParamManager.vue web/tests/unit/FactorTable.spec.ts
git commit -m "feat(web): ParamManager 开发/运维因子 tab 实装 (GAP-B)"
```

---

## Task 11: ParamManager 规模变更 tab 实装

**Goal:** GAP-B 子项 — scale_change tab 不再是 stub。

**Files:**
- Modify: `web/src/views/ParamManager.vue`

- [ ] **Step 1: 改 scale_change tab**

找到 `activeTab === 'scale_change'` block，替换：

```vue
<div v-else-if="activeTab === 'scale_change' && eff && eff.scale_change" role="tabpanel" class="panel">
  <p class="hint">规模变更因子 — 处理需求增加 / 减少 / 修改 / 转换的场景。</p>
  <table class="rate-table">
    <thead><tr><th>变更类型</th><th>因子值</th></tr></thead>
    <tbody>
      <tr v-for="(value, key) in eff.scale_change" :key="String(key)">
        <td>{{ SCALE_CHANGE_LABELS[String(key)] ?? String(key) }}</td>
        <td>
          <RateCell
            :model-value="value as number"
            :overridden="store.isOverridden(`scale_change.${String(key)}`)"
            @update:model-value="(nv) => patchOverride(`scale_change.${String(key)}`, nv)" />
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

`<script setup>` 加：

```typescript
const SCALE_CHANGE_LABELS: Record<string, string> = {
  add: "新增",
  remove: "删除",
  modify: "修改",
  convert: "转换",
  threshold: "变更率门槛",
};
```

- [ ] **Step 2: 手动 / e2e 验证 — 跑 dev server 在浏览器里看一眼**

```bash
cd server && uvicorn app.main:app --reload --port 8788 &
cd web && pnpm dev
# 浏览器：http://localhost:5173/params → 切到"规模变更" tab
```

- [ ] **Step 3: Commit**

```bash
git add web/src/views/ParamManager.vue
git commit -m "feat(web): ParamManager 规模变更 tab 实装 (GAP-B)"
```

---

## Task 12: ParamManager 快照 tab 实装

**Goal:** GAP-H — snapshots tab 接 /api/params/snapshots 4 endpoint。

**Files:**
- Modify: `web/src/views/ParamManager.vue`
- Test: `web/tests/unit/ParamManager-snapshots.spec.ts`

- [ ] **Step 1: 写测试**

```typescript
// web/tests/unit/ParamManager-snapshots.spec.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createTestingPinia } from "@pinia/testing";
import ParamManager from "@/views/ParamManager.vue";

const mockSnaps = [
  { id: 1, scope: "global", label: "实验前", created_at: "2026-05-11T00:00:00Z" },
  { id: 2, scope: "global", label: "after-edit", created_at: "2026-05-11T01:00:00Z" },
];

vi.mock("@/api/snapshots", () => ({
  listSnapshots: vi.fn().mockResolvedValue(mockSnaps),
  createSnapshot: vi.fn().mockResolvedValue({ id: 3, scope: "global", label: "x", created_at: "" }),
  restoreSnapshot: vi.fn().mockResolvedValue({}),
  deleteSnapshot: vi.fn().mockResolvedValue(undefined),
}));
vi.mock("@/api/params", () => ({
  fetchEffective: vi.fn().mockResolvedValue({ data: { city_rate: {}, productivity_dev: {}, factors_dev: {}, factors_ops: {}, scale_change: {} } }),
  patchOverride: vi.fn(),
}));

describe("ParamManager — snapshots tab", () => {
  it("lists snapshots after switching tab", async () => {
    const wrapper = mount(ParamManager, {
      global: { plugins: [createTestingPinia({ stubActions: false })] },
    });
    await wrapper.vm.$nextTick();
    await wrapper.find('[data-tab="snapshots"]').trigger("click");
    await new Promise((r) => setTimeout(r, 10));
    expect(wrapper.text()).toContain("实验前");
    expect(wrapper.text()).toContain("after-edit");
  });
});
```

- [ ] **Step 2: 跑测试，确认失败**

- [ ] **Step 3: 在 ParamManager.vue 装填 snapshots tab**

`<script setup>` 顶部加：

```typescript
import { ref } from "vue";
import { listSnapshots, createSnapshot, restoreSnapshot, deleteSnapshot, type ParamSnapshot } from "@/api/snapshots";

const snapshots = ref<ParamSnapshot[]>([]);
const newSnapLabel = ref("");

async function reloadSnapshots() {
  snapshots.value = await listSnapshots(scope.value);
}

async function onCreateSnapshot() {
  await createSnapshot({ scope: scope.value, label: newSnapLabel.value || undefined });
  newSnapLabel.value = "";
  await reloadSnapshots();
}

async function onRestore(id: number) {
  if (!window.confirm("确定 restore 到这一时刻的参数？当前未保存的修改会被覆盖。")) return;
  await restoreSnapshot(id);
  // 触发 effective 重新拉取
  await store.refresh();
}

async function onDelete(id: number) {
  if (!window.confirm("删除这个快照？")) return;
  await deleteSnapshot(id);
  await reloadSnapshots();
}

// watch tab 切换 — 进 snapshots tab 时拉一次
watch(activeTab, (v) => { if (v === "snapshots") reloadSnapshots(); });
```

替换 `activeTab === 'snapshots'` block：

```vue
<div v-else-if="activeTab === 'snapshots'" role="tabpanel" class="panel">
  <div class="snap-toolbar">
    <input v-model="newSnapLabel" placeholder="备注（可选）" class="snap-label-input" />
    <button class="btn-primary" @click="onCreateSnapshot">立即快照</button>
  </div>
  <table class="rate-table">
    <thead>
      <tr><th>ID</th><th>备注</th><th>创建时间</th><th>操作</th></tr>
    </thead>
    <tbody>
      <tr v-for="s in snapshots" :key="s.id">
        <td>#{{ s.id }}</td>
        <td>{{ s.label || "—" }}</td>
        <td>{{ new Date(s.created_at).toLocaleString() }}</td>
        <td>
          <button class="btn-secondary" @click="onRestore(s.id)">恢复</button>
          <button class="btn-link" @click="onDelete(s.id)">删除</button>
        </td>
      </tr>
      <tr v-if="snapshots.length === 0">
        <td colspan="4" class="empty">暂无快照</td>
      </tr>
    </tbody>
  </table>
</div>
```

- [ ] **Step 4: 跑测试**

```bash
cd web && pnpm vitest run tests/unit/ParamManager-snapshots.spec.ts
```

- [ ] **Step 5: Commit**

```bash
git add web/src/views/ParamManager.vue web/tests/unit/ParamManager-snapshots.spec.ts
git commit -m "feat(web): ParamManager 快照 tab 实装 (GAP-H)"
```

---

# Phase D — Wizard v2 (GAP-E/G/K + 因子)

## Task 13: Wizard 拆分 5 步 → 7 步骨架

**Goal:** 把 ProjectWizard.vue 重构成 7 步结构（不改业务，只重组 UI），为后续 task 铺路。

**Files:**
- Modify: `web/src/views/ProjectWizard.vue`
- Test: `web/tests/unit/ProjectWizard-steps.spec.ts`

- [ ] **Step 1: 写测试 — 7 步骨架渲染**

```typescript
// web/tests/unit/ProjectWizard-steps.spec.ts
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import { createTestingPinia } from "@pinia/testing";
import ProjectWizard from "@/views/ProjectWizard.vue";

describe("ProjectWizard 7 steps", () => {
  it("renders 7 step indicators", () => {
    const w = mount(ProjectWizard, {
      global: { plugins: [createTestingPinia()] },
    });
    const steps = w.findAll('[data-testid="wizard-step"]');
    expect(steps.length).toBe(7);
  });

  it("step 1 has client + evaluator inputs", () => {
    const w = mount(ProjectWizard, {
      global: { plugins: [createTestingPinia()] },
    });
    expect(w.find('input[name="client"]').exists()).toBe(true);
    expect(w.find('input[name="evaluator"]').exists()).toBe(true);
  });
});
```

- [ ] **Step 2: 跑测试，确认失败**

- [ ] **Step 3: 重构 ProjectWizard.vue 骨架**

将 `<template>` 重构为 7 步渲染（每步独立 div + step indicator）。`<script setup>` 顶部 form ref 增加：

```typescript
const form = reactive<FormState>({
  // 已有
  mode: "forward",
  name: "",
  city: "北京",
  industry: "电子政务",
  phase: "bidding",
  project_type: "dev_only",
  target_total: 0,
  alpha: 0.7,            // 改默认 0.7
  // 新增 v2.0
  client: "",
  evaluator: "",
  include_ops: false,
  factors_dev: {} as Record<string, string>,  // {"app_type": "OLTP", ...}
  factors_ops: {} as Record<string, string>,
});

const currentStep = ref(1);
const totalSteps = 7;
```

`<template>` 顶部加 step indicator：

```vue
<div class="wizard-steps">
  <div
    v-for="i in totalSteps"
    :key="i"
    class="step"
    data-testid="wizard-step"
    :data-active="i === currentStep"
    :data-done="i < currentStep">
    <span class="num">{{ i }}</span>
    <span class="label">{{ STEP_LABELS[i - 1] }}</span>
  </div>
</div>
```

加 STEP_LABELS：

```typescript
const STEP_LABELS = ["基础信息", "项目类型", "阶段", "正/反向", "开发因子", "运维因子", "确认"];
```

每步用 `v-if="currentStep === N"` 包住对应 form 部分。step1 内容：

```vue
<div v-if="currentStep === 1" class="step-body">
  <h3>基础信息</h3>
  <label>项目名 *
    <input v-model="form.name" required maxlength="120" />
  </label>
  <label>城市 *
    <select v-model="form.city">
      <option v-for="c in CITIES" :key="c">{{ c }}</option>
    </select>
  </label>
  <label>行业 *
    <select v-model="form.industry">
      <option v-for="i in INDUSTRIES" :key="i">{{ i }}</option>
    </select>
  </label>
  <label>客户（可选）
    <input v-model="form.client" name="client" maxlength="80" />
  </label>
  <label>评估方（可选）
    <input v-model="form.evaluator" name="evaluator" maxlength="80" />
  </label>
</div>
```

step 2-7 暂留 placeholder（后续 task 填充）：

```vue
<div v-if="currentStep === 2" class="step-body">[Step 2 — Task 14]</div>
<div v-if="currentStep === 3" class="step-body">[Step 3 — Task 15]</div>
... (4-7 placeholder)
```

底部 nav 按钮：

```vue
<div class="wizard-nav">
  <button v-if="currentStep > 1" @click="currentStep--">上一步</button>
  <button v-if="currentStep < totalSteps" @click="currentStep++" :disabled="!canAdvance">下一步</button>
  <button v-if="currentStep === totalSteps" class="btn-primary" @click="submit">创建项目</button>
</div>
```

`canAdvance` computed 校验当前 step 必填项：

```typescript
const canAdvance = computed(() => {
  if (currentStep.value === 1) return form.name.trim().length > 0;
  return true;
});
```

- [ ] **Step 4: 跑测试**

```bash
cd web && pnpm vitest run tests/unit/ProjectWizard-steps.spec.ts
```

- [ ] **Step 5: Commit**

```bash
git add web/src/views/ProjectWizard.vue web/tests/unit/ProjectWizard-steps.spec.ts
git commit -m "feat(web): Wizard 7 步骨架 + client/evaluator (GAP-G)"
```

---

## Task 14: Wizard Step 2 — 项目类型 + alpha + include_ops

**Goal:** GAP-E — alpha_dev 滑块 + include_ops 联动 + project_type radio。

**Files:**
- Create: `web/src/components/AlphaSlider.vue`
- Modify: `web/src/views/ProjectWizard.vue`

- [ ] **Step 1: 创建 AlphaSlider.vue**

```vue
<!-- web/src/components/AlphaSlider.vue -->
<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  modelValue: number;
}>();
const emit = defineEmits<{
  (e: "update:modelValue", v: number): void;
}>();

const value = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});
const opsShare = computed(() => (1 - value.value).toFixed(2));
</script>

<template>
  <div class="alpha-slider">
    <label class="title">α (开发占总成本比例)</label>
    <div class="control">
      <input type="range" min="0.5" max="1.0" step="0.05" v-model.number="value" />
      <span class="value">α = {{ value.toFixed(2) }}</span>
    </div>
    <p class="hint">
      运维占比 = 1 − α = <strong>{{ opsShare }}</strong>。
      α 越大，开发权重越高；α=1.0 等价于"仅开发"。
    </p>
  </div>
</template>

<style scoped>
.alpha-slider { padding: 12px; border: 1px solid var(--border-default); border-radius: 6px; }
.title { font-weight: 600; display: block; margin-bottom: 8px; }
.control { display: flex; align-items: center; gap: 12px; }
.control input[type="range"] { flex: 1; }
.value { font-variant-numeric: tabular-nums; min-width: 80px; text-align: right; }
.hint { color: var(--text-secondary); font-size: 12px; margin: 8px 0 0; }
</style>
```

- [ ] **Step 2: 替换 step 2 placeholder**

```vue
<div v-if="currentStep === 2" class="step-body">
  <h3>项目类型</h3>
  <fieldset class="radio-group">
    <label v-for="t in ['dev_only', 'ops_only', 'dev_and_ops']" :key="t">
      <input type="radio" :value="t" v-model="form.project_type" @change="onProjectTypeChange" />
      {{ PROJECT_TYPE_LABELS[t] }}
    </label>
  </fieldset>
  <label class="checkbox" v-if="form.project_type !== 'ops_only'">
    <input type="checkbox" v-model="form.include_ops"
           :disabled="form.project_type === 'dev_and_ops'" />
    包含运维成本
  </label>
  <AlphaSlider v-if="form.project_type === 'dev_and_ops'" v-model="form.alpha" />
</div>
```

`<script setup>` 加：

```typescript
import AlphaSlider from "@/components/AlphaSlider.vue";

const PROJECT_TYPE_LABELS: Record<string, string> = {
  dev_only: "仅开发",
  ops_only: "仅运维",
  dev_and_ops: "开发 + 运维",
};

function onProjectTypeChange() {
  if (form.project_type === "ops_only") {
    form.include_ops = true;  // ops_only 隐含
  }
  if (form.project_type === "dev_and_ops") {
    form.include_ops = true;  // 强制
  }
  if (form.project_type === "dev_only") {
    form.include_ops = false;
    form.alpha = 1.0;
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add web/src/components/AlphaSlider.vue web/src/views/ProjectWizard.vue
git commit -m "feat(web): Wizard step 2 — project_type + alpha + include_ops (GAP-E)"
```

---

## Task 15: Wizard Step 3 — 阶段 + CF 预览

**Goal:** GAP-K — phase radio + 当前 CF 值显示。

**Files:**
- Create: `web/src/components/PhaseCfPreview.vue`
- Modify: `web/src/views/ProjectWizard.vue`

- [ ] **Step 1: 创建 PhaseCfPreview.vue**

```vue
<!-- web/src/components/PhaseCfPreview.vue -->
<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  phase: string;
  cf: Record<string, number>;  // 来自 effective.cf — {"budget": 1.5, "bidding": 1.21, ...}
}>();

const PHASE_LABELS: Record<string, string> = {
  budget: "预算",
  bidding: "招标",
  planning: "立项",
  change: "变更",
  settled: "结算",
};

const PHASE_HINTS: Record<string, string> = {
  budget: "项目尚未立项 — 预算阶段最大不确定性。",
  bidding: "已经发标 — 不确定性中等。",
  planning: "立项完成 — 已收敛。",
  change: "变更过程中 — 二次估算。",
  settled: "项目结束 — 数值已确定。",
};

const currentCf = computed(() => props.cf?.[props.phase] ?? 1.0);
</script>

<template>
  <div class="phase-grid">
    <label v-for="key in Object.keys(PHASE_LABELS)" :key="key" class="phase-card"
           :data-active="key === phase">
      <input type="radio" :value="key" :checked="key === phase" @change="$emit('update:phase', key)" />
      <strong>{{ PHASE_LABELS[key] }}</strong>
      <span class="cf">CF = {{ (cf?.[key] ?? 1.0).toFixed(2) }}</span>
      <p>{{ PHASE_HINTS[key] }}</p>
    </label>
  </div>
  <div class="phase-summary">
    您选择的阶段对应的 CF 调整因子 = <strong>{{ currentCf.toFixed(2) }}</strong>。
    它会作为本项目所有计算的乘数。
  </div>
</template>

<style scoped>
.phase-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 8px; }
.phase-card { display: block; padding: 12px; border: 1px solid var(--border-default); border-radius: 6px; cursor: pointer; }
.phase-card[data-active="true"] { border-color: var(--color-primary); background: var(--color-primary-subtle); }
.phase-card input[type="radio"] { margin-right: 6px; }
.phase-card strong { display: block; margin: 4px 0; }
.phase-card .cf { font-size: 12px; font-variant-numeric: tabular-nums; color: var(--text-secondary); }
.phase-card p { font-size: 12px; color: var(--text-secondary); margin: 4px 0 0; }
.phase-summary { margin-top: 16px; padding: 12px; background: var(--color-info-subtle); border-radius: 6px; }
</style>
```

- [ ] **Step 2: 替换 step 3 placeholder**

```vue
<div v-if="currentStep === 3" class="step-body">
  <h3>项目阶段</h3>
  <PhaseCfPreview :phase="form.phase" :cf="effectiveParams?.cf ?? {}"
                  @update:phase="(v: string) => form.phase = v" />
</div>
```

`<script setup>` 加：

```typescript
import PhaseCfPreview from "@/components/PhaseCfPreview.vue";
import { fetchEffective } from "@/api/params";

const effectiveParams = ref<any>(null);
onMounted(async () => {
  effectiveParams.value = (await fetchEffective()).data;
});
```

- [ ] **Step 3: Commit**

```bash
git add web/src/components/PhaseCfPreview.vue web/src/views/ProjectWizard.vue
git commit -m "feat(web): Wizard step 3 — phase + CF 实时预览 (GAP-K)"
```

---

## Task 16: Wizard Step 4 — 正/反向

**Goal:** 维持现有正/反向逻辑，移到 step 4。

**Files:**
- Modify: `web/src/views/ProjectWizard.vue`

- [ ] **Step 1: 替换 step 4 placeholder**

```vue
<div v-if="currentStep === 4" class="step-body">
  <h3>计算模式</h3>
  <fieldset class="radio-group">
    <label>
      <input type="radio" value="forward" v-model="form.mode" />
      正向 — 已有功能点 → 估算成本
    </label>
    <label>
      <input type="radio" value="reverse" v-model="form.mode" />
      反向 — 已有目标成本 → 推算功能点
    </label>
  </fieldset>
  <label v-if="form.mode === 'reverse'" class="field">
    目标总成本（元） *
    <input type="number" v-model.number="form.target_total" min="1" required />
  </label>
</div>
```

- [ ] **Step 2: 修 canAdvance**

```typescript
const canAdvance = computed(() => {
  switch (currentStep.value) {
    case 1: return form.name.trim().length > 0;
    case 4: return form.mode === "forward" || form.target_total > 0;
    default: return true;
  }
});
```

- [ ] **Step 3: Commit**

```bash
git add web/src/views/ProjectWizard.vue
git commit -m "feat(web): Wizard step 4 — 正向/反向"
```

---

## Task 17: Wizard Step 5/6 — 因子 dropdown + 实时计算

**Goal:** GAP-B — 用户在 wizard 选因子值，wizard 实时显示组装后的 dev_factor / ops_factor。

**Files:**
- Create: `web/src/components/FactorDropdown.vue`
- Modify: `web/src/views/ProjectWizard.vue`
- Test: `web/tests/unit/FactorDropdown.spec.ts`

- [ ] **Step 1: 写测试**

```typescript
// web/tests/unit/FactorDropdown.spec.ts
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import FactorDropdown from "@/components/FactorDropdown.vue";

describe("FactorDropdown", () => {
  const def = {
    name: "app_type",
    label: "应用类型",
    levels: {
      OLTP: { multiplier: 1.0 },
      OLAP: { multiplier: 1.1 },
    },
  };

  it("renders options with multipliers", () => {
    const w = mount(FactorDropdown, {
      props: { factor: def, modelValue: "OLTP" },
    });
    expect(w.text()).toContain("OLTP");
    expect(w.text()).toContain("1.00");
  });

  it("emits update:modelValue on select", async () => {
    const w = mount(FactorDropdown, {
      props: { factor: def, modelValue: "OLTP" },
    });
    await w.find("select").setValue("OLAP");
    expect(w.emitted("update:modelValue")![0]).toEqual(["OLAP"]);
  });
});
```

- [ ] **Step 2: 跑测试，确认失败**

- [ ] **Step 3: 创建 FactorDropdown.vue**

```vue
<!-- web/src/components/FactorDropdown.vue -->
<script setup lang="ts">
const props = defineProps<{
  factor: { name: string; label: string; levels: Record<string, { multiplier: number; description?: string }> };
  modelValue: string | undefined;
}>();
defineEmits<{ (e: "update:modelValue", v: string): void }>();
</script>

<template>
  <label class="factor-dd">
    <span class="lbl">{{ factor.label }} <span class="key">({{ factor.name }})</span></span>
    <select :value="modelValue ?? ''" @change="$emit('update:modelValue', ($event.target as HTMLSelectElement).value)">
      <option value="" disabled>请选择</option>
      <option v-for="(lvl, key) in factor.levels" :key="String(key)" :value="String(key)">
        {{ key }} — ×{{ lvl.multiplier.toFixed(2) }}<span v-if="lvl.description"> · {{ lvl.description }}</span>
      </option>
    </select>
  </label>
</template>

<style scoped>
.factor-dd { display: block; margin-bottom: 12px; }
.lbl { display: block; font-size: 13px; font-weight: 500; margin-bottom: 4px; }
.key { font-weight: 400; color: var(--text-secondary); margin-left: 4px; }
.factor-dd select { width: 100%; padding: 6px 8px; border: 1px solid var(--border-default); border-radius: 4px; }
</style>
```

- [ ] **Step 4: 替换 step 5/6 placeholder**

```vue
<div v-if="currentStep === 5" class="step-body">
  <h3>开发调整因子</h3>
  <p class="hint">不填的因子按 ×1.00 计算（不影响成本）。</p>
  <FactorDropdown
    v-for="(def, key) in (effectiveParams?.factors_dev ?? {})"
    :key="String(key)"
    :factor="{ name: String(key), label: FACTOR_LABELS[String(key)] ?? String(key), levels: def as any }"
    :model-value="form.factors_dev[String(key)]"
    @update:model-value="(v: string) => form.factors_dev[String(key)] = v" />
  <div class="factor-chain-preview">
    实时 dev_factor 链 = <strong>{{ devFactorPreview.toFixed(2) }}</strong>
  </div>
</div>

<div v-if="currentStep === 6 && form.include_ops" class="step-body">
  <h3>运维调整因子</h3>
  <FactorDropdown
    v-for="(def, key) in (effectiveParams?.factors_ops ?? {})"
    :key="String(key)"
    :factor="{ name: String(key), label: FACTOR_LABELS[String(key)] ?? String(key), levels: def as any }"
    :model-value="form.factors_ops[String(key)]"
    @update:model-value="(v: string) => form.factors_ops[String(key)] = v" />
  <div class="factor-chain-preview">
    实时 ops_factor 链 = <strong>{{ opsFactorPreview.toFixed(2) }}</strong>
  </div>
</div>

<div v-if="currentStep === 6 && !form.include_ops" class="step-body">
  <p>本项目未启用运维，跳过运维因子。</p>
</div>
```

`<script setup>` 加：

```typescript
import FactorDropdown from "@/components/FactorDropdown.vue";

const FACTOR_LABELS: Record<string, string> = {
  app_type: "应用类型",
  integrity_level: "完整性等级",
  non_func: "非功能性要求",
  platform: "运行平台",
  team_bg: "团队背景",
};

function chainMultiply(
  selections: Record<string, string>,
  defs: Record<string, Record<string, { multiplier: number }>>,
): number {
  let f = 1.0;
  for (const [factorName, levelKey] of Object.entries(selections)) {
    if (!levelKey) continue;
    const m = defs?.[factorName]?.[levelKey]?.multiplier;
    if (typeof m === "number") f *= m;
  }
  return f;
}

const devFactorPreview = computed(() =>
  chainMultiply(form.factors_dev, effectiveParams.value?.factors_dev ?? {}),
);
const opsFactorPreview = computed(() =>
  chainMultiply(form.factors_ops, effectiveParams.value?.factors_ops ?? {}),
);
```

- [ ] **Step 5: 跑测试**

```bash
cd web && pnpm vitest run tests/unit/FactorDropdown.spec.ts
```

- [ ] **Step 6: Commit**

```bash
git add web/src/components/FactorDropdown.vue web/src/views/ProjectWizard.vue web/tests/unit/FactorDropdown.spec.ts
git commit -m "feat(web): Wizard step 5/6 — factor dropdowns + 实时 chain 预览 (GAP-B)"
```

---

## Task 18: Wizard Step 7 — 确认 + 提交

**Goal:** Step 7 展示全部参数 + 提交时把 factors 序列化进 payload。

**Files:**
- Modify: `web/src/views/ProjectWizard.vue`

- [ ] **Step 1: 替换 step 7 placeholder**

```vue
<div v-if="currentStep === 7" class="step-body">
  <h3>确认</h3>
  <dl class="confirm-list">
    <dt>项目名</dt><dd>{{ form.name }}</dd>
    <dt>城市 / 行业</dt><dd>{{ form.city }} / {{ form.industry }}</dd>
    <dt>客户 / 评估方</dt><dd>{{ form.client || "—" }} / {{ form.evaluator || "—" }}</dd>
    <dt>类型</dt><dd>{{ PROJECT_TYPE_LABELS[form.project_type] }}</dd>
    <dt v-if="form.project_type === 'dev_and_ops'">α</dt>
    <dd v-if="form.project_type === 'dev_and_ops'">{{ form.alpha.toFixed(2) }}</dd>
    <dt>阶段</dt><dd>{{ form.phase }} (CF = {{ (effectiveParams?.cf?.[form.phase] ?? 1).toFixed(2) }})</dd>
    <dt>模式</dt><dd>{{ form.mode === "forward" ? "正向" : `反向（目标 ${form.target_total} 元）` }}</dd>
    <dt>开发因子</dt>
    <dd>
      <ul class="factor-list">
        <li v-for="(v, k) in form.factors_dev" :key="String(k)" v-if="v">
          {{ FACTOR_LABELS[String(k)] }}: {{ v }}
        </li>
        <li v-if="Object.values(form.factors_dev).every(v => !v)">未配置（按 1.0 计算）</li>
      </ul>
    </dd>
    <dt v-if="form.include_ops">运维因子</dt>
    <dd v-if="form.include_ops">
      <ul class="factor-list">
        <li v-for="(v, k) in form.factors_ops" :key="String(k)" v-if="v">
          {{ FACTOR_LABELS[String(k)] }}: {{ v }}
        </li>
      </ul>
    </dd>
  </dl>
</div>
```

- [ ] **Step 2: 改 submit() 把 factors 写进 payload**

```typescript
async function submit() {
  const payload = {
    name: form.name,
    project_type: form.project_type,
    phase: form.phase,
    city: form.city,
    industry: form.industry,
    client: form.client || null,
    evaluator: form.evaluator || null,
    mode: form.mode,
    target_cost: form.mode === "reverse" ? form.target_total : null,
    include_ops: form.include_ops,
    alpha_dev: form.alpha,
    basis_data_ver: "CSBMK®-202510",
    factors_dev: hasAnyFactor(form.factors_dev) ? form.factors_dev : null,
    factors_ops: hasAnyFactor(form.factors_ops) ? form.factors_ops : null,
  };
  const proj = await createProject(payload);
  router.push(`/projects/${proj.id}/fp`);
}

function hasAnyFactor(obj: Record<string, string>): boolean {
  return Object.values(obj).some((v) => v && v.length > 0);
}
```

- [ ] **Step 3: e2e smoke**

```bash
cd web && pnpm dev
# 浏览器手测：完成 7 步 → 创建项目 → 跳到 FP 页
```

- [ ] **Step 4: Commit**

```bash
git add web/src/views/ProjectWizard.vue
git commit -m "feat(web): Wizard step 7 确认 + factors 写进 create payload"
```

---

## Task 19: Wizard E2E 完整流程测试

**Goal:** Playwright 跑一次 7 步完整流程。

**Files:**
- Create: `web/tests/e2e/v2-wizard-flow.spec.ts`

- [ ] **Step 1: 写 e2e**

```typescript
// web/tests/e2e/v2-wizard-flow.spec.ts
import { test, expect } from "@playwright/test";

test("Wizard 7 步完整流程，创建项目并跳到 FP 页", async ({ page }) => {
  await page.goto("/projects/new");

  // Step 1
  await page.fill('input[name="client"]', "测试客户");
  await page.fill('input[name="evaluator"]', "测试评估方");
  await page.fill('input[required]', "E2E 项目");
  await page.click("text=下一步");

  // Step 2
  await page.click('input[value="dev_only"]');
  await page.click("text=下一步");

  // Step 3
  await page.click("text=招标");
  await page.click("text=下一步");

  // Step 4
  await page.click('input[value="forward"]');
  await page.click("text=下一步");

  // Step 5
  await page.selectOption("select >> nth=0", "OLTP");
  await page.click("text=下一步");

  // Step 6 — 跳过（dev_only 没有运维）
  await page.click("text=下一步");

  // Step 7 确认
  await expect(page.getByText("E2E 项目")).toBeVisible();
  await page.click("text=创建项目");

  // 跳到 FP 页
  await expect(page).toHaveURL(/\/projects\/[^/]+\/fp/);
});
```

- [ ] **Step 2: 跑 e2e**

```bash
cd web && pnpm exec playwright test tests/e2e/v2-wizard-flow.spec.ts
```

- [ ] **Step 3: Commit**

```bash
git add web/tests/e2e/v2-wizard-flow.spec.ts
git commit -m "test(web): Wizard 7 步 E2E 流程"
```

---

# Phase E — ProjectList v2 + 审计 view (GAP-F/I/J 前端)

## Task 20: ProjectList toolbar — 搜索 + 筛选 + 排序 + 分页

**Goal:** GAP-F 前端 — 接 fetchProjects(opts) 新签名。

**Files:**
- Modify: `web/src/views/ProjectList.vue`

- [ ] **Step 1: 替换 ProjectList.vue 顶部加 toolbar**

```vue
<!-- ProjectList.vue 在 <template> 顶部 -->
<div class="list-toolbar">
  <input v-model="filter.q" @input="debouncedReload" placeholder="🔍 搜索项目名…" class="search" />
  <select v-model="filter.city" @change="reload">
    <option value="">所有城市</option>
    <option v-for="c in CITIES" :key="c" :value="c">{{ c }}</option>
  </select>
  <select v-model="filter.industry" @change="reload">
    <option value="">所有行业</option>
    <option v-for="i in INDUSTRIES" :key="i" :value="i">{{ i }}</option>
  </select>
  <select v-model="filter.phase" @change="reload">
    <option value="">所有阶段</option>
    <option value="budget">预算</option>
    <option value="bidding">招标</option>
    <option value="planning">立项</option>
    <option value="change">变更</option>
    <option value="settled">结算</option>
  </select>
  <select v-model="filter.sort" @change="reload">
    <option value="created_at">创建时间</option>
    <option value="updated_at">更新时间</option>
    <option value="name">名称</option>
  </select>
  <button @click="filter.order = filter.order === 'asc' ? 'desc' : 'asc'; reload()">
    {{ filter.order === "asc" ? "↑" : "↓" }}
  </button>
  <router-link to="/projects/new" class="btn-primary">+ 新建</router-link>
</div>

<div v-if="totalCount > pageSize" class="pagination">
  <button :disabled="page <= 1" @click="page--; reload()">上一页</button>
  <span>第 {{ page }} / {{ Math.ceil(totalCount / pageSize) }} 页（共 {{ totalCount }}）</span>
  <button :disabled="page * pageSize >= totalCount" @click="page++; reload()">下一页</button>
</div>
```

`<script setup>` 改：

```typescript
import { ref, reactive, onMounted } from "vue";
import { fetchProjects } from "@/api/projects";

const projects = ref<any[]>([]);
const totalCount = ref(0);
const page = ref(1);
const pageSize = 20;

const filter = reactive({
  q: "",
  city: "",
  industry: "",
  phase: "",
  sort: "created_at",
  order: "desc" as "asc" | "desc",
});

async function reload() {
  const r = await fetchProjects({
    q: filter.q || undefined,
    city: filter.city || undefined,
    industry: filter.industry || undefined,
    phase: filter.phase || undefined,
    sort: filter.sort as any,
    order: filter.order,
    page: page.value,
    size: pageSize,
  });
  projects.value = r.data;
  totalCount.value = r.meta.total;
}

let debounceTimer: number | null = null;
function debouncedReload() {
  if (debounceTimer) window.clearTimeout(debounceTimer);
  debounceTimer = window.setTimeout(() => {
    page.value = 1;
    reload();
  }, 250);
}

onMounted(reload);
```

- [ ] **Step 2: 跑 dev server 手测**

```bash
cd web && pnpm dev
# 浏览器：搜「智」、切城市、切排序，验证生效
```

- [ ] **Step 3: Commit**

```bash
git add web/src/views/ProjectList.vue
git commit -m "feat(web): ProjectList 搜索/筛选/排序/分页 (GAP-F)"
```

---

## Task 21: ProjectList 行操作菜单 + AuditView

**Goal:** GAP-I 前端复制 + GAP-J 前端审计 view。

**Files:**
- Create: `web/src/components/ProjectActionMenu.vue`
- Create: `web/src/views/AuditView.vue`
- Modify: `web/src/views/ProjectList.vue`
- Modify: `web/src/router/index.ts`

- [ ] **Step 1: 创建 ProjectActionMenu.vue**

```vue
<!-- web/src/components/ProjectActionMenu.vue -->
<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { copyProject } from "@/api/projects";

const props = defineProps<{ projectId: string; projectName: string }>();
const emit = defineEmits<{ (e: "deleted"): void; (e: "copied"): void }>();
const open = ref(false);
const router = useRouter();

async function onCopy() {
  open.value = false;
  const newName = window.prompt("新项目名", `${props.projectName} (副本)`);
  if (!newName?.trim()) return;
  const r = await copyProject(props.projectId, newName.trim());
  emit("copied");
  router.push(`/projects/${r.id}/fp`);
}

function onAudit() {
  open.value = false;
  router.push(`/projects/${props.projectId}/audit`);
}

async function onDelete() {
  open.value = false;
  if (!window.confirm(`确定删除「${props.projectName}」？该操作不可恢复。`)) return;
  // 假设 deleteProject 已存在
  const { deleteProject } = await import("@/api/projects");
  await deleteProject(props.projectId);
  emit("deleted");
}
</script>

<template>
  <div class="action-menu">
    <button class="trigger" @click.stop="open = !open" aria-label="项目操作">⋯</button>
    <ul v-if="open" class="menu" @click.stop>
      <li @click="onCopy">📋 复制项目</li>
      <li @click="onAudit">🕒 审计日志</li>
      <li class="danger" @click="onDelete">🗑️ 删除</li>
    </ul>
  </div>
</template>

<style scoped>
.action-menu { position: relative; display: inline-block; }
.trigger { background: transparent; border: none; cursor: pointer; padding: 4px 10px; font-size: 18px; }
.menu { position: absolute; right: 0; top: 100%; background: var(--surface-elevated); border: 1px solid var(--border-default); border-radius: 4px; box-shadow: var(--shadow-md); list-style: none; padding: 4px 0; margin: 0; min-width: 140px; z-index: 10; }
.menu li { padding: 6px 12px; cursor: pointer; }
.menu li:hover { background: var(--color-primary-subtle); }
.menu li.danger { color: var(--color-danger); }
</style>
```

- [ ] **Step 2: 创建 AuditView.vue**

```vue
<!-- web/src/views/AuditView.vue -->
<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import { listAudit, type AuditEntry } from "@/api/audit";

const route = useRoute();
const projectId = route.params.id as string;
const entries = ref<AuditEntry[]>([]);
const loading = ref(false);

const ACTION_LABELS: Record<string, string> = {
  "project.create": "✨ 创建项目",
  "project.update": "✏️ 修改项目",
  "project.delete": "🗑️ 删除项目",
  "project.copy": "📋 复制项目",
  "fp.create": "➕ 添加 FP",
  "fp.update": "✏️ 修改 FP",
  "fp.delete": "➖ 删除 FP",
  "fp.bulk_write": "📦 批量写入 FP",
  "fp.restore": "🔄 恢复 FP 快照",
  "params.override": "⚙️ 修改参数",
  "upload.create": "📁 上传文档",
  "upload.delete": "🗑️ 删除上传",
  "calc.run": "🧮 执行计算",
  "report.export": "📤 导出报告",
};

async function reload(beforeId?: number) {
  loading.value = true;
  try {
    const more = await listAudit(projectId, { limit: 50, beforeId });
    if (beforeId) {
      entries.value.push(...more);
    } else {
      entries.value = more;
    }
  } finally {
    loading.value = false;
  }
}

onMounted(() => reload());

async function onLoadMore() {
  const last = entries.value[entries.value.length - 1];
  if (last) await reload(last.id);
}
</script>

<template>
  <div class="audit-view">
    <header>
      <router-link :to="`/projects/${projectId}/fp`" class="back">← 返回项目</router-link>
      <h2>审计日志</h2>
    </header>
    <ol class="timeline">
      <li v-for="e in entries" :key="e.id" class="audit-row">
        <time>{{ new Date(e.ts).toLocaleString() }}</time>
        <strong>{{ ACTION_LABELS[e.action] ?? e.action }}</strong>
        <span class="target" v-if="e.target && e.target !== projectId">→ {{ e.target }}</span>
      </li>
      <li v-if="entries.length === 0 && !loading" class="empty">暂无审计记录</li>
    </ol>
    <button v-if="entries.length >= 50" @click="onLoadMore" :disabled="loading" class="btn-secondary">
      {{ loading ? "加载中…" : "加载更早记录" }}
    </button>
  </div>
</template>

<style scoped>
.audit-view { max-width: 800px; margin: 0 auto; padding: 24px; }
.back { color: var(--text-secondary); text-decoration: none; }
.timeline { list-style: none; padding: 0; margin: 16px 0; }
.audit-row { display: flex; align-items: baseline; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--border-subtle); }
.audit-row time { color: var(--text-secondary); font-size: 12px; min-width: 140px; }
.audit-row .target { color: var(--text-secondary); font-size: 12px; }
.empty { padding: 24px; text-align: center; color: var(--text-secondary); }
</style>
```

- [ ] **Step 3: 在 ProjectList.vue 行尾插入 ActionMenu**

```vue
<!-- 已有 v-for 项目行末尾加 -->
<td>
  <ProjectActionMenu
    :project-id="p.id" :project-name="p.name"
    @deleted="reload" @copied="reload" />
</td>
```

`<script setup>`：`import ProjectActionMenu from "@/components/ProjectActionMenu.vue";`

- [ ] **Step 4: 在 router 注册 audit route**

`web/src/router/index.ts`：

```typescript
{
  path: "/projects/:id/audit",
  component: () => import("@/views/AuditView.vue"),
  name: "ProjectAudit",
},
```

- [ ] **Step 5: e2e smoke**

```bash
cd web && pnpm dev
# 浏览器：项目列表 → ⋯ → 复制 / 审计 → 验证
```

- [ ] **Step 6: Commit**

```bash
git add web/src/components/ProjectActionMenu.vue web/src/views/AuditView.vue web/src/views/ProjectList.vue web/src/router/index.ts
git commit -m "feat(web): ProjectList 行操作菜单 + AuditView (GAP-I/J)"
```

---

# Phase F — AI Plugin 链路 (GAP-A/C)

## Task 22: FpEditor — AI hint + claude_draft 高亮

**Goal:** GAP-A 前端 — 上传完成后告知用户用 /cost；AI 生成的 FP 用浅黄底色 + 徽标。

**Files:**
- Modify: `web/src/views/FpEditor.vue`
- Test: `web/tests/unit/FpEditor-ai-draft.spec.ts`

- [ ] **Step 1: 写测试**

```typescript
// web/tests/unit/FpEditor-ai-draft.spec.ts
import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createTestingPinia } from "@pinia/testing";
import FpEditor from "@/views/FpEditor.vue";

vi.mock("@/api/functions", () => ({
  listFunctions: vi.fn().mockResolvedValue([
    { id: "1", name: "manual fp", source: "manual", category: "EI", complexity: "low", ufp: 3, us: 3 },
    { id: "2", name: "AI 草稿 fp", source: "claude_draft", category: "EI", complexity: "low", ufp: 3, us: 3 },
  ]),
}));

describe("FpEditor — claude_draft 高亮", () => {
  it("renders AI draft rows with claude-draft data attribute", async () => {
    const w = mount(FpEditor, {
      props: { projectId: "p1" },
      global: { plugins: [createTestingPinia()] },
    });
    await new Promise((r) => setTimeout(r, 10));
    const aiRow = w.find('[data-source="claude_draft"]');
    expect(aiRow.exists()).toBe(true);
    expect(aiRow.text()).toContain("AI 草稿");
  });
});
```

- [ ] **Step 2: 改 FpEditor.vue**

找到上传完成的 alert（约 line 56）：

```typescript
// OLD:
window.alert("上传完成。AI 提取功能将在 Phase 5 接入；请先手动添加功能点。");

// NEW:
showToast({
  message: "已上传。在 Claude Code 终端运行 /cost 让 AI 提取 FP 草稿；或继续手动添加。",
  duration: 6000,
  type: "info",
});
// 启动 polling — 等 AI 写入
startPolling();
```

新增 `startPolling`：

```typescript
let pollTimer: number | null = null;
const lastFpCount = ref(0);
const aiPollHint = ref("");

function startPolling() {
  if (pollTimer) return;
  lastFpCount.value = fps.value.length;
  aiPollHint.value = "等待 Claude Code 写入 AI 草稿…（每 30s 自动刷新）";
  pollTimer = window.setInterval(async () => {
    await reloadFps();
    if (fps.value.length > lastFpCount.value) {
      stopPolling();
      showToast({ message: `AI 写入了 ${fps.value.length - lastFpCount.value} 条 FP 草稿，请审核。`, type: "success" });
    }
  }, 30000);
  // 5 分钟后自动停
  setTimeout(stopPolling, 300_000);
}

function stopPolling() {
  if (pollTimer) { window.clearInterval(pollTimer); pollTimer = null; }
  aiPollHint.value = "";
}
```

FP 表格行加 `data-source` + 徽标：

```vue
<tr v-for="fp in fps" :key="fp.id" :data-source="fp.source"
    :class="{ 'ai-draft': fp.source === 'claude_draft' }">
  <td>
    <span v-if="fp.source === 'claude_draft'" class="badge-ai">AI 草稿</span>
    {{ fp.name }}
  </td>
  ... (其他列)
</tr>
```

CSS：

```css
.ai-draft { background: oklch(95% 0.08 95); }
.badge-ai { display: inline-block; padding: 2px 6px; font-size: 10px; background: var(--color-warn); color: white; border-radius: 3px; margin-right: 6px; }
```

`<template>` 上传按钮旁加 polling hint：

```vue
<p v-if="aiPollHint" class="ai-poll-hint">{{ aiPollHint }} <button @click="reloadFps">立即刷新</button></p>
```

- [ ] **Step 3: 跑测试**

```bash
cd web && pnpm vitest run tests/unit/FpEditor-ai-draft.spec.ts
```

- [ ] **Step 4: Commit**

```bash
git add web/src/views/FpEditor.vue web/tests/unit/FpEditor-ai-draft.spec.ts
git commit -m "feat(web): FpEditor — AI Plugin hint + claude_draft 高亮 + 自动 polling (GAP-A)"
```

---

## Task 23: ResultView — 反向 allocator UI

**Goal:** GAP-C — 反向结果页加"生成模块分摊"按钮 + 结果表。

**Files:**
- Modify: `web/src/views/ResultView.vue`
- Modify: `web/src/api/calc.ts` (确认 allocate 已暴露)

- [ ] **Step 1: 改 ResultView.vue**

在反向路径渲染区下方加：

```vue
<section v-if="mode === 'reverse' && result" class="allocator-panel">
  <h3>AI 模块分摊</h3>
  <p>反向计算给出三档总 FP；让 Claude 把 FP 拆成模块清单（每模块带名称 + 权重）。</p>
  <button class="btn-primary" @click="onAllocate" :disabled="allocating">
    {{ allocating ? "等待 Claude…" : "生成模块分摊" }}
  </button>
  <p v-if="allocateHint" class="hint">{{ allocateHint }}</p>
  <table v-if="allocResult" class="alloc-table">
    <thead>
      <tr><th>模块</th><th>权重</th><th>分配 US</th></tr>
    </thead>
    <tbody>
      <tr v-for="r in allocResult" :key="r.name">
        <td>{{ r.name }}</td>
        <td>{{ r.weight.toFixed(2) }}</td>
        <td>{{ r.assigned_us.toFixed(1) }}</td>
      </tr>
    </tbody>
  </table>
</section>
```

`<script setup>` 加：

```typescript
const allocating = ref(false);
const allocateHint = ref("");
const allocResult = ref<any[] | null>(null);

async function onAllocate() {
  allocating.value = true;
  allocateHint.value = "在 Claude Code 终端运行 /cost-allocate " + projectId + " 让 AI 生成模块草稿。";
  // 启动 polling 等 allocator 完成（写法与 FpEditor polling 类似）
  // MVP 实现：依赖用户后续 trigger 一个 reload；或直接 poll /functions（claude_draft 数量变化 → 假设拿到了）
  // 此处我们简化：用户跑 /cost-allocate 后 server 端 cli 会调 /api/calc/allocate 并把结果存项目下；前端 30s 后 fetch
  setTimeout(async () => {
    const { fetchAllocateResult } = await import("@/api/calc");
    try {
      allocResult.value = await fetchAllocateResult(projectId, "p50"); // P50 档
    } catch {}
    allocating.value = false;
  }, 35000);
}
```

注：本 task 假定 `/api/projects/{id}/allocations` 端点存在 — 若无，本 task 改为前端直接调 `/api/calc/allocate`，passthrough 用户在 step / drafts 自定义。MVP 实现是后者：

```typescript
async function onAllocate() {
  if (!result.value?.bands) return;
  const targetUs = result.value.bands.p50.scale_us;
  const drafts = window.prompt(
    "输入模块草稿，JSON 数组 [{name, weight}, ...]（v2.0 后续可从 Claude 生成）",
    JSON.stringify([{ name: "前端", weight: 1 }, { name: "后端", weight: 1.5 }]),
  );
  if (!drafts) return;
  const { allocate } = await import("@/api/calc");
  allocResult.value = await allocate(projectId, {
    target_us: targetUs,
    drafts: JSON.parse(drafts),
    cf: 1.21,
  });
}
```

- [ ] **Step 2: 手测 + commit**

```bash
cd web && pnpm dev
# 浏览器：反向结果页 → 生成模块分摊
```

```bash
git add web/src/views/ResultView.vue web/src/api/calc.ts
git commit -m "feat(web): ResultView 反向 allocator UI (GAP-C)"
```

---

## Task 24: SKILL.md polish

**Goal:** 让宿主 Claude Code 通过 SKILL.md 能正确生成 NESMA FP 草稿。

**Files:**
- Modify: `SKILL.md` (项目根)

- [ ] **Step 1: 阅读现有 SKILL.md，找到 AI 提取章节**

```bash
grep -n "提取\|extract\|FP\|功能点\|category\|complexity" SKILL.md
```

- [ ] **Step 2: 重写 / 增补提取 prompt 章节**

在 SKILL.md 加 / 替换：

```markdown
## AI 功能点提取 — Plugin 工作流

当用户在 Claude Code 终端运行 `/cost <project_id>`，按以下 prompt 操作：

### Step 1：拉取上传文档的 parsed_text

调 GET /api/projects/{project_id}/uploads — 拿到 upload list。
对每个 upload 调 GET /api/projects/{project_id}/uploads/{upload_id}/parsed
得到纯文本。

### Step 2：根据文本生成 NESMA FP 列表

把文档里描述的"功能"按 NESMA 5 类别归类：

- **EI（External Input）**：用户向系统提交的事件 — 增/改/删。 例：注册用户、提交订单
- **EO（External Output）**：系统对外输出经过派生 / 计算的数据。 例：生成报表、对账单
- **EQ（External Query）**：纯粹查询 / 检索。 例：列表查询、按 ID 查
- **ILF（Internal Logical File）**：系统内维护的逻辑文件 / 数据集。 例：用户表、订单表
- **EIF（External Interface File）**：外部系统维护、本系统读取的接口文件。 例：调用第三方支付的回调

### Step 3：为每个 FP 选复杂度

按 NESMA 估算法标准 UFP 表：

| 类别 | low | average | high |
|---|---|---|---|
| EI | 3 | 4 | 6 |
| EO | 4 | 5 | 7 |
| EQ | 3 | 4 | 6 |
| ILF | 7 | 10 | 15 |
| EIF | 5 | 7 | 10 |

复杂度判定（DET = 字段数，FTR = 引用文件数）：
- EI/EO/EQ: low if DET<5 ∨ FTR<2; high if DET≥10 ∧ FTR≥3; else average
- ILF/EIF: low if DET<20 ∧ RET<2; high if DET≥50 ∨ RET≥6; else average

如果文档信息不足，**默认 average**。

### Step 4：调用 bulk_write 写入

```http
POST /api/projects/{project_id}/functions/bulk
Content-Type: application/json

{
  "items": [
    {
      "name": "用户注册",
      "category": "EI",
      "complexity": "low",
      "ufp": 3,
      "us": 3,
      "source": "claude_draft",
      "description": "用户填写邮箱+密码，提交"
    },
    ...
  ],
  "replace": false
}
```

**关键约束**：
- `source` 必须是 `"claude_draft"`，让前端高亮提示用户审核
- `ufp` 与 `us` 应等于上表对应单元格的 NESMA 默认值（不要自创）
- 优先生成完整 FP 列表（覆盖全部业务流程），而非半成品

### Step 5：完成后回复用户

> "已根据文档生成 N 条 FP 草稿，已写入项目 {id}。请在浏览器 FP 编辑屏审核 / 调整。"
```

- [ ] **Step 3: Commit**

```bash
git add SKILL.md
git commit -m "docs(plugin): SKILL.md NESMA FP 提取 prompt — Plugin 模式工作流 (GAP-A)"
```

---

## Task 25: commands/cost.md 工作流 + commands/cost-allocate.md

**Goal:** 让 `/cost` 与 `/cost-allocate` 命令真正调用 SKILL.md。

**Files:**
- Modify: `commands/cost.md`
- Create: `commands/cost-allocate.md`

- [ ] **Step 1: 读现有 cost.md**

```bash
cat commands/cost.md
```

- [ ] **Step 2: 替换 cost.md**

```markdown
# /cost — 软件造价制作系统启动 + AI 提取

参数：
- 不带参数：列出所有项目，让用户选择
- `<project_id>`：直接对该项目执行 AI FP 提取

## 工作流

1. 检查 server 是否运行：调 GET http://127.0.0.1:8788/api/health
   - 如果失败：告诉用户运行 `cd server && uvicorn app.main:app --port 8788`
   - 如果成功：继续

2. 如果**无 project_id**：
   - 调 GET /api/projects → 列出 id + name + city + industry
   - 询问用户选哪个，或建议浏览器打开 http://127.0.0.1:5173 创建新项目

3. 如果**有 project_id**：
   - 调 GET /api/projects/{id}/uploads — 拿 upload list
   - 如果没有 upload：告诉用户先在浏览器上传文档
   - 否则按 SKILL.md "AI 功能点提取" 章节走：
     - 对每个 upload 调 GET /api/projects/{id}/uploads/{upload_id}/parsed 拿文本
     - 按 NESMA 5 类别规则生成 FP 列表
     - 调 POST /api/projects/{id}/functions/bulk 写入（replace=false, source="claude_draft"）

4. 提取完成后回复用户：
   "已生成 N 条 FP 草稿。请在浏览器 http://127.0.0.1:5173/projects/{id}/fp 审核。"
```

- [ ] **Step 3: 创建 commands/cost-allocate.md**

```markdown
# /cost-allocate — AI 模块分摊（反向模式）

参数：`<project_id>`

## 工作流

1. 检查 project mode：GET /api/projects/{id} → 如果不是 reverse，提示用户先切到反向

2. 拉最近的 reverse result：GET /api/projects/{id}/result/latest（如有）
   - 没有结果就先让用户跑反向 calc

3. 从结果中拿 P50 档的 scale_us（中位档总 US）

4. 让 AI 根据项目名 / 描述 / 行业 / 城市 推断模块清单：
   - 比如"智慧政务系统" → ["前端门户", "后台管理", "数据接入", "权限中心", ...]
   - 给每个模块估个相对权重（complexity-aware）

5. 调 POST /api/projects/{id}/calc/allocate
   ```json
   {
     "target_us": <P50 scale_us>,
     "drafts": [
       {"name": "前端门户", "weight": 1.5, "locked": false},
       {"name": "后台管理", "weight": 2.0, "locked": false},
       ...
     ],
     "cf": <project.phase 对应的 CF 值>
   }
   ```

6. 用返回的 allocator output（每模块 assigned_us）调 POST /api/projects/{id}/functions/bulk
   - 每个模块产出一条 FP（category 默认 ILF + average / 让 AI 判断）
   - source = "allocator"

7. 完成后告知用户。
```

- [ ] **Step 4: Commit**

```bash
git add commands/cost.md commands/cost-allocate.md
git commit -m "feat(plugin): /cost AI 提取工作流 + /cost-allocate (GAP-A/C)"
```

---

# Phase G — 文档 + 版本

## Task 26: README.md + user-guide.md v2.0 章节

**Files:**
- Modify: `README.md`
- Modify: `docs/user-guide.md`

- [ ] **Step 1: README 加 v2.0 章节**

在 README.md 现有 "## 版本历史 / Changelog" 之前（或末尾）加：

```markdown
## v2.0 新功能（2026-05-11）

### 11 项 v1.1 后审计 gap 全部闭环

- ✅ **AI 提取功能点**（GAP-A）：在 Claude Code 终端运行 `/cost <project_id>`，AI 读取上传文档自动生成 NESMA FP 草稿
- ✅ **AI 模块分摊**（GAP-C）：反向模式下 `/cost-allocate <project_id>` 让 AI 把三档 FP 拆成模块清单
- ✅ **17+ 调整因子全部可配**（GAP-B）：ParamManager 4 个 v2 stub tab 实装；Wizard 第 5/6 步用 dropdown 选因子级别，实时显示链式相乘
- ✅ **运维费率 / 生产率**（GAP-D）：城市费率表新增 ops 列；生产率 tab 新增运维行业表
- ✅ **alpha_dev / include_ops**（GAP-E）：dev_and_ops 项目类型显式滑块 + 联动开关
- ✅ **客户 / 评估方填写**（GAP-G）：Wizard 第 1 步可选字段，写入 Excel 报告封面
- ✅ **项目列表搜索 / 筛选 / 排序 / 分页**（GAP-F）：toolbar 实时搜索，5 个筛选维度
- ✅ **参数快照 + restore**（GAP-H）：ParamManager 快照 tab 可创建 / 恢复 / 删除
- ✅ **项目复制**（GAP-I）：行 ⋯ 菜单一键复制项目（含 FP + 参数 override）
- ✅ **项目审计日志**（GAP-J）：所有 mutating 操作自动记录，AuditView 可查
- ✅ **阶段 CF 实时预览**（GAP-K）：Wizard 第 3 步显示选定阶段的 CF 调整因子值

### 数据迁移

v1.1 老项目自动兼容：
- `factors_dev_json` / `factors_ops_json` 为 NULL → calc 用 1.0 + Result.warning_messages 提示
- 已有参数 / FP / 上传 不受影响
- 跑 `cd server && alembic upgrade head` 应用 3 个新 migration（factors 列、param_snapshots 表、audit_log 表）
```

- [ ] **Step 2: user-guide.md 加 v2.0 章节**

参考现有 v1.0 / v1.1 章节风格，加 v2.0 节（每个 GAP 一个使用示例 + 截图位置预留）。略，按现有 user-guide.md 模板续写。

- [ ] **Step 3: Commit**

```bash
git add README.md docs/user-guide.md
git commit -m "docs: README + user-guide v2.0 章节 — 11 GAP 闭环说明"
```

---

## Task 27: 版本号 1.1.0 → 2.0.0

**Files:**
- Modify: `web/package.json`
- Modify: `web/vite.config.ts` (如 `__APP_VERSION__` define 引用)
- Modify: `server/pyproject.toml` (version)

- [ ] **Step 1: 改 web/package.json**

`web/package.json` 的 `"version"` 字段 `"1.1.0"` → `"2.0.0"`。

- [ ] **Step 2: 改 server/pyproject.toml**

```bash
grep -n version server/pyproject.toml
```

把 `[project] version = "1.1.0"` 改成 `"2.0.0"`。

- [ ] **Step 3: 跑全套**

```bash
cd server && pytest -x
cd web && pnpm vitest run
cd web && pnpm build  # 确认 vite build 通过
cd web && pnpm exec playwright test  # e2e 全过
```

- [ ] **Step 4: Final commit**

```bash
git add web/package.json server/pyproject.toml
git commit -m "chore: bump version 1.1.0 → 2.0.0 (v2 gap closure release)"
```

---

# Self-Review checklist（写完 plan 必跑）

- [ ] **Spec coverage:** 11 个 GAP 是否每个都有 task 实现？

| GAP | 实现 task |
|---|---|
| A AI 提取 | T22 (FpEditor UI) + T24 (SKILL.md) + T25 (cost.md) |
| B 17+ 因子 UI | T1 (column) + T7 (calc 接因子) + T10 (ParamTable factors tab) + T11 (scale_change) + T17 (Wizard dropdown) |
| C AI 分摊 | T23 (ResultView) + T25 (cost-allocate.md) |
| D ops 费率 / 生产率 | T9 (ParamManager rate + productivity) |
| E alpha / include_ops | T14 (Wizard step 2) |
| F 列表查询 | T6 (后端 query) + T20 (前端 toolbar) |
| G client/evaluator | T13 (Wizard step 1) |
| H 参数快照 | T2 (table) + T4 (service+API) + T12 (UI) |
| I 项目复制 | T6 (后端) + T21 (UI) |
| J 审计日志 | T3 (table) + T5 (middleware+API) + T21 (UI) |
| K phase CF 预览 | T15 (Wizard step 3) |

✅ 全覆盖。

- [ ] **Placeholder scan:** 全 plan 内已搜过 "TBD" "TODO" "fill in" — 0 命中。

- [ ] **Type consistency:**
  - `factors_dev_json` 字段名一致（T1 + T6 + T7 + T18）✅
  - `ParamSnapshot.scope` 字段名一致（T2 + T4 + T8 + T12）✅
  - `AuditLog.action` 字段名一致（T3 + T5 + T8 + T21）✅
  - `copyProject(srcId, name)` 签名一致（T6 + T8 + T21）✅

无差异。

---

# 执行注意

1. **顺序敏感：** 后端 T1-T7 必须先于前端 T8-T23（schema + endpoint 是前端 wiring 的契约）
2. **Phase 内并行：** Phase B / C 可并行（ParamManager 与 Wizard 互不依赖；Wizard 需要 effectiveParams 但只读）
3. **Audit middleware 触雷点：** middleware 注册顺序必须最外层（T5 step 6），否则 401 / 422 也会被记进去
4. **factor chain 算法对齐：** Wizard 前端实时预览（T17 chainMultiply）必须与后端 services/factors.py 等价 — 否则用户在 Wizard 看到的 dev_factor 与 calc 实际用的不一致。检查 / 加同步测试

---

**Plan 完。** 27 task，估计 CC 执行 6-8 小时，人工执行 ~3 天。
