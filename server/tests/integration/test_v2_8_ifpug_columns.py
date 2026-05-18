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


@pytest.mark.asyncio
async def test_create_fp_autocomputes_ufp_from_ifpug(client_factory, db_session):
    """提供 det/ret 时 create 按 IFPUG 重算 ufp/us，忽略请求里的手填值。"""
    _seed(db_session, pid="p-ifpug-auto")
    async with await client_factory() as client:
        r = await client.post(
            "/api/projects/p-ifpug-auto/functions",
            headers={**H, "Content-Type": "application/json"},
            json={
                "name": "用户表", "category": "ILF", "complexity": "low",
                "det": 60, "ret": 6, "ufp": 999, "us": 999, "modify_type": "add",
            },
        )
        assert r.status_code == 201
        data = r.json()["data"]
        # det=60 ret=6 → high → ILF high = 15；complexity 也被重算为 high
        assert data["complexity"] == "high"
        assert data["ufp"] == 15
        assert data["us"] == 15


@pytest.mark.asyncio
async def test_forward_uses_assessment_kind(client_factory, db_session):
    """enhancement 项目 forward 计入 change/delete。"""
    from app.db.models import FunctionPoint
    p = _seed(db_session, pid="p-ifpug-efp")
    p.assessment_kind = "enhancement"
    for mt, us in [("add", 10), ("change", 20), ("delete", 5)]:
        db_session.add(FunctionPoint(
            id=f"fp-{mt}", project_id="p-ifpug-efp", version=1,
            category="EI", complexity="average", modify_type=mt,
            ufp=us, us=us))
    db_session.commit()
    async with await client_factory() as client:
        r = await client.post(
            "/api/calc/forward",
            headers={**H, "Content-Type": "application/json"},
            json={"project_id": "p-ifpug-efp"},
        )
        assert r.status_code == 200
        assert r.json()["data"]["scale_us"] == 35  # 10 + 20 + 5
