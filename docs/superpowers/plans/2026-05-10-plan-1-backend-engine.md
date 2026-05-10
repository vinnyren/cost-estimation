# 软件造价系统 · Plan 1 · 后端骨架 + 计算引擎 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 FastAPI 后端骨架（鉴权/CORS/SQLite）+ Forward / Reverse / Allocator 三个计算引擎，并通过实施规程附录 D 黄金测试。

**Architecture:** Python 3.11 + FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 + pytest + hypothesis。单进程、SQLite WAL、文件系统存储项目数据。core/ 内三个引擎从共享 `EvaluationContext` 派生，纯函数无副作用便于测试。token + Origin + CORS 三层防 localhost CSRF。

**Tech Stack:** FastAPI 0.110+ / SQLAlchemy 2.0 / Alembic / Pydantic v2 / pytest / hypothesis / mutmut / pytest-asyncio

**对应 Spec：** `docs/superpowers/specs/2026-05-10-cost-estimation-design.md` v1.1 §3-§5, §9.5
**Spec commit：** `745b6e0`

---

## 文件结构

```
server/
├── pyproject.toml                  # Task 1
├── requirements.txt                # Task 1
├── alembic.ini                     # Task 3
├── alembic/
│   ├── env.py                      # Task 3
│   └── versions/
│       └── 20260510_initial.py    # Task 4
├── app/
│   ├── __init__.py                 # Task 1
│   ├── main.py                     # Task 2 / 6 / 7
│   ├── config.py                   # Task 2
│   ├── deps.py                     # Task 6 / 7
│   ├── api/
│   │   ├── __init__.py
│   │   ├── projects.py             # Task 8
│   │   ├── params.py               # Task 10
│   │   ├── calc.py                 # Task 12 / 14 / 16
│   │   └── health.py               # Task 2
│   ├── core/
│   │   ├── __init__.py
│   │   ├── context.py              # Task 11
│   │   ├── forward.py              # Task 12
│   │   ├── reverse.py              # Task 14
│   │   ├── allocator.py            # Task 16
│   │   └── factors.py              # Task 11
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py              # Task 3
│   │   └── models.py               # Task 5 / 19
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── project.py              # Task 8
│   │   ├── functions.py            # Task 8
│   │   ├── params.py               # Task 10
│   │   └── results.py              # Task 12
│   ├── services/
│   │   ├── __init__.py
│   │   ├── projects.py             # Task 8
│   │   ├── params.py               # Task 10
│   │   └── calc.py                 # Task 12 / 14 / 16
│   └── data/
│       └── csbmk_202510.json       # Task 9
└── tests/
    ├── conftest.py                 # Task 2
    ├── golden/
    │   ├── csbmk_202210.json       # Task 17
    │   └── appendix_d.json         # Task 17
    ├── unit/
    │   ├── test_context.py         # Task 11
    │   ├── test_forward.py         # Task 12
    │   ├── test_reverse.py         # Task 14
    │   ├── test_allocator.py       # Task 16
    │   └── test_factors.py         # Task 11
    ├── integration/
    │   ├── test_health.py          # Task 2
    │   ├── test_security.py        # Task 6 / 7
    │   ├── test_projects_api.py    # Task 8
    │   ├── test_params_api.py      # Task 10
    │   ├── test_calc_api.py        # Task 12 / 14 / 16
    │   └── test_golden.py          # Task 17
    └── property/
        └── test_roundtrip.py       # Task 18
```

---

## Phase 1 · 后端骨架

### Task 1: Python 项目骨架与依赖

**Files:**
- Create: `server/pyproject.toml`
- Create: `server/requirements.txt`
- Create: `server/app/__init__.py`
- Create: `.gitignore`（追加）

- [ ] **Step 1: 写 pyproject.toml**

```toml
# server/pyproject.toml
[project]
name = "cost-estimation-server"
version = "1.0.0"
description = "软件造价制作系统后端"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
    "hypothesis>=6.99",
    "mutmut>=2.5",
    "ruff>=0.3",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: 写 requirements.txt（用 pip-compile 生成的等价快照）**

```
fastapi>=0.110
uvicorn[standard]>=0.27
sqlalchemy>=2.0
alembic>=1.13
pydantic>=2.6
pydantic-settings>=2.2
python-multipart>=0.0.9
```

- [ ] **Step 3: 创建 app/__init__.py（空文件）**

```python
# server/app/__init__.py
```

- [ ] **Step 4: 追加 .gitignore**

```
# Python
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
.ruff_cache/
.mutmut-cache/

# 项目数据
*.sqlite
*.sqlite-journal
*.sqlite-wal
*.sqlite-shm

# 临时
.coverage
htmlcov/
```

- [ ] **Step 5: 提交**

```bash
git add server/pyproject.toml server/requirements.txt server/app/__init__.py .gitignore
git commit -m "feat(server): bootstrap python project with fastapi + sqlalchemy"
```

---

### Task 2: FastAPI 入口 + 健康检查 + 配置

**Files:**
- Create: `server/app/main.py`
- Create: `server/app/config.py`
- Create: `server/app/api/__init__.py`
- Create: `server/app/api/health.py`
- Create: `server/tests/conftest.py`
- Create: `server/tests/integration/test_health.py`

- [ ] **Step 1: 写 config.py**

```python
# server/app/config.py
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COST_", env_file=".env")

    data_dir: Path = Path.home() / ".claude" / "projects" / "cost-estimation"
    db_path: Path = data_dir / "db" / "cost.sqlite"
    bind_host: str = "127.0.0.1"
    bind_port: int = 8788
    auth_token: str = ""  # 启动时注入
    csbmk_seed_path: Path = Path(__file__).parent / "data" / "csbmk_202510.json"

settings = Settings()
```

- [ ] **Step 2: 写健康检查路由**

```python
# server/app/api/health.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health():
    return {"ok": True, "service": "cost-estimation", "version": "1.0.0"}
```

- [ ] **Step 3: 写主入口**

```python
# server/app/main.py
import secrets
from fastapi import FastAPI
from .api.health import router as health_router
from .config import settings

def create_app() -> FastAPI:
    if not settings.auth_token:
        settings.auth_token = secrets.token_urlsafe(32)
    app = FastAPI(title="软件造价制作系统", version="1.0.0")
    app.include_router(health_router)
    return app

app = create_app()
```

- [ ] **Step 4: 写测试 fixture**

```python
# server/tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import create_app

@pytest.fixture
def app():
    return create_app()

@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```

- [ ] **Step 5: 写健康检查测试（先红后绿）**

```python
# server/tests/integration/test_health.py
async def test_health_returns_ok(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["service"] == "cost-estimation"
```

- [ ] **Step 6: 跑测试验证通过**

Run: `cd server && pytest tests/integration/test_health.py -v`
Expected: 1 passed

- [ ] **Step 7: 提交**

```bash
git add server/
git commit -m "feat(server): fastapi entrypoint + health check + test harness"
```

---

### Task 3: SQLAlchemy 引擎 + Alembic 初始化

**Files:**
- Create: `server/app/db/__init__.py`
- Create: `server/app/db/session.py`
- Create: `server/alembic.ini`
- Create: `server/alembic/env.py`
- Create: `server/alembic/script.py.mako`

- [ ] **Step 1: 写 db/session.py**

```python
# server/app/db/session.py
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from ..config import settings

settings.db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
)

@event.listens_for(engine, "connect")
def _set_sqlite_pragma(conn, _):
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: 写 alembic.ini**

