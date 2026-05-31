"""/cost-upgrade 升级编排回归。"""
import json
from pathlib import Path

from click.testing import CliRunner
from sqlalchemy import create_engine, text

from app.db.session import Base
from app.db import models as _models  # noqa: F401  注册模型


def _seed_db_with_standard(eng, version: str):
    """直接灌几行 params_global，模拟某标准的库。"""
    Base.metadata.create_all(eng)
    with eng.begin() as conn:
        conn.execute(text(
            "INSERT INTO params_global (key, value, basis_version, modified) VALUES "
            "('cf.budget', '1.39', :v, 1), "
            "('city_rate.北京.dev', '32198', :v, 1), "
            "('hours_per_pm', '174', :v, 0)"
        ), {"v": version})


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


def test_reconcile_schema_backfills_server_default_on_existing_rows(tmp_path: Path):
    """老库有数据行且缺 server_default NOT NULL 列 → 加列后老行被填默认值(非 NULL)。"""
    from app.upgrade import reconcile_schema
    from sqlalchemy import inspect

    db = tmp_path / "db" / "cost.sqlite"
    db.parent.mkdir(parents=True)
    eng = _engine(db)
    Base.metadata.create_all(eng)
    with eng.begin() as conn:
        conn.execute(text("ALTER TABLE projects DROP COLUMN selected_band"))
        # projects 有多列 NOT NULL 无默认值，INSERT 需全部提供
        conn.execute(text(
            "INSERT INTO projects (id, name, project_type, phase, city, industry, mode, basis_data_ver)"
            " VALUES ('p1', 'demo', 'web', 'plan', 'bj', 'finance', 'normal', 'SSM-BK-TEST')"
        ))

    reconcile_schema(eng)

    with eng.connect() as conn:
        val = conn.execute(text("SELECT selected_band FROM projects WHERE id='p1'")).scalar()
    assert val == "P50", f"expected 'P50' but got {val!r}"  # 被 server_default 回填，而非 NULL
    assert "selected_band" in {c["name"] for c in inspect(eng).get_columns("projects")}


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
    with eng.connect() as conn:
        versions = {r[0] for r in conn.execute(text(
            "SELECT DISTINCT basis_version FROM params_global")).all()}
        budget = conn.execute(text(
            "SELECT value FROM params_global WHERE key='cf.budget'")).scalar()
    assert versions == {"SSM-BK-TEST"}
    assert json.loads(budget) == 1.7   # 旧 1.39 已被新标准覆盖
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
        budget = conn.execute(text(
            "SELECT value FROM params_global WHERE key='cf.budget'")).scalar()
    assert json.loads(budget) == 1.39   # modified=True 行保留原值
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
    assert (db.parent / "cost.sqlite.pre-upgrade-T2.bak").exists()
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


def test_cli_reports_recovery_command_on_failure(tmp_path: Path, monkeypatch):
    import app.upgrade as up
    from app.upgrade import cli

    db = tmp_path / "db" / "cost.sqlite"
    db.parent.mkdir(parents=True)
    eng = _engine(db)
    _seed_db_with_standard(eng, "CSBMK®-202510")
    eng.dispose()
    seed = _seed_json(tmp_path, version="SSM-BK-TEST")

    def _boom(engine):
        raise RuntimeError("schema 炸了")
    monkeypatch.setattr(up, "reconcile_schema", _boom)

    runner = CliRunner()
    r = runner.invoke(cli, ["--db", str(db), "--seed", str(seed), "--ts", "TF"])
    assert r.exit_code == 1
    assert "升级失败" in r.output
    assert "恢复命令: cp" in r.output
    # 备份已先于失败生成
    assert (db.parent / "cost.sqlite.pre-upgrade-TF.bak").exists()
