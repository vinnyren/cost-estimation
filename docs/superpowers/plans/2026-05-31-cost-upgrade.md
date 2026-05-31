# /cost-upgrade 插件升级功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增独立命令 `/cost-upgrade`，安全地把既有数据目录推进到当前代码版本（备份 + alembic 漂移修复 + 基准重灯 + 刷新 venv/前端）。

**Architecture:** 方案 A——薄命令壳 `commands/cost-upgrade.md` 负责路径/venv/停服/传参/前端；新增 Python 模块 `server/app/upgrade.py` 承载全部有状态逻辑，拆成可独立测试的纯函数（`detect_state` / `backup_db` / `reconcile_schema` / `reconcile_baseline`）+ 一个 `cli` 编排入口。schema 修复用内省驱动（已到位→`stamp head`，缺可空列→加列+回填默认），不重放迁移链以避开现网 stamp 漂移崩溃。

**Tech Stack:** Python 3.11 / SQLAlchemy 2.0 / Alembic / click / pytest（集成测试用 `CliRunner` + `db_session` fixture）。

设计依据：`docs/superpowers/specs/2026-05-31-plugin-upgrade-design.md`

---

## 文件结构

| 文件 | 责任 |
|---|---|
| `server/app/upgrade.py`（新增） | 升级编排：detect / backup / schema reconcile / baseline reconcile + `cli` |
| `server/tests/integration/test_upgrade.py`（新增） | 8 个分支回归 |
| `commands/cost-upgrade.md`（新增） | 薄命令壳 |
| `.claude-plugin/plugin.json`（改） | `commands` 数组加 `./commands/cost-upgrade.md` |
| `docs/v2-changelog.md`（改） | 加 `/cost-upgrade` 条目 |
| `README.md`（改） | 命令表补 `/cost-upgrade` |

**复用既有件**（不重写）：`app.bootstrap.reseed_if_outdated`、`app.bootstrap._flatten`、`app.db.session.Base`、`app.db.models.ParamGlobal`、`app.config.settings`。

**实际表名**：全局基准 = `params_global`，按项目覆盖 = `params_override`（升级永不触碰后者）。

---

## Task 1: `detect_state` —— 内省驱动的状态检测

**Files:**
- Create: `server/app/upgrade.py`
- Test: `server/tests/integration/test_upgrade.py`

- [ ] **Step 1: 写失败测试**

```python
# server/tests/integration/test_upgrade.py
"""/cost-upgrade 升级编排回归。"""
import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from sqlalchemy import create_engine, text

from app.db.session import Base
from app.db import models as _models  # noqa: F401  注册模型


def _engine(db_path: Path):
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


def _seed_json(tmp_path: Path, version: str = "SSM-BK-TEST") -> Path:
    p = tmp_path / "seed.json"
    p.write_text(json.dumps({
        "version": version,
        "city_rate": {"北京": {"dev": 33400, "ops": 25800, "class": "A"}},
        "cf": {"budget": 1.7},
        "hours_per_pm": 174,
    }, ensure_ascii=False), encoding="utf-8")
    return p


def test_detect_diverged_stamp(tmp_path: Path):
    """schema 到位但 alembic stamp 落后 → schema_at_head=True 且 stamp_rev 落后。"""
    from app.upgrade import detect_state

    db = tmp_path / "db" / "cost.sqlite"
    db.parent.mkdir(parents=True)
    eng = _engine(db)
    Base.metadata.create_all(eng)  # 建全部 head 表
    with eng.begin() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        conn.execute(text("INSERT INTO alembic_version VALUES ('4b7939b0712d')"))  # 落后的戳

    state = detect_state(eng, _seed_json(tmp_path))
    assert state.schema_at_head is True
    assert state.stamp_rev == "4b7939b0712d"
    assert state.missing_cols == []
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd server && .venv/bin/pytest tests/integration/test_upgrade.py::test_detect_diverged_stamp -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'app.upgrade'`

- [ ] **Step 3: 写最小实现**

