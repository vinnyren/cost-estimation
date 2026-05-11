"""GAP-B foundation: Project 加 factors_dev_json / factors_ops_json 列。"""
import json


def test_project_has_factors_columns(db_session):
    from app.db.models import Project
    p = Project(
        id="p1", name="T", project_type="dev_only", phase="bidding",
        city="北京", industry="电子政务", mode="forward",
        basis_data_ver="CSBMK®-202510",
        factors_dev_json=json.dumps({"app_type": "OLTP"}),
        factors_ops_json=None,
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    assert json.loads(p.factors_dev_json) == {"app_type": "OLTP"}
    assert p.factors_ops_json is None


def test_project_factors_default_null(db_session):
    from app.db.models import Project
    p = Project(
        id="p2", name="T2", project_type="dev_only", phase="bidding",
        city="北京", industry="电子政务", mode="forward",
        basis_data_ver="CSBMK®-202510",
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    assert p.factors_dev_json is None
    assert p.factors_ops_json is None
