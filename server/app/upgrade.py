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
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.dialects import sqlite as sqlite_dialect
from sqlalchemy.engine import Engine

from app.db import models as _models  # noqa: F401  确保模型注册到 Base.metadata
from app.db.session import Base


@dataclass(frozen=True)
class UpgradeState:
    stamp_rev: str | None
    schema_at_head: bool
    missing_tables: list[str] = field(default_factory=list)
    missing_cols: list[tuple[str, str]] = field(default_factory=list)  # (table, column)
    basis_db: set[str] = field(default_factory=set)
    basis_target: str = ""
    standard_changed: bool = False


def _actual_columns(engine: Engine) -> dict[str, set[str]]:
    insp = inspect(engine)
    return {t: {c["name"] for c in insp.get_columns(t)} for t in insp.get_table_names()}


def detect_state(engine: Engine, seed_path: Path) -> UpgradeState:
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
        # basis_db 为空(全新/仅 user 行) → standard_changed=False，视作首装而非漂移
        standard_changed=bool(basis_db) and basis_target not in basis_db,
    )


def _alembic_head() -> str | None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    return ScriptDirectory.from_config(Config(str(ini))).get_current_head()


def _stamp(engine: Engine, rev: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS alembic_version "
            "(version_num VARCHAR(32) NOT NULL)"
        ))
        conn.execute(text("DELETE FROM alembic_version"))
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
                     {"v": rev})


def _add_column(engine: Engine, table: str, col) -> None:
    """对已存在表加一列。仅可空/带默认的列可安全 ADD COLUMN(SQLite)。

    用 CreateColumn 渲染完整列 DDL（含 DEFAULT/NOT NULL），使带 server_default 的
    NOT NULL 列能被 SQLite 用默认值回填现有行；ORM python-side(default=) 标量默认值
    在 ADD COLUMN 后另行 UPDATE 回填。
    """
    if not col.nullable and col.default is None and col.server_default is None:
        raise RuntimeError(
            f"无法自动加非空无默认列 {table}.{col.name}：该迁移非加性，"
            f"请在 upgrade.py 为对应 revision 加显式 handler"
        )
    from sqlalchemy.schema import CreateColumn

    col_spec = CreateColumn(col).compile(dialect=sqlite_dialect.dialect()).string
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_spec}"))
        # ORM python-side 标量默认值(server_default=None 时)：回填老行 NULL
        if col.default is not None and getattr(col.default, "is_scalar", False):
            conn.execute(
                text(f"UPDATE {table} SET {col.name} = :d WHERE {col.name} IS NULL"),
                {"d": col.default.arg},
            )


def reconcile_schema(engine: Engine) -> str:
    """create_all 补缺失表 + 对已存在表补可空缺列 + stamp head。返回 head 修订号。"""
    Base.metadata.create_all(engine)            # 幂等补齐缺失【表】
    actual = _actual_columns(engine)
    for t in Base.metadata.sorted_tables:
        acols = actual.get(t.name, set())
        for col in t.columns:
            if col.name not in acols:
                _add_column(engine, t.name, col)
    head = _alembic_head()
    if head is None:
        raise RuntimeError("alembic 无 head revision，请检查 alembic/versions 迁移脚本")
    _stamp(engine, head)
    return head