```python
# server/app/upgrade.py
"""插件升级编排：把既有数据目录安全推进到当前代码版本。

用法：
  python -m app.upgrade --db <db> --seed <seed.json> --ts <timestamp> [--yes]

职责：备份 → schema 漂移修复(create_all + 可空加列 + stamp head) → 基准重灯
(标准变更→导出+全量重置；不变→reseed 未改动行)。

铁律：不触碰 params_override（按项目定制）；备份先于一切变更；失败立即停、
不自动回滚，打印恢复命令。

约束：本模块假设迁移为【加性 schema 变更】（新表 / 可空新列 / 索引）。若未来出现
非加性 DDL（删列/改类型/加约束）或需复杂数据回填的迁移，必须在此为对应 revision
加显式 handler——reconcile_schema 遇非空无默认缺列会主动抛错提示。
"""
from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

import click
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects import sqlite as sqlite_dialect
from sqlalchemy.orm import sessionmaker

from app.bootstrap import _flatten, reseed_if_outdated
from app.db import models as _models  # noqa: F401  确保模型注册到 Base.metadata
from app.db.session import Base


@dataclass
class UpgradeState:
    stamp_rev: str | None
    schema_at_head: bool
    missing_tables: list[str] = field(default_factory=list)
    missing_cols: list[tuple[str, str]] = field(default_factory=list)  # (table, column)
    basis_db: set[str] = field(default_factory=set)
    basis_target: str = ""
    standard_changed: bool = False


def _actual_columns(engine) -> dict[str, set[str]]:
    insp = inspect(engine)
    return {t: {c["name"] for c in insp.get_columns(t)} for t in insp.get_table_names()}


def detect_state(engine, seed_path: Path) -> UpgradeState:
    actual = _actual_columns(engine)
    missing_tables: list[str] = []
    missing_cols: list[tuple[str, str]] = []
    for t in Base.metadata.sorted_tables:
        if t.name not in actual:
            missing_tables.append(t.name)
            continue
        for col in t.columns:
            if col.name not in actual[t.name]:
                missing_cols.append((t.name, col.name))

    stamp_rev = None
    if "alembic_version" in actual:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT version_num FROM alembic_version")).first()
            stamp_rev = row[0] if row else None

    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    basis_target = seed.get("version", "CSBMK®-unknown")
    basis_db: set[str] = set()
    if "params_global" in actual:
        with engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT DISTINCT basis_version FROM params_global "
                "WHERE basis_version != 'user'"
            )).all()
            basis_db = {r[0] for r in rows}

    return UpgradeState(
        stamp_rev=stamp_rev,
        schema_at_head=(not missing_tables and not missing_cols),
        missing_tables=missing_tables,
        missing_cols=missing_cols,
        basis_db=basis_db,
        basis_target=basis_target,
        standard_changed=bool(basis_db) and basis_target not in basis_db,
    )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd server && .venv/bin/pytest tests/integration/test_upgrade.py::test_detect_diverged_stamp -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add server/app/upgrade.py server/tests/integration/test_upgrade.py
git commit -m "feat(upgrade): detect_state 内省驱动状态检测"
```

---

## Task 2: `reconcile_schema` —— 漂移修复（stamp / 加可空列）

**Files:**
- Modify: `server/app/upgrade.py`
- Test: `server/tests/integration/test_upgrade.py`

- [ ] **Step 1: 写失败测试（两个用例：stamp 修复 + 加缺列）**

```python
# 追加到 test_upgrade.py
def test_reconcile_schema_stamps_when_current(tmp_path: Path):
    """漂移 DB（schema 到位、stamp 落后）→ stamp head，无 DDL 报错，列完好。"""
    from app.upgrade import reconcile_schema, _alembic_head

    db = tmp_path / "db" / "cost.sqlite"
    db.parent.mkdir(parents=True)
    eng = _engine(db)
    Base.metadata.create_all(eng)
    with eng.begin() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        conn.execute(text("INSERT INTO alembic_version VALUES ('4b7939b0712d')"))

    head = reconcile_schema(eng)

    with eng.connect() as conn:
        stamp = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert stamp == head == _alembic_head()
    # projects 表关键列仍在
    cols = {c["name"] for c in inspect(eng).get_columns("projects")}
    assert "measurement_method" in cols


def test_reconcile_schema_adds_missing_nullable_column(tmp_path: Path):
    """老库缺一可空列 → 加列 + 回填默认 + stamp head。"""
    from app.upgrade import reconcile_schema

    db = tmp_path / "db" / "cost.sqlite"
    db.parent.mkdir(parents=True)
    eng = _engine(db)
    Base.metadata.create_all(eng)
    # 制造"缺列"：物理删除 projects.selected_band（SQLite 3.35+ 支持 DROP COLUMN）
    with eng.begin() as conn:
        conn.execute(text("ALTER TABLE projects DROP COLUMN selected_band"))
    assert "selected_band" not in {c["name"] for c in inspect(eng).get_columns("projects")}

    reconcile_schema(eng)

    cols = {c["name"] for c in inspect(eng).get_columns("projects")}
    assert "selected_band" in cols
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd server && .venv/bin/pytest tests/integration/test_upgrade.py -k reconcile_schema -v`
Expected: FAIL，`ImportError: cannot import name 'reconcile_schema'`

