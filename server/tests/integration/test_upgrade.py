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
