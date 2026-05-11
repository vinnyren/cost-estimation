"""GAP-H foundation: ParamSnapshot 表 + 模型，给 ParamManager 快照 tab 用。"""
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