- [ ] **Step 3: 写实现（追加到 upgrade.py）**

```python
def _alembic_head() -> str:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    return ScriptDirectory.from_config(Config(str(ini))).get_current_head()


def _stamp(engine, rev: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS alembic_version "
            "(version_num VARCHAR(32) NOT NULL)"
        ))
        conn.execute(text("DELETE FROM alembic_version"))
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
                     {"v": rev})


def _add_column(engine, table: str, col) -> None:
    """对已存在表加一列。仅可空/带默认的列可安全 ADD COLUMN(SQLite)。"""
    if not col.nullable and col.default is None and col.server_default is None:
        raise RuntimeError(
            f"无法自动加非空无默认列 {table}.{col.name}：该迁移非加性，"
            f"请在 upgrade.py 为对应 revision 加显式 handler"
        )
    coltype = col.type.compile(dialect=sqlite_dialect.dialect())
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col.name} {coltype}"))
        # 回填默认值，避免老行留 NULL 破坏计算
        if col.default is not None and getattr(col.default, "is_scalar", False):
            conn.execute(
                text(f"UPDATE {table} SET {col.name} = :d WHERE {col.name} IS NULL"),
                {"d": col.default.arg},
            )


def reconcile_schema(engine) -> str:
    """create_all 补缺失表 + 对已存在表补可空缺列 + stamp head。返回 head 修订号。"""
    Base.metadata.create_all(engine)            # 幂等补齐缺失【表】
    actual = _actual_columns(engine)
    for t in Base.metadata.sorted_tables:
        acols = actual.get(t.name, set())
        for col in t.columns:
            if col.name not in acols:
                _add_column(engine, t.name, col)
    head = _alembic_head()
    _stamp(engine, head)
    return head
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd server && .venv/bin/pytest tests/integration/test_upgrade.py -k reconcile_schema -v`
Expected: PASS（2 passed）

注：若运行环境 SQLite < 3.35（不支持 `DROP COLUMN`），`test_reconcile_schema_adds_missing_nullable_column` 的"制造缺列"步骤会失败——届时改用"建一张缺列的临时表"方式，但 macOS 自带 SQLite 与 Python 3.11 内置均 ≥ 3.39，通常无需处理。

- [ ] **Step 5: 提交**

```bash
git add server/app/upgrade.py server/tests/integration/test_upgrade.py
git commit -m "feat(upgrade): reconcile_schema 内省驱动漂移修复(stamp/加可空列)"
```

---

## Task 3: `reconcile_baseline` —— 基准重灯双路径 + 导出

**Files:**
- Modify: `server/app/upgrade.py`
- Test: `server/tests/integration/test_upgrade.py`

- [ ] **Step 1: 写失败测试（标准变更重置+导出 / 标准不变 reseed / override 不动）**

