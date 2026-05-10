"""Tests for POST /api/projects/{id}/functions/restore?version=N.

The restore endpoint replays a previously taken FPSnapshot back into the
function_points table. bulk_write already snapshots before mutation, so the
restore-cycle is: bulk_write v1 → bulk_write v2 → restore v1 → reads v1's data.
"""
import pytest
import uuid
from httpx import AsyncClient, ASGITransport

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    db_file = f"/tmp/cost-test-{uuid.uuid4()}.sqlite"
    monkeypatch.setenv("COST_DB_PATH", db_file)
    import importlib
    for m in ["app.config", "app.db.session", "app.deps", "app.db.models",
              "app.services.params", "app.services.projects", "app.services.calc",
              "app.services.functions",
              "app.api.projects", "app.api.params", "app.api.calc",
              "app.api.functions", "app.api.health", "app.main"]:
        importlib.reload(importlib.import_module(m))
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    import app.services.params
    app.services.params.seed_from_csbmk()
    import app.main
    transport = ASGITransport(app=app.main.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects",
        headers={**H, "Content-Type": "application/json"},
        json={
            "name": "qa-restore",
            "project_type": "dev_only",
            "mode": "forward",
            "city": "北京",
            "industry": "电子政务",
            "phase": "bidding",
            "basis_data_ver": "CSBMK®-202510",
        },
    )
    return r.json()["data"]["id"]


async def _bulk(client, pid, items, replace=False):
    return await client.post(
        f"/api/projects/{pid}/functions/bulk",
        headers={**H, "Content-Type": "application/json"},
        json={"items": items, "replace": replace},
    )


async def test_restore_replaces_current_with_snapshot(client):
    pid = await _make_project(client)
    # v1: 1 个 FP
    await _bulk(client, pid, [
        {"name": "v1-only", "category": "EI", "complexity": "low",
         "ufp": 3, "us": 3, "source": "manual"},
    ], replace=True)

    # v2: 完全替换为 2 个不同 FP
    await _bulk(client, pid, [
        {"name": "v2-a", "category": "EQ", "complexity": "average",
         "ufp": 4, "us": 4, "source": "manual"},
        {"name": "v2-b", "category": "ILF", "complexity": "high",
         "ufp": 15, "us": 15, "source": "manual"},
    ], replace=True)

    cur = await client.get(f"/api/projects/{pid}/functions", headers=H)
    names_v2 = sorted([fp["name"] for fp in cur.json()["data"]])
    assert names_v2 == ["v2-a", "v2-b"]

    # restore 回 v1
    r = await client.post(
        f"/api/projects/{pid}/functions/restore?version=1",
        headers=H,
    )
    assert r.status_code == 200, r.text

    cur2 = await client.get(f"/api/projects/{pid}/functions", headers=H)
    names_after = [fp["name"] for fp in cur2.json()["data"]]
    assert names_after == ["v1-only"]


async def test_restore_unknown_version_404(client):
    pid = await _make_project(client)
    await _bulk(client, pid, [
        {"name": "x", "category": "EI", "complexity": "low",
         "ufp": 3, "us": 3, "source": "manual"},
    ], replace=True)
    r = await client.post(
        f"/api/projects/{pid}/functions/restore?version=999",
        headers=H,
    )
    assert r.status_code == 404


async def test_restore_unknown_project_404(client):
    r = await client.post(
        "/api/projects/prj-nope/functions/restore?version=1",
        headers=H,
    )
    assert r.status_code == 404


async def test_restore_marks_results_stale(client):
    """restore 后已有结果应被标记 stale，避免展示陈旧造价。"""
    pid = await _make_project(client)
    await _bulk(client, pid, [
        {"name": "x", "category": "EI", "complexity": "low",
         "ufp": 3, "us": 3, "source": "manual"},
    ], replace=True)
    await _bulk(client, pid, [
        {"name": "y", "category": "EQ", "complexity": "high",
         "ufp": 6, "us": 6, "source": "manual"},
    ], replace=True)

    # 跑一次 forward 让 Result 行存在
    await client.post(
        "/api/calc/forward",
        headers={**H, "Content-Type": "application/json"},
        json={"project_id": pid},
    )

    # restore v1
    r = await client.post(
        f"/api/projects/{pid}/functions/restore?version=1",
        headers=H,
    )
    assert r.status_code == 200

    # 直接查 DB 确认 stale
    from app.db.session import SessionLocal
    from app.db.models import Result
    db = SessionLocal()
    try:
        rows = db.query(Result).filter_by(project_id=pid).all()
        assert all(r.is_stale for r in rows)
    finally:
        db.close()
