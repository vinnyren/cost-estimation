import json


def test_audit_log_inserts_with_required_fields(db_session):
    from app.db.models import Project, AuditLog
    p = Project(
        id="p1", name="T", project_type="dev_only", phase="bidding",
        city="北京", industry="电子政务", mode="forward",
        basis_data_ver="CSBMK®-202510",
    )
    db_session.add(p)
    db_session.commit()
    log = AuditLog(
        project_id="p1", actor="user", action="project.create",
        target="p1", diff_json=json.dumps({"after": {"name": "T"}})
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)
    assert log.id > 0
    assert log.action == "project.create"
    assert log.ts is not None


def test_audit_log_cascades_on_project_delete(db_session):
    from app.db.models import Project, AuditLog
    p = Project(
        id="p2", name="T2", project_type="dev_only", phase="bidding",
        city="北京", industry="电子政务", mode="forward",
        basis_data_ver="CSBMK®-202510",
    )
    db_session.add(p)
    db_session.commit()
    db_session.add(AuditLog(project_id="p2", action="project.create", target="p2"))
    db_session.commit()
    db_session.delete(p)
    db_session.commit()
    assert db_session.query(AuditLog).filter_by(project_id="p2").count() == 0