```python
# 追加到 test_upgrade.py
def _seed_db_with_standard(eng, version: str):
    """直接灌几行 params_global，模拟某标准的库。"""
    Base.metadata.create_all(eng)
    with eng.begin() as conn:
        conn.execute(text(
            "INSERT INTO params_global (key, value, basis_version, modified) VALUES "
            "('cf.budget', '1.39', :v, 1), "      # modified=True 旧改动
            "('city_rate.北京.dev', '32198', :v, 1), "
            "('hours_per_pm', '174', :v, 0)"
        ), {"v": version})


def test_baseline_standard_changed_full_reset_and_export(tmp_path: Path):
    from app.upgrade import detect_state, reconcile_baseline

    db = tmp_path / "db" / "cost.sqlite"
    db.parent.mkdir(parents=True)
    eng = _engine(db)
    _seed_db_with_standard(eng, "CSBMK®-202510")
    seed = _seed_json(tmp_path, version="SSM-BK-TEST")
    export_dir = tmp_path / "exports"

    state = detect_state(eng, seed)
    assert state.standard_changed is True
    res = reconcile_baseline(eng, seed, "20260531T193000", state, export_dir)

    assert res["path"] == "reset"
    # params_global 全部新标准
    with eng.connect() as conn:
        versions = {r[0] for r in conn.execute(text(
            "SELECT DISTINCT basis_version FROM params_global")).all()}
        budget = conn.execute(text(
            "SELECT value FROM params_global WHERE key='cf.budget'")).scalar()
    assert versions == {"SSM-BK-TEST"}
    assert json.loads(budget) == 1.7   # 旧 1.39 已被新标准覆盖
    # 导出文件
    exported = json.loads((export_dir / "upgrade-modified-params-20260531T193000.json")
                          .read_text(encoding="utf-8"))
    assert exported["from_standard"] == "CSBMK®-202510"
    assert exported["to_standard"] == "SSM-BK-TEST"
    assert exported["count"] == 2     # 两行 modified=True
    keys = {r["key"] for r in exported["modified_rows"]}
    assert keys == {"cf.budget", "city_rate.北京.dev"}


def test_baseline_standard_unchanged_reseed_unmodified(tmp_path: Path):
    from app.upgrade import detect_state, reconcile_baseline

    db = tmp_path / "db" / "cost.sqlite"
    db.parent.mkdir(parents=True)
    eng = _engine(db)
    _seed_db_with_standard(eng, "SSM-BK-TEST")   # 与 seed 同标准
    seed = _seed_json(tmp_path, version="SSM-BK-TEST")
    export_dir = tmp_path / "exports"

    state = detect_state(eng, seed)
    assert state.standard_changed is False
    res = reconcile_baseline(eng, seed, "20260531T193000", state, export_dir)

    assert res["path"] == "reseed"
    with eng.connect() as conn:
        # modified=True 行保留原值
        budget = conn.execute(text(
            "SELECT value FROM params_global WHERE key='cf.budget'")).scalar()
    assert json.loads(budget) == 1.39
    # 不产生导出文件
    assert not (export_dir / "upgrade-modified-params-20260531T193000.json").exists()


def test_param_override_untouched(tmp_path: Path):
    from app.upgrade import detect_state, reconcile_baseline

    db = tmp_path / "db" / "cost.sqlite"
    db.parent.mkdir(parents=True)
    eng = _engine(db)
    _seed_db_with_standard(eng, "CSBMK®-202510")
    # 测试 engine 未启用 FK（无 session.py 的 pragma 监听器），故无需真实 project 行
    with eng.begin() as conn:
        conn.execute(text(
            "INSERT INTO params_override (project_id, key, value) "
            "VALUES ('p1', 'cf.budget', '2.0')"))
    seed = _seed_json(tmp_path, version="SSM-BK-TEST")

    state = detect_state(eng, seed)
    reconcile_baseline(eng, seed, "20260531T193000", state, tmp_path / "exports")

    with eng.connect() as conn:
        ov = conn.execute(text(
            "SELECT value FROM params_override WHERE project_id='p1' AND key='cf.budget'"
        )).scalar()
    assert json.loads(ov) == 2.0   # 按项目覆盖原样幸存
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd server && .venv/bin/pytest tests/integration/test_upgrade.py -k baseline -o "addopts=" -v`
Expected: FAIL，`ImportError: cannot import name 'reconcile_baseline'`

- [ ] **Step 3: 写实现（追加到 upgrade.py）**

