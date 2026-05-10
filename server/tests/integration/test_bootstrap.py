"""集成：app.bootstrap 应能初始化 SQLite + 装载 CSBMK seed。

Plan 1 实际 params_global schema: (key, value, basis_version, modified, updated_at)。
Plan 1 服务层（app.services.params.seed_from_csbmk）将 seed JSON 扁平化为
多行 key/value 存储；本 bootstrap CLI 与该约定保持一致。
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.fixture
def seed_file(tmp_path: Path) -> Path:
    seed = tmp_path / "csbmk-test.json"
    seed.write_text(
        json.dumps(
            {
                "version": "TEST-202510",
                "effective_date": "2025-10-01",
                "productivity": {
                    "dev": {"全行业": {"P10": 2.0, "P50": 6.7, "P90": 17.0}},
                    "ops": {"全行业": {"P10": 0.2, "P50": 0.7, "P90": 2.0}},
                },
                "city_rate": {"北京": {"dev": 32198, "ops": 26335, "class": "A"}},
                "cf": {"bidding": 1.21},
                "factors_dev": {"app_type": {"业务处理": 1.0}},
                "factors_ops": {"update_freq": {"monthly": 1.0}},
                "hours_per_pm": 174,
                "ops_cost_ratio": {"P50": 0.0902},
            }
        ),
        encoding="utf-8",
    )
    return seed


def test_bootstrap_creates_schema_and_seeds(tmp_path: Path, seed_file: Path):
    from app.bootstrap import cli

    db_path = tmp_path / "cost.sqlite"
    runner = CliRunner()
    result = runner.invoke(cli, ["--db", str(db_path), "--seed", str(seed_file)])

    assert result.exit_code == 0, result.output
    assert "✓" in result.output
    assert db_path.exists()

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    tables = {
        row[0]
        for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    # 至少应含 plan 1 创建的核心表
    assert "projects" in tables
    assert "params_global" in tables
    assert "function_points" in tables
    assert "params_override" in tables
    assert "results" in tables
    assert "uploads" in tables
    assert "fp_snapshots" in tables

    # 扁平化 seed 后，'version' key 直接存为 JSON 字符串
    cur.execute("SELECT value FROM params_global WHERE key = 'version'")
    row = cur.fetchone()
    assert row is not None, "扁平化后应有 key='version' 的行"
    assert json.loads(row[0]) == "TEST-202510"

    # basis_version 列也应记录版本号
    cur.execute("SELECT DISTINCT basis_version FROM params_global")
    versions = {r[0] for r in cur.fetchall()}
    assert "TEST-202510" in versions

    # 验证扁平化粒度：city_rate.北京.dev 应能直接定位
    cur.execute(
        "SELECT value FROM params_global WHERE key = 'city_rate.北京.dev'"
    )
    row = cur.fetchone()
    assert row is not None
    assert json.loads(row[0]) == 32198

    con.close()


def test_bootstrap_idempotent(tmp_path: Path, seed_file: Path):
    """二次运行不应破坏已有数据，且应跳过 seed 装载。"""
    from app.bootstrap import cli

    db_path = tmp_path / "cost.sqlite"
    runner = CliRunner()

    r1 = runner.invoke(cli, ["--db", str(db_path), "--seed", str(seed_file)])
    assert r1.exit_code == 0, r1.output

    # 创建一个用户项目（按 Plan 1 实际 Project schema）
    project_id = str(uuid.uuid4())
    con = sqlite3.connect(str(db_path))
    con.execute(
        """INSERT INTO projects
        (id, name, project_type, phase, city, industry, mode, basis_data_ver)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            project_id,
            "user-data",
            "dev_only",
            "bidding",
            "北京",
            "全行业",
            "forward",
            "TEST-202510",
        ),
    )
    con.commit()
    con.close()

    r2 = runner.invoke(cli, ["--db", str(db_path), "--seed", str(seed_file)])
    assert r2.exit_code == 0, r2.output
    assert "已存在" in r2.output or "skip" in r2.output.lower()

    # 用户数据未被破坏
    con = sqlite3.connect(str(db_path))
    cur = con.execute("SELECT count(*) FROM projects WHERE name=?", ("user-data",))
    assert cur.fetchone()[0] == 1
    con.close()


def test_bootstrap_missing_seed_fails(tmp_path: Path):
    from app.bootstrap import cli

    db_path = tmp_path / "cost.sqlite"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--db", str(db_path), "--seed", str(tmp_path / "nonexistent.json")],
    )
    assert result.exit_code != 0
    combined = (result.output + (str(result.exception) if result.exception else "")).lower()
    assert "seed" in combined or "not found" in combined
