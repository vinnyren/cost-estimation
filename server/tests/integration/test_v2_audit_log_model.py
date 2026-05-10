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


def test_audit_log_inserts_with_required_fields(db):
    from app.db.models import Project, AuditLog
    p = Project(
        id="p1", name="T", project_type="dev_only", phase="bidding",
        city="北京", industry="电子政务", mode="forward",
        basis_data_ver="CSBMK®-202510",
    )
    db.add(p)
    db.commit()
    log = AuditLog(
        project_id="p1", actor="user", action="project.create",
        target="p1", diff_json=json.dumps({"after": {"name": "T"}})
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    assert log.id > 0
    assert log.action == "project.create"
    assert log.ts is not None


def test_audit_log_cascades_on_project_delete(db):
    from app.db.models import Project, AuditLog
    p = Project(
        id="p2", name="T2", project_type="dev_only", phase="bidding",
        city="北京", industry="电子政务", mode="forward",
        basis_data_ver="CSBMK®-202510",
    )
    db.add(p)
    db.commit()
    db.add(AuditLog(project_id="p2", action="project.create", target="p2"))
    db.commit()
    db.delete(p)
    db.commit()
    assert db.query(AuditLog).filter_by(project_id="p2").count() == 0
