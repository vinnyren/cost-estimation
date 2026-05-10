import pytest, uuid
from httpx import AsyncClient, ASGITransport

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


@pytest.fixture
async def client_with_project(monkeypatch, tmp_path):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    db_file = f"/tmp/cost-test-{uuid.uuid4()}.sqlite"
    monkeypatch.setenv("COST_DB_PATH", db_file)
    monkeypatch.setenv("COST_DATA_DIR", str(tmp_path))
    import importlib
    for m in ["app.config", "app.db.session", "app.deps", "app.db.models",
              "app.services.params", "app.services.projects", "app.services.calc",
              "app.services.uploads", "app.services.functions",
              "app.api.projects", "app.api.params", "app.api.calc",
              "app.api.uploads", "app.api.functions",
              "app.api.health", "app.main"]:
        importlib.reload(importlib.import_module(m))
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    import app.services.params
    app.services.params.seed_from_csbmk()
    import app.main
    transport = ASGITransport(app=app.main.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/projects", headers=H, json={
            "name": "T", "project_type": "dev_only", "phase": "bidding",
            "city": "北京", "industry": "电子政务", "mode": "forward",
            "basis_data_ver": "CSBMK®-202510",
        })
        pid = r.json()["data"]["id"]
        yield c, pid


SAMPLE_FP = {
    "name": "门户首页", "category": "EQ", "complexity": "low",
    "ufp": 4.0, "us": 4.0, "subsystem": "政务平台", "l2_module": "首页",
}


async def test_create_fp(client_with_project):
    c, pid = client_with_project
    r = await c.post(f"/api/projects/{pid}/functions",
                      headers={**H, "Content-Type": "application/json"}, json=SAMPLE_FP)
    assert r.status_code == 201
    assert r.json()["data"]["category"] == "EQ"


async def test_bulk_replace(client_with_project):
    c, pid = client_with_project
    items = [{**SAMPLE_FP, "name": f"Item-{i}"} for i in range(5)]
    r = await c.post(f"/api/projects/{pid}/functions/bulk",
                      headers={**H, "Content-Type": "application/json"},
                      json={"items": items, "replace": True})
    assert r.status_code == 201
    assert r.json()["data"]["written"] == 5

    r2 = await c.get(f"/api/projects/{pid}/functions", headers=H)
    assert len(r2.json()["data"]) == 5


async def test_patch_fp_marks_results_stale(client_with_project):
    c, pid = client_with_project
    r = await c.post(f"/api/projects/{pid}/functions",
                      headers={**H, "Content-Type": "application/json"}, json=SAMPLE_FP)
    fp_id = r.json()["data"]["id"]
    r2 = await c.patch(f"/api/projects/{pid}/functions/{fp_id}",
                        headers={**H, "Content-Type": "application/json"},
                        json={"complexity": "high", "ufp": 7.0})
    assert r2.status_code == 200
    assert r2.json()["data"]["complexity"] == "high"
