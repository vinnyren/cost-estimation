"""Integration tests for the audit-log middleware + GET /audit endpoint.

GAP-J (Task T5) — every mutating call under /api/projects/* must leave a row
in audit_log; GET requests must not; cursor pagination via ?before_id= must
return strictly older rows.
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


@pytest.fixture
async def client(monkeypatch, tmp_path):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    monkeypatch.setenv("COST_DB_PATH", f"/tmp/cost-test-{uuid.uuid4()}.sqlite")
    monkeypatch.setenv("COST_DATA_DIR", str(tmp_path))
    import importlib
    for m in ["app.config", "app.db.session", "app.deps", "app.db.models",
              "app.middleware.audit", "app.services.audit", "app.services.params",
              "app.api.projects", "app.api.params", "app.api.audit",
              "app.api.health", "app.main"]:
        importlib.reload(importlib.import_module(m))
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    import app.services.params
    app.services.params.seed_from_csbmk()
    import app.main
    transport = ASGITransport(app=app.main.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _make_project(c) -> str:
    r = await c.post("/api/projects", headers=H, json={
        "name": "T", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    return r.json()["data"]["id"]


async def test_project_create_writes_audit_log(client):
    pid = await _make_project(client)
    rows = (await client.get(f"/api/projects/{pid}/audit", headers=H)).json()["data"]
    assert any(r["action"] == "project.create" for r in rows)


async def test_project_patch_writes_audit_log(client):
    pid = await _make_project(client)
    await client.patch(
        f"/api/projects/{pid}", headers={**H, "Content-Type": "application/json"},
        json={"name": "T-renamed"})
    rows = (await client.get(f"/api/projects/{pid}/audit", headers=H)).json()["data"]
    actions = [r["action"] for r in rows]
    assert "project.update" in actions
    assert actions.count("project.create") == 1


async def test_get_does_not_write_audit_log(client):
    pid = await _make_project(client)
    initial = len((await client.get(f"/api/projects/{pid}/audit", headers=H)).json()["data"])
    for _ in range(3):
        await client.get(f"/api/projects/{pid}", headers=H)
    rows = (await client.get(f"/api/projects/{pid}/audit", headers=H)).json()["data"]
    assert len(rows) == initial


async def test_audit_log_cursor_pagination(client):
    pid = await _make_project(client)
    for i in range(5):
        await client.patch(
            f"/api/projects/{pid}", headers={**H, "Content-Type": "application/json"},
            json={"name": f"T-{i}"})
    rows = (await client.get(f"/api/projects/{pid}/audit?limit=3", headers=H)).json()["data"]
    assert len(rows) == 3
    last_id = rows[-1]["id"]
    next_page = (await client.get(
        f"/api/projects/{pid}/audit?limit=3&before_id={last_id}", headers=H
    )).json()["data"]
    assert all(r["id"] < last_id for r in next_page)
