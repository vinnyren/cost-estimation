"""GAP-B foundation: Project 加 factors_dev_json / factors_ops_json 列。"""
import json
import uuid
import pytest


@pytest.fixture
def db(monkeypatch, tmp_path):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    monkeypatch.setenv("COST_DB_PATH", f"/tmp/cost-test-{uuid.uuid4()}.sqlite")
    monkeypatch.setenv("COST_DATA_DIR", str(tmp_path))
    import importlib
    for m in ["app.config", "app.db.session", "app.db.models",
              "app.services.params"]:
        importlib.reload(importlib.import_module(m))
    from app.db.session import Base, engine, SessionLocal
    Base.metadata.create_all(bind=engine)
    import app.services.params
    app.services.params.seed_from_csbmk()
    s = SessionLocal()
    yield s
    s.close()


def test_project_has_factors_columns(db):
    from app.db.models import Project
    p = Project(
        id="p1", name="T", project_type="dev_only", phase="bidding",
        city="北京", industry="电子政务", mode="forward",
        basis_data_ver="CSBMK®-202510",
        factors_dev_json=json.dumps({"app_type": "OLTP"}),
        factors_ops_json=None,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    assert json.loads(p.factors_dev_json) == {"app_type": "OLTP"}
    assert p.factors_ops_json is None


def test_project_factors_default_null(db):
    from app.db.models import Project
    p = Project(
        id="p2", name="T2", project_type="dev_only", phase="bidding",
        city="北京", industry="电子政务", mode="forward",
        basis_data_ver="CSBMK®-202510",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    assert p.factors_dev_json is None
    assert p.factors_ops_json is None