```python
def _export_modified(engine, out_path: Path, from_std: str, to_std: str, ts: str) -> int:
    from app.db.models import ParamGlobal

    Sess = sessionmaker(bind=engine)
    with Sess() as s:
        rows = s.query(ParamGlobal).filter_by(modified=True).all()
        payload = {
            "exported_at": ts,
            "from_standard": from_std,
            "to_standard": to_std,
            "count": len(rows),
            "modified_rows": [
                {"key": r.key, "value": json.loads(r.value),
                 "basis_version": r.basis_version}
                for r in rows
            ],
        }
        n = len(rows)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    return n


def reconcile_baseline(engine, seed_path: Path, ts: str, state: UpgradeState,
                       export_dir: Path) -> dict:
    """标准变更→导出 modified + 全量重置；不变→reseed 未改动行。绝不碰 params_override。"""
    from app.db.models import ParamGlobal

    Sess = sessionmaker(bind=engine)
    if state.standard_changed:
        from_std = sorted(state.basis_db)[0] if state.basis_db else "unknown"
        export_path = export_dir / f"upgrade-modified-params-{ts}.json"
        n_exported = _export_modified(engine, export_path, from_std,
                                      state.basis_target, ts)
        raw = json.loads(seed_path.read_text(encoding="utf-8"))
        flat: dict = {}
        _flatten("", raw, flat)
        with Sess() as s:
            s.query(ParamGlobal).delete()
            for k, v in flat.items():
                s.add(ParamGlobal(
                    key=k, value=json.dumps(v, ensure_ascii=False),
                    basis_version=state.basis_target, modified=False))
            s.commit()
        return {"path": "reset", "exported": n_exported,
                "export_file": str(export_path), "seeded": len(flat)}

    with Sess() as s:
        n = reseed_if_outdated(s, seed_path=seed_path)
    return {"path": "reseed", "reseeded": n}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd server && .venv/bin/pytest tests/integration/test_upgrade.py -k "baseline or override" -o "addopts=" -v`
Expected: PASS（3 passed）

- [ ] **Step 5: 提交**

```bash
git add server/app/upgrade.py server/tests/integration/test_upgrade.py
git commit -m "feat(upgrade): reconcile_baseline 双路径(重置+导出/reseed)"
```

---

## Task 4: `backup_db` —— WAL 落盘 + 时间戳备份

**Files:**
- Modify: `server/app/upgrade.py`
- Test: `server/tests/integration/test_upgrade.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 test_upgrade.py
def test_backup_db_created(tmp_path: Path):
    from app.upgrade import backup_db

    db = tmp_path / "db" / "cost.sqlite"
    db.parent.mkdir(parents=True)
    eng = _engine(db)
    Base.metadata.create_all(eng)
    eng.dispose()

    bak = backup_db(db, "20260531T193000")
    assert bak.exists()
    assert bak.name == "cost.sqlite.pre-upgrade-20260531T193000.bak"
    assert bak.stat().st_size > 0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd server && .venv/bin/pytest tests/integration/test_upgrade.py::test_backup_db_created -o "addopts=" -v`
Expected: FAIL，`ImportError: cannot import name 'backup_db'`

- [ ] **Step 3: 写实现（追加到 upgrade.py）**

```python
def backup_db(db_path: Path, ts: str) -> Path:
    """WAL checkpoint 落盘后复制为时间戳备份。返回备份路径。"""
    eng = create_engine(f"sqlite:///{db_path}")
    with eng.begin() as conn:
        conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
    eng.dispose()
    bak = db_path.with_name(f"{db_path.name}.pre-upgrade-{ts}.bak")
    shutil.copy2(db_path, bak)
    return bak
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd server && .venv/bin/pytest tests/integration/test_upgrade.py::test_backup_db_created -o "addopts=" -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add server/app/upgrade.py server/tests/integration/test_upgrade.py
git commit -m "feat(upgrade): backup_db WAL落盘+时间戳备份"
```

---

## Task 5: `cli` —— 编排入口 + 幂等 + 错误处理

**Files:**
- Modify: `server/app/upgrade.py`
- Test: `server/tests/integration/test_upgrade.py`

- [ ] **Step 1: 写失败测试（端到端 + 幂等 + 缺库报错）**

