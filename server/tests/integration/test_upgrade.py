"""/cost-upgrade 升级编排回归。"""
import json
from pathlib import Path

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
    from sqlalchemy import inspect
    cols = {c["name"] for c in inspect(eng).get_columns("projects")}
    assert "measurement_method" in cols


def test_reconcile_schema_adds_missing_nullable_column(tmp_path: Path):
    """老库缺一可空列 → 加列 + 回填默认 + stamp head。"""
    from app.upgrade import reconcile_schema
    from sqlalchemy import inspect

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
