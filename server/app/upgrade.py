"""插件升级编排：把既有数据目录安全推进到当前代码版本。

用法：
  python -m app.upgrade --db <db> --seed <seed.json> --ts <timestamp>

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
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.bootstrap import _flatten, reseed_if_outdated
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
    """对已存在表加一列。仅可空、或带 python-side 标量默认值、或带字面量
    server_default 的列可安全 ADD COLUMN(SQLite)。

    非空且无字面量默认值的列（含 func.now() 等非常量 server_default）无法被
    SQLite 安全 ADD COLUMN——视作非加性迁移，主动抛错要求加显式 handler，
    避免抛出晦涩的 SQLite "non-constant default" 错误。

    用 CreateColumn 渲染完整列 DDL（含 DEFAULT/NOT NULL），使带字面量 server_default
    的 NOT NULL 列能被 SQLite 用默认值回填现有行；ORM python-side(default=) 标量默认值
    在 ADD COLUMN 后另行 UPDATE 回填。
    """
    server_default_literal = (
        col.server_default is not None
        and isinstance(getattr(col.server_default, "arg", None), str)
    )
    if not col.nullable and col.default is None and not server_default_literal:
        raise RuntimeError(
            f"无法自动加列 {table}.{col.name}（非空且无字面量默认值，"
            f"可能是 func.now() 等非常量 server_default）：该迁移非加性，"
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


def _export_modified(engine: Engine, out_path: Path, from_std: str, to_std: str, ts: str) -> int:
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


def reconcile_baseline(engine: Engine, seed_path: Path, ts: str, state: UpgradeState,
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


def backup_db(db_path: Path, ts: str) -> Path:
    """WAL checkpoint 落盘后复制为时间戳备份。返回备份路径。"""
    eng = create_engine(f"sqlite:///{db_path}")
    with eng.begin() as conn:
        conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
    eng.dispose()
    bak = db_path.with_name(f"{db_path.name}.pre-upgrade-{ts}.bak")
    shutil.copy2(db_path, bak)
    return bak


@click.command()
@click.option("--db", "db_path", required=True, type=click.Path(path_type=Path),
              help="SQLite 数据库路径")
@click.option("--seed", "seed_path", required=True, type=click.Path(path_type=Path),
              help="基准 seed JSON 路径")
@click.option("--ts", required=True, help="时间戳(命令层注入, 用于备份/导出命名)")
def cli(db_path: Path, seed_path: Path, ts: str) -> None:
    """把既有 DB 升级到当前代码版本（备份 + schema 修复 + 基准重灯）。"""
    if not db_path.exists():
        click.echo(f"✗ 数据库不存在: {db_path}（升级≠首装，请先 /setup）", err=True)
        sys.exit(2)
    if not seed_path.exists():
        click.echo(f"✗ seed 文件不存在: {seed_path}", err=True)
        sys.exit(2)

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    with engine.begin() as conn:
        conn.execute(text("PRAGMA journal_mode = WAL"))
        conn.execute(text("PRAGMA busy_timeout = 5000"))
        conn.execute(text("PRAGMA foreign_keys = ON"))
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
        # 约定: db_path = <data_dir>/db/<name>.sqlite → exports 落在 <data_dir>/exports/
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