```python
# 追加到 test_upgrade.py
def test_cli_end_to_end_then_idempotent(tmp_path: Path):
    """端到端：漂移+旧标准库 → 一次升级到位；再跑一次为 no-op、不丢数据。"""
    from app.upgrade import cli, _alembic_head

    db = tmp_path / "db" / "cost.sqlite"
    db.parent.mkdir(parents=True)
    eng = _engine(db)
    _seed_db_with_standard(eng, "CSBMK®-202510")
    with eng.begin() as conn:   # 落后的 stamp
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        conn.execute(text("INSERT INTO alembic_version VALUES ('4b7939b0712d')"))
    eng.dispose()
    seed = _seed_json(tmp_path, version="SSM-BK-TEST")

    runner = CliRunner()
    r1 = runner.invoke(cli, ["--db", str(db), "--seed", str(seed), "--ts", "T1"])
    assert r1.exit_code == 0, r1.output
    assert "升级完成" in r1.output

    eng = _engine(db)
    with eng.connect() as conn:
        stamp = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        versions = {r[0] for r in conn.execute(text(
            "SELECT DISTINCT basis_version FROM params_global")).all()}
        n1 = conn.execute(text("SELECT count(*) FROM params_global")).scalar()
    assert stamp == _alembic_head()
    assert versions == {"SSM-BK-TEST"}
    eng.dispose()

    # 再跑：标准已是 SSM-BK-TEST → reseed 路径，no-op，不丢数据
    r2 = runner.invoke(cli, ["--db", str(db), "--seed", str(seed), "--ts", "T2"])
    assert r2.exit_code == 0, r2.output
    eng = _engine(db)
    with eng.connect() as conn:
        n2 = conn.execute(text("SELECT count(*) FROM params_global")).scalar()
    assert n2 == n1


def test_cli_refuses_when_db_missing(tmp_path: Path):
    from app.upgrade import cli

    seed = _seed_json(tmp_path)
    runner = CliRunner()
    r = runner.invoke(cli, ["--db", str(tmp_path / "nope.sqlite"),
                            "--seed", str(seed), "--ts", "T1"])
    assert r.exit_code == 2
    assert "请先 /setup" in r.output
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd server && .venv/bin/pytest tests/integration/test_upgrade.py -k cli -o "addopts=" -v`
Expected: FAIL，`ImportError: cannot import name 'cli'`

- [ ] **Step 3: 写实现（追加到 upgrade.py）**

```python
@click.command()
@click.option("--db", "db_path", required=True, type=click.Path(path_type=Path),
              help="SQLite 数据库路径")
@click.option("--seed", "seed_path", required=True, type=click.Path(path_type=Path),
              help="基准 seed JSON 路径")
@click.option("--ts", required=True, help="时间戳(命令层注入, 用于备份/导出命名)")
@click.option("--yes", is_flag=True, default=False, help="非交互模式")
def cli(db_path: Path, seed_path: Path, ts: str, yes: bool) -> None:
    """把既有 DB 升级到当前代码版本（备份 + schema 修复 + 基准重灯）。"""
    if not db_path.exists():
        click.echo(f"✗ 数据库不存在: {db_path}（升级≠首装，请先 /setup）", err=True)
        sys.exit(2)
    if not seed_path.exists():
        click.echo(f"✗ seed 文件不存在: {seed_path}", err=True)
        sys.exit(2)

    engine = create_engine(f"sqlite:///{db_path}",
                           connect_args={"check_same_thread": False})
    state = detect_state(engine, seed_path)
    head = _alembic_head()
    click.echo(f"升级计划: schema stamp {state.stamp_rev} → {head} "
               f"(已到位={state.schema_at_head}, 缺表={len(state.missing_tables)}, "
               f"缺列={len(state.missing_cols)})")
    click.echo(f"          基准 {sorted(state.basis_db) or '空'} → {state.basis_target} "
               f"(标准变更={state.standard_changed})")

    bak = None
    try:
        bak = backup_db(db_path, ts)
        click.echo(f"✓ 备份: {bak}")
        reconcile_schema(engine)
        click.echo(f"✓ schema 已对齐 head={head}")
        export_dir = db_path.parent.parent / "exports"
        res = reconcile_baseline(engine, seed_path, ts, state, export_dir)
        if res["path"] == "reset":
            click.echo(f"✓ 基准全量重置 → {res['seeded']} 行；"
                       f"导出旧改动 {res['exported']} 条 → {res['export_file']}")
        else:
            click.echo(f"✓ 基准 reseed 未改动行 {res['reseeded']} 条（标准未变）")
        click.echo("✓ 升级完成。运行 /cost 启动。")
    except Exception as e:  # noqa: BLE001
        click.echo(f"✗ 升级失败: {e}", err=True)
        if bak:
            click.echo(f"  恢复命令: cp {bak} {db_path}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
```

