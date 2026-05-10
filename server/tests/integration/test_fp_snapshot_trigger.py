import json

import pytest
from sqlalchemy import create_engine, text

from app.db import models  # noqa: F401  触发模型注册
from app.db.session import Base


@pytest.fixture
def db_engine(tmp_path):
    db_file = tmp_path / "trigger-test.sqlite"
    engine = create_engine(
        f"sqlite:///{db_file}", connect_args={"check_same_thread": False}
    )
    # 应用 metadata + trigger
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(
            text(
                """
                CREATE TRIGGER trim_fp_snapshots AFTER INSERT ON fp_snapshots
                BEGIN
                  DELETE FROM fp_snapshots
                  WHERE project_id = NEW.project_id
                    AND id NOT IN (
                      SELECT id FROM fp_snapshots
                      WHERE project_id = NEW.project_id
                      ORDER BY id DESC LIMIT 5
                    );
                END
                """
            )
        )
        conn.commit()
    return engine


def test_trigger_keeps_only_last_five_per_project(db_engine):
    with db_engine.connect() as conn:
        # 先建一个项目
        conn.execute(
            text(
                "INSERT INTO projects (id, name, project_type, phase, city, industry, mode, basis_data_ver) "
                "VALUES ('p1', 'P1', 'dev_only', 'bidding', '北京', '电子政务', 'forward', 'CSBMK')"
            )
        )
        conn.commit()
        # 插入 7 个快照
        for v in range(1, 8):
            conn.execute(
                text(
                    "INSERT INTO fp_snapshots (project_id, version, snapshot_json, reason) "
                    "VALUES ('p1', :v, :j, 'test')"
                ),
                {"v": v, "j": json.dumps({})},
            )
        conn.commit()
        result = conn.execute(
            text(
                "SELECT version FROM fp_snapshots WHERE project_id='p1' ORDER BY version"
            )
        ).fetchall()
        versions = [r[0] for r in result]
        # 触发器保留前 5 版（最新的 5 个 = version 3-7）
        assert len(versions) == 5
        assert versions == [3, 4, 5, 6, 7]


def test_trigger_isolates_projects(db_engine):
    with db_engine.connect() as conn:
        # 两个项目
        conn.execute(
            text(
                "INSERT INTO projects (id, name, project_type, phase, city, industry, mode, basis_data_ver) "
                "VALUES ('p1', 'P1', 'dev_only', 'bidding', '北京', '电子政务', 'forward', 'CSBMK')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO projects (id, name, project_type, phase, city, industry, mode, basis_data_ver) "
                "VALUES ('p2', 'P2', 'dev_only', 'bidding', '北京', '电子政务', 'forward', 'CSBMK')"
            )
        )
        conn.commit()
        # p1 插入 3 个，p2 插入 8 个
        for v in range(1, 4):
            conn.execute(
                text(
                    "INSERT INTO fp_snapshots (project_id, version, snapshot_json, reason) "
                    "VALUES ('p1', :v, '{}', 't')"
                ),
                {"v": v},
            )
        for v in range(1, 9):
            conn.execute(
                text(
                    "INSERT INTO fp_snapshots (project_id, version, snapshot_json, reason) "
                    "VALUES ('p2', :v, '{}', 't')"
                ),
                {"v": v},
            )
        conn.commit()
        # p1 应保留全部 3 个（不到 5 个上限）
        p1 = conn.execute(
            text("SELECT COUNT(*) FROM fp_snapshots WHERE project_id='p1'")
        ).scalar()
        # p2 应保留 5 个（最新 4-8）
        p2 = conn.execute(
            text("SELECT COUNT(*) FROM fp_snapshots WHERE project_id='p2'")
        ).scalar()
        assert p1 == 3
        assert p2 == 5
