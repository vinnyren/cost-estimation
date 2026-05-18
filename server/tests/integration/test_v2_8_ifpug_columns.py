"""v2.8 — FunctionPoint 新增 det/ret/ftr 列、Project 新增 assessment_kind 列。"""
import pytest
from app.db.models import Project, FunctionPoint

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


def _seed(db, pid="p-ifpug-cols"):
    p = Project(id=pid, name="ifpug cols",
                project_type="dev_only", phase="bidding",
                city="北京", industry="电子政务",
                mode="forward", basis_data_ver="CSBMK-202510",
                assessment_kind="development")
    db.add(p)
    db.commit()
    return p


def test_project_has_assessment_kind_column(db_session):
    p = _seed(db_session)
    assert p.assessment_kind == "development"
    cols = {c.name for c in Project.__table__.columns}
    assert "assessment_kind" in cols


def test_function_point_has_ifpug_columns(db_session):
    cols = {c.name for c in FunctionPoint.__table__.columns}
    assert {"det", "ret", "ftr"} <= cols


@pytest.mark.asyncio
async def test_create_fp_with_ifpug_fields_persists(client_factory, db_session):
    _seed(db_session, pid="p-ifpug-create")
    async with await client_factory() as client:
        r = await client.post(
            "/api/projects/p-ifpug-create/functions",
            headers={**H, "Content-Type": "application/json"},
            json={
                "name": "用户表", "category": "ILF", "complexity": "average",
                "det": 25, "ret": 3, "ufp": 10, "us": 10, "modify_type": "add",
            },
        )
        assert r.status_code == 201
        data = r.json()["data"]
        assert data["det"] == 25
        assert data["ret"] == 3
        assert data["modify_type"] == "add"