- [ ] **Step 4: 跑测试确认通过 + 全文件回归**

Run: `cd server && .venv/bin/pytest tests/integration/test_upgrade.py -o "addopts=" -v`
Expected: PASS（9 passed：detect 1 + schema 2 + baseline/override 3 + backup 1 + cli 2）

- [ ] **Step 5: 提交**

```bash
git add server/app/upgrade.py server/tests/integration/test_upgrade.py
git commit -m "feat(upgrade): cli 编排入口(检测/备份/修复/重灯)+幂等+错误处理"
```

---

## Task 6: `commands/cost-upgrade.md` —— 薄命令壳

**Files:**
- Create: `commands/cost-upgrade.md`

- [ ] **Step 1: 写命令文件**

```markdown
---
description: 升级既有安装：备份 + alembic 迁移 + 基准重灯(SSM-BK-202509) + 刷新 venv/前端
allowed-tools: Bash, Read
---

执行以下步骤，按顺序：

1. 路径检测 + 数据目录（与 setup 一致，兼容 marketplace 与旧扁平布局）：
   ```bash
   PLUGIN_DIR="${CLAUDE_PLUGIN_ROOT:-}"
   if [ -z "$PLUGIN_DIR" ] || [ ! -d "$PLUGIN_DIR/server" ]; then
     PLUGIN_DIR=$(ls -d "$HOME"/.claude/plugins/cache/*/cost-estimation/*/ 2>/dev/null | sort -V | tail -1)
     PLUGIN_DIR="${PLUGIN_DIR%/}"
   fi
   [ -d "$PLUGIN_DIR/server" ] || PLUGIN_DIR="$HOME/.claude/plugins/cache/cost-estimation"
   [ -d "$PLUGIN_DIR/server" ] || PLUGIN_DIR="$HOME/.claude/plugins/data/cost-estimation"
   [ -d "$PLUGIN_DIR/server" ] || { echo "✗ 未找到插件安装目录"; exit 1; }
   DATA_DIR="$HOME/.claude/projects/cost-estimation"
   DB="$DATA_DIR/db/cost.sqlite"
   [ -f "$DB" ] || { echo "✗ 未找到数据库（升级≠首装），请先 /cost-estimation:setup"; exit 1; }
   ```

2. 停止运行中的后端（升级不可对活库动手）：
   ```bash
   if [ -f "$DATA_DIR/.pid" ]; then
     PID=$(cat "$DATA_DIR/.pid")
     if kill -0 "$PID" 2>/dev/null; then
       kill "$PID"; for i in 1 2 3 4 5; do kill -0 "$PID" 2>/dev/null || break; sleep 1; done
       kill -0 "$PID" 2>/dev/null && kill -9 "$PID"
       echo "✓ 已停止后端 PID=$PID"
     fi
   fi
   rm -f "$DATA_DIR/.pid" "$DATA_DIR/.token" "$DATA_DIR/.port"
   ```

3. 确保 venv(≥3.11) 并刷新依赖：
   ```bash
   cd "$PLUGIN_DIR/server"
   PYBIN=""
   for cand in python3.13 python3.12 python3.11 python3; do
     command -v "$cand" >/dev/null 2>&1 || continue
     v=$("$cand" -c 'import sys;print(sys.version_info[0]*100+sys.version_info[1])' 2>/dev/null)
     if [ -n "$v" ] && [ "$v" -ge 311 ]; then PYBIN="$cand"; break; fi
   done
   [ -z "$PYBIN" ] && { echo "✗ 未找到 Python ≥ 3.11"; exit 1; }
   [ -d ".venv" ] || "$PYBIN" -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt --quiet -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

4. 执行升级编排（备份 + schema 修复 + 基准重灯）：
   ```bash
   TS=$(date +%Y%m%dT%H%M%S)
   python -m app.upgrade \
     --db "$DB" \
     --seed "$PLUGIN_DIR/server/app/data/ssm_bk_202509.json" \
     --ts "$TS"
   ```

