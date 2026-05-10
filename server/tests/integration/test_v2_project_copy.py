"""Integration tests for POST /api/projects/{id}/copy.

Task T6 (v2.0 gap-closure) — GAP-I project copy. The copy must:
  - clone project metadata (name overridable, factors/factors_ops/client/evaluator…)
  - clone function points (with new ids, source="copied")
  - copy param overrides with a "(copied from …)" reason
  - NOT carry over results or fp_snapshots
  - 404 when src project missing; 422 when new name is empty
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
              "app.services.params", "app.services.projects",
              "app.api.projects", "app.api.params", "app.api.functions",
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


async def test_copy_clones_project_metadata(client):
    r = await client.post("/api/projects", headers=H, json={
        "name": "原项目", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510", "client": "甲方A", "evaluator": "评估方B",
    })
    src_id = r.json()["data"]["id"]
    r2 = await client.post(
        f"/api/projects/{src_id}/copy", headers=H, json={"name": "副本"})
    assert r2.status_code == 201
    new = r2.json()["data"]
    assert new["id"] != src_id
    assert new["name"] == "副本"
    assert new["client"] == "甲方A"
    assert new["evaluator"] == "评估方B"


async def test_copy_clones_function_points(client):
    r = await client.post("/api/projects", headers=H, json={
        "name": "原项目", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    src_id = r.json()["data"]["id"]
    await client.post(
        f"/api/projects/{src_id}/functions", headers=H,
        json={"name": "fp1", "category": "EI", "complexity": "low",
              "ufp": 3, "us": 3, "source": "manual"})
    r2 = await client.post(
        f"/api/projects/{src_id}/copy", headers=H, json={"name": "副本"})
    new_id = r2.json()["data"]["id"]
    fps = (await client.get(f"/api/projects/{new_id}/functions", headers=H)).json()["data"]
    assert len(fps) == 1
    assert fps[0]["name"] == "fp1"


async def test_copy_does_not_clone_results_or_snapshots(client):
    r = await client.post("/api/projects", headers=H, json={
        "name": "原", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    src_id = r.json()["data"]["id"]
    await client.post(
        f"/api/projects/{src_id}/functions", headers=H,
        json={"name": "fp1", "category": "EI", "complexity": "low",
              "ufp": 3, "us": 3, "source": "manual"})
    await client.post(f"/api/projects/{src_id}/calc/forward", headers=H, json={})
    r2 = await client.post(
        f"/api/projects/{src_id}/copy", headers=H, json={"name": "副本"})
    new_id = r2.json()["data"]["id"]
    snaps = (await client.get(
        f"/api/projects/{new_id}/functions/snapshots", headers=H)).json()["data"]
    assert snaps == []


async def test_copy_404_on_unknown_source(client):
    r = await client.post(
        "/api/projects/no-such-id/copy", headers=H, json={"name": "x"})
    assert r.status_code == 404


async def test_copy_422_on_empty_name(client):
    r = await client.post("/api/projects", headers=H, json={
        "name": "原", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    src_id = r.json()["data"]["id"]
    r2 = await client.post(
        f"/api/projects/{src_id}/copy", headers=H, json={"name": ""})
    assert r2.status_code == 422