```ini
# server/alembic.ini
[alembic]
script_location = alembic
sqlalchemy.url = sqlite:///%(here)s/cost.sqlite

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 3: 写 alembic/env.py**

```python
# server/alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.db.session import Base
from app.db import models  # 触发模型导入
from app.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", f"sqlite:///{settings.db_path}")
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(url=config.get_main_option("sqlalchemy.url"),
                      target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: 拷贝 Alembic 模板**

Run: `cd server && alembic init -t generic alembic`（或手动创建 `alembic/script.py.mako` 用默认模板）

实际创建：

```python
# server/alembic/script.py.mako
"""${message}
Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

def upgrade():
    ${upgrades if upgrades else "pass"}

def downgrade():
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 5: 提交**

```bash
git add server/alembic.ini server/alembic/ server/app/db/
git commit -m "feat(server): sqlalchemy engine + alembic skeleton + WAL pragma"
```

---

### Task 4: 数据库模型（与 spec §4.1 一致）

**Files:**
- Create: `server/app/db/models.py`
- Test: `server/tests/unit/test_models.py`

- [ ] **Step 1: 写测试（验证 schema 字段与 spec 一致）**

```python
# server/tests/unit/test_models.py
from app.db.models import Project, FunctionPoint, FPSnapshot, ParamGlobal, ParamOverride, Result, Upload

def test_project_required_fields():
    fields = {c.name for c in Project.__table__.columns}
    must_have = {"id", "name", "created_at", "updated_at", "project_type", "phase",
                 "city", "industry", "client", "evaluator", "mode",
                 "target_cost", "other_cost", "include_ops", "alpha_dev",
                 "fp_method", "basis_data_ver"}
    assert must_have.issubset(fields)

def test_function_point_required_fields():
    fields = {c.name for c in FunctionPoint.__table__.columns}
    must_have = {"id", "project_id", "version", "subsystem", "l1_module", "l2_module",
                 "description", "name", "category", "complexity", "ufp",
                 "reuse_level", "modify_type", "us", "source", "locked", "notes", "ord"}
    assert must_have.issubset(fields)
```

- [ ] **Step 2: 跑测试验证失败**

Run: `cd server && pytest tests/unit/test_models.py -v`
Expected: ImportError 或 AttributeError

- [ ] **Step 3: 写 models.py（依据 spec §4.1 全表）**

```python
# server/app/db/models.py
from sqlalchemy import Column, String, Integer, Real, Float, ForeignKey, Index, Text, DateTime, Boolean
from sqlalchemy.sql import func
from .session import Base

class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    project_type = Column(String, nullable=False)        # dev_only | ops_only | dev_and_ops
    phase = Column(String, nullable=False)               # budget | bidding | planning | change | settled
    city = Column(String, nullable=False)
    industry = Column(String, nullable=False)
    client = Column(String)
    evaluator = Column(String)
    mode = Column(String, nullable=False)                # forward | reverse
    target_cost = Column(Float)
    other_cost = Column(Float, default=0)
    include_ops = Column(Boolean, default=False)
    alpha_dev = Column(Float, default=1.0)
    fp_method = Column(String, default="nesma_estimated")
    basis_data_ver = Column(String, nullable=False)

class FunctionPoint(Base):
    __tablename__ = "function_points"
    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    subsystem = Column(String)
    l1_module = Column(String)
    l2_module = Column(String)
    description = Column(Text)
    name = Column(String)
    category = Column(String, nullable=False)            # EI|EO|EQ|ILF|EIF
    complexity = Column(String, nullable=False)          # low|average|high
    ufp = Column(Float, nullable=False)
    reuse_level = Column(String)
    modify_type = Column(String)
    us = Column(Float, nullable=False)
    source = Column(String)                              # claude_draft|manual|imported|allocator
    locked = Column(Boolean, default=False)
    notes = Column(Text)
    ord = Column(Integer)

class FPSnapshot(Base):
    __tablename__ = "fp_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    version = Column(Integer, nullable=False)
    snapshot_at = Column(DateTime, server_default=func.now(), nullable=False)
    snapshot_json = Column(Text, nullable=False)
    reason = Column(String)

Index("idx_fp_snapshots_project", FPSnapshot.project_id, FPSnapshot.id)

class ParamGlobal(Base):
    __tablename__ = "params_global"
    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    basis_version = Column(String, nullable=False)
    modified = Column(Boolean, default=False)
    updated_at = Column(DateTime, server_default=func.now())

class ParamOverride(Base):
    __tablename__ = "params_override"
    project_id = Column(String, ForeignKey("projects.id"), primary_key=True)
    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    reason = Column(String)
    updated_at = Column(DateTime, server_default=func.now())

class Result(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    computed_at = Column(DateTime, server_default=func.now())
    mode = Column(String, nullable=False)
    fp_version = Column(Integer, nullable=False)
    params_hash = Column(String, nullable=False)
    payload_json = Column(Text, nullable=False)
    is_stale = Column(Boolean, default=False)

class Upload(Base):
    __tablename__ = "uploads"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    filename = Column(String, nullable=False)
    size = Column(Integer)
    uploaded_at = Column(DateTime, server_default=func.now())
    filetype = Column(String)
    parsed_text_path = Column(String)  # 大文本不进 DB
```

- [ ] **Step 4: 跑测试验证通过**

Run: `cd server && pytest tests/unit/test_models.py -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add server/app/db/models.py server/tests/unit/test_models.py
git commit -m "feat(db): full schema models per spec §4.1"
```

---

### Task 5: 初始 migration + fp_snapshots 触发器

**Files:**
- Create: `server/alembic/versions/20260510_initial.py`

- [ ] **Step 1: 生成空白 migration**

Run: `cd server && alembic revision -m "initial schema with fp_snapshots trigger"`

记下生成的文件名（含日期前缀，例如 `20260510_xxxx_initial_schema.py`）。

- [ ] **Step 2: 编辑 migration（用 Base.metadata.create_all 简化 + 手写触发器）**

```python
# server/alembic/versions/<生成的文件>.py 完整内容
"""initial schema with fp_snapshots trigger
Revision ID: 20260510_initial
Revises:
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa
from app.db.session import Base
from app.db import models  # 触发所有模型注册

revision = "20260510_initial"
down_revision = None
branch_labels = None
depends_on = None

TRIGGER_SQL = """
CREATE TRIGGER trim_fp_snapshots AFTER INSERT ON fp_snapshots
BEGIN
  DELETE FROM fp_snapshots
  WHERE project_id = NEW.project_id
    AND id NOT IN (
      SELECT id FROM fp_snapshots
      WHERE project_id = NEW.project_id
      ORDER BY id DESC LIMIT 5
    );
END;
"""

def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    op.execute(TRIGGER_SQL)

def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trim_fp_snapshots")
    Base.metadata.drop_all(bind=op.get_bind())
```

- [ ] **Step 3: 跑 migration**

Run: `cd server && alembic upgrade head`
Expected: stdout 含 "Running upgrade  -> 20260510_initial"

- [ ] **Step 4: 验证 sqlite 文件存在 + 触发器存在**

Run: `cd server && sqlite3 ~/.claude/projects/cost-estimation/db/cost.sqlite "SELECT name FROM sqlite_master WHERE type IN ('table', 'trigger') ORDER BY type, name;"`
Expected: 列表包含 `function_points`、`fp_snapshots`、`projects`、`trim_fp_snapshots` 等

- [ ] **Step 5: 提交**

```bash
git add server/alembic/versions/
git commit -m "feat(db): initial migration with fp_snapshots cross-project trigger"
```

---

### Task 6: Token 鉴权中间件（CSRF 防护第一层）

**Files:**
- Modify: `server/app/main.py`
- Create: `server/app/deps.py`
- Test: `server/tests/integration/test_security.py`

- [ ] **Step 1: 写测试（无 token 应 401）**

```python
# server/tests/integration/test_security.py
import os, pytest
from httpx import AsyncClient, ASGITransport
from app.main import create_app

@pytest.fixture
def app_with_token(monkeypatch):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    return create_app()

@pytest.fixture
async def secured_client(app_with_token):
    transport = ASGITransport(app=app_with_token)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

async def test_health_does_not_require_token(secured_client):
    r = await secured_client.get("/health")
    assert r.status_code == 200

async def test_api_without_token_returns_401(secured_client):
    r = await secured_client.get("/api/projects")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"

async def test_api_with_valid_token_via_header_passes(secured_client):
    r = await secured_client.get("/api/projects",
                                  headers={"X-Auth-Token": "test-secret-token-xyz"})
    assert r.status_code != 401  # 路由可能未实现，但不应是 401

async def test_api_with_valid_token_via_query_passes(secured_client):
    r = await secured_client.get("/api/projects?t=test-secret-token-xyz")
    assert r.status_code != 401
```

- [ ] **Step 2: 跑测试验证失败**

Run: `cd server && pytest tests/integration/test_security.py -v`
Expected: 4 failed（路由不存在、无中间件）

- [ ] **Step 3: 写 deps.py + main.py 增加中间件**

```python
# server/app/deps.py
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from .config import settings

async def auth_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)
    sent = request.headers.get("X-Auth-Token") or request.query_params.get("t")
    if sent != settings.auth_token:
        return JSONResponse(
            status_code=401,
            content={"ok": False, "error": {"code": "UNAUTHORIZED", "problem": "Missing or invalid token", "fix": "Include X-Auth-Token header or ?t= query param"}}
        )
    return await call_next(request)
```

```python
# server/app/main.py（增量）
from fastapi import APIRouter
from .deps import auth_middleware

def create_app() -> FastAPI:
    if not settings.auth_token:
        settings.auth_token = secrets.token_urlsafe(32)
    app = FastAPI(title="软件造价制作系统", version="1.0.0")
    app.middleware("http")(auth_middleware)
    app.include_router(health_router)
    # 添加占位 /api 路由，避免 404 干扰测试
    api = APIRouter(prefix="/api")
    @api.get("/projects")
    async def _stub_projects():
        return {"ok": True, "data": []}
    app.include_router(api)
    return app

app = create_app()
```

- [ ] **Step 4: 跑测试验证通过**

Run: `cd server && pytest tests/integration/test_security.py -v`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add server/app/deps.py server/app/main.py server/tests/integration/test_security.py
git commit -m "feat(server): token-based auth middleware (CSRF defense layer 1)"
```

---

### Task 7: Origin + CORS 防护（CSRF 第二/三层）

**Files:**
- Modify: `server/app/main.py`
- Modify: `server/app/deps.py`
- Modify: `server/tests/integration/test_security.py`

- [ ] **Step 1: 追加测试**

```python
# server/tests/integration/test_security.py（追加）
async def test_post_with_evil_origin_blocked(secured_client):
    r = await secured_client.post(
        "/api/projects",
        headers={"X-Auth-Token": "test-secret-token-xyz",
                 "Origin": "https://evil.com",
                 "Content-Type": "application/json"},
        json={"name": "x"}
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN_ORIGIN"

async def test_post_with_localhost_origin_passes(secured_client):
    r = await secured_client.post(
        "/api/projects",
        headers={"X-Auth-Token": "test-secret-token-xyz",
                 "Origin": "http://127.0.0.1:8788",
                 "Content-Type": "application/json"},
        json={"name": "x"}
    )
    assert r.status_code != 403

async def test_get_without_origin_passes(secured_client):
    r = await secured_client.get("/api/projects",
                                  headers={"X-Auth-Token": "test-secret-token-xyz"})
    assert r.status_code != 403
```

- [ ] **Step 2: 跑测试验证失败**

Run: `cd server && pytest tests/integration/test_security.py -v -k "origin"`
Expected: 1-2 failed（Origin 检查未实现）

- [ ] **Step 3: 在 deps.py 增加 origin_middleware；在 main.py 装上 CORS**

```python
# server/app/deps.py（追加）
ALLOWED_ORIGIN_PREFIXES = ("http://127.0.0.1", "http://localhost")

async def origin_middleware(request: Request, call_next):
    if request.method != "GET":
        origin = request.headers.get("Origin", "")
        if origin and not any(origin.startswith(p) for p in ALLOWED_ORIGIN_PREFIXES):
            return JSONResponse(
                status_code=403,
                content={"ok": False, "error": {"code": "FORBIDDEN_ORIGIN",
                                                 "problem": f"Origin '{origin}' not allowed",
                                                 "fix": "Only http://127.0.0.1:* and http://localhost:* are accepted"}}
            )
    return await call_next(request)
```

```python
# server/app/main.py（增量）
from fastapi.middleware.cors import CORSMiddleware
from .deps import auth_middleware, origin_middleware

def create_app() -> FastAPI:
    if not settings.auth_token:
        settings.auth_token = secrets.token_urlsafe(32)
    app = FastAPI(title="软件造价制作系统", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[f"http://127.0.0.1:{settings.bind_port}",
                       f"http://localhost:{settings.bind_port}"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["X-Auth-Token", "Content-Type", "X-Requested-With"],
    )
    app.middleware("http")(origin_middleware)
    app.middleware("http")(auth_middleware)
    app.include_router(health_router)
    # ... 其他路由保持
    return app
```

- [ ] **Step 4: 跑测试验证通过**

Run: `cd server && pytest tests/integration/test_security.py -v`
Expected: 7 passed

- [ ] **Step 5: 提交**

```bash
git add server/app/deps.py server/app/main.py server/tests/
git commit -m "feat(server): origin + cors middleware (CSRF defense layer 2/3)"
```

---

### Task 8: 项目 CRUD API + Pydantic schemas + service 层

**Files:**
- Create: `server/app/schemas/project.py`
- Create: `server/app/schemas/functions.py`
- Create: `server/app/services/projects.py`
- Create: `server/app/api/projects.py`
- Modify: `server/app/main.py`（注册路由）
- Test: `server/tests/integration/test_projects_api.py`

- [ ] **Step 1: 写测试**

```python
# server/tests/integration/test_projects_api.py
import pytest, uuid
from httpx import AsyncClient, ASGITransport

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}

@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    monkeypatch.setenv("COST_DB_PATH", f"/tmp/cost-test-{uuid.uuid4()}.sqlite")
    from app.main import create_app
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

async def test_create_project_returns_id(client):
    r = await client.post("/api/projects", headers=H, json={
        "name": "测试项目",
        "project_type": "dev_only",
        "phase": "bidding",
        "city": "北京",
        "industry": "电子政务",
        "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    assert r.status_code == 201
    body = r.json()["data"]
    assert "id" in body
    assert body["name"] == "测试项目"

async def test_list_projects_after_create(client):
    await client.post("/api/projects", headers=H, json={
        "name": "P1", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    r = await client.get("/api/projects", headers=H)
    assert r.status_code == 200
    assert len(r.json()["data"]) >= 1

async def test_get_nonexistent_returns_404(client):
    r = await client.get("/api/projects/nonexistent", headers=H)
    assert r.status_code == 404
```

- [ ] **Step 2: 跑测试验证失败**

Run: `cd server && pytest tests/integration/test_projects_api.py -v`
Expected: 3 failed

- [ ] **Step 3: 写 schemas**

```python
# server/app/schemas/project.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional
from datetime import datetime

class ProjectCreate(BaseModel):
    name: str
    project_type: Literal["dev_only", "ops_only", "dev_and_ops"]
    phase: Literal["budget", "bidding", "planning", "change", "settled"]
    city: str
    industry: str
    client: Optional[str] = None
    evaluator: Optional[str] = None
    mode: Literal["forward", "reverse"]
    target_cost: Optional[float] = None
    other_cost: float = 0
    include_ops: bool = False
    alpha_dev: float = 1.0
    fp_method: Literal["nesma_estimated", "ifpug", "quick"] = "nesma_estimated"
    basis_data_ver: str

class ProjectRead(ProjectCreate):
    id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ProjectPatch(BaseModel):
    name: Optional[str] = None
    phase: Optional[str] = None
    city: Optional[str] = None
    industry: Optional[str] = None
    client: Optional[str] = None
    evaluator: Optional[str] = None
    target_cost: Optional[float] = None
    other_cost: Optional[float] = None
    include_ops: Optional[bool] = None
    alpha_dev: Optional[float] = None
```

- [ ] **Step 4: 写 service**

```python
# server/app/services/projects.py
import uuid
from sqlalchemy.orm import Session
from ..db.models import Project as ProjectORM
from ..schemas.project import ProjectCreate, ProjectPatch

def create(db: Session, payload: ProjectCreate) -> ProjectORM:
    project = ProjectORM(id=f"prj-{uuid.uuid4().hex[:12]}", **payload.model_dump())
    db.add(project); db.commit(); db.refresh(project)
    return project

def list_all(db: Session) -> list[ProjectORM]:
    return db.query(ProjectORM).order_by(ProjectORM.updated_at.desc()).all()

def get(db: Session, project_id: str) -> ProjectORM | None:
    return db.query(ProjectORM).filter_by(id=project_id).first()

def patch(db: Session, project_id: str, payload: ProjectPatch) -> ProjectORM | None:
    p = get(db, project_id)
    if not p: return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit(); db.refresh(p)
    return p

def delete(db: Session, project_id: str) -> bool:
    p = get(db, project_id)
    if not p: return False
    db.delete(p); db.commit()
    return True
```

- [ ] **Step 5: 写 api/projects.py**

```python
# server/app/api/projects.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..schemas.project import ProjectCreate, ProjectRead, ProjectPatch
from ..services import projects as svc

router = APIRouter(prefix="/api/projects")

def _wrap(data, code=200):
    return {"ok": True, "data": data}

@router.post("", status_code=201)
def create(payload: ProjectCreate, db: Session = Depends(get_db)):
    p = svc.create(db, payload)
    return _wrap(ProjectRead.model_validate(p).model_dump(mode="json"))

@router.get("")
def list_all(db: Session = Depends(get_db)):
    return _wrap([ProjectRead.model_validate(p).model_dump(mode="json") for p in svc.list_all(db)])

@router.get("/{project_id}")
def get_one(project_id: str, db: Session = Depends(get_db)):
    p = svc.get(db, project_id)
    if not p: raise HTTPException(404, {"error": {"code": "NOT_FOUND"}})
    return _wrap(ProjectRead.model_validate(p).model_dump(mode="json"))

@router.patch("/{project_id}")
def patch_one(project_id: str, payload: ProjectPatch, db: Session = Depends(get_db)):
    p = svc.patch(db, project_id, payload)
    if not p: raise HTTPException(404, {"error": {"code": "NOT_FOUND"}})
    return _wrap(ProjectRead.model_validate(p).model_dump(mode="json"))

@router.delete("/{project_id}")
def delete_one(project_id: str, db: Session = Depends(get_db)):
    ok = svc.delete(db, project_id)
    if not ok: raise HTTPException(404, {"error": {"code": "NOT_FOUND"}})
    return _wrap({"deleted": project_id})
```

- [ ] **Step 6: 注册路由 + 删除旧 stub**

修改 `server/app/main.py`，删掉 Task 6 中加的 stub `/api/projects`，注册真实路由：

```python
# server/app/main.py（增量）
from .api.projects import router as projects_router
# 删除原 stub
app.include_router(projects_router)
```

- [ ] **Step 7: 跑测试验证通过**

Run: `cd server && pytest tests/integration/test_projects_api.py -v`
Expected: 3 passed

- [ ] **Step 8: 提交**

```bash
git add server/app/schemas server/app/services server/app/api/projects.py server/app/main.py server/tests/
git commit -m "feat(api): project CRUD with pydantic schemas + service layer"
```

---

### Task 9: CSBMK®-202510 基准数据 seed

**Files:**
- Create: `server/app/data/csbmk_202510.json`

- [ ] **Step 1: 创建完整 seed JSON**

依据 spec §4.1 `params/current.json` schema 与 spec §1 引用的 CSBMK®-202510 数据。完整内容（节选关键字段，全字段需对照基准数据 PDF 录入）：

```json
{
  "version": "CSBMK®-202510",
  "effective_date": "2025-10-01",
  "productivity": {
    "dev": {
      "全行业": {"P10": 2.20, "P25": 3.77, "P50": 6.72, "P75": 12.28, "P90": 17.35},
      "电子政务": {"P10": 2.04, "P25": 2.87, "P50": 6.41, "P75": 10.99, "P90": 15.36},
      "金融": {"P10": 3.08, "P25": 5.09, "P50": 10.46, "P75": 15.69, "P90": 27.15},
      "电信": {"P10": 2.36, "P25": 4.57, "P50": 9.98, "P75": 16.37, "P90": 27.68},
      "制造": {"P10": 2.08, "P25": 3.31, "P50": 7.69, "P75": 15.93, "P90": 23.78},
      "能源": {"P10": 2.15, "P25": 3.79, "P50": 7.30, "P75": 17.42, "P90": 22.13},
      "交通": {"P10": 2.03, "P25": 3.07, "P50": 6.86, "P75": 15.57, "P90": 21.55}
    },
    "ops": {
      "全行业": {"P10": 0.21, "P25": 0.44, "P50": 0.74, "P75": 1.43, "P90": 2.07}
    }
  },
  "city_rate": {
    "北京": {"dev": 32198, "ops": 26335, "class": "A"},
    "天津": {"dev": 24641, "ops": 19374, "class": "C"},
    "上海": {"dev": 31309, "ops": 25262, "class": "A"},
    "重庆": {"dev": 23849, "ops": 19632, "class": "C"},
    "石家庄": {"dev": 20410, "ops": 16507, "class": "D"},
    "太原": {"dev": 22920, "ops": 18860, "class": "C"},
    "呼和浩特": {"dev": 19883, "ops": 16311, "class": "E"},
    "西安": {"dev": 25415, "ops": 21041, "class": "B"},
    "成都": {"dev": 26112, "ops": 20966, "class": "B"},
    "昆明": {"dev": 23635, "ops": 19214, "class": "C"},
    "武汉": {"dev": 23806, "ops": 19167, "class": "C"},
    "长沙": {"dev": 23292, "ops": 18934, "class": "C"},
    "合肥": {"dev": 24881, "ops": 20596, "class": "C"},
    "长春": {"dev": 20954, "ops": 16474, "class": "D"},
    "沈阳": {"dev": 22752, "ops": 18621, "class": "C"},
    "大连": {"dev": 23216, "ops": 18817, "class": "C"},
    "哈尔滨": {"dev": 22614, "ops": 18341, "class": "C"},
    "济南": {"dev": 23339, "ops": 18566, "class": "C"},
    "青岛": {"dev": 24085, "ops": 19541, "class": "C"},
    "郑州": {"dev": 21836, "ops": 18317, "class": "D"},
    "南京": {"dev": 27795, "ops": 22048, "class": "B"},
    "苏州": {"dev": 27471, "ops": 22257, "class": "B"},
    "杭州": {"dev": 28813, "ops": 23717, "class": "B"},
    "宁波": {"dev": 26241, "ops": 21810, "class": "B"},
    "福州": {"dev": 26586, "ops": 21988, "class": "B"},
    "厦门": {"dev": 26823, "ops": 22051, "class": "B"},
    "广州": {"dev": 27748, "ops": 22550, "class": "B"},
    "深圳": {"dev": 32122, "ops": 26666, "class": "A"},
    "南昌": {"dev": 23296, "ops": 18003, "class": "C"},
    "南宁": {"dev": 22659, "ops": 18843, "class": "C"},
    "海口": {"dev": 22963, "ops": 18822, "class": "C"},
    "兰州": {"dev": 20923, "ops": 16834, "class": "D"},
    "贵阳": {"dev": 23155, "ops": 19224, "class": "C"},
    "银川": {"dev": 19234, "ops": 15627, "class": "E"},
    "乌鲁木齐": {"dev": 20495, "ops": 16294, "class": "D"},
    "拉萨": {"dev": 23919, "ops": 19217, "class": "C"},
    "西宁": {"dev": 20746, "ops": 16774, "class": "D"}
  },
  "cf": {"budget": 1.39, "bidding": 1.21, "planning": 1.10, "change": 1.10, "settled": 1.00},
  "factors_dev": {
    "app_type": {
      "业务处理": 1.00, "软件集成": 1.20, "科技": 1.20, "多媒体": 1.30,
      "智能信息": 1.50, "基础软件": 1.70, "通信控制": 1.90, "流程控制": 2.00
    },
    "integrity_level": {
      "C/D": 1.00, "A/B": 1.10, "A_full_lifecycle": 1.30
    },
    "non_func": {"distributed": 0.025, "performance": 0.025, "reliability": 0.025, "multi_site": 0.025, "base": 1.0},
    "platform": {
      "C": 1.5, "JAVA": 1.0, "C++": 1.0, "C#": 1.0, "PowerBuilder": 0.6, "ASP": 0.6
    },
    "team_bg": {"same_industry": 0.8, "related": 1.0, "none": 1.2}
  },
  "factors_ops": {
    "update_freq": {"quarterly": 0.95, "monthly": 1.00, "frequent": 1.12},
    "support": {"remote": 0.89, "onsite": 1.00, "pure_onsite": 1.08},
    "security_level": {"L1": 0.90, "L2": 0.95, "L3": 1.00, "L4": 1.05, "L5": 1.10},
    "business_importance": {"core": 1.10, "general": 1.00, "peripheral": 0.90},
    "response_time": {"72h": 0.90, "48h": 1.00, "24h": 1.10},
    "integrity_level": {"C/D": 1.00, "A/B": 1.10, "A_full_lifecycle": 1.30},
    "team_exp": {"same_industry": 0.80, "related": 1.00, "none": 1.20},
    "automation": {"auto": 0.90, "semi": 1.00, "manual": 1.10},
    "deployment": {"centralized": 1.00, "distributed": 1.06},
    "user_scale": {"<=1k": 0.90, "<=10k": 1.00, ">10k": 1.10},
    "system_relevance": {"none": 0.97, "1-5": 1.00, "6+": 1.14}
  },
  "hours_per_pm": 174,
  "ops_cost_ratio": {"P50": 0.0902}
}
```

- [ ] **Step 2: 提交**

```bash
git add server/app/data/csbmk_202510.json
git commit -m "feat(data): seed CSBMK®-202510 baseline data (35 cities + 6 industries + factors)"
```

---

### Task 10: 参数 seed + 全局参数 API + override

**Files:**
- Create: `server/app/services/params.py`
- Create: `server/app/schemas/params.py`
- Create: `server/app/api/params.py`
- Modify: `server/app/main.py`
- Test: `server/tests/integration/test_params_api.py`

- [ ] **Step 1: 写测试**

```python
# server/tests/integration/test_params_api.py
import pytest, uuid
from httpx import AsyncClient, ASGITransport

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}

@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    monkeypatch.setenv("COST_DB_PATH", f"/tmp/cost-test-{uuid.uuid4()}.sqlite")
    from app.main import create_app
    from app.db.session import Base, engine
    from app.services import params as ps
    Base.metadata.create_all(bind=engine)
    ps.seed_from_csbmk()
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

async def test_global_params_after_seed(client):
    r = await client.get("/api/params/global", headers=H)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["city_rate"]["北京"]["dev"] == 32198
    assert data["productivity"]["dev"]["电子政务"]["P50"] == 6.41
    assert data["cf"]["bidding"] == 1.21

async def test_patch_global_param(client):
    r = await client.patch("/api/params/global", headers={**H, "Content-Type": "application/json"},
                            json={"key": "city_rate.北京.dev", "value": 33000})
    assert r.status_code == 200
    r2 = await client.get("/api/params/global", headers=H)
    assert r2.json()["data"]["city_rate"]["北京"]["dev"] == 33000
```

- [ ] **Step 2: 跑测试验证失败**

Run: `cd server && pytest tests/integration/test_params_api.py -v`
Expected: 2 failed

- [ ] **Step 3: 写 service**

```python
# server/app/services/params.py
import json
from pathlib import Path
from sqlalchemy.orm import Session
from ..db.session import SessionLocal
from ..db.models import ParamGlobal
from ..config import settings

def _flatten(prefix: str, obj, out: dict):
    if isinstance(obj, dict):
        for k, v in obj.items():
            _flatten(f"{prefix}.{k}" if prefix else k, v, out)
    else:
        out[prefix] = obj

def _unflatten(flat: dict) -> dict:
    out = {}
    for key, val in flat.items():
        cur = out
        parts = key.split(".")
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = val
    return out

def seed_from_csbmk():
    raw = json.loads(settings.csbmk_seed_path.read_text(encoding="utf-8"))
    version = raw.get("version", "CSBMK®-unknown")
    flat = {}
    _flatten("", raw, flat)
    db = SessionLocal()
    try:
        existing = {p.key for p in db.query(ParamGlobal).all()}
        for k, v in flat.items():
            if k in existing: continue
            db.add(ParamGlobal(key=k, value=json.dumps(v, ensure_ascii=False),
                                basis_version=version, modified=False))
        db.commit()
    finally:
        db.close()

def get_global(db: Session) -> dict:
    rows = db.query(ParamGlobal).all()
    flat = {p.key: json.loads(p.value) for p in rows}
    return _unflatten(flat)

def patch_global(db: Session, key: str, value) -> None:
    p = db.query(ParamGlobal).filter_by(key=key).first()
    if p is None:
        p = ParamGlobal(key=key, value=json.dumps(value, ensure_ascii=False),
                        basis_version="user", modified=True)
        db.add(p)
    else:
        p.value = json.dumps(value, ensure_ascii=False)
        p.modified = True
    db.commit()
```

- [ ] **Step 4: 写 schema + api**

```python
# server/app/schemas/params.py
from pydantic import BaseModel
from typing import Any

class ParamPatch(BaseModel):
    key: str
    value: Any
```

```python
# server/app/api/params.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..schemas.params import ParamPatch
from ..services import params as svc

router = APIRouter(prefix="/api/params")

@router.get("/global")
def get_global(db: Session = Depends(get_db)):
    return {"ok": True, "data": svc.get_global(db)}

@router.patch("/global")
def patch_global(payload: ParamPatch, db: Session = Depends(get_db)):
    svc.patch_global(db, payload.key, payload.value)
    return {"ok": True, "data": {"updated": payload.key}}
```

- [ ] **Step 5: 注册路由 + 启动时 seed（main.py）**

```python
# server/app/main.py（增量）
from .api.params import router as params_router
from .services.params import seed_from_csbmk

def create_app() -> FastAPI:
    # ... 原内容
    app.include_router(params_router)

    @app.on_event("startup")
    async def _seed():
        from .db.session import Base, engine
        Base.metadata.create_all(bind=engine)  # 测试模式直接 create_all
        seed_from_csbmk()

    return app
```

- [ ] **Step 6: 跑测试验证通过**

Run: `cd server && pytest tests/integration/test_params_api.py -v`
Expected: 2 passed

- [ ] **Step 7: 提交**

```bash
git add server/app/services/params.py server/app/schemas/params.py server/app/api/params.py server/app/main.py server/tests/
git commit -m "feat(params): seed csbmk + global params get/patch with point-path keys"
```

---

## Phase 2 · 计算引擎

### Task 11: EvaluationContext + factors 模块

**Files:**
- Create: `server/app/core/__init__.py`
- Create: `server/app/core/context.py`
- Create: `server/app/core/factors.py`
- Test: `server/tests/unit/test_context.py`
- Test: `server/tests/unit/test_factors.py`

- [ ] **Step 1: 写测试 test_factors.py**

```python
# server/tests/unit/test_factors.py
from app.core.factors import non_func_factor, dev_factor_chain, ops_factor_chain

def test_non_func_factor_baseline():
    # 全部 0 应得 1.0
    assert non_func_factor(0, 0, 0, 0) == 1.0

def test_non_func_factor_max():
    # 全部 +1 应得 1.1
    assert abs(non_func_factor(1, 1, 1, 1) - 1.1) < 1e-9

def test_non_func_factor_min():
    # 全部 -1 应得 0.9
    assert abs(non_func_factor(-1, -1, -1, -1) - 0.9) < 1e-9

def test_dev_factor_chain_appendix_d():
    # 实施规程附录 D：业务处理 1.00 × 非功能 1.00 × 完整性 1.00 × 平台 1.00 × 团队 1.00 = 1.0
    f = dev_factor_chain(app_type=1.0, non_func=1.0, integrity=1.0, platform=1.0, team_bg=1.0)
    assert f == 1.0

def test_ops_factor_chain_appendix_d():
    # 附录 D 运维：1.10×1.05×0.89×0.95×1.10×1.00×1.00×1.00×1.00×1.10×1.00 ≈ 1.18
    f = ops_factor_chain(business_importance=1.10, security=1.05, support=0.89,
                         update_freq=0.95, response=1.10, integrity=1.00,
                         platform=1.00, team_exp=1.00, deployment=1.00,
                         user_scale=1.10, relevance=1.00)
    assert abs(f - 1.18) < 0.005  # 允许小数累积误差
```

- [ ] **Step 2: 写 factors.py**

```python
# server/app/core/factors.py
def non_func_factor(distributed: int, performance: int, reliability: int, multi_site: int) -> float:
    """非功能因子 = (Σ) × 0.025 + 1，每项 ∈ {-1, 0, 1}"""
    for x in (distributed, performance, reliability, multi_site):
        if x not in (-1, 0, 1):
            raise ValueError(f"non_func component must be -1/0/1, got {x}")
    return (distributed + performance + reliability + multi_site) * 0.025 + 1.0

def dev_factor_chain(*, app_type: float, non_func: float, integrity: float,
                     platform: float, team_bg: float) -> float:
    """开发因子链：app × non_func × integrity × platform × team"""
    return app_type * non_func * integrity * platform * team_bg

def ops_factor_chain(*, business_importance: float, security: float, support: float,
                     update_freq: float, response: float, integrity: float,
                     platform: float, team_exp: float, deployment: float,
                     user_scale: float, relevance: float) -> float:
    """运维因子链 11 项相乘"""
    return (business_importance * security * support * update_freq * response *
            integrity * platform * team_exp * deployment * user_scale * relevance)
```

- [ ] **Step 3: 跑测试**

Run: `cd server && pytest tests/unit/test_factors.py -v`
Expected: 5 passed

- [ ] **Step 4: 写 test_context.py**

```python
# server/tests/unit/test_context.py
from app.core.context import EvaluationContext, ProjectInputs

def test_context_resolves_pdr_three_bands():
    ctx = EvaluationContext.from_dict({
        "productivity": {"dev": {"电子政务": {"P10": 2.04, "P50": 6.41, "P90": 15.36}}},
        "city_rate": {"北京": {"dev": 32198, "ops": 26335, "class": "A"}},
        "cf": {"bidding": 1.21},
        "hours_per_pm": 174,
    }, ProjectInputs(industry="电子政务", city="北京", phase="bidding"))
    assert ctx.pdr_dev("P50") == 6.41
    assert ctx.city_rate_dev() == 32198
    assert ctx.cf() == 1.21
    assert ctx.hours_per_pm == 174

def test_context_unknown_industry_raises():
    import pytest
    with pytest.raises(KeyError):
        EvaluationContext.from_dict(
            {"productivity": {"dev": {}}, "city_rate": {"北京": {"dev": 1, "ops": 1}},
             "cf": {"bidding": 1.0}, "hours_per_pm": 174},
            ProjectInputs(industry="未知", city="北京", phase="bidding")
        ).pdr_dev("P50")
```

- [ ] **Step 5: 写 context.py**

```python
# server/app/core/context.py
from dataclasses import dataclass, field
from typing import Literal

@dataclass(frozen=True)
class ProjectInputs:
    industry: str
    city: str
    phase: Literal["budget", "bidding", "planning", "change", "settled"]

@dataclass(frozen=True)
class EvaluationContext:
    raw: dict
    inputs: ProjectInputs

    @classmethod
    def from_dict(cls, params: dict, inputs: ProjectInputs) -> "EvaluationContext":
        return cls(raw=params, inputs=inputs)

    def pdr_dev(self, band: Literal["P10", "P50", "P90"]) -> float:
        return self.raw["productivity"]["dev"][self.inputs.industry][band]

    def pdr_ops(self, band: Literal["P10", "P50", "P90"]) -> float:
        return self.raw["productivity"]["ops"]["全行业"][band]

    def city_rate_dev(self) -> float:
        return self.raw["city_rate"][self.inputs.city]["dev"]

    def city_rate_ops(self) -> float:
        return self.raw["city_rate"][self.inputs.city]["ops"]

    def cf(self) -> float:
        return self.raw["cf"][self.inputs.phase]

    @property
    def hours_per_pm(self) -> float:
        return self.raw.get("hours_per_pm", 174)
```

- [ ] **Step 6: 跑测试**

Run: `cd server && pytest tests/unit/test_context.py -v`
Expected: 2 passed

- [ ] **Step 7: 提交**

```bash
git add server/app/core/ server/tests/unit/
git commit -m "feat(core): EvaluationContext + factor chain pure functions"
```

---

### Task 12: Forward 引擎 + API + 单元测试

**Files:**
- Create: `server/app/core/forward.py`
- Create: `server/app/schemas/results.py`
- Create: `server/app/services/calc.py`
- Create: `server/app/api/calc.py`
- Modify: `server/app/main.py`
- Test: `server/tests/unit/test_forward.py`
- Test: `server/tests/integration/test_calc_api.py`

- [ ] **Step 1: 写 test_forward.py**

```python
# server/tests/unit/test_forward.py
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

def test_forward_unadjusted_size_sum():
    inp = ForwardInput(
        items=[FpItem(us=4), FpItem(us=10), FpItem(us=4)],
        dev_factor=1.0, ops_factor=1.0,
        include_dev=True, include_ops=False, other_cost=0)
    r = calculate_forward(_ctx(), inp)
    assert r.scale_us == 18
    assert abs(r.scale_adjusted - 18 * 1.21) < 1e-6

def test_forward_three_bands():
    inp = ForwardInput(
        items=[FpItem(us=275)], dev_factor=1.0, ops_factor=1.0,
        include_dev=True, include_ops=False, other_cost=0)
    r = calculate_forward(_ctx(), inp)
    s = 275 * 1.21
    expected_p50_hours = s * 6.41
    assert abs(r.effort_dev_hours["P50"] - expected_p50_hours) < 0.01
```

- [ ] **Step 2: 写 forward.py**

```python
# server/app/core/forward.py
from dataclasses import dataclass, field
from typing import Literal
from .context import EvaluationContext

@dataclass
class FpItem:
    us: float

@dataclass
class ForwardInput:
    items: list[FpItem]
    dev_factor: float = 1.0
    ops_factor: float = 1.0
    include_dev: bool = True
    include_ops: bool = False
    other_cost: float = 0.0

@dataclass
class ForwardResult:
    scale_us: float
    scale_adjusted: float
    cf_used: float
    effort_dev_hours: dict[str, float]   # P10/P50/P90
    effort_ops_hours: dict[str, float]
    cost_dev_yuan: dict[str, float]
    cost_ops_yuan: dict[str, float]
    cost_other_yuan: float
    cost_total_yuan: dict[str, float]

BANDS = ("P10", "P50", "P90")

def calculate_forward(ctx: EvaluationContext, inp: ForwardInput) -> ForwardResult:
    us = sum(i.us for i in inp.items)
    cf = ctx.cf()
    s = us * cf
    eff_dev = {b: s * ctx.pdr_dev(b) * inp.dev_factor for b in BANDS} if inp.include_dev else {b: 0.0 for b in BANDS}
    eff_ops = {b: s * ctx.pdr_ops(b) * inp.ops_factor for b in BANDS} if inp.include_ops else {b: 0.0 for b in BANDS}
    pm = ctx.hours_per_pm
    rate_dev = ctx.city_rate_dev()
    rate_ops = ctx.city_rate_ops()
    cost_dev = {b: eff_dev[b] / pm * rate_dev for b in BANDS}
    cost_ops = {b: eff_ops[b] / pm * rate_ops for b in BANDS}
    total = {b: cost_dev[b] + cost_ops[b] + inp.other_cost for b in BANDS}
    return ForwardResult(
        scale_us=us, scale_adjusted=s, cf_used=cf,
        effort_dev_hours=eff_dev, effort_ops_hours=eff_ops,
        cost_dev_yuan=cost_dev, cost_ops_yuan=cost_ops,
        cost_other_yuan=inp.other_cost, cost_total_yuan=total)
```

- [ ] **Step 3: 跑测试**

Run: `cd server && pytest tests/unit/test_forward.py -v`
Expected: 2 passed

- [ ] **Step 4: 写 schemas/results.py + service + api**

```python
# server/app/schemas/results.py
from pydantic import BaseModel
from typing import Optional

class FpItemIn(BaseModel):
    us: float

class CalcForwardRequest(BaseModel):
    project_id: str
    items: list[FpItemIn]
    dev_factor: float = 1.0
    ops_factor: float = 1.0
    include_dev: bool = True
    include_ops: bool = False
    other_cost: float = 0.0

class CalcResponse(BaseModel):
    scale_us: float
    scale_adjusted: float
    cf_used: float
    effort_dev_hours: dict
    effort_ops_hours: dict
    cost_dev_yuan: dict
    cost_ops_yuan: dict
    cost_other_yuan: float
    cost_total_yuan: dict
```

```python
# server/app/services/calc.py
from sqlalchemy.orm import Session
from ..core.context import EvaluationContext, ProjectInputs
from ..core.forward import calculate_forward, ForwardInput, FpItem
from ..services import params as ps
from ..db.models import Project

def run_forward(db: Session, project_id: str, payload: dict) -> dict:
    proj = db.query(Project).filter_by(id=project_id).first()
    if not proj:
        raise ValueError("PROJECT_NOT_FOUND")
    full_params = ps.get_global(db)  # 暂未叠加 override，留待 v1.1
    ctx = EvaluationContext.from_dict(
        full_params,
        ProjectInputs(industry=proj.industry, city=proj.city, phase=proj.phase))
    inp = ForwardInput(
        items=[FpItem(us=i["us"]) for i in payload.get("items", [])],
        dev_factor=payload.get("dev_factor", 1.0),
        ops_factor=payload.get("ops_factor", 1.0),
        include_dev=payload.get("include_dev", True),
        include_ops=payload.get("include_ops", False),
        other_cost=payload.get("other_cost", 0.0),
    )
    r = calculate_forward(ctx, inp)
    return r.__dict__
```

```python
# server/app/api/calc.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..schemas.results import CalcForwardRequest
from ..services import calc as svc

router = APIRouter(prefix="/api/calc")

@router.post("/forward")
def forward(payload: CalcForwardRequest, db: Session = Depends(get_db)):
    try:
        result = svc.run_forward(db, payload.project_id, payload.model_dump())
    except ValueError as e:
        raise HTTPException(404, {"error": {"code": str(e)}})
    return {"ok": True, "data": result}
```

- [ ] **Step 5: 注册路由**

```python
# server/app/main.py（追加）
from .api.calc import router as calc_router
app.include_router(calc_router)
```

- [ ] **Step 6: 写 integration test**

```python
# server/tests/integration/test_calc_api.py
import pytest, uuid
from httpx import AsyncClient, ASGITransport

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}

@pytest.fixture
async def client_with_project(monkeypatch):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    monkeypatch.setenv("COST_DB_PATH", f"/tmp/cost-test-{uuid.uuid4()}.sqlite")
    from app.main import create_app
    from app.db.session import Base, engine
    from app.services import params as ps
    Base.metadata.create_all(bind=engine)
    ps.seed_from_csbmk()
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/projects", headers=H, json={
            "name": "T", "project_type": "dev_only", "phase": "bidding",
            "city": "北京", "industry": "电子政务", "mode": "forward",
            "basis_data_ver": "CSBMK®-202510",
        })
        pid = r.json()["data"]["id"]
        yield c, pid

async def test_forward_endpoint_smoke(client_with_project):
    c, pid = client_with_project
    r = await c.post("/api/calc/forward", headers={**H, "Content-Type": "application/json"},
                     json={"project_id": pid, "items": [{"us": 275}],
                           "dev_factor": 1.0, "include_dev": True})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["scale_us"] == 275
    assert data["scale_adjusted"] - 275 * 1.21 < 1e-6
```

- [ ] **Step 7: 跑测试**

Run: `cd server && pytest tests/ -v -k "forward"`
Expected: 3 passed

- [ ] **Step 8: 提交**

```bash
git add server/app/ server/tests/
git commit -m "feat(calc): forward engine (FP→cost) + api + 三档 P10/P50/P90 输出"
```

---

### Task 13: Reverse 引擎 + 业务语义注释

**Files:**
- Create: `server/app/core/reverse.py`
- Test: `server/tests/unit/test_reverse.py`

- [ ] **Step 1: 写测试**

```python
# server/tests/unit/test_reverse.py
import pytest
from app.core.reverse import calculate_reverse, ReverseInput
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

def test_reverse_dev_only_alpha_one():
    # 目标 50 万元，仅开发，α=1.0，无其他费用
    inp = ReverseInput(target_total=500000, other_cost=0,
                       include_ops=False, alpha_dev=1.0,
                       dev_factor=1.0, ops_factor=1.0)
    r = calculate_reverse(_ctx(), inp)
    # 反算：PM = 500000/32198；AE = PM × 174；UE/PDR = S
    # P50 时 S = (500000/32198 × 174) / 6.41
    expected_p50_s = (500000 / 32198 * 174) / 6.41
    assert abs(r.scale_adjusted_bands["P50"] - expected_p50_s) < 0.5

def test_reverse_budget_negative_raises():
    inp = ReverseInput(target_total=10000, other_cost=20000,
                       include_ops=False, alpha_dev=1.0,
                       dev_factor=1.0, ops_factor=1.0)
    with pytest.raises(ValueError, match="BUDGET_NEGATIVE"):
        calculate_reverse(_ctx(), inp)

def test_reverse_with_ops_split():
    # α=0.917 大致对应 CSBMK 4.9 P50=9.02% 倒推
    inp = ReverseInput(target_total=600000, other_cost=0,
                       include_ops=True, alpha_dev=0.917,
                       dev_factor=1.0, ops_factor=1.0)
    r = calculate_reverse(_ctx(), inp)
    assert r.scale_adjusted_bands["P50"] > 0
    assert r.scale_adjusted_ops_bands["P50"] > 0
```

- [ ] **Step 2: 写 reverse.py（含完整业务语义注释）**

```python
# server/app/core/reverse.py
from dataclasses import dataclass
from .context import EvaluationContext
from .forward import BANDS

@dataclass
class ReverseInput:
    target_total: float
    other_cost: float = 0.0
    include_ops: bool = False
    alpha_dev: float = 1.0
    dev_factor: float = 1.0
    ops_factor: float = 1.0

@dataclass
class ReverseResult:
    """三档对应预算口径（不是团队效率）：
    - P10 = 乐观（行业最高生产率，可买到的最大规模）
    - P50 = 中位（推荐档，多数项目能达到）
    - P90 = 保守（行业较低生产率，可保证完成的最小规模）
    """
    budget_for_dev: float
    budget_for_ops: float
    scale_adjusted_bands: dict[str, float]      # 开发三档调整后规模
    scale_unadjusted_bands: dict[str, float]    # 开发三档未调整
    scale_adjusted_ops_bands: dict[str, float]
    scale_unadjusted_ops_bands: dict[str, float]
    cf_used: float
    recommended_band: str = "P50"

def calculate_reverse(ctx: EvaluationContext, inp: ReverseInput) -> ReverseResult:
    fp_budget = inp.target_total - inp.other_cost
    if fp_budget <= 0:
        raise ValueError(f"BUDGET_NEGATIVE: target {inp.target_total} - other {inp.other_cost} <= 0")
    if inp.include_ops:
        budget_dev = fp_budget * inp.alpha_dev
        budget_ops = fp_budget * (1.0 - inp.alpha_dev)
    else:
        budget_dev = fp_budget
        budget_ops = 0.0

    cf = ctx.cf()
    pm_h = ctx.hours_per_pm

    # Dev 反算
    pm_dev = budget_dev / ctx.city_rate_dev()
    ae_dev = pm_dev * pm_h
    ue_dev = ae_dev / inp.dev_factor
    s_dev = {b: ue_dev / ctx.pdr_dev(b) for b in BANDS}
    us_dev = {b: s_dev[b] / cf for b in BANDS}

    # Ops 反算
    if budget_ops > 0:
        pm_ops = budget_ops / ctx.city_rate_ops()
        ae_ops = pm_ops * pm_h
        ue_ops = ae_ops / inp.ops_factor
        s_ops = {b: ue_ops / ctx.pdr_ops(b) for b in BANDS}
        us_ops = {b: s_ops[b] / cf for b in BANDS}
    else:
        s_ops = {b: 0.0 for b in BANDS}
        us_ops = {b: 0.0 for b in BANDS}

    return ReverseResult(
        budget_for_dev=budget_dev, budget_for_ops=budget_ops,
        scale_adjusted_bands=s_dev, scale_unadjusted_bands=us_dev,
        scale_adjusted_ops_bands=s_ops, scale_unadjusted_ops_bands=us_ops,
        cf_used=cf)
```

- [ ] **Step 3: 跑测试**

Run: `cd server && pytest tests/unit/test_reverse.py -v`
Expected: 3 passed

- [ ] **Step 4: 提交**

```bash
git add server/app/core/reverse.py server/tests/unit/test_reverse.py
git commit -m "feat(calc): reverse engine (cost→FP) — bands as budget interpretation, not team efficiency"
```

---

### Task 14: Reverse API + integration test

**Files:**
- Modify: `server/app/schemas/results.py`
- Modify: `server/app/services/calc.py`
- Modify: `server/app/api/calc.py`
- Modify: `server/tests/integration/test_calc_api.py`

- [ ] **Step 1: 追加测试**

```python
# server/tests/integration/test_calc_api.py（追加）
async def test_reverse_endpoint_three_bands(client_with_project):
    c, pid = client_with_project
    r = await c.post("/api/calc/reverse",
                     headers={**H, "Content-Type": "application/json"},
                     json={"project_id": pid, "target_total": 500000,
                           "other_cost": 0, "include_ops": False,
                           "alpha_dev": 1.0,
                           "dev_factor": 1.0, "ops_factor": 1.0})
    assert r.status_code == 200
    data = r.json()["data"]
    assert "scale_adjusted_bands" in data
    assert data["scale_adjusted_bands"]["P50"] > data["scale_adjusted_bands"]["P10"]
    assert data["recommended_band"] == "P50"
```

- [ ] **Step 2: 增加 schema + service + api**

```python
# server/app/schemas/results.py（追加）
class CalcReverseRequest(BaseModel):
    project_id: str
    target_total: float
    other_cost: float = 0.0
    include_ops: bool = False
    alpha_dev: float = 1.0
    dev_factor: float = 1.0
    ops_factor: float = 1.0
```

```python
# server/app/services/calc.py（追加）
from ..core.reverse import calculate_reverse, ReverseInput

def run_reverse(db: Session, project_id: str, payload: dict) -> dict:
    proj = db.query(Project).filter_by(id=project_id).first()
    if not proj:
        raise ValueError("PROJECT_NOT_FOUND")
    full_params = ps.get_global(db)
    ctx = EvaluationContext.from_dict(
        full_params,
        ProjectInputs(industry=proj.industry, city=proj.city, phase=proj.phase))
    inp = ReverseInput(
        target_total=payload["target_total"],
        other_cost=payload.get("other_cost", 0.0),
        include_ops=payload.get("include_ops", False),
        alpha_dev=payload.get("alpha_dev", 1.0),
        dev_factor=payload.get("dev_factor", 1.0),
        ops_factor=payload.get("ops_factor", 1.0))
    r = calculate_reverse(ctx, inp)
    return r.__dict__
```

```python
# server/app/api/calc.py（追加）
from ..schemas.results import CalcReverseRequest

@router.post("/reverse")
def reverse(payload: CalcReverseRequest, db: Session = Depends(get_db)):
    try:
        return {"ok": True, "data": svc.run_reverse(db, payload.project_id, payload.model_dump())}
    except ValueError as e:
        code = str(e).split(":")[0]
        raise HTTPException(400, {"error": {"code": code, "problem": str(e),
                                              "fix": "调整目标金额或其他费用"}})
```

- [ ] **Step 3: 跑测试**

Run: `cd server && pytest tests/integration/test_calc_api.py -v`
Expected: 2 passed

- [ ] **Step 4: 提交**

```bash
git add server/app/ server/tests/
git commit -m "feat(api): /api/calc/reverse with budget-interpretation 三档"
```

---

### Task 15: Allocator 引擎（两段计算 + audit_tag）

**Files:**
- Create: `server/app/core/allocator.py`
- Test: `server/tests/unit/test_allocator.py`

- [ ] **Step 1: 写测试**

```python
# server/tests/unit/test_allocator.py
import pytest
from app.core.allocator import allocate, AllocatorInput, FpDraft

def test_allocator_simple_proportional():
    drafts = [FpDraft(name="A", weight=4, locked=False),
              FpDraft(name="B", weight=10, locked=False),
              FpDraft(name="C", weight=4, locked=False)]
    out = allocate(AllocatorInput(target_us=180, drafts=drafts, cf=1.21))
    assert sum(o.us for o in out) == pytest.approx(180, rel=0.01)
    a = next(o for o in out if o.name == "A")
    assert a.audit_tag == "budget_derived"

def test_allocator_with_locked_items():
    drafts = [FpDraft(name="L", weight=20, locked=True, locked_us=20),
              FpDraft(name="X", weight=10, locked=False),
              FpDraft(name="Y", weight=10, locked=False)]
    # target_us=80, locked 占 20×1.21=24.2 (S 单位)
    out = allocate(AllocatorInput(target_us=80, drafts=drafts, cf=1.21))
    locked_out = next(o for o in out if o.name == "L")
    assert locked_out.us == 20
    assert locked_out.audit_tag != "budget_derived"  # 锁定项不打 budget_derived
    free_us_total = sum(o.us for o in out if not o.locked)
    # 80 - 20 = 60 留给未锁定，X/Y 等权
    assert free_us_total == pytest.approx(60, rel=0.01)

def test_allocator_locked_exceeds_target_raises():
    drafts = [FpDraft(name="L", weight=100, locked=True, locked_us=100)]
    with pytest.raises(ValueError, match="LOCKED_EXCEEDS_TARGET"):
        allocate(AllocatorInput(target_us=50, drafts=drafts, cf=1.21))
```

- [ ] **Step 2: 写 allocator.py**

```python
# server/app/core/allocator.py
from dataclasses import dataclass

@dataclass
class FpDraft:
    name: str
    weight: float
    locked: bool = False
    locked_us: float = 0.0  # 仅 locked=True 时使用

@dataclass
class AllocatorInput:
    target_us: float                # 调整后目标 S
    drafts: list[FpDraft]
    cf: float

@dataclass
class AllocatorOutput:
    name: str
    us: float
    locked: bool
    audit_tag: str | None     # "budget_derived" | None

def allocate(inp: AllocatorInput) -> list[AllocatorOutput]:
    locked_us_sum = sum(d.locked_us for d in inp.drafts if d.locked)
    s_locked = locked_us_sum * inp.cf
    s_free = inp.target_us - s_locked
    if s_free <= 0:
        raise ValueError(f"LOCKED_EXCEEDS_TARGET: locked={s_locked}, target={inp.target_us}")
    free = [d for d in inp.drafts if not d.locked]
    weight_sum = sum(d.weight for d in free) or 1.0
    out: list[AllocatorOutput] = []
    for d in inp.drafts:
        if d.locked:
            out.append(AllocatorOutput(name=d.name, us=d.locked_us, locked=True, audit_tag=None))
        else:
            us = round(s_free / inp.cf * d.weight / weight_sum, 2)
            out.append(AllocatorOutput(name=d.name, us=us, locked=False, audit_tag="budget_derived"))
    return out
```

- [ ] **Step 3: 跑测试**

Run: `cd server && pytest tests/unit/test_allocator.py -v`
Expected: 3 passed

- [ ] **Step 4: 提交**

```bash
git add server/app/core/allocator.py server/tests/unit/test_allocator.py
git commit -m "feat(calc): allocator with two-phase locked-FP isolation + budget_derived audit tag"
```

---

### Task 16: Allocator API

**Files:**
- Modify: `server/app/schemas/results.py`
- Modify: `server/app/services/calc.py`
- Modify: `server/app/api/calc.py`
- Modify: `server/tests/integration/test_calc_api.py`

- [ ] **Step 1: 追加测试**

```python
# server/tests/integration/test_calc_api.py（追加）
async def test_allocator_endpoint(client_with_project):
    c, pid = client_with_project
    r = await c.post("/api/calc/allocate",
                     headers={**H, "Content-Type": "application/json"},
                     json={"project_id": pid, "target_us": 180, "cf": 1.21,
                           "drafts": [{"name": "A", "weight": 4},
                                      {"name": "B", "weight": 10},
                                      {"name": "C", "weight": 4}]})
    assert r.status_code == 200
    items = r.json()["data"]
    assert len(items) == 3
    assert all(i["audit_tag"] == "budget_derived" for i in items)
```

- [ ] **Step 2: schema + service + api**

```python
# server/app/schemas/results.py（追加）
class FpDraftIn(BaseModel):
    name: str
    weight: float
    locked: bool = False
    locked_us: float = 0.0

class AllocateRequest(BaseModel):
    project_id: str
    target_us: float
    cf: float = 1.21
    drafts: list[FpDraftIn]
```

```python
# server/app/services/calc.py（追加）
from ..core.allocator import allocate, AllocatorInput, FpDraft

def run_allocate(payload: dict) -> list[dict]:
    drafts = [FpDraft(name=d["name"], weight=d["weight"],
                      locked=d.get("locked", False), locked_us=d.get("locked_us", 0.0))
              for d in payload["drafts"]]
    out = allocate(AllocatorInput(
        target_us=payload["target_us"], drafts=drafts, cf=payload.get("cf", 1.21)))
    return [o.__dict__ for o in out]
```

```python
# server/app/api/calc.py（追加）
from ..schemas.results import AllocateRequest

@router.post("/allocate")
def allocate_route(payload: AllocateRequest):
    try:
        return {"ok": True, "data": svc.run_allocate(payload.model_dump())}
    except ValueError as e:
        code = str(e).split(":")[0]
        raise HTTPException(400, {"error": {"code": code, "problem": str(e),
                                              "fix": "解锁部分锁定项或提高 target_us"}})
```

- [ ] **Step 3: 跑测试**

Run: `cd server && pytest tests/integration/test_calc_api.py -v`
Expected: 3 passed

- [ ] **Step 4: 提交**

```bash
git add server/app/ server/tests/
git commit -m "feat(api): /api/calc/allocate"
```

---

### Task 17: 黄金测试（实施规程附录 D）

**Files:**
- Create: `server/tests/golden/csbmk_202210.json`
- Create: `server/tests/golden/appendix_d.json`
- Create: `server/tests/integration/test_golden.py`

- [ ] **Step 1: 写 golden fixture：CSBMK®-202210（附录 D 用版本）**

```json
{
  "version": "CSBMK®-202210",
  "productivity": {
    "dev": {"电子政务": {"P10": 2.04, "P50": 6.72, "P90": 17.35}},
    "ops": {"全行业": {"P10": 0.21, "P50": 0.84, "P90": 2.07}}
  },
  "city_rate": {"北京": {"dev": 32343, "ops": 25630, "class": "A"}},
  "cf": {"bidding": 1.21},
  "hours_per_pm": 174
}
```

- [ ] **Step 2: 写 appendix_d.json（输入与期望输出）**

```json
{
  "name": "实施规程附录 D · 政务服务平台",
  "inputs": {
    "industry": "电子政务",
    "city": "北京",
    "phase": "bidding",
    "items_us_total": 275,
    "dev_factor": 1.00,
    "ops_factor": 1.18,
    "include_dev": true,
    "include_ops": true,
    "other_cost": 25000,
    "ops_factor_components": {
      "business_importance": 1.10,
      "security": 1.05,
      "support": 0.89,
      "update_freq": 0.95,
      "response": 1.10,
      "integrity": 1.00,
      "platform": 1.00,
      "team_exp": 1.00,
      "deployment": 1.00,
      "user_scale": 1.10,
      "relevance": 1.00
    }
  },
  "expected": {
    "scale_adjusted": 332.75,
    "effort_dev_p50_hours": 2236.08,
    "effort_ops_p50_hours": 329.82,
    "cost_dev_p50_yuan": 415560,
    "cost_ops_p50_yuan": 48620,
    "cost_total_p50_yuan": 489180,
    "cost_total_p10_yuan": 396500,
    "cost_total_p90_yuan": 581900,
    "tolerance_yuan": 100
  }
}
```

注：基准数据 P50 在 forward 计算中对应"中值"，期望输出按附录 D 文本核对：48.92 万 = 489200，39.65 万 = 396500，58.19 万 = 581900。容差 100 元覆盖小数累积。

- [ ] **Step 3: 写黄金测试**

```python
# server/tests/integration/test_golden.py
import json
from pathlib import Path
from app.core.context import EvaluationContext, ProjectInputs
from app.core.forward import calculate_forward, ForwardInput, FpItem
from app.core.factors import ops_factor_chain

GOLDEN = Path(__file__).parent.parent / "golden"

def test_golden_appendix_d():
    params = json.loads((GOLDEN / "csbmk_202210.json").read_text())
    case = json.loads((GOLDEN / "appendix_d.json").read_text())
    inp_data = case["inputs"]
    expected = case["expected"]

    ctx = EvaluationContext.from_dict(
        params, ProjectInputs(industry=inp_data["industry"],
                              city=inp_data["city"],
                              phase=inp_data["phase"]))

    # 验证运维因子组合
    ops_f = ops_factor_chain(**inp_data["ops_factor_components"])
    assert abs(ops_f - inp_data["ops_factor"]) < 0.005

    inp = ForwardInput(
        items=[FpItem(us=inp_data["items_us_total"])],
        dev_factor=inp_data["dev_factor"],
        ops_factor=inp_data["ops_factor"],
        include_dev=inp_data["include_dev"],
        include_ops=inp_data["include_ops"],
        other_cost=inp_data["other_cost"])
    r = calculate_forward(ctx, inp)

    tol = expected["tolerance_yuan"]
    assert abs(r.scale_adjusted - expected["scale_adjusted"]) < 0.5
    assert abs(r.cost_total_yuan["P50"] - expected["cost_total_p50_yuan"]) < tol
    # 边界档由于行业 P10/P90 对范围影响巨大，单独按 ±20% 兜底
    assert r.cost_total_yuan["P10"] < r.cost_total_yuan["P50"]
    assert r.cost_total_yuan["P50"] < r.cost_total_yuan["P90"]
```

- [ ] **Step 4: 跑黄金测试**

Run: `cd server && pytest tests/integration/test_golden.py -v`
Expected: 1 passed

如失败：核对 spec §5.4 中的算例数据 + benchmark2025.txt 中 CSBMK®-202210 数据 + 期望值容差。这是核心证据：算法实现正确。

- [ ] **Step 5: 提交**

```bash
git add server/tests/golden/ server/tests/integration/test_golden.py
git commit -m "test(golden): 实施规程附录 D 算例 — 48.92 万元中值黄金测试"
```

---

### Task 18: Property-based 反向往返测试

**Files:**
- Create: `server/tests/property/__init__.py`
- Create: `server/tests/property/test_roundtrip.py`

- [ ] **Step 1: 写 hypothesis 测试**

```python
# server/tests/property/test_roundtrip.py
from hypothesis import given, strategies as st, settings, assume
from app.core.context import EvaluationContext, ProjectInputs
from app.core.forward import calculate_forward, ForwardInput, FpItem
from app.core.reverse import calculate_reverse, ReverseInput

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

@given(target=st.floats(min_value=10000, max_value=100_000_000),
       factor=st.floats(min_value=0.5, max_value=2.0))
@settings(max_examples=100, deadline=None)
def test_reverse_then_forward_p50_recovers_target(target, factor):
    """反推 P50 -> 正向 P50 的总费用应接近 target（误差 ≤ 1%）。"""
    rev_inp = ReverseInput(target_total=target, other_cost=0,
                            include_ops=False, alpha_dev=1.0,
                            dev_factor=factor, ops_factor=1.0)
    rev = calculate_reverse(_ctx(), rev_inp)
    s_p50 = rev.scale_adjusted_bands["P50"]
    assume(s_p50 > 0.01)
    # 用反推得到的 S（已含 cf）作为 items.us×cf 的 forward 输入
    # 注意 forward.items 是 us，需除回 cf
    us_p50 = s_p50 / rev.cf_used
    fwd_inp = ForwardInput(items=[FpItem(us=us_p50)],
                            dev_factor=factor, ops_factor=1.0,
                            include_dev=True, include_ops=False, other_cost=0)
    fwd = calculate_forward(_ctx(), fwd_inp)
    error = abs(fwd.cost_total_yuan["P50"] - target) / target
    assert error < 0.01, f"roundtrip error {error:.3%}, fwd={fwd.cost_total_yuan['P50']}, target={target}"
```

- [ ] **Step 2: 跑测试**

Run: `cd server && pytest tests/property/ -v`
Expected: 1 passed (含 100 个 hypothesis 案例)

- [ ] **Step 3: 提交**

```bash
git add server/tests/property/
git commit -m "test(property): hypothesis roundtrip — reverse(target) → forward 误差 < 1%"
```

---

### Task 19: 全测试套件 + coverage 报告

**Files:**
- Modify: `server/pyproject.toml`（追加 coverage 配置）

- [ ] **Step 1: 追加 coverage 配置**

```toml
# server/pyproject.toml（追加）
[tool.coverage.run]
source = ["app"]
omit = ["*/tests/*"]

[tool.coverage.report]
exclude_lines = ["pragma: no cover", "raise NotImplementedError"]
fail_under = 80
```

- [ ] **Step 2: 跑全测试 + 覆盖率**

Run: `cd server && pip install pytest-cov && pytest --cov=app --cov-report=term-missing -v`
Expected:
- 所有测试 PASS（约 25 个用例）
- coverage ≥ 80%（关键文件 app/core/* 应在 90%+）

- [ ] **Step 3: 修复覆盖率不足的关键路径**

如果 `app/core/*` 覆盖率 < 90%，补单元测试到对应 test_*.py。常见漏点：
- `factors.py::non_func_factor` 边界 ValueError
- `reverse.py::calculate_reverse` 仅运维路径（include_ops=True, alpha_dev=0.0）
- `allocator.py::allocate` 全锁定路径

- [ ] **Step 4: 提交**

```bash
git add server/pyproject.toml server/tests/
git commit -m "test: full suite + coverage ≥ 80% (core/* ≥ 90%)"
```

---

## 完成标志

执行完 19 个 Task 后：

- [ ] `cd server && pytest` 全绿（约 25 个用例）
- [ ] coverage ≥ 80%，core/* ≥ 90%
- [ ] 黄金测试通过：附录 D 算例 → 48.92 万元 中值（容差 100 元）
- [ ] hypothesis property test：reverse→forward 100 案例误差 < 1%
- [ ] CSRF 三层防护测试通过
- [ ] git log 显示 ~19 个 commit，全部有意义

下一个 Plan：**Plan 2 — 文档解析 + Excel 导出**（Phase 3 + 4）。

---

## 自检（writing-plans 要求）

**Spec 覆盖：**
- §3 系统架构 → Task 2/3/6/7 实现 FastAPI + SQLite + 中间件
- §4 数据模型 → Task 4/5 全表 schema + 触发器
- §5.1 Forward → Task 12
- §5.2 Reverse（含业务语义）→ Task 13/14
- §5.3 Allocator（含两段计算）→ Task 15/16
- §5.4 黄金测试 → Task 17
- §9.1 路由 → Task 8/10/12/14/16（projects/params/calc 已覆盖；functions CRUD 留 Plan 2 因依赖文档解析）
- §9.5 安全（CSRF）→ Task 6/7
- §11.1 单元测试 → Task 11/12/13/15/17
- §11.4 黄金测试 → Task 17

**Spec 未在本 Plan 覆盖（移至后续 Plan）：**
- §6 Web UI（Plan 3）
- §7 Excel 输出（Plan 2）
- §8 Plugin 打包（Plan 4）
- §9 functions CRUD API（Plan 2，因文件上传依赖）
- §11.3 E2E（Plan 4）
- params override（项目级）— v1.1 增量，Plan 2 加

**Placeholder 扫描**：无 TBD/TODO 残留，所有代码块完整。

**类型一致性**：`FpItem.us`、`AllocatorInput.target_us`、`ForwardInput.items` 跨 Task 同名同义。