5. 前端 fallback（仓库通常已携带 web/dist/）：
   ```bash
   if [ ! -f "$PLUGIN_DIR/web/dist/index.html" ]; then
     echo "⚠ 未找到 web/dist/，尝试本地构建..."
     if command -v pnpm >/dev/null 2>&1; then
       cd "$PLUGIN_DIR/web" && pnpm install --silent && pnpm build || { echo "✗ 前端构建失败"; exit 1; }
     elif command -v npm >/dev/null 2>&1; then
       cd "$PLUGIN_DIR/web" && npm install --silent && npm run build || { echo "✗ 前端构建失败"; exit 1; }
     else
       echo "✗ 缺少 pnpm/npm，无法构建前端。"; exit 1
     fi
   fi
   ```

6. 报告："✓ 升级完成。历史项目需重新触发一次计算才反映新基准口径。运行 /cost 启动。"
```

- [ ] **Step 2: 手动验证命令文件语法（无可执行测试，做静态检查）**

Run: `bash -n <(sed -n '/```bash/,/```/p' commands/cost-upgrade.md | grep -v '```')`
Expected: 无语法错误输出（退出码 0）

- [ ] **Step 3: 提交**

```bash
git add commands/cost-upgrade.md
git commit -m "feat(upgrade): /cost-upgrade 薄命令壳(路径/停服/venv/编排/前端)"
```

---

## Task 7: 注册命令 + 文档

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Modify: `docs/v2-changelog.md`
- Modify: `README.md`

- [ ] **Step 1: 在 plugin.json 的 commands 数组注册**

把 `.claude-plugin/plugin.json` 的 `commands` 段改为（在 `cost-stop.md` 后加一行）：

```json
  "commands": [
    "./commands/setup.md",
    "./commands/cost.md",
    "./commands/cost-allocate.md",
    "./commands/cost-stop.md",
    "./commands/cost-upgrade.md"
  ],
```

- [ ] **Step 2: 在 docs/v2-changelog.md 的「安装与初始化修复」补丁子段后追加**

在 v2.9 段的补丁子段表格后插入：

```markdown
### 升级命令（2026-05-31 patch）

| # | 描述 |
|---|---|
| P5 | **新增 `/cost-upgrade`** —— 既有安装的升级路径：备份 DB（WAL 落盘 + 时间戳副本）→ 内省驱动的 alembic 漂移修复（schema 到位则 `stamp head`，缺可空列则加列回填，避开重放迁移链崩溃）→ 基准重灯（标准变更如 CSBMK→SSM 则导出 modified 行 + 全量重置 + 清死键；标准不变则 reseed 未改动行）→ 刷新 venv 依赖 + 前端。逻辑在可测的 `server/app/upgrade.py`，命令文件保持薄壳。铁律：`params_override` 永不触碰、备份先于变更、失败不自动回滚而给恢复命令 |
```

- [ ] **Step 3: 在 README.md 命令表补一行**

找到 README.md 的命令/模式表格，在 `/cost-stop` 行后加：

```markdown
| `/cost-upgrade` | 升级既有安装：备份 + alembic 迁移 + 基准重灯 + 刷新依赖/前端 |
```

（若 README 表格列结构不同，按其实际表头对齐填写——保留"命令"与"说明"两列语义。）

- [ ] **Step 4: 全后端测试回归**

Run: `cd server && .venv/bin/pytest -q`
Expected: PASS（既有 363 + 新增 9 = 372 左右，无回归失败）

- [ ] **Step 5: 提交**

```bash
git add .claude-plugin/plugin.json docs/v2-changelog.md README.md
git commit -m "feat(upgrade): 注册 /cost-upgrade 命令 + changelog/README"
```

---

## 完成标准

- [ ] `server/app/upgrade.py` 全部函数有对应测试，`test_upgrade.py` 9 项全绿
- [ ] 全后端套件无回归
- [ ] `/cost-upgrade` 已在 plugin.json 注册
- [ ] changelog + README 已更新
- [ ] 命令在现网 DB 上实跑一次（手动验收）：漂移 stamp 被修正为 head、基准为 SSM、备份与导出文件生成、`param_override` 不变

> 手动验收建议在合并前于真实环境跑一遍 `/cost-upgrade`，确认与 spec 行为一致（现网 DB 已是 SSM-BK-202509，应走 reseed 路径、no-op）。
